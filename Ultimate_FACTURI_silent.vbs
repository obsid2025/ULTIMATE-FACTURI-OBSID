Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c ""cd /d """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & """ && Ultimate_FACTURI.bat""", 7, False
