#!/usr/bin/env python3
"""RAM-Tetris — ein Spiel auf den RGB-LEDs der Arbeitsspeicher-Riegel.

Vorbild ist das Video "Mein RAM spielt Tetris, ganz ohne mich" von Bastel Nerd: Steine
fallen von oben in die Spalten, treffen aufeinander, und wenn sich in einer Reihe drei
gleiche Farben berühren, verschwinden sie und der Rest rutscht nach. Läuft das Feld voll,
ist die Runde vorbei und es beginnt von vorn.

Angesteuert wird OpenRGB über dessen SDK-Schnittstelle (TCP, Vorgabe 127.0.0.1:6742).
OpenRGB muss laufen und die Riegel erkannt haben; iCUE darf sie gleichzeitig nicht
steuern. Es wird nichts installiert — OpenRGB läuft portabel, und als Python-Interpreter
tut es Blenders eigener.

Aufrufe:
    ram_tetris.py --probe                  Geräte und LED-Zahlen zeigen, nichts ändern
    ram_tetris.py --simulate --steine 60   Spiel im Terminal (ASCII), ohne Hardware
    ram_tetris.py --static FF8800          statische Farbe setzen
    ram_tetris.py --play                   spielen
    ram_tetris.py --record lauf.json       spielen und dabei jede Frame aufzeichnen
    ram_tetris.py --replay lauf.json       Aufzeichnung abspielen
    ram_tetris.py --replay lauf.json --loop    ... endlos, alle N Sekunden von vorn
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "vendor"))   # damit "openrgb" als Paket importierbar ist

# Drei Farben, nicht fünf: bei nur zwei Reihen Höhe muss eine Dreierkette oft genug
# zustande kommen, sonst ist das Feld voll, bevor das Spiel in Gang kommt (gemessen:
# mit fünf Farben war nach acht Steinen Schluss, ohne einen einzigen Treffer).
# Farbwahl des Nutzers (13.11.2026): gelb, dunkelblau, rot, weiß.
PALETTE = [
    ("Y", (255, 210, 0)),        # gelb
    ("B", (10, 40, 170)),        # dunkelblau
    ("R", (255, 30, 30)),        # rot
    ("W", (255, 255, 255)),      # weiß
    ("G", (30, 200, 80)),        # grün (nur mit --farben 5)
    ("P", (180, 50, 255)),       # lila (nur mit --farben 6)
]
# Formen aus mehreren Zellen — wie im Vorbildvideo: es kommen Muster von oben, nicht
# einzelne Punkte. Koordinaten als (dReihe, dSpalte), Ursprung oben links.
FORMEN = {
    "O":     [(0, 0), (0, 1), (1, 0), (1, 1)],
    "I2":    [(0, 0), (1, 0)],
    "I3":    [(0, 0), (1, 0), (2, 0)],
    "L":     [(0, 0), (1, 0), (1, 1)],
    "J":     [(0, 1), (1, 0), (1, 1)],
    "S":     [(0, 1), (0, 2), (1, 0), (1, 1)],
    "T":     [(0, 0), (0, 1), (0, 2), (1, 1)],
    "Punkt": [(0, 0)],
}
# Wird beim Start überschrieben, wenn --palette angegeben ist.
PALETTE_AKTIV = PALETTE

# Gewichtung: kleine Formen häufiger, sonst läuft das schmale Feld zu schnell voll.
FORMEN_GEWICHT = ["I2", "I2", "I3", "L", "L", "J", "J", "O", "T", "S", "Punkt", "Punkt"]

LEER = (0, 0, 0)
AUS = (0, 0, 0)
WEISS = (255, 255, 255)
ROT = (255, 0, 0)

# Farben für die Sondersequenzen — über die Konfigurationsdatei änderbar (Einstellungsfenster).
FARBE_VERLOREN = ROT      # Blinken, wenn die Runde verloren ist
FARBE_WELLE = WEISS       # die Putz-Wellen beim Neustart


# ---------------------------------------------------------------------------
# Spielfeld
# ---------------------------------------------------------------------------
class Feld:
    """Reihen × Spalten. Reihe 0 ist oben, die letzte Reihe unten."""

    def __init__(self, reihen: int, spalten: int):
        self.reihen = reihen
        self.spalten = spalten
        self.gitter = [[None] * spalten for _ in range(reihen)]

    def tiefste_freie(self, spalte: int) -> int | None:
        for r in range(self.reihen - 1, -1, -1):
            if self.gitter[r][spalte] is None:
                return r
        return None

    def freie_spalten(self) -> list[int]:
        return [s for s in range(self.spalten) if self.gitter[0][s] is None]

    def treffer(self, reihe: int, mindest: int = 3) -> list[int]:
        """Spalten einer waagerechten Kette gleicher Farbe (>= mindest)."""
        treffer: list[int] = []
        s = 0
        while s < self.spalten:
            farbe = self.gitter[reihe][s]
            if farbe is None:
                s += 1
                continue
            ende = s
            while ende + 1 < self.spalten and self.gitter[reihe][ende + 1] == farbe:
                ende += 1
            if ende - s + 1 >= mindest:
                treffer.extend(range(s, ende + 1))
            s = ende + 1
        return treffer

    def treffer_senkrecht(self, spalte: int, mindest: int = 3) -> list[int]:
        """Reihen einer senkrechten Kette gleicher Farbe in dieser Spalte.

        Nötig, weil das Feld nur vier Spalten breit ist: eine waagerechte Dreierkette
        kommt dort so selten zustande, dass nie etwas verschwindet (Rückmeldung
        13.11.2026: "es werden keine Farben gelöscht").
        """
        treffer: list[int] = []
        r = 0
        while r < self.reihen:
            farbe = self.gitter[r][spalte]
            if farbe is None:
                r += 1
                continue
            ende = r
            while ende + 1 < self.reihen and self.gitter[ende + 1][spalte] == farbe:
                ende += 1
            if ende - r + 1 >= mindest:
                treffer.extend(range(r, ende + 1))
            r = ende + 1
        return treffer

    def alle_treffer(self) -> list[tuple[int, list[int], str]]:
        """(Reihe, Spalten, Richtung) für jede waagerechte Kette."""
        return [(r, t, "waagerecht") for r in range(self.reihen) if (t := self.treffer(r))]

    def leeren(self, reihe: int, spalten: list[int]) -> None:
        for s in spalten:
            self.gitter[reihe][s] = None

    def nachrutschen(self) -> None:
        """Alles, was über einem Loch steht, fällt eine Reihe tiefer."""
        for s in range(self.spalten):
            ziel = self.reihen - 1
            for r in range(self.reihen - 1, -1, -1):
                if self.gitter[r][s] is not None:
                    if r != ziel:
                        self.gitter[ziel][s] = self.gitter[r][s]
                        self.gitter[r][s] = None
                    ziel -= 1

    def voll(self) -> bool:
        """Verloren, sobald EINE Leiste oben angekommen ist.

        Vorher mussten alle Spalten gleichzeitig voll sein — dadurch lief das Spiel viel zu
        lange weiter, obwohl ein Riegel längst bis oben zugebaut war (Wunsch 13.11.2026).
        """
        return any(self.gitter[0][s] is not None for s in range(self.spalten))

    def volle_spalte(self) -> int | None:
        for s in range(self.spalten):
            if self.gitter[0][s] is not None:
                return s
        return None

    def farben(self) -> list[list[tuple[int, int, int]]]:
        return [[z if z is not None else LEER for z in reihe] for reihe in self.gitter]


# ---------------------------------------------------------------------------
# Hardware: OpenRGB
# ---------------------------------------------------------------------------
class Hardware:
    """Eine Reihe je Riegel — oder zwei Hälften eines Geräts."""

    def __init__(self, host: str, port: int, muster: str, reihen: int):
        from openrgb.orgb import OpenRGBClient    # vendor/openrgb
        from openrgb.utils import RGBColor

        self.RGBColor = RGBColor
        self.client = OpenRGBClient(address=host, port=port, name="ram-tetris")
        geraete = [g for g in self.client.devices if muster.lower() in (g.name or "").lower()]
        if not geraete:
            geraete = list(self.client.devices)
        if not geraete:
            raise SystemExit("OpenRGB meldet kein Gerät. Läuft OpenRGB, und sind die Riegel erkannt?")

        self.ziele = []
        if len(geraete) >= reihen:
            for g in geraete[:reihen]:
                g.set_custom_mode()
                self.ziele.append((g, 0, len(g.leds)))
        else:
            g = geraete[0]
            g.set_custom_mode()
            pro = max(1, len(g.leds) // reihen)
            for i in range(reihen):
                self.ziele.append((g, i * pro, pro))
        self.spalten = min(a for _, _, a in self.ziele)

    def zeige(self, zeilen: list[list[tuple[int, int, int]]]) -> None:
        for (geraet, offset, anzahl), farben in zip(self.ziele, zeilen):
            bild = list(geraet.colors)
            for i in range(anzahl):
                c = farben[i] if i < len(farben) else LEER
                bild[offset + i] = self.RGBColor(*c)
            geraet.set_colors(bild, fast=True)

    def probe(self) -> str:
        zeilen = []
        for g in self.client.devices:
            zonen = ", ".join(f"{z.name}:{len(z.leds)}" for z in g.zones) or "—"
            modi = ", ".join(m.name for m in getattr(g, "modes", [])[:4]) or "—"
            zeilen.append(f"  {g.name}\n      {len(g.leds)} LEDs · Zonen {zonen}\n      Modi: {modi}")
        return "\n".join(zeilen)


# ---------------------------------------------------------------------------
# Hardware über das iCUE-SDK (der Weg mit den RAM-Riegeln)
# ---------------------------------------------------------------------------
class HardwareIcue:
    """Bildet das Spielfeld auf die LED-Positionen ab.

    iCUE meldet die Speichermodule als 4 Spalten (x) mit je 10 LEDs (y) — die Riegel
    stehen in seinem Modell senkrecht. Aus den Koordinaten wird die Zuordnung
    (Reihe, Spalte) -> LED-Kennung gebaut, statt sie zu raten.
    """

    def __init__(self, muster: str = "VENGEANCE", typ: int = 0x0080):
        import icue_sdk

        self.sdk = icue_sdk.Sdk()
        zustand = self.sdk.verbinde()
        if not self.sdk.verbunden:
            raise SystemExit("iCUE-SDK nicht verbunden: " + zustand)
        self.geraet = next((g for g in self.sdk.geraete()
                            if g["typ"] == typ and muster.lower() in g["modell"].lower()), None)
        if not self.geraet:
            raise SystemExit(f"Kein Gerät {muster!r} vom Typ {typ:#x} gefunden.")
        print("Kontrolle:", self.sdk.kontrolle(self.geraet))
        positionen = self.sdk.positionen(self.geraet)
        if not positionen:
            raise SystemExit("Keine LED-Positionen — ohne Geometrie kein Spielfeld.")
        xs = sorted({round(p["x"], 1) for p in positionen})
        # y aufsteigend = oben zuerst. Vorher war es umgekehrt, dadurch lief das Spiel
        # von unten nach oben (Rückmeldung des Nutzers am 13.11.2026).
        ys = sorted({round(p["y"], 1) for p in positionen})
        self.spalten = len(xs)
        self.reihen = len(ys)
        # (Reihe, Spalte) -> LED-Kennung
        self.karte: dict[tuple[int, int], int] = {}
        for p in positionen:
            s = xs.index(round(p["x"], 1))
            r = ys.index(round(p["y"], 1))
            self.karte[(r, s)] = p["id"]
        print(f"{self.geraet['modell']}: {self.reihen} Reihen × {self.spalten} Spalten "
              f"({len(positionen)} LEDs adressierbar)")

    def zeige(self, zeilen: list[list[tuple[int, int, int]]]) -> None:
        farben = []
        for r in range(self.reihen):
            for s in range(self.spalten):
                kennung = self.karte.get((r, s))
                if kennung is None:
                    continue
                c = zeilen[r][s] if r < len(zeilen) and s < len(zeilen[r]) else LEER
                farben.append((kennung, c))
        # Auf die SDK-Struktur abbilden: Liste von (id, r, g, b)
        self.sdk.setze_farben_raw(farben)

    def probe(self) -> str:
        return f"{self.geraet['modell']} · {self.geraet['leds']} LEDs · {self.geraet['kanaele']} Kanäle"


# ---------------------------------------------------------------------------
# ASCII-Vorschau
# ---------------------------------------------------------------------------
def ascii_bild(feld: Feld, hinweis: str = "") -> str:
    zeichen = {farbe: buchstabe for buchstabe, farbe in PALETTE_AKTIV}
    zeilen = ["".join(zeichen.get(z, "?") if z else "." for z in reihe) for reihe in feld.gitter]
    return (f"[{hinweis}] " if hinweis else "") + "  /  ".join(zeilen)


# ---------------------------------------------------------------------------
# Spiel
# ---------------------------------------------------------------------------
class Spiel:
    def __init__(self, reihen: int, spalten: int, farbzahl: int, rng: random.Random, still: bool = False):
        self.feld = Feld(reihen, spalten)
        self.palette = PALETTE_AKTIV[:farbzahl] if farbzahl else PALETTE_AKTIV
        self.rng = rng
        self.still = still
        self.frames: list[dict] = []
        self.aufzeichnen = False
        self.steine = 0
        self.punkte = 0
        self.serien = 0

    # -- Ausgabe ---------------------------------------------------------
    def _zeigen(self, hardware: Hardware | None, bild, hinweis: str, dauer: float) -> None:
        if hardware:
            hardware.zeige(bild)
        if self.aufzeichnen:
            self.frames.append({"t": time.time(),
                                "bild": [[list(c) for c in reihe] for reihe in bild],
                                "hinweis": hinweis})
        if dauer > 0:
            time.sleep(dauer)

    def _leer(self):
        return [[LEER] * self.feld.spalten for _ in range(self.feld.reihen)]

    @staticmethod
    def _dimmen(bild, anteil: float):
        """Bild mit einem Bruchteil der Helligkeit."""
        return [[tuple(int(k * anteil) for k in zelle) for zelle in reihe] for reihe in bild]

    # Abfall der Welle nach Abstand zur Bandmitte: Mitte voll, Flanken schwächer.
    WELLE_VERLAUF = {0: 1.0, 1: 0.55, 2: 0.22}

    def _welle_senkrecht(self, mitte: int):
        """Waagerechte Bande, die senkrecht durchläuft."""
        bild = self._leer()
        for r in range(self.feld.reihen):
            anteil = self.WELLE_VERLAUF.get(abs(r - mitte), 0.0)
            if anteil:
                bild[r] = [tuple(int(k * anteil) for k in FARBE_WELLE) for _ in range(self.feld.spalten)]
        return bild

    def _welle_quer(self, mitte: int, rueckwaerts: bool = False):
        """Senkrechte Bande, die waagerecht durchläuft."""
        bild = self._leer()
        for s in range(self.feld.spalten):
            anteil = self.WELLE_VERLAUF.get(abs(s - mitte), 0.0)
            if anteil:
                spalte = tuple(int(k * anteil) for k in FARBE_WELLE)
                for r in range(self.feld.reihen):
                    bild[r][s] = spalte
        return bild

    # -- ein Stein -------------------------------------------------------
    @staticmethod
    def _frei(feld, form, reihe: int, spalte: int) -> bool:
        for dr, dc in form:
            r, s = reihe + dr, spalte + dc
            if not (0 <= r < feld.reihen and 0 <= s < feld.spalten):
                return False
            if feld.gitter[r][s] is not None:
                return False
        return True

    def _landet(self, feld, form, spalte: int) -> int | None:
        """Tiefste Reihe, in der die Form in dieser Spalte Platz hat."""
        if not self._frei(feld, form, 0, spalte):
            return None
        r = 0
        while self._frei(feld, form, r + 1, spalte):
            r += 1
        return r

    def stein(self, hardware: Hardware | None, takt: float) -> bool:
        feld = self.feld
        offen = feld.freie_spalten()
        if not offen:
            return False

        # Form wählen, die in die freie Breite passt
        name = self.rng.choice(FORMEN_GEWICHT)
        form = FORMEN[name]
        breite = max(dc for _, dc in form) + 1
        passend = [c for c in range(feld.spalten - breite + 1)
                   if self._landet(feld, form, c) is not None]
        if not passend:
            return False
        spalte = self.rng.choice(passend)
        buchstabe, farbe = self.rng.choice(self.palette)
        ziel = self._landet(feld, form, spalte)
        if ziel is None:
            return False

        # Fall animieren: die ganze Form wandert von oben bis zur Landeposition
        for r in range(0, ziel + 1):
            bild = feld.farben()
            for dr, dc in form:
                if 0 <= r + dr < feld.reihen and 0 <= spalte + dc < feld.spalten:
                    bild[r + dr][spalte + dc] = farbe
            self._zeigen(hardware, bild, f"fallen:{name}", takt)
        for dr, dc in form:
            feld.gitter[ziel + dr][spalte + dc] = farbe
        self.steine += 1

        # Treffer auflösen, bis nichts mehr passt — auch in der oberen Reihe
        while True:
            # Waagerecht UND senkrecht prüfen. Bei vier Spalten ist die waagerechte
            # Dreierkette zu selten — ohne die senkrechte Prüfung passiert nie etwas.
            waagerecht = feld.alle_treffer()
            senkrecht = [(s, z) for s in range(feld.spalten)
                         if (z := feld.treffer_senkrecht(s))]
            if not waagerecht and not senkrecht:
                break
            summe = sum(len(t) for _, t, _ in waagerecht) + sum(len(z) for _, z in senkrecht)
            # Aufblitzen vor dem Auflösen. Ist Weiß selbst eine Spielfarbe, wird stattdessen
            # dunkel geblitzt — sonst sähe ein Treffer aus wie ein weißer Stein.
            blitz = AUS if any(c == WEISS for _, c in self.palette) else WEISS
            for _ in range(2):
                hell = [list(reihe) for reihe in feld.farben()]
                for r, spalten, _ in waagerecht:
                    for s in spalten:
                        hell[r][s] = blitz
                for s, zeilen in senkrecht:
                    for r in zeilen:
                        hell[r][s] = blitz
                self._zeigen(hardware, hell, "treffer", takt * 1.2)
                self._zeigen(hardware, feld.farben(), "", takt * 0.8)
            for r, spalten, _ in waagerecht:
                feld.leeren(r, spalten)
            for s, zeilen in senkrecht:
                for r in zeilen:
                    feld.gitter[r][s] = None
            self.punkte += summe
            self.serien += 1
            self._zeigen(hardware, feld.farben(), f"{summe} weg", takt * 1.5)
            feld.nachrutschen()
            self._zeigen(hardware, feld.farben(), "rutschen", takt * 1.5)
            if not self.still:
                print(ascii_bild(feld, f"{buchstabe}->{spalte + 1}: {summe} weg"))

        if not self.still:
            print(ascii_bild(feld, f"{buchstabe}->{spalte + 1}"))
        return not feld.voll()

    def runde_zu_ende(self, hardware: Hardware | None, takt: float) -> None:
        # 1. Verloren: alles rot, dreimal blinken
        for _ in range(3):
            self._zeigen(hardware, [[FARBE_VERLOREN] * self.feld.spalten for _ in self.feld.gitter],
                         "vorbei", takt * 2)
            self._zeigen(hardware, self._leer(), "", takt * 0.6)
        # Wisch-Tempo: 0.5 Takte je Schritt.
        schritt = takt * 0.5

        # Kein Vollbild-Aufhellen mehr (sah falsch aus), sondern eine Welle mit weichem Rand
        # wie die Wellen-Animation in iCUE: eine helle Bande läuft durch, ihre Flanken
        # leuchten schwächer und laufen ins Dunkel aus. WELLE_VERLAUF ist der Abfall nach
        # Abstand zur Bandmitte.
        for g in range(-2, self.feld.reihen + 2):
            self._zeigen(hardware, self._welle_senkrecht(g), "welle-senkrecht", schritt)
        for g in range(-2, self.feld.spalten + 2):
            self._zeigen(hardware, self._welle_quer(g, rueckwaerts=False), "welle-quer", schritt)
        for g in range(self.feld.spalten + 1, -3, -1):
            self._zeigen(hardware, self._welle_quer(g, rueckwaerts=True), "welle-zurueck", schritt)
        # 5. Kurz dunkel bleiben, bevor die neue Runde beginnt
        self._zeigen(hardware, self._leer(), "pause", takt * 8)
        if not self.still:
            print(f"--- Runde vorbei: {self.steine} Steine, {self.punkte} Punkte, "
                  f"{self.serien} Ketten — neu ---")
        self.feld = Feld(self.feld.reihen, self.feld.spalten)


# ---------------------------------------------------------------------------
# Aufzeichnung abspielen
# ---------------------------------------------------------------------------
def wiedergeben(datei: str, hardware: Hardware | None, schleife: bool, speed: float, simulate: bool) -> None:
    daten = json.loads(open(datei, encoding="utf-8").read())
    frames = daten.get("frames") or []
    if not frames:
        raise SystemExit("Die Aufzeichnung ist leer.")
    dauer = (frames[-1]["t"] - frames[0]["t"]) / max(speed, 0.01)
    print(f"{len(frames)} Frames · {dauer:.1f} s je Durchlauf"
          + (" · Endlosschleife (Strg+C beendet)" if schleife else ""))
    try:
        while True:
            start = time.time()
            basis = frames[0]["t"]
            for frame in frames:
                ziel = start + (frame["t"] - basis) / max(speed, 0.01)
                warte = ziel - time.time()
                if warte > 0:
                    time.sleep(warte)
                if hardware:
                    hardware.zeige(frame["bild"])
                elif simulate:
                    print("   ", frame.get("hinweis", ""))
            if not schleife:
                break
    except KeyboardInterrupt:
        print("\nabgebrochen")


def mache_hardware(args):
    """Baut den Zugang zur Beleuchtung: iCUE-SDK (Vorgabe) oder OpenRGB."""
    if args.backend == "icue":
        return HardwareIcue(args.muster if args.muster != "Vengeance" else "VENGEANCE")
    return Hardware(args.host, args.port, args.muster, args.reihen)


def main() -> int:
    p = argparse.ArgumentParser(description="Tetris auf den RGB-LEDs der RAM-Riegel (über OpenRGB)")
    p.add_argument("--backend", choices=["icue", "openrgb"], default="icue",
                   help="icue = Corsair-SDK (RAM-Riegel), openrgb = OpenRGB-SDK")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=6742)
    p.add_argument("--muster", default="Vengeance", help="Gerätename enthält")
    p.add_argument("--reihen", type=int, default=2)
    p.add_argument("--spalten", type=int, default=0, help="0 = aus den LEDs ableiten")
    p.add_argument("--farben", type=int, default=4, help="Anzahl Farben aus der Palette")
    p.add_argument("--palette", metavar="RRGGBB,RRGGBB,...",
                   help="eigene Farben, mit Komma getrennt (überschreibt --farben)")
    p.add_argument("--fps", type=float, default=6.0)
    p.add_argument("--steine", type=int, default=60, help="nur bei --simulate: Anzahl Steine")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--static", metavar="RRGGBB")
    p.add_argument("--play", action="store_true")
    p.add_argument("--record", metavar="DATEI")
    p.add_argument("--replay", metavar="DATEI")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dauer", type=float, default=0, help="nach N Sekunden sauber aufhören (0 = endlos)")
    p.add_argument("--konfig", metavar="DATEI",
                   help="Konfigurationsdatei (Vorgabe: einstellungen.json neben dem Skript)")
    p.add_argument("--runden", type=int, default=0,
                   help="nach N abgeschlossenen Runden aufhören (0 = endlos) — für eine Schleife, "
                        "die auch Verloren-Animation und Wischen enthält")
    args = p.parse_args()

    # Konfigurationsdatei (aus dem Einstellungsfenster): Farben für Formen, Verloren, Wellen
    konfig_pfad = args.konfig or os.path.join(HIER, "einstellungen.json")
    konfig = {}
    if os.path.exists(konfig_pfad):
        try:
            konfig = json.loads(open(konfig_pfad, encoding="utf-8").read())
        except Exception as fehler:
            print(f"Hinweis: {konfig_pfad} ist unlesbar ({fehler}) — es gelten die Vorgaben.")
    global FARBE_VERLOREN, FARBE_WELLE
    if isinstance(konfig.get("verloren"), list) and len(konfig["verloren"]) == 3:
        FARBE_VERLOREN = tuple(konfig["verloren"])
    if isinstance(konfig.get("welle"), list) and len(konfig["welle"]) == 3:
        FARBE_WELLE = tuple(konfig["welle"])
    if not args.palette and isinstance(konfig.get("palette"), list) and len(konfig["palette"]) >= 2:
        args.palette = ",".join(f"{r:02X}{g:02X}{b:02X}"
                                for r, g, b in (tuple(c) for c in konfig["palette"]))

    # Eigene Farben von der Kommandozeile: "FFD200,0A28AA,FF1E1E,FFFFFF"
    palette = PALETTE
    if args.palette:
        roh = [t.strip().lstrip("#") for t in args.palette.replace(";", ",").split(",") if t.strip()]
        eigene = []
        for i, hexwert in enumerate(roh):
            if len(hexwert) != 6:
                raise SystemExit(f"Farbe {hexwert!r} ist keine RRGGBB-Angabe.")
            farbe = tuple(int(hexwert[j:j + 2], 16) for j in (0, 2, 4))
            eigene.append((chr(ord("A") + i % 26), farbe))
        if len(eigene) < 2:
            raise SystemExit("Mindestens zwei Farben angeben.")
        palette = eigene
    global PALETTE_AKTIV
    PALETTE_AKTIV = palette

    if args.probe:
        hardware = mache_hardware(args)
        print("Geräte laut OpenRGB:")
        print(hardware.probe())
        reihen_ = getattr(hardware, "reihen", args.reihen)
        print(f"\nVerwendet: {reihen_} Reihe(n) × {hardware.spalten} Spalten")
        return 0

    if args.static:
        farbe = tuple(int(args.static[i:i + 2], 16) for i in (0, 2, 4))
        hardware = mache_hardware(args)
        reihen_ = getattr(hardware, "reihen", args.reihen)
        hardware.zeige([[farbe] * hardware.spalten for _ in range(reihen_)])
        print(f"{args.static} gesetzt: {reihen_} × {hardware.spalten} LEDs")
        return 0

    if args.replay:
        hardware = None if args.simulate else mache_hardware(args)
        wiedergeben(args.replay, hardware, args.loop, args.speed, args.simulate)
        return 0

    if not (args.play or args.record or args.simulate):
        p.print_help()
        return 1

    hardware = None if args.simulate else mache_hardware(args)
    spalten = args.spalten or (hardware.spalten if hardware else 4)
    reihen = hardware.reihen if hardware else args.reihen
    anzahl = len(PALETTE_AKTIV) if args.palette else max(2, min(args.farben, len(PALETTE_AKTIV)))
    spiel = Spiel(reihen, spalten, anzahl, random.Random(args.seed), still=False)
    spiel.aufzeichnen = bool(args.record)
    takt = 1.0 / args.fps
    print(f"Feld: {reihen} Reihen × {spalten} Spalten, {len(spiel.palette)} Farben. "
          f"Strg+C beendet.")
    start = time.time()
    runden = 0
    try:
        while True:
            if args.dauer and time.time() - start >= args.dauer:
                print(f"nach {args.dauer:.0f} s beendet")
                break
            if not spiel.stein(hardware, takt):
                spiel.runde_zu_ende(hardware, takt)
                runden += 1
                if args.runden and runden >= args.runden:
                    print(f"{runden} Runde(n) abgeschlossen — Aufnahme endet")
                    break
                if args.simulate and spiel.steine >= args.steine:
                    break
            if args.simulate and spiel.steine >= args.steine:
                break
    except KeyboardInterrupt:
        print("\nabgebrochen")
    finally:
        if args.record:
            with open(args.record, "w", encoding="utf-8") as fh:
                json.dump({"frames": spiel.frames, "seed": args.seed,
                           "reihen": args.reihen, "spalten": spalten}, fh)
            dauer = (spiel.frames[-1]["t"] - spiel.frames[0]["t"]) if spiel.frames else 0
            print(f"aufgezeichnet: {args.record} · {len(spiel.frames)} Frames · {dauer:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
