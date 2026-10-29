"""Link de vídeo copiado (o painel oferece "Colar" quando você copia um link).

Lê o texto da área de transferência do Windows direto (o programa roda no
mesmo computador), em vez de pedir ao navegador, que perguntaria permissão
toda vez. Só devolve algo se o texto copiado for um link de um site que o
yt-dlp sabe baixar; qualquer outro texto copiado (senhas, mensagens...) não
sai daqui nem fica guardado.
"""
import ctypes
import re
import sys
import time

from servicos.sites import nome_amigavel

CF_UNICODETEXT = 13
LINK = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TAMANHO_MAXIMO = 4000  # texto maior que isso não é "um link copiado"

_extratores = None
_cache = {}


def ler_texto():
    """O texto copiado agora (ou None: nada copiado, não é texto ou não deu para ler)."""
    if sys.platform != "win32":
        return None
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]

    # Outro programa pode estar usando a área de transferência neste instante
    for _ in range(5):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return None
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        dados = user32.GetClipboardData(CF_UNICODETEXT)
        if not dados:
            return None
        if kernel32.GlobalSize(dados) > TAMANHO_MAXIMO * 2:  # 2 bytes por letra
            return None
        ponteiro = kernel32.GlobalLock(dados)
        if not ponteiro:
            return None
        try:
            return ctypes.wstring_at(ponteiro)
        finally:
            kernel32.GlobalUnlock(dados)
    finally:
        user32.CloseClipboard()


def _site_do_link(url):
    """Nome do site se o yt-dlp sabe baixar desse link; None se não sabe."""
    global _extratores
    if url in _cache:
        return _cache[url]
    if _extratores is None:
        from yt_dlp.extractor import gen_extractor_classes
        # "Generic" aceita qualquer link: não diz nada sobre ser um site de vídeo
        _extratores = [e for e in gen_extractor_classes() if e.ie_key() != "Generic"]
    extrator = next((e for e in _extratores if e.suitable(url)), None)
    site = nome_amigavel(extrator.ie_key(), extrator.IE_NAME) if extrator else None
    if len(_cache) > 200:
        _cache.clear()
    _cache[url] = site
    return site


def link_de_video(texto):
    """{"url", "site"} do primeiro link de vídeo no texto, ou None."""
    if not texto or len(texto) > TAMANHO_MAXIMO:
        return None
    achado = LINK.search(texto)
    if not achado:
        return None
    url = achado.group(0).rstrip("),.;")
    site = _site_do_link(url)
    return {"url": url, "site": site} if site else None


def link_copiado():
    """O link de vídeo que está copiado agora, ou None."""
    return link_de_video(ler_texto())
