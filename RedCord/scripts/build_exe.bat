@echo off
cd /d %~dp0\..
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
pyinstaller --name RedCord --onefile --windowed --icon assets\redcord.ico redcord\main.py
