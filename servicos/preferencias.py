"""Preferências da pessoa, guardadas em .preferencias.json ao lado do programa.

Ex.: { "modo_abertura": "navegador", "atualizacao_adiada": "2.1.0" }
O arquivo fica fora do Git e o botão de atualizar não mexe nele.
"""
import json
import os
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
