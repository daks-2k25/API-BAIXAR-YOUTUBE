# Prepara tudo o que o Baixar YouTube precisa e abre o painel no navegador.
# É chamado pelo iniciar.bat.
#
# Na primeira vez, instala sozinho o que estiver faltando (Python, FFmpeg, Deno
# e as bibliotecas do Python) usando o winget, que já vem no Windows 10 e 11.
# Nas próximas vezes, vê que está tudo pronto e abre direto.

$ErrorActionPreference = "Stop"
$Projeto = Split-Path -Parent $PSScriptRoot
Set-Location $Projeto
$Host.UI.RawUI.WindowTitle = "Baixar YouTube"
$instalouAlgo = $false

function Escrever($texto, $cor = "Gray") {
    Write-Host $texto -ForegroundColor $cor
}

function Atualizar-Path {
    # Programas recém-instalados só entram no PATH de janelas novas.
    # Relê o PATH do Windows para enxergá-los sem precisar reabrir.
    $maquina = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $usuario = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$maquina;$usuario"
}

function Instalar-Com-Winget($id, $nome) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Não encontrei o winget para instalar o $nome. Instale o `"Instalador de Aplicativo`" pela Microsoft Store e tente de novo."
    }
    Escrever "Instalando $nome (só na primeira vez, pode levar alguns minutos)..." Cyan
    $opcoes = @("install", "--id", $id, "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements")

    # Tenta instalar só para o usuário (sem pedir administrador); se o pacote
    # não tiver essa opção, instala do jeito padrão
    winget @opcoes --scope user | Out-Host
    if ($LASTEXITCODE -ne 0) {
        winget @opcoes | Out-Host
    }
    Atualizar-Path
    $script:instalouAlgo = $true
}

function Encontrar-Python {
    # Testa cada Python possível e devolve o caminho real do primeiro que funcionar
    # (o "python" da Microsoft Store pode ser só um atalho que não roda nada)
    $teste = "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')"
    $candidatos = @()
    if (Get-Command py -ErrorAction SilentlyContinue) { $candidatos += , @("py", "-3") }
    Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object { $candidatos += , @($_.Source) }
    Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
        ForEach-Object { $candidatos += , @($_.FullName) }

    foreach ($candidato in $candidatos) {
        try {
            $exe = $candidato[0]
            $argumentos = @($candidato | Select-Object -Skip 1) + @("-c", $teste)
            # Sem "| Select-Object -First 1": ele interrompe o programa e o código de saída vira -1
            $saida = @(& $exe @argumentos 2>$null)
            $caminho = if ($saida.Count -gt 0) { "$($saida[0])".Trim() } else { "" }
            if ($LASTEXITCODE -eq 0 -and $caminho -and (Test-Path $caminho)) { return $caminho }
        } catch { }
    }
    return $null
}

try {
    # Enxerga programas instalados depois que esta janela (ou o Explorer) foi aberta
    Atualizar-Path

    # 1. Python
    $python = Encontrar-Python
    if (-not $python) {
        Instalar-Com-Winget "Python.Python.3.13" "Python"
        $python = Encontrar-Python
        if (-not $python) { throw "O Python foi instalado, mas não consegui encontrá-lo. Feche esta janela e abra o iniciar.bat de novo." }
    }
    $pythonw = Join-Path (Split-Path $python) "pythonw.exe"

    # 2. FFmpeg (junta vídeo e áudio, gera MP3 e converte HEIC)
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Instalar-Com-Winget "Gyan.FFmpeg" "FFmpeg"
        if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            throw "O FFmpeg foi instalado, mas não consegui encontrá-lo. Feche esta janela e abra o iniciar.bat de novo."
        }
    }

    # 3. Deno (o yt-dlp usa para ler o YouTube). Opcional: se falhar, segue sem ele.
    if (-not (Get-Command deno -ErrorAction SilentlyContinue)) {
        try { Instalar-Com-Winget "DenoLand.Deno" "Deno" }
        catch { Escrever "[AVISO] Não consegui instalar o Deno. O programa funciona, mas alguns vídeos podem falhar." Yellow }
    }

    # 4. Bibliotecas do Python (Flask, yt-dlp...)
    & $python -c "import flask, flask_cors, yt_dlp" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Escrever "Instalando as bibliotecas do Python..." Cyan
        & $python -m pip install -q --disable-pip-version-check -r requirements.txt | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Não consegui instalar as bibliotecas do Python (veja as mensagens acima)." }
        $instalouAlgo = $true
    }

    # 5. Atualiza o yt-dlp no máximo uma vez por dia (o YouTube muda com frequência)
    $marca = Join-Path $env:TEMP "baixar_youtube_ytdlp_atualizado.txt"
    $hoje = (Get-Date).ToString("yyyy-MM-dd")
    if (-not (Test-Path $marca) -or (Get-Content $marca -ErrorAction SilentlyContinue) -ne $hoje) {
        Escrever "Atualizando o yt-dlp..." Cyan
        & $python -m pip install -q --disable-pip-version-check -U yt-dlp | Out-Host
        if ($LASTEXITCODE -eq 0) { Set-Content $marca $hoje }
    }

    # 6. Abre o programa sem janela; ele mesmo abre o painel no navegador
    if ($instalouAlgo) { Escrever "`nTudo pronto! Abrindo o painel no navegador..." Green }
    Start-Process -FilePath $pythonw -ArgumentList "app.py" -WorkingDirectory $Projeto
    if ($instalouAlgo) { Start-Sleep -Seconds 3 }
}
catch {
    Escrever "`n[ERRO] $($_.Exception.Message)" Red
    Read-Host "`nAperte Enter para fechar"
    exit 1
}
