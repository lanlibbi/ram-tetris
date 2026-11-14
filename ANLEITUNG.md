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

## 7. Spiel wählen, Snake-Farben — alles im Dashboard

Seit dem Umbau gibt es **einen** Starter und **einen** Ort für die Einstellungen. Die Karte
**Now Playing** oben im Dashboard schaltet um:

| Knopf | Wirkung |
|---|---|
| **Tetris** | beendet Snake, startet die Endlosschleife von Tetris |
| **Snake** | beendet Tetris, startet Snake (spielt sich selbst) |
| **Off** | beendet beides, iCUE steuert die Riegel wieder |

Immer nur eins — beide Spiele schreiben auf dieselben 40 LEDs.

Die Karte **Snake** setzt die Farben für **Kopf**, **Körper** und **Futter** sowie die Züge je
Sekunde. **Verloren-Blitz** und **Cleanup Sweep** stehen bei den **Sequences** und gelten für beide
Spiele; Snake nutzt also denselben roten Verloren-Screen und denselben weissen Putzlauf wie Tetris.

Gespeichert wird in `einstellungen.json`:

```json
"snake": {"kopf": [255,214,0], "koerper": [0,190,110], "futter": [255,45,45], "fps": 6},
"modus": "snake"
```

**Wie das Umschalten funktioniert:** die Windows-Aufgabe `RamLoop` ruft `run.cmd` auf, das
`spielen.py` startet. `spielen.py` liest `einstellungen.json` und startet danach das passende
Spiel. Deshalb hat die Aufgabe eine feste Kommandozeile und muss beim Umschalten nur neu gestartet
werden — Farben und Tempo gelten ab dem nächsten Start.

## 8. Wenn das Bild steht: Protokoll, Aufsicht, fensterloser Start

**Warum das Bild einfrieren konnte:** das SDK bietet zwei Wege, LEDs zu setzen — synchron
(`CorsairSetLedColors`) und über einen Puffer mit asynchronem Flush
(`CorsairSetLedColorsBuffer` + `CorsairSetLedColorsFlushBufferAsync`). Der Puffer-Weg räumt
nebenläufig auf und griff dabei auf bereits freigegebenen Speicher zu: der Prozess starb mit
`0xC0000005`, die LEDs blieben beim letzten Bild stehen. Von außen sieht das wie ein Hänger aus,
der Prozess ist aber tot. **Es wird jetzt immer synchron geschrieben** (`icue_sdk.py`,
`setze_farben_raw`) — einen Hauch langsamer, dafür stabil.

**Aufsicht.** `RamLoop` startet `run_hidden.vbs` → `run.cmd` → `spielen.py`. `spielen.py` liest
`einstellungen.json`, startet das gewählte Spiel als Kindprozess und passt auf:

| Datei | Inhalt |
|---|---|
| `ram-log.txt` | Start, Ende mit Rückgabewert, LED-Schreibfehler, Watchdogs |
| `ram-ausgabe.txt` | alles, was das Spiel auf die Konsole schreibt (Absturzspuren) |

Stirbt das Spiel, startet die Aufsicht es nach ein paar Sekunden neu (bis 50 Versuche, dann gibt
sie auf). Eine Dateisperre sorgt dafür, dass nie zwei Aufsichten nebeneinander laufen — beide
würden auf dieselben LEDs schreiben.

**Zweiter Schutz im Spiel:** bleibt ein Bild 25 Sekunden ohne erfolgreichen Schreibvorgang (oder
scheitern 40 Bilder in Folge), beendet sich das Spiel selbst und die Aufsicht startet es frisch.
Das ist der Ausweg, wenn iCUE die Kontrolle zurückholt: einmal wird sie über
`CorsairRequestControl` neu angefordert, hilft das nicht, ist ein frischer Prozess der ehrlichere
Weg. Die Sitzung im laufenden Prozess abzubauen (`ReleaseControl` + `Disconnect` + `Connect`) hat
die DLL mit einer Zugriffsverletzung beendet — nicht nachmachen.

**Kein Fenster mehr.** Die Aufgabe ruft `wscript.exe` mit `run_hidden.vbs` auf; Skripte mit
`wscript` haben keine Konsole, und `run.cmd` wird mit Fensterstil 0 gestartet. Nachgeprüft: alle
Prozesse der Kette melden Fenstergriff 0.

## 9. Reiter statt Farbwüste

Die Farbkarte zeigt nur noch die Palette des Spiels, das gerade gewählt ist. Der Umschalter ist
gleichzeitig Spielwahl und Reiter:

| Reiter | Wirkung |
|---|---|
| **Tetris** | startet Tetris und zeigt Piece 01–04, Presets, FPS und Playback |
| **Snake** | startet Snake und zeigt Kopf, Körper, Futter und Züge je Sekunde |
| **Off** | beendet beide Spiele; die zuletzt offene Palette bleibt sichtbar |

**Game Over Flash** und **Cleanup Sweep** liegen unter beiden Reitern, weil sie für beide Spiele
gelten — sie stehen deshalb nur einmal auf der Seite. Die Live-Vorschau wechselt mit dem Reiter:
bei Snake zeigt sie Kopf, Körper, Futter, bei Tetris das Spielfeld.

Ein weiteres Spiel (Pong, Game of Life, …) braucht damit nur drei Dinge: ein Skript, einen Eintrag
in `spielen.py` und einen Reiter mit seinem Farbblock.

## 10. Pong und Space Invaders

Beide Spiele nutzen die gemeinsame Basis `spielbasis.py`: dieselbe Anzeige mit
Wiederverbinden, dasselbe Protokoll, derselbe Watchdog und dieselbe Todes-Sequenz
(**Game Over Flash** rot, dann **Cleanup Sweep** weiß). Farben und Tempo stehen im Dashboard unter
ihrem eigenen Reiter.

### Pong (`pong.py`)

Der Ball läuft senkrecht, prallt an den Seitenwänden ab, unten steht eine zwei LEDs breite
Schlagfläche. Jeder Rückläufer macht den Ball schneller. Geht er unten vorbei, kommt der
Verloren-Screen.

Der Rechner führt die Schlagfläche selbst — mit Vorausschau, sonst wäre er chancenlos: er rechnet
aus, in welcher Spalte der Ball unten ankommt (Seitenwände mitgerechnet). Damit wäre er unfehlbar,
deshalb verschätzt er sich pro Ballwechsel mit einer Wahrscheinlichkeit, die mit der Länge des
Wechsels steigt — um **zwei** Spalten, denn eine Spalte daneben bleibt bei zwei LEDs Breite
folgenlos (mit ±1 endete in der Messung kein einziger Ballwechsel).

Gemessen über 20.000 Züge: im Schnitt **12 Rückläufer** je Runde, längster 45, kürzester 2. Bei
8 Zügen/s endet eine Runde etwa alle halbe Minute.

### Space Invaders (`invaders.py`)

Ein waagerecht marschierender Alienblock ist auf vier Spalten sinnlos — er stößt nach zwei Zügen
an und steht nach Sekunden unten. Der Angriff läuft deshalb **senkrecht**: ein Block aus zwei
Reihen à vier Aliens steigt Reihe für Reihe herab, das Schiff unten schießt nach oben und weicht
feindlichen Schüssen aus.

- Schiff getroffen oder Aliens auf der unteren Reihe → Verloren-Screen (rot + Putzlauf)
- Block abgeräumt → nur der **Putzlauf** (ohne rot), dann die nächste, schnellere Welle

Gemessen über 20.000 Züge: **147 abgeräumte Wellen** und 121 verlorene Runden — das Spiel gewinnt
also öfter, als es verliert, und zeigt beide Abschlüsse regelmäßig (bei 10 Zügen/s etwa alle
13–16 Sekunden).

### Farben

```json
"pong":     {"schlaeger": [0,220,255], "ball": [255,255,255], "treffer": [255,214,0], "fps": 8},
"invaders": {"schiff": [0,220,255], "alien": [140,255,90], "schuss": [255,214,0],
             "alien_schuss": [255,60,200], "fps": 10}
```

### Ein neues Spiel anschließen

Drei Stellen, mehr nicht:

1. ein Skript, das `spielbasis` nutzt (`schreibe_bild`, `verloren_und_putzen`, `watchdog_starten`),
2. ein Eintrag in `SPIELE` in `spielen.py`,
3. ein Reiter samt Farbblock in `einstellungen.py` — plus der Name in der Modus-Prüfung von
   `_spiel_umschalten` und in `SPIEL_MUSTER`, sonst beendet der Schalter das neue Spiel nicht.

Hinweis: `snake.py` trägt diese Hilfsfunktionen noch selbst mit sich (es lief zuerst und blieb
unangetastet) — beim nächsten Anfassen auf `spielbasis` umstellen, damit es nur eine Stelle gibt.

