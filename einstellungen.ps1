# RAM-Tetris - Einstellungen oeffnen.
# Startet den lokalen Server (falls er noch nicht laeuft) und oeffnet die Seite im Browser.
# Laeuft der Server schon, wird nur der Browser geoeffnet - es gibt keinen Port zum Merken.
$ErrorActionPreference = 'Continue'
$hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8787
$url  = "http://127.0.0.1:$port/"

function Test-Port {
    param([int]$Port)
    try {
        $c = New-Object Net.Sockets.TcpClient
        $c.Connect('127.0.0.1', $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

# --- Python finden ---------------------------------------------------------
# Unter Windows liegt eine python.exe im WindowsApps-Ordner, die nur den Microsoft Store
# oeffnet. Sie meldet trotzdem Erfolg - deshalb zaehlt die Ausgabe, nicht der Rueckgabewert.
$kandidaten = @()
$gefunden = Get-Command python -ErrorAction SilentlyContinue
if ($gefunden) { $kandidaten += $gefunden.Source }
$kandidaten += @(
    'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe',
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)
$python = $null
foreach ($k in $kandidaten) {
    if (-not (Test-Path $k)) { continue }
    # Die Store-Attrappe im WindowsApps-Ordner ueberspringen: sie startet nur den Store
    # und schreibt eine Fehlermeldung auf stderr.
    if ($k -like '*\WindowsApps\*') { continue }
    try {
        $aus = (& $k -c "print(7)" 2>&1 | Out-String)
    } catch { $aus = '' }
    if ($aus -match '(?m)^\s*7\s*$') { $python = $k; break }
}
if (-not $python) {
    Write-Host 'Python wurde nicht gefunden.' -ForegroundColor Yellow
    Write-Host 'Bitte Python 3 von python.org installieren und "Add Python to PATH" anhaken.'
    Read-Host 'Enter zum Schliessen'
    exit 1
}
Write-Host "Interpreter: $python"

# --- laeuft schon? ---------------------------------------------------------
if (Test-Port $port) {
    Write-Host 'Server laeuft bereits - oeffne die Seite.'
    Start-Process $url
    exit 0
}

# --- starten ---------------------------------------------------------------
# --- starten ---------------------------------------------------------------
# Zwei Wege, in dieser Reihenfolge:
#   1. existiert die geplante Aufgabe "RamTetrisGui" (auf diesem Rechner so eingerichtet),
#      wird sie gestartet - sie laeuft unabhaengig von diesem Fenster.
#   2. sonst den Interpreter direkt starten.
Write-Host 'Starte den Einstellungs-Server ...'
$task = $null
try { $task = (& schtasks /query /tn RamTetrisGui 2>&1 | Out-String) } catch { $task = $null }
if ($task -and $task -notmatch 'FEHLER|ERROR|cannot find') {
    & schtasks /run /tn RamTetrisGui | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 800
        if (Test-Port $port) { Start-Process $url; exit 0 }
    }
}

$log = Join-Path $env:TEMP 'ramtetris-gui.log'
$p = Start-Process -FilePath $python -ArgumentList 'einstellungen.py' -WorkingDirectory $hier -PassThru
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Milliseconds 700
    if (Test-Port $port) { Start-Process $url; exit 0 }
    if ($p -and $p.HasExited) { break }
}

Write-Host 'Der Server antwortet nicht.' -ForegroundColor Yellow
foreach ($datei in @($log, "$log.err")) {
    if (Test-Path $datei) { Write-Host "--- $datei"; Get-Content $datei -Tail 15 | ForEach-Object { Write-Host $_ } }
}
if ($p -and $p.HasExited) { Write-Host "Prozess beendet, Code $($p.ExitCode)" }
Read-Host 'Enter zum Schliessen'
exit 1
