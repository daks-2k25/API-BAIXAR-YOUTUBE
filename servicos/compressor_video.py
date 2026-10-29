"""Compressor de vídeos (aba "Comprimir vídeo"), feito com o FFmpeg.

O resultado é sempre MP4 (H.264 + AAC), que abre em qualquer celular, no
WhatsApp, no Discord e em qualquer player. Dois jeitos:

- Tamanho do arquivo (WhatsApp 16 MB, Discord 10 MB, E-mail 25 MB ou outro):
  calcula a taxa de bits que cabe no tamanho e comprime em duas passadas (a
  primeira estuda o vídeo, a segunda distribui os bits onde precisa). Se a
  resolução for grande demais para tão poucos bits, ela é reduzida sozinha,
  senão o vídeo viraria um borrão quadriculado.
- Qualidade (alta, equilibrada, máxima compressão): qualidade constante (CRF).

Nunca devolve um arquivo maior que o original. Comprime um vídeo por vez (o
FFmpeg já usa todos os núcleos do processador) e mostra o andamento em %.

Usa os mesmos dicionários de status dos downloads, então o painel acompanha
o andamento pela mesma consulta (/api/progresso) e o programa sabe que há um
trabalho em andamento antes de fechar ou atualizar.
"""
import glob
import json
import os
import queue
import shutil
import subprocess
import threading

from servicos import destinos, historico, programa
from servicos.caminhos import PASTA_DOWNLOADS
from servicos.downloader import (
    arquivos_salvos, caminho_sem_sobrescrever, erros_download, extras_download, nome_de_arquivo_seguro,
    status_download, titulos_download,
)

ENTRADAS = ("mp4", "mov", "mkv", "webm", "avi", "m4v", "3gp", "wmv", "flv", "mpg", "mpeg", "ts")

# Tamanhos prontos, em MB (MiB: 1 MB = 1024 × 1024 bytes, como contam o WhatsApp e o Discord)
TAMANHOS = {"whatsapp": 16, "discord": 10, "email": 25}
TAMANHO_MINIMO, TAMANHO_MAXIMO = 1, 4000

# Qualidade constante do x264: menor = melhor e maior
QUALIDADES = {"alta": 21, "equilibrada": 24, "forte": 28}

# Maior resolução (lado menor da imagem: "720" vale para 1280×720 e para 720×1280)
RESOLUCOES = {"original": None, "1080": 1080, "720": 720, "480": 480}
RESOLUCOES_AUTOMATICAS = (1080, 720, 540, 480, 360, 240)

# Bits por pixel mínimos para o vídeo não virar borrão (abaixo disso, reduz a resolução)
BITS_POR_PIXEL_MINIMO = 0.045
# Abaixo disso nem reduzindo dá para ficar assistível
TAXA_MINIMA_KBPS = 80
# Margem para o tamanho final não passar do alvo (a taxa de bits real varia um pouco)
MARGEM = 0.96
ECONOMIA_MINIMA = 0.02

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

fila = queue.Queue()
trabalhos = set()   # IDs de compressão de vídeo (para o cancelar saber que é daqui)
cancelados = set()
processos = {}      # ID -> FFmpeg rodando (para cancelar no meio)


class Cancelado(Exception):
    pass


class NaoCabe(Exception):
    """O vídeo é longo demais para caber no tamanho pedido."""


# ==========================================
# Informações do vídeo
# ==========================================

def analisar(caminho):
    """Duração, tamanho da imagem (já girada, como aparece na tela), quadros por segundo e se tem áudio."""
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", caminho],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=SEM_JANELA,
    )
    dados = json.loads(resultado.stdout or "{}")
    video = next((s for s in dados.get("streams", []) if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if not video or not float(dados.get("format", {}).get("duration") or 0):
        raise ValueError("Não encontrei um vídeo nesse arquivo.")

    largura, altura = int(video["width"]), int(video["height"])
    # Vídeo de celular gravado em pé vem "deitado" com um aviso de rotação
    rotacao = next((abs(int(d.get("rotation", 0))) for d in video.get("side_data_list", []) if "rotation" in d),
                   abs(int(video.get("tags", {}).get("rotate", 0) or 0)))
    if rotacao in (90, 270):
        largura, altura = altura, largura

    numerador, _, denominador = (video.get("avg_frame_rate") or video.get("r_frame_rate") or "30/1").partition("/")
    try:
        quadros = float(numerador) / float(denominador or 1)
    except (ValueError, ZeroDivisionError):
        quadros = 30.0
    return {
        "duracao": float(dados["format"]["duration"]),
        "largura": largura,
        "altura": altura,
        "quadros": quadros if 1 <= quadros <= 240 else 30.0,
        "audio": any(s.get("codec_type") == "audio" for s in dados.get("streams", [])),
    }


def tamanho_reduzido(largura, altura, lado_menor):
    """Novo tamanho com o lado menor = lado_menor (nunca aumenta), sempre em números pares."""
    menor = min(largura, altura)
    if lado_menor and lado_menor < menor:
        escala = lado_menor / menor
        largura, altura = largura * escala, altura * escala
    return int(round(largura / 2)) * 2, int(round(altura / 2)) * 2


# ==========================================
# Compressão
# ==========================================

def _rodar_ffmpeg(id_trabalho, argumentos, duracao, inicio_pct, fim_pct):
    """Roda o FFmpeg mostrando o andamento entre inicio_pct e fim_pct."""
    if id_trabalho in cancelados:
        raise Cancelado()
    processo = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-v", "error", "-nostats", "-progress", "pipe:1", "-y", *argumentos],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        creationflags=SEM_JANELA,
    )
    processos[id_trabalho] = processo
    try:
        for linha in processo.stdout:
            if linha.startswith("out_time_us=") and duracao:
                try:
                    feito = int(linha.split("=", 1)[1]) / 1_000_000 / duracao
                except ValueError:
                    continue
                pct = inicio_pct + (fim_pct - inicio_pct) * min(max(feito, 0), 1)
                status_download[id_trabalho] = f"{pct:.1f}%"
        erro = processo.stderr.read()
        processo.wait()
    finally:
        processos.pop(id_trabalho, None)
    if id_trabalho in cancelados:
        raise Cancelado()
    if processo.returncode != 0:
        raise RuntimeError(erro.strip()[-400:] or f"FFmpeg terminou com código {processo.returncode}")


def _comprimir(trabalho):
    id_trabalho = trabalho["id"]
    entrada = trabalho["entrada"]
    info = analisar(entrada)
    duracao = info["duracao"]
    saida = os.path.join(PASTA_DOWNLOADS, f"{id_trabalho}_comprimido.mp4")
    passadas = os.path.join(PASTA_DOWNLOADS, f"{id_trabalho}_passadas")
    limite = RESOLUCOES[trabalho["resolucao"]]

    audio_kbps = 128
    if trabalho["modo"] == "tamanho":
        alvo_bytes = trabalho["tamanho_mb"] * 1024 * 1024
        if os.path.getsize(entrada) <= alvo_bytes and not limite:
            return {"ja_otimizada": True}  # já cabe: não precisa mexer

        total_kbps = alvo_bytes * 8 * MARGEM / duracao / 1000
        if info["audio"]:
            # Pouco espaço: o áudio cede um pouco (64 kbps ainda é bom para voz)
            audio_kbps = 128 if total_kbps > 1000 else 96 if total_kbps > 400 else 64
        video_kbps = total_kbps - (audio_kbps if info["audio"] else 0)
        if video_kbps < TAXA_MINIMA_KBPS:
            raise NaoCabe()

        # Maior resolução (até o limite escolhido) que ainda fica nítida com essa taxa
        def fica_nitido(lado_menor):
            largura, altura = tamanho_reduzido(info["largura"], info["altura"], lado_menor)
            return video_kbps * 1000 / (largura * altura * info["quadros"]) >= BITS_POR_PIXEL_MINIMO

        lado_original = min(info["largura"], info["altura"])
        opcoes = [lado_original] + [r for r in RESOLUCOES_AUTOMATICAS if r < lado_original]
        lado = next((r for r in opcoes if (not limite or r <= limite) and fica_nitido(r)),
                    RESOLUCOES_AUTOMATICAS[-1])
    else:
        lado = limite

    largura, altura = tamanho_reduzido(info["largura"], info["altura"], lado)
    imagem = ["-vf", f"scale={largura}:{altura}:flags=lanczos", "-pix_fmt", "yuv420p"]
    som = ["-map", "0:a:0?", "-c:a", "aac", "-b:a", f"{audio_kbps}k"] if info["audio"] else ["-an"]
    final = ["-map_metadata", "0", "-movflags", "+faststart", saida]

    try:
        if trabalho["modo"] == "tamanho":
            # Duas passadas; se mesmo assim passar do tamanho (raro), tenta uma vez com menos bits
            for tentativa, fator in enumerate((1.0, 0.88)):
                taxa = f"{int(video_kbps * fator)}k"
                comum = ["-i", entrada, "-map", "0:v:0", *imagem, "-c:v", "libx264", "-preset", "medium",
                         "-b:v", taxa, "-passlogfile", passadas]
                _rodar_ffmpeg(id_trabalho, [*comum, "-pass", "1", "-an", "-f", "null", os.devnull], duracao, 0, 35)
                _rodar_ffmpeg(id_trabalho, [*comum, "-pass", "2", *som, *final], duracao, 35, 99)
                if os.path.getsize(saida) <= alvo_bytes or tentativa == 1:
                    break
                print(f"[VÍDEO] {id_trabalho}: passou do tamanho, tentando com menos bits")
        else:
            _rodar_ffmpeg(id_trabalho, ["-i", entrada, "-map", "0:v:0", *imagem, "-c:v", "libx264",
                                        "-preset", "medium", "-crf", str(QUALIDADES[trabalho["qualidade"]]),
                                        *som, *final], duracao, 0, 99)
    finally:
        for arquivo in glob.glob(glob.escape(passadas) + "*"):
            os.remove(arquivo)

    antes, depois = os.path.getsize(entrada), os.path.getsize(saida)
    reduziu_resolucao = (largura, altura) != tamanho_reduzido(info["largura"], info["altura"], None)
    if depois >= antes * (1 - ECONOMIA_MINIMA) and not reduziu_resolucao:
        os.remove(saida)
        return {"ja_otimizada": True}
    return {"caminho": saida, "largura": largura, "altura": altura, "ja_otimizada": False}


def processar(trabalho):
    id_trabalho = trabalho["id"]
    antes = os.path.getsize(trabalho["entrada"])
    extras_download[id_trabalho] = {"antes": antes}
    try:
        if id_trabalho in cancelados:  # cancelado enquanto esperava na fila
            raise Cancelado()
        status_download[id_trabalho] = "0.0%"
        resultado = _comprimir(trabalho)
        if resultado["ja_otimizada"]:
            extras_download[id_trabalho].update(depois=antes, ja_otimizada=True)
        else:
            nome = f"{trabalho['nome']} (comprimido)"
            pasta = destinos.pasta_para("video")
            destino = caminho_sem_sobrescrever(pasta, nome_de_arquivo_seguro(nome), "mp4")
            shutil.move(resultado["caminho"], destino)
            arquivos_salvos[id_trabalho] = destino
            historico.registrar(id_trabalho, destino, nome)
            extras_download[id_trabalho].update(
                depois=os.path.getsize(destino), largura=resultado["largura"], altura=resultado["altura"],
                ja_otimizada=False,
            )
        status_download[id_trabalho] = "Pronto"
    except Cancelado:
        status_download[id_trabalho] = "Cancelado"
    except NaoCabe:
        erros_download[id_trabalho] = (
            f"O vídeo é longo demais para caber em {trabalho['tamanho_mb']} MB com uma qualidade assistível. "
            "Escolha um tamanho maior."
        )
        status_download[id_trabalho] = "Erro"
    except Exception as e:
        print(f"[VÍDEO] Erro ao comprimir {trabalho['nome']}: {e}")
        erros_download[id_trabalho] = "Não foi possível comprimir. Verifique se o arquivo é um vídeo válido."
        status_download[id_trabalho] = "Erro"
    finally:
        cancelados.discard(id_trabalho)
        for arquivo in glob.glob(os.path.join(PASTA_DOWNLOADS, f"{glob.escape(id_trabalho)}_*")):
            try:
                os.remove(arquivo)
            except OSError:
                pass


def _trabalhar():
    while True:
        trabalho = fila.get()
        try:
            processar(trabalho)
        finally:
            fila.task_done()


threading.Thread(target=_trabalhar, daemon=True).start()


# ==========================================
# Usado pelas rotas
# ==========================================

def adicionar(id_trabalho, entrada, nome, modo, tamanho_mb=None, qualidade=None, resolucao="original"):
    """Põe um vídeo na fila. modo: "tamanho" (com tamanho_mb) ou "qualidade" (com qualidade)."""
    trabalhos.add(id_trabalho)
    titulos_download[id_trabalho] = nome
    status_download[id_trabalho] = "Na fila..."
    fila.put({"id": id_trabalho, "entrada": entrada, "nome": nome, "modo": modo, "tamanho_mb": tamanho_mb,
              "qualidade": qualidade, "resolucao": resolucao})


def parar_tudo():
    """Ao fechar o programa: para o FFmpeg que estiver rodando e apaga os arquivos
    temporários das compressões que não terminaram."""
    cancelados.update(processos)  # interrompido de propósito: não é erro
    for processo in list(processos.values()):
        processo.kill()
        try:
            processo.wait(timeout=3)  # espera soltar os arquivos para poder apagar
        except subprocess.TimeoutExpired:
            pass
    for id_trabalho in list(trabalhos):
        if status_download.get(id_trabalho) not in ("Pronto", "Erro", "Cancelado"):
            for arquivo in glob.glob(os.path.join(PASTA_DOWNLOADS, f"{glob.escape(id_trabalho)}_*")):
                try:
                    os.remove(arquivo)
                except OSError:
                    pass


programa.ao_encerrar.append(parar_tudo)


def cancelar(id_trabalho):
    """Cancela na fila ou no meio da compressão. False se não existe ou já terminou."""
    if id_trabalho not in trabalhos or status_download.get(id_trabalho) in ("Pronto", "Erro", "Cancelado"):
        return False
    cancelados.add(id_trabalho)
    processo = processos.get(id_trabalho)
    if processo:
        processo.kill()
    elif status_download.get(id_trabalho) == "Na fila...":
        status_download[id_trabalho] = "Cancelado"
    return True
