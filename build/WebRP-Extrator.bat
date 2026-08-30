@echo off
setlocal
set "DIR=%~dp0"
set "PLAYWRIGHT_BROWSERS_PATH=%DIR%ms-playwright"
start "" "%DIR%WebRP-Extrator.exe"
