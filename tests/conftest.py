"""Shared fixtures: Playwright browser and a routed fake chat page (no server)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["WALLED_ENABLE_HARNESS"] = "1"

from playwright.sync_api import sync_playwright  # noqa: E402

from walled_guard import browser as wg_browser  # noqa: E402

HARNESS_HTML = (Path(__file__).parent / "harness" / "index.html").read_text(encoding="utf-8")
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def pw_browser():
    with sync_playwright() as p:
        browser = None
        for channel in ("chrome", "msedge", None):
            try:
                kwargs = {"headless": True}
                if channel:
                    kwargs["channel"] = channel
                browser = p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if browser is None:
            pytest.skip("no Chrome/Edge/Chromium available")
        yield browser
        browser.close()


@pytest.fixture
def context(pw_browser):
    ctx = pw_browser.new_context()
    for host in ("harness.local", "other.local"):
        ctx.route(f"http://{host}/**", lambda route: route.fulfill(
            status=200, content_type="text/html; charset=utf-8", body=HARNESS_HTML))
    wg_browser.install_guard(ctx)
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    p.goto("http://harness.local/")
    return p
