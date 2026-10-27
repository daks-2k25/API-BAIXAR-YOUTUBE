@echo off
chcp 65001 >nul
title Gerar executável - Puxaí

rem Gera o programa (Puxai\Puxai.exe) com o PyInstaller.
rem É o mesmo arquivo usado pelo GitHub para gerar o .exe de cada versão
rem (.github\workflows\gerar-exe.yml). Lá a variável CI existe, então ele
rem não para em "pause" esperando alguém apertar uma tecla.

rem Vai para a pasta principal do projeto (uma acima de ferramentas\)
cd /d "%~dp0.."
set "PROJETO=%CD%"
set "TEMPORARIOS=%PROJETO%\ferramentas\compilacao"
set "PROGRAMA=%PROJETO%\Puxai"
set "ATALHO=%PROJETO%\Puxaí.lnk"

rem O uv prepara o Python e as bibliotecas (o mesmo ambiente do iniciar.bat)
set "UV_PROJECT_ENVIRONMENT=%PROJETO%\.ambiente"
set "UV_PYTHON_PREFERENCE=system"
where uv >nul 2>nul || (
    echo [ERRO] uv não encontrado. Rode o iniciar.bat uma vez antes ^(ele instala o uv^).
    if not defined CI pause
    exit /b 1
)
echo Preparando o Python e as bibliotecas...
uv sync --no-dev --quiet || (
    echo [ERRO] Não consegui preparar o Python e as bibliotecas.
    if not defined CI pause
    exit /b 1
)

rem Apaga a versão antiga para não confundir com uma geração que falhou
if exist "%PROGRAMA%\Puxai.exe" del "%PROGRAMA%\Puxai.exe" 2>nul
if exist "%PROGRAMA%\Puxai.exe" (
    echo.
    echo [ERRO] O programa está aberto. Feche a janela dele e rode este arquivo de novo.
    if not defined CI pause
    exit /b 1
)

echo.
echo Gerando o programa (pode levar alguns minutos)...
rem --onedir: o programa fica numa pasta já descompactada e abre bem mais rápido
rem           que o modo arquivo único (--onefile)
rem --noconsole: abre só a janela do programa, sem a janela preta
rem Arquivos temporários (.spec e build) ficam em ferramentas\compilacao
rem "uv run --with pyinstaller": usa o PyInstaller só durante a geração
rem --clean: gera do zero (sem isso, trocar o ícone podia não ter efeito)
uv run --no-dev --with pyinstaller python -m PyInstaller --noconfirm --clean --onedir --noconsole --name Puxai ^
    --specpath "%TEMPORARIOS%" ^
    --workpath "%TEMPORARIOS%" ^
    --distpath "%PROJETO%" ^
    --icon "%PROJETO%\painel\icone.ico" ^
    --add-data "%PROJETO%\painel;painel" ^
    --add-data "%PROJETO%\versao.json;." ^
    --collect-submodules yt_dlp ^
    "%PROJETO%\app.py"

echo.
if not exist "%PROGRAMA%\Puxai.exe" (
    echo [ERRO] O programa não foi gerado. Veja as mensagens acima.
    if not defined CI pause
    exit /b 1
)

rem FFmpeg junto do programa (ffmpeg.exe e ffprobe.exe ao lado do Puxai.exe):
rem quem recebe o programa não precisa instalar nada. Usa o FFmpeg deste PC.
set "PASTA_FFMPEG="
for /f "delims=" %%F in ('where ffmpeg 2^>nul') do if not defined PASTA_FFMPEG set "PASTA_FFMPEG=%%~dpF"
if defined PASTA_FFMPEG (
    copy /y "%PASTA_FFMPEG%ffmpeg.exe" "%PROGRAMA%\" >nul
    copy /y "%PASTA_FFMPEG%ffprobe.exe" "%PROGRAMA%\" >nul
)
if exist "%PROGRAMA%\ffprobe.exe" (
    echo FFmpeg incluído no programa.
) else (
    echo [AVISO] FFmpeg não encontrado neste PC: o programa vai precisar dele instalado
    echo         ^(ou do ffmpeg.exe e do ffprobe.exe dentro da pasta Puxai\^).
    if defined CI exit /b 1
)

rem Atalho na pasta principal: é só dar dois cliques nele
if not defined CI powershell -NoProfile -Command "$a = (New-Object -ComObject WScript.Shell).CreateShortcut('%ATALHO%'); $a.TargetPath = '%PROGRAMA%\Puxai.exe'; $a.WorkingDirectory = '%PROGRAMA%'; $a.Description = 'Abre o Puxaí'; $a.Save()"

echo.
echo Pronto! Programa gerado na pasta Puxai\
echo Para abrir, dê dois cliques no atalho "Puxaí" na pasta principal.
echo Para levar para outro PC, copie a pasta Puxai\ inteira.
if not defined CI pause
exit /b 0
