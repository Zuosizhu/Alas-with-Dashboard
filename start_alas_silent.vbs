Set WshShell = CreateObject("WScript.Shell")
WshShell.Environment("Process")("PYTHONIOENCODING") = "utf-8"
WshShell.Environment("Process")("PYTHONUTF8") = "1"
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\alas_wrapped"
WshShell.Run """.venv\Scripts\python.exe"" gui.py --run PatrickCustom", 0, False
