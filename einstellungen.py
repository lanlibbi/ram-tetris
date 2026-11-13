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
}


def lade() -> dict:
    daten = json.loads(json.dumps(VORGABE))
    if os.path.exists(KONFIG):
        try:
            gelesen = json.loads(open(KONFIG, encoding="utf-8").read())
            for schluessel in daten:
                if schluessel in gelesen:
                    daten[schluessel] = gelesen[schluessel]
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
<title>RAM-Tetris — Farben und Installation</title>
<style>
  :root{
    color-scheme: dark;
    --bg:#0e1014; --bg2:#141821; --card:#171b23; --linie:#252b36;
    --text:#e9ecf2; --gedimmt:#8d95a6; --akzent:#4c8dff; --akzent2:#8b5cf6;
    --gut:#3ddc97; --warn:#ff7a7a;
    --radius:16px;
  }
  *{box-sizing:border-box}
  body{
    margin:0; min-height:100vh; color:var(--text);
    font:15px/1.55 ui-sans-serif,system-ui,"Segoe UI",Inter,sans-serif;
    background:
      radial-gradient(1100px 600px at 12% -8%, rgba(76,141,255,.14), transparent 60%),
      radial-gradient(900px 500px at 92% 4%, rgba(139,92,246,.12), transparent 62%),
      var(--bg);
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:900px; margin:0 auto; padding:44px 22px 80px}

  header.kopf{margin-bottom:30px}
  .marke{display:flex; align-items:center; gap:13px}
  .logo{width:40px;height:40px;border-radius:12px;flex:0 0 auto;
    background:linear-gradient(135deg,var(--akzent),var(--akzent2));
    display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:3px;padding:7px}
  .logo i{border-radius:2px;background:#0e1014cc}
  .logo i:nth-child(1){background:#ffd200}
  .logo i:nth-child(2){background:#0a28aa}
  .logo i:nth-child(3){background:#ff1e1e}
  .logo i:nth-child(4){background:#fff}
  h1{font-size:26px;margin:0;letter-spacing:-.02em;font-weight:650}
  .unter{color:var(--gedimmt);margin:6px 0 0;font-size:14px;max-width:60ch}

  .karte{
    background:linear-gradient(180deg,rgba(255,255,255,.02),transparent 40%),var(--card);
    border:1px solid var(--linie); border-radius:var(--radius);
    padding:22px; margin-top:18px;
  }
  .karte > h2{
    font-size:12px; text-transform:uppercase; letter-spacing:.11em; color:var(--gedimmt);
    margin:0 0 16px; font-weight:600; display:flex; align-items:center; gap:9px;
  }
  .karte > h2::after{content:""; flex:1; height:1px; background:var(--linie)}

  .farben{display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:14px}
  .kachel{position:relative; cursor:pointer; border:0; padding:0; background:none; font:inherit;
    color:inherit; text-align:left; transition:transform .14s ease}
  .kachel:hover{transform:translateY(-2px)}
  .kachel:focus-visible{outline:2px solid var(--akzent); outline-offset:3px; border-radius:16px}
  .kachel .farbe{
    height:112px; border-radius:14px; border:1px solid #00000055;
    box-shadow:inset 0 1px 0 #ffffff2e, inset 0 -18px 40px #00000055, 0 8px 22px -14px #000;
    position:relative; overflow:hidden;
  }
  .kachel .farbe::after{
    content:""; position:absolute; inset:0 auto auto 0; width:100%; height:44%;
    background:linear-gradient(180deg,rgba(255,255,255,.16),transparent);
  }
  .kachel .name{font-size:12.5px; margin-top:9px; color:var(--gedimmt)}
  .kachel .hex{
    position:absolute; bottom:8px; right:9px; font:11px/1 ui-monospace,Consolas,monospace;
    color:#000000a6; background:#ffffffcc; padding:4px 6px; border-radius:6px; letter-spacing:.04em;
  }
  .kachel input[type=color]{position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%}
  .kachel.welle .farbe::before{
    content:""; position:absolute; inset:0; z-index:0;
    background:linear-gradient(105deg,transparent 20%,#ffffff66 42%,#ffffffaa 50%,#ffffff66 58%,transparent 80%);
    background-size:220% 100%; animation:welle 3.6s linear infinite}
  @keyframes welle{from{background-position:180% 0} to{background-position:-80% 0}}
  .kachel .farbe > .hex{z-index:2}
  button.aktion.hinweis{border-color:#2f4d7a; color:#a9c8ff; background:#111a26}
  footer a{color:#7ea6ff; text-decoration:none}
  footer a:hover{text-decoration:underline}

  .vorschau-karte{display:flex; gap:22px; flex-wrap:wrap; align-items:flex-start}
  .brett{display:grid; grid-template-columns:repeat(4,24px); gap:4px;
    padding:13px; border-radius:13px; background:#0b0d11; border:1px solid var(--linie);
    box-shadow:inset 0 0 26px #00000088}
  .brett span{width:24px;height:15px;border-radius:3px;background:#181d26;
    box-shadow:inset 0 1px 0 #ffffff10}
  .legende{color:var(--gedimmt); font-size:12.5px; max-width:34ch}
  .legende b{color:var(--text); font-weight:600}

  .zahlen{display:flex; gap:24px; flex-wrap:wrap}
  .feld label{display:block; font-size:12.5px; color:var(--gedimmt); margin-bottom:7px}
  .feld small{display:block; color:#69707f; font-size:11.5px}
  input[type=number]{
    width:96px; font:15px/1 inherit; padding:11px 12px; border-radius:10px;
    border:1px solid var(--linie); background:#101319; color:var(--text);
  }
  input[type=number]:focus{outline:none; border-color:var(--akzent); box-shadow:0 0 0 3px #4c8dff33}

  .chips{display:flex; gap:9px; flex-wrap:wrap; margin-top:4px}
  .chip{border:1px solid var(--linie); background:#101319; color:#c9d1e0; border-radius:999px;
    padding:8px 14px; font-size:13px; cursor:pointer; display:flex; align-items:center; gap:8px;
    transition:border-color .15s, background .15s}
  .chip:hover{border-color:#3a4050; background:#161b24}
  .chip i{width:12px;height:12px;border-radius:3px;display:inline-block}

  .leiste{display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-top:6px}
  button.aktion{
    font:inherit; font-weight:550; padding:12px 20px; border-radius:11px; cursor:pointer;
    border:1px solid var(--linie); background:#1a1f28; color:var(--text);
    transition:transform .12s ease, filter .15s ease, border-color .15s
  }
  button.aktion:hover{filter:brightness(1.16)}
  button.aktion:active{transform:translateY(1px)}
  button.haupt{border:0; background:linear-gradient(135deg,var(--akzent),var(--akzent2));
    box-shadow:0 10px 24px -12px #4c8dff}
  button.gefahr{color:var(--warn); border-color:#4a2a2f; background:#1d1417}
  .abstand{flex:1}

  #status{
    margin-top:16px; min-height:0; font-size:13.5px; color:var(--gut);
    opacity:0; transform:translateY(-3px); transition:opacity .2s, transform .2s;
  }
  #status.an{opacity:1; transform:none}
  footer{margin-top:30px; color:#596071; font-size:12.5px; line-height:1.7}
  code{background:#101319; border:1px solid var(--linie); padding:1px 6px; border-radius:5px;
    font:12px/1.4 ui-monospace,Consolas,monospace; color:#b9c2d4}
</style></head>
<body><div class="wrap">

<header class="kopf">
  <div class="marke">
    <div class="logo"><i></i><i></i><i></i><i></i></div>
    <div>
      <h1>RAM-Tetris</h1>
      <p class="unter">Farben, Sondersequenzen und Tempo. Alles was du hier einstellst, landet in
        <code>einstellungen.json</code> und gilt ab dem nächsten Start.</p>
    </div>
  </div>
</header>

<section class="karte">
  <h2>Farben der Formen</h2>
  <div class="farben" id="palette"></div>
</section>

<section class="karte">
  <h2>Verloren und Putzen</h2>
  <div class="farben" id="sondersequenzen"></div>
</section>

<section class="karte">
  <h2>Vorschau</h2>
  <div class="vorschau-karte">
    <div class="brett" id="brett"></div>
    <div class="legende">
      So sieht das Feld aus: <b>10 Reihen × 4 Spalten</b>, jeder Riegel eine Spalte.
      Oben fallen die Formen hinein, drei gleiche Farben waagerecht oder senkrecht verschwinden.<br><br>
      Ist eine Spalte voll, blinkt alles in der Farbe <b>Verloren-Blitz</b>, danach laufen die
      <b>Putz-Wellen</b> durch und es beginnt von vorn.
    </div>
  </div>
</section>

<section class="karte">
  <h2>Beliebte Paletten</h2>
  <div class="chips" id="chips"></div>
</section>

<section class="karte">
  <h2>Tempo</h2>
  <div class="zahlen">
    <div class="feld">
      <label>Bilder je Sekunde</label>
      <input type="number" id="fps" min="1" max="10" step="1">
      <small>höher = schneller</small>
    </div>
    <div class="feld">
      <label>Wiedergabe</label>
      <input type="number" id="speed" min="0.5" max="4" step="0.5">
      <small>2 = doppelt so schnell</small>
    </div>
  </div>
</section>

<section class="karte">
  <h2>Installation</h2>
  <div class="leiste">
    <button class="aktion haupt" onclick="speichern()">Speichern</button>
    <button class="aktion" onclick="aktion('probelauf')">Kurz zeigen</button>
    <button class="aktion hinweis" onclick="aktion('installieren')">Installieren</button>
    <button class="aktion gefahr" onclick="aktion('entfernen')">Entfernen</button>
  </div>
  <div id="status"></div>
  <footer>
    <b>Installieren</b> legt <code>start.cmd</code> an, setzt eine Verknüpfung in den
    Autostart-Ordner und startet das Spiel — ab dann läuft es bei jeder Anmeldung.<br>
    <b>Entfernen</b> nimmt beides zurück und beendet das Spiel; iCUE steuert die Riegel danach wieder.
    <br><br>Projekt: <a href="https://github.com/lanlibbi/ram-tetris" target="_blank" rel="noopener">github.com/lanlibbi/ram-tetris</a>
  </footer>
</section>

</div>
<script>
const NAMEN = ["Form 1","Form 2","Form 3","Form 4"];
// Grobe Farbnamen, damit unter der Kachel nicht nur "Form 2" steht
function farbname(c){
  const [r,g,b] = c.map(k => k/255);
  const max = Math.max(r,g,b), min = Math.min(r,g,b), d = max-min;
  if (max < 0.12) return "Schwarz";
  if (d < 0.10) return max > 0.86 ? "Weiß" : (max > 0.45 ? "Grau" : "Dunkelgrau");
  let h = 0;
  if (max === r) h = ((g-b)/d) % 6; else if (max === g) h = (b-r)/d + 2; else h = (r-g)/d + 4;
  h = (h*60+360)%360;
  const hell = max > 0.85 && d < 0.35;
  if (h < 15 || h >= 345) return hell ? "Hellrot" : "Rot";
  if (h < 40) return hell ? "Orange" : "Orange";
  if (h < 70) return max > 0.8 ? "Gelb" : "Oliv";
  if (h < 160) return max > 0.8 ? "Grün" : "Dunkelgrün";
  if (h < 200) return hell ? "Türkis" : "Petrol";
  if (h < 250) return max > 0.8 ? "Hellblau" : "Dunkelblau";
  if (h < 290) return "Violett";
  return hell ? "Rosa" : "Magenta";
}
const PALETTEN = [
  {name:"Vorgabe",   p:["#ffd200","#0a28aa","#ff1e1e","#ffffff"]},
  {name:"Neon",      p:["#39ff14","#00e5ff","#ff00d4","#fff9b0"]},
  {name:"Eis",       p:["#7fd4ff","#2b6df6","#b6f0ff","#ffffff"]},
  {name:"Glut",      p:["#ff3b00","#ff9d00","#ffd200","#fff3d6"]},
  {name:"Gameboy",   p:["#9bbc0f","#8bac0f","#306230","#e0f8d0"]},
  {name:"Mitternacht",p:["#4c8dff","#8b5cf6","#22d3ee","#e9ecf2"]}
];
let daten = __DATEN__;

const hex = c => '#' + c.map(k => k.toString(16).padStart(2,'0')).join('');
const vonHex = h => [1,3,5].map(i => parseInt(h.substr(i,2),16));

function kachel(id, titel, farbe, beiAenderung, extraKlasse){
  const b = document.createElement('button');
  b.className = 'kachel' + (extraKlasse ? ' ' + extraKlasse : '');
  b.type = 'button';
  b.innerHTML = `<div class="farbe" style="background:${hex(farbe)}">
      <span class="hex">${hex(farbe).slice(1).toUpperCase()}</span>
      <input type="color" value="${hex(farbe)}" aria-label="${titel}">
    </div><div class="name">${titel} · ${farbname(farbe)}</div>`;
  const eingabe = b.querySelector('input');
  eingabe.addEventListener('input', e => {
    const neu = vonHex(e.target.value);
    beiAenderung(neu);
    b.querySelector('.farbe').style.background = e.target.value;
    b.querySelector('.hex').textContent = e.target.value.slice(1).toUpperCase();
    b.querySelector('.name').textContent = titel + ' · ' + farbname(neu);
    vorschauBrett();
  });
  b.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') eingabe.click(); });
  if (id) b.id = id;
  return b;
}

function baue(){
  const p = document.getElementById('palette');
  p.innerHTML = '';
  daten.palette.forEach((c,i) => p.appendChild(
    kachel('k'+i, NAMEN[i] || ('Form '+(i+1)), c, neu => daten.palette[i] = neu)));

  const s = document.getElementById('sondersequenzen');
  s.innerHTML = '';
  s.appendChild(kachel(null, 'Verloren-Blitz', daten.verloren, neu => daten.verloren = neu));
  s.appendChild(kachel(null, 'Putz-Wellen', daten.welle, neu => daten.welle = neu, 'welle'));

  const chips = document.getElementById('chips');
  chips.innerHTML = '';
  PALETTEN.forEach(v => {
    const c = document.createElement('button');
    c.className = 'chip';
    c.type = 'button';
    c.innerHTML = v.p.map(f => `<i style="background:${f}"></i>`).join('') + `<span>${v.name}</span>`;
    c.onclick = () => { daten.palette = v.p.map(vonHex); baue(); vorschauBrett(); };
    chips.appendChild(c);
  });

  document.getElementById('fps').value = daten.fps;
  document.getElementById('speed').value = daten.speed;
  vorschauBrett();
}

function vorschauBrett(){
  const brett = document.getElementById('brett');
  const f = daten.palette;
  const muster = [0,1,2,3,1,0,3,2,2,3,0,1,3,2,1,0,1,1,2,2,0,3,3,0,2,0,1,3,3,1,0,2,0,2,3,1,2,1,0,3];
  brett.innerHTML = '';
  muster.forEach((k,i) => {
    const s = document.createElement('span');
    const leer = i < 8;                 // oben ein paar Lücken wie im Spiel
    if (!leer) s.style.background = hex(f[k % f.length]);
    brett.appendChild(s);
  });
}

function sammle(){
  daten.fps = parseInt(document.getElementById('fps').value,10) || 3;
  daten.speed = parseFloat(document.getElementById('speed').value) || 2;
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
        if self.path in ("/", "/index.html"):
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

        if self.path == "/installieren":
            self._sende(self._installieren())
            return

        if self.path == "/entfernen":
            self._sende(self._entfernen())
            return

        self._sende("unbekannte Aktion", 404)

    # -- Aktionen -------------------------------------------------------
    def _installieren(self) -> str:
        daten = lade()
        with open(START_CMD, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write("@echo off\n")
            fh.write("rem Autostart für RAM-Tetris — von einstellungen.py erzeugt\n")
            fh.write('cd /d "%~dp0"\n')
            fh.write(f'"{PYTHON}" ram_tetris.py --replay "{AUFNAHME}" --loop --speed {daten.get("speed", 2)}\n')
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
