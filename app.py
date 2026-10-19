from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.wsgi import ClosingIterator
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlparse, parse_qs

# Importando as ferramentas da pasta servicos/
from servicos.caminhos import PASTA_DOWNLOADS, PASTA_PAINEL
from servicos import atualizador
atualizador.usar_versao_atualizada()  # Precisa vir antes de qualquer import do yt-dlp
from servicos.downloader import (
    STATUS_FINAIS, adicionar_fila, arquivos_salvos, cancelar_download,
    status_download, titulos_download,
)
from servicos.conversor import converter_heic_para_jpg
from servicos.informacoes import obter_informacoes

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
        return jsonify({"erro": "Não encontramos esse vídeo. Confira o link."}), 404


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
    })


@app.route('/api/cancelar/<id_download>', methods=['POST'])
def cancelar_api(id_download):
    if not cancelar_download(id_download):
        return jsonify({"erro": "Esse download não existe ou já terminou."}), 404
    return jsonify({"mensagem": "Cancelando...", "id": id_download})


@app.route('/api/mostrar/<id_download>', methods=['POST'])
def mostrar_na_pasta_api(id_download):
    # Abre o Explorador de Arquivos com o arquivo baixado selecionado
    caminho = arquivos_salvos.get(id_download)
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
# FERRAMENTA 2: CONVERSOR DE HEIC PARA JPG
# ==========================================

@app.route('/api/converter/heic', methods=['POST'])
def converter_heic_api():
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo' no form-data."}), 400

    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        return jsonify({"erro": "Nenhum arquivo selecionado."}), 400

    # Gera um ID para a imagem e salva temporariamente
    id_conversao = str(uuid.uuid4())
    caminho_heic = os.path.join(PASTA_DOWNLOADS, f"{id_conversao}.heic")
    arquivo.save(caminho_heic)

    # Aciona o seu conversor.py
    caminho_jpg = converter_heic_para_jpg(caminho_heic)

    if caminho_jpg and os.path.exists(caminho_jpg):
        nome_download = arquivo.filename.rsplit('.', 1)[0] + ".jpg"
        resposta = send_file(caminho_jpg, as_attachment=True, download_name=nome_download)

        def limpar_arquivos():
            try:
                if os.path.exists(caminho_heic):
                    os.remove(caminho_heic)
                if os.path.exists(caminho_jpg):
                    os.remove(caminho_jpg)
                print(f"Limpeza: Arquivos {id_conversao} removidos com sucesso.")
            except Exception as e:
                print(f"Erro ao limpar arquivos: {e}")

        return ao_terminar_envio(resposta, limpar_arquivos)
        
    else:
        if os.path.exists(caminho_heic):
            os.remove(caminho_heic)
        return jsonify({"erro": "Falha na conversão. Verifique se o arquivo é um HEIC válido."}), 500


# ==========================================
# INICIALIZAÇÃO (python app.py, iniciar.bat ou BaixarYouTube.exe)
# ==========================================

PORTA = int(os.environ.get("PORTA", 5000))
ENDERECO_PAINEL = f"http://localhost:{PORTA}"

# Sem a janela preta, o programa fecha sozinho quando ninguém está com o painel
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


def abrir_navegador_quando_pronto():
    """Fica checando a porta e abre o navegador no instante em que o servidor sobe."""
    for _ in range(100):  # desiste depois de ~10 segundos
        if ja_esta_rodando():
            webbrowser.open(ENDERECO_PAINEL)
            return
        time.sleep(0.1)


def encerrar_programa():
    print("Encerrando o programa...")
    os._exit(0)


@app.route('/api/ping', methods=['POST'])
def ping_api():
    # O painel avisa a cada 30 segundos que continua aberto
    global ultimo_sinal_do_painel
    ultimo_sinal_do_painel = time.time()
    return jsonify({"ok": True})


@app.route('/api/encerrar', methods=['POST'])
def encerrar_api():
    # Responde primeiro e fecha logo depois, para o painel receber a resposta
    threading.Timer(0.5, encerrar_programa).start()
    return jsonify({"mensagem": "Programa encerrado."})


def fechar_quando_ninguem_usar():
    while True:
        time.sleep(30)
        baixando = any(st not in STATUS_FINAIS for st in list(status_download.values()))
        if not baixando and time.time() - ultimo_sinal_do_painel > FECHAR_SEM_PAINEL_SEGUNDOS:
            encerrar_programa()


if __name__ == "__main__":
    # Clicou de novo com o programa já aberto: só abre o navegador
    if ja_esta_rodando():
        print(f"O programa já está aberto. Abrindo {ENDERECO_PAINEL} ...")
        webbrowser.open(ENDERECO_PAINEL)
        sys.exit(0)

    print("==========================================")
    print("          Baixar YouTube")
    print("==========================================")
    print(f"Painel: {ENDERECO_PAINEL}")
    print("Para fechar: botão \"Encerrar\" no painel (ou feche o painel e espere 3 minutos).\n")

    # Abre o painel no navegador assim que o servidor estiver pronto
    threading.Thread(target=abrir_navegador_quando_pronto, daemon=True).start()
    threading.Thread(target=fechar_quando_ninguem_usar, daemon=True).start()
    atualizador.verificar_atualizacao()  # Só faz algo dentro do .exe, uma vez por dia

    # Sem debug: o modo debug reinicia o processo e não funciona dentro do .exe
    app.run(host="127.0.0.1", port=PORTA, debug=False)