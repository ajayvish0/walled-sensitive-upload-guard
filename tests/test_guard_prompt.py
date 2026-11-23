import time

import pytest

from walled_guard import bridge

SENSITIVE = "summarise WALLED_SENSITIVE roadmap"


@pytest.fixture
def calls(monkeypatch):
    """Record every prompt inspection that reaches Python."""
    seen: list[str] = []
    real = bridge.handle_prompt

    def spy(payload):
        seen.append(payload["text"])
        return real(payload)

    monkeypatch.setattr(bridge, "handle_prompt", spy)
    return seen


def _type(page, text):
    page.click("#composer")
    page.keyboard.type(text)


def _settled(page):
    page.wait_for_function("window.__wgDebug && !window.__wgDebug().pending")


def _sent(page):
    return page.evaluate("window.__sent")


def _composer(page):
    return page.evaluate("document.getElementById('composer').innerText")


def test_clean_enter_sent_once(page, calls, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")  # must not matter: no marker
    _type(page, "hello there")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")
    assert _sent(page) == ["hello there"]
    assert len(calls) == 1


def test_marker_enter_cancel_then_retry_continue(page, calls, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    _type(page, SENSITIVE)
    page.keyboard.press("Enter")
    _settled(page)
    assert len(calls) == 1 and _sent(page) == []
    assert _composer(page) == SENSITIVE

    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")
    _settled(page)
    assert _sent(page) == [SENSITIVE]


@pytest.mark.parametrize("choice,expected_sent", [("cancel", 0), ("continue", 1)])
def test_marker_click_send(page, calls, monkeypatch, choice, expected_sent):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", choice)
    _type(page, SENSITIVE)
    page.click("#send")
    if expected_sent:
        page.wait_for_function("window.__sent.length === 1")
    _settled(page)
    if not expected_sent:
        assert _composer(page) == SENSITIVE
    assert len(calls) == 1 and len(_sent(page)) == expected_sent


def test_shift_enter_not_inspected(page, calls):
    _type(page, "line one")
    page.keyboard.press("Shift+Enter")
    page.keyboard.type("line two")
    assert _sent(page) == [] and calls == []
    assert "line one" in _composer(page) and "line two" in _composer(page)


def test_empty_composer_does_nothing(page, calls):
    page.click("#composer")
    page.keyboard.press("Enter")
    page.click("#send")
    _settled(page)
    assert calls == [] and _sent(page) == []


def test_two_rapid_enters_one_inspection(page, monkeypatch):
    seen = []
    real = bridge.handle_prompt

    def slow(payload):
        seen.append(1)
        time.sleep(0.4)
        return real(payload)

    monkeypatch.setattr(bridge, "handle_prompt", slow)
    _type(page, "rapid")
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length >= 1")
    _settled(page)
    assert len(seen) == 1 and _sent(page) == ["rapid"]


def test_sent_text_is_byte_identical(page, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    text = "Ünïcode ✓ WALLED_SENSITIVE  two  spaces"
    _type(page, text)
    typed = _composer(page)
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")
    assert _sent(page)[0] == typed


def test_missing_binding_fails_open(page):
    page.evaluate("window.__wg_inspect_prompt = undefined")
    _type(page, "WALLED_SENSITIVE hi")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")
    _settled(page)


def test_debug_helper(page):
    info = page.evaluate("window.__wgDebug()")
    assert info["siteKey"] == "harness" and info["composerFound"] and info["styleTagPresent"]
