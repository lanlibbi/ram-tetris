#!/usr/bin/env python3
"""Startet das im Dashboard gewählte Spiel — und passt auf, dass es weiterläuft.

Zwei Dinge, die hier gelöst werden:

1. **Absturz/Stillstand:** die Aufgabe hat eine feste Kommandozeile, also kann sie nicht auf
   Fehler reagieren. Dieser Starter startet das Spiel als Kindprozess, schreibt dessen Ausgabe in
   `ram-log.txt` und startet es neu, wenn es stirbt (mit Wartezeit, damit es keine Schleife gibt).

2. **Fenster:** der Aufruf kommt aus einer Windows-Aufgabe. Damit kein Konsolenfenster im
   Vordergrund auftaucht, wird der Kindprozess ohne Fenster gestartet (CREATE_NO_WINDOW).

Aufruf:  python spielen.py            # startet und überwacht
         python spielen.py --zeigen   # nur sagen, was gestartet würde
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
KONFIG = HIER / "einstellungen.json"
PROTOKOLL = HIER / "ram-log.txt"
AUSGABE = HIER / "ram-ausgabe.txt"
_SPERRDATEI = None


def protokoll(text: str) -> None:
    """Schreibt eine Zeile mit Zeitstempel und hält die Datei klein."""
    zeile = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n"
    try:
        if PROTOKOLL.exists() and PROTOKOLL.stat().st_size > 1_000_000:
            PROTOKOLL.write_text("", encoding="utf-8")
        with PROTOKOLL.open("a", encoding="utf-8") as fh:
            fh.write(zeile)
    except Exception:
        pass


def einstellungen() -> dict:
    if KONFIG.exists():
        try:
            return json.loads(KONFIG.read_text(encoding="utf-8"))
        except Exception as fehler:
            protokoll(f"einstellungen.json nicht lesbar: {fehler}")
    return {}


# Ein Eintrag je Spiel: Skript und wie das Tempo aus den Einstellungen gelesen wird
SPIELE = {
    "snake": ("snake.py", lambda d: ["--fps", str((d.get("snake") or {}).get("fps", 6))]),
    "pong": ("pong.py", lambda d: ["--fps", str((d.get("pong") or {}).get("fps", 8))]),
    "invaders": ("invaders.py", lambda d: ["--fps", str((d.get("invaders") or {}).get("fps", 10))]),
}


def befehl(daten: dict) -> list[str] | None:
    """Welches Spiel soll laufen? None heisst: keins."""
    modus = (daten.get("modus") or "tetris").lower()
    if modus == "aus":
        return None
    if modus in SPIELE:
        skript, tempo = SPIELE[modus]
        return [sys.executable, str(HIER / skript)] + tempo(daten)
    aufnahme = HIER / "recorded" / "ram-lauf2.json"
    return [sys.executable, str(HIER / "ram_tetris.py"), "--replay", str(aufnahme),
            "--loop", "--speed", str(daten.get("speed", 2))]


def sperre_holen():
    """Verhindert zwei Aufsichten nebeneinander.

    Am 14.11.2026 liefen nach einem Task-Neustart zwei Ketten gleichzeitig — beide schrieben auf
    dieselben LEDs. Windows-Dateisperre; auf anderen Systemen gibt es kein msvcrt, dann laeuft es
    ohne Sperre weiter (dort wird das Spiel ohnehin nicht gebraucht).
    """
    global _SPERRDATEI
    try:
        import msvcrt
    except ImportError:
        return True
    try:
        _SPERRDATEI = open(HIER / "spielen.lock", "w")
        msvcrt.locking(_SPERRDATEI.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def main() -> int:
    if not sperre_holen():
        protokoll("Es laeuft bereits eine Aufsicht — dieser Start beendet sich.")
        print("Es laeuft bereits eine Aufsicht.")
        return 0
    daten = einstellungen()
    kommando = befehl(daten)
    if kommando is None:
        protokoll("Modus ist 'aus' — nichts zu starten.")
        print("Modus ist 'aus' — es wird nichts gestartet.")
        return 0

    if "--zeigen" in sys.argv:
        print("Würde starten:", " ".join(kommando[1:]))
        return 0

    ohne_fenster = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    versuche = 0
    while True:
        # Bei jedem Start neu lesen: so greifen Farb- und Modusänderungen nach einem Neustart
        daten = einstellungen()
        kommando = befehl(daten)
        if kommando is None:
            protokoll("Modus auf 'aus' gestellt — Aufsicht beendet.")
            return 0

        versuche += 1
        protokoll(f"Start #{versuche}: {' '.join(kommando[1:])}")
        try:
            with AUSGABE.open("a", encoding="utf-8") as kanal:
                kanal.write(f"\n--- Start {datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
                kanal.flush()
                lauf = subprocess.run(kommando, cwd=HIER, creationflags=ohne_fenster,
                                      stdout=kanal, stderr=subprocess.STDOUT)
            protokoll(f"Ende mit Rückgabewert {lauf.returncode}")
        except Exception as fehler:
            protokoll(f"Start fehlgeschlagen: {fehler!r}")

        if versuche >= 50:
            protokoll("50 Startversuche erreicht — Aufsicht gibt auf.")
            return 1
        time.sleep(min(5 + versuche, 30))


if __name__ == "__main__":
    raise SystemExit(main())
