@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "VENV_CLI=%PROJECT_ROOT%.venv\Scripts\tobicloud.exe"

if exist "%VENV_CLI%" (
    "%VENV_CLI%" %*
    exit /b %ERRORLEVEL%
)

uv run tobicloud %*
exit /b %ERRORLEVEL%
