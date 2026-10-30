"""Atalho "Puxaí" no menu de aplicativos do Linux (o arquivo puxai.desktop).

Criado na primeira vez que o programa abre e corrigido se a pasta do programa
mudar de lugar. Se a pessoa apagar o atalho, ele não é criado de novo (como o
da Área de Trabalho no Windows, que o iniciar.ps1 cria).
"""
import os
import re
import sys
import time

from servicos.caminhos import EXECUTAVEL, PASTA_BASE, PASTA_PAINEL

PASTA_ATALHOS = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "applications")
ATALHO = os.path.join(PASTA_ATALHOS, "puxai.desktop")
MARCA = os.path.join(PASTA_BASE, ".atalho_criado")


def _argumento(texto):
    """Um argumento do Exec=, entre aspas, com \\ " ` e $ escapados (regras do formato .desktop)."""
    texto = re.sub(r'([\\"`$])', r"\\\1", texto)
    return '"' + texto.replace("\\", "\\\\") + '"'


def _conteudo():
    if EXECUTAVEL:
        comando = _argumento(sys.executable)
    else:
        # "sh iniciar.sh": a atualização pelo ZIP não guarda a permissão de executar
        comando = "sh " + _argumento(os.path.join(PASTA_BASE, "iniciar.sh"))
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Puxaí",
        "GenericName=Baixar vídeos e músicas",
        "Comment=Baixa vídeos do YouTube, TikTok, Instagram e de mais de mil sites em MP4 ou MP3",
        f"Exec={comando}",
        f"Icon={os.path.join(PASTA_PAINEL, 'icone.png')}",
        "Terminal=false",
        "Categories=AudioVideo;Network;",
        "Keywords=youtube;tiktok;instagram;mp3;mp4;download;baixar;",
        # O mesmo nome que a janela informa (janela.py): a barra de tarefas mostra a logo
        "StartupWMClass=puxai",
        "",
    ])


def criar():
    """Cria ou corrige o atalho (só no Linux). Se não der, o programa segue sem ele."""
    if not sys.platform.startswith("linux"):
        return
    try:
        if not os.path.exists(ATALHO) and os.path.exists(MARCA):
            return  # a pessoa apagou o atalho de propósito
        conteudo = _conteudo()
        try:
            with open(ATALHO, encoding="utf-8") as f:
                if f.read() == conteudo:
                    return
        except OSError:
            pass
        os.makedirs(PASTA_ATALHOS, exist_ok=True)
        with open(ATALHO, "w", encoding="utf-8") as f:
            f.write(conteudo)
        os.chmod(ATALHO, 0o755)
        if not os.path.exists(MARCA):
            with open(MARCA, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d"))
            print('[ATALHO] Atalho "Puxaí" criado no menu de aplicativos.')
    except OSError as e:
        print(f"[ATALHO] Não foi possível criar o atalho no menu de aplicativos: {e}")
