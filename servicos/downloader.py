import glob
import os
import queue
import re
import shutil
import threading
import time

import yt_dlp
from yt_dlp.utils import DownloadCancelled, download_range_func

from servicos.caminhos import PASTA_DESTINO, PASTA_DOWNLOADS
from servicos.sites import mensagem_de_erro, opcoes_de_login, titulo_amigavel

# Quantos downloads rodam ao mesmo tempo (os outros esperam na fila)
DOWNLOADS_SIMULTANEOS = 3

# Quantas vezes tenta baixar antes de marcar "Erro"
TENTATIVAS = 2

# Status que indicam que o download acabou (deu certo ou não)
STATUS_FINAIS = ("Pronto", "Erro", "Cancelado")

# Dicionários e Fila globais
status_download = {}
titulos_download = {}  # ID -> título do vídeo
arquivos_salvos = {}   # ID -> caminho do arquivo pronto na pasta Downloads
cancelados = set()     # IDs que o usuário pediu para cancelar
erros_download = {}    # ID -> mensagem explicando por que o download falhou
fila_downloads = queue.Queue()


def nome_de_arquivo_seguro(texto):
    """Tira do título os caracteres que o Windows não aceita em nome de arquivo."""
    return re.sub(r'[\\/:*?"<>|]', '', str(texto)).strip()[:150] or "download"


def formatar_tempo(segundos):
    """80 -> "1.20" | 3725 -> "1.02.05" (sem ":" porque o Windows não aceita em nomes)."""
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas}.{minutos:02d}.{segundos:02d}" if horas else f"{minutos}.{segundos:02d}"


def caminho_sem_sobrescrever(pasta, nome, extensao):
    """Se "nome.mp4" já existe, devolve "nome (2).mp4", "nome (3).mp4"..."""
    caminho = os.path.join(pasta, f"{nome}.{extensao}")
    numero = 2
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome} ({numero}).{extensao}")
        numero += 1
    return caminho


def apagar_temporarios(id_download):
    """Apaga os arquivos parciais deste download (.part, partes de vídeo/áudio...)."""
    for caminho in glob.glob(os.path.join(PASTA_DOWNLOADS, f"{glob.escape(id_download)}.*")):
        try:
            os.remove(caminho)
        except OSError:
            pass


def worker_fila():
    """Fica rodando em segundo plano processando os downloads da fila."""
    while True:
        # Pega o próximo item da fila (se não houver, fica esperando travado aqui consumindo 0% de CPU)
        tarefa = fila_downloads.get()
        try:
            processar(tarefa)
        finally:
            # Sinaliza para a fila que essa tarefa acabou
            fila_downloads.task_done()


def processar(tarefa):
    url = tarefa["url"]
    formato = tarefa["formato"]
    qualidade = tarefa["qualidade"]
    trecho = tarefa["trecho"]
    id_download = tarefa["id_download"]
    extensao = "mp3" if formato == "mp3" else "mp4"

    # Cancelado enquanto ainda esperava na fila
    if id_download in cancelados:
        status_download[id_download] = "Cancelado"
        return

    os.makedirs(PASTA_DOWNLOADS, exist_ok=True)
    caminho_temporario = os.path.join(PASTA_DOWNLOADS, f"{id_download}.{extensao}")

    def parar_se_cancelado():
        if id_download in cancelados:
            raise DownloadCancelled("Cancelado pelo usuário")

    def hook_progresso(d):
        parar_se_cancelado()
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                porcentagem = d.get('downloaded_bytes', 0) / total * 100
                status_download[id_download] = f"{min(porcentagem, 100):.1f}%"
        elif d['status'] == 'finished':
            status_download[id_download] = "Processando arquivo..."

    def hook_processamento(d):
        # Chamado antes de juntar vídeo/áudio ou converter para MP3
        parar_se_cancelado()

    # Salva com o ID no nome (e não o título) para sempre saber onde o arquivo está
    ydl_opts = {
        'outtmpl': os.path.join(PASTA_DOWNLOADS, f"{id_download}.%(ext)s"),
        'noplaylist': True,  # Link com &list=... baixa só o vídeo, não a playlist inteira
        'concurrent_fragment_downloads': 4,  # Baixa 4 partes ao mesmo tempo quando o vídeo vem fatiado
        'progress_hooks': [hook_progresso],
        'postprocessor_hooks': [hook_processamento],
        **opcoes_de_login(),  # cookies.txt, se existir (posts do Instagram que pedem login)
    }

    if formato == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # Conversão para MP3 ~2,5x mais rápida, sem diferença audível a 192 kbps
            'postprocessor_args': {'extractaudio': ['-compression_level', '7']},
        })
    else:
        ydl_opts.update({
            # Melhor vídeo + áudio, nunca a versão com marca d'água (TikTok)
            'format': 'bv*[format_note!*=?watermark]+ba/b[format_note!*=?watermark]',
            # "res" é a MENOR dimensão do vídeo: 720p vale tanto para 1280x720
            # (horizontal) quanto para 720x1280 (vertical: TikTok, Reels, Shorts).
            # Nunca passa da qualidade escolhida (máximo 1080p).
            # Depois prefere H.264 + AAC: arquivo menor que AV1 HDR, baixa mais
            # rápido e abre em qualquer player
            'format_sort': [f'res:{qualidade}', 'vcodec:h264', 'acodec:m4a'],
            'merge_output_format': 'mp4',
            # Garante .mp4 mesmo se vier um arquivo único em outro formato (ex.: .webm)
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4',
            }],
        })

    if trecho:
        # Baixa só o pedaço escolhido; corta no segundo exato (e não no quadro-chave mais próximo)
        ydl_opts['download_ranges'] = download_range_func(None, [trecho])
        ydl_opts['force_keyframes_at_cuts'] = True

    print(f"\n[FILA] Iniciando processamento do ID: {id_download}")

    try:
        # O YouTube às vezes falha do nada; tenta de novo antes de desistir
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                status_download[id_download] = "Baixando..."

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                parar_se_cancelado()

                if os.path.exists(caminho_temporario):
                    titulo = titulo_amigavel(info)
                    nome = nome_de_arquivo_seguro(titulo)
                    if trecho:
                        inicio, fim = trecho
                        fim_texto = formatar_tempo(fim) if fim != float("inf") else "fim"
                        nome += f" (trecho {formatar_tempo(inicio)} a {fim_texto})"

                    # Move para a pasta Downloads do usuário, com o título no nome
                    destino = caminho_sem_sobrescrever(PASTA_DESTINO, nome, extensao)
                    shutil.move(caminho_temporario, destino)

                    titulos_download[id_download] = titulo
                    arquivos_salvos[id_download] = destino
                    status_download[id_download] = "Pronto"
                    print(f"[FILA] Sucesso! Salvo em: {destino}")
                    break

                print(f"[FILA] Arquivo final não encontrado no ID {id_download} (tentativa {tentativa}/{TENTATIVAS})")

            except DownloadCancelled:
                raise
            except Exception as e:
                if id_download in cancelados:
                    raise DownloadCancelled("Cancelado pelo usuário")
                print(f"[FILA] Erro no ID {id_download} (tentativa {tentativa}/{TENTATIVAS}): {e}")
                erros_download[id_download] = mensagem_de_erro(e)

            if tentativa < TENTATIVAS:
                time.sleep(2)
        else:
            status_download[id_download] = "Erro"

    except DownloadCancelled:
        status_download[id_download] = "Cancelado"
        print(f"[FILA] Download {id_download} cancelado.")

    finally:
        apagar_temporarios(id_download)


# Inicializa as Threads "Worker" em background assim que o módulo é importado
for _ in range(DOWNLOADS_SIMULTANEOS):
    threading.Thread(target=worker_fila, daemon=True).start()


def adicionar_fila(url, formato, qualidade, id_download, trecho=None):
    """Adiciona um novo pedido na fila e define o status inicial.
    trecho: (inicio, fim) em segundos, para baixar só um pedaço do vídeo."""
    cancelados.discard(id_download)
    status_download[id_download] = "Na fila..."
    fila_downloads.put({
        "url": url,
        "formato": formato,
        "qualidade": qualidade,
        "trecho": trecho,
        "id_download": id_download,
    })


def cancelar_download(id_download):
    """Pede para cancelar. Devolve False se o download não existe ou já terminou."""
    status = status_download.get(id_download)
    if status is None or status in STATUS_FINAIS:
        return False

    cancelados.add(id_download)
    if status == "Na fila...":
        status_download[id_download] = "Cancelado"
    return True

