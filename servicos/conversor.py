import os
import subprocess

# Usa o FFmpeg (já necessário para os downloads) para ler o formato HEIC da Apple.
# O pillow-heif foi removido porque o Controle Inteligente de Aplicativos do
# Windows bloqueia a DLL dele.

# Formato de saída -> extensões de entrada aceitas.
# JPG só aceita HEIC: um PNG com fundo transparente ficaria com fundo preto.
# WebP mantém a transparência, então aceita PNG também.
FORMATOS = {
    "jpg": ("heic", "heif"),
    "webp": ("heic", "heif", "jpg", "jpeg", "png"),
}

# Opções do FFmpeg para cada formato de saída
OPCOES_SAIDA = {
    "jpg": ["-q:v", "1"],                                  # Qualidade máxima do JPG
    "webp": ["-c:v", "libwebp", "-quality", "90"],         # Boa qualidade, arquivo bem menor
}


def converter_imagem(caminho_entrada, formato="jpg", caminho_saida=None):
    if not os.path.exists(caminho_entrada):
        print("Erro: Arquivo de entrada não encontrado.")
        return False

    # Se não informar o caminho de saída, salva com o mesmo nome, mas com a extensão nova
    if not caminho_saida:
        caminho_saida = caminho_entrada.rsplit('.', 1)[0] + "." + formato

    print(f"Iniciando conversão para {formato.upper()} de: {caminho_entrada}")

    comando = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", caminho_entrada,
        "-frames:v", "1",   # HEIC pode ter várias imagens; pega só a principal
        *OPCOES_SAIDA[formato],
        caminho_saida,
    ]

    try:
        # CREATE_NO_WINDOW: não pisca uma janela preta do FFmpeg no Windows
        resultado = subprocess.run(
            comando, capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if resultado.returncode != 0 or not os.path.exists(caminho_saida):
            print(f"Erro durante a conversão: {resultado.stderr.strip()}")
            return False

        print(f"Sucesso! Imagem salva em: {caminho_saida}")

        # Retorna o caminho para que a rota (rotas/fotos.py) consiga devolver ao usuário
        return caminho_saida

    except FileNotFoundError:
        print("Erro durante a conversão: FFmpeg não encontrado no PATH.")
        return False
