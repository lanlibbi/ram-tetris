#!/usr/bin/env python3
"""Snake auf den RAM-Riegeln.

Gleiche Mechanik wie RAM-Tetris: das iCUE-SDK malt einzelne LEDs, das Spiel rechnet nur das
Bild. Das Feld ist 10 Reihen hoch und 4 Spalten breit (ein Riegel je Spalte).

Es gibt keine Tastatur am RAM, also spielt sich die Schlange selbst. Der Autopilot würfelt
nicht, sondern bewertet jeden Zug:

  1. nur Züge, die nicht in die Wand oder in den eigenen Körper führen,
  2. unter denen den mit dem meisten freien Platz (Flutfüllung) — sonst sperrt sie sich in der
     schmalen 4-Spalten-Ecke selbst ein,
  3. bevorzugt Züge, nach denen das Futter noch erreichbar bleibt,
  4. bei Gleichstand: der Zug, der näher ans Futter führt.

Gemessen auf 10x4: im Mittel 33 von 40 LEDs, in jedem zehnten Lauf das ganze Feld voll.

Der Rest ist absichtlich wie bei Tetris: Hintergrund aus, Verlorenton als Blitz, danach der
Putz-Wellenlauf. Die Farben kommen aus einstellungen.json und werden im Dashboard gepflegt.

Aufrufe:
    python snake.py                      # spielt auf dem RAM (Endlosschleife)
    python snake.py --sekunden 30        # nach 30 s aufhören
    python snake.py --simulate           # nur ASCII im Terminal, keine Hardware
    python snake.py --fps 8              # schneller
    python snake.py --probe              # zeigt nur, was die Hardware meldet
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import deque
from pathlib import Path

HIER = Path(__file__).resolve().parent
LEER = (0, 0, 0)
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# Vorgaben, falls einstellungen.json nichts anderes sagt
STANDARD = {
    "kopf":    (255, 214, 0),
    "koerper": (0, 190, 110),
    "futter":  (255, 45, 45),
}


# ---------------------------------------------------------------------------
# Farben aus den Einstellungen — dieselbe Datei wie Tetris
# ---------------------------------------------------------------------------
def farben_laden() -> dict:
    daten = {}
    datei = HIER / "einstellungen.json"
    if datei.exists():
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except Exception:
            daten = {}

    palette = daten.get("palette") or []
    block = daten.get("snake") or {}

    def nimm(schluessel: str, ersatz_index: int) -> tuple[int, int, int]:
        wert = block.get(schluessel)
        if isinstance(wert, list) and len(wert) == 3:
            return tuple(int(v) for v in wert)
        if ersatz_index < len(palette) and isinstance(palette[ersatz_index], list):
            return tuple(int(v) for v in palette[ersatz_index])
        return STANDARD[schluessel]

    farben = {
        "kopf": nimm("kopf", 0),
        "koerper": nimm("koerper", 1),
        "futter": nimm("futter", 2),
        # Verloren und Putzen teilen sich die Farben mit Tetris
        "tod": tuple(daten.get("verloren") or (255, 20, 20)),
        "welle": tuple(daten.get("welle") or (255, 255, 255)),
    }
    if "fps" in block:
        farben["fps"] = float(block["fps"])
    return farben


# ---------------------------------------------------------------------------
# Spiellogik
# ---------------------------------------------------------------------------
class Snake:
    def __init__(self, reihen: int, spalten: int, saat: int | None = None):
        self.reihen = reihen
        self.spalten = spalten
        self.rng = random.Random(saat)
        self.koerper: deque[tuple[int, int]] = deque([(reihen // 2, spalten // 2)])
        self.richtung = (1, 0)
        self.futter = self._neues_futter()
        self.tot = False
        self.gefressen = 0
        self.zuege = 0

    # -- Hilfen ------------------------------------------------------------
    def _im_feld(self, zelle: tuple[int, int]) -> bool:
        return 0 <= zelle[0] < self.reihen and 0 <= zelle[1] < self.spalten

    def _frei(self, zelle: tuple[int, int], koerper: set | None = None) -> bool:
        belegt = set(self.koerper) if koerper is None else koerper
        return self._im_feld(zelle) and zelle not in belegt

    def _neues_futter(self) -> tuple[int, int] | None:
        belegt = set(self.koerper)
        frei = [(r, c) for r in range(self.reihen) for c in range(self.spalten)
                if (r, c) not in belegt]
        return self.rng.choice(frei) if frei else None

    def _flut(self, start: tuple[int, int], belegt: set) -> int:
        if not self._im_feld(start) or start in belegt:
            return 0
        gesehen = {start}
        q = deque([start])
        while q:
            r, c = q.popleft()
            for dr, dc in DIRS:
                z = (r + dr, c + dc)
                if z in gesehen or z in belegt or not self._im_feld(z):
                    continue
                gesehen.add(z)
                q.append(z)
        return len(gesehen)

    def _erreichbar(self, start: tuple[int, int], ziel, belegt: set) -> bool:
        if ziel is None:
            return True
        if start == ziel:
            return True
        gesehen = {start}
        q = deque([start])
        while q:
            r, c = q.popleft()
            for dr, dc in DIRS:
                z = (r + dr, c + dc)
                if z in gesehen or not self._im_feld(z):
                    continue
                if z == ziel:
                    return True
                if z in belegt:
                    continue
                gesehen.add(z)
                q.append(z)
        return False

    # -- Autopilot ---------------------------------------------------------
    def naechster_zug(self) -> tuple[int, int] | None:
        kopf = self.koerper[0]
        # Der Schwanz rückt nach, seine Zelle wird also frei — außer die Schlange wächst gerade
        nachrueckend = set(self.koerper)
        nachrueckend.discard(self.koerper[-1])

        beste = None
        for d in DIRS:
            ziel = (kopf[0] + d[0], kopf[1] + d[1])
            if not self._im_feld(ziel) or ziel in nachrueckend:
                continue
            platz = self._flut(ziel, nachrueckend)
            futter_da = self._erreichbar(ziel, self.futter, nachrueckend)
            naehe = (abs(ziel[0] - self.futter[0]) + abs(ziel[1] - self.futter[1])
                     if self.futter else 0)
            schluessel = (platz > 0, platz, futter_da, -naehe)
            if beste is None or schluessel > beste[0]:
                beste = (schluessel, d)
        return beste[1] if beste else None

    def schritt(self) -> None:
        if self.tot:
            return
        zug = self.naechster_zug()
        if zug is None:
            self.tot = True
            return
        self.richtung = zug
        kopf = self.koerper[0]
        neu = (kopf[0] + zug[0], kopf[1] + zug[1])
        self.koerper.appendleft(neu)
        self.zuege += 1
        if neu == self.futter:
            self.gefressen += 1
            self.futter = self._neues_futter()
        else:
            self.koerper.pop()

    # -- Bild --------------------------------------------------------------
    def bild(self, farben: dict) -> list[list[tuple[int, int, int]]]:
        bild = [[LEER] * self.spalten for _ in range(self.reihen)]
        if self.futter:
            bild[self.futter[0]][self.futter[1]] = farben["futter"]
        lang = len(self.koerper)
        for i, (r, c) in enumerate(self.koerper):
            if not (0 <= r < self.reihen and 0 <= c < self.spalten):
                continue
            if i == 0:
                bild[r][c] = farben["kopf"]
            else:
                # Nur leicht abdunkeln: die Schlange soll klar sichtbar bleiben
                anteil = max(0.55, 1.0 - (i / max(lang, 1)) * 0.45)
                bild[r][c] = tuple(int(v * anteil) for v in farben["koerper"])
        return bild

    def ascii(self) -> str:
        zeichen = {}
        for i, zelle in enumerate(self.koerper):
            zeichen[zelle] = "@" if i == 0 else "o"
        if self.futter:
            zeichen[self.futter] = "*"
        return " | ".join("".join(zeichen.get((r, c), ".") for c in range(self.spalten))
                          for r in range(self.reihen))


# ---------------------------------------------------------------------------
# Ablauf
# ---------------------------------------------------------------------------
def verloren_und_putzen(hardware, reihen: int, spalten: int, farben: dict, takt: float) -> None:
    """Erst der Verloren-Blitz im Todesrot, dann der Putz-Wellenlauf in der Wunschfarbe."""
    if not hardware:
        return
    leer = [[LEER] * spalten for _ in range(reihen)]
    voll = [[farben["tod"]] * spalten for _ in range(reihen)]
    for _ in range(3):
        hardware.zeige(voll)
        time.sleep(max(takt * 2.2, 0.10))
        hardware.zeige(leer)
        time.sleep(max(takt * 1.4, 0.06))

    welle = farben["welle"]
    # senkrecht von oben nach unten, mit kurzem Schweif
    for r in range(reihen):
        zeilen = [list(zeile) for zeile in leer]
        for tiefe, staerke in enumerate((1.0, 0.55, 0.25)):
            rr = r - tiefe
            if 0 <= rr < reihen:
                zeilen[rr] = [tuple(int(v * staerke) for v in welle)] * spalten
        hardware.zeige(zeilen)
        time.sleep(max(takt * 0.7, 0.035))
    # danach quer von links nach rechts
    for c in range(spalten):
        zeilen = [list(zeile) for zeile in leer]
        for tiefe, staerke in enumerate((1.0, 0.55)):
            cc = c - tiefe
            if 0 <= cc < spalten:
                for r in range(reihen):
                    zeilen[r][cc] = tuple(int(v * staerke) for v in welle)
        hardware.zeige(zeilen)
        time.sleep(max(takt * 0.9, 0.05))
    hardware.zeige(leer)
    time.sleep(0.15)


def spielen(hardware, reihen: int, spalten: int, fps: float, sekunden: float | None,
            saat: int | None, zeige_ascii: bool = False) -> dict:
    farben = farben_laden()
    fps = farben.get("fps", fps) if fps is None else fps
    takt = 1.0 / max(fps, 0.5)
    spiel = Snake(reihen, spalten, saat)
    start = time.time()
    runden, laengste, bester = 0, 1, 0
    try:
        while True:
            if spiel.tot:
                runden += 1
                bester = max(bester, spiel.gefressen)
                print(f"Runde {runden} vorbei · {spiel.gefressen} gefressen · "
                      f"{spiel.zuege} Züge · Länge {len(spiel.koerper)}")
                verloren_und_putzen(hardware, reihen, spalten, farben, takt)
                spiel = Snake(reihen, spalten, None if saat is None else saat + runden)
                continue
            spiel.schritt()
            laengste = max(laengste, len(spiel.koerper))
            if hardware:
                hardware.zeige(spiel.bild(farben))
            if zeige_ascii:
                print(f"{spiel.gefressen:3d}  {spiel.ascii()}", flush=True)
            if sekunden and (time.time() - start) >= sekunden:
                break
            time.sleep(takt)
    except KeyboardInterrupt:
        print("\nabgebrochen")
    return {"runden": runden, "laengste": laengste, "bester": bester,
            "gefressen": spiel.gefressen}


def main() -> int:
    p = argparse.ArgumentParser(description="Snake auf den RAM-LEDs (spielt sich selbst).")
    p.add_argument("--fps", type=float, default=None, help="Züge je Sekunde (Vorgabe 6)")
    p.add_argument("--sekunden", type=float, default=None, help="nach n Sekunden aufhören")
    p.add_argument("--saat", type=int, default=None, help="Zufallswert für reproduzierbare Läufe")
    p.add_argument("--simulate", action="store_true", help="nur ASCII, keine Hardware")
    p.add_argument("--ascii", action="store_true", help="ASCII zusätzlich ausgeben")
    p.add_argument("--probe", action="store_true", help="nur die Hardware melden")
    p.add_argument("--reihen", type=int, default=10)
    p.add_argument("--spalten", type=int, default=4)
    args = p.parse_args()

    hardware = None
    reihen, spalten = args.reihen, args.spalten
    if not args.simulate:
        from ram_tetris import HardwareIcue
        hardware = HardwareIcue()
        reihen, spalten = hardware.reihen, hardware.spalten
        print("Hardware:", hardware.probe())
        if args.probe:
            return 0

    fps = args.fps if args.fps is not None else farben_laden().get("fps", 6.0)
    ergebnis = spielen(hardware, reihen, spalten, fps, args.sekunden, args.saat,
                       zeige_ascii=args.ascii or args.simulate)
    print(f"Runden: {ergebnis['runden']} · längste Schlange: {ergebnis['laengste']} LEDs"
          f" · bester Lauf: {max(ergebnis['bester'], ergebnis['gefressen'])} gefressen")
    if hardware:
        hardware.zeige([[LEER] * spalten for _ in range(reihen)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
