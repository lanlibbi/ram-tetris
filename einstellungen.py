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
<title>RAM-Tetris — Farben und Installation</title>
<style>
 :root { color-scheme: dark; }
 body { margin:0; background:#14161a; color:#e7e9ee; font:15px/1.5 "Segoe UI",system-ui,sans-serif; }
 .wrap { max-width:820px; margin:0 auto; padding:28px 22px 60px; }
 h1 { font-size:22px; margin:0 0 4px; }
 h2 { font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#8b93a2;
      margin:30px 0 10px; font-weight:600; }
 p.hinweis { color:#8b93a2; margin:0 0 18px; }
 .reihe { display:flex; gap:14px; flex-wrap:wrap; }
 .farbe { flex:0 0 auto; text-align:center; }
 .farbe label { display:block; font-size:12px; color:#8b93a2; margin-bottom:6px; }
 input[type=color] { width:118px; height:118px; border:2px solid #2a2f38; border-radius:14px;
      background:none; padding:0; cursor:pointer; }
 input[type=color]::-webkit-color-swatch-wrapper { padding:0; }
 input[type=color]::-webkit-color-swatch { border:none; border-radius:11px; }
 .code { font:12px/1 ui-monospace,Consolas,monospace; color:#9aa3b2; margin-top:6px; }
 .vorschau { display:flex; gap:6px; margin:10px 0 0; }
 .vorschau div { height:26px; flex:1; border-radius:5px; }
 .knopfreihe { display:flex; gap:10px; flex-wrap:wrap; margin-top:26px; }
 button { font:inherit; padding:11px 18px; border-radius:10px; border:1px solid #2f3540;
      background:#1e232b; color:#e7e9ee; cursor:pointer; }
 button.haupt { background:#2b6df6; border-color:#2b6df6; font-weight:600; }
 button.warnung { border-color:#5a2a2a; color:#ffb3b3; }
 button:hover { filter:brightness(1.15); }
 .zahlen { display:flex; gap:26px; align-items:flex-end; }
 input[type=number] { width:76px; font:inherit; padding:8px 10px; border-radius:8px;
      border:1px solid #2f3540; background:#1a1e25; color:#e7e9ee; }
 #status { margin-top:22px; min-height:22px; color:#6ee7a0; font-size:14px; }
 footer { margin-top:40px; color:#5f6673; font-size:12px; }
 code { background:#1a1e25; padding:1px 5px; border-radius:4px; }
</style></head><body><div class="wrap">
<h1>RAM-Tetris</h1>
<p class="hinweis">Farben anklicken und im Farbwähler einstellen. Gespeichert wird in
 <code>einstellungen.json</code>; das Spiel liest sie beim Start.</p>

<h2>Farben der Formen</h2>
<div class="reihe" id="palette"></div>
<div class="vorschau" id="vorschau"></div>

<h2>Verloren und Putzen</h2>
<div class="reihe">
  <div class="farbe"><label>Verloren-Blitz</label><input type="color" id="verloren"><div class="code" id="c_verloren"></div></div>
  <div class="farbe"><label>Putz-Wellen</label><input type="color" id="welle"><div class="code" id="c_welle"></div></div>
</div>

<h2>Tempo</h2>
<div class="zahlen">
  <div><label>Bilder je Sekunde<br><small>höher = schneller</small></label>
       <input type="number" id="fps" min="1" max="10" step="1"></div>
  <div><label>Wiedergabe<br><small>2 = doppelt so schnell</small></label>
       <input type="number" id="speed" min="0.5" max="4" step="0.5"></div>
</div>

<div class="knopfreihe">
  <button class="haupt" onclick="speichern()">Speichern</button>
  <button onclick="aktion('probelauf')">Kurz zeigen</button>
  <button onclick="aktion('installieren')">Installieren</button>
  <button class="warnung" onclick="aktion('entfernen')">Entfernen</button>
</div>
<div id="status"></div>
<footer>„Installieren" legt <code>start.cmd</code> an, setzt eine Verknüpfung in den Autostart und
 startet das Spiel. „Entfernen" nimmt beides zurück und beendet das Spiel — iCUE übernimmt dann
 wieder die Beleuchtung.</footer>
</div>
<script>
let daten = __DATEN__;
const farben = ["Farbe 1","Farbe 2","Farbe 3","Farbe 4"];

function bauePalette() {
  const behaelter = document.getElementById('palette');
  behaelter.innerHTML = '';
  daten.palette.forEach((c, i) => {
    const div = document.createElement('div');
    div.className = 'farbe';
    div.innerHTML = `<label>${farben[i] || 'Farbe ' + (i+1)}</label>
      <input type="color" value="${zuHex(c)}" oninput="setzePalette(${i}, this.value)">
      <div class="code" id="c_p${i}">${zuHex(c).toUpperCase()}</div>`;
    behaelter.appendChild(div);
  });
  document.getElementById('verloren').value = zuHex(daten.verloren);
  document.getElementById('welle').value = zuHex(daten.welle);
  document.getElementById('c_verloren').textContent = zuHex(daten.verloren).toUpperCase();
  document.getElementById('c_welle').textContent = zuHex(daten.welle).toUpperCase();
  document.getElementById('fps').value = daten.fps;
  document.getElementById('speed').value = daten.speed;
  vorschau();
}

function zuHex(c) { return '#' + c.map(k => k.toString(16).padStart(2,'0')).join(''); }
function vonHex(h) { return [1,3,5].map(i => parseInt(h.substr(i,2),16)); }

function setzePalette(i, hex) {
  daten.palette[i] = vonHex(hex);
  document.getElementById('c_p' + i).textContent = hex.toUpperCase();
  vorschau();
}

function vorschau() {
  const v = document.getElementById('vorschau');
  v.innerHTML = '';
  const feld = [0,1,2,3,4,5,6,7,8,9];
  daten.palette.forEach(c => {
    const div = document.createElement('div');
    div.style.background = zuHex(c);
    v.appendChild(div);
  });
}

function sammle() {
  daten.verloren = vonHex(document.getElementById('verloren').value);
  daten.welle = vonHex(document.getElementById('welle').value);
  daten.fps = parseInt(document.getElementById('fps').value, 10);
  daten.speed = parseFloat(document.getElementById('speed').value);
}
document.getElementById('verloren').oninput = () => {
  daten.verloren = vonHex(document.getElementById('verloren').value);
  document.getElementById('c_verloren').textContent = document.getElementById('verloren').value.toUpperCase();
};
document.getElementById('welle').oninput = () => {
  daten.welle = vonHex(document.getElementById('welle').value);
  document.getElementById('c_welle').textContent = document.getElementById('welle').value.toUpperCase();
};

async function speichern(still) {
  sammle();
  const r = await fetch('/speichern', {method:'POST', body: JSON.stringify(daten)});
  const t = await r.text();
  if (!still) zeige(t);
  return true;
}

async function aktion(was) {
  await speichern(true);
  const r = await fetch('/' + was, {method:'POST'});
  zeige(await r.text());
}

function zeige(text) {
  const s = document.getElementById('status');
  s.textContent = text;
  clearTimeout(window._t);
  window._t = setTimeout(() => s.textContent = '', 8000);
}
bauePalette();
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
