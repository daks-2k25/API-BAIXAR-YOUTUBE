"""Janela própria do programa (pywebview), com a logo na barra de tarefas."""
import os
import sys

from servicos import programa
from servicos.caminhos import PASTA_PAINEL
from servicos.downloader import downloads_em_andamento

TITULO = "Baixar YouTube"


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
    import webview

    if sys.platform == "win32":
        import ctypes
        # Faz a barra de tarefas tratar o programa como um aplicativo próprio (e não como "Python")
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BaixarYouTube.Painel")

    janela = programa.janela = webview.create_window(
        TITULO, programa.ENDERECO_PAINEL,
        width=760, height=900, min_size=(440, 620), background_color="#fff4ea",
    )

    def ao_mostrar():
        # Coloca a logo do programa na janela e na barra de tarefas
        try:
            colocar_icone_na_janela(TITULO, os.path.join(PASTA_PAINEL, "icone.ico"))
        except Exception as e:
            print(f"[JANELA] Não foi possível colocar o ícone: {e}")

    def ao_fechar():
        # Trocando para o navegador: o programa continua, então não precisa perguntar
        if programa.trocando_para_navegador:
            return True
        # Avisa antes de fechar se ainda há download acontecendo
        if downloads_em_andamento():
            return janela.create_confirmation_dialog(
                "Fechar o Baixar YouTube?",
                "Ainda há downloads em andamento. Se fechar agora, eles serão interrompidos.",
            )
        return True

    janela.events.shown += ao_mostrar
    janela.events.closing += ao_fechar
    webview.start(gui="edgechromium")


def trazer_para_frente():
    """Clicou no atalho com o programa já aberto: traz a janela para a frente."""
    janela = programa.janela
    janela.restore()
    janela.show()
    janela.on_top = True   # liga e desliga o "sempre no topo" para a
    janela.on_top = False  # janela passar na frente das outras
