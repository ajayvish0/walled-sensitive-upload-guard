"""Engine: launches the real Chrome (or Edge) with Playwright and wires the guard in.

All Playwright calls happen inside one worker thread, as the sync API requires.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable

from playwright.sync_api import BrowserContext, Page, sync_playwright

from . import config
from .browser import install_guard

logger = logging.getLogger(__name__)

CHANNELS: tuple[str | None, ...] = ("chrome", "msedge", None)
_LAUNCH_ARGS = ["--start-maximized", "--disable-blink-features=AutomationControlled"]


class EngineError(Exception):
    """Raised when the protected browser cannot be started."""


def launch_context(playwright: Any) -> BrowserContext:
    """Launch a persistent context, trying Chrome, then Edge, then bundled Chromium."""
    config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for channel in CHANNELS:
        kwargs: dict[str, Any] = {
            "headless": False,
            "no_viewport": True,
            "args": _LAUNCH_ARGS,
            "ignore_default_args": ["--enable-automation"],
        }
        if channel:
            kwargs["channel"] = channel
        try:
            return playwright.chromium.launch_persistent_context(str(config.PROFILE_DIR), **kwargs)
        except Exception as exc:
            logger.warning("could not launch %s: %s", channel or "chromium", type(exc).__name__)
    raise EngineError("Install Google Chrome or Microsoft Edge")


class Engine:
    """Runs the protected browser in a background thread."""

    def __init__(self, on_status: Callable[[str], None] | None = None) -> None:
        self._on_status = on_status or (lambda _s: None)
        self._commands: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._error: Exception | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, timeout: float = 60.0) -> None:
        """Start the worker thread; raises EngineError if the browser cannot launch."""
        if self.is_running:
            return
        self._stop.clear()
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, name="walled-guard-engine", daemon=True)
        self._thread.start()
        self._ready.wait(timeout)
        if self._error is not None:
            raise self._error

    def stop(self) -> None:
        """Ask the worker to close the browser and wait for it."""
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=15)

    def open_site(self, key: str) -> None:
        """Queue opening (or focusing) a supported site."""
        if key not in config.SITES:
            raise KeyError(key)
        self._commands.put(("open", key))

    # ------------------------------------------------------------------ worker thread
    def _run(self) -> None:
        self._on_status("starting")
        try:
            with sync_playwright() as p:
                context = launch_context(p)
                try:
                    self._serve(context)
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
        except Exception as exc:  # noqa: BLE001 - reported to the caller
            logger.error("engine failed: %s", type(exc).__name__)
            self._error = exc if isinstance(exc, EngineError) else EngineError(str(exc))
        finally:
            self._ready.set()
            self._on_status("stopped")

    def _serve(self, context: BrowserContext) -> None:
        install_guard(context)
        context.on("page", self._attach_console)
        for page in context.pages:
            self._attach_console(page)
        closed = threading.Event()
        context.on("close", lambda *_: closed.set())

        first = context.pages[0] if context.pages else context.new_page()
        pages: dict[str, Page] = {}
        for index, key in enumerate(config.SITES):
            page = first if index == 0 else context.new_page()
            self._goto(page, key)
            pages[key] = page
        self._on_status("running")
        self._ready.set()

        while not self._stop.is_set() and not closed.is_set():
            self._drain_commands(context, pages)
            try:
                (pages.get("chatgpt") or first).wait_for_timeout(200)  # serves bindings
            except Exception:
                if closed.is_set() or not context.pages:
                    break
                first = context.pages[0]
                pages = {k: p for k, p in pages.items() if not p.is_closed()}
                if not pages:
                    pages["chatgpt"] = first

    def _drain_commands(self, context: BrowserContext, pages: dict[str, Page]) -> None:
        while True:
            try:
                cmd, key = self._commands.get_nowait()
            except queue.Empty:
                return
            if cmd != "open" or key is None:
                continue
            page = pages.get(key)
            if page is None or page.is_closed():
                page = context.new_page()
                self._goto(page, key)
                pages[key] = page
            page.bring_to_front()

    @staticmethod
    def _goto(page: Page, key: str) -> None:
        try:
            page.goto(config.SITES[key]["url"], wait_until="domcontentloaded")
        except Exception as exc:
            logger.warning("navigation to %s failed: %s", key, type(exc).__name__)

    @staticmethod
    def _attach_console(page: Page) -> None:
        page.on("console", lambda msg: logger.debug("page: %s", msg.text) if msg.text.startswith("[WG]") else None)


def main() -> int:
    """Developer runner: python -m walled_guard.engine."""
    from .logging_setup import setup_logging

    setup_logging()
    engine = Engine()
    try:
        engine.start()
    except EngineError as exc:
        print(f"Error: {exc}")
        return 1
    print("Protected browser running. Close the Chrome window or press Ctrl+C to quit.")
    try:
        while engine.is_running:
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
