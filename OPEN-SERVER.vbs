Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
' /k keeps window open forever even if bat fails
sh.Run "cmd.exe /k """ & dir & "\RUN-SERVER.bat""", 1, False
