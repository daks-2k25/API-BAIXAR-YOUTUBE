"""O que muda entre o Windows e o Linux: abrir um arquivo no programa padrão,
mostrar o arquivo na pasta, abrir o navegador e chamar programas do sistema.

No Windows, usa o Explorador. No Linux, o xdg-open (que abre com o programa
escolhido no sistema, em qualquer área de trabalho: GNOME, KDE, XFCE...) e,
para "mostrar na pasta", o pedido padrão de D-Bus que os gerenciadores de
arquivos entendem (Arquivos/Nautilus, Dolphin, Nemo, Thunar...).
"""
import os
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from servicos.caminhos import EXECUTAVEL

WINDOWS = sys.platform == "win32"
MAC = sys.platform == "darwin"


def ambiente():
    """As variáveis de ambiente para abrir um programa do sistema.

    No programa gerado para Linux, o PyInstaller troca o LD_LIBRARY_PATH para
    achar as bibliotecas que vêm junto (o Qt precisa delas). Os programas do
    sistema (navegador, xdg-open, zenity...) precisam do original, senão podem
    nem abrir.
    """
    variaveis = dict(os.environ)
    if EXECUTAVEL and not WINDOWS:
        original = variaveis.pop("LD_LIBRARY_PATH_ORIG", None)
        if original:
            variaveis["LD_LIBRARY_PATH"] = original
        else:
            variaveis.pop("LD_LIBRARY_PATH", None)
    return variaveis


def rodar(comando, **opcoes):
    """subprocess.run com o ambiente do sistema (veja ambiente())."""
    return subprocess.run(comando, env=ambiente(), **opcoes)


def _soltar(comando):
    """Abre outro programa sem esperar por ele (e sem prender este ao terminal)."""
    subprocess.Popen(comando, env=ambiente(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def abrir(caminho):
    """Abre um arquivo (no player, visualizador de fotos...) ou uma pasta."""
    if WINDOWS:
        os.startfile(caminho)
    elif MAC:
        _soltar(["open", caminho])
    else:
        _soltar(["xdg-open", caminho])


def abrir_no_navegador(endereco):
    if not EXECUTAVEL or WINDOWS or MAC:
        webbrowser.open(endereco)
        return
    # Programa gerado para Linux: o navegador da variável BROWSER, se houver, ou o
    # padrão do sistema (xdg-open), sempre com o ambiente do sistema
    navegador = os.environ.get("BROWSER", "").split(os.pathsep)[0]
    if not navegador:
        _soltar(["xdg-open", endereco])
    elif "%s" in navegador:
        _soltar([parte.replace("%s", endereco) for parte in shlex.split(navegador)])
    else:
        _soltar([*shlex.split(navegador), endereco])


def mostrar_na_pasta(caminho):
    """Abre a pasta do arquivo com ele selecionado."""
    if WINDOWS:
        subprocess.Popen(f'explorer /select,"{caminho}"')
    elif MAC:
        _soltar(["open", "-R", caminho])
    elif not _mostrar_pelo_dbus(caminho):
        # Sem D-Bus (ou gerenciador que não entende): abre a pasta, sem selecionar
        abrir(os.path.dirname(caminho))


def _mostrar_pelo_dbus(caminho):
    """org.freedesktop.FileManager1.ShowItems: abre a pasta já com o arquivo selecionado."""
    if not shutil.which("dbus-send"):
        return False
    try:
        resultado = rodar(
            ["dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.FileManager1",
             "--type=method_call", "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1.ShowItems",
             f"array:string:{Path(caminho).as_uri()}", "string:"],
            capture_output=True, timeout=5,
        )
        return resultado.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
