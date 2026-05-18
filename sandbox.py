# sandbox.py
import json
import tempfile
import os
import time
from datetime import datetime
from secure_exec import SandboxRunner, get_sandbox_pid
from typing import Optional

DEFAULT_VFS = {
    "/sandbox/input.txt": "This is the default input file.\n",
    "/sandbox/output.txt": ""
}

BLOCKED_KEYWORDS = [
    "import os", "import sys", "import subprocess", "import socket",
    "open(", "eval(", "exec(", "compile(", "__import__", "shutil",
    "ctypes", "pickle", "os.", "sys.", "subprocess."
]

def _now():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def contains_dangerous_code(code: str):
    if not code:
        return None
    lower = code.lower()
    for block in BLOCKED_KEYWORDS:
        if block in lower:
            return block
    return None

class SandboxController:
    def __init__(self, timeout=4):
        self.vfs = dict(DEFAULT_VFS)
        self.logs = []
        self.runner = SandboxRunner(timeout=timeout)
        self.timeout = timeout
        self.mem_limit_percent = 25.0  
        self.cpu_limit_percent = 80.0  
        self.last_result = None

    # Logging
    def log(self, text):
        entry = f"{_now()} {text}"
        self.logs.append(entry)
        return entry

    def get_logs(self):
        return "\n".join(self.logs)

    def clear_logs(self):
        self.logs.clear()
        return True

    # VFS operations
    def list_vfs(self):
        return list(self.vfs.keys())

    def read_vfs(self, path):
        return self.vfs.get(path, "")

    def write_vfs(self, path, content):
        self.vfs[path] = content
        self.log(f"Wrote {len(content)} bytes to {path}")
        return True

    def delete_vfs(self, path):
        if path in self.vfs:
            del self.vfs[path]
            self.log(f"Deleted VFS file {path}")
            return True
        return False

    def export_vfs(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.vfs, f, indent=2)
        self.log(f"Exported VFS to {path}")
        return path

    def import_vfs(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            self.vfs = data
            self.log(f"Imported VFS from {path}")
            return True
        return False

    # Execution
    def _make_prelude(self, vfs_json_path):
        """
        Prelude provides read_file / write_file functions that operate on the JSON file path given.
        This allows the child process to update the VFS file which we read back after execution.
        """
        prelude = f'''\
import json
VFS_FILE = r"{vfs_json_path.replace("\\\\","\\\\\\\\")}"

def read_file(path):
    with open(VFS_FILE, "r", encoding="utf-8") as __f:
        v = json.load(__f)
    if path not in v:
        raise Exception("Access denied or file not found in VFS: " + str(path))
    return v[path]

def write_file(path, data):
    with open(VFS_FILE, "r", encoding="utf-8") as __f:
        v = json.load(__f)
    v[path] = data
    with open(VFS_FILE, "w", encoding="utf-8") as __f:
        json.dump(v, __f, indent=2)
'''
        return prelude

    def run_code(self, user_code: str, timeout: Optional[int] = None):
        """
        Execute user code safely with resource limits and VFS handling.
        """
        if timeout is None:
            timeout = self.timeout

        # Block dangerous keywords early
        danger = contains_dangerous_code(user_code)
        if danger:
            self.log(f"Blocked dangerous operation: {danger}")
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"⛔ Blocked dangerous operation or keyword: {danger}"
            }

        # 1) write VFS to temp JSON
        tmp_vfs = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        try:
            json.dump(self.vfs, tmp_vfs, indent=2)
            tmp_vfs.flush()
            tmp_vfs.close()

            # 2) prepare code (prelude + user code)
            prelude = self._make_prelude(tmp_vfs.name)
            safe_code = prelude + "\n# --- USER CODE START ---\n" + user_code + "\n# --- USER CODE END ---\n"

            self.log("Starting execution (timeout={}s, mem_limit={}%, cpu_limit={}%)".format(
                timeout, self.mem_limit_percent, self.cpu_limit_percent))

            # 3) execute - pass resource limits to runner
            result = self.runner.execute(safe_code, timeout=timeout,
                                         mem_limit_percent=self.mem_limit_percent,
                                         cpu_limit_percent=self.cpu_limit_percent)

            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")

            # 4) reload VFS (child may have changed it)
            try:
                with open(tmp_vfs.name, "r", encoding="utf-8") as f:
                    new_vfs = json.load(f)
                if isinstance(new_vfs, dict):
                    self.vfs = new_vfs
                    self.log("VFS updated by executed code.")
            except Exception as e:
                self.log("Could not refresh VFS after run: " + str(e))

            # store last_result for inspection
            self.last_result = {"status": "ok" if not stderr else "error", "stdout": stdout, "stderr": stderr}

            # 5) return info
            if stderr and stderr.strip():
                self.log("Execution finished with errors.")
                return {"status": "error", "stdout": stdout, "stderr": stderr}
            else:
                self.log("Execution finished successfully.")
                return {"status": "ok", "stdout": stdout, "stderr": stderr}

        finally:
            try:
                os.unlink(tmp_vfs.name)
            except Exception:
                pass
