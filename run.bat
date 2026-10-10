@echo off
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" bot.py
    goto :done
)

python bot.py

:done
pause
