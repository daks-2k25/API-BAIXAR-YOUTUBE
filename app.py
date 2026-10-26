from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.wsgi import ClosingIterator
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from urllib.parse import urlparse, parse_qs

# Importando as ferramentas da pasta servicos/
from servicos.caminhos import EXECUTAVEL, PASTA_DESTINO, PASTA_DOWNLOADS, PASTA_PAINEL
from servicos import atualizador
atualizador.usar_versao_atualizada()  # Precisa vir antes de qualquer import do yt-dlp
from servicos.downloader import (
    STATUS_FINAIS, adicionar_fila, arquivos_salvos, cancelar_download,
    caminho_sem_sobrescrever, erros_download, nome_de_arquivo_seguro, status_download, titulos_download,
)
from servicos.conversor import FORMATOS, converter_imagem
from servicos.informacoes import obter_informacoes
from servicos.sites import mensagem_de_erro
from servicos import autoatualizacao, historico, preferencias

# O painel web (pasta painel/) é servido pela própria API em http://localhost:5000
app = Flask(__name__, static_folder=PASTA_PAINEL, static_url_path="")
CORS(app)


# Resoluções permitidas para MP4 (máximo 1080p para não pesar no servidor)
QUALIDADES_PERMITIDAS = [360, 480, 720, 1080]
QUALIDADE_PADRAO = 720

# O ID vira nome de arquivo: só letras, números, "-" e "_" (evita acessar outras pastas)
PADRAO_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def ao_terminar_envio(resposta, funcao):
    """Executa a função só depois que o arquivo foi enviado e fechado.
    (No Windows não dá para apagar um arquivo que ainda está aberto.)"""
    resposta.response = ClosingIterator(resposta.response, funcao)
    return resposta

def ler_tempo(valor):
    """Converte "1:20", "1:02:05" ou 80 em segundos. Vazio -> None."""
    if valor is None or str(valor).strip() == "":
        return None
    partes = str(valor).strip().split(":")
    if len(partes) > 3:
        raise ValueError("tempo inválido")
    segundos = 0.0
    for parte in partes:
        numero = float(parte)
        if numero < 0:
            raise ValueError("tempo negativo")
        segundos = segundos * 60 + numero
    return segundos


def e_playlist_sem_video(url):
    """True quando o link é de uma playlist inteira (ex.: youtube.com/playlist?list=...).
    Um vídeo aberto dentro de uma playlist (watch?v=...&list=...) é aceito:
    o downloader baixa só aquele vídeo."""
    try:
        partes = urlparse(str(url).strip())
    except ValueError:
        return False

    parametros = parse_qs(partes.query)
    if "list" not in parametros:
        return False

    host = (partes.hostname or "").lower()
    tem_video = (
        "v" in parametros
        or (host.endswith("youtu.be") and len(partes.path) > 1)
        or partes.path.startswith(("/shorts/", "/live/", "/embed/"))
    )
    return not tem_video


@app.route('/')
def painel():
    return send_from_directory(PASTA_PAINEL, "index.html")

# ==========================================
# FERRAMENTA 1: YOUTUBE DOWNLOADER
# ==========================================

@app.route('/api/download', methods=['POST'])
def download_api():
    dados = request.get_json()

    if not dados or 'url' not in dados:
        return jsonify({"erro": "A URL do video e obrigatoria."}), 400

    url = dados['url']
    formato = dados.get('formato', 'mp4')
    id_download = str(dados.get('id', uuid.uuid4()))

    if formato not in ('mp4', 'mp3'):
        return jsonify({"erro": "Formato inválido. Use 'mp4' ou 'mp3'."}), 400

    if e_playlist_sem_video(url):
        return jsonify({"erro": "Este link é de uma playlist. Playlists não são permitidas: envie o link de um vídeo só."}), 400

    if not PADRAO_ID.match(id_download):
        return jsonify({"erro": "ID inválido. Use só letras, números, '-' e '_' (até 64 caracteres)."}), 400

    try:
        qualidade = int(str(dados.get('qualidade', QUALIDADE_PADRAO)).lower().rstrip('p'))
    except ValueError:
        qualidade = None

    if qualidade not in QUALIDADES_PERMITIDAS:
        return jsonify({
            "erro": f"Qualidade inválida. Opções: {', '.join(f'{q}p' for q in QUALIDADES_PERMITIDAS)}."
        }), 400

    # Trecho opcional: "inicio" e "fim" como "1:20" (ou segundos)
    try:
        inicio = ler_tempo(dados.get('inicio'))
        fim = ler_tempo(dados.get('fim'))
    except ValueError:
        return jsonify({"erro": "Tempo do trecho inválido. Use o formato 1:20 (minutos:segundos)."}), 400

    trecho = None
    if inicio is not None or fim is not None:
        inicio = inicio or 0
        fim = fim if fim is not None else float("inf")  # sem fim: até o final do vídeo
        if fim <= inicio:
            return jsonify({"erro": "O fim do trecho precisa ser depois do início."}), 400
        trecho = (inicio, fim)

    adicionar_fila(url, formato, qualidade, id_download, trecho)

    return jsonify({
        "mensagem": "Vídeo enfileirado com sucesso!",
        "id": id_download,
        "formato": formato,
        "qualidade": f"{qualidade}p" if formato == "mp4" else None,
        "trecho": {"inicio": trecho[0], "fim": None if trecho[1] == float("inf") else trecho[1]} if trecho else None,
        "status": "Na fila..."
    }), 202


@app.route('/api/info', methods=['GET'])
def info_api():
    # Prévia do vídeo (título, canal, duração, miniatura) antes de baixar
    url = request.args.get('url', '').strip()

    if not url:
        return jsonify({"erro": "Informe a URL do vídeo."}), 400

    if e_playlist_sem_video(url):
        return jsonify({"erro": "Este link é de uma playlist."}), 400

    try:
        return jsonify(obter_informacoes(url))
    except Exception as e:
        print(f"[INFO] Não foi possível obter a prévia de {url}: {e}")
        return jsonify({"erro": mensagem_de_erro(e)}), 404


@app.route('/api/qualidades', methods=['GET'])
def qualidades_api():
    # Para o frontend montar a lista de opções
    return jsonify({
        "qualidades": [f"{q}p" for q in QUALIDADES_PERMITIDAS],
        "padrao": f"{QUALIDADE_PADRAO}p"
    })

@app.route('/api/progresso/<id_download>', methods=['GET'])
def progresso_api(id_download):
    status = status_download.get(id_download, "Desconhecido")
    caminho = arquivos_salvos.get(id_download)
    return jsonify({
        "id": id_download,
        "status": status,
        "titulo": titulos_download.get(id_download),
        "arquivo": os.path.basename(caminho) if caminho else None,  # nome do arquivo na pasta Downloads
        "erro": erros_download.get(id_download) if status == "Erro" else None,  # motivo da falha
    })


@app.route('/api/cancelar/<id_download>', methods=['POST'])
def cancelar_api(id_download):
    if not cancelar_download(id_download):
        return jsonify({"erro": "Esse download não existe ou já terminou."}), 404
    return jsonify({"mensagem": "Cancelando...", "id": id_download})


def caminho_do_arquivo(id_arquivo):
    """Arquivo salvo nesta sessão ou, depois de reabrir o programa, pelo histórico."""
    return arquivos_salvos.get(id_arquivo) or historico.caminho(id_arquivo)


@app.route('/api/mostrar/<id_download>', methods=['POST'])
def mostrar_na_pasta_api(id_download):
    # Abre o Explorador de Arquivos com o arquivo baixado selecionado
    caminho = caminho_do_arquivo(id_download)
    if not caminho or not os.path.exists(caminho):
        return jsonify({"erro": "Arquivo não encontrado (foi movido ou apagado?)."}), 404
    if sys.platform == "win32":
        subprocess.Popen(f'explorer /select,"{caminho}"')
    return jsonify({"mensagem": "Pasta aberta."})


@app.route('/api/arquivo/<id_download>', methods=['GET'])
def baixar_arquivo_api(id_download):
    # O arquivo já fica salvo na pasta Downloads; esta rota é para quem usa a API
    # de outro programa e quer receber o arquivo pela resposta HTTP
    caminho = arquivos_salvos.get(id_download)
    if not caminho or not os.path.exists(caminho):
        return jsonify({"erro": "Arquivo ainda não está pronto ou não foi encontrado."}), 404
    return send_file(caminho, as_attachment=True, download_name=os.path.basename(caminho))


# ==========================================
# MEUS DOWNLOADS (histórico do que o programa salvou)
# ==========================================

@app.route('/api/historico', methods=['GET'])
def historico_api():
    return jsonify(historico.listar())


@app.route('/api/historico/<id_arquivo>', methods=['DELETE'])
def remover_do_historico_api(id_arquivo):
    # Só tira da lista: o arquivo continua na pasta Downloads
    if not historico.remover(id_arquivo):
        return jsonify({"erro": "Esse item não está no histórico."}), 404
    return jsonify({"mensagem": "Removido da lista."})


@app.route('/api/historico', methods=['DELETE'])
def limpar_historico_api():
    historico.limpar()
    return jsonify({"mensagem": "Histórico limpo."})


@app.route('/api/abrir/<id_arquivo>', methods=['POST'])
def abrir_arquivo_api(id_arquivo):
    # Abre o arquivo no programa padrão do Windows (player de vídeo, música, fotos)
    caminho = caminho_do_arquivo(id_arquivo)
    if not caminho or not os.path.exists(caminho):
        return jsonify({"erro": "Arquivo não encontrado (foi movido ou apagado?)."}), 404
    if sys.platform == "win32":
        os.startfile(caminho)
    return jsonify({"mensagem": "Arquivo aberto."})


# ==========================================
# FERRAMENTA 2: CONVERSOR DE FOTOS (HEIC -> JPG, HEIC/JPG/PNG -> WebP)
# ==========================================

# /api/converter/heic é o endereço antigo (sempre JPG); continua funcionando
@app.route('/api/converter/heic', methods=['POST'])
@app.route('/api/converter/imagem', methods=['POST'])
def converter_imagem_api():
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo' no form-data."}), 400

    arquivo = request.files['arquivo']

    if arquivo.filename == '':
        return jsonify({"erro": "Nenhum arquivo selecionado."}), 400

    formato = (request.form.get('formato') or request.args.get('formato') or 'jpg').lower()
    if formato not in FORMATOS:
        return jsonify({"erro": f"Formato inválido. Use: {', '.join(FORMATOS)}."}), 400

    extensao = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
    if extensao not in FORMATOS[formato]:
        aceitos = ", ".join(e.upper() for e in FORMATOS[formato])
        return jsonify({"erro": f"Para {formato.upper()}, envie uma foto {aceitos}."}), 400

    # Gera um ID para a imagem e salva temporariamente (com a extensão original, que o FFmpeg usa)
    id_conversao = str(uuid.uuid4())
    caminho_original = os.path.join(PASTA_DOWNLOADS, f"{id_conversao}_original.{extensao}")
    arquivo.save(caminho_original)

    caminho_convertido = converter_imagem(
        caminho_original, formato, os.path.join(PASTA_DOWNLOADS, f"{id_conversao}.{formato}"),
    )

    if caminho_convertido and os.path.exists(caminho_convertido):
        nome_sem_extensao = arquivo.filename.rsplit('.', 1)[0]
        nome_download = f"{nome_sem_extensao}.{formato}"

        # O painel pede ?salvar=1: a foto vai direto para a pasta Downloads (igual aos vídeos)
        if request.args.get('salvar') == '1':
            destino = caminho_sem_sobrescrever(PASTA_DESTINO, nome_de_arquivo_seguro(nome_sem_extensao), formato)
            shutil.move(caminho_convertido, destino)
            if os.path.exists(caminho_original):
                os.remove(caminho_original)
            arquivos_salvos[id_conversao] = destino  # permite usar /api/mostrar/<id>
            historico.registrar(id_conversao, destino, nome_sem_extensao)
            return jsonify({"id": id_conversao, "arquivo": os.path.basename(destino)})

        resposta = send_file(caminho_convertido, as_attachment=True, download_name=nome_download)

        def limpar_arquivos():
            try:
                if os.path.exists(caminho_original):
                    os.remove(caminho_original)
                if os.path.exists(caminho_convertido):
                    os.remove(caminho_convertido)
                print(f"Limpeza: Arquivos {id_conversao} removidos com sucesso.")
            except Exception as e:
                print(f"Erro ao limpar arquivos: {e}")

        return ao_terminar_envio(resposta, limpar_arquivos)

    else:
        if os.path.exists(caminho_original):
            os.remove(caminho_original)
        return jsonify({"erro": f"Falha na conversão. Verifique se o arquivo é uma foto {extensao.upper()} válida."}), 500


# ==========================================
# INICIALIZAÇÃO (iniciar.bat, atalho, BaixarYouTube.exe ou "uv run app.py")
# ==========================================

PORTA = int(os.environ.get("PORTA", 5000))
ENDERECO_PAINEL = f"http://127.0.0.1:{PORTA}"

# Janela própria do programa (pywebview). Fica None quando o painel abre no
# navegador, o que acontece só se a janela não puder ser criada neste PC.
janela = None
# Virou True quando a pessoa clica em "Abrir no navegador": a janela fecha, mas o programa continua
trocando_para_navegador = False

# Modo navegador: o programa fecha sozinho quando ninguém está com o painel
# aberto há esse tempo e não há downloads em andamento
FECHAR_SEM_PAINEL_SEGUNDOS = 3 * 60
ultimo_sinal_do_painel = time.time()


def ja_esta_rodando():
    """Verifica se o programa já está aberto (porta ocupada)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # No Windows, conectar numa porta fechada leva ~2s para falhar.
        # Se o programa estiver aberto, a resposta vem em milissegundos.
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", PORTA)) == 0


def esperar_servidor(limite_segundos=10):
    for _ in range(limite_segundos * 20):
        if ja_esta_rodando():
            return True
        time.sleep(0.05)
    return False


def reiniciar_programa(modo):
    """Abre o programa de novo daqui a ~2 segundos (tempo de este processo fechar),
    já no modo pedido ("janela" ou "navegador")."""
    if EXECUTAVEL:
        pasta, comando = os.path.dirname(sys.executable), f'"{sys.executable}"'
    else:
        pasta = os.path.dirname(os.path.abspath(__file__))
        comando = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
    # "ping" para esperar: o "timeout" do Windows falha quando não há janela de console
    subprocess.Popen(
        f'cmd /c ping -n 3 127.0.0.1 >nul & start "" {comando}',
        cwd=pasta, env=dict(os.environ, BAIXAR_YOUTUBE_MODO=modo),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def encerrar_programa():
    print("Encerrando o programa...")
    os._exit(0)


def ha_downloads_em_andamento():
    return any(st not in STATUS_FINAIS for st in list(status_download.values()))


@app.route('/api/modo', methods=['GET'])
def modo_api():
    # O painel esconde o botão "Encerrar" quando está na janela própria
    return jsonify({
        "janela": janela is not None and not trocando_para_navegador,
        "preferencia": preferencias.modo_de_abertura(),
    })


@app.route('/api/ping', methods=['POST'])
def ping_api():
    # No modo navegador, o painel avisa a cada 30 segundos que continua aberto
    global ultimo_sinal_do_painel
    ultimo_sinal_do_painel = time.time()
    return jsonify({"ok": True})


@app.route('/api/encerrar', methods=['POST'])
def encerrar_api():
    # Responde primeiro e fecha logo depois, para o painel receber a resposta
    threading.Timer(0.5, encerrar_programa).start()
    return jsonify({"mensagem": "Programa encerrado."})


@app.route('/api/focar', methods=['POST'])
def focar_api():
    # Clicou no atalho com o programa já aberto: traz a janela para a frente
    if janela is not None:
        janela.restore()
        janela.show()
        janela.on_top = True   # liga e desliga o "sempre no topo" para a
        janela.on_top = False  # janela passar na frente das outras
    else:
        webbrowser.open(ENDERECO_PAINEL)
    return jsonify({"ok": True})


@app.route('/api/preferencias', methods=['GET'])
def preferencias_api():
    return jsonify({"modo_abertura": preferencias.modo_de_abertura()})


@app.route('/api/preferencias', methods=['POST'])
def salvar_preferencias_api():
    # Configurações do painel: abrir sempre na janela do aplicativo ou no navegador
    modo = (request.get_json(silent=True) or {}).get("modo_abertura")
    if modo not in preferencias.MODOS_DE_ABERTURA:
        return jsonify({"erro": "Use 'janela' ou 'navegador'."}), 400
    preferencias.salvar("modo_abertura", modo)
    return jsonify({"modo_abertura": modo})


@app.route('/api/abrir-no-navegador', methods=['POST'])
def abrir_no_navegador_api():
    # Abre o painel no navegador agora e fecha a janela; o programa continua rodando
    global trocando_para_navegador
    if janela is not None:
        trocando_para_navegador = True
        threading.Timer(0.3, janela.destroy).start()
    webbrowser.open(ENDERECO_PAINEL)
    return jsonify({"ok": True})


@app.route('/api/reabrir-como-aplicativo', methods=['POST'])
def reabrir_como_aplicativo_api():
    # No navegador: reinicia o programa já na janela do aplicativo
    if janela is not None and not trocando_para_navegador:
        return jsonify({"erro": "O programa já está aberto como aplicativo."}), 409
    reiniciar_programa("janela")
    threading.Timer(0.5, encerrar_programa).start()
    return jsonify({"ok": True})


@app.route('/api/versao', methods=['GET'])
def versao_api():
    # Versão instalada e, se houver, a versão nova disponível no GitHub
    dados = dict(autoatualizacao.verificar(forcar=request.args.get('forcar') == '1'))
    # "adiada": a pessoa clicou em "Depois" para esta versão; o painel não insiste
    dados["adiada"] = bool(dados["disponivel"] and dados["nova"] == autoatualizacao.versao_adiada())
    return jsonify(dados)


@app.route('/api/versao/adiar', methods=['POST'])
def adiar_versao_api():
    # Botão "Depois" da notificação: não avisar de novo sobre esta versão
    versao = (request.get_json(silent=True) or {}).get("versao")
    if not versao:
        return jsonify({"erro": "Informe a versão."}), 400
    autoatualizacao.adiar(versao)
    return jsonify({"ok": True})


@app.route('/api/atualizar', methods=['POST'])
def atualizar_api():
    if ha_downloads_em_andamento():
        return jsonify({"erro": "Espere os downloads terminarem (ou cancele) antes de atualizar."}), 409
    try:
        autoatualizacao.aplicar()
    except Exception as e:
        print(f"[ATUALIZAÇÃO] Falhou: {e}")
        return jsonify({"erro": f"Não foi possível atualizar: {e}"}), 500

    # Responde ao painel e reinicia já na versão nova
    autoatualizacao.reiniciar()
    threading.Timer(0.5, encerrar_programa).start()
    return jsonify({"mensagem": "Atualizado! Reiniciando...", "versao": autoatualizacao.versao_instalada()})


def fechar_quando_ninguem_usar():
    while True:
        time.sleep(30)
        if not ha_downloads_em_andamento() and time.time() - ultimo_sinal_do_painel > FECHAR_SEM_PAINEL_SEGUNDOS:
            encerrar_programa()


def iniciar_servidor():
    from waitress import serve
    # Waitress: servidor robusto (o do Flask é só para desenvolvimento).
    # threads=16: atende o painel enquanto os downloads acontecem
    serve(app, host="127.0.0.1", port=PORTA, threads=16)


def colocar_icone_na_janela(titulo, caminho_icone):
    """Troca o ícone da janela (barra de título e barra de tarefas).

    Usa mensagens do Windows enviadas com PostMessage, que não esperam resposta.
    Não mexe na janela pelo .NET a partir de outra thread: isso pode travar a
    janela ("Não respondendo"), porque só a thread dona da janela pode alterá-la.
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    meu_pid = os.getpid()
    encontrada = []

    # Procura a janela com esse título que pertence a este processo
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def verificar(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == meu_pid:
            texto = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, texto, 256)
            if texto.value == titulo:
                encontrada.append(hwnd)
                return False
        return True

    user32.EnumWindows(verificar, 0)
    if not encontrada:
        return

    IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
    # Tipos declarados: no Windows 64 bits, os identificadores não cabem num int comum
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    for tipo, metrica in ((1, 11), (0, 49)):  # ícone grande (SM_CXICON) e pequeno (SM_CXSMICON)
        tamanho = user32.GetSystemMetrics(metrica)
        icone = user32.LoadImageW(None, caminho_icone, IMAGE_ICON, tamanho, tamanho, LR_LOADFROMFILE)
        if icone:
            user32.PostMessageW(encontrada[0], WM_SETICON, tipo, icone)


def abrir_janela():
    """Abre o painel numa janela própria. Bloqueia até a janela ser fechada."""
    global janela
    import webview

    if sys.platform == "win32":
        import ctypes
        # Faz a barra de tarefas tratar o programa como um aplicativo próprio (e não como "Python")
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BaixarYouTube.Painel")

    janela = webview.create_window(
        "Baixar YouTube", ENDERECO_PAINEL,
        width=760, height=900, min_size=(440, 620), background_color="#fff4ea",
    )

    def ao_mostrar():
        # Coloca a logo do programa na janela e na barra de tarefas
        try:
            colocar_icone_na_janela("Baixar YouTube", os.path.join(PASTA_PAINEL, "icone.ico"))
        except Exception as e:
            print(f"[JANELA] Não foi possível colocar o ícone: {e}")

    def ao_fechar():
        # Trocando para o navegador: o programa continua, então não precisa perguntar
        if trocando_para_navegador:
            return True
        # Avisa antes de fechar se ainda há download acontecendo
        if ha_downloads_em_andamento():
            return janela.create_confirmation_dialog(
                "Fechar o Baixar YouTube?",
                "Ainda há downloads em andamento. Se fechar agora, eles serão interrompidos.",
            )
        return True

    janela.events.shown += ao_mostrar
    janela.events.closing += ao_fechar
    webview.start(gui="edgechromium")


def usar_navegador(servidor, abrir=True):
    """Modo navegador: o painel fica numa aba e o programa roda em segundo plano.
    Fecha sozinho 3 minutos depois que nenhuma aba estiver aberta (sem downloads)."""
    global janela, ultimo_sinal_do_painel
    janela = None
    ultimo_sinal_do_painel = time.time()
    print(f"Painel no navegador: {ENDERECO_PAINEL}")
    if abrir:
        webbrowser.open(ENDERECO_PAINEL)
    threading.Thread(target=fechar_quando_ninguem_usar, daemon=True).start()
    servidor.join()


if __name__ == "__main__":
    # Clicou de novo com o programa já aberto: só traz a janela para a frente
    if ja_esta_rodando():
        try:
            urllib.request.urlopen(urllib.request.Request(f"{ENDERECO_PAINEL}/api/focar", method="POST"), timeout=3)
        except Exception:
            webbrowser.open(ENDERECO_PAINEL)
        sys.exit(0)

    print("==========================================")
    print("          Baixar YouTube")
    print("==========================================")

    servidor = threading.Thread(target=iniciar_servidor, daemon=True)
    servidor.start()
    esperar_servidor()
    atualizador.verificar_atualizacao()  # Só faz algo dentro do .exe, uma vez por dia

    # Janela do aplicativo ou navegador: escolhido em Configurações (⚙) no painel.
    # BAIXAR_YOUTUBE_MODO força um modo uma vez (usado ao reabrir pelo painel).
    modo = os.environ.pop("BAIXAR_YOUTUBE_MODO", "") or preferencias.modo_de_abertura()

    if modo == "janela":
        try:
            abrir_janela()
        except Exception as e:
            # Sem a janela (ex.: WebView2 ausente), usa o navegador
            print(f"[JANELA] Não foi possível abrir a janela própria ({e}); usando o navegador.")
            usar_navegador(servidor)
        else:
            if not trocando_para_navegador:
                encerrar_programa()  # a janela foi fechada
            # "Abrir no navegador": a aba já foi aberta; o programa segue no navegador
            usar_navegador(servidor, abrir=False)
    else:
        usar_navegador(servidor)
