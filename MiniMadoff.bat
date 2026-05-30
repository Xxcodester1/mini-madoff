@echo off
title Mini Madoff
chcp 65001 >nul
mode con: cols=120 lines=40
"C:\Users\xxcod\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0dashboard.py"
pause
