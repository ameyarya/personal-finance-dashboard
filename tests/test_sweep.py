"""A sweep over every page, in month and year view, on phone, tablet and desktop, with example data and with none:
no script errors, no 'undefined' or 'NaN' on screen, nothing wider than the window, and the header agrees with the page."""
import re
import pytest
from playwright.sync_api import expect
from test_ui import go, open_page

VIEWS = ["overview", "cards", "payments", "bills", "budgets", "insights", "household", "check", "accounts"]
SIZES = [(390, 800), (768, 1000), (1280, 800)]
BAD = re.compile(r"undefined|NaN|\[object|\bnull\b|Infinity|Invalid Date", re.I)


def problems(page, tag, errors):
    found = list(errors)
    text = page.locator("#view").inner_text()
    m = BAD.search(text)
    if m:
        found.append("%s: shows '%s' near: %s" % (tag, m.group(0), text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")))
    if page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"):
        wide = page.evaluate("""() => [...document.querySelectorAll('#view *')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
                                  .slice(0, 3).map(e => e.tagName + '.' + e.className + ' ' + (e.innerText || '').slice(0, 30))""")
        found.append("%s: wider than the window: %s" % (tag, wide))
    return found


def sweep(browser, srv, width, height):
    p = open_page(browser, srv, viewport={"width": width, "height": height})
    errors = []
    p.on("pageerror", lambda e: errors.append("script error: %s" % e))
    p.on("console", lambda m: errors.append("console: %s" % m.text) if m.type == "error" else None)
    found = []
    for view in VIEWS:
        go(p, view)
        for period in ("month", "year"):
            p.click('#period [data-id="%s"]' % period)
            for step in ("", "#prev", "#prev", "#next", "#next", "#next"):
                if step and p.locator(step).is_enabled():
                    p.click(step)
                p.wait_for_timeout(60)
                tag = "%s/%s/%dpx/%s" % (view, period, width, p.locator("#mlabel").inner_text())
                found += problems(p, tag, errors)
                errors.clear()
                label = p.locator("#mlabel").inner_text()
                if period == "year" and not re.fullmatch(r"\d{4}", label):
                    found.append("%s: year view shows '%s'" % (tag, label))
                if period == "month" and re.fullmatch(r"\d{4}", label):
                    found.append("%s: month view shows '%s'" % (tag, label))
    p.context.close()
    return found


@pytest.mark.parametrize("width,height", SIZES)
def test_sweep_with_example_data(browser, server, width, height):
    found = sweep(browser, server, width, height)
    assert not found, "\n".join(sorted(set(found))[:25])


@pytest.mark.parametrize("width,height", SIZES)
def test_sweep_with_no_data(browser, empty_server, width, height):
    found = sweep(browser, empty_server, width, height)
    assert not found, "\n".join(sorted(set(found))[:25])


def test_the_page_makes_no_request_to_any_other_site_and_its_fonts_load_from_here(browser, server):
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    page.goto(server.url + "/")
    expect(page.locator("#view .card").first).to_be_visible()
    page.wait_for_timeout(500)
    outside = [u for u in urls if not u.startswith(server.url) and not u.startswith("data:")]
    assert not outside, outside
    assert page.evaluate("document.fonts.check('16px Inter') && document.fonts.check('600 16px Sora')")
    assert page.evaluate("[...document.fonts].filter(f => f.status === 'loaded').length") >= 1
    context.close()
