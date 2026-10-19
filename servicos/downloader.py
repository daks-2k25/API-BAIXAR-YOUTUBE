import yt_dlp
import os
import queue
import threading
import time
from servicos.caminhos import PASTA_DOWNLOADS
from servicos.limpeza import registrar_arquivo

# Quantos downloads rodam ao mesmo tempo (os outros esperam na fila)
DOWNLOADS_SIMULTANEOS = 3

# Quantas vezes tenta baixar antes de marcar "Erro"
TENTATIVAS = 2

# Dicionários e Fila globais
status_download = {}
titulos_download = {}  # ID -> título do vídeo (usado no nome do arquivo baixado)
fila_downloads = queue.Queue()

def worker_fila():
    """Fica rodando em segundo plano processando os downloads da fila."""
    while True:
        # Pega o próximo item da fila (se não houver, fica esperando travado aqui consumindo 0% de CPU)
        tarefa = fila_downloads.get()
        url = tarefa["url"]
        formato = tarefa["formato"]
        qualidade = tarefa["qualidade"]
        id_download = tarefa["id_download"]
        caminho_final = tarefa["caminho_final"]

        pasta_saida = PASTA_DOWNLOADS
        os.makedirs(pasta_saida, exist_ok=True)

        def hook_progresso(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                baixado = d.get('downloaded_bytes', 0)
                if total > 0:
                    porcentagem = (baixado / total) * 100
                    status_download[id_download] = f"{porcentagem:.1f}%"
            elif d['status'] == 'finished':
                status_download[id_download] = "Processando arquivo..."

        # Salva com o ID no nome (e não o título) para sempre saber onde o arquivo está
        modelo_nome = os.path.join(pasta_saida, f"{id_download}.%(ext)s")

        if formato == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': modelo_nome,
                'noplaylist': True,  # Link com &list=... baixa só o vídeo, não a playlist inteira
                'concurrent_fragment_downloads': 4,  # Baixa 4 partes ao mesmo tempo quando o vídeo vem fatiado
                'progress_hooks': [hook_progresso],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                # Conversão para MP3 ~2,5x mais rápida, sem diferença audível a 192 kbps
                'postprocessor_args': {'extractaudio': ['-compression_level', '7']},
            }
        else:
            # Nunca passa da qualidade escolhida (máximo 1080p)
            ydl_opts = {
                'format': f'bestvideo[height<={qualidade}]+bestaudio/best[height<={qualidade}]',
                # Prefere H.264 + AAC: arquivo menor que AV1 HDR, baixa mais rápido
                # e abre em qualquer player
                'format_sort': [f'res:{qualidade}', 'vcodec:h264', 'acodec:m4a'],
                'outtmpl': modelo_nome,
                'noplaylist': True,  # Link com &list=... baixa só o vídeo, não a playlist inteira
                'concurrent_fragment_downloads': 4,  # Baixa 4 partes ao mesmo tempo quando o vídeo vem fatiado
                'progress_hooks': [hook_progresso],
                'merge_output_format': 'mp4',
                # Garante .mp4 mesmo se vier um arquivo único em outro formato (ex.: .webm)
                'postprocessors': [{
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': 'mp4',
                }],
            }

        print(f"\n[FILA] Iniciando processamento do ID: {id_download}")

        # O YouTube às vezes falha do nada; tenta de novo antes de desistir
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                status_download[id_download] = "Baixando..."

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                # O yt-dlp já salva com o ID no nome; com MP3/merge a extensão final é a esperada
                if os.path.exists(caminho_final):
                    titulos_download[id_download] = info.get("title") or id_download
                    status_download[id_download] = "Pronto"
                    # Se ninguém baixar, o arquivo é apagado depois de um tempo
                    registrar_arquivo(caminho_final, lambda id_download=id_download: esquecer_download(id_download))
                    print(f"[FILA] Sucesso! Salvo em: {caminho_final}")
                    break

                print(f"[FILA] Arquivo final não encontrado no ID {id_download} (tentativa {tentativa}/{TENTATIVAS})")

            except Exception as e:
                print(f"[FILA] Erro no ID {id_download} (tentativa {tentativa}/{TENTATIVAS}): {e}")

            if tentativa < TENTATIVAS:
                time.sleep(2)
        else:
            status_download[id_download] = "Erro"

        # Sinaliza para a fila que essa tarefa acabou
        fila_downloads.task_done()

# Inicializa as Threads "Worker" em background assim que o módulo é importado
for _ in range(DOWNLOADS_SIMULTANEOS):
    threading.Thread(target=worker_fila, daemon=True).start()

def adicionar_fila(url, formato, qualidade, id_download, caminho_final):
    """Adiciona um novo pedido na fila e define o status inicial."""
    status_download[id_download] = "Na fila..."
    fila_downloads.put({
        "url": url,
        "formato": formato,
        "qualidade": qualidade,
        "id_download": id_download,
        "caminho_final": caminho_final
    })

def esquecer_download(id_download):
    """Remove o status e o título de um download que já foi entregue ou expirou."""
    status_download.pop(id_download, None)
    titulos_download.pop(id_download, None)