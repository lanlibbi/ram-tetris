#!/usr/bin/env python3
"""Pong auf den RAM-Riegeln.

Das Feld ist 10 Reihen hoch und 4 Spalten breit. Der Ball läuft senkrecht zwischen zwei
Schlagflächen: unten die eigene (2 LEDs breit, vom Rechner geführt), oben die Wand. Jeder
Rückläufer macht den Ball schneller. Geht der Ball unten vorbei, kommt der gemeinsame
Verloren-Screen (rot) und der Putz-Wellenlauf (weiß), dann beginnt eine neue Runde.

Es gibt keine Tastatur am RAM, also spielt der Rechner die Schlagfläche selbst — mit Absicht
nicht perfekt: je länger der Ballwechsel, desto langsamer reagiert sie. Sonst würde das Spiel nie
enden und der Verloren-Screen käme nie zu sehen.

Aufrufe:
    python pong.py                   # spielt (Endlosschleife)
    python pong.py --sekunden 30     # nach 30 s aufhören
    python pong.py --simulate        # nur ASCII im Terminal
    python pong.py --probe           # nur die Hardware melden
"""

from __future__ import annotations

import argparse
import random
import time

import spielbasis as basis
from spielbasis import LEER

VORGABE = {
    "schlaeger": (0, 220, 255),     # Schlagfläche unten
    "ball": (255, 255, 255),        # Ball
    "treffer": (255, 214, 0),       # Aufblitzen beim Treffer / an der Wand
}
SCHLAEGER_BREITE = 2

# Wie gut der Rechner die Schlagfläche führt. Nachjustierbar, damit sich das Spiel nicht
# festsurft: REAKTION_START ist die Trefferwahrscheinlichkeit zu Beginn, sie sinkt mit jedem
# Rückläufer um REAKTION_ABFALL bis auf REAKTION_MIN, und SCHRITT_WEITE begrenzt, wie viele
# Zellen die Schlagfläche je Zug aufholen darf.
REAKTION_START = 0.97
REAKTION_ABFALL = 0.05
REAKTION_MIN = 0.45
SCHRITT_WEITE = 2
# Fehleinschätzung: die Vorhersage ist stabil, deshalb wird der Rechner sonst unfehlbar. Pro
# Ballwechsel verschätzt er sich mit dieser Wahrscheinlichkeit um eine Spalte — sie wächst mit
# der Länge des Ballwechsels, damit lange Wechsel selten bleiben.
# Gemessen über je 20.000 Züge: im Schnitt 12 Rückläufer je Runde, längster 45, kürzester 2;
# eine Runde endet damit alle ~25 Sekunden und der Verloren-Screen kommt regelmässig zu sehen.
FEHLER_START = 0.03
FEHLER_ABFALL = 0.02
FEHLER_MAX = 0.25


class Pong:
    def __init__(self, reihen: int, spalten: int, saat: int | None = None):
        self.reihen = reihen
        self.spalten = spalten
        self.rng = random.Random(saat)
        self.schlaeger = 0                       # linke Zelle der Schlagfläche
        self.ball = [0, self.spalten // 2]       # [Reihe, Spalte]
        self.richtung = [1, 1]                   # [Zeile, Spalte]
        self.wechsel = 0                         # erfolgreiche Rückläufer
        self.tot = False
        self.treffer_blitz = 0
        self.naechster_halt = 0                  # Zähler: wie oft der Ball pro Zug weiterrückt
        self.zug = 0
        self.fehler = 0                          # verschätzt sich um so viele Spalten

    # -- Tempo ---------------------------------------------------------------
    def halte_abstand(self) -> int:
        """Wie viele Züge zwischen zwei Ballschritten liegen (sinkt mit jedem Rückläufer)."""
        return max(0, 1 - self.wechsel // 2)

    # -- Schlagfläche -------------------------------------------------------
    def vorhersage(self) -> int:
        """In welcher Spalte kommt der Ball unten an?

        Ohne diese Vorausschau ist der Rechner chancenlos: er reagiert auf die *jetzige* Spalte,
        der Ball wechselt aber kurz vor dem Auftreffen noch die Spalte (am Rand gleich zweimal).
        """
        r, c = self.ball
        dr, dc = self.richtung
        for _ in range(self.reihen * 6):
            r += dr
            c += dc
            if c < 0 or c >= self.spalten:
                dc = -dc
                c = max(0, min(self.spalten - 1, c + 2 * dc))
            if r < 0:
                dr = 1
                r = 0
            if r >= self.reihen - 1:
                return c
        return c

    def neue_fehlschaetzung(self) -> None:
        """Nach jedem Rückläufer neu würfeln, ob sich die Schlagfläche verschätzt.

        Der Fehler muss zwei Spalten betragen: bei einer Schlagfläche von zwei Zellen bleibt eine
        Spalte daneben folgenlos, weil die Kugel dann trotzdem auf der Kante landet (getestet —
        mit ±1 endete kein einziger Ballwechsel).
        """
        grenze = min(FEHLER_MAX, FEHLER_START + self.wechsel * FEHLER_ABFALL)
        if self.rng.random() < grenze:
            self.fehler = self.rng.choice((-2, 2))
        else:
            self.fehler = 0

    def schlaeger_bewegen(self) -> None:
        ziel = max(0, min(self.spalten - 1, self.vorhersage() + self.fehler))
        # Reaktion lässt nach: anfangs fast immer, mit jedem Rückläufer seltener
        wahrscheinlichkeit = max(REAKTION_MIN, REAKTION_START - self.wechsel * REAKTION_ABFALL)
        if self.rng.random() > wahrscheinlichkeit:
            return
        # steuert die Mitte der Schlagfläche an und darf zwei Zellen je Zug aufholen
        mitte = self.schlaeger + (SCHLAEGER_BREITE - 1) / 2
        if abs(ziel - mitte) <= 0.5:
            return
        schrittweite = SCHRITT_WEITE if abs(ziel - mitte) > 1.5 else 1
        if ziel < mitte:
            self.schlaeger = max(0, self.schlaeger - schrittweite)
        else:
            self.schlaeger = min(self.spalten - SCHLAEGER_BREITE, self.schlaeger + schrittweite)

    # -- Schritt ------------------------------------------------------------
    def schritt(self) -> None:
        if self.tot:
            return
        self.zug += 1
        self.schlaeger_bewegen()
        if self.zug <= self.naechster_halt:
            return
        self.naechster_halt = self.zug + self.halte_abstand()

        if self.treffer_blitz > 0:
            self.treffer_blitz -= 1

        r, c = self.ball
        dr, dc = self.richtung
        r += dr
        c += dc

        # Seitenwände
        if c < 0 or c >= self.spalten:
            dc = -dc
            c = max(0, min(self.spalten - 1, c + 2 * dc))
            self.treffer_blitz = 1

        # obere Wand: dort prallt der Ball ab
        if r < 0:
            dr = 1
            r = 0
            self.treffer_blitz = 1

        # untere Reihe: Schlagfläche oder vorbei
        # Achtung: geprüft wird auf der Reihe, auf der die Schlagfläche *liegt* (reihen-1),
        # nicht eine Reihe darunter — sonst fliegt der Ball durch sie hindurch.
        if r >= self.reihen - 1:
            if self.schlaeger <= c <= self.schlaeger + SCHLAEGER_BREITE - 1:
                dr = -1
                r = self.reihen - 2
                self.wechsel += 1
                self.treffer_blitz = 2
                self.neue_fehlschaetzung()
            else:
                self.tot = True
                self.ball = [self.reihen, c]
                return

        self.ball = [r, c]
        self.richtung = [dr, dc]

    # -- Bild --------------------------------------------------------------
    def bild(self, farben: dict):
        bild = [[LEER] * self.spalten for _ in range(self.reihen)]
        # Schlagfläche
        for i in range(SCHLAEGER_BREITE):
            c = self.schlaeger + i
            if 0 <= c < self.spalten:
                bild[self.reihen - 1][c] = farben["schlaeger"]
        # Ball
        r, c = self.ball
        if 0 <= r < self.reihen and 0 <= c < self.spalten:
            farbe = farben["treffer"] if self.treffer_blitz > 0 else farben["ball"]
            bild[r][c] = farbe
        return bild

    def ascii(self) -> str:
        bild = self.bild({"schlaeger": "S", "ball": "O", "treffer": "+"})
        return " | ".join("".join(z if z != LEER else "." for z in zeile) for zeile in bild)


def spielen(hardware, reihen: int, spalten: int, fps: float, sekunden: float | None,
            saat: int | None, zeige_ascii: bool = False) -> dict:
    basis.marke_setzen("pong")
    farben = basis.farben_fuer("pong", VORGABE)
    fps = farben.get("_fps", fps)
    takt = 1.0 / max(fps, 0.5)
    spiel = Pong(reihen, spalten, saat)
    start = time.time()
    runden, bester = 0, 0
    try:
        while True:
            if spiel.tot:
                runden += 1
                bester = max(bester, spiel.wechsel)
                print(f"Runde {runden} vorbei · {spiel.wechsel} Rückläufer")
                basis.verloren_und_putzen(hardware, reihen, spalten, farben, takt)
                spiel = Pong(reihen, spalten, None if saat is None else saat + runden)
                continue
            spiel.schritt()
            if hardware:
                basis.schreibe_bild(hardware, spiel.bild(farben))
                if basis.zu_viele_fehlschlaege():
                    basis.protokoll("40 Bilder in Folge nicht geschrieben — Neustart durch spielen.py")
                    raise SystemExit(4)
            if zeige_ascii:
                print(f"{spiel.wechsel:3d}  {spiel.ascii()}", flush=True)
            if sekunden and (time.time() - start) >= sekunden:
                break
            time.sleep(takt)
    except KeyboardInterrupt:
        print("\nabgebrochen")
    return {"runden": runden, "bester": max(bester, spiel.wechsel)}


def main() -> int:
    p = argparse.ArgumentParser(description="Pong auf den RAM-LEDs (spielt sich selbst).")
    p.add_argument("--fps", type=float, default=8.0, help="Züge je Sekunde (Vorgabe 8)")
    p.add_argument("--sekunden", type=float, default=None)
    p.add_argument("--saat", type=int, default=None)
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--ascii", action="store_true")
    p.add_argument("--probe", action="store_true")
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
        basis.marke_setzen("pong")
        basis.protokoll(f"gestartet · {hardware.probe()} · fps={args.fps}")
        if args.probe:
            return 0
        basis.watchdog_starten()

    ergebnis = spielen(hardware, reihen, spalten, args.fps, args.sekunden, args.saat,
                       zeige_ascii=args.ascii or args.simulate)
    print(f"Runden: {ergebnis['runden']} · längster Ballwechsel: {ergebnis['bester']}")
    if hardware:
        basis.schreibe_bild(hardware, [[LEER] * spalten for _ in range(reihen)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
