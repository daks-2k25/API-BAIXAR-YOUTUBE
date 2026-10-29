import glob
import os
import queue
import re
import shutil
import threading
import time

import yt_dlp
from yt_dlp.postprocessor import PostProcessor
from yt_dlp.utils import DownloadCancelled, download_range_func

from servicos import destinos, historico
from servicos.caminhos import PASTA_DOWNLOADS
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
extras_download = {}   # ID -> dados a mais para o painel (ex.: tamanho antes/depois de comprimir um vídeo)
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


# "(Official Video)", "[Lyrics]", "(4K Remaster)", "(Clipe Oficial)"...: sobra do título
# do vídeo que não faz parte do nome da música. "(feat. X)", "(Ao Vivo)" e "(Remix)" ficam.
SOBRAS_DO_TITULO = re.compile(
    r"\s*[(\[][^)\]]*\b(official|oficial|video|vídeo|videoclipe|clipe|clip|audio|áudio|"
    r"lyrics?|letra|visualizer|remaster(ed)?|hd|hq|4k|mv)\b[^)\]]*[)\]]",
    re.IGNORECASE,
)


def titulo_da_musica(titulo, artista):
    """"Rick Astley - Never Gonna Give You Up (Official Video)" -> "Never Gonna Give You Up"."""
    limpo = SOBRAS_DO_TITULO.sub("", titulo).strip()
    if artista:
        for separador in (" - ", " – ", " — ", " | "):
            if limpo.lower().startswith(artista.lower() + separador):
                limpo = limpo[len(artista) + len(separador):].strip()
                break
    return limpo or titulo


class DadosDoMp3(PostProcessor):
    """Ajusta o que vai gravado no MP3 (o que aparece no player e no celular).

    O yt-dlp usa os campos "meta_*" no lugar dos que ele escolheria sozinho:
    - título: o nome da música; sem ele, o título do vídeo sem o artista na
      frente nem "(Official Video)" etc. (no TikTok/Instagram, o título amigável,
      porque o "título" original é a legenda inteira do post)
    - artista: os artistas da música oficial ou o canal, sem o " - Topic"
    - gênero: só um gênero de verdade (o padrão seriam as tags do vídeo)
    - descrição: fica de fora (a do YouTube é enorme e cheia de links);
      no comentário vai o link do vídeo
    """

    def run(self, info):
        artistas = info.get('artists') or ([info['artist']] if info.get('artist') else [])
        canal = (info.get('channel') or info.get('uploader') or '').removesuffix(' - Topic')
        ano = info.get('release_year') or (info.get('upload_date') or '')[:4]

        artista = ', '.join(artistas) or canal
        info['meta_title'] = info.get('track') or titulo_da_musica(titulo_amigavel(info), artistas[0] if artistas else canal)
        info['meta_artist'] = artista
        info['meta_date'] = str(ano or '')
        info['meta_genre'] = info.get('genre') or ''
        info['meta_description'] = ''
        info['meta_synopsis'] = ''
        info['meta_comment'] = info.get('webpage_url') or ''
        return [], info


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
            # Baixa a miniatura do vídeo para virar a capa do MP3
            'writethumbnail': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                # Título, artista, álbum e ano (ajustados por DadosDoMp3)
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                # Capa: a miniatura vira JPG quadrado (corte no centro)
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg', 'when': 'before_dl'},
                {'key': 'EmbedThumbnail'},
            ],
            'postprocessor_args': {
                # Conversão para MP3 ~2,5x mais rápida, sem diferença audível a 192 kbps
                'extractaudio': ['-compression_level', '7'],
                # Capa quadrada, como a de um álbum. Na música oficial do YouTube a
                # miniatura é a capa do álbum com faixas dos lados: o corte deixa só a capa
                'thumbnailsconvertor+ffmpeg_o': [
                    '-c:v', 'mjpeg', '-q:v', '3',
                    '-vf', "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'",
                ],
            },
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
                    if formato == "mp3":
                        ydl.add_post_processor(DadosDoMp3(), when='pre_process')
                    info = ydl.extract_info(url, download=True)
                parar_se_cancelado()

                if os.path.exists(caminho_temporario):
                    titulo = titulo_amigavel(info)
                    nome = nome_de_arquivo_seguro(titulo)
                    if trecho:
                        inicio, fim = trecho
                        fim_texto = formatar_tempo(fim) if fim != float("inf") else "fim"
                        nome += f" (trecho {formatar_tempo(inicio)} a {fim_texto})"

                    # Playlist: pasta com o nome dela e o número na frente ("03 - Título"),
                    # para os arquivos ficarem na ordem da playlist
                    # Pasta escolhida em Configurações (Downloads, se nenhuma)
                    base = destinos.pasta_para("musica" if extensao == "mp3" else "video")
                    pasta = base
                    if tarefa.get("pasta"):
                        pasta = os.path.join(base, tarefa["pasta"])
                        os.makedirs(pasta, exist_ok=True)
                    if tarefa.get("numero"):
                        nome = f"{tarefa['numero']} - {nome}"

                    # Move para a pasta de destino, com o título no nome
                    destino = caminho_sem_sobrescrever(pasta, nome, extensao)
                    shutil.move(caminho_temporario, destino)

                    titulos_download[id_download] = titulo
                    arquivos_salvos[id_download] = destino
                    historico.registrar(id_download, destino, titulo, url)
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


def adicionar_fila(url, formato, qualidade, id_download, trecho=None, pasta=None, numero=None):
    """Adiciona um novo pedido na fila e define o status inicial.
    trecho: (inicio, fim) em segundos, para baixar só um pedaço do vídeo.
    pasta e numero (playlists): subpasta dentro de Downloads e o número que vai
    na frente do nome, já formatado (ex.: "03")."""
    cancelados.discard(id_download)
    status_download[id_download] = "Na fila..."
    fila_downloads.put({
        "url": url,
        "formato": formato,
        "qualidade": qualidade,
        "trecho": trecho,
        "id_download": id_download,
        "pasta": pasta,
        "numero": numero,
    })


def quantos_em_andamento():
    """Quantos downloads (e compressões de vídeo) ainda estão na fila ou acontecendo."""
    return sum(st not in STATUS_FINAIS for st in list(status_download.values()))


def downloads_em_andamento():
    """True se algum download ainda está na fila ou acontecendo."""
    return quantos_em_andamento() > 0


def cancelar_download(id_download):
    """Pede para cancelar. Devolve False se o download não existe ou já terminou."""
    status = status_download.get(id_download)
    if status is None or status in STATUS_FINAIS:
        return False

    cancelados.add(id_download)
    if status == "Na fila...":
        status_download[id_download] = "Cancelado"
    return True

