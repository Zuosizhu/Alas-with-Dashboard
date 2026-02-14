Set WshShell = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd /c """ & root & "\start_alas.bat"" --silent"
WshShell.Run cmd, 0, False
