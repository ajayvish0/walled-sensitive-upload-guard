"""Native desktop confirmation dialog (Tk, run in a separate process)."""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from typing import Literal

from . import config

logger = logging.getLogger(__name__)

TITLE = "Walled AI – Sensitive Upload Guard"
_PREVIEW_CHARS = 150


def confirm(kind: Literal["prompt", "file"], name: str, detail: str = "") -> bool:
    """Ask the user to continue (True) or cancel (False); fail-closed on any problem."""
    auto = os.environ.get(config.DIALOG_AUTO_ENV)
    if auto == "continue":
        return True
    if auto == "cancel":
        return False
    cmd = [sys.executable, "-m", "walled_guard.dialog", "--kind", kind, "--name", name, "--detail", detail]
    try:
        return subprocess.run(cmd, check=False).returncode == 0
    except Exception as exc:
        logger.error("confirmation dialog failed (%s); blocking", type(exc).__name__)
        return False


def prompt_preview(text: str) -> str:
    """One-line preview (max 150 chars) plus the total length."""
    flat = " ".join(text.split())
    shown = flat if len(flat) <= _PREVIEW_CHARS else flat[:_PREVIEW_CHARS] + "…"
    return f"{shown}  ({len(text)} characters)"


def _show(kind: str, name: str, detail: str) -> int:
    import tkinter as tk
    from tkinter import ttk

    result = {"code": 1}
    root = tk.Tk()
    root.title(TITLE)
    root.resizable(False, False)
    root.attributes("-topmost", True)

    where = "a TEXT PROMPT" if kind == "prompt" else "a FILE"
    frame = ttk.Frame(root, padding=20)
    frame.pack()
    ttk.Label(frame, text=f"Sensitive marker {config.MARKER} detected in {where}",
              font=("Segoe UI", 11, "bold"), foreground="#B00020").pack(anchor="w")
    label = "Prompt:" if kind == "prompt" else "File:"
    ident = prompt_preview(name) if kind == "prompt" else name
    ttk.Label(frame, text=label, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 0))
    ttk.Label(frame, text=ident, wraplength=460, justify="left").pack(anchor="w")
    if kind == "file" and detail:
        ttk.Label(frame, text=detail, foreground="#555").pack(anchor="w")
    ttk.Label(frame, text="Do you want to continue?").pack(anchor="w", pady=(14, 8))

    def finish(code: int) -> None:
        result["code"] = code
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(anchor="e")
    ttk.Button(buttons, text="Continue", command=lambda: finish(0)).pack(side="left", padx=6)
    cancel = ttk.Button(buttons, text="Cancel", command=lambda: finish(1))
    cancel.pack(side="left")

    root.protocol("WM_DELETE_WINDOW", lambda: finish(1))
    root.bind("<Escape>", lambda _e: finish(1))
    # Enter must not trigger Continue: swallow it, even on the focused Cancel button.
    root.bind_class("TButton", "<Return>", lambda _e: "break")
    root.bind_class("TButton", "<KP_Enter>", lambda _e: "break")

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")

    def raise_window() -> None:
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
        cancel.focus_set()

    raise_window()
    root.after(100, raise_window)
    root.mainloop()
    return result["code"]


def main(argv: list[str] | None = None) -> int:
    """Show the dialog; exit code 0 = Continue, 1 = Cancel."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["prompt", "file"], required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--detail", default="")
    args = parser.parse_args(argv)
    return _show(args.kind, args.name, args.detail)


if __name__ == "__main__":
    raise SystemExit(main())
