@echo off
rem RAM-Tetris - Einstellungen oeffnen.
rem Doppelklick: startet den lokalen Server (falls er noch nicht laeuft) und oeffnet die Seite.
rem Laeuft der Server schon, wird nur der Browser geoeffnet - kein Port zum Merken.
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PORT=8787
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"

rem --- Python finden -------------------------------------------------------
rem Achtung: unter Windows gibt es eine python.exe im WindowsApps-Ordner, die nur den
rem Microsoft Store oeffnet und trotzdem Erfolg meldet. Deshalb wird geprueft, ob wirklich
rem eine Ausgabe kommt - nicht nur der Rueckgabewert.
set "PY="
for /f "delims=" %%v in ('python -c "print(7)" 2^>nul') do set "PY=python"
if not defined PY (
    if exist %BLENDER% (
        for /f "delims=" %%v in ('%BLENDER% -c "print(7)" 2^>nul') do set "PY=%BLENDER%"
    )
)
if not defined PY (
    echo Python wurde nicht gefunden.
    echo Bitte Python 3 von python.org installieren und "Add Python to PATH" anhaken.
    pause
    exit /b 1
)
echo Interpreter: !PY!

rem --- Laeuft der Server schon? --------------------------------------------
set "PRUEF=powershell -NoProfile -Command \"try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 } catch { exit 1 }\""
%PRUEF%
if not errorlevel 1 (
    echo Server laeuft bereits - oeffne die Seite.
    start "" "http://127.0.0.1:%PORT%/"
    exit /b 0
)

rem --- Server starten ------------------------------------------------------
echo Starte den Einstellungs-Server ...
start "RAM-Tetris Einstellungen" /min cmd /c "!PY! einstellungen.py"
for /l %%i in (1,1,20) do (
    %PRUEF%
    if not errorlevel 1 goto offen
    timeout /t 1 >nul
)
echo Der Server antwortet nicht. Bitte das Fenster "RAM-Tetris Einstellungen" pruefen.
pause
exit /b 1

:offen
start "" "http://127.0.0.1:%PORT%/"
exit /b 0
