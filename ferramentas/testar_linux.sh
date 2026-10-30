#!/bin/sh
# Teste rápido do programa gerado para Linux (Puxai/Puxai), antes de publicar.
# O equivalente do testar_exe.ps1.
#
# Abre uma cópia do programa no modo navegador, confere se a API responde,
# converte e comprime uma imagem (prova que o FFmpeg incluído funciona) e
# fecha. Roda numa cópia da pasta, para o que o programa cria ao rodar (log,
# pasta downloads/) não ir junto no pacote.
#
# Uso: sh ferramentas/testar_linux.sh [pasta do programa] [porta]
# Também é usado pelo GitHub (.github/workflows/gerar-exe.yml).
PASTA=${1:-"$(cd "$(dirname "$0")/.." && pwd)/Puxai"}
PORTA=${2:-5097}
ENDERECO="http://127.0.0.1:$PORTA"
COPIA=$(mktemp -d)/Puxai
falhas=0
pid=""

conferir() {  # conferir NOME DETALHE COMANDO...
    nome=$1 detalhe=$2
    shift 2
    if "$@" >/dev/null 2>&1; then
        printf '  OK      %s %s\n' "$nome" "$detalhe"
    else
        printf '  FALHOU  %s %s\n' "$nome" "$detalhe"
        falhas=$((falhas + 1))
    fi
}

terminar() {
    [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
    if [ "$falhas" -gt 0 ] && [ -f "$COPIA/registro.txt" ]; then
        printf '\n--- mensagens do programa ---\n'; tail -n 40 "$COPIA/registro.txt"
    fi
    rm -rf "$(dirname "$COPIA")"
    if [ "$falhas" -gt 0 ]; then printf '\n%s teste(s) falharam.\n' "$falhas"; exit 1; fi
    printf '\nTudo certo com o programa gerado.\n'
    exit 0
}

[ -x "$PASTA/Puxai" ] || { echo "Não achei $PASTA/Puxai"; falhas=1; terminar; }
echo "Copiando o programa para $COPIA..."
cp -a "$PASTA" "$COPIA"

conferir "ffmpeg incluído" "" test -x "$COPIA/ffmpeg"
conferir "ffprobe incluído" "" test -x "$COPIA/ffprobe"
conferir "deno incluído" "" test -x "$COPIA/deno"

# Tira do PATH o FFmpeg e o Deno instalados no PC: o teste só passa se os incluídos no programa funcionarem
PATH=$(printf '%s' "$PATH" | tr ':' '\n' | while read -r p; do
    [ -n "$p" ] && [ ! -e "$p/ffmpeg" ] && [ ! -e "$p/deno" ] && printf '%s:' "$p"
done)
export PATH="${PATH%:}"
conferir "sem FFmpeg instalado no PATH" "" sh -c '! command -v ffmpeg'

# Janela própria (Qt) numa tela virtual: prova que o Qt e o WebEngine vieram junto
if command -v xvfb-run >/dev/null 2>&1; then
    conferir "janela (Qt) abre" "" timeout 60 xvfb-run -a "$COPIA/Puxai" --testar-janela
fi

# Modo navegador, sem abrir navegador de verdade (o "navegador" é o comando true, que não faz nada)
PORTA=$PORTA PUXAI_MODO=navegador BROWSER=true "$COPIA/Puxai" > "$COPIA/registro.txt" 2>&1 &
pid=$!

respondeu=""
for _ in $(seq 90); do
    sleep 1
    if curl -sf "$ENDERECO/api/qualidades" -o "$COPIA/qualidades.json"; then respondeu=1; break; fi
done
conferir "programa abriu e a API responde" "" test -n "$respondeu"
[ -n "$respondeu" ] || terminar
conferir "lista de qualidades" "" grep -q '"qualidades"' "$COPIA/qualidades.json"

versao=$(curl -sf "$ENDERECO/api/versao" | sed -n 's/.*"atual": *"\([^"]*\)".*/\1/p')
conferir "versão" "($versao)" test -n "$versao"
conferir "painel (index.html)" "" curl -sf "$ENDERECO/" -o /dev/null

# Uma imagem PNG de teste, feita pelo próprio FFmpeg incluído
imagem="$COPIA/teste.png"
"$COPIA/ffmpeg" -v error -y -f lavfi -i "testsrc2=s=320x240" -frames:v 1 "$imagem"
conferir "FFmpeg incluído roda" "" test -s "$imagem"

codigo=$(curl -s -o "$COPIA/teste.webp" -w "%{http_code}" -F "arquivo=@$imagem" -F "formato=webp" "$ENDERECO/api/converter/imagem")
conferir "converter PNG para WebP" "(HTTP $codigo)" sh -c "[ '$codigo' = 200 ] && [ -s '$COPIA/teste.webp' ]"

conferir "comprimir foto (usa o ffprobe)" "" sh -c "curl -s -F 'arquivo=@$imagem' -F 'nivel=forte' '$ENDERECO/api/comprimir' | grep -q ."

# Segurança: um pedido "de outro site" tem que ser recusado
codigo=$(curl -s -o /dev/null -w "%{http_code}" -H "Origin: https://site-ruim.com" -H "Sec-Fetch-Site: cross-site" "$ENDERECO/api/qualidades")
conferir "pedido de outro site recusado" "(HTTP $codigo)" test "$codigo" = 403

curl -sf -X POST "$ENDERECO/api/encerrar" -o /dev/null
fechou=""
for _ in $(seq 15); do
    if ! kill -0 "$pid" 2>/dev/null; then fechou=1; break; fi
    sleep 1
done
conferir "programa fechou" "" test -n "$fechou"
[ -n "$fechou" ] && pid=""
terminar
