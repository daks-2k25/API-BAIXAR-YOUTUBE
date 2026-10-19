@echo off
chcp 65001 >nul
title API Baixar YouTube
cd /d "%~dp0"

echo ==========================================
echo           API Baixar YouTube
echo ==========================================
echo.

where python >nul 2>nul || (
    echo [ERRO] Python não encontrado. Instale em https://www.python.org/downloads/
    pause
    exit /b 1
)

where ffmpeg >nul 2>nul || (
    echo [ERRO] FFmpeg não encontrado. Instale com: winget install ffmpeg
    pause
    exit /b 1
)

rem Só instala as dependências se estiver faltando alguma (abre bem mais rápido)
python -c "import flask, flask_cors, yt_dlp" >nul 2>nul || (
    echo Instalando dependências...
    python -m pip install -q --disable-pip-version-check -r requirements.txt
)

rem Atualiza o yt-dlp no máximo uma vez por dia (o YouTube muda com frequência)
set "MARCA_ATUALIZACAO=%TEMP%\baixar_youtube_ytdlp_atualizado.txt"
set "ULTIMA_ATUALIZACAO="
if exist "%MARCA_ATUALIZACAO%" set /p ULTIMA_ATUALIZACAO=<"%MARCA_ATUALIZACAO%"
if not "%ULTIMA_ATUALIZACAO%"=="%DATE%" (
    echo Atualizando o yt-dlp...
    python -m pip install -q --disable-pip-version-check -U yt-dlp && (echo %DATE%)>"%MARCA_ATUALIZACAO%"
)

where deno >nul 2>nul || (
    echo.
    echo [AVISO] Deno não encontrado: alguns vídeos podem falhar.
    echo         Para instalar: winget install DenoLand.Deno
)

echo.
echo Abrindo o painel no navegador...
rem pythonw roda sem janela; esta janela fecha sozinha em seguida
start "" pythonw app.py
