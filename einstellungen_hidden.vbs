' Öffnet die Einstellungsseite ohne Konsolenfenster.
' Die Verknüpfung auf dem Desktop zeigt auf diese Datei (wscript.exe ist ein GUI-Host und hat
' keine Konsole). Die Logik steckt in einstellungen.ps1; Fehler zeigt das Skript als Meldung,
' weil ein verstecktes Fenster nichts anzeigen kann.
Dim shell, fso, ordner, ziel
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ordner = fso.GetParentFolderName(WScript.ScriptFullName)
ziel = ordner & "\einstellungen.ps1"
shell.CurrentDirectory = ordner
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ziel & """", 0, False
