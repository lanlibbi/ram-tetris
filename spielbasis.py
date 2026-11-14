#!/usr/bin/env python3
"""Gemeinsame Basis für die LED-Spiele: Anzeige, Protokoll, Aufsicht, Todes-Sequenz.

Warum ein eigenes Modul: Snake, Pong und Invaders brauchen alle dasselbe — ein Bild auf die
Riegel schreiben, Fehler protokollieren (es gibt kein Fenster, in dem man sie sehen könnte), sich
bei Stillstand selbst beenden und den gemeinsamen Verloren-/Putzlauf abspielen. Dreimal
abgeschrieben wird so etwas gern unterschiedlich falsch.

Alle Spiele lesen ihre Farben aus `einstellungen.json`; Verloren und Putzen sind für alle gleich.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
PROTOKOLL = HIER / "ram-log.txt"
LEER = (0, 0, 0)

_letzter_schreibvorgang = time.time()
_fehlschlaege = 0
_marke = "spiel"


# ---------------------------------------------------------------------------
# Protokoll
# ---------------------------------------------------------------------------
def marke_setzen(name: str) -> None:
    """Name, der vor jeder Protokollzeile steht — sonst ist bei mehreren Spielen unklar, wer schrieb."""
    global _marke
    _marke = name


def protokoll(text: str) -> None:
    """Zeile mit Zeitstempel in ram-log.txt.

    Wichtig: stellt bewusst *nicht* die Watchdog-Uhr. Die hängt am erfolgreichen LED-Schreiben;
    sonst hält der Watchdog ein gesundes Spiel für tot (genau das ist einmal passiert).
    """
    try:
        if PROTOKOLL.exists() and PROTOKOLL.stat().st_size > 1_000_000:
            PROTOKOLL.write_text("", encoding="utf-8")
        with PROTOKOLL.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  [{_marke}] {text}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Anzeige
# ---------------------------------------------------------------------------
def schreibe_bild(hardware, bild) -> bool:
    """Bild setzen und die Watchdog-Uhr stellen. False heisst: die LEDs nehmen nichts mehr an."""
    global _letzter_schreibvorgang, _fehlschlaege
    ok = hardware.zeige_robust(bild, schreibe=protokoll)
    if ok:
        _letzter_schreibvorgang = time.time()
        _fehlschlaege = 0
    else:
        _fehlschlaege += 1
    return ok


def zu_viele_fehlschlaege(grenze: int = 40) -> bool:
    return _fehlschlaege >= grenze


def watchdog_starten(grenze: float = 25.0) -> None:
    """Beendet den Prozess, wenn die LEDs laenger als `grenze` Sekunden stehen.

    Ohne Fenster merkt niemand, dass das Bild steht. Der Starter `spielen.py` startet danach neu.
    """

    def lauf():
        while True:
            time.sleep(5)
            if time.time() - _letzter_schreibvorgang > grenze:
                protokoll(f"Watchdog: {grenze:.0f} s ohne erfolgreichen Schreibvorgang — Neustart")
                os._exit(3)

    threading.Thread(target=lauf, daemon=True).start()


def putzen(hardware, reihen: int, spalten: int, farben: dict, takt: float) -> None:
    """Der Putz-Wellenlauf allein: senkrecht von oben nach unten, dann quer.

    Wird auch nach einem Sieg abgespielt (Welle abgeräumt) — dort ohne den roten Blitz.
    """
    if not hardware:
        return
    leer = [[LEER] * spalten for _ in range(reihen)]
    welle = farben["_welle"]
    for r in range(reihen):
        zeilen = [list(zeile) for zeile in leer]
        for tiefe, staerke in enumerate((1.0, 0.55, 0.25)):
            rr = r - tiefe
            if 0 <= rr < reihen:
                zeilen[rr] = [tuple(int(v * staerke) for v in welle)] * spalten
        schreibe_bild(hardware, zeilen)
        time.sleep(max(takt * 0.7, 0.035))
    for c in range(spalten):
        zeilen = [list(zeile) for zeile in leer]
        for tiefe, staerke in enumerate((1.0, 0.55)):
            cc = c - tiefe
            if 0 <= cc < spalten:
                for r in range(reihen):
                    zeilen[r][cc] = tuple(int(v * staerke) for v in welle)
        schreibe_bild(hardware, zeilen)
        time.sleep(max(takt * 0.9, 0.05))
    schreibe_bild(hardware, leer)
    time.sleep(0.15)


def verloren_und_putzen(hardware, reihen: int, spalten: int, farben: dict, takt: float) -> None:
    """Verloren-Blitz im Todesrot, dann der Putz-Wellenlauf.

    Absichtlich für alle Spiele gleich: erst dreimal alles rot, danach wischen, am Ende dunkel.
    """
    if not hardware:
        return
    leer = [[LEER] * spalten for _ in range(reihen)]
    voll = [[farben["_tod"]] * spalten for _ in range(reihen)]
    for _ in range(3):
        schreibe_bild(hardware, voll)
        time.sleep(max(takt * 2.2, 0.10))
        schreibe_bild(hardware, leer)
        time.sleep(max(takt * 1.4, 0.06))
    putzen(hardware, reihen, spalten, farben, takt)


def abdunkeln(farbe, anteil: float):
    """Farbe anteilig dunkler. Zeichen (in der ASCII-Vorschau) bleiben unverändert."""
    if not isinstance(farbe, (tuple, list)):
        return farbe
    return tuple(int(v * anteil) for v in farbe)


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------
def konfiguration() -> dict:
    datei = HIER / "einstellungen.json"
    if datei.exists():
        try:
            return json.loads(datei.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def farben_fuer(block: str, vorgabe: dict) -> dict:
    """Farben eines Spiels aus `einstellungen.json` holen, mit Vorgaben als Rückfall.

    Liefert zusätzlich `_tod` und `_welle` (für alle Spiele gleich) sowie `_fps`, falls im Block
    gesetzt.
    """
    daten = konfiguration()
    eigen = daten.get(block) or {}
    farben = {k: tuple(v) for k, v in vorgabe.items()}
    for schluessel in vorgabe:
        wert = eigen.get(schluessel)
        if isinstance(wert, list) and len(wert) == 3:
            farben[schluessel] = tuple(int(v) for v in wert)
    farben["_tod"] = tuple(daten.get("verloren") or (255, 20, 20))
    farben["_welle"] = tuple(daten.get("welle") or (255, 255, 255))
    if isinstance(eigen.get("fps"), (int, float)):
        farben["_fps"] = float(eigen["fps"])
    return farben
