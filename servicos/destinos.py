"""Onde salvar os arquivos prontos (⚙ Configurações > Salvar arquivos em).

Dois jeitos, guardados no .preferencias.json:
- "uma": uma pasta para tudo (padrão: a pasta Downloads do Windows)
- "separadas": uma pasta para vídeos (MP4), outra para músicas (MP3) e outra
  para fotos (convertidas e comprimidas)

Se a pasta escolhida sumir (ex.: pendrive ou HD externo desconectado), o
arquivo vai para Downloads em vez de se perder.
"""
import os
import shutil
import sys
import threading

from servicos import preferencias, sistema
from servicos.caminhos import PASTA_DESTINO

MODOS = ("uma", "separadas")
TIPOS = ("video", "musica", "foto")
CHAVES = {"tudo": "pasta_tudo", "video": "pasta_videos", "musica": "pasta_musicas", "foto": "pasta_fotos"}

# Uma janela de escolher pasta por vez
_trava_janela = threading.Lock()


def configuracao():
    """O que está escolhido; pasta não escolhida = Downloads."""
    modo = preferencias.obter("pastas_modo", "uma")
    dados = {"modo": modo if modo in MODOS else "uma", "padrao": PASTA_DESTINO}
    for nome, chave in CHAVES.items():
        dados[nome] = preferencias.obter(chave) or PASTA_DESTINO
    return dados


def pasta_para(tipo):
    """A pasta onde salvar um arquivo do tipo "video", "musica" ou "foto"."""
    dados = configuracao()
    pasta = dados["tudo"] if dados["modo"] == "uma" else dados[tipo]
    try:
        os.makedirs(pasta, exist_ok=True)
        return pasta
    except OSError as e:
        print(f"[PASTAS] Não foi possível usar {pasta} ({e}); salvando em Downloads.")
        return PASTA_DESTINO


def salvar(novos):
    """Salva o modo e/ou as pastas enviadas pelo painel. Pasta vazia ou None
    volta para Downloads. Erro de validação vira ValueError (com a mensagem)."""
    if "modo" in novos:
        if novos["modo"] not in MODOS:
            raise ValueError("Modo inválido. Use 'uma' ou 'separadas'.")
        preferencias.salvar("pastas_modo", novos["modo"])

    for nome, chave in CHAVES.items():
        if nome not in novos:
            continue
        pasta = (novos[nome] or "").strip()
        if not pasta:
            preferencias.salvar(chave, None)  # volta para Downloads
            continue
        if not os.path.isabs(pasta) or not os.path.isdir(pasta):
            raise ValueError(f"Pasta não encontrada: {pasta}")
        preferencias.salvar(chave, os.path.normpath(pasta))
    return configuracao()


def escolher_pasta(inicial=None):
    """Abre a janela do sistema para escolher uma pasta. Devolve o caminho ou
    None (se a pessoa cancelar). Na janela do aplicativo usa a do pywebview
    (fica presa à janela); no navegador, a do tkinter (que vem com o Python)
    ou, no Linux, a do zenity (GNOME) ou do kdialog (KDE), se houver."""
    inicial = inicial if inicial and os.path.isdir(inicial) else PASTA_DESTINO
    with _trava_janela:
        from servicos import programa
        if programa.na_janela():
            import webview
            tipo = webview.FileDialog.FOLDER if hasattr(webview, "FileDialog") else webview.FOLDER_DIALOG
            escolhida = programa.janela.create_file_dialog(tipo, directory=inicial)
            pasta = escolhida[0] if escolhida else None
        elif sys.platform.startswith("linux") and _programa_de_escolher_pasta():
            pasta = _escolher_no_linux(inicial)
        else:
            pasta = _escolher_com_tkinter(inicial)
    return os.path.normpath(pasta) if pasta else None


def _programa_de_escolher_pasta():
    """O zenity ou o kdialog (o da área de trabalho em uso primeiro), ou None."""
    kde = "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    for nome in (("kdialog", "zenity") if kde else ("zenity", "kdialog")):
        if shutil.which(nome):
            return nome
    return None


def _escolher_no_linux(inicial):
    titulo = "Puxaí: escolha a pasta para salvar"
    if _programa_de_escolher_pasta() == "kdialog":
        comando = ["kdialog", "--title", titulo, "--getexistingdirectory", inicial]
    else:
        comando = ["zenity", "--file-selection", "--directory", f"--title={titulo}",
                   f"--filename={os.path.join(inicial, '')}"]
    resultado = sistema.rodar(comando, capture_output=True, text=True)
    # Código 1 = a pessoa cancelou
    return resultado.stdout.strip() if resultado.returncode == 0 else None


def _escolher_com_tkinter(inicial):
    import tkinter
    from tkinter import filedialog

    raiz = tkinter.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)  # aparece na frente do navegador
    try:
        return filedialog.askdirectory(parent=raiz, initialdir=inicial, mustexist=True,
                                       title="Puxaí: escolha a pasta para salvar")
    finally:
        raiz.destroy()
