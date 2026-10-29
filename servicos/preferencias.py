"""Preferências da pessoa, guardadas em .preferencias.json ao lado do programa.

Ex.: { "modo_abertura": "navegador", "tema": "escuro", "atualizacao_adiada": "2.1.0" }
O arquivo fica fora do Git e o botão de atualizar não mexe nele.
"""
import json
import os
import sys
import threading

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


# Tema do painel: "automatico" segue o Windows (claro ou escuro)
TEMAS = ("automatico", "claro", "escuro")


def tema():
    escolhido = obter("tema", "automatico")
    return escolhido if escolhido in TEMAS else "automatico"


def windows_no_modo_escuro():
    """True se os aplicativos do Windows estão no modo escuro (Configurações > Cores)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as chave:
            return winreg.QueryValueEx(chave, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def tema_em_uso():
    """ "claro" ou "escuro": o escolhido, ou o do Windows quando é automático."""
    escolhido = tema()
    if escolhido == "automatico":
        return "escuro" if windows_no_modo_escuro() else "claro"
    return escolhido
