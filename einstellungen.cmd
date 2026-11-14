@echo off
rem Fallback zum Nachsehen: fuehrt die Logik sichtbar aus und zeigt bei Fehlern das Protokoll.
rem Fuer den Alltag die Verknuepfung "RAM-Tetris Einstellungen" nehmen - die oeffnet ohne Fenster.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0einstellungen.ps1"
if errorlevel 1 (
    echo.
    echo --- Protokoll ---
    type "%TEMP%\ram-games-einstellungen.log"
    echo.
    pause
)
