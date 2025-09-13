Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obține directorul curent al scriptului VBS
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Schimbă la directorul scriptului și rulează aplicația Python direct
objShell.CurrentDirectory = scriptDir

' Activează mediul virtual și rulează aplicația Python fără cmd vizibil
If fso.FileExists(scriptDir & "\.venv\Scripts\python.exe") Then
    ' Folosește Python din mediul virtual
    objShell.Run """" & scriptDir & "\.venv\Scripts\python.exe"" """ & scriptDir & "\grupare facturi.py""", 1, False
Else
    ' Fallback la Python global
    objShell.Run "python """ & scriptDir & "\grupare facturi.py""", 1, False
End If
