"""Desktop control window (Tk). The engine runs in its own thread; status arrives via a queue."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import config
from .dialog import TITLE
from .engine import Engine, EngineError

logger = logging.getLogger(__name__)

POLL_MS = 200


class App:
    """Main window: start and stop the protected browser."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.inbox: queue.Queue[tuple[str, str]] = queue.Queue()
        self.engine = Engine(on_status=lambda s: self.inbox.put(("status", s)))
        self._busy = False
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(POLL_MS, self._poll)

    def _build(self) -> None:
        self.root.title(TITLE)
        self.root.resizable(False, False)
        frm = ttk.Frame(self.root, padding=16)
        frm.pack()

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
        buttons.pack(fill="x", pady=(12, 0))
        self.start_btn = ttk.Button(buttons, text="Start protected browser", command=self.start)
        self.stop_btn = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn.pack(side="left")

    def start(self) -> None:
        """Launch the protected browser without blocking the UI."""
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
            self.inbox.put(("started", ""))

    def stop(self) -> None:
        """Close the protected browser."""
        self.stop_btn.configure(state="disabled")
        threading.Thread(target=self.engine.stop, daemon=True).start()

    def close(self) -> None:
        """Stop the engine (closing Chrome) and exit."""
        self.engine.stop()
        self.root.destroy()

    def _poll(self) -> None:
        try:
            while True:
                kind, value = self.inbox.get_nowait()
                if kind == "status":
                    self.status_var.set({"running": "Running", "starting": "Starting…"}.get(value, "Stopped"))
                elif kind == "error":
                    messagebox.showerror(TITLE, value)
                elif kind == "started":
                    self._busy = False
                self._refresh_buttons()
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll)

    def _refresh_buttons(self) -> None:
        running = self.engine.is_running and self.status_var.get() == "Running"
        self.start_btn.configure(state="disabled" if (running or self._busy) else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")


def run() -> None:
    """Open the main window and block until it is closed."""
    root = tk.Tk()
    App(root)
    root.mainloop()
