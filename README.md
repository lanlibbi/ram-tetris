# RAM-Tetris

Tetris auf den RGB-LEDs der Arbeitsspeicher-Riegel. Formen fallen von oben in die Spalten, drei
gleiche Farben waagerecht oder senkrecht verschwinden und der Rest rutscht nach. Ist eine Leiste
zugebaut, blinkt alles rot, weiße Wellen wischen das Feld sauber, und es geht von vorn los.

**Anleitung: [ANLEITUNG.md](ANLEITUNG.md)** — Einrichtung, Farben ändern, Tempo, Autostart,
Fehlersuche. Ohne Programmierkenntnisse lesbar.

Vorbild ist der Short „Mein RAM spielt Tetris, ganz ohne mich" von **Bastel Nerd**. Dort ist es
laut Beschreibung „gevibe coded", also ein eigenes Programm und kein iCUE-Effekt.

## Der Trick: das iCUE-SDK

iCUE 5 hat keine Kommandozeile — aber es liefert eine SDK-DLL mit, die einzelne LEDs setzen kann.
Damit macht iCUE die Hardware-Arbeit und das Skript setzt nur Farben. Kein zusätzlicher Treiber,
kein OpenRGB, keine Installation.

Die DLL bringt meist schon eine Mainboard-Hersteller-Software mit:

```
C:\Program Files\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll
C:\Program Files\Corsair\Corsair iCUE5 Software\iCUESDK.x64_2019.dll
```

Angesprochen wird sie über `ctypes`, also ohne Compiler und ohne Zusatzpaket. Als Python tut es auch
der Interpreter, den Blender mitbringt.

## Schnellstart

```
python ram_tetris.py --probe        # Geräte und Spielfeldgröße zeigen
python ram_tetris.py --play         # spielen
python ram_tetris.py --play --palette FFD200,0A28AA,FF1E1E,FFFFFF   # eigene Farben
```

## Aufnehmen und als Schleife laufen lassen

```
python ram_tetris.py --record recorded\meinelauf.json --runden 1 --fps 3
python ram_tetris.py --replay recorded\meinelauf.json --loop --speed 2
```

Deterministisch: dieselbe Aufnahme, derselbe Ablauf, endlos. `--runden 1` nimmt genau eine Runde auf,
inklusive Verloren-Blinken und Putz-Wellen.

## Geometrie kommt aus der Hardware

Das Spielfeld wird nicht geraten: `CorsairGetLedPositions` liefert die LED-Koordinaten in
Millimetern. Bei Vengeance-RGB-Pro sind das vier x-Werte (je Riegel eine Spalte) und zehn y-Werte —
also **10 Reihen × 4 Spalten**. Andere Module ergeben automatisch ihr eigenes Feld.

## Fallen, die beim Bauen Zeit gekostet haben

- `CorsairGetDeviceCount` gibt es in SDK 5 nicht — Geräte über `CorsairGetDevices` mit Filtermaske.
- Der Verbindungs-Callback bekommt einen **Zeiger auf ein Struct**; als `int` gelesen kommt Müll.
  Verbunden ist `CSS_Connected = 6`.
- `CorsairSetLedColorsBuffer` + asynchrones Flush → Zugriffsverstoß `0xC0000005`. Synchron setzen.
- y wächst nach oben; absteigend sortiert läuft die Animation verkehrt.
- Ist Weiß eine Spielfarbe, darf der Treffer-Blitz nicht weiß sein.
- Eine `.cmd` mit LF-Zeilenenden scheitert unter `cmd.exe` stumm.

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die mitgelieferte OpenRGB-Anbindung in `vendor/` stammt aus
[jath03/openrgb-python](https://github.com/jath03/openrgb-python) (MIT) und ist unverändert; sie ist
nur der Rückfallweg für Geräte, die das iCUE-SDK nicht erreicht.
