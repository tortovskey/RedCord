@echo off
setlocal
cd /d "%~dp0.."

echo [RedCord 0.8.3] starting...

if not exist ".venv\Scripts\activate.bat" (
    echo [RedCord] .venv not found.
    echo Create it first:
    echo   py -3.12 -m venv .venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m redcord.app.main

if errorlevel 1 (
    echo.
    echo [RedCord] Application finished with error code %errorlevel%.
    pause
)
endlocal
