@echo off
rem Startet das im Dashboard gewaehlte Spiel. Wird von der Aufgabe "RamLoop" aufgerufen,
rem damit die Aufgabe eine feste, einfach zu pflegende Kommandozeile hat.
cd /d "%~dp0"
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
if exist %BLENDER% (
    %BLENDER% spielen.py
) else (
    python spielen.py
)
