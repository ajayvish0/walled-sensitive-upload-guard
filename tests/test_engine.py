import pytest

from walled_guard import engine


class FakeChromium:
    def __init__(self, fail_channels):
        self.fail_channels = fail_channels
        self.tried: list[str | None] = []

    def launch_persistent_context(self, profile, **kwargs):
        channel = kwargs.get("channel")
        self.tried.append(channel)
        if channel in self.fail_channels:
            raise RuntimeError("no such browser")
        return f"context-{channel}"


class FakePlaywright:
    def __init__(self, fail_channels):
        self.chromium = FakeChromium(fail_channels)


def test_launches_chrome(monkeypatch, tmp_path):
    monkeypatch.setattr(engine.config, "PROFILE_DIR", tmp_path / "profile")
    pw = FakePlaywright(set())
    assert engine.launch_context(pw) == "context-chrome"
    assert pw.chromium.tried == ["chrome"]


def test_engine_error_when_chrome_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(engine.config, "PROFILE_DIR", tmp_path / "profile")
    with pytest.raises(engine.EngineError, match="Install Google Chrome"):
        engine.launch_context(FakePlaywright({"chrome"}))
