import threading

import yt_dlp

from servicos.sites import nome_do_site, opcoes_de_login, titulo_amigavel

# Guarda as últimas consultas: colar o mesmo link de novo responde na hora
LIMITE_CACHE = 100
cache_informacoes = {}
trava = threading.Lock()


def formatar_duracao(segundos):
    """165 -> "2:45" | 3725 -> "1:02:05\""""
    if not segundos:
        return None
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segundos:02d}"
    return f"{minutos}:{segundos:02d}"


def obter_informacoes(url):
    """Busca título, canal, duração e miniatura do vídeo, sem baixar nada."""
    with trava:
        if url in cache_informacoes:
            return cache_informacoes[url]

    opcoes = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,  # Vídeo dentro de playlist: pega só o vídeo
        'skip_download': True,
        **opcoes_de_login(),
    }
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=False)

    resultado = {
        "id": info.get("id"),
        "titulo": titulo_amigavel(info),
        "canal": info.get("channel") or info.get("uploader"),
        "site": nome_do_site(info),  # YouTube, TikTok ou Instagram
        "duracao": formatar_duracao(info.get("duration")),
        "miniatura": info.get("thumbnail"),
        # Só vídeos do YouTube podem ser assistidos dentro do painel
        "youtube": info.get("extractor_key") == "Youtube",
    }

    with trava:
        if len(cache_informacoes) >= LIMITE_CACHE:
            cache_informacoes.pop(next(iter(cache_informacoes)))
        cache_informacoes[url] = resultado
    return resultado
