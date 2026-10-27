# Prepara tudo o que o Puxaí precisa e abre o programa.
# É chamado pelo iniciar.bat (e pelo atalho "Puxaí" da Área de Trabalho).
#
# Na primeira vez, instala sozinho o que estiver faltando:
#   - uv: cuida do Python e das bibliotecas (usa o Python do PC ou baixa um, sem
#     instalar nada no Windows)
#   - FFmpeg e Deno: pelo winget, que já vem no Windows 10 e 11
# Nas próximas vezes, vê que está tudo pronto e abre direto.

# "Continue" e não "Stop": no PowerShell 5.1, com "Stop", qualquer texto que um
# programa escreva no stderr vira uma exceção e interrompe o script. Os erros de
# verdade são conferidos pelo código de saída ($LASTEXITCODE) de cada comando.
$ErrorActionPreference = "Continue"

# winget e uv escrevem em UTF-8; sem isso os acentos saem embaralhados
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Projeto = Split-Path -Parent $PSScriptRoot
Set-Location $Projeto
$Host.UI.RawUI.WindowTitle = "Puxaí"
$instalouAlgo = $false

# Ambiente do programa (Python + bibliotecas) fica na pasta .ambiente do projeto
$env:UV_PROJECT_ENVIRONMENT = Join-Path $Projeto ".ambiente"
# Prefere o Python já instalado no PC (assinado pela Microsoft/PSF); só baixa
# um se não houver nenhum
$env:UV_PYTHON_PREFERENCE = "system"

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

function Garantir-Programa($comando, $idWinget, $nome) {
    if (Get-Command $comando -ErrorAction SilentlyContinue) { return }
    Instalar-Com-Winget $idWinget $nome
    if (-not (Get-Command $comando -ErrorAction SilentlyContinue)) {
        throw "O $nome foi instalado, mas não consegui encontrá-lo. Feche esta janela e abra o iniciar.bat de novo."
    }
}

function Criar-Atalho {
    # GetFolderPath acha a Área de Trabalho certa, mesmo quando ela está no OneDrive
    $areaDeTrabalho = [Environment]::GetFolderPath("Desktop")
    $atalho = Join-Path $areaDeTrabalho "Puxaí.lnk"
    $alvo = Join-Path $Projeto "iniciar.bat"
    $marca = Join-Path $Projeto ".atalho_criado"
    $shell = New-Object -ComObject WScript.Shell

    # O app se chamava "Baixar YouTube": renomeia o atalho antigo em vez de criar outro
    $antigo = Join-Path $areaDeTrabalho "Baixar YouTube.lnk"
    $renomeado = $false
    if ((Test-Path $antigo) -and -not (Test-Path $atalho)) {
        Move-Item $antigo $atalho
        $renomeado = $true
    }

    if (Test-Path $atalho) {
        # Já existe: só corrige se a pasta do projeto mudou de lugar (ou se acabou de ser renomeado)
        $existente = $shell.CreateShortcut($atalho)
        if ($existente.TargetPath -eq $alvo -and -not $renomeado) { return }
    }
    elseif (Test-Path $marca) {
        return # A pessoa apagou o atalho de propósito: não cria de novo
    }

    $novo = $shell.CreateShortcut($atalho)
    $novo.TargetPath = $alvo
    $novo.WorkingDirectory = $Projeto
    $novo.IconLocation = Join-Path $Projeto "painel\icone.ico"
    $novo.Description = "Abre o Puxaí"
    $novo.WindowStyle = 7 # minimizado: só a janela do programa aparece
    $novo.Save()
    Set-Content $marca (Get-Date).ToString("yyyy-MM-dd")
    if (-not $renomeado) { Escrever "Atalho `"Puxaí`" criado na Área de Trabalho." Green }
}

try {
    # Enxerga programas instalados depois que esta janela (ou o Explorer) foi aberta
    Atualizar-Path

    # 1. uv (Python + bibliotecas), FFmpeg e Deno
    Garantir-Programa "uv" "astral-sh.uv" "uv"
    Garantir-Programa "ffmpeg" "Gyan.FFmpeg" "FFmpeg"
    if (-not (Get-Command deno -ErrorAction SilentlyContinue)) {
        # Opcional: o yt-dlp usa para ler o YouTube; se falhar, segue sem ele
        try { Instalar-Com-Winget "DenoLand.Deno" "Deno" }
        catch { Escrever "[AVISO] Não consegui instalar o Deno. O programa funciona, mas alguns vídeos podem falhar." Yellow }
    }

    # 2. Python e bibliotecas (o uv só faz algo se estiver faltando ou mudou)
    $pythonw = Join-Path $env:UV_PROJECT_ENVIRONMENT "Scripts\pythonw.exe"
    if (-not (Test-Path $pythonw)) {
        Escrever "Preparando o Python e as bibliotecas (só na primeira vez)..." Cyan
        $instalouAlgo = $true
    }
    uv sync --no-dev --quiet
    if ($LASTEXITCODE -ne 0) {
        uv sync --no-dev  # de novo, mostrando os detalhes do erro
        throw "Não consegui preparar o Python e as bibliotecas (veja as mensagens acima)."
    }

    # 3. Atualiza o yt-dlp no máximo uma vez por dia (o YouTube muda com frequência)
    $marca = Join-Path $env:TEMP "puxai_ytdlp_atualizado.txt"
    $hoje = (Get-Date).ToString("yyyy-MM-dd")
    if (-not (Test-Path $marca) -or (Get-Content $marca -ErrorAction SilentlyContinue) -ne $hoje) {
        Escrever "Atualizando o yt-dlp..." Cyan
        uv sync --no-dev --quiet --upgrade-package yt-dlp
        if ($LASTEXITCODE -eq 0) { Set-Content $marca $hoje }
    }

    # 4. Atalho "Puxaí" na Área de Trabalho (criado uma vez só)
    try { Criar-Atalho } catch { Escrever "[AVISO] Não consegui criar o atalho na Área de Trabalho: $($_.Exception.Message)" Yellow }

    # 5. Abre o programa (sem janela preta); ele abre a própria janela do painel
    if ($instalouAlgo) { Escrever "`nTudo pronto! Abrindo o Puxaí..." Green }
    Start-Process -FilePath $pythonw -ArgumentList "app.py" -WorkingDirectory $Projeto -ErrorAction Stop
    if ($instalouAlgo) { Start-Sleep -Seconds 3 }
}
catch {
    Escrever "`n[ERRO] $($_.Exception.Message)" Red
    Read-Host "`nAperte Enter para fechar"
    exit 1
}
