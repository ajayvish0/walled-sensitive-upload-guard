from walled_guard import config


def test_marker():
    assert config.MARKER == "WALLED_SENSITIVE"


def test_marker_bytes():
    assert config.MARKER_BYTES == config.MARKER.encode()


def test_sites():
    assert {"chatgpt", "perplexity"} <= set(config.SITES)


def test_harness_flag_read_at_call_time(monkeypatch):
    monkeypatch.delenv("WALLED_ENABLE_HARNESS", raising=False)
    assert config.harness_enabled() is False
    monkeypatch.setenv("WALLED_ENABLE_HARNESS", "1")
    assert config.harness_enabled() is True
