#!/bin/sh
# Abre o Puxaí no Linux (o equivalente ao iniciar.bat do Windows).
# Uso: sh iniciar.sh   (ou ./iniciar.sh; depois, pelo atalho "Puxaí" no menu de aplicativos)
#
# Na primeira vez, prepara sozinho o que estiver faltando, sem pedir senha
# (nada é instalado no sistema, tudo fica na sua pasta pessoal ou na do projeto):
#   - uv: cuida do Python e das bibliotecas (usa o Python do PC ou baixa um)
#   - FFmpeg: usa o do sistema; se não houver, baixa um pronto para a pasta .ffmpeg
#   - Deno (o yt-dlp usa para ler o YouTube) e a janela do programa (Qt) vêm
#     junto com as bibliotecas
# Nas próximas vezes, vê que está tudo pronto e abre direto.

PROJETO=$(cd "$(dirname "$0")" && pwd)
cd "$PROJETO" || exit 1

# Ambiente do programa (Python + bibliotecas) fica na pasta .ambiente do projeto
export UV_PROJECT_ENVIRONMENT="$PROJETO/.ambiente"
# O uv fica em ~/.local/bin, que nem sempre está no PATH (ex.: aberto pelo menu)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
REGISTRO="$PROJETO/Puxai.log"
instalou_algo=""

escrever() { printf '%s\n' "$*"; }

erro() {
    escrever "" "[ERRO] $*"
    # Aberto pelo menu (sem terminal): mostra o erro numa janela, se der
    if [ ! -t 1 ]; then
        if command -v zenity >/dev/null 2>&1; then
            zenity --error --title="Puxaí" --text="$*" 2>/dev/null
        elif command -v kdialog >/dev/null 2>&1; then
            kdialog --title "Puxaí" --error "$*" 2>/dev/null
        elif command -v notify-send >/dev/null 2>&1; then
            notify-send "Puxaí" "$*"
        fi
    fi
    exit 1
}

baixar() {  # baixar URL ARQUIVO
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 2 -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$2" "$1"
    else
        erro "Não encontrei o curl nem o wget para baixar o que falta. Instale um deles (ex.: sudo apt install curl) e tente de novo."
    fi
}

[ "$(uname -s)" = "Linux" ] || erro "Este arquivo é para o Linux. No Windows, use o iniciar.bat."

# O Puxai.log recomeça do zero quando passa de 1 MB
if [ -f "$REGISTRO" ] && [ "$(wc -c < "$REGISTRO")" -gt 1000000 ]; then : > "$REGISTRO"; fi
# Aberto pelo menu (sem terminal), as mensagens daqui também vão para o Puxai.log
[ -t 1 ] || exec >> "$REGISTRO" 2>&1

preparando() {
    # Aberto pelo menu, na primeira vez: avisa que vai demorar um pouco (uma vez só)
    if [ -z "$instalou_algo" ] && [ ! -t 1 ] && command -v notify-send >/dev/null 2>&1; then
        notify-send "Puxaí" "Preparando o programa (só na primeira vez). Pode levar alguns minutos..."
    fi
    instalou_algo=1
}

# 1. uv (Python + bibliotecas)
if ! command -v uv >/dev/null 2>&1; then
    escrever "Instalando o uv (só na primeira vez)..."
    preparando
    temporario=$(mktemp)
    baixar "https://astral.sh/uv/install.sh" "$temporario" || erro "Não consegui baixar o uv. Confira a internet e tente de novo."
    # UV_NO_MODIFY_PATH: não mexe nos arquivos de configuração do seu terminal
    UV_NO_MODIFY_PATH=1 sh "$temporario" || erro "Não consegui instalar o uv (veja as mensagens acima)."
    rm -f "$temporario"
    command -v uv >/dev/null 2>&1 || erro "O uv foi instalado, mas não consegui encontrá-lo em ~/.local/bin."
fi

# 2. FFmpeg: o do sistema ou um pronto (com H.264, MP3 e WebP), na pasta .ffmpeg
if ! { command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; } && [ ! -x "$PROJETO/.ffmpeg/ffprobe" ]; then
    case "$(uname -m)" in
        x86_64|amd64) arquitetura=linux64 ;;
        aarch64|arm64) arquitetura=linuxarm64 ;;
        *) erro "Não há FFmpeg pronto para este processador ($(uname -m)). Instale pelo sistema (ex.: sudo apt install ffmpeg) e tente de novo." ;;
    esac
    escrever "Baixando o FFmpeg (só na primeira vez, cerca de 150 MB)..."
    preparando
    nome="ffmpeg-master-latest-$arquitetura-gpl.tar.xz"
    endereco="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
    temporaria=$(mktemp -d)
    baixar "$endereco/$nome" "$temporaria/$nome" && baixar "$endereco/checksums.sha256" "$temporaria/checksums.sha256" \
        || erro "Não consegui baixar o FFmpeg. Confira a internet, ou instale pelo sistema (ex.: sudo apt install ffmpeg)."
    # Confere que o arquivo chegou inteiro e é o publicado
    (cd "$temporaria" && grep " $nome\$" checksums.sha256 | sha256sum -c --status) \
        || erro "O FFmpeg baixado não confere (SHA-256 diferente). Tente de novo mais tarde."
    tar -xJf "$temporaria/$nome" -C "$temporaria" || erro "Não consegui descompactar o FFmpeg."
    mkdir -p "$PROJETO/.ffmpeg"
    cp "$temporaria"/ffmpeg-*/bin/ffmpeg "$temporaria"/ffmpeg-*/bin/ffprobe "$PROJETO/.ffmpeg/"
    rm -rf "$temporaria"
fi

# 3. Python e bibliotecas (o uv só faz algo se estiver faltando ou mudou)
if [ ! -x "$UV_PROJECT_ENVIRONMENT/bin/python" ]; then
    escrever "Preparando o Python e as bibliotecas (só na primeira vez, pode levar alguns minutos)..."
    preparando
fi
if ! uv sync --no-dev --quiet; then
    uv sync --no-dev  # de novo, mostrando os detalhes do erro
    erro "Não consegui preparar o Python e as bibliotecas (veja as mensagens acima)."
fi

# 4. Atualiza o yt-dlp no máximo uma vez por dia (o YouTube muda com frequência)
marca="${XDG_CACHE_HOME:-$HOME/.cache}/puxai_ytdlp_atualizado.txt"
hoje=$(date +%Y-%m-%d)
if [ "$(cat "$marca" 2>/dev/null)" != "$hoje" ]; then
    escrever "Atualizando o yt-dlp..."
    if uv sync --no-dev --quiet --upgrade-package yt-dlp; then
        mkdir -p "$(dirname "$marca")" && printf '%s\n' "$hoje" > "$marca"
    fi
fi

# 5. Abre o programa em segundo plano (ele abre a própria janela do painel), com
#    as mensagens no Puxai.log. Na primeira vez, ele cria o atalho "Puxaí" no menu
#    de aplicativos. Se já estiver aberto, só traz a janela para a frente.
[ -n "$instalou_algo" ] && escrever "" "Tudo pronto! Abrindo o Puxaí..."
nohup "$UV_PROJECT_ENVIRONMENT/bin/python" app.py >> "$REGISTRO" 2>&1 &
[ -t 1 ] && escrever "Pode fechar este terminal; as mensagens do programa ficam no Puxai.log."
exit 0
