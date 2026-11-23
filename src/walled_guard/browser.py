"""Playwright context wiring: injects the guard script and exposes bindings."""
from __future__ import annotations

from playwright.sync_api import BrowserContext

from . import bridge
from .script_builder import build_init_script


def install_guard(context: BrowserContext) -> None:
    """Install the page script and Python bindings into every page of the context."""
    script = build_init_script()
    context.add_init_script(script)
    context.expose_binding("__wg_inspect_prompt", lambda source, payload: bridge.handle_prompt(payload))
    context.expose_binding("__wg_inspect_file", lambda source, payload: bridge.handle_file(payload))
    for page in context.pages:
        try:
            page.evaluate(script)
        except Exception:  # page may be closed or not scriptable
            continue
