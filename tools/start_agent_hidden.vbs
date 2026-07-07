' Starts the capture agent with NO console window — for truly hands-off running.
' Put a shortcut to this file in your Startup folder (Win+R -> shell:startup) and
' the agent runs silently every time you log in.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("Wscript.Shell").Run "python """ & scriptDir & "\capture_agent.py""", 0, False
