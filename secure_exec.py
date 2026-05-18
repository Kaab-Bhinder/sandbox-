# secure_exec.py
import sys
import subprocess
import tempfile
import os
import traceback
import time
import psutil
from typing import Optional

# Global handle to currently running process
_current_process: Optional[subprocess.Popen] = None

def _set_current_process(proc: Optional[subprocess.Popen]):
    global _current_process
    _current_process = proc

def get_sandbox_pid():
    """Return PID of currently running sandbox process (or None)."""
    global _current_process
    if _current_process is not None:
        return _current_process.pid
    return None

def force_kill():
    """Forcefully kill the running sandbox process if any. Returns True if killed."""
    global _current_process
    if _current_process is None:
        return False
    try:
        _current_process.kill()
        # Clear handle
        _set_current_process(None)
        return True
    except Exception:
        return False

def execute_python_file(file_path: str, timeout: int, mem_limit_percent: Optional[float]=None, cpu_limit_percent: Optional[float]=None):
    """
    Run Python file in a subprocess, monitor resource usage and enforce limits.
    Returns dict with stdout, stderr, returncode.
    If limits are exceeded, process is killed and stderr explains why.
    """
    global _current_process
    try:
        proc = subprocess.Popen(
            [sys.executable, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        _set_current_process(proc)

        # create psutil.Process for monitoring
        try:
            ps_proc = psutil.Process(proc.pid)
        except Exception:
            ps_proc = None

        stdout_chunks = []
        stderr_chunks = []

        start_time = time.time()
        # We'll poll while process is alive; read stdout/stderr on completion
        while True:
            # check if finished
            if proc.poll() is not None:
                # process ended
                break

            now = time.time()
            elapsed = now - start_time
            if timeout is not None and elapsed > timeout:
                try:
                    proc.kill()
                except Exception:
                    pass
                _set_current_process(None)
                return {
                    "stdout": "",
                    "stderr": f"⛔ Timeout: Execution exceeded {timeout} seconds",
                    "returncode": None
                }

            # resource checks
            if ps_proc is not None:
                try:
                    # memory_percent may be instant value
                    mem_pct = ps_proc.memory_percent()
                    # cpu_percent requires an interval; we use a non-blocking call with small sleep later
                    cpu_pct = ps_proc.cpu_percent(interval=0.1)
                except Exception:
                    mem_pct = cpu_pct = 0.0

                if mem_limit_percent is not None and mem_pct is not None:
                    if mem_pct > mem_limit_percent:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        _set_current_process(None)
                        return {
                            "stdout": "",
                            "stderr": f"⛔ Memory limit exceeded ({mem_pct:.2f}% > {mem_limit_percent}%).",
                            "returncode": None
                        }

                if cpu_limit_percent is not None and cpu_pct is not None:
                    # cpu_percent is percent of a single logical CPU — this is approximate.
                    if cpu_pct > cpu_limit_percent:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        _set_current_process(None)
                        return {
                            "stdout": "",
                            "stderr": f"⛔ CPU limit exceeded ({cpu_pct:.2f}% > {cpu_limit_percent}%).",
                            "returncode": None
                        }

            # short sleep to avoid busy loop
            time.sleep(0.05)

        # Process finished; read stdout/stderr
        try:
            stdout, stderr = proc.communicate(timeout=1)
        except Exception:
            # fallback: try to read without timeout
            stdout, stderr = proc.communicate()

        _set_current_process(None)
        return {
            "stdout": stdout or "",
            "stderr": stderr or "",
            "returncode": proc.returncode
        }

    except Exception:
        _set_current_process(None)
        return {
            "stdout": "",
            "stderr": "⛔ Sandbox internal error:\n" + traceback.format_exc(),
            "returncode": None
        }

class SandboxRunner:
    def __init__(self, timeout=4):
        self.timeout = timeout

    def execute(self, code: str, timeout: int = None, mem_limit_percent: Optional[float]=None, cpu_limit_percent: Optional[float]=None):
        """
        Write code to a temp file and execute it in a new Python process.
        This wrapper forwards resource limits to execute_python_file.
        """
        if timeout is None:
            timeout = self.timeout

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
        try:
            tmp.write(code)
            tmp.flush()
            tmp.close()

            result = execute_python_file(tmp.name, timeout=timeout, mem_limit_percent=mem_limit_percent, cpu_limit_percent=cpu_limit_percent)

            return result

        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
