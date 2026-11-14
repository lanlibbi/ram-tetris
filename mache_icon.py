#!/usr/bin/env python3
"""Baut das Programmsymbol `ram-tetris.ico` (ohne fremde Bibliotheken).

Warum von Hand: das Projekt soll nichts nachinstallieren. Ein ICO ist nur ein Kopf plus Bilder;
die Pixel werden hier direkt gerechnet, mit vierfacher Abtastung gegen Treppchen.

Motiv: dieselben vier Farbkacheln wie das Logo auf der Einstellungsseite (Bernstein, Blau, Rot,
Weiss) auf dunklem, abgerundetem Grund.

Aufruf:  python mache_icon.py            # schreibt ram-tetris.ico daneben
         python mache_icon.py --vorschau  # zusätzlich vorschau.png zum Ansehen
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "ram-tetris.ico"

GROESSEN = (16, 24, 32, 48, 64, 128, 256)
KACHELN = (
    (255, 210, 0),      # Bern -- wie Piece 01
    (59, 107, 255),     # Blau
    (255, 59, 59),      # Rot
    (255, 255, 255),    # Weiss
)
HINTERGRUND_OBEN = (32, 38, 50)
HINTERGRUND_UNTEN = (10, 13, 18)
ABTASTUNG = 4           # Kantenglättung durch Mehrfachabtastung


def _im_abgerundeten_rechteck(x: float, y: float, rand: float) -> bool:
    """Punkt in einem abgerundeten Quadrat 0..1 mit Eckenradius `rand`?"""
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        return False
    r = rand
    # Abstand zum nächsten Eckmittelpunkt prüfen
    naechste_x = min(max(x, r), 1.0 - r)
    naechste_y = min(max(y, r), 1.0 - r)
    dx, dy = x - naechste_x, y - naechste_y
    return dx * dx + dy * dy <= r * r


def _farbe_an(x: float, y: float):
    """Farbe (r,g,b,a) an der Stelle x,y im Einheitsquadrat."""
    if not _im_abgerundeten_rechteck(x, y, 0.20):
        return (0, 0, 0, 0)

    # Hintergrund als senkrechter Verlauf
    t = y
    r = int(HINTERGRUND_OBEN[0] * (1 - t) + HINTERGRUND_UNTEN[0] * t)
    g = int(HINTERGRUND_OBEN[1] * (1 - t) + HINTERGRUND_UNTEN[1] * t)
    b = int(HINTERGRUND_OBEN[2] * (1 - t) + HINTERGRUND_UNTEN[2] * t)

    # vier Kacheln, 2x2, mit Rand und Fuge
    rand, fuge = 0.145, 0.028
    feld = (1.0 - 2 * rand - fuge) / 2       # Kantenlänge einer Kachel
    for i in range(4):
        spalte, zeile = i % 2, i // 2
        x0 = rand + spalte * (feld + fuge)
        y0 = rand + zeile * (feld + fuge)
        if x0 <= x <= x0 + feld and y0 <= y <= y0 + feld:
            # leichte Abdunklung nach unten, damit die Kacheln plastisch wirken
            faktor = 1.0 - 0.22 * ((y - y0) / feld)
            f = KACHELN[i]
            return (int(f[0] * faktor), int(f[1] * faktor), int(f[2] * faktor), 255)
    return (r, g, b, 255)


def bild_malen(kante: int) -> list[bytes]:
    """Bild als Zeilen von oben nach unten, je Pixel RGBA."""
    zeilen: list[bytes] = []
    schritt = 1.0 / (kante * ABTASTUNG)
    for py in range(kante):
        zeile = bytearray()
        for px in range(kante):
            sr = sg = sb = sa = 0
            for sy in range(ABTASTUNG):
                for sx in range(ABTASTUNG):
                    x = (px * ABTASTUNG + sx + 0.5) * schritt
                    y = (py * ABTASTUNG + sy + 0.5) * schritt
                    r, g, b, a = _farbe_an(x, y)
                    sr += r * a
                    sg += g * a
                    sb += b * a
                    sa += a
            n = ABTASTUNG * ABTASTUNG
            if sa == 0:
                zeile += bytes((0, 0, 0, 0))
            else:
                zeile += bytes((sr // sa, sg // sa, sb // sa, sa // n))
        zeilen.append(bytes(zeile))
    return zeilen


def als_bmp(zeilen: list[bytes], kante: int) -> bytes:
    """ICO-Bild als 32-Bit-BMP (von unten nach oben, BGRA) samt AND-Maske."""
    kopf = struct.pack("<IiiHHIIiiII", 40, kante, kante * 2, 1, 32, 0, kante * kante * 4, 0, 0, 0, 0)
    pixel = bytearray()
    for zeile in reversed(zeilen):
        for i in range(0, len(zeile), 4):
            r, g, b, a = zeile[i], zeile[i + 1], zeile[i + 2], zeile[i + 3]
            pixel += bytes((b, g, r, a))
    # AND-Maske: 1 Bit je Pixel, Zeilen auf 4 Byte aufgefüllt, hier überall 0 (deckend)
    maskenbreite = ((kante + 31) // 32) * 4
    maske = bytes(maskenbreite * kante)
    return kopf + bytes(pixel) + maske


def als_png(zeilen: list[bytes], kante: int) -> bytes:
    """Einfaches PNG (nur für die Vorschau)."""
    roh = bytearray()
    for zeile in zeilen:
        roh.append(0)           # Filter "keine"
        roh += zeile

    def chunk(art: bytes, daten: bytes) -> bytes:
        return (struct.pack(">I", len(daten)) + art + daten
                + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", kante, kante, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(roh), 9))
            + chunk(b"IEND", b""))


def main() -> int:
    bilder = {}
    for kante in GROESSEN:
        bilder[kante] = bild_malen(kante)

    # ICO-Kopf: reserviert=0, Typ=1, Anzahl
    eintraege = bytearray(struct.pack("<HHH", 0, 1, len(GROESSEN)))
    daten = bytearray()
    versatz = 6 + 16 * len(GROESSEN)
    for kante in GROESSEN:
        roh = als_bmp(bilder[kante], kante)
        seite = 0 if kante >= 256 else kante     # 256 wird als 0 eingetragen
        eintraege += struct.pack("<BBBBHHII", seite, seite, 0, 0, 1, 32, len(roh), versatz)
        daten += roh
        versatz += len(roh)
    ZIEL.write_bytes(bytes(eintraege) + bytes(daten))
    print(f"{ZIEL.name} geschrieben: {ZIEL.stat().st_size} B · Größen {GROESSEN}")

    if "--vorschau" in sys.argv:
        vorschau = HIER / "ram-tetris-vorschau.png"
        vorschau.write_bytes(als_png(bilder[128], 128))
        print("Vorschau:", vorschau)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
