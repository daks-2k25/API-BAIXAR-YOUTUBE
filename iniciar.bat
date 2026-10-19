@echo off
rem Dois cliques aqui abrem o Baixar YouTube.
rem Na primeira vez, instala sozinho o que faltar (Python, FFmpeg, Deno e bibliotecas).
rem A lógica fica em ferramentas\iniciar.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ferramentas\iniciar.ps1"
