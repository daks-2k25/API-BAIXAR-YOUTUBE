import os
import sys

# Quando roda como .exe (PyInstaller), os arquivos do painel ficam numa pasta
# temporária (sys._MEIPASS) e a pasta de downloads deve ficar ao lado do .exe.
# Rodando com "python app.py", tudo fica na pasta do projeto.
EXECUTAVEL = getattr(sys, "frozen", False)

if EXECUTAVEL:
    PASTA_RECURSOS = sys._MEIPASS
    PASTA_BASE = os.path.dirname(sys.executable)
else:
    PASTA_RECURSOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PASTA_BASE = PASTA_RECURSOS

PASTA_PAINEL = os.path.join(PASTA_RECURSOS, "painel")
# Arquivos temporários enquanto o download acontece
PASTA_DOWNLOADS = os.path.join(PASTA_BASE, "downloads")


def _pasta_downloads_do_usuario():
    """A pasta Downloads do Windows, mesmo se o usuário a moveu (outro disco, OneDrive...)."""
    if sys.platform == "win32":
        try:
            import ctypes
            import uuid

            # FOLDERID_Downloads
            guid = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")

            class GUID(ctypes.Structure):
                _fields_ = [("data", ctypes.c_byte * 16)]

            caminho = ctypes.c_wchar_p()
            resultado = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(GUID((ctypes.c_byte * 16)(*guid.bytes_le))), 0, None, ctypes.byref(caminho)
            )
            if resultado == 0 and caminho.value:
                pasta = caminho.value
                ctypes.windll.ole32.CoTaskMemFree(caminho)
                return pasta
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


# Onde os vídeos e músicas prontos são salvos
PASTA_DESTINO = _pasta_downloads_do_usuario()

os.makedirs(PASTA_DOWNLOADS, exist_ok=True)

# Sem a janela preta (BaixarYouTube.exe ou pythonw), não existe onde mostrar as
# mensagens. Elas vão para o arquivo BaixarYouTube.log, útil se algo der errado.
if sys.stdout is None or sys.stderr is None:
    caminho_registro = os.path.join(PASTA_BASE, "BaixarYouTube.log")
    # Continua o arquivo existente; recomeça do zero quando passa de 1 MB
    modo = "w" if os.path.exists(caminho_registro) and os.path.getsize(caminho_registro) > 1_000_000 else "a"
    registro = open(caminho_registro, modo, encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or registro
    sys.stderr = sys.stderr or registro

# Se tiver um ffmpeg.exe ao lado do programa, usa ele (não precisa instalar no PC)
if os.path.exists(os.path.join(PASTA_BASE, "ffmpeg.exe")):
    os.environ["PATH"] = PASTA_BASE + os.pathsep + os.environ.get("PATH", "")
