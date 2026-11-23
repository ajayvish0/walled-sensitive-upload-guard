import time

from walled_guard.gui import Stats, format_event


def _event(kind="prompt", flagged=False, action="allow", name="prompt", site="chatgpt"):
    return {"time": time.time(), "site": site, "kind": kind, "name": name, "flagged": flagged, "action": action}


def test_format_event_is_metadata_only():
    line = format_event(_event(kind="file", name="a.pdf", action="block", site="perplexity"))
    parts = line.split()
    assert parts[1:4] == ["perplexity", "file", "a.pdf"]
    assert line.endswith("→ blocked") and len(parts[0]) == 8 and parts[0].count(":") == 2


def test_format_event_allowed():
    assert format_event(_event()).endswith("→ allowed")


def test_counters():
    s = Stats()
    s.record(_event())
    s.record(_event(flagged=True, action="block"))
    s.record(_event(kind="file", flagged=True, action="allow", name="x.txt"))
    assert (s.prompts, s.files, s.flagged, s.allowed, s.blocked) == (2, 1, 2, 2, 1)
