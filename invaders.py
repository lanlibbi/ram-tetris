#!/usr/bin/env python3
"""Space Invaders auf den RAM-Riegeln.

Feld: 10 Reihen hoch, 4 Spalten breit. Oben ein Block Aliens, unten das eigene Schiff. Das Schiff
schiesst nach oben, die Aliens schiessen nach unten. Wird das Schiff getroffen oder erreichen die
Aliens die untere Reihe, kommt der gemeinsame Verloren-Screen (rot) und der Putz-Wellenlauf
(weiss). Ist der Block abgeräumt, läuft nur der Putzlauf — dann folgt die nächste, schnellere
Welle.

Wie bei den anderen Spielen spielt der Rechner selbst, weil am RAM niemand sitzen kann:

  1. droht ein feindlicher Schuss in der eigenen Spalte, wird ausgewichen,
  2. sonst wird auf die Spalte des tiefsten Aliens gezielt und geschossen.

Aufrufe:
    python invaders.py                # spielt (Endlosschleife)
    python invaders.py --sekunden 30  # nach 30 s aufhören
    python invaders.py --simulate     # nur ASCII im Terminal
    python invaders.py --probe        # nur die Hardware melden
"""

from __future__ import annotations

import argparse
import random
import time

import spielbasis as basis
from spielbasis import LEER

VORGABE = {
    "schiff": (0, 220, 255),        # eigenes Schiff
    "alien": (140, 255, 90),        # Alienblock
    "schuss": (255, 214, 0),        # eigener Schuss
    "alien_schuss": (255, 60, 200), # feindlicher Schuss
}
SCHIFF_REIHE = 9          # unterste Reihe
ALIEN_ZEILEN = 2          # wie viele Reihen der Block hoch ist
SCHUSS_TAKT = 2           # alle n Züge rückt der eigene Schuss weiter
ALIEN_SCHUSS_TAKT = 26    # alle n Züge feuert ein Alien
# Auf vier Spalten ist ein waagerecht marschierender Block Unsinn: er stösst nach zwei Zügen an
# und steht nach wenigen Sekunden unten. Der Angriff läuft deshalb senkrecht — die Aliens steigen
# Reihe für Reihe herab, das Schiff muss sie vorher abschiessen.
# Gemessen über 20.000 Züge: 121 verlorene Runden und 147 abgeräumte Wellen — das Spiel gewinnt
# also öfter, als es verliert, und zeigt beide Abschlüsse regelmässig (bei 10 Zügen/s etwa alle
# 13–16 Sekunden).
ALIEN_ABSTIEG = 34        # alle n Züge eine Reihe tiefer (wird je Welle schneller)
SCHIFF_SCHUSS_TAKT = 4    # alle n Züge ein neuer Schuss


class Invaders:
    def __init__(self, reihen: int, spalten: int, saat: int | None = None, welle: int = 1):
        self.reihen = reihen
        self.spalten = spalten
        self.rng = random.Random(saat)
        self.welle = welle
        self.schiff = spalten // 2
        self.aliens = [(r, c) for r in range(1, ALIEN_ZEILEN + 1) for c in range(spalten)]
        self.schuesse: list[list[int]] = []        # [Reihe, Spalte], wandern nach oben
        self.alien_schuesse: list[list[int]] = []  # wandern nach unten
        self.zug = 0
        self.tot = False
        self.gewonnen = False
        self.abschuesse = 0
        self.blitz = {}                            # (Reihe, Spalte) -> Züge, die es noch blitzt

    # -- Hilfen ------------------------------------------------------------
    def _abstieg(self) -> int:
        # je Welle etwas schneller, aber nie hektisch
        return max(8, ALIEN_ABSTIEG - (self.welle - 1) * 3)

    def _schusstakt(self) -> int:
        return max(8, ALIEN_SCHUSS_TAKT - (self.welle - 1) * 3)

    # -- Steuerung ---------------------------------------------------------
    def _gefahr(self, spalte: int) -> bool:
        """Kommt ein feindlicher Schuss in dieser Spalte auf uns zu?"""
        for r, c in self.alien_schuesse:
            if c == spalte and SCHIFF_REIHE - r <= 4:
                return True
        return False

    def schiff_bewegen(self) -> None:
        # 1. ausweichen
        if self._gefahr(self.schiff):
            for schritt in (-1, 1):
                ziel = self.schiff + schritt
                if 0 <= ziel < self.spalten and not self._gefahr(ziel):
                    self.schiff = ziel
                    return
        # 2. auf das tiefste Alien zielen
        if self.aliens:
            tiefstes = max(self.aliens, key=lambda a: (a[0], -abs(a[1] - self.schiff)))
            if tiefstes[1] != self.schiff:
                self.schiff += 1 if tiefstes[1] > self.schiff else -1

    def schiessen(self) -> None:
        # nicht schiessen, wenn schon ein eigener Schuss unterwegs ist
        if self.schuesse:
            return
        if self.zug % SCHIFF_SCHUSS_TAKT != 0:
            return
        self.schuesse.append([SCHIFF_REIHE - 1, self.schiff])

    # -- Schritt -----------------------------------------------------------
    def schritt(self) -> None:
        if self.tot or self.gewonnen:
            return
        self.zug += 1

        # Blitze abbauen
        for zelle in list(self.blitz):
            self.blitz[zelle] -= 1
            if self.blitz[zelle] <= 0:
                del self.blitz[zelle]

        self.schiff_bewegen()
        self.schiessen()

        # eigener Schuss wandert nach oben
        if self.zug % SCHUSS_TAKT == 0:
            neue = []
            for r, c in self.schuesse:
                r -= 1
                if r < 0:
                    continue
                treffer = next((a for a in self.aliens if a == (r, c)), None)
                if treffer:
                    self.aliens.remove(treffer)
                    self.abschuesse += 1
                    self.blitz[(r, c)] = 2
                    continue
                neue.append([r, c])
            self.schuesse = neue

        # Aliens steigen eine Reihe herab
        if self.zug % self._abstieg() == 0 and self.aliens:
            self.aliens = [(r + 1, c) for r, c in self.aliens]
            if any(r >= SCHIFF_REIHE for r, _ in self.aliens):
                self.tot = True
                return

        # Aliens feuern
        if self.zug % self._schusstakt() == 0 and self.aliens:
            r, c = self.rng.choice(self.aliens)
            self.alien_schuesse.append([r + 1, c])

        # feindliche Schüsse wandern nach unten
        neue_alien = []
        for r, c in self.alien_schuesse:
            r += 1
            if r >= SCHIFF_REIHE:
                if c == self.schiff:
                    self.tot = True
                    return
                continue
            neue_alien.append([r, c])
        self.alien_schuesse = neue_alien

        if not self.aliens:
            self.gewonnen = True

    # -- Bild --------------------------------------------------------------
    def bild(self, farben: dict):
        bild = [[LEER] * self.spalten for _ in range(self.reihen)]
        for r, c in self.aliens:
            if 0 <= r < self.reihen and 0 <= c < self.spalten:
                bild[r][c] = farben["alien"]
        for (r, c), rest in self.blitz.items():
            if 0 <= r < self.reihen and 0 <= c < self.spalten:
                bild[r][c] = basis.abdunkeln(farben["schuss"], 0.5 + 0.5 * min(rest, 2) / 2)
        for r, c in self.schuesse:
            if 0 <= r < self.reihen and 0 <= c < self.spalten:
                bild[r][c] = farben["schuss"]
        for r, c in self.alien_schuesse:
            if 0 <= r < self.reihen and 0 <= c < self.spalten:
                bild[r][c] = farben["alien_schuss"]
        bild[SCHIFF_REIHE][self.schiff] = farben["schiff"]
        return bild

    def ascii(self) -> str:
        probe = {"schiff": "S", "alien": "A", "schuss": "|", "alien_schuss": "v"}
        bild = self.bild(probe)
        return " | ".join("".join(z if z != LEER else "." for z in zeile) for zeile in bild)


def spielen(hardware, reihen: int, spalten: int, fps: float, sekunden: float | None,
            saat: int | None, zeige_ascii: bool = False) -> dict:
    basis.marke_setzen("invaders")
    farben = basis.farben_fuer("invaders", VORGABE)
    fps = farben.get("_fps", fps)
    takt = 1.0 / max(fps, 0.5)
    spiel = Invaders(reihen, spalten, saat)
    start = time.time()
    runden, wellen, bester = 0, 0, 0
    try:
        while True:
            if spiel.tot:
                runden += 1
                bester = max(bester, spiel.abschuesse)
                print(f"Runde {runden} vorbei · {spiel.abschuesse} Aliens · Welle {spiel.welle}")
                basis.verloren_und_putzen(hardware, reihen, spalten, farben, takt)
                spiel = Invaders(reihen, spalten, None if saat is None else saat + runden,
                                 welle=1)
                continue
            if spiel.gewonnen:
                wellen += 1
                bester = max(bester, spiel.abschuesse)
                print(f"Welle {spiel.welle} abgeräumt · {spiel.abschuesse} Aliens")
                # Sieg: nur der Putzlauf, kein roter Blitz
                basis.putzen(hardware, reihen, spalten, farben, takt)
                spiel = Invaders(reihen, spalten, None, welle=spiel.welle + 1)
                spiel.abschuesse = bester
                continue

            spiel.schritt()
            if hardware:
                basis.schreibe_bild(hardware, spiel.bild(farben))
                if basis.zu_viele_fehlschlaege():
                    basis.protokoll("40 Bilder in Folge nicht geschrieben — Neustart durch spielen.py")
                    raise SystemExit(4)
            if zeige_ascii:
                print(f"{spiel.abschuesse:3d}  {spiel.ascii()}", flush=True)
            if sekunden and (time.time() - start) >= sekunden:
                break
            time.sleep(takt)
    except KeyboardInterrupt:
        print("\nabgebrochen")
    return {"runden": runden, "wellen": wellen, "bester": max(bester, spiel.abschuesse)}


def main() -> int:
    p = argparse.ArgumentParser(description="Space Invaders auf den RAM-LEDs (spielt sich selbst).")
    p.add_argument("--fps", type=float, default=10.0, help="Züge je Sekunde (Vorgabe 10)")
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
        basis.marke_setzen("invaders")
        basis.protokoll(f"gestartet · {hardware.probe()} · fps={args.fps}")
        if args.probe:
            return 0
        basis.watchdog_starten()

    ergebnis = spielen(hardware, reihen, spalten, args.fps, args.sekunden, args.saat,
                       zeige_ascii=args.ascii or args.simulate)
    print(f"Runden: {ergebnis['runden']} · Wellen geschafft: {ergebnis['wellen']} · "
          f"beste Abschüsse: {ergebnis['bester']}")
    if hardware:
        basis.schreibe_bild(hardware, [[LEER] * spalten for _ in range(reihen)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
