"""Compressor de fotos (aba "Comprimir foto"), feito com o FFmpeg.

Em vez de usar uma qualidade fixa, mede o resultado: para cada foto, testa
algumas qualidades e fica com o MENOR arquivo que continua visualmente igual
ao original, segundo o nível escolhido. A comparação usa o SSIM (do FFmpeg),
uma medida de semelhança visual em que 1,0 é idêntico.

- JPG continua JPG e WebP continua WebP (o WebP também tenta a versão sem
  perdas e fica com a menor)
- PNG continua PNG: sempre otimizado sem perdas e, quando a imagem permite
  (logos, ilustrações), reduzido a uma paleta de 256 cores, como o TinyPNG
- HEIC (iPhone) vira JPG
- Nunca devolve um arquivo maior que o original
- Corrige a orientação das fotos de celular e remove os metadados (EXIF,
  localização GPS)
"""
import os
import re
import subprocess

# Extensões aceitas -> formato de saída
SAIDAS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp", "heic": "jpg", "heif": "jpg"}

# Semelhança mínima com o original (SSIM) em cada nível:
# - "perdas": JPG e WebP com perdas
# - "paleta": PNG reduzido a 256 cores (medido com um leve desfoque, para não
#   punir o pontilhado, que de perto é invisível; borrões e faixas continuam contando)
NIVEIS = {
    "alta": {"perdas": 0.990, "paleta": 0.997},
    "equilibrado": {"perdas": 0.980, "paleta": 0.990},
    "forte": {"perdas": 0.965, "paleta": 0.960},
}
NIVEL_PADRAO = "equilibrado"

# Maior lado da foto depois de comprimir (None = mantém o tamanho)
TAMANHOS = {"original": None, "2560": 2560, "1920": 1920, "1280": 1280}

# Abaixo disso de economia, não vale a pena salvar outro arquivo
ECONOMIA_MINIMA = 0.02

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ffmpeg(*argumentos):
    """Roda o FFmpeg e devolve as mensagens (stderr). Erro vira exceção."""
    resultado = subprocess.run(
        ["ffmpeg", "-hide_banner", "-y", *argumentos],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=SEM_JANELA,
    )
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr.strip()[-500:])
    return resultado.stderr


def _tem_transparencia(caminho):
    """True se a imagem tem canal de transparência (PNG/WebP com fundo transparente)."""
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt",
         "-of", "csv=p=0", caminho],
        capture_output=True, text=True, creationflags=SEM_JANELA,
    )
    formato = resultado.stdout.strip()
    # pal8 (PNG com paleta) pode ter transparência: trata como se tivesse
    return formato == "pal8" or "a" in formato.replace("gray", "").replace("yuvj", "yuv")


def _ssim(referencia, candidato, transparencia, desfocar=False):
    """Semelhança entre a referência e a versão comprimida (1,0 = idêntico)."""
    preparo = "format=rgb24" + (",gblur=sigma=1" if desfocar else "")
    if transparencia:
        # Cores multiplicadas pela transparência (pixel invisível não conta)...
        preparo = "format=rgba,premultiply=inplace=1," + preparo
    notas = []
    filtros = [f"[0]{preparo}[a];[1]{preparo}[b];[a][b]ssim"]
    if transparencia:
        # ...e a transparência medida à parte
        filtros.append("[0]format=rgba,alphaextract[a];[1]format=rgba,alphaextract[b];[a][b]ssim")
    for filtro in filtros:
        saida = _ffmpeg("-v", "info", "-i", referencia, "-i", candidato, "-lavfi", filtro, "-f", "null", "-")
        nota = re.search(r"All:([0-9.]+)", saida)
        notas.append(float(nota.group(1)) if nota else 0.0)
    return min(notas)


def _buscar_qualidade(menor, maior, gerar, passou):
    """Busca binária: o valor mais "econômico" entre menor e maior que ainda passa.
    gerar(valor) cria o arquivo; passou() diz se ele ficou bom. Valores maiores
    economizam mais. Devolve o melhor valor que passou (ou None)."""
    melhor = None
    while menor <= maior:
        meio = (menor + maior) // 2
        gerar(meio)
        if passou():
            melhor = meio
            menor = meio + 1
        else:
            maior = meio - 1
    return melhor


def comprimir(entrada, extensao, nivel=NIVEL_PADRAO, lado_maximo=None, pasta_trabalho=None):
    """Comprime a foto e devolve um dicionário com o resultado:
    {"caminho", "formato", "largura", "altura", "antes", "depois", "ja_otimizada"}.
    Se não der para economizar, "caminho" é None e "ja_otimizada" é True."""
    extensao = extensao.lower()
    formato = SAIDAS[extensao]
    limites = NIVEIS.get(nivel, NIVEIS[NIVEL_PADRAO])
    pasta_trabalho = pasta_trabalho or os.path.dirname(entrada)
    base = os.path.join(pasta_trabalho, os.path.splitext(os.path.basename(entrada))[0])
    transparencia = formato != "jpg" and _tem_transparencia(entrada)

    # 1. Referência: a foto já girada (EXIF) e reduzida, sem perdas. As
    #    tentativas partem dela e são comparadas com ela.
    referencia = base + "_referencia.nut"
    filtros = []
    if lado_maximo:
        filtros.append(
            f"scale=w='min(iw,{lado_maximo})':h='min(ih,{lado_maximo})'"
            ":force_original_aspect_ratio=decrease:flags=lanczos"
        )
    if transparencia:
        filtros.append("format=rgba")
    _ffmpeg("-i", entrada, "-frames:v", "1", *(["-vf", ",".join(filtros)] if filtros else []),
            "-c:v", "rawvideo", "-f", "nut", referencia)

    tentativa = base + "_tentativa." + formato
    melhor = base + "_comprimida." + formato
    candidatos = []  # caminhos que passaram no teste de qualidade

    def guardar(caminho, nome):
        destino = f"{base}_{nome}.{formato}"
        os.replace(caminho, destino)
        candidatos.append(destino)

    try:
        if formato == "jpg":
            # q:v do FFmpeg: 2 (melhor) a 31 (pior); maior = arquivo menor
            def gerar(q):
                _ffmpeg("-i", referencia, "-q:v", str(q), "-pix_fmt", "yuvj420p", tentativa)

            q = _buscar_qualidade(2, 24, gerar, lambda: _ssim(referencia, tentativa, False) >= limites["perdas"])
            if q is not None:
                gerar(q)
                guardar(tentativa, "jpg")

        elif formato == "webp":
            # Qualidade do WebP: 100 (melhor) a 0; a busca usa 100 - qualidade
            def gerar(inverso):
                _ffmpeg("-i", referencia, "-c:v", "libwebp", "-quality", str(100 - inverso),
                        "-compression_level", "6", tentativa)

            inverso = _buscar_qualidade(5, 70, gerar,
                                        lambda: _ssim(referencia, tentativa, transparencia) >= limites["perdas"])
            if inverso is not None:
                gerar(inverso)
                guardar(tentativa, "perdas")
            # Sem perdas: costuma ganhar em logos, prints e ilustrações
            _ffmpeg("-i", referencia, "-c:v", "libwebp", "-lossless", "1", "-compression_level", "6", tentativa)
            guardar(tentativa, "sem_perdas")

        else:  # png
            # Sem perdas: sempre igual ao original, só melhor compactado
            _ffmpeg("-i", referencia, "-pred", "mixed", "-compression_level", "9", tentativa)
            guardar(tentativa, "sem_perdas")
            # Paleta de 256 cores (como o TinyPNG), se continuar parecida o bastante
            _ffmpeg("-i", referencia, "-lavfi",
                    "split[a][b];[a]palettegen=max_colors=256:stats_mode=full:reserve_transparent=1[p];"
                    "[b][p]paletteuse=dither=floyd_steinberg:alpha_threshold=128",
                    "-pred", "mixed", "-compression_level", "9", tentativa)
            if _ssim(referencia, tentativa, transparencia, desfocar=True) >= limites["paleta"]:
                guardar(tentativa, "paleta")

        antes = os.path.getsize(entrada)
        escolhido = min(candidatos, key=os.path.getsize) if candidatos else None
        depois = os.path.getsize(escolhido) if escolhido else antes

        # HEIC sempre vira JPG (é o objetivo); nos outros, só vale se economizar
        if escolhido and (extensao in ("heic", "heif") or depois < antes * (1 - ECONOMIA_MINIMA)):
            os.replace(escolhido, melhor)
            largura, altura = _dimensoes(melhor)
            return {"caminho": melhor, "formato": formato, "largura": largura, "altura": altura,
                    "antes": antes, "depois": depois, "ja_otimizada": False}
        return {"caminho": None, "formato": formato, "largura": None, "altura": None,
                "antes": antes, "depois": antes, "ja_otimizada": True}

    finally:
        for caminho in [referencia, tentativa, *candidatos]:
            if os.path.exists(caminho):
                os.remove(caminho)


def _dimensoes(caminho):
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", caminho],
        capture_output=True, text=True, creationflags=SEM_JANELA,
    )
    try:
        largura, altura = resultado.stdout.strip().split("x")
        return int(largura), int(altura)
    except ValueError:
        return None, None
