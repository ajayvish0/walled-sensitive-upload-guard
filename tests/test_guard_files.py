import base64
import hashlib
from pathlib import Path

import pytest

from walled_guard import bridge, dialog

FIX = Path(__file__).parent / "fixtures"
SENSITIVE_FILES = ["sensitive.txt", "sensitive.pdf", "sensitive_scanned.pdf", "sensitive.png", "sensitive.jpg"]
MIME = {".txt": "text/plain", ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}


@pytest.fixture
def dialogs(monkeypatch):
    """Record every file name a dialog was shown for."""
    shown: list[str] = []
    real = dialog.confirm

    def spy(kind, name, detail=""):
        shown.append(name)
        return real(kind, name, detail)

    monkeypatch.setattr(dialog, "confirm", spy)
    return shown


def _settled(page):
    page.wait_for_function("!window.__wgDebug().pending")


def _uploads(page):
    return page.evaluate("window.__uploads")


def _expected(name):
    data = (FIX / name).read_bytes()
    return {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _synthetic(page, kind, name):
    """Dispatch a drop or paste event carrying a fixture file on #composer."""
    data = (FIX / name).read_bytes()
    page.evaluate(
        """({kind, name, b64, mime}) => {
            const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
            const dt = new DataTransfer();
            dt.items.add(new File([bytes], name, {type: mime}));
            const el = document.getElementById('composer');
            const ev = kind === 'drop'
              ? new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt})
              : new ClipboardEvent('paste', {bubbles: true, cancelable: true, clipboardData: dt});
            el.dispatchEvent(ev);
        }""",
        {"kind": kind, "name": name, "b64": base64.b64encode(data).decode(),
         "mime": MIME[Path(name).suffix]},
    )


def test_clean_file_uploaded_without_dialog(page, dialogs, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    page.set_input_files("#file", str(FIX / "clean.txt"))
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)
    assert _uploads(page) == [_expected("clean.txt")] and dialogs == []


@pytest.mark.parametrize("name", SENSITIVE_FILES)
def test_sensitive_cancel(page, dialogs, monkeypatch, name):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    page.set_input_files("#file", str(FIX / name))
    page.wait_for_function("document.getElementById('file').files.length === 0")
    _settled(page)
    assert dialogs == [name]
    assert _uploads(page) == []


@pytest.mark.parametrize("name", SENSITIVE_FILES)
def test_sensitive_continue_identical(page, dialogs, monkeypatch, name):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    page.set_input_files("#file", str(FIX / name))
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)
    assert _uploads(page) == [_expected(name)]
    assert dialogs == [name]


def test_two_files_one_flagged_cancel(page, dialogs, monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    page.set_input_files("#file", [str(FIX / "clean.txt"), str(FIX / "sensitive.txt")])
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)
    assert _uploads(page) == [_expected("clean.txt")]
    assert dialogs == ["sensitive.txt"]
    assert page.evaluate("document.getElementById('file').files.length") == 1


@pytest.mark.parametrize("kind", ["drop", "paste"])
def test_sensitive_drop_paste_cancel_continue(page, dialogs, monkeypatch, kind):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    _synthetic(page, kind, "sensitive.pdf")
    _settled(page)
    assert _uploads(page) == [] and dialogs == ["sensitive.pdf"]

    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    _synthetic(page, kind, "sensitive.pdf")
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)
    assert _uploads(page) == [_expected("sensitive.pdf")]


@pytest.mark.parametrize("kind", ["drop", "paste"])
def test_clean_drop_paste(page, dialogs, kind):
    _synthetic(page, kind, "clean.png")
    page.wait_for_function("window.__uploads.length === 1")
    _settled(page)
    assert _uploads(page) == [_expected("clean.png")] and dialogs == []


def test_plain_text_paste_not_intercepted(page, monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "handle_file", lambda p: calls.append(p) or {"action": "allow"})
    page.evaluate(
        """() => {
            const dt = new DataTransfer(); dt.setData('text/plain', 'just text');
            document.getElementById('composer').dispatchEvent(
              new ClipboardEvent('paste', {bubbles: true, cancelable: true, clipboardData: dt}));
        }"""
    )
    assert page.evaluate("window.__pasteEvents") == [{"files": 0, "text": "just text"}]
    assert calls == [] and _uploads(page) == []


def test_missing_binding_fails_open(page):
    page.evaluate("window.__wg_inspect_file = undefined")
    page.set_input_files("#file", str(FIX / "sensitive.txt"))
    page.wait_for_function("window.__uploads.length === 1")
