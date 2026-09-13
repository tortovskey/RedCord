@echo off
setlocal
cd /d "%~dp0.."

echo [RedCord 0.8.3] building installer...

if not exist ".venv\Scripts\activate.bat" (
    echo [Installer] .venv not found.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo.
echo [Installer] Building RedCord...
set "REDCORD_SKIP_PAUSE=1"
call scripts\build_exe.bat
if errorlevel 1 exit /b 1
set "REDCORD_SKIP_PAUSE="

echo.
echo [Installer] Checking build output...
if not exist "redcord_build\redcord\RedCord.exe" (
    echo [Installer] Missing redcord_build\redcord\RedCord.exe
    pause
    exit /b 1
)

where ISCC.exe >nul 2>nul
if errorlevel 1 (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    ) else (
        echo [Installer] Inno Setup 6 not found.
        echo Install Inno Setup 6 or add ISCC.exe to PATH.
        pause
        exit /b 1
    )
) else (
    set "ISCC=ISCC.exe"
)

if not exist "installer_output" mkdir "installer_output"
"%ISCC%" installer\RedCord_Installer.iss

if errorlevel 1 (
    echo [Installer] Build failed.
    pause
    exit /b 1
)

echo.
echo [Installer] Done:
echo   installer_output\RedCord_Setup_0_8_3.exe
pause
endlocal
