@echo off
chcp 65001 >nul
title Gerar executável - Baixar YouTube

rem Vai para a pasta principal do projeto (uma acima de ferramentas\)
cd /d "%~dp0.."
set "PROJETO=%CD%"
set "TEMPORARIOS=%PROJETO%\ferramentas\compilacao"
set "PROGRAMA=%PROJETO%\BaixarYouTube"
set "ATALHO=%PROJETO%\Baixar YouTube.lnk"

echo Instalando dependências e o PyInstaller...
python -m pip install -q --disable-pip-version-check -r requirements.txt pyinstaller

rem Apaga a versão antiga para não confundir com uma geração que falhou
if exist "%PROGRAMA%\BaixarYouTube.exe" del "%PROGRAMA%\BaixarYouTube.exe"

echo.
echo Gerando o programa (pode levar alguns minutos)...
rem --onedir: o programa fica numa pasta já descompactada e abre bem mais rápido
rem           que o modo arquivo único (--onefile)
rem --noconsole: abre só o navegador, sem a janela preta
rem Arquivos temporários (.spec e build) ficam em ferramentas\compilacao
python -m PyInstaller --noconfirm --onedir --noconsole --name BaixarYouTube ^
    --specpath "%TEMPORARIOS%" ^
    --workpath "%TEMPORARIOS%" ^
    --distpath "%PROJETO%" ^
    --icon "%PROJETO%\painel\icone.ico" ^
    --add-data "%PROJETO%\painel;painel" ^
    --collect-submodules yt_dlp ^
    "%PROJETO%\app.py"

echo.
if not exist "%PROGRAMA%\BaixarYouTube.exe" (
    echo [ERRO] O programa não foi gerado. Veja as mensagens acima.
    pause
    exit /b 1
)

rem Atalho na pasta principal: é só dar dois cliques nele
powershell -NoProfile -Command "$a = (New-Object -ComObject WScript.Shell).CreateShortcut('%ATALHO%'); $a.TargetPath = '%PROGRAMA%\BaixarYouTube.exe'; $a.WorkingDirectory = '%PROGRAMA%'; $a.Description = 'Abre o painel do Baixar YouTube'; $a.Save()"

echo Pronto! Programa gerado na pasta BaixarYouTube\
echo Para abrir, dê dois cliques no atalho "Baixar YouTube" na pasta principal.
echo.
echo O FFmpeg precisa estar instalado no PC ou o ffmpeg.exe
echo deve ficar dentro da pasta BaixarYouTube\.
pause
