# Anleitung — RAM-Tetris einrichten und anpassen

Diese Anleitung führt vom leeren Rechner bis zum laufenden Spiel und zeigt, wie man Farben,
Tempo und Ablauf ändert. Alles ohne Programmieren.

## 1. Was vorhanden sein muss

| Was | Warum | Woher |
|---|---|---|
| **iCUE** (Corsair) | steuert die Hardware, das Skript setzt nur Farben | corsair.com, iCUE 5 |
| **iCUESDK-DLL** | die Schnittstelle, über die Farben gesetzt werden | kommt meist schon mit: Gigabyte Control Center, MSI Center, ASUS Armoury — oder iCUE selbst |
| **Python 3.9 oder neuer** | führt das Spiel aus | python.org, „Add Python to PATH" anhaken |
| Corsair-RAM **mit RGB** | das Spielfeld | z. B. Vengeance RGB Pro / Pro SL |

Die DLL sucht das Skript selbst:

```
C:\Program Files\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll
C:\Program Files (x86)\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll
C:\Program Files\Corsair\Corsair iCUE5 Software\iCUESDK.x64_2019.dll
```

Fehlt sie überall, sagt das Skript das beim Start — dann fehlt der Mainboard-Hersteller-Software
die SDK-Komponente, oder man besorgt sie über Corsairs SDK-Seite.

## 2. Erster Start: prüfen, ob das Feld erkannt wird

Im Ordner des Spiels eine Eingabeaufforderung öffnen (Shift + Rechtsklick → „Terminal hier öffnen")
und:

```
python ram_tetris.py --probe
```

Erwartete Ausgabe:

```
Kontrolle: Erfolg
VENGEANCE RGB PRO: 10 Reihen × 4 Spalten (40 LEDs adressierbar)
```

Erscheint statt des RAM ein anderes Gerät, den Namen mit `--muster` setzen:
`--muster "VENGEANCE"`. Wird gar kein Gerät gefunden, läuft iCUE nicht — dann iCUE starten.

## 3. Spielen

```
python ram_tetris.py --play
```

Beenden mit `Strg + C`. Danach übernimmt iCUE die Beleuchtung wieder.

Ohne Hardware testen (zeigt das Spielfeld im Terminal):

```
python ram_tetris.py --simulate --steine 60
```

## 4. Farben ändern

**Der einfache Weg** — Farben als Hex-Werte, mit Komma getrennt:

```
python ram_tetris.py --play --palette FFD200,0A28AA,FF1E1E,FFFFFF
```

Das sind Gelb, Dunkelblau, Rot und Weiß (die Vorgabe). Beliebige eigene Werte gehen genauso:
`--palette 00FF88,FF00AA` ergibt zwei Farben, `--palette 111111,222222,333333,444444,555555` fünf.
Mindestens zwei, höchstens so viele, wie das Feld sinnvoll verkraftet — bei vielen Farben entstehen
seltener Ketten.

**Der dauerhafte Weg** — Farbe in der Datei `start.cmd` ändern (siehe Abschnitt 7), damit man den
Befehl nicht jedes Mal tippen muss.

Farbnamen für Hex-Werte findet man überall im Netz („color picker"). Die Reihenfolge der Liste ist
egal, sie bestimmt nur, welche Farbe im Terminal als A, B, C… erscheint.

## 5. Tempo ändern

| Was | Schalter | Wirkung |
|---|---|---|
| Fallgeschwindigkeit | `--fps 6` | Bilder je Sekunde; größer = schneller |
| Wiedergabe einer Aufnahme | `--speed 2` | 2 = doppelt so schnell, 0.5 = halb so schnell |

## 6. Aufnehmen und als Schleife laufen lassen

Einmal live spielen und dabei aufnehmen — danach läuft dieselbe Runde endlos, ohne Zufall:

```
python ram_tetris.py --record recorded\meinelauf.json --runden 1 --fps 3
python ram_tetris.py --replay recorded\meinelauf.json --loop --speed 2
```

`--runden 1` nimmt genau eine Runde auf, inklusive Verloren-Blinken und Putz-Wellen. Die Wiedergabe
ist deterministisch: gleiche Aufnahme, gleicher Ablauf, immer wieder.

## 7. Automatisch starten (optional)

`start.cmd` im Spielordner anlegen:

```bat
@echo off
cd /d "%~dp0"
python ram_tetris.py --replay recorded\meinelauf.json --loop --speed 2
```

Doppelklick startet die Schleife. Für Autostart nach der Anmeldung: `Win + R`, `shell:startup`,
eine Verknüpfung auf `start.cmd` hineinlegen.

## 8. Wenn etwas nicht geht

| Symptom | Ursache | Lösung |
|---|---|---|
| `iCUE-SDK-DLL nicht gefunden` | keine SDK-DLL auf dem Rechner | Abschnitt 1, Pfade prüfen |
| `iCUE-SDK nicht verbunden` | iCUE läuft nicht | iCUE starten, dann erneut |
| `Kein Gerät 'VENGEANCE' vom Typ 0x80 gefunden` | anderer Modellname | `--probe` zeigt die echten Namen, dann `--muster` anpassen |
| Riegel leuchten nicht, Spiel läuft | iCUE hat die Kontrolle behalten | `--probe` zeigt „Kontrolle: Erfolg"; sonst iCUE neu starten |
| nur ein Teil der Spalten leuchtet | iCUE meldet mehr Kanäle als Riegel gesteckt sind | normal, das Spiel läuft auf allen gemeldeten Kanälen |
| `python` wird nicht gefunden | Python nicht im PATH | Python neu installieren, „Add to PATH" anhaken |

## 9. Was das Spiel macht

Formen (O, I2, I3, L, J, S, T) fallen von oben in die Spalten. Drei gleiche Farben waagerecht oder
senkrecht verschwinden, der Rest rutscht nach. Ist eine Leiste bis oben zugebaut, ist die Runde
verloren: alles blinkt rot, danach wischen drei weiße Wellen das Feld sauber (senkrecht, dann
waagerecht hin und zurück), und es geht von vorn los.
