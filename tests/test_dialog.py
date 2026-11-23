import subprocess

from walled_guard import dialog


def test_auto_continue(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "continue")
    assert dialog.confirm("prompt", "x") is True


def test_auto_cancel(monkeypatch):
    monkeypatch.setenv("WALLED_DIALOG_AUTO", "cancel")
    assert dialog.confirm("file", "x.pdf") is False


def test_launch_failure_is_fail_closed(monkeypatch):
    monkeypatch.delenv("WALLED_DIALOG_AUTO", raising=False)

    def boom(*a, **k):
        raise OSError("nope")

    monkeypatch.setattr(subprocess, "run", boom)
    assert dialog.confirm("prompt", "x") is False


def test_nonzero_exit_blocks(monkeypatch):
    monkeypatch.delenv("WALLED_DIALOG_AUTO", raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, -9))
    assert dialog.confirm("prompt", "x") is False


def test_zero_exit_continues(monkeypatch):
    monkeypatch.delenv("WALLED_DIALOG_AUTO", raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0))
    assert dialog.confirm("prompt", "x") is True


def test_prompt_preview_truncates():
    out = dialog.prompt_preview("a" * 400)
    assert out.startswith("a" * 150 + "…") and "(400 characters)" in out
    assert "\n" not in dialog.prompt_preview("a\nb")
