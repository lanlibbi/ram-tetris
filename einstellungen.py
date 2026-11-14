#!/usr/bin/env python3
"""Einstellungsfenster für RAM-Tetris — als lokale Seite im Browser.

Warum nicht Tkinter: Blenders Python (das hier als Interpreter dient) bringt Tkinter nicht mit.
Eine Seite im Browser kann außerdem das, was hier zählt — große Farbflächen und den Farbwähler des
Systems. Es wird nichts installiert: das Skript liefert die Seite selbst aus (http.server aus der
Standardbibliothek) und schreibt die Einstellungen in `einstellungen.json`.

Aufruf:  python einstellungen.py        → öffnet http://127.0.0.1:8787
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HIER = os.path.dirname(os.path.abspath(__file__))
KONFIG = os.path.join(HIER, "einstellungen.json")
START_CMD = os.path.join(HIER, "start.cmd")
AUFNAHME = os.path.join(HIER, "recorded", "ram-lauf2.json")
PYTHON = sys.executable
PORT = int(os.environ.get("RAMTETRIS_PORT", "8787"))
STARTUP = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup",
                       "RAM-Tetris.lnk")

VORGABE = {
    "palette": [[255, 210, 0], [10, 40, 170], [255, 30, 30], [255, 255, 255]],
    "verloren": [255, 40, 40],
    "welle": [255, 255, 255],
    "fps": 3,
    "speed": 2,
    # Snake: eigene Farben, Verloren und Putzen teilt es mit Tetris
    "snake": {"kopf": [255, 214, 0], "koerper": [0, 190, 110],
              "futter": [255, 45, 45], "fps": 6},
    # welches Spiel laeuft gerade: "tetris", "snake" oder "aus"
    "modus": "tetris",
}

# Eine Windows-Aufgabe startet, was im Dashboard gewählt ist (spielen.py liest die Wahl).
AUFGABE = "RamLoop"
ALTE_AUFGABEN = ["RamTetrisLoop", "RamSnakeLoop"]
# Prozessmuster, an denen ein laufendes Spiel erkannt wird (das Einstellungsfenster
# selbst heisst einstellungen.py und darf NICHT mit erwischt werden)
SPIEL_MUSTER = ["*ram_tetris*", "*snake.py*"]


def _rufe(befehl: list[str], text: bool = False):
    """Externen Befehl aufrufen und Fehlen tolerieren.

    Auf Windows gibt es schtasks, auf Linux nicht — das Einstellungsfenster soll trotzdem
    antworten statt mit einem Stapelabzug zu sterben.
    """
    try:
        return subprocess.run(befehl, capture_output=True, text=text)
    except FileNotFoundError:
        class _Fehlt:
            returncode = 127
            stdout = stderr = ""
        return _Fehlt()


def lade() -> dict:
    daten = json.loads(json.dumps(VORGABE))
    if os.path.exists(KONFIG):
        try:
            gelesen = json.loads(open(KONFIG, encoding="utf-8").read())
            for schluessel in daten:
                if schluessel in gelesen:
                    daten[schluessel] = gelesen[schluessel]
            # Unterschlüssel ergänzen, die in einer älteren Datei fehlen
            for schluessel, vorgabe in VORGABE.items():
                if isinstance(vorgabe, dict) and isinstance(daten.get(schluessel), dict):
                    for unterschluessel, wert in vorgabe.items():
                        daten[schluessel].setdefault(unterschluessel, wert)
        except Exception:
            pass
    return daten


def speichere(daten: dict) -> None:
    with open(KONFIG, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, indent=1)


def hexwert(farbe) -> str:
    return "#%02x%02x%02x" % tuple(int(k) for k in farbe)


SEITE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAM Games — Lighting Control</title>
<style>
  :root{
    color-scheme: dark;
    --text:#eef1f7; --gedimmt:#98a1b4; --fein:#6d7688;
    --glas:rgba(255,255,255,.045);
    --glas-hell:rgba(255,255,255,.075);
    --rand:rgba(255,255,255,.10);
    --rand-hell:rgba(255,255,255,.18);
    --akzent:#5b8cff; --akzent2:#a855f7; --gut:#4ade80; --warn:#ff8080;
  }
  *{box-sizing:border-box}
  html,body{min-height:100%}
  body{
    margin:0; color:var(--text); overflow-x:hidden;
    font:15px/1.55 ui-sans-serif,system-ui,"Segoe UI",Inter,sans-serif;
    background:#07080c; -webkit-font-smoothing:antialiased;
  }
  /* Hintergrund: tiefe Fläche mit weichen Farbwolken */
  .himmel{position:fixed; inset:-20% -10% auto -10%; height:75vh; z-index:-2; pointer-events:none;
    background:
      radial-gradient(46% 60% at 18% 22%, #2456c7aa, transparent 62%),
      radial-gradient(40% 52% at 78% 12%, #7b3fe4aa, transparent 60%),
      radial-gradient(38% 46% at 58% 58%, #0f7f8c99, transparent 64%);
    filter:blur(64px) saturate(130%);
  }
  .korn{position:fixed; inset:0; z-index:-1; pointer-events:none; opacity:.035;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");}
  .wrap{max-width:920px; margin:0 auto; padding:46px 22px 90px}

  /* Kopf */
  header.kopf{display:flex; align-items:center; gap:15px; margin-bottom:26px}
  .logo{width:45px;height:45px;border-radius:13px;flex:0 0 auto;
    display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:3px;padding:8px;
    background:linear-gradient(140deg,#ffffff1f,#ffffff08);
    border:1px solid var(--rand-hell); backdrop-filter:blur(12px);
    box-shadow:0 14px 34px -22px #7b3fe4, inset 0 1px 0 #ffffff40}
  .logo i{border-radius:2px; box-shadow:0 0 8px currentColor}
  .logo i:nth-child(1){background:#ffd200;color:#ffd200}
  .logo i:nth-child(2){background:#3b6bff;color:#3b6bff}
  .logo i:nth-child(3){background:#ff3b3b;color:#ff3b3b}
  .logo i:nth-child(4){background:#fff;color:#fff}
  h1{font-size:27px;margin:0;letter-spacing:-.025em;font-weight:660;
     background:linear-gradient(100deg,#fff,#c7d2ff 60%,#e6c9ff);
     -webkit-background-clip:text;background-clip:text;color:transparent}
  .unter{color:var(--gedimmt);margin:5px 0 0;font-size:13.5px}
  .badge{margin-left:auto; font-size:11.5px; letter-spacing:.1em; text-transform:uppercase;
    color:#c7d2ff; padding:7px 12px; border-radius:999px;
    background:linear-gradient(140deg,#ffffff14,#ffffff06); border:1px solid var(--rand);
    backdrop-filter:blur(12px); white-space:nowrap}

  /* Glaskarten */
  .karte{
    position:relative; border-radius:20px; padding:22px 22px 24px; margin-top:16px;
    background:linear-gradient(160deg,var(--glas-hell),var(--glas) 42%,rgba(255,255,255,.02));
    border:1px solid var(--rand);
    backdrop-filter:blur(22px) saturate(150%);
    -webkit-backdrop-filter:blur(22px) saturate(150%);
    box-shadow:0 26px 60px -40px #000, inset 0 1px 0 rgba(255,255,255,.14);
  }
  .karte::before{content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
    background:radial-gradient(120% 80% at 12% -20%, #ffffff14, transparent 60%)}
  .karte > h2{position:relative; font-size:11.5px; text-transform:uppercase; letter-spacing:.16em;
    color:#b9c3d6; margin:0 0 16px; font-weight:600; display:flex; align-items:center; gap:12px}
  .karte > h2 span{color:#6f7a8f; letter-spacing:.04em; text-transform:none; font-weight:400;
    font-size:12px}
  .karte > h2::after{content:""; flex:1; height:1px;
    background:linear-gradient(90deg,rgba(255,255,255,.16),transparent)}

  /* Farbkacheln */
  .farben{display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:14px}
  .kachel{position:relative; cursor:pointer; border:0; padding:0; background:none; font:inherit;
    color:inherit; text-align:left; transition:transform .16s cubic-bezier(.2,.8,.3,1)}
  .kachel:hover{transform:translateY(-3px)}
  .kachel:focus-visible{outline:2px solid var(--akzent); outline-offset:4px; border-radius:18px}
  .kachel .farbe{position:relative; height:118px; border-radius:16px; overflow:hidden;
    border:1px solid rgba(255,255,255,.22);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.45), inset 0 -30px 60px rgba(0,0,0,.45),
               0 18px 40px -26px #000}
  .kachel .farbe::after{content:""; position:absolute; inset:0;
    background:linear-gradient(165deg,rgba(255,255,255,.30),rgba(255,255,255,.04) 38%,transparent 62%)}
  .kachel .glasrand{position:absolute; inset:0; border-radius:16px; pointer-events:none;
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.14)}
  .kachel .hex{position:absolute; bottom:9px; right:10px; z-index:3;
    font:11px/1 ui-monospace,Consolas,monospace; letter-spacing:.05em; color:#0b0d12;
    background:rgba(255,255,255,.82); padding:5px 7px; border-radius:7px;
    backdrop-filter:blur(6px); box-shadow:0 2px 8px rgba(0,0,0,.25)}
  .kachel .name{margin-top:10px; font-size:12.5px; color:#c9d2e2; display:flex; gap:6px;
    align-items:baseline}
  .kachel .name b{font-weight:600; color:#eef1f7}
  .kachel .name i{font-style:normal; color:var(--fein); font-size:11.5px}
  .kachel input[type=color]{position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%}
  .kachel.sweep .farbe::before{content:""; position:absolute; inset:0; z-index:1;
    background:linear-gradient(105deg,transparent 22%,#ffffff55 44%,#ffffffcc 50%,#ffffff55 56%,transparent 78%);
    background-size:230% 100%; animation:sweep 3.4s linear infinite}
  @keyframes sweep{from{background-position:180% 0} to{background-position:-90% 0}}
  .kachel.flash .farbe::before{content:""; position:absolute; inset:0; z-index:1;
    background:#fff; opacity:0; animation:flash 2.4s ease-in-out infinite}
  @keyframes flash{0%,62%,100%{opacity:0} 8%,18%{opacity:.55} 13%,24%{opacity:0}}

  /* Vorschau */
  .vorschau-karte{display:flex; gap:26px; flex-wrap:wrap; align-items:flex-start}
  .bretter{display:flex; gap:14px}
  .brett{display:grid; grid-template-columns:repeat(4,26px); gap:4px; padding:14px;
    border-radius:15px; background:rgba(4,6,10,.55); border:1px solid rgba(255,255,255,.10);
    backdrop-filter:blur(10px); box-shadow:inset 0 0 34px #00000099, 0 10px 30px -24px #000}
  .brett span{width:26px;height:16px;border-radius:4px;background:rgba(255,255,255,.045);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}
  .legende{color:var(--gedimmt); font-size:13px; max-width:36ch}
  .legende b{color:var(--text); font-weight:600}

  /* Paletten */
  .chips{display:flex; gap:10px; flex-wrap:wrap}
  .chip{border:1px solid var(--rand); border-radius:999px; padding:9px 15px; font-size:13px;
    color:#d3daea; cursor:pointer; display:flex; align-items:center; gap:9px;
    background:linear-gradient(150deg,#ffffff12,#ffffff04); backdrop-filter:blur(10px);
    transition:border-color .15s, transform .12s, background .15s}
  .chip:hover{border-color:var(--rand-hell); transform:translateY(-1px); background:#ffffff18}
  .chip i{width:13px;height:13px;border-radius:4px;display:inline-block;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.5), 0 0 8px currentColor}

  /* Zahlen */
  .zahlen{display:flex; gap:26px; flex-wrap:wrap}
  .feld label{display:block; font-size:12px; letter-spacing:.09em; text-transform:uppercase;
    color:#b9c3d6; margin-bottom:8px}
  .feld small{display:block; color:var(--fein); font-size:11.5px; margin-top:7px}
  input[type=number]{width:104px; font:15px/1 inherit; padding:12px 13px; border-radius:12px;
    border:1px solid var(--rand); background:rgba(6,8,12,.55); color:var(--text);
    backdrop-filter:blur(8px)}
  input[type=number]:focus{outline:none; border-color:var(--akzent);
    box-shadow:0 0 0 4px rgba(91,140,255,.20)}

  /* Knöpfe */
  .leiste{display:flex; gap:11px; flex-wrap:wrap; align-items:center}
  button.aktion{font:inherit; font-weight:560; padding:13px 21px; border-radius:13px; cursor:pointer;
    color:var(--text); border:1px solid var(--rand); backdrop-filter:blur(12px);
    background:linear-gradient(160deg,#ffffff16,#ffffff05);
    transition:transform .12s, filter .15s, border-color .15s}
  button.aktion:hover{filter:brightness(1.2); border-color:var(--rand-hell)}
  button.aktion:active{transform:translateY(1px)}
  button.haupt{position:relative; border:1px solid rgba(255,255,255,.28); color:#fff;
    background:linear-gradient(135deg,#5b8cff,#a855f7);
    box-shadow:0 18px 40px -20px #5b8cff99, inset 0 1px 0 #ffffff66}
  button.deploy{border-color:rgba(168,85,247,.45); color:#e6d4ff;
    background:linear-gradient(160deg,rgba(168,85,247,.22),rgba(91,140,255,.12))}
  button.modus-knopf.aktiv{border-color:rgba(91,140,255,.65); color:#fff;
    background:linear-gradient(135deg,rgba(91,140,255,.45),rgba(168,85,247,.30));
    box-shadow:0 14px 34px -18px #5b8cff, inset 0 1px 0 #ffffff55}
  button.gefahr{color:#ffc2c2; border-color:rgba(255,110,110,.32);
    background:linear-gradient(160deg,rgba(255,80,80,.14),rgba(255,80,80,.04))}

  #modus-status{margin-top:14px; font-size:13.5px; color:#9fc0ff; opacity:0;
    transform:translateY(-4px); transition:opacity .22s, transform .22s}
  #modus-status.an{opacity:1; transform:none}
  #status{margin-top:16px; font-size:13.5px; color:var(--gut); opacity:0; transform:translateY(-4px);
    transition:opacity .22s, transform .22s}
  #status.an{opacity:1; transform:none}
  footer{margin-top:22px; color:var(--fein); font-size:12.5px; line-height:1.75}
  footer b{color:#c9d2e2; font-weight:600}
  a{color:#8fb3ff; text-decoration:none}
  a:hover{text-decoration:underline}
  code{background:rgba(6,8,12,.6); border:1px solid var(--rand); padding:2px 7px; border-radius:6px;
    font:12px/1.4 ui-monospace,Consolas,monospace; color:#aeb8cc}
</style></head>
<body>
<div class="himmel"></div><div class="korn"></div>
<div class="wrap">

<header class="kopf">
  <div class="logo"><i></i><i></i><i></i><i></i></div>
  <div>
    <h1>RAM-Tetris</h1>
    <p class="unter">Lighting Control — Tetris und Snake. Farben, Sequenzen und Takt, gespeichert in
      <code>einstellungen.json</code>, aktiv ab dem nächsten Start.</p>
  </div>
  <div class="badge">iCUE SDK</div>
</header>

<section class="karte">
  <h2>Now Playing <span>welches Spiel auf den Riegeln laufen soll</span></h2>
  <div class="leiste" id="modus-leiste">
    <button class="aktion modus-knopf" data-modus="tetris" onclick="modus('tetris')">Tetris</button>
    <button class="aktion modus-knopf" data-modus="snake" onclick="modus('snake')">Snake</button>
    <button class="aktion modus-knopf" data-modus="aus" onclick="modus('aus')">Off</button>
  </div>
  <footer>
    Immer nur ein Spiel — beide schreiben auf dieselben LEDs. <b>Off</b> beendet beide, danach
    steuert iCUE die Riegel wieder.
  </footer>
  <div id="modus-status"></div>
</section>

<section class="karte">
  <h2>Piece Colors <span>die vier Farben der fallenden Formen</span></h2>
  <div class="farben" id="palette"></div>
</section>

<section class="karte">
  <h2>Sequences <span>was beim Verlieren und beim Aufräumen passiert</span></h2>
  <div class="farben" id="sequenzen"></div>
</section>

<section class="karte">
  <h2>Snake <span>Kopf, Körper und Futter · Verloren und Putzen siehe Sequences</span></h2>
  <div class="farben" id="snake-farben"></div>
  <div class="zahlen" style="margin-top:20px">
    <div class="feld"><label>Snake Speed</label>
      <input type="number" id="snake-fps" min="1" max="20" step="1">
      <small>Züge je Sekunde</small></div>
  </div>
</section>

<section class="karte">
  <h2>Live Preview <span>10 Reihen × 4 Spalten, ein Riegel je Spalte</span></h2>
  <div class="vorschau-karte">
    <div class="bretter"><div class="brett" id="brett"></div></div>
    <div class="legende">
      Drei gleiche Farben waagerecht oder senkrecht <b>match &amp; clear</b>. Volle Spalte heisst
      <b>Game Over</b>: erst der Flash, dann der <b>Cleanup Sweep</b>, dann neu.
    </div>
  </div>
</section>

<section class="karte">
  <h2>Presets <span>ein Klick setzt alle vier Formfarben</span></h2>
  <div class="chips" id="chips"></div>
</section>

<section class="karte">
  <h2>Speed <span>Fall und Wiedergabe</span></h2>
  <div class="zahlen">
    <div class="feld"><label>Frames per second</label>
      <input type="number" id="fps" min="1" max="10" step="1">
      <small>höher = schneller</small></div>
    <div class="feld"><label>Playback</label>
      <input type="number" id="speed" min="0.5" max="4" step="0.5">
      <small>2 = doppelt so schnell</small></div>
  </div>
</section>

<section class="karte">
  <h2>Deploy <span>installieren, ausprobieren, entfernen</span></h2>
  <div class="leiste">
    <button class="aktion haupt" onclick="speichern()">Save</button>
    <button class="aktion" onclick="aktion('probelauf')">Preview Run</button>
    <button class="aktion deploy" onclick="aktion('installieren')">Deploy</button>
    <button class="aktion gefahr" onclick="aktion('entfernen')">Remove</button>
  </div>
  <div id="status"></div>
  <footer>
    <b>Deploy</b> legt <code>start.cmd</code> an, setzt eine Verknüpfung in den Autostart und startet
    das Spiel. <b>Remove</b> nimmt beides zurück und beendet es — danach steuert iCUE wieder.<br><br>
    <a href="https://github.com/lanlibbi/ram-tetris" target="_blank" rel="noopener">github.com/lanlibbi/ram-tetris</a>
  </footer>
</section>

</div>
<script>
const ROLLEN = ["Piece 01","Piece 02","Piece 03","Piece 04"];
const PRESETS = [
  {name:"Default",    p:["#ffd200","#0a28aa","#ff1e1e","#ffffff"]},
  {name:"Neon",       p:["#39ff14","#00e5ff","#ff00d4","#fff9b0"]},
  {name:"Arctic",     p:["#7fd4ff","#2b6df6","#b6f0ff","#ffffff"]},
  {name:"Ember",      p:["#ff3b00","#ff9d00","#ffd200","#fff3d6"]},
  {name:"Gameboy",    p:["#9bbc0f","#8bac0f","#306230","#e0f8d0"]},
  {name:"Midnight",   p:["#4c8dff","#8b5cf6","#22d3ee","#e9ecf2"]}
];
let daten = __DATEN__;

const hex = c => '#' + c.map(k => k.toString(16).padStart(2,'0')).join('');
const vonHex = h => [1,3,5].map(i => parseInt(h.substr(i,2),16));

function farbname(c){
  const [r,g,b] = c.map(k => k/255);
  const max = Math.max(r,g,b), min = Math.min(r,g,b), d = max-min;
  if (max < 0.12) return "Black";
  if (d < 0.10) return max > 0.86 ? "White" : (max > 0.45 ? "Grey" : "Charcoal");
  let h = 0;
  if (max === r) h = ((g-b)/d) % 6; else if (max === g) h = (b-r)/d + 2; else h = (r-g)/d + 4;
  h = (h*60+360)%360;
  const hell = max > 0.82 && d < 0.40;
  if (h < 15 || h >= 345) return hell ? "Rose" : "Red";
  if (h < 40) return hell ? "Coral" : "Orange";
  if (h < 70) return max > 0.78 ? "Amber" : "Olive";
  if (h < 160) return max > 0.78 ? "Mint" : "Forest";
  if (h < 200) return hell ? "Ice" : "Teal";
  if (h < 250) return max > 0.78 ? "Sky" : "Navy";
  if (h < 290) return "Violet";
  return hell ? "Pink" : "Magenta";
}

function kachel(titel, farbe, beiAenderung, extra){
  const b = document.createElement('button');
  b.className = 'kachel' + (extra ? ' ' + extra : '');
  b.type = 'button';
  b.innerHTML = `<div class="farbe" style="background:${hex(farbe)}">
      <span class="glasrand"></span>
      <span class="hex">${hex(farbe).slice(1).toUpperCase()}</span>
      <input type="color" value="${hex(farbe)}" aria-label="${titel}">
    </div>
    <div class="name"><b>${titel}</b><i>${farbname(farbe)}</i></div>`;
  const eingabe = b.querySelector('input');
  eingabe.addEventListener('input', e => {
    const neu = vonHex(e.target.value);
    beiAenderung(neu);
    b.querySelector('.farbe').style.background = e.target.value;
    b.querySelector('.hex').textContent = e.target.value.slice(1).toUpperCase();
    b.querySelector('.name i').textContent = farbname(neu);
    vorschauBrett();
  });
  b.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') eingabe.click(); });
  return b;
}

function baue(){
  const p = document.getElementById('palette');
  p.innerHTML = '';
  daten.palette.forEach((c,i) => p.appendChild(
    kachel(ROLLEN[i] || ('Piece 0' + (i+1)), c, neu => daten.palette[i] = neu)));

  const s = document.getElementById('sequenzen');
  s.innerHTML = '';
  s.appendChild(kachel('Game Over Flash', daten.verloren, neu => daten.verloren = neu, 'flash'));
  s.appendChild(kachel('Cleanup Sweep', daten.welle, neu => daten.welle = neu, 'sweep'));

  const sn = document.getElementById('snake-farben');
  sn.innerHTML = '';
  if (!daten.snake) daten.snake = {kopf:[255,214,0], koerper:[0,190,110], futter:[255,45,45], fps:6};
  sn.appendChild(kachel('Snake Head', daten.snake.kopf, neu => daten.snake.kopf = neu));
  sn.appendChild(kachel('Snake Body', daten.snake.koerper, neu => daten.snake.koerper = neu));
  sn.appendChild(kachel('Food', daten.snake.futter, neu => daten.snake.futter = neu));
  document.getElementById('snake-fps').value = daten.snake.fps || 6;

  const chips = document.getElementById('chips');
  chips.innerHTML = '';
  PRESETS.forEach(v => {
    const c = document.createElement('button');
    c.className = 'chip';
    c.type = 'button';
    c.innerHTML = v.p.map(f => `<i style="background:${f};color:${f}"></i>`).join('') +
                  `<span>${v.name}</span>`;
    c.onclick = () => { daten.palette = v.p.map(vonHex); baue(); vorschauBrett(); };
    chips.appendChild(c);
  });

  document.getElementById('fps').value = daten.fps;
  document.getElementById('speed').value = daten.speed;
  modusAnzeigen(daten.modus || 'tetris');
  vorschauBrett();
}

function modusAnzeigen(aktiv){
  document.querySelectorAll('.modus-knopf').forEach(k => {
    k.classList.toggle('aktiv', k.dataset.modus === aktiv);
  });
  daten.modus = aktiv;
}

async function modus(was){
  sammle();
  await fetch('/speichern',{method:'POST',body:JSON.stringify(daten)});
  const r = await fetch('/modus',{method:'POST',body:JSON.stringify({modus:was})});
  modusAnzeigen(was);
  const s = document.getElementById('modus-status');
  s.textContent = await r.text();
  s.classList.add('an');
  clearTimeout(window._tm);
  window._tm = setTimeout(() => s.classList.remove('an'), 8000);
}

function vorschauBrett(){
  const brett = document.getElementById('brett');
  const f = daten.palette;
  const muster = [0,1,2,3,1,0,3,2,2,3,0,1,3,2,1,0,1,1,2,2,0,3,3,0,2,0,1,3,3,1,0,2,0,2,3,1,2,1,0,3];
  brett.innerHTML = '';
  muster.forEach((k,i) => {
    const s = document.createElement('span');
    if (i >= 8){
      s.style.background = hex(f[k % f.length]);
      s.style.boxShadow = 'inset 0 1px 0 rgba(255,255,255,.35), 0 0 10px ' + hex(f[k % f.length]) + '55';
    }
    brett.appendChild(s);
  });
}

function sammle(){
  daten.fps = parseInt(document.getElementById('fps').value,10) || 3;
  daten.speed = parseFloat(document.getElementById('speed').value) || 2;
  if (!daten.snake) daten.snake = {};
  daten.snake.fps = parseInt(document.getElementById('snake-fps').value,10) || 6;
}

function zeige(text){
  const s = document.getElementById('status');
  s.textContent = text;
  s.classList.add('an');
  clearTimeout(window._t);
  window._t = setTimeout(() => s.classList.remove('an'), 7000);
}

async function speichern(){
  sammle();
  const r = await fetch('/speichern',{method:'POST',body:JSON.stringify(daten)});
  zeige(await r.text());
}

async function aktion(was){
  sammle();
  await fetch('/speichern',{method:'POST',body:JSON.stringify(daten)});
  const r = await fetch('/'+was,{method:'POST'});
  zeige(await r.text());
}

baue();
</script></body></html>
"""


def seite() -> bytes:
    return SEITE.replace("__DATEN__", json.dumps(lade())).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _sende(self, text: str, code: int = 200) -> None:
        roh = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    def do_GET(self) -> None:      # noqa: N802
        pfad = self.path.split("?", 1)[0]
        if pfad in ("/", "/index.html"):
            roh = seite()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(roh)))
            self.end_headers()
            self.wfile.write(roh)
        else:
            self._sende("nicht gefunden", 404)

    def do_POST(self) -> None:     # noqa: N802
        laenge = int(self.headers.get("Content-Length") or 0)
        koerper = self.rfile.read(laenge).decode("utf-8") if laenge else ""

        if self.path == "/speichern":
            try:
                daten = json.loads(koerper)
                speichere(daten)
                self._sende("gespeichert — das Spiel liest die Farben beim nächsten Start")
            except Exception as fehler:
                self._sende(f"nicht gespeichert: {fehler}", 400)
            return

        if self.path == "/probelauf":
            subprocess.Popen([PYTHON, os.path.join(HIER, "ram_tetris.py"), "--play"],
                             cwd=HIER, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            self._sende("Probelauf gestartet — im Konsolenfenster mit Strg+C beenden")
            return

        if self.path == "/modus":
            try:
                wunsch = (json.loads(koerper or "{}").get("modus") or "").lower()
            except Exception:
                self._sende("ungültiger Wunsch", 400)
                return
            self._sende(self._spiel_umschalten(wunsch))
            return

        if self.path == "/installieren":
            self._sende(self._installieren())
            return

        if self.path == "/entfernen":
            self._sende(self._entfernen())
            return

        self._sende("unbekannte Aktion", 404)

    # -- Aktionen -------------------------------------------------------
    def _spiel_umschalten(self, modus: str) -> str:
        """Beendet beide Spiele und startet das gewünschte über seine Windows-Aufgabe."""
        if modus not in ("tetris", "snake", "aus"):
            return f"unbekannter Spielmodus: {modus!r}"

        daten = lade()
        daten["modus"] = modus
        speichere(daten)

        # laufendes Spiel anhalten (auch die früheren Einzelaufgaben)
        for aufgabe in [AUFGABE] + ALTE_AUFGABEN:
            _rufe(["schtasks", "/end", "/tn", aufgabe])
        muster = " -or ".join(f"$_.CommandLine -like '{m}'" for m in SPIEL_MUSTER)
        _rufe(["powershell", "-NoProfile", "-Command",
               "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" "
               f"| Where-Object {{ {muster} }} "
               "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"])

        if modus == "aus":
            return "beide Spiele beendet — iCUE steuert die Riegel wieder"

        pruefung = _rufe(["schtasks", "/query", "/tn", AUFGABE], text=True)
        if pruefung.returncode != 0:
            # Aufgabe fehlt (frischer Rechner): direkt starten, dann läuft es bis zum Abmelden
            subprocess.Popen([PYTHON, os.path.join(HIER, "spielen.py")], cwd=HIER,
                             creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            return f"{modus} gestartet (Aufgabe {AUFGABE} fehlt, läuft direkt)"

        start = _rufe(["schtasks", "/run", "/tn", AUFGABE], text=True)
        if start.returncode != 0:
            return f"{AUFGABE} konnte nicht gestartet werden: {start.stdout.strip() or start.stderr.strip()}"
        return f"{modus} läuft — Aufgabe {AUFGABE} gestartet"

    def _installieren(self) -> str:
        daten = lade()
        with open(START_CMD, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write("@echo off\n")
            fh.write("rem Autostart für RAM-Tetris — von einstellungen.py erzeugt\n")
            fh.write('cd /d "%~dp0"\n')
            fh.write(f'"{PYTHON}" spielen.py\n')
        teile = ["start.cmd angelegt"]
        if STARTUP:
            ps = ("$w = New-Object -ComObject WScript.Shell; "
                  f"$s = $w.CreateShortcut('{STARTUP}'); "
                  f"$s.TargetPath = '{START_CMD}'; $s.WorkingDirectory = '{HIER}'; "
                  "$s.WindowStyle = 7; $s.Save()")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            if os.path.exists(STARTUP):
                teile.append("Autostart-Verknüpfung gesetzt")
        subprocess.Popen(["cmd", "/c", "start", "", START_CMD], cwd=HIER)
        teile.append("Spiel gestartet")
        return "installiert: " + ", ".join(teile)

    def _entfernen(self) -> str:
        teile = []
        if STARTUP and os.path.exists(STARTUP):
            os.remove(STARTUP)
            teile.append("Autostart entfernt")
        if os.path.exists(START_CMD):
            os.remove(START_CMD)
            teile.append("start.cmd gelöscht")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" "
                        "| Where-Object { $_.CommandLine -like '*ram_tetris*' } "
                        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)
        teile.append("laufendes Spiel beendet")
        teile.append("iCUE steuert wieder")
        return "entfernt: " + ", ".join(teile)


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    adresse = f"http://127.0.0.1:{PORT}/"
    print(f"RAM-Tetris Einstellungen: {adresse}")
    print("Spielmodus laut Einstellungen:", lade().get("modus", "tetris"))
    print("Beenden mit Strg+C.")
    threading.Timer(0.6, lambda: webbrowser.open(adresse)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbeendet")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
