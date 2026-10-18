#!/usr/bin/env python3
"""Wi-Fi Control for Linux Mint / NetworkManager. Standard-library Tkinter GUI."""
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path

APP_NAME = "Wi-Fi Control"
REFRESH_MS = 8000
BG = "#111827"
PANEL = "#1f2937"
PANEL_2 = "#273449"
TEXT = "#f3f4f6"
MUTED = "#a7b3c5"
ACCENT = "#38bdf8"
GREEN = "#34d399"
RED = "#fb7185"
AMBER = "#fbbf24"


def split_nmcli(line):
    """Split nmcli terse output while respecting backslash-escaped separators."""
    fields, current, escaped = [], [], False
    for ch in line:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(ch)
    fields.append("".join(current))
    return fields


class WifiControl:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x690")
        self.root.minsize(760, 590)
        self.root.configure(bg=BG)
        # Use the supplied AIRCTL-style icon when installed alongside this app.
        try:
            icon_path = Path(__file__).resolve().parent / "wifi-control.png"
            if icon_path.exists():
                self._window_icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self._window_icon)
        except (tk.TclError, OSError):
            self._window_icon = None
        self.busy = False
        self.device = None
        self.network_rows = {}
        self._styles()
        self._build()
        self.refresh_status()
        self.root.after(REFRESH_MS, self._periodic_refresh)

    def _styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Sans", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Sans", 9))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Sans", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Sans", 22, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Sans", 10))
        style.configure("CardTitle.TLabel", background=PANEL, foreground=MUTED, font=("Sans", 9))
        style.configure("CardValue.TLabel", background=PANEL, foreground=TEXT, font=("Sans", 14, "bold"))
        style.configure("TButton", font=("Sans", 10), padding=(12, 8), background=PANEL_2, foreground=TEXT)
        style.map("TButton", background=[("active", "#34445d"), ("disabled", "#263143")])
        style.configure("Accent.TButton", background="#0369a1", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#0284c7")])
        style.configure("Danger.TButton", background="#7f1d1d", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#991b1b")])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=30, borderwidth=0, font=("Sans", 10))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT,
                        font=("Sans", 9, "bold"), padding=7)
        style.map("Treeview", background=[("selected", "#075985")], foreground=[("selected", "#ffffff")])
        style.configure("TSeparator", background="#374151")

    def _build(self):
        shell = ttk.Frame(self.root, padding=(20, 18))
        shell.pack(fill="both", expand=True)

        top = ttk.Frame(shell)
        top.pack(fill="x", pady=(0, 15))
        heading = ttk.Frame(top)
        heading.pack(side="left", fill="x", expand=True)
        ttk.Label(heading, text="Wi-Fi Control", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="Manage your wireless connection with NetworkManager",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(3, 0))
        self.status_badge = tk.Label(top, text="● CHECKING", bg="#374151", fg=TEXT,
                                     font=("Sans", 9, "bold"), padx=12, pady=8)
        self.status_badge.pack(side="right", anchor="center")

        cards = ttk.Frame(shell)
        cards.pack(fill="x", pady=(0, 14))
        self.adapter_value = tk.StringVar(value="Detecting…")
        self.radio_value = tk.StringVar(value="Checking…")
        self.state_value = tk.StringVar(value="Checking…")
        self._card(cards, "WIRELESS ADAPTER", self.adapter_value, 0)
        self._card(cards, "WI-FI RADIO", self.radio_value, 1)
        self._card(cards, "DEVICE STATE", self.state_value, 2)

        controls = ttk.Frame(shell)
        controls.pack(fill="x", pady=(0, 14))
        self.on_btn = ttk.Button(controls, text="⏻  Turn Wi-Fi ON", style="Accent.TButton",
                                 command=lambda: self.action("wifi_on"))
        self.on_btn.pack(side="left", padx=(0, 8))
        self.off_btn = ttk.Button(controls, text="Turn Wi-Fi OFF", style="Danger.TButton",
                                  command=lambda: self.action("wifi_off"))
        self.off_btn.pack(side="left", padx=(0, 8))
        self.scan_btn = ttk.Button(controls, text="↻  Scan networks", command=lambda: self.action("scan"))
        self.scan_btn.pack(side="left", padx=(0, 8))
        self.refresh_btn = ttk.Button(controls, text="Refresh", command=self.refresh_status)
        self.refresh_btn.pack(side="left")

        net_panel = ttk.Frame(shell, style="Panel.TFrame", padding=12)
        net_panel.pack(fill="both", expand=True)
        net_head = ttk.Frame(net_panel, style="Panel.TFrame")
        net_head.pack(fill="x", pady=(0, 8))
        ttk.Label(net_head, text="Available networks", style="Panel.TLabel",
                  font=("Sans", 12, "bold")).pack(side="left")
        ttk.Label(net_head, text="Select a network, then Connect", style="Panel.TLabel",
                  foreground=MUTED).pack(side="right")
        tree_wrap = ttk.Frame(net_panel, style="Panel.TFrame")
        tree_wrap.pack(fill="both", expand=True)
        cols = ("ssid", "signal", "security", "active")
        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", selectmode="browse", height=8)
        self.tree.heading("ssid", text="NETWORK")
        self.tree.heading("signal", text="SIGNAL")
        self.tree.heading("security", text="SECURITY")
        self.tree.heading("active", text="STATUS")
        self.tree.column("ssid", width=360, anchor="w")
        self.tree.column("signal", width=95, anchor="center")
        self.tree.column("security", width=150, anchor="center")
        self.tree.column("active", width=120, anchor="center")
        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        net_actions = ttk.Frame(net_panel, style="Panel.TFrame")
        net_actions.pack(fill="x", pady=(10, 0))
        self.connect_btn = ttk.Button(net_actions, text="Connect to selected", style="Accent.TButton",
                                      command=self.connect_selected)
        self.connect_btn.pack(side="left", padx=(0, 8))
        self.disconnect_btn = ttk.Button(net_actions, text="Disconnect", command=lambda: self.action("disconnect"))
        self.disconnect_btn.pack(side="left", padx=(0, 8))
        self.manage_btn = ttk.Button(net_actions, text="Fix “unmanaged” adapter…",
                                     command=lambda: self.action("manage"))
        self.manage_btn.pack(side="left")

        bottom = ttk.Frame(shell)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Label(bottom, text="Auto-refresh every 8 seconds • Admin action asks for permission",
                  style="Muted.TLabel").pack(side="left")
        self.status_text = tk.StringVar(value="Ready")
        ttk.Label(bottom, textvariable=self.status_text, style="Muted.TLabel").pack(side="right")

    def _card(self, parent, title, variable, col):
        parent.grid_columnconfigure(col, weight=1, uniform="cards")
        card = ttk.Frame(parent, style="Panel.TFrame", padding=(14, 12))
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 7, 7 if col < 2 else 0))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(5, 0))

    @staticmethod
    def run(args, timeout=18):
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            return p.returncode, p.stdout.strip(), p.stderr.strip()
        except FileNotFoundError:
            return 127, "", f"Command not found: {args[0]}"
        except subprocess.TimeoutExpired:
            return 124, "", f"Timed out: {' '.join(args)}"

    def get_device(self):
        code, out, err = self.run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"])
        if code:
            return None, err or out or "Could not query NetworkManager"
        for line in out.splitlines():
            parts = split_nmcli(line)
            if len(parts) >= 2 and parts[1] == "wifi":
                return parts[0], None
        return None, "No Wi-Fi adapter detected by NetworkManager"

    def refresh_status(self):
        if self.busy:
            return
        code, radio, err = self.run(["nmcli", "radio", "wifi"])
        enabled = code == 0 and radio.lower() == "enabled"
        self.radio_value.set("ON" if enabled else ("OFF" if code == 0 else "Unavailable"))
        self.device, problem = self.get_device()
        if self.device:
            self.adapter_value.set(self.device)
            c, out, e = self.run(["nmcli", "-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION,GENERAL.MANAGED", "device", "show", self.device])
            values = {}
            if c == 0:
                for line in out.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        values[key.rsplit(".", 1)[-1]] = value
            managed = values.get("MANAGED", "unknown")
            state = values.get("STATE", "unknown")
            conn = values.get("CONNECTION", "--")
            self.state_value.set("Managed" if managed.lower() == "yes" else ("Unmanaged" if managed.lower() == "no" else state))
            if state.lower().startswith("100") or "connected" in state.lower():
                badge, color = "● CONNECTED", "#065f46"
            elif managed.lower() == "no":
                badge, color = "● UNMANAGED", "#92400e"
            elif not enabled:
                badge, color = "● WI-FI OFF", "#374151"
            else:
                badge, color = "● READY", "#1e40af"
            self.status_badge.configure(text=badge, bg=color)
            self.status_text.set(f"{self.device} • {conn}")
        else:
            self.adapter_value.set("Not found")
            self.state_value.set(problem or "Unknown")
            self.status_badge.configure(text="● NO ADAPTER", bg="#7f1d1d")
            self.status_text.set("Check Wi-Fi adapter / NetworkManager")
        self.radio_value.set("ON" if enabled else ("OFF" if code == 0 else "Unavailable"))

    def _periodic_refresh(self):
        if self.root.winfo_exists():
            if not self.busy:
                self.refresh_status()
            self.root.after(REFRESH_MS, self._periodic_refresh)

    def action(self, name):
        if self.busy:
            return
        self.busy = True
        self.status_text.set("Working…")
        for b in (self.on_btn, self.off_btn, self.scan_btn, self.refresh_btn,
                  self.connect_btn, self.disconnect_btn, self.manage_btn):
            b.configure(state="disabled")
        threading.Thread(target=self._worker, args=(name,), daemon=True).start()

    def _worker(self, name):
        label = name.replace("_", " ").title()
        if name in ("wifi_on", "wifi_off"):
            value = "on" if name == "wifi_on" else "off"
            result = self.run(["nmcli", "radio", "wifi", value])
        elif name == "scan":
            dev, problem = self.get_device()
            result = self._scan(dev) if dev else (1, "", problem)
        elif name == "manage":
            dev, problem = self.get_device()
            pkexec = shutil.which("pkexec")
            nmcli = shutil.which("nmcli") or "/usr/bin/nmcli"
            if not dev:
                result = (1, "", problem)
            elif not pkexec:
                result = (1, "", "pkexec is unavailable. Run: sudo nmcli device set " + dev + " managed yes")
            else:
                result = self.run([pkexec, nmcli, "device", "set", dev, "managed", "yes"], timeout=60)
        elif name == "disconnect":
            dev, problem = self.get_device()
            result = self.run(["nmcli", "device", "disconnect", dev]) if dev else (1, "", problem)
        else:
            result = (1, "", "Unknown action")
        code, out, err = result
        self.root.after(0, lambda: self._finish(name, code, out, err))

    def _scan(self, dev):
        code, out, err = self.run(["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                                   "device", "wifi", "list", "ifname", dev], timeout=30)
        networks = []
        if code == 0:
            seen = set()
            for line in out.splitlines():
                p = split_nmcli(line)
                if len(p) < 4:
                    continue
                active, ssid, signal, security = p[:4]
                ssid = ssid or "(Hidden network)"
                key = (ssid, security)
                if key in seen:
                    continue
                seen.add(key)
                networks.append((ssid, signal, security or "Open", "Connected" if active == "*" else ""))
        return code, networks if code == 0 else out, err

    def _finish(self, name, code, out, err):
        self.busy = False
        for b in (self.on_btn, self.off_btn, self.scan_btn, self.refresh_btn,
                  self.connect_btn, self.disconnect_btn, self.manage_btn):
            b.configure(state="normal")
        if name == "scan" and code == 0 and isinstance(out, list):
            self.tree.delete(*self.tree.get_children())
            self.network_rows.clear()
            for i, row in enumerate(out):
                item = f"net{i}"
                self.tree.insert("", "end", iid=item, values=row)
                self.network_rows[item] = row
            self.status_text.set(f"Found {len(out)} network(s)")
        else:
            if code == 0:
                self.status_text.set("Done")
            else:
                self.status_text.set("Action failed — see message")
                messagebox.showerror("Wi-Fi Control", err or str(out) or "The operation failed.")
        self.refresh_status()

    def connect_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select a network", "Choose a network from the list first.")
            return
        row = self.network_rows.get(selected[0])
        if not row:
            return
        ssid, signal, security, active = row
        if ssid == "(Hidden network)":
            entered = simpledialog.askstring("Hidden network", "Enter the hidden Wi-Fi network name:")
            if not entered:
                return
            ssid = entered
        password = None
        if security and security.lower() not in ("open", "--", "none"):
            password = simpledialog.askstring("Wi-Fi password", f"Password for “{ssid}”:", show="•")
            if password is None:
                return
        self.busy = True
        for b in (self.on_btn, self.off_btn, self.scan_btn, self.refresh_btn,
                  self.connect_btn, self.disconnect_btn, self.manage_btn):
            b.configure(state="disabled")
        self.status_text.set(f"Connecting to {ssid}…")
        threading.Thread(target=self._connect_worker, args=(ssid, password), daemon=True).start()

    def _connect_worker(self, ssid, password):
        dev, problem = self.get_device()
        if not dev:
            result = (1, "", problem)
        else:
            cmd = ["nmcli", "device", "wifi", "connect", ssid, "ifname", dev]
            if password:
                cmd += ["password", password]
            result = self.run(cmd, timeout=45)
        code, out, err = result
        self.root.after(0, lambda: self._finish_connect(code, out, err, ssid))

    def _finish_connect(self, code, out, err, ssid):
        self.busy = False
        for b in (self.on_btn, self.off_btn, self.scan_btn, self.refresh_btn,
                  self.connect_btn, self.disconnect_btn, self.manage_btn):
            b.configure(state="normal")
        if code == 0:
            self.status_text.set(f"Connected to {ssid}")
            messagebox.showinfo("Connected", out or f"Connected to {ssid}.")
        else:
            self.status_text.set("Connection failed")
            messagebox.showerror("Connection failed", err or out or "Could not connect.")
        self.refresh_status()


def main():
    if not shutil.which("nmcli"):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("NetworkManager not found", "Install NetworkManager (nmcli) first.")
        root.destroy()
        return
    root = tk.Tk()
    WifiControl(root)
    root.mainloop()


if __name__ == "__main__":
    main()
