import yt_dlp
import os
import queue
import threading
from servicos.limpeza import registrar_arquivo

#test
# Dicionários e Fila globais
status_download = {}
fila_downloads = queue.Queue()

def worker_fila():
    """Fica rodando em segundo plano processando um download por vez."""
    while True:
        # Pega o próximo item da fila (se não houver, fica esperando travado aqui consumindo 0% de CPU)
        tarefa = fila_downloads.get()
        url = tarefa["url"]
        formato = tarefa["formato"]
        qualidade = tarefa["qualidade"]
        id_download = tarefa["id_download"]
        caminho_final = tarefa["caminho_final"]

        pasta_saida = "downloads"
        if not os.path.exists(pasta_saida):
            os.makedirs(pasta_saida)

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
                'progress_hooks': [hook_progresso],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            # Nunca passa da qualidade escolhida (máximo 1080p)
            ydl_opts = {
                'format': (
                    f'bestvideo[height<={qualidade}][ext=mp4]+bestaudio[ext=m4a]'
                    f'/bestvideo[height<={qualidade}]+bestaudio'
                    f'/best[height<={qualidade}]'
                ),
                'outtmpl': modelo_nome,
                'progress_hooks': [hook_progresso],
                'merge_output_format': 'mp4',
                # Garante .mp4 mesmo se vier um arquivo único em outro formato (ex.: .webm)
                'postprocessors': [{
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': 'mp4',
                }],
            }

        try:
            status_download[id_download] = "Baixando..."
            print(f"\n[FILA] Iniciando processamento do ID: {id_download}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            # O yt-dlp já salva com o ID no nome; com MP3/merge a extensão final é a esperada
            if os.path.exists(caminho_final):
                status_download[id_download] = "Pronto"
                # Se ninguém baixar, o arquivo é apagado depois de um tempo
                registrar_arquivo(caminho_final, lambda id_download=id_download: status_download.pop(id_download, None))
                print(f"[FILA] Sucesso! Salvo em: {caminho_final}")
            else:
                status_download[id_download] = "Erro"

        except Exception as e:
            print(f"[FILA] Erro no ID {id_download}: {e}")
            status_download[id_download] = "Erro"
        
        # Sinaliza para a fila que essa tarefa acabou
        fila_downloads.task_done()

# Inicializa a Thread "Worker" em background assim que o módulo é importado
t = threading.Thread(target=worker_fila, daemon=True)
t.start()

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