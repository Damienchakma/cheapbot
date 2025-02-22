import os
import sys
import win32com.client

def create_shortcut(
    shortcut_name="CheapGPT.lnk",
    target_script="chatbot_app.py",
    icon_file="pig.ico"
):
    """
    Creates a Windows shortcut on the Desktop referencing `target_script`
    with an icon from `icon_file`.
    """
    shell = win32com.client.Dispatch("WScript.Shell")

    desktop = shell.SpecialFolders("Desktop")
    shortcut_path = os.path.join(desktop, shortcut_name)

    shortcut = shell.CreateShortcut(shortcut_path)
    # Full path to python.exe or pythonw.exe
    python_exe = sys.executable

    # Example: "C:\Path\To\python.exe" "C:\Path\To\cheapgpt_app.py"
    # Adjust if you want pythonw.exe to avoid a console window
    shortcut.TargetPath = python_exe
    # We pass the script as an argument
    script_full = os.path.abspath(target_script)
    shortcut.Arguments = f'"{script_full}"'
    # Use the same directory as the script as the working dir
    shortcut.WorkingDirectory = os.path.dirname(script_full)

    # Icon
    icon_full = os.path.abspath(icon_file)
    if os.path.exists(icon_full):
        shortcut.IconLocation = icon_full
    else:
        print("Warning: Icon file not found. Using default icon.")

    shortcut.WindowStyle = 1  # Normal window
    shortcut.Description = "Launch CheapGPT"
    shortcut.Save()

if __name__ == "__main__":
    create_shortcut()
    print("Shortcut created on Desktop.")
