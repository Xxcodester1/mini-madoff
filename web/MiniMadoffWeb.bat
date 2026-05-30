@echo off
title Mini Madoff Web
echo.
echo  Starting Mini Madoff Web Dashboard...
echo  Opening http://localhost:5000
echo.
start "" "http://localhost:5000"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%~dp0app.py"
pause
