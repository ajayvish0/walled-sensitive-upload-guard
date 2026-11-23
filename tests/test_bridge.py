import base64
from pathlib import Path

import pytest

from walled_guard import bridge, dialog

FIX = Path(__file__).parent / "fixtures"


def _file(name, site="chatgpt"):
    return {"site": site, "name": name, "type": "", "size": 0,
            "b64": base64.b64encode((FIX / name).read_bytes()).decode()}


@pytest.fixture(autouse=True)
def _reset():
    yield
    bridge.set_event_listener(None)


def test_clean_prompt_no_dialog(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("dialog must not be shown")
    monkeypatch.setattr(dialog, "confirm", boom)
    assert bridge.handle_prompt({"site": "chatgpt", "text": "hello"})["action"] == "allow"


def test_sensitive_prompt_cancel(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    r = bridge.handle_prompt({"site": "chatgpt", "text": "x WALLED_SENSITIVE"})
    assert r["action"] == "block" and r["flagged"]


def test_sensitive_prompt_continue(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    assert bridge.handle_prompt({"site": "perplexity", "text": "WALLED_SENSITIVE"})["action"] == "allow"


def test_sensitive_pdf_cancel(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    assert bridge.handle_file(_file("sensitive.pdf"))["action"] == "block"


def test_sensitive_pdf_continue(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    assert bridge.handle_file(_file("sensitive.pdf"))["action"] == "allow"


def test_clean_png_no_dialog(monkeypatch):
    monkeypatch.setattr(dialog, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    assert bridge.handle_file(_file("clean.png"))["action"] == "allow"


@pytest.mark.parametrize("payload", [{}, {"site": "x"}, {"site": "x", "text": 5},
                                     {"site": "x", "name": "a", "b64": "!!notb64!!"}])
def test_malformed_allows(payload):
    assert bridge.handle_prompt(payload)["action"] == "allow"
    assert bridge.handle_file(payload)["action"] == "allow"


def test_listener_gets_metadata_only(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    events = []
    bridge.set_event_listener(events.append)
    secret = "top secret plan WALLED_SENSITIVE"
    bridge.handle_prompt({"site": "chatgpt", "text": secret})
    bridge.handle_prompt({"site": "chatgpt", "text": "hi"})
    bridge.handle_file(_file("sensitive.txt"))
    assert [e["action"] for e in events] == ["block", "allow", "block"]
    assert all(set(e) == {"time", "site", "kind", "name", "flagged", "action"} for e in events)
    assert "top secret" not in repr(events)
