@echo off
rem Startet die Endlosschleife. Farben und Tempo hier anpassen.
rem Farben: --palette RRGGBB,RRGGBB,...   Tempo: --speed 2
set PY=python
cd /d "%~dp0"
"%PY%" ram_tetris.py --replay recorded\ram-lauf2.json --loop --speed 2
if errorlevel 1 pause
