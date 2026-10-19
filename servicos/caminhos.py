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
PASTA_DOWNLOADS = os.path.join(PASTA_BASE, "downloads")

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
