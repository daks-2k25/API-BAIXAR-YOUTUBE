@echo off
chcp 65001 >nul
title Gerar executável - Puxaí

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
    pause
    exit /b 1
)
echo Preparando o Python e as bibliotecas...
uv sync --no-dev --quiet

rem Apaga a versão antiga para não confundir com uma geração que falhou
if exist "%PROGRAMA%\Puxai.exe" del "%PROGRAMA%\Puxai.exe" 2>nul
if exist "%PROGRAMA%\Puxai.exe" (
    echo.
    echo [ERRO] O programa está aberto. Feche a janela dele e rode este arquivo de novo.
    pause
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
    pause
    exit /b 1
)

rem Atalho na pasta principal: é só dar dois cliques nele
powershell -NoProfile -Command "$a = (New-Object -ComObject WScript.Shell).CreateShortcut('%ATALHO%'); $a.TargetPath = '%PROGRAMA%\Puxai.exe'; $a.WorkingDirectory = '%PROGRAMA%'; $a.Description = 'Abre o Puxaí'; $a.Save()"

echo Pronto! Programa gerado na pasta Puxai\
echo Para abrir, dê dois cliques no atalho "Puxaí" na pasta principal.
echo.
echo O FFmpeg precisa estar instalado no PC ou o ffmpeg.exe
echo deve ficar dentro da pasta Puxai\.
pause
