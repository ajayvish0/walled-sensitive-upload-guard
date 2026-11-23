"""Reliability cases from the assignment's general expectations (fail-closed / fail-open, scope)."""
import logging
import subprocess
from pathlib import Path

import pytest

from walled_guard import bridge, config
from walled_guard.inspector import inspect_file
from walled_guard.script_builder import build_init_script

FIX = Path(__file__).parent / "fixtures"


def _settled(page):
    page.wait_for_function("!window.__wgDebug().pending")


def _type(page, text):
    page.click("#composer")
    page.keyboard.type(text)


def test_dialog_process_crash_blocks_and_page_recovers(page, monkeypatch):
    monkeypatch.delenv("WALLED_DIALOG_AUTO", raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, -9))
    _type(page, "WALLED_SENSITIVE plan")
    page.keyboard.press("Enter")
    _settled(page)
    assert page.evaluate("window.__sent") == []
    assert page.evaluate("document.getElementById('composer').innerText") == "WALLED_SENSITIVE plan"

    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")  # the user can retry normally
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")


def test_dialog_launch_failure_blocks_file(page, monkeypatch):
    monkeypatch.delenv("WALLED_DIALOG_AUTO", raising=False)

    def boom(*a, **k):
        raise OSError("cannot start")

    monkeypatch.setattr(subprocess, "run", boom)
    page.set_input_files("#file", str(FIX / "sensitive.txt"))
    page.wait_for_function("document.getElementById('file').files.length === 0")
    _settled(page)
    assert page.evaluate("window.__uploads") == []


def test_binding_raising_allows_prompt(page, monkeypatch):
    def boom(payload):
        raise RuntimeError("binding exploded")

    monkeypatch.setattr(bridge, "handle_prompt", boom)
    _type(page, "WALLED_SENSITIVE hi")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__sent.length === 1")
    _settled(page)


def test_binding_raising_allows_file(page, monkeypatch):
    def boom(payload):
        raise RuntimeError("binding exploded")

    monkeypatch.setattr(bridge, "handle_file", boom)
    page.set_input_files("#file", str(FIX / "sensitive.txt"))
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)


def test_oversized_file_not_inspected_and_logged(caplog):
    data = b"WALLED_SENSITIVE" + b"\0" * config.MAX_FILE_BYTES
    with caplog.at_level(logging.WARNING):
        verdict = inspect_file("huge.bin", data)
    assert verdict.flagged is False and "too large" in (verdict.error or "")
    assert any("too large" in r.message for r in caplog.records)


def test_oversized_file_skipped_by_page(page, monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "handle_file", lambda p: calls.append(p) or {"action": "allow"})
    page.evaluate("window.__WG_CONFIG.maxFileBytes = 10")
    page.set_input_files("#file", str(FIX / "sensitive.txt"))
    page.wait_for_function("window.__uploads.length === 1")
    assert calls == []


def test_logs_never_contain_content(page, caplog, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    secret = "zebra-confidential-sentence WALLED_SENSITIVE"
    with caplog.at_level(logging.DEBUG):
        _type(page, secret)
        page.keyboard.press("Enter")
        page.wait_for_function("window.__sent.length === 1")
        page.set_input_files("#file", str(FIX / "sensitive.pdf"))
        page.wait_for_function("window.__uploads.length === 1")
        _settled(page)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "zebra" not in text and "Quarterly" not in text and "Roadmap" not in text


def test_harness_host_disabled_without_flag(monkeypatch):
    monkeypatch.delenv("WALLED_ENABLE_HARNESS", raising=False)
    assert '"enableHarness": false' in build_init_script()


def test_other_hosts_untouched(context):
    p = context.new_page()
    p.goto("http://other.local/")
    assert p.evaluate("window.__wgInstalled") is None
    assert p.evaluate("typeof window.__wgDebug") == "undefined"
    p.click("#composer")
    p.keyboard.type("WALLED_SENSITIVE not guarded here")
    p.keyboard.press("Enter")
    p.wait_for_function("window.__sent.length === 1")
    p.set_input_files("#file", str(FIX / "sensitive.txt"))
    p.wait_for_function("window.__uploads.length === 1")
