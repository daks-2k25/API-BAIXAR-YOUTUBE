import yt_dlp
import os
import queue
import threading

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

        if formato == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{pasta_saida}/%(title)s.%(ext)s',
                'progress_hooks': [hook_progresso],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': f'{pasta_saida}/%(title)s.%(ext)s',
                'progress_hooks': [hook_progresso],
                'merge_output_format': 'mp4'
            }

        try:
            status_download[id_download] = "Baixando..."
            print(f"\n[FILA] Iniciando processamento do ID: {id_download}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=True)
                caminho_arquivo = ydl.prepare_filename(info)

                if formato == "mp3":
                    caminho_arquivo = caminho_arquivo.rsplit('.', 1)[0] + '.mp3'

                # Move/Renomeia o arquivo gerado para o caminho exato que o app.py espera
                if os.path.exists(caminho_arquivo):
                    os.rename(caminho_arquivo, caminho_final)
                    status_download[id_download] = "Pronto"
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

def adicionar_fila(url, formato, id_download, caminho_final):
    """Adiciona um novo pedido na fila e define o status inicial."""
    status_download[id_download] = "Na fila..."
    fila_downloads.put({
        "url": url,
        "formato": formato,
        "id_download": id_download,
        "caminho_final": caminho_final
    })