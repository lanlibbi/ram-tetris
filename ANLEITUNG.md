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


## 4b. Das Einstellungsfenster (empfohlen)

Kein Befehl, kein Port zum Merken: im Projektordner liegt **`einstellungen.cmd`** — ein Doppelklick
genügt. Der Starter prüft, ob der lokale Server schon läuft; wenn ja, öffnet er nur den Browser, wenn
nein, startet er ihn und öffnet dann die Seite. Auf Wunsch eine Verknüpfung auf den Desktop legen
(Rechtsklick → Senden an → Desktop).

Dort einstellen:

- **Piece Colors** — die vier Farben der fallenden Formen (große Flächen, Klick öffnet den Farbwähler)
- **Game Over Flash** — die Farbe, in der es blinkt, wenn eine Leiste voll ist
- **Cleanup Sweep** — die Farbe der Wellen, die danach durchlaufen
- **Speed** — Bilder je Sekunde und Wiedergabe-Tempo
- **Presets** — sechs fertige Paletten zum Antippen

Knöpfe: **Save** · **Preview Run** · **Deploy** · **Remove**

| Knopf | Wirkung |
|---|---|
| **Save** | schreibt `einstellungen.json`; das Spiel liest sie beim nächsten Start |
| **Preview Run** | startet einen Probelauf mit den aktuellen Farben |
| **Deploy** | legt `start.cmd` an, setzt eine Verknüpfung in den Autostart und startet das Spiel |
| **Remove** | nimmt Autostart und `start.cmd` zurück und beendet das Spiel |

Von Hand geht es auch: `python einstellungen.py` und dann `http://127.0.0.1:8787/` aufrufen. Warum im
Browser und nicht als klassisches Fenster: Blenders Python — der Interpreter, den dieses Projekt
mitbenutzt — bringt Tkinter nicht mit, und große Farbflächen mit dem System-Farbwähler bekommt man im
Browser ohnehin leichter.

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

## 6. Snake — das zweite Spiel

Dasselbe Feld, dieselbe Technik, andere Logik: statt fallender Steine eine Schlange, die sich
selbst spielt. Bedienung gibt es keine — es gibt keine Tastatur am RAM.

```
snake.cmd                  Doppelklick: spielt los (Strg+C beendet)
snake.cmd --fps 8          schneller
snake.cmd --sekunden 60    nach einer Minute aufhören
snake.cmd --probe          zeigt nur, was die Hardware meldet
python snake.py --simulate nur ASCII im Terminal, ohne LEDs
```

**Warum spielt es sich selbst?** Weil man an den RAM-Riegeln nicht herankommt, während der Rechner
läuft. Der Autopilot würfelt nicht, sondern sucht:

1. nur Züge, die nicht in die Wand oder in den eigenen Körper führen,
2. davon die, nach denen das Futter noch erreichbar bleibt,
3. unter denen den Zug mit dem meisten freien Platz (Flutfüllung) — sonst sperrt sich die Schlange
   in der schmalen 4-Spalten-Ecke selbst ein,
4. bei Gleichstand: der Zug, der näher ans Futter führt.

Über 4.000 Züge gemessen: bis zu 28 von 40 LEDs Länge, gelegentliche Tode, danach Neustart.

**Farben** stehen in `einstellungen.json` unter `snake`:

```json
"snake": {"kopf": [255, 214, 0], "koerper": [0, 190, 110],
          "futter": [255, 45, 45], "tod": [255, 20, 20]}
```

Fehlt der Block, gelten die Vorgaben; der Verlorenton wird dann aus `verloren` übernommen.

