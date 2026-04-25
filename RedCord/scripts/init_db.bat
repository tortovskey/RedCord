@echo off
cd /d %~dp0\..
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m redcord.main --migrate
python -m redcord.main --health-check
