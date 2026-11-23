"""Desktop control window (Tk). The engine runs in its own thread; events arrive via a queue."""
from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any

from . import bridge, config
from .dialog import TITLE
from .engine import Engine, EngineError

logger = logging.getLogger(__name__)

MAX_EVENTS = 200
POLL_MS = 200


@dataclass
class Stats:
    """Decision counters."""

    prompts: int = 0
    files: int = 0
    flagged: int = 0
    allowed: int = 0
    blocked: int = 0

    def record(self, event: dict[str, Any]) -> None:
        """Update counters from a bridge event."""
        if event["kind"] == "prompt":
            self.prompts += 1
        else:
            self.files += 1
        if event["flagged"]:
            self.flagged += 1
        if event["action"] == "allow":
            self.allowed += 1
        else:
            self.blocked += 1


def format_event(event: dict[str, Any]) -> str:
    """One metadata-only line: 'HH:MM:SS  site  prompt|file  name  -> allowed|blocked'."""
    stamp = time.strftime("%H:%M:%S", time.localtime(event["time"]))
    verdict = "allowed" if event["action"] == "allow" else "blocked"
    return f"{stamp}  {event['site']}  {event['kind']}  {event['name']}  → {verdict}"


class App:
    """Main window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.stats = Stats()
        self.events: deque[str] = deque(maxlen=MAX_EVENTS)
        self.inbox: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.engine = Engine(on_status=lambda s: self.inbox.put(("status", s)))
        self._busy = False
        self._build()
        bridge.set_event_listener(lambda e: self.inbox.put(("event", e)))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(POLL_MS, self._poll)

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        self.root.title(TITLE)
        self.root.minsize(560, 480)
        frm = ttk.Frame(self.root, padding=14)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x")
        ttk.Label(top, text="Status:").pack(side="left")
        self.status_var = tk.StringVar(value="Stopped")
        ttk.Label(top, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=6)

        marker = ttk.Frame(frm)
        marker.pack(fill="x", pady=(8, 0))
        ttk.Label(marker, text="Sensitive marker:").pack(side="left")
        entry = ttk.Entry(marker, width=24)
        entry.insert(0, config.MARKER)
        entry.configure(state="readonly")
        entry.pack(side="left", padx=6)

        buttons = ttk.Frame(frm)
        buttons.pack(fill="x", pady=10)
        self.start_btn = ttk.Button(buttons, text="Start protected browser", command=self.start)
        self.stop_btn = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.site_btns = [
            ttk.Button(buttons, text=f"Open {cfg['name']}", command=lambda k=key: self.engine.open_site(k),
                       state="disabled")
            for key, cfg in config.SITES.items()
        ]
        for b in (self.start_btn, self.stop_btn, *self.site_btns):
            b.pack(side="left", padx=(0, 6))

        counters = ttk.LabelFrame(frm, text="Counters", padding=8)
        counters.pack(fill="x")
        self.counter_vars: dict[str, tk.StringVar] = {}
        for label in ("Prompts checked", "Files checked", "Flagged", "Allowed", "Blocked"):
            cell = ttk.Frame(counters)
            cell.pack(side="left", expand=True)
            var = tk.StringVar(value="0")
            self.counter_vars[label] = var
            ttk.Label(cell, textvariable=var, font=("Segoe UI", 14, "bold")).pack()
            ttk.Label(cell, text=label).pack()

        ttk.Label(frm, text="Recent events (metadata only)").pack(anchor="w", pady=(10, 2))
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(box, activestyle="none", font=("Consolas", 9))
        scroll = ttk.Scrollbar(box, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------------ actions
    def start(self) -> None:
        if self._busy or self.engine.is_running:
            return
        self._busy = True
        self.start_btn.configure(state="disabled")
        self.status_var.set("Starting…")
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self) -> None:
        try:
            self.engine.start()
        except EngineError as exc:
            self.inbox.put(("error", str(exc)))
        finally:
            self.inbox.put(("started", None))

    def stop(self) -> None:
        self.stop_btn.configure(state="disabled")
        threading.Thread(target=self.engine.stop, daemon=True).start()

    def close(self) -> None:
        """Stop the engine (closing Chrome) and exit."""
        bridge.set_event_listener(None)
        self.engine.stop()
        self.root.destroy()

    # ------------------------------------------------------------------ queue pump
    def _poll(self) -> None:
        try:
            while True:
                kind, value = self.inbox.get_nowait()
                if kind == "event":
                    self._on_event(value)
                elif kind == "status":
                    self._on_status(value)
                elif kind == "error":
                    messagebox.showerror(TITLE, value)
                elif kind == "started":
                    self._busy = False
                    self._refresh_buttons()
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll)

    def _on_event(self, event: dict[str, Any]) -> None:
        self.stats.record(event)
        self.events.append(format_event(event))
        self.listbox.insert(0, self.events[-1])
        if self.listbox.size() > MAX_EVENTS:
            self.listbox.delete(MAX_EVENTS, "end")
        values = (self.stats.prompts, self.stats.files, self.stats.flagged, self.stats.allowed, self.stats.blocked)
        for var, value in zip(self.counter_vars.values(), values):
            var.set(str(value))

    def _on_status(self, status: str) -> None:
        self.status_var.set({"running": "Running", "starting": "Starting…"}.get(status, "Stopped"))
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        running = self.engine.is_running and self.status_var.get() == "Running"
        self.start_btn.configure(state="disabled" if (running or self._busy) else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        for b in self.site_btns:
            b.configure(state="normal" if running else "disabled")


def run() -> None:
    """Open the main window and block until it is closed."""
    root = tk.Tk()
    App(root)
    root.mainloop()
