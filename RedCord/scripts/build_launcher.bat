@echo off
cd /d %~dp0\..\launcher
dotnet build -c Release
