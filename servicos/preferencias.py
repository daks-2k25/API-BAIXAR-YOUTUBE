"""Preferências da pessoa, guardadas em .preferencias.json ao lado do programa.

Ex.: { "modo_abertura": "navegador", "tema": "escuro", "atualizacao_adiada": "2.1.0" }
O arquivo fica fora do Git e o botão de atualizar não mexe nele.
"""
import json
import os
import shutil
import subprocess
import sys
import threading

from servicos import sistema
from servicos.caminhos import PASTA_BASE

ARQUIVO = os.path.join(PASTA_BASE, ".preferencias.json")
_trava = threading.Lock()

# Como o programa abre: na janela própria (aplicativo) ou no navegador
MODOS_DE_ABERTURA = ("janela", "navegador")


def ler():
    try:
        with open(ARQUIVO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def obter(chave, padrao=None):
    return ler().get(chave, padrao)


def salvar(chave, valor):
    with _trava:
        preferencias = ler()
        preferencias[chave] = valor
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(preferencias, f, ensure_ascii=False, indent=2)


def modo_de_abertura():
    modo = obter("modo_abertura", "janela")
    return modo if modo in MODOS_DE_ABERTURA else "janela"


def detectar_link():
    """Avisar quando um link de vídeo for copiado (ligado, a não ser que a pessoa desligue)."""
    return obter("detectar_link", True) is not False


# Tema do painel: "automatico" segue o sistema (claro ou escuro)
TEMAS = ("automatico", "claro", "escuro")


def tema():
    escolhido = obter("tema", "automatico")
    return escolhido if escolhido in TEMAS else "automatico"


def sistema_no_modo_escuro():
    """True se o sistema está no modo escuro (no Windows: Configurações > Cores)."""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as chave:
                return winreg.QueryValueEx(chave, "AppsUseLightTheme")[0] == 0
        except OSError:
            return False
    if sys.platform.startswith("linux"):
        return _linux_no_modo_escuro()
    return False


def _linux_no_modo_escuro():
    # GNOME (e Cinnamon, Budgie...): Configurações > Aparência > Escuro
    if shutil.which("gsettings"):
        for chave in ("color-scheme", "gtk-theme"):  # gtk-theme: GNOME antigo (tema "Adwaita-dark", "Yaru-dark"...)
            try:
                valor = sistema.rodar(["gsettings", "get", "org.gnome.desktop.interface", chave],
                                      capture_output=True, text=True, timeout=2).stdout.lower()
            except (OSError, subprocess.TimeoutExpired):
                break
            if "dark" in valor:
                return True
            if chave == "color-scheme" and "light" in valor:
                return False
    # KDE: o esquema de cores (ex.: "BreezeDark")
    try:
        with open(os.path.expanduser("~/.config/kdeglobals"), encoding="utf-8") as f:
            return any(linha.startswith("ColorScheme=") and "dark" in linha.lower() for linha in f)
    except OSError:
        return False


def tema_em_uso():
    """ "claro" ou "escuro": o escolhido, ou o do sistema quando é automático."""
    escolhido = tema()
    if escolhido == "automatico":
        return "escuro" if sistema_no_modo_escuro() else "claro"
    return escolhido
