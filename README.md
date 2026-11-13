# RAM-Tetris

Ein Spiel auf den RGB-LEDs der Arbeitsspeicher-Riegel. Blöcke und Muster fallen von oben in die
Spalten, und wenn sich in einer Reihe oder Spalte drei gleiche Farben berühren, verschwinden sie
und der Rest rutscht nach. Läuft das Feld voll, beginnt die Runde von vorn.

Vorbild: der Short „Mein RAM spielt Tetris, ganz ohne mich" von Bastel Nerd — dort ausdrücklich
„gevibe coded", also ein eigenes Programm und kein iCUE-Effekt. Genau so ist es hier gelöst.

## Wie es funktioniert

iCUE 5 hat keine Kommandozeile, aber es liefert eine SDK-DLL mit. Auf diesem Rechner stammt sie von
Gigabytes Control Center:

```
C:\Program Files\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll
```

Angesprochen wird sie über `ctypes` aus Blenders eigenem Python — es muss also **nichts installiert
werden**. iCUE macht die Hardware-Arbeit, das Skript setzt nur Farben.

Die Geometrie kommt aus `CorsairGetLedPositions`: bei Speichermodulen in Millimetern, vier x-Werte
(je Riegel eine Spalte) und zehn y-Werte. Daraus baut das Skript die Zuordnung (Reihe, Spalte) → LED.

## Aufrufe

```
ram_tetris.py --probe                          Geräte und Spielfeldgröße zeigen
ram_tetris.py --simulate --steine 60           Spiel im Terminal, ohne Hardware
ram_tetris.py --static FF8800                  statische Farbe setzen
ram_tetris.py --play                           live spielen
ram_tetris.py --record recorded\lauf.json --dauer 60     aufzeichnen
ram_tetris.py --replay recorded\lauf.json --loop --speed 3   Endlosschleife
```

Optionen: `--farben N` (Palette: gelb, dunkelblau, rot, weiß, grün, lila), `--fps`,
`--backend icue|openrgb`, `--speed` für die Wiedergabe.

## Felder

Das Spielfeld wird aus der Hardware abgeleitet, nicht fest verdrahtet: **10 Reihen × 4 Spalten** am
Vengeance-RGB-Pro. Formen: O, I2, I3, L, J, S, T — ohne Drehung, weil das Feld zu schmal dafür ist.

Geräumt wird bei **drei gleichen Farben** waagerecht **oder** senkrecht. Waagerecht allein reicht
nicht: bei vier Spalten kommt eine Dreierkette sonst fast nie zustande.

## Betrieb auf dem Windows-Rechner

Liegt unter `C:\Users\LanLibbi\Tools\ram-tetris\`. Python nicht nötig — es läuft mit
`C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe`.

Die Schleife läuft als geplante Aufgabe **RamTetrisLoop** (als SYSTEM, damit sie die SSH-Sitzung
überlebt):

```
schtasks /run /tn RamTetrisLoop     starten
schtasks /end /tn RamTetrisLoop     beenden — danach steuert iCUE die Riegel wieder
```

Solange das Skript läuft, hat es die Kontrolle über die Riegel; iCUE steuert sie dann nicht.

## Fallen (alle teuer bezahlt)

- `CorsairGetDeviceCount` gibt es in SDK 5 nicht — Geräte über `CorsairGetDevices` mit Filtermaske.
- Der Verbindungs-Callback bekommt einen **Zeiger auf ein Struct**; als `int` gelesen kommt Müll.
  Verbunden ist `CSS_Connected = 6`.
- `CorsairSetLedColorsBuffer` + asynchrones Flush → Zugriffsverstoß `0xC0000005`. Synchron setzen.
- y wächst nach oben; absteigend sortiert läuft die Animation verkehrt.
- Ist Weiß eine Spielfarbe, darf der Treffer-Blitz nicht weiß sein.
- Eine `.cmd` mit LF-Zeilenenden scheitert unter `cmd.exe` stumm.
