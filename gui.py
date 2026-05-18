import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog
import threading
import psutil
import time

from sandbox import SandboxController
from utils import save_text_file_dialog, load_text_file_dialog, save_json_dialog, load_json_dialog
from secure_exec import force_kill, get_sandbox_pid

# Theme colors
BG = "#0d0f17"
PANEL = "#11121A"
ACCENT = "#666DF6"
ACCENT2 = "#B066FF"
TEXT = "#E8EEF6"
NEON = "#4DFF91"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_TITLE = "Secure Sandbox Executor"

class FuturisticApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=BG)

        self.controller = SandboxController(timeout=5)

        self._build_ui()
        self._start_stats_thread()

    def _build_ui(self):
        sidebar = ctk.CTkFrame(self, width=220, fg_color=PANEL, corner_radius=8)
        sidebar.grid(row=0, column=0, padx=12, pady=12, sticky="ns")
        sidebar.grid_rowconfigure(20, weight=1)
        
        menu_frame = ctk.CTkFrame(sidebar, fg_color=PANEL, corner_radius=0)
        menu_frame.grid(row=0, column=0, pady=(12,12), sticky="ew")
        ctk.CTkLabel(menu_frame, text="MENU", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0,6))

        def make_btn(frame, text, cmd, color=ACCENT):
            return ctk.CTkButton(frame, text=text, command=cmd,
                                 fg_color=color, hover_color="#00a3d6", corner_radius=10, height=32)
        make_btn(menu_frame, "Run (Ctrl+Enter)", self._on_run).pack(fill="x", padx=12, pady=4)
        make_btn(menu_frame, "Stop", self._on_stop).pack(fill="x", padx=12, pady=4)
        make_btn(menu_frame, "Save Code", self._on_save_code).pack(fill="x", padx=12, pady=4)
        make_btn(menu_frame, "Load Code", self._on_load_code).pack(fill="x", padx=12, pady=4)

        # VFS Frame
        vfs_frame = ctk.CTkFrame(sidebar, fg_color=PANEL, corner_radius=0)
        vfs_frame.grid(row=1, column=0, pady=(6,12), sticky="ew")
        ctk.CTkLabel(vfs_frame, text="VFS", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(4,6))
        make_btn(vfs_frame, "Export VFS", self._on_export_vfs, ACCENT2).pack(fill="x", padx=12, pady=4)
        make_btn(vfs_frame, "Import VFS", self._on_import_vfs, ACCENT2).pack(fill="x", padx=12, pady=4)

        # System Frame
        system_frame = ctk.CTkFrame(sidebar, fg_color=PANEL, corner_radius=0)
        system_frame.grid(row=2, column=0, pady=(6,12), sticky="ew")
        ctk.CTkLabel(system_frame, text="SYSTEM", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(4,6))
        self.cpu_lbl = ctk.CTkLabel(system_frame, text="CPU: --%")
        self.cpu_lbl.pack(padx=12, pady=(2,2))
        self.cpu_bar = ctk.CTkProgressBar(system_frame, width=180, fg_color="#222733", progress_color=NEON)
        self.cpu_bar.pack(padx=12, pady=(0,6))
        self.mem_lbl = ctk.CTkLabel(system_frame, text="RAM: --%")
        self.mem_lbl.pack(padx=12, pady=(2,2))
        self.mem_bar = ctk.CTkProgressBar(system_frame, width=180, fg_color="#222733", progress_color=ACCENT2)
        self.mem_bar.pack(padx=12, pady=(0,6))

        # ---------------- Center: Editor + Terminal ----------------
        center = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        center.grid(row=0, column=1, padx=(0,12), pady=12, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # PanedWindow for resizable editor + terminal
        split = tk.PanedWindow(center, orient="vertical", sashrelief="raised", sashwidth=8, bg="#11121A")
        split.grid(row=0, column=0, sticky="nsew")
        center.grid_rowconfigure(0, weight=1)
        center.grid_columnconfigure(0, weight=1)

        # Editor Frame
        editor_frame = ctk.CTkFrame(split, fg_color="#0f1116", corner_radius=10)
        self.code_text = tk.Text(editor_frame, wrap="none", bg="#0b0c10", fg=TEXT, insertbackground=TEXT,
                                 font=("Consolas", 13), padx=10, pady=10, relief="flat", undo=True)
        self.code_text.pack(fill="both", expand=True, padx=6, pady=6)
        split.add(editor_frame, minsize=300)

        # Terminal Frame
        terminal_frame = ctk.CTkFrame(split, fg_color="#08090b", corner_radius=10)
        self.terminal = scrolledtext.ScrolledText(terminal_frame, height=12, bg="#030304", fg=NEON,
                                                  insertbackground=NEON, font=("Consolas", 12), relief="flat")
        self.terminal.pack(fill="both", expand=True, padx=6, pady=6)
        split.add(terminal_frame, minsize=150)

        # Sample starter code
        sample = (
            "# Welcome to Secure Sandbox \n"
            "print('Hello from Sandbox')\n\n"
            "# You can read and write VFS files:\n"
            "try:\n"
            "    print('VFS input content:')\n"
            "    print(read_file('/sandbox/input.txt'))\n"
            "    write_file('/sandbox/output.txt', 'Result from sandbox at runtime')\n"
            "except Exception as e:\n"
            "    print('VFS error:', e)\n"
        )
        self.code_text.insert("1.0", sample)

        # ---------------- Right Panel: Tabs ----------------
        right = ctk.CTkFrame(self, width=360, fg_color=PANEL, corner_radius=8)
        right.grid(row=0, column=2, padx=(0,12), pady=12, sticky="ns")
        right.grid_rowconfigure(1, weight=1)

        tabs = ctk.CTkTabview(right, width=340, height=640)
        tabs.grid(row=0, column=0, padx=12, pady=12, sticky="n")
        tabs.add("VFS")
        tabs.add("Logs")
        tabs.add("Settings")

        # VFS tab
        vfs_tab = ctk.CTkFrame(tabs.tab("VFS"))
        vfs_tab.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(vfs_tab, text="Virtual Filesystem", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(4,6))
        self.vfs_listbox = tk.Listbox(vfs_tab, bg="#0b0c10", fg=TEXT, relief="flat", selectbackground="#222733", font=("Consolas", 11))
        self.vfs_listbox.pack(fill="both", expand=True, padx=6, pady=(0,6))
        vfs_buttons = ctk.CTkFrame(vfs_tab)
        vfs_buttons.pack(fill="x", pady=4)
        ctk.CTkButton(vfs_buttons, text="Open", command=self._vfs_open).pack(side="left", padx=6)
        ctk.CTkButton(vfs_buttons, text="New", command=self._vfs_new).pack(side="left", padx=6)
        ctk.CTkButton(vfs_buttons, text="Delete", command=self._vfs_delete).pack(side="left", padx=6)
        ctk.CTkButton(vfs_buttons, text="Save VFS", command=self._export_vfs).pack(side="left", padx=6)

        # Logs tab
        logs_tab = ctk.CTkFrame(tabs.tab("Logs"))
        logs_tab.pack(fill="both", expand=True, padx=8, pady=8)
        self.logs_text = scrolledtext.ScrolledText(logs_tab, bg="#060608", fg=TEXT, font=("Consolas", 10))
        self.logs_text.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkButton(logs_tab, text="Export Logs", command=self._export_logs).pack(pady=6)

        # Settings tab
        settings_tab = ctk.CTkFrame(tabs.tab("Settings"))
        settings_tab.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(settings_tab, text="Execution Timeout (seconds)").pack(anchor="w", pady=(6,2))
        self.timeout_spin = ctk.CTkSlider(settings_tab, from_=1, to=30, number_of_steps=29)
        self.timeout_spin.set(self.controller.timeout)
        self.timeout_spin.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(settings_tab, text="(Slide to change timeout)").pack(anchor="w", pady=(2,12))

        # Resource limits
        ctk.CTkLabel(settings_tab, text="Memory Limit (%)").pack(anchor="w")
        self.mem_limit = ctk.CTkSlider(settings_tab, from_=5, to=90, number_of_steps=85)
        self.mem_limit.set(self.controller.mem_limit_percent)
        self.mem_limit.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(settings_tab, text="CPU Limit (%)").pack(anchor="w")
        self.cpu_limit = ctk.CTkSlider(settings_tab, from_=5, to=100, number_of_steps=95)
        self.cpu_limit.set(self.controller.cpu_limit_percent)
        self.cpu_limit.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(settings_tab, text="(These limits apply to the sandboxed process)").pack(anchor="w", pady=(6,0))

        # populate VFS list initially
        self._refresh_vfs_list()

        # keyboard shortcut: Ctrl+Enter runs
        self.bind_all("<Control-Return>", lambda e: self._on_run())

    # ----------------- VFS / Logs / Terminal / Execution ----------------
    def _refresh_vfs_list(self):
        self.vfs_listbox.delete(0, tk.END)
        for key in self.controller.list_vfs():
            self.vfs_listbox.insert(tk.END, key)

    def _vfs_open(self):
        sel = self.vfs_listbox.curselection()
        if not sel:
            messagebox.showinfo("VFS", "Select a file first.")
            return
        path = self.vfs_listbox.get(sel[0])
        content = self.controller.read_vfs(path)
        editor = tk.Toplevel(self)
        editor.title(f"Edit VFS: {path}")
        txt = scrolledtext.ScrolledText(editor, width=80, height=25, bg="#0b0c10", fg=TEXT)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", content)

        def save_and_close():
            self.controller.write_vfs(path, txt.get("1.0", "end"))
            self._refresh_vfs_list()
            editor.destroy()

        ctk.CTkButton(editor, text="Save", command=save_and_close).pack(pady=6)

    def _vfs_new(self):
        name = simpledialog.askstring("New VFS File", "Enter new VFS path (e.g. /sandbox/new.txt):")
        if not name:
            return
        if name in self.controller.vfs:
            messagebox.showwarning("VFS", "File already exists.")
            return
        self.controller.write_vfs(name, "")
        self._refresh_vfs_list()

    def _vfs_delete(self):
        sel = self.vfs_listbox.curselection()
        if not sel:
            return
        path = self.vfs_listbox.get(sel[0])
        if messagebox.askyesno("Delete", f"Delete {path}?"):
            self.controller.delete_vfs(path)
            self._refresh_vfs_list()

    def _export_vfs(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
        if not path:
            return
        self.controller.export_vfs(path)
        messagebox.showinfo("Export", f"VFS exported to {path}")

    def _export_logs(self):
        path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files","*.log"),("Text files","*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.controller.get_logs())
        messagebox.showinfo("Export", f"Logs saved to {path}")

    def _append_terminal(self, text):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text + "\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def _on_run(self):
        code = self.code_text.get("1.0", "end")
        timeout_val = int(self.timeout_spin.get())
        # Update controller limits from UI
        try:
            mem_lim = float(self.mem_limit.get())
            cpu_lim = float(self.cpu_limit.get())
        except Exception:
            mem_lim = self.controller.mem_limit_percent
            cpu_lim = self.controller.cpu_limit_percent

        self.controller.timeout = timeout_val
        self.controller.mem_limit_percent = mem_lim
        self.controller.cpu_limit_percent = cpu_lim

        self._append_terminal(f">> Running (timeout={timeout_val}s, mem_limit={mem_lim}%, cpu_limit={cpu_lim}%)...")
        threading.Thread(target=self._execute_thread, args=(code, timeout_val), daemon=True).start()

    def _execute_thread(self, code, timeout_val):
        res = self.controller.run_code(code, timeout=timeout_val)
        def finish():
            if res.get("stderr"):
                self._append_terminal("=== STDERR ===")
                self._append_terminal(res["stderr"])
            if res.get("stdout"):
                self._append_terminal("=== STDOUT ===")
                self._append_terminal(res["stdout"])
            if not res.get("stdout") and not res.get("stderr"):
                self._append_terminal("✔ Execution finished (no output).")
            self._refresh_vfs_list()
            self.logs_text.delete("1.0", "end")
            self.logs_text.insert("1.0", self.controller.get_logs())
        self.after(50, finish)

    def _on_stop(self):
        killed = force_kill()
        if killed:
            self.controller.log("Execution forcefully terminated by user.")
            self._append_terminal("⛔ Process terminated by user.")
        else:
            self._append_terminal("⚠ No active process to terminate.")

    def _on_save_code(self):
        code = self.code_text.get("1.0", "end")
        path = save_text_file_dialog(default_name="script.py", content=code)
        if path:
            messagebox.showinfo("Saved", f"Saved code to {path}")
            self.controller.log(f"Saved code to {path}")

    def _on_load_code(self):
        path, data = load_text_file_dialog()
        if path:
            self.code_text.delete("1.0", "end")
            self.code_text.insert("1.0", data)
            messagebox.showinfo("Loaded", f"Loaded {path}")
            self.controller.log(f"Loaded code from {path}")

    def _on_export_vfs(self):
        res = save_json_dialog(default_name="vfs.json", data=self.controller.vfs)
        if res:
            messagebox.showinfo("Export", f"VFS saved to {res}")
            self.controller.log(f"Exported VFS to {res}")

    def _on_import_vfs(self):
        path, data = load_json_dialog()
        if path and isinstance(data, dict):
            self.controller.vfs = data
            self._refresh_vfs_list()
            messagebox.showinfo("Import", f"Imported VFS from {path}")
            self.controller.log(f"Imported VFS from {path}")

    # ---------------- Stats Thread ----------------
    def _start_stats_thread(self):
        def loop():
            while True:
                pid = get_sandbox_pid()
                if pid:
                    try:
                        proc = psutil.Process(pid)
                        # cpu_percent with interval=0.1 returns usage over that interval
                        cpu = proc.cpu_percent(interval=0.1)
                        mem = proc.memory_percent()
                    except Exception:
                        cpu = mem = 0.0
                else:
                    # show host idle values (optional)
                    try:
                        cpu = psutil.cpu_percent(interval=0.1)
                        mem = psutil.virtual_memory().percent
                    except Exception:
                        cpu = mem = 0.0

                # clamp values
                try:
                    cpu_val = float(cpu)
                except Exception:
                    cpu_val = 0.0
                try:
                    mem_val = float(mem)
                except Exception:
                    mem_val = 0.0

                self.after(0, lambda v=cpu_val: self.cpu_lbl.configure(text=f"CPU: {v:.1f}%"))
                self.after(0, lambda v=cpu_val: self.cpu_bar.set(max(0.0, min(1.0, v / 100.0))))
                self.after(0, lambda v=mem_val: self.mem_lbl.configure(text=f"RAM: {v:.1f}%"))
                self.after(0, lambda v=mem_val: self.mem_bar.set(max(0.0, min(1.0, v / 100.0))))

                time.sleep(0.9)
        threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app = FuturisticApp()
    app.mainloop()
