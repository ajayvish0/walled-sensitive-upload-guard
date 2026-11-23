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


def test_channel_order_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(engine.config, "PROFILE_DIR", tmp_path / "profile")
    pw = FakePlaywright({"chrome"})
    assert engine.launch_context(pw) == "context-msedge"
    assert pw.chromium.tried == ["chrome", "msedge"]


def test_falls_back_to_bundled_chromium(monkeypatch, tmp_path):
    monkeypatch.setattr(engine.config, "PROFILE_DIR", tmp_path / "profile")
    pw = FakePlaywright({"chrome", "msedge"})
    assert engine.launch_context(pw) == "context-None"
    assert pw.chromium.tried == ["chrome", "msedge", None]


def test_engine_error_when_everything_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(engine.config, "PROFILE_DIR", tmp_path / "profile")
    pw = FakePlaywright({"chrome", "msedge", None})
    with pytest.raises(engine.EngineError, match="Install Google Chrome"):
        engine.launch_context(pw)


def test_open_site_rejects_unknown():
    with pytest.raises(KeyError):
        engine.Engine().open_site("nope")
