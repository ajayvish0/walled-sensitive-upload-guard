"""Handlers called from the page (via Playwright bindings)."""
from __future__ import annotations

import base64
import logging
import time
from typing import Any, Callable

from . import dialog, inspector

logger = logging.getLogger(__name__)

_listener: Callable[[dict], None] | None = None
_ALLOW_ERR = {"action": "allow", "flagged": False, "reason": "error"}


def set_event_listener(fn: Callable[[dict], None] | None) -> None:
    """Register a callback receiving metadata-only decision events."""
    global _listener
    _listener = fn


def _emit(site: str, kind: str, name: str, flagged: bool, action: str) -> None:
    if _listener is None:
        return
    try:
        _listener({"time": time.time(), "site": site, "kind": kind, "name": name,
                   "flagged": flagged, "action": action})
    except Exception:
        logger.exception("event listener failed")


def _decide(site: str, verdict: inspector.Verdict, name: str, detail: str, ident: str) -> dict[str, Any]:
    if not verdict.flagged:
        _emit(site, verdict.kind, name, False, "allow")
        return {"action": "allow", "flagged": False, "reason": verdict.reason}
    proceed = dialog.confirm(verdict.kind, ident, detail)
    action = "allow" if proceed else "block"
    logger.info("flagged %s on %s (%s): %s", verdict.kind, site, name, action)
    _emit(site, verdict.kind, name, True, action)
    return {"action": action, "flagged": True, "reason": verdict.reason}


def handle_prompt(payload: dict) -> dict[str, Any]:
    """Inspect a prompt; ask the user if it is flagged."""
    try:
        site, text = str(payload["site"]), payload["text"]
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return _decide(site, inspector.inspect_prompt(text), "prompt", "", text)
    except Exception as exc:
        logger.error("prompt handling failed (%s); allowing", type(exc).__name__)
        return dict(_ALLOW_ERR)


def handle_file(payload: dict) -> dict[str, Any]:
    """Inspect an uploaded file; ask the user if it is flagged."""
    try:
        site, name = str(payload["site"]), str(payload["name"])
        data = base64.b64decode(payload["b64"], validate=True)
        verdict = inspector.inspect_file(name, data)
        size_kb = max(1, round(len(data) / 1024))
        detail = f"{verdict.file_type.upper()}, {size_kb} KB"
        return _decide(site, verdict, name, detail, name)
    except Exception as exc:
        logger.error("file handling failed (%s); allowing", type(exc).__name__)
        return dict(_ALLOW_ERR)
