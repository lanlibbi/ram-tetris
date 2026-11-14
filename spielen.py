#!/usr/bin/env python3
"""Startet das Spiel, das im Dashboard gewählt ist.

Warum diese Zwischenschicht: die Windows-Aufgabe hat eine feste Kommandozeile. Ohne diesen
Starter müsste man beim Umschalten die Aufgabe neu anlegen. Jetzt liest der Starter bei jedem
Start `einstellungen.json` und entscheidet selbst — Umschalten heisst nur: Aufgabe neu starten.

Aufruf:  python spielen.py           # startet, was in einstellungen.json unter "modus" steht
         python spielen.py --zeigen   # nur sagen, was gestartet würde
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
KONFIG = HIER / "einstellungen.json"


def einstellungen() -> dict:
    daten = {}
    if KONFIG.exists():
        try:
            daten = json.loads(KONFIG.read_text(encoding="utf-8"))
        except Exception:
            daten = {}
    return daten


def befehl(daten: dict) -> list[str] | None:
    modus = (daten.get("modus") or "tetris").lower()
    if modus == "aus":
        return None
    if modus == "snake":
        fps = (daten.get("snake") or {}).get("fps", 6)
        return [sys.executable, str(HIER / "snake.py"), "--fps", str(fps)]
    speed = daten.get("speed", 2)
    aufnahme = HIER / "recorded" / "ram-lauf2.json"
    return [sys.executable, str(HIER / "ram_tetris.py"), "--replay", str(aufnahme),
            "--loop", "--speed", str(speed)]


def main() -> int:
    daten = einstellungen()
    kommando = befehl(daten)
    if kommando is None:
        print("Modus ist 'aus' — es wird nichts gestartet.")
        return 0
    print("Modus:", daten.get("modus", "tetris"))
    print("Starte:", " ".join(kommando[1:]))
    if "--zeigen" in sys.argv:
        return 0
    os.chdir(HIER)
    return subprocess.run(kommando).returncode


if __name__ == "__main__":
    raise SystemExit(main())
