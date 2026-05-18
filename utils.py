# utils.py
import json
from tkinter.filedialog import asksaveasfilename, askopenfilename
import os

def save_text_file_dialog(default_name="script.py", content=""):
    path = asksaveasfilename(defaultextension=".py", initialfile=default_name,
                             filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")])
    if not path:
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def load_text_file_dialog():
    path = askopenfilename(filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")])
    if not path:
        return None, ""
    with open(path, "r", encoding="utf-8") as f:
        return path, f.read()

def save_json_dialog(default_name="vfs.json", data=None):
    path = asksaveasfilename(defaultextension=".json", initialfile=default_name, filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if not path:
        return None
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data or {}, f, indent=2)
    return path

def load_json_dialog():
    path = askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if not path:
        return None, None
    with open(path, "r", encoding="utf-8") as f:
        return path, json.load(f)
