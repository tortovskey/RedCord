@echo off
setlocal
cd /d "%~dp0.."

echo [RedCord 0.8.3] building Windows EXE...

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
python -m pip install -r requirements.txt

if exist "redcord_build" rmdir /s /q "redcord_build"
if exist "build" rmdir /s /q "build"

pyinstaller --noconfirm --clean --distpath redcord_build redcord.spec

if errorlevel 1 (
    echo.
    echo [RedCord] Build failed.
    pause
    exit /b 1
)

echo.
echo [RedCord] Build complete.
echo Output folder:
echo   redcord_build\redcord
echo.
echo Run:
echo   redcord_build\redcord\RedCord.exe
if "%REDCORD_SKIP_PAUSE%"=="" pause
endlocal
