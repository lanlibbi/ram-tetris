# RAM Games - Einstellungen öffnen.
# Startet den lokalen Server (falls er noch nicht läuft) und öffnet die Seite im Browser.
# Läuft der Server schon, wird nur der Browser geöffnet – es gibt keinen Port zum Merken.
#
# Wird normalerweise versteckt aufgerufen (einstellungen_hidden.vbs), deshalb gibt es keine
# Write-Host-Ausgaben mehr: Fehler erscheinen als Meldungsfenster und landen zusätzlich im
# Protokoll. Wer zusehen will, startet diese Datei direkt in einer PowerShell.
$ErrorActionPreference = 'Continue'
$hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8787
$url  = "http://127.0.0.1:$port/"
$log  = Join-Path $env:TEMP 'ram-games-einstellungen.log'

function Sag($text) {
    try { Add-Content -Path $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $text) } catch {}
}

function Meldung($text) {
    try { (New-Object -ComObject WScript.Shell).Popup($text, 0, 'RAM Games', 16) | Out-Null } catch {}
    Sag "MELDUNG: $text"
}

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
# öffnet. Sie meldet trotzdem Erfolg – deshalb zählt die Ausgabe, nicht der Rückgabewert.
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
    if ($k -like '*\WindowsApps\*') { continue }
    try { $aus = (& $k -c "print(7)" 2>&1 | Out-String) } catch { $aus = '' }
    if ($aus -match '(?m)^\s*7\s*$') { $python = $k; break }
}
if (-not $python) {
    Meldung "Python wurde nicht gefunden.`n`nBitte Python 3 von python.org installieren (»Add Python to PATH« anhaken) oder Blender installieren."
    exit 1
}
Sag "Interpreter: $python"

# --- läuft schon? ----------------------------------------------------------
if (Test-Port $port) {
    Sag 'Server läuft bereits – öffne nur den Browser'
    Start-Process $url
    exit 0
}

# --- starten ---------------------------------------------------------------
# Zwei Wege, in dieser Reihenfolge:
#   1. existiert die geplante Aufgabe "RamTetrisGui" (auf diesem Rechner so eingerichtet),
#      wird sie gestartet – sie läuft unabhängig von diesem Prozess.
#   2. sonst den Interpreter direkt und versteckt starten.
Sag 'starte den Einstellungs-Server'
$task = $null
try { $task = (& schtasks /query /tn RamTetrisGui 2>&1 | Out-String) } catch { $task = $null }
if ($task -and $task -notmatch 'FEHLER|ERROR|cannot find') {
    & schtasks /run /tn RamTetrisGui | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 800
        if (Test-Port $port) { Sag 'Seite offen'; Start-Process $url; exit 0 }
    }
}

$p = Start-Process -FilePath $python -ArgumentList 'einstellungen.py' -WorkingDirectory $hier `
    -PassThru -WindowStyle Hidden
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Milliseconds 700
    if (Test-Port $port) { Sag 'Seite offen'; Start-Process $url; exit 0 }
    if ($p -and $p.HasExited) { break }
}

Sag "Server antwortet nicht (Prozess beendet: $($p.HasExited), Code $($p.ExitCode))"
Meldung "Der Einstellungs-Server antwortet nicht.`n`nProtokoll: $log"
exit 1
