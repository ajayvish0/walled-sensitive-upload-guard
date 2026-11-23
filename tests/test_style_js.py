ORANGE = "rgb(255, 122, 0)"


def _color(page, sel):
    return page.evaluate("s => getComputedStyle(document.querySelector(s)).color", sel)


def test_assistant_coloured_user_not(page):
    assert _color(page, ".fake-assistant") == ORANGE
    assert _color(page, ".fake-assistant p") == ORANGE
    assert _color(page, ".fake-user") != ORANGE


def test_style_restored_when_removed(page):
    page.evaluate("document.getElementById('__wg_style').remove()")
    page.wait_for_function("document.getElementById('__wg_style') !== null")
    assert _color(page, ".fake-assistant") == ORANGE


def test_idempotent(page):
    assert page.evaluate("document.querySelectorAll('#__wg_style').length") == 1


def test_nothing_on_other_hosts(context):
    p = context.new_page()
    p.goto("http://other.local/")
    assert p.evaluate("document.getElementById('__wg_style')") is None
    assert _color(p, ".fake-assistant") != ORANGE
