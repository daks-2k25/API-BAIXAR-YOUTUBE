#!/bin/sh
# Gera o programa para Linux (Puxai/Puxai) com o PyInstaller.
# É o equivalente do gerar_exe.bat, usado pelo GitHub para gerar o programa de
# cada versão (.github/workflows/gerar-exe.yml).
#
# Uso: sh ferramentas/gerar_linux.sh
# Precisa do uv e do FFmpeg (o ffmpeg e o ffprobe do PATH vão junto no programa).

# Vai para a pasta principal do projeto (uma acima de ferramentas/)
cd "$(dirname "$0")/.." || exit 1
PROJETO=$(pwd)
TEMPORARIOS="$PROJETO/ferramentas/compilacao"
PROGRAMA="$PROJETO/Puxai"

erro() { printf '\n[ERRO] %s\n' "$*"; exit 1; }

# O uv prepara o Python e as bibliotecas (o mesmo ambiente do iniciar.sh)
export UV_PROJECT_ENVIRONMENT="$PROJETO/.ambiente"
export UV_PYTHON_PREFERENCE=system
command -v uv >/dev/null 2>&1 || erro "uv não encontrado. Rode o iniciar.sh uma vez antes (ele instala o uv)."
echo "Preparando o Python e as bibliotecas..."
uv sync --no-dev --quiet || erro "Não consegui preparar o Python e as bibliotecas."

echo
echo "Gerando o programa (pode levar alguns minutos)..."
# --onedir: o programa fica numa pasta já descompactada e abre bem mais rápido
# --windowed: sem terminal junto
# A janela usa o Qt, que o pywebview e o qtpy escolhem durante o uso (o
# PyInstaller não enxerga sozinho): por isso os --hidden-import
# "uv run --with pyinstaller": usa o PyInstaller só durante a geração
uv run --no-dev --with pyinstaller python -m PyInstaller --noconfirm --clean --onedir --windowed --name Puxai \
    --specpath "$TEMPORARIOS" \
    --workpath "$TEMPORARIOS" \
    --distpath "$PROJETO" \
    --add-data "$PROJETO/painel:painel" \
    --add-data "$PROJETO/versao.json:." \
    --collect-submodules yt_dlp \
    --hidden-import webview.platforms.qt \
    --hidden-import PyQt6.QtWebEngineWidgets \
    --hidden-import PyQt6.QtWebEngineCore \
    --hidden-import PyQt6.QtWebChannel \
    --hidden-import PyQt6.QtNetwork \
    "$PROJETO/app.py" || erro "O programa não foi gerado. Veja as mensagens acima."
[ -x "$PROGRAMA/Puxai" ] || erro "O programa não foi gerado. Veja as mensagens acima."

# FFmpeg e Deno junto do programa (ao lado do Puxai): quem recebe o programa
# não precisa instalar nada. O FFmpeg é o deste PC; o Deno, o das bibliotecas.
ffmpeg=$(command -v ffmpeg) && ffprobe=$(command -v ffprobe) || erro "FFmpeg não encontrado neste PC."
cp "$ffmpeg" "$ffprobe" "$PROGRAMA/"
cp "$UV_PROJECT_ENVIRONMENT/bin/deno" "$PROGRAMA/" || erro "Deno não encontrado no ambiente (.ambiente/bin/deno)."
echo "FFmpeg e Deno incluídos no programa."

echo
echo "Pronto! Programa gerado na pasta Puxai/"
echo "Para abrir: ./Puxai/Puxai (na primeira vez, ele cria o atalho no menu de aplicativos)."
echo "Para levar para outro PC, copie a pasta Puxai/ inteira."
