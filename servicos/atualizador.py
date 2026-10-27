"""Mantém o yt-dlp atualizado dentro do programa gerado (Puxai.exe).

O YouTube muda com frequência e versões antigas do yt-dlp param de funcionar.
Rodando com Python (iniciar.bat), quem atualiza é o pip. Dentro do .exe, o yt-dlp
vem congelado; por isso, uma vez por dia este módulo procura uma versão nova no
PyPI, baixa e guarda em atualizacoes/. Na próxima abertura do programa, essa
versão é usada no lugar da que veio empacotada.

Precisa ser importado ANTES de qualquer "import yt_dlp".
"""
import glob
import hashlib
import json
import os
import sys
import threading
import time
import urllib.request

from servicos.caminhos import EXECUTAVEL, PASTA_BASE

PASTA_ATUALIZACOES = os.path.join(PASTA_BASE, "atualizacoes")
MARCA_VERIFICACAO = os.path.join(PASTA_ATUALIZACOES, "ultima_verificacao.txt")
URL_PYPI = "https://pypi.org/pypi/yt-dlp/json"


def _versao_como_tupla(versao):
    """"2026.08.19" -> (2026, 8, 19), para comparar versões."""
    return tuple(int(parte) for parte in str(versao).split(".") if parte.isdigit())


def _versao_do_arquivo(caminho):
    """".../yt_dlp-2026.8.19.whl" -> (2026, 8, 19)"""
    nome = os.path.basename(caminho)
    return _versao_como_tupla(nome[len("yt_dlp-"):-len(".whl")])


def usar_versao_atualizada():
    """Se já existe um yt-dlp mais novo baixado, faz o Python usá-lo."""
    if not EXECUTAVEL:
        return

    # Cada versão fica num arquivo próprio (yt_dlp-2026.8.19.whl), porque o
    # Windows não deixa substituir o arquivo que o programa está usando.
    # Aqui ainda nenhum está em uso: fica só o mais novo e os outros são apagados.
    baixados = sorted(glob.glob(os.path.join(PASTA_ATUALIZACOES, "yt_dlp-*.whl")), key=_versao_do_arquivo)
    for antigo in baixados[:-1]:
        try:
            os.remove(antigo)
        except OSError:
            pass
    if not baixados:
        return
    arquivo = baixados[-1]

    # O Python procura módulos na ordem do sys.path: o arquivo baixado vem antes
    # do yt-dlp empacotado no .exe
    sys.path.insert(0, arquivo)
    try:
        import yt_dlp  # noqa: F401
        print(f"[ATUALIZADOR] Usando yt-dlp atualizado: {yt_dlp.version.__version__}")
    except Exception as e:
        # Arquivo corrompido ou incompatível: volta para o yt-dlp empacotado
        print(f"[ATUALIZADOR] yt-dlp baixado não carregou ({e}); usando o empacotado.")
        sys.path.remove(arquivo)
        for nome in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
            del sys.modules[nome]
        try:
            os.remove(arquivo)
        except OSError:
            pass


def _ja_verificou_hoje():
    try:
        with open(MARCA_VERIFICACAO, encoding="utf-8") as f:
            return f.read().strip() == time.strftime("%Y-%m-%d")
    except OSError:
        return False


def _baixar_versao_nova():
    import yt_dlp

    versao_atual = yt_dlp.version.__version__
    with urllib.request.urlopen(URL_PYPI, timeout=15) as resposta:
        dados = json.load(resposta)

    versao_nova = dados["info"]["version"]
    if _versao_como_tupla(versao_nova) <= _versao_como_tupla(versao_atual):
        print(f"[ATUALIZADOR] yt-dlp já está na versão mais nova ({versao_atual}).")
        return

    wheel = next(u for u in dados["urls"] if u["packagetype"] == "bdist_wheel")
    print(f"[ATUALIZADOR] Baixando yt-dlp {versao_nova} (atual: {versao_atual})...")
    with urllib.request.urlopen(wheel["url"], timeout=60) as resposta:
        conteudo = resposta.read()

    # Confere que o arquivo chegou inteiro e é o publicado no PyPI
    if hashlib.sha256(conteudo).hexdigest() != wheel["digests"]["sha256"]:
        raise ValueError("o arquivo baixado não confere com o PyPI (SHA-256 diferente)")

    destino = os.path.join(PASTA_ATUALIZACOES, f"yt_dlp-{versao_nova}.whl")
    temporario = destino + ".baixando"
    with open(temporario, "wb") as f:
        f.write(conteudo)
    os.replace(temporario, destino)
    print(f"[ATUALIZADOR] yt-dlp {versao_nova} pronto; será usado na próxima vez que o programa abrir.")


def _verificar_em_segundo_plano():
    try:
        os.makedirs(PASTA_ATUALIZACOES, exist_ok=True)
        _baixar_versao_nova()
        with open(MARCA_VERIFICACAO, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d"))
    except Exception as e:
        # Sem internet, PyPI fora do ar etc.: tenta de novo na próxima abertura
        print(f"[ATUALIZADOR] Não foi possível verificar atualizações: {e}")


def verificar_atualizacao():
    """Procura uma versão nova do yt-dlp (no máximo uma vez por dia), sem travar o programa."""
    if EXECUTAVEL and not _ja_verificou_hoje():
        threading.Thread(target=_verificar_em_segundo_plano, daemon=True).start()
