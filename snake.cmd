@echo off
rem Snake auf dem RAM starten (spielt sich selbst, Strg+C beendet).
setlocal
cd /d "%~dp0"
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
if exist %BLENDER% (
    %BLENDER% snake.py %*
) else (
    python snake.py %*
)
if errorlevel 1 pause
