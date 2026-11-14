' Startet run.cmd ohne Fenster.
' Die Aufgabe "RamLoop" ruft diese Datei auf: wscript.exe ist ein GUI-Programm, deshalb blitzt
' beim Start kein Konsolenfenster auf. run.cmd laeuft mit Fensterstil 0 (versteckt).
Dim shell, fso, ordner, ziel
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ordner = fso.GetParentFolderName(WScript.ScriptFullName)
ziel = ordner & "\run.cmd"
shell.CurrentDirectory = ordner
shell.Run Chr(34) & ziel & Chr(34), 0, False
