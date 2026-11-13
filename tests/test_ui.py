"""Browser tests for the flows in TEST_CASES.md. Each test name starts with the case id it covers.

Run with:  pytest tests/test_ui.py
Set PW_CHANNEL=chrome to use an installed Chrome instead of Playwright's own Chromium.
The clock in the page is pinned to 12 November 2026, 10:00, to match the server's example data.
"""
import datetime
import os
import re

import pytest

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect
NOW = datetime.datetime(2026, 11, 12, 10, 0)


@pytest.fixture(scope="session")
def browser():
    with pw.sync_playwright() as p:
        channel = os.environ.get("PW_CHANNEL")
        b = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        yield b
        b.close()


def open_page(browser, server, path="/", **ctx):
    ctx.setdefault("reduced_motion", "reduce")  # animations are cosmetic; keep figures final for assertions
    context = browser.new_context(**ctx)
    page = context.new_page()
    page.clock.set_fixed_time(NOW)
    page.goto(server.url + path)
    expect(page.locator("#view .card").first).to_be_visible()
    expect(page.locator("#view")).not_to_contain_text("Loading your figures")
    return page


@pytest.fixture
def page(browser, server):
    p = open_page(browser, server)
    yield p
    p.context.close()


@pytest.fixture
def blank(browser, empty_server):
    p = open_page(browser, empty_server)
    yield p
    p.context.close()


def money(text):
    return int(re.sub(r"[^\d-]", "", text.replace("−", "-")))


def go(page, view):
    page.click('#nav button[data-id="%s"]' % view)


def add_payment(page, desc, amount, category="Groceries", direction="Money out", who=None):
    page.click("#btn-add")
    page.fill("#f-desc", desc)
    page.fill("#f-amount", str(amount))
    page.select_option("#f-dir", direction)
    page.select_option("#f-category", category)
    if who:
        page.select_option("#f-who", who)
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Payment added")


# ---------------------------------------------------------------- overview

def test_OV01_overview_shows_usd_example_figures(page, server):
    expect(page.locator("#greet")).to_have_text("Good morning")
    expect(page.locator("#date")).to_have_text("Thursday, November 12")
    expect(page.locator("#mlabel")).to_have_text("November 2026")
    expect(page.locator("#balance")).to_have_text("${:,}".format(round(server.balance())))
    expect(page.locator("#banner")).to_contain_text("Example data")
    expect(page.locator("#lede")).to_contain_text("Paycheck (Sam) lands in 8 days")
    for card in ("c-balance", "c-flow", "c-cats", "c-tx", "c-noticed", "c-pots", "c-due"):
        expect(page.locator("#" + card)).to_be_visible()
    expect(page.locator("#chart svg")).to_be_visible()
    expect(page.locator("#c-tx .row")).to_have_count(6)


def test_OV02_safe_to_spend_is_balance_minus_unpaid_bills(page, server):
    unpaid = sum(-r["amount"] for r in server.docs("recurring").values() if r["amount"] < 0 and r["day"] > 12)
    assert money(page.locator("#safe b").inner_text()) == round(server.balance() - unpaid)
    expect(page.locator("#safe")).to_contain_text("18 days left")


def test_OV03_forecast_ends_at_balance_plus_what_is_due(page, server):
    due = sum(r["amount"] for r in server.docs("recurring").values() if r["day"] > 12)
    assert abs(money(page.locator("#month-end").inner_text()) - round(server.balance() + due)) <= 1
    assert page.locator("#chart circle").count() == sum(1 for r in server.docs("recurring").values() if r["day"] > 12)


def test_OV04_period_switch_changes_the_months_shown(page):
    expect(page.locator("#c-flow .flow .col")).to_have_count(6)
    page.click('#c-flow .seg button[data-id="3"]')
    expect(page.locator("#c-flow .flow .col")).to_have_count(3)
    page.click('#c-flow .seg button[data-id="12"]')
    expect(page.locator("#c-flow .flow .col")).to_have_count(12)
    expect(page.locator('#c-flow .seg button[data-id="12"]')).to_have_attribute("aria-pressed", "true")


def test_OV05_noticed_card_pages_through_observations(page):
    first = page.locator("#c-noticed h3").inner_text()
    expect(page.locator("#note-pos")).to_contain_text("1 of")
    page.click('#c-noticed button[data-id="1"]')
    expect(page.locator("#note-pos")).to_contain_text("2 of")
    assert page.locator("#c-noticed h3").inner_text() != first
    page.click("#c-noticed .link")
    assert page.locator("#greet").inner_text() != "Good morning"


def test_OV06_empty_household_shows_guidance_not_errors(blank):
    expect(blank.locator("#balance")).to_have_text("$0")
    expect(blank.locator("#banner")).to_be_hidden()
    expect(blank.locator("#c-tx")).to_contain_text("No payments recorded")
    expect(blank.locator("#c-pots")).to_contain_text("No pots yet")
    expect(blank.locator("#c-due")).to_contain_text("No regular bills")
    expect(blank.locator("#c-noticed")).to_contain_text("Nothing stands out")


# ---------------------------------------------------------------- navigation

def test_NAV01_every_page_opens_from_the_sidebar(page):
    for view, title in (("payments", "Payments"), ("bills", "Bills"), ("budgets", "Budgets"), ("pots", "Pots"),
                        ("insights", "Insights"), ("household", "Household"), ("accounts", "Accounts"), ("overview", "Good morning")):
        go(page, view)
        expect(page.locator("#greet")).to_have_text(title)
        expect(page.locator('#nav button[data-id="%s"]' % view)).to_have_attribute("aria-current", "page")
        assert page.url.endswith("#" + view)


def test_NAV02_a_link_with_a_page_name_opens_that_page(browser, server):
    p = open_page(browser, server, "/#bills")
    expect(p.locator("#greet")).to_have_text("Bills")
    p.goto(server.url + "/#nonsense")
    p.reload()
    expect(p.locator("#greet")).to_have_text("Good morning")
    p.context.close()


def test_NAV03_month_navigation(page):
    expect(page.locator("#next")).to_be_disabled()
    page.click("#prev")
    expect(page.locator("#mlabel")).to_have_text("October 2026")
    expect(page.locator("#lede")).to_have_text("Looking back at October 2026.")
    expect(page.locator("#c-balance h2")).to_have_text("Balance at the end of October")
    expect(page.locator('#c-due button[data-act="pay"]')).to_have_count(0)
    expect(page.locator("#next")).to_be_enabled()
    page.click("#next")
    expect(page.locator("#mlabel")).to_have_text("November 2026")
    expect(page.locator("#next")).to_be_disabled()


def test_NAV04_phone_layout_has_bottom_bar_and_no_sideways_scroll(browser, server):
    p = open_page(browser, server, viewport={"width": 375, "height": 812})
    box = p.locator("#nav").bounding_box()
    assert box["y"] > 700
    expect(p.locator(".safe")).to_be_hidden()
    for view in ("overview", "payments", "insights", "accounts"):
        go(p, view)
        assert p.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), view
    p.context.close()


def test_NAV05_theme_button_cycles_and_is_remembered(page):
    html = page.locator("html")
    page.click("#btn-theme")
    expect(html).to_have_attribute("data-theme", "light")
    page.click("#btn-theme")
    expect(html).to_have_attribute("data-theme", "dark")
    page.reload()
    expect(html).to_have_attribute("data-theme", "dark")
    page.click("#btn-theme")
    assert html.get_attribute("data-theme") is None


# ---------------------------------------------------------------- payments

def test_PAY01_add_a_payment(page, server):
    before = round(server.balance())
    add_payment(page, "Bike repair", 80, "Transport", who="Sam")
    expect(page.locator("#balance")).to_have_text("${:,}".format(before - 80))
    go(page, "payments")
    row = page.locator("#tx-list .row", has_text="Bike repair")
    expect(row).to_contain_text("Today · Transport · Sam")
    expect(row).to_contain_text("−$80")
    saved = [t for t in server.docs("transactions").values() if t["desc"] == "Bike repair"]
    assert saved == [{"date": "2026-11-12", "desc": "Bike repair", "amount": -80, "category": "Transport", "who": "Sam"}]


def test_PAY02_add_money_in(page, server):
    before = round(server.balance())
    add_payment(page, "Tax refund", 250, direction="Money in")
    expect(page.locator("#balance")).to_have_text("${:,}".format(before + 250))
    go(page, "payments")
    expect(page.locator("#tx-list .row", has_text="Tax refund")).to_contain_text("+$250")
    expect(page.locator("#tx-list .row", has_text="Tax refund")).to_contain_text("Income")


def test_PAY03_amount_is_required(page, server):
    count = len(server.docs("transactions"))
    page.click("#btn-add")
    page.fill("#f-desc", "No amount")
    page.click("#dlg-ok")
    expect(page.locator("#dlg")).to_be_visible()
    page.click("#dlg-cancel")
    expect(page.locator("#dlg")).to_be_hidden()
    assert len(server.docs("transactions")) == count


def test_PAY04_edit_a_payment_and_remember_its_category(page, server):
    go(page, "payments")
    page.locator("#tx-list .row", has_text="Hardware store").click()
    expect(page.locator("#dlg h2")).to_have_text("Edit payment")
    expect(page.locator("#f-desc")).to_have_value("Hardware store")
    page.select_option("#f-category", "Housing")
    page.check("#remember")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("filed under Housing")
    expect(page.locator("#tx-list .row", has_text="Hardware store")).to_contain_text("Housing")
    assert list(server.docs("rules").values()) == [{"match": "hardware store", "category": "Housing"}]
    go(page, "accounts")
    expect(page.locator("#c-data")).to_contain_text("1 category rule remembered")
    page.click('#c-data [data-act="rules"]')
    page.click('#dlg [data-act="del-rule"]')
    expect(page.locator("#toast")).to_contain_text("Rule forgotten")
    assert server.docs("rules") == {}


def test_PAY05_keyboard_opens_a_payment(page):
    go(page, "payments")
    page.locator("#tx-list .row").first.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#dlg h2")).to_have_text("Edit payment")


def test_PAY06_delete_and_undo(page, server):
    go(page, "payments")
    total = len(server.docs("transactions"))
    row = page.locator("#tx-list .row", has_text="Pharmacy")
    row.locator('[data-act="del-tx"]').click()
    expect(page.locator("#toast")).to_contain_text("Payment deleted")
    expect(page.locator("#tx-list .row", has_text="Pharmacy")).to_have_count(0)
    assert len(server.docs("transactions")) == total - 1
    page.click("#toast-undo")
    expect(page.locator("#tx-list .row", has_text="Pharmacy")).to_have_count(1)
    assert len(server.docs("transactions")) == total


def test_PAY07_search_and_category_filter(page):
    go(page, "payments")
    all_rows = page.locator("#tx-list .row").count()
    page.fill("#q", "grocery")
    expect(page.locator("#tx-list .row")).to_have_count(2)
    expect(page.locator("#tx-count")).to_contain_text("2 entries")
    expect(page.locator("#q")).to_be_focused()
    page.fill("#q", "zzz")
    expect(page.locator("#tx-list")).to_contain_text("No payments match")
    page.fill("#q", "")
    page.select_option("#fcat", "Dining")
    rows = page.locator("#tx-list .row")
    assert 0 < rows.count() < all_rows
    for i in range(rows.count()):
        expect(rows.nth(i)).to_contain_text("Dining")
    page.select_option("#fcat", "Income")
    expect(page.locator("#tx-list .row")).to_have_count(1)


def test_PAY08_text_typed_by_people_is_never_run_as_code(page):
    add_payment(page, '<img src=x onerror="window.__hacked=1">', 5)
    go(page, "payments")
    expect(page.locator("#tx-list")).to_contain_text('<img src=x onerror="window.__hacked=1">')
    assert page.evaluate("window.__hacked") is None
    assert page.locator("#tx-list img").count() == 0


def test_PAY09_import_a_statement(page, server, tmp_path):
    f = tmp_path / "statement.csv"
    f.write_text("Date,Description,Amount\n11/09/2026,TRADER JOE'S #12,-61.30\n11/10/2026,SHELL OIL 5521,-39.00\n11/11/2026,ACME PAYROLL,1200.00\n")
    go(page, "payments")
    page.set_input_files("#csv-file", str(f))
    expect(page.locator("#csv-summary")).to_contain_text("3 new payments")
    expect(page.locator("#dlg table tbody tr")).to_have_count(3)
    expect(page.locator("#dlg table")).to_contain_text("Groceries")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Imported 3 payments")
    expect(page.locator("#tx-list .row", has_text="TRADER JOE'S #12")).to_contain_text("Groceries")
    expect(page.locator("#tx-list .row", has_text="SHELL OIL 5521")).to_contain_text("Transport")
    # the same file again brings in nothing
    page.set_input_files("#csv-file", str(f))
    expect(page.locator("#csv-summary")).to_contain_text("0 new payments")
    expect(page.locator("#dlg-ok")).to_be_disabled()
    page.click("#dlg-cancel")


def test_PAY10_statement_with_reversed_amounts(blank, empty_server, tmp_path):
    f = tmp_path / "card.csv"
    f.write_text("Date,Description,Amount\n11/10/2026,Bookshop,24.00\n")
    go(blank, "payments")
    blank.set_input_files("#csv-file", str(f))
    expect(blank.locator("#dlg table")).to_contain_text("+$24")
    blank.check("#csv-flip")
    expect(blank.locator("#dlg table")).to_contain_text("−$24")
    blank.click("#dlg-ok")
    expect(blank.locator("#toast")).to_contain_text("Imported 1 payment")
    assert [t["amount"] for t in empty_server.docs("transactions").values()] == [-24.0]


def test_PAY11_unreadable_statement_is_explained(page, tmp_path):
    f = tmp_path / "notes.csv"
    f.write_text("hello,world\n1,2\n")
    go(page, "payments")
    page.set_input_files("#csv-file", str(f))
    expect(page.locator("#toast")).to_contain_text("No header row with a date column")


def test_PAY12_export_link(page):
    go(page, "payments")
    link = page.locator('#c-tx a[href="api/export.csv"]')
    expect(link).to_have_attribute("download", "payments.csv")
    with page.expect_download() as d:
        link.click()
    assert d.value.suggested_filename == "payments.csv"


# ---------------------------------------------------------------- bills

def test_BILL01_mark_a_bill_paid(page, server):
    go(page, "bills")
    row = page.locator('[data-rec="power"]')
    expect(row).to_contain_text("in 3 days")
    safe_before = money(page.locator("#safe b").inner_text())
    row.locator('[data-act="pay"]').click()
    expect(page.locator("#toast")).to_contain_text("Marked paid")
    expect(row).to_contain_text("paid")
    expect(row.locator('[data-act="pay"]')).to_have_count(0)
    assert money(page.locator("#safe b").inner_text()) == safe_before
    paid = [t for t in server.docs("transactions").values() if t.get("recId") == "power" and t["date"] == "2026-11-12"]
    assert len(paid) == 1 and paid[0]["amount"] == -96


def test_BILL02_mark_a_payday_received(page, server):
    before = round(server.balance())
    go(page, "bills")
    page.locator('[data-rec="pay-b"] [data-act="pay"]').click()
    expect(page.locator("#toast")).to_contain_text("Marked received")
    go(page, "overview")
    expect(page.locator("#balance")).to_have_text("${:,}".format(before + 3900))


def test_BILL03_add_and_remove_a_bill(page, server):
    go(page, "bills")
    count = page.locator("#c-due .row").count()
    page.click('#c-due [data-act="add-rec"]')
    page.fill("#f-name", "Water")
    page.fill("#f-amount", "40")
    page.fill("#f-day", "25")
    page.select_option("#f-category", "Utilities")
    page.click("#dlg-ok")
    row = page.locator("#c-due .row", has_text="Water")
    expect(row).to_contain_text("in 13 days")
    expect(page.locator("#c-due .row")).to_have_count(count + 1)
    row.locator('[data-act="del-rec"]').click()
    expect(page.locator("#toast")).to_contain_text("Removed Water")
    expect(page.locator("#c-due .row")).to_have_count(count)
    page.click("#toast-undo")
    expect(page.locator("#c-due .row")).to_have_count(count + 1)


def test_BILL04_overdue_bill_is_flagged(blank, empty_server):
    empty_server.call("PUT", "/api/doc/recurring/late", {"name": "Late fee", "amount": -30, "day": 5, "category": "Other"})
    go(blank, "bills")
    expect(blank.locator('[data-rec="late"] .pill.bad')).to_have_text("Overdue")


# ---------------------------------------------------------------- budgets, pots, household

def test_BUD01_set_a_budget_and_see_over_budget(page):
    go(page, "budgets")
    expect(page.locator('[data-cat="Housing"]')).to_contain_text("no budget")
    page.click('#c-budgets [data-act="settings"]')
    page.fill("#b-Housing", "2000")
    page.fill("#b-Dining", "")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Settings saved")
    expect(page.locator('[data-cat="Housing"]')).to_contain_text("of $2,000")
    expect(page.locator('[data-cat="Housing"] .pill.bad')).to_have_text("Over")
    expect(page.locator('[data-cat="Dining"]')).to_contain_text("no budget")
    go(page, "overview")
    expect(page.locator("#c-cats")).to_contain_text("Over")


def test_POT01_create_a_pot_and_move_money_in(page, server):
    before = round(server.balance())
    go(page, "pots")
    page.click('[data-act="add-pot"]')
    page.fill("#f-name", "New bike")
    page.fill("#f-target", "800")
    page.fill("#f-saved", "100")
    page.click("#dlg-ok")
    pot = page.locator("#c-pots .cat", has_text="New bike")
    expect(pot).to_contain_text("$100 of $800")
    pot.locator('[data-act="pot"]').click()
    page.fill("#f-amount", "700")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Moved $700 to New bike")
    expect(pot).to_contain_text("$800 of $800")
    expect(pot.locator(".pill.ok")).to_have_text("Full")
    go(page, "overview")
    expect(page.locator("#balance")).to_have_text("${:,}".format(before - 700))
    go(page, "payments")
    expect(page.locator("#tx-list .row", has_text="To New bike")).to_contain_text("Savings")


def test_POT02_remove_a_pot(page):
    go(page, "pots")
    page.locator('[data-pot="s-trip"] [data-act="pot"]').click()
    page.click("#dlg-extra")
    expect(page.locator("#toast")).to_contain_text("Removed Summer trip")
    expect(page.locator('[data-pot="s-trip"]')).to_have_count(0)


def test_HOUSE01_spending_is_split_by_person(page):
    go(page, "household")
    card = page.locator("#c-house")
    for name in ("Alex", "Sam", "Shared"):
        expect(card.locator(".cat", has_text=name).first).to_be_visible()
    expect(card.locator(".cat", has_text="Alex").first).to_contain_text("brought in $4,850")


# ---------------------------------------------------------------- insights

def test_INS01_insights_page(page):
    go(page, "insights")
    expect(page.locator("#heat div")).to_have_count(30)
    expect(page.locator("#heat div.future")).to_have_count(18)
    expect(page.locator("#c-split")).to_contain_text("guide 50%")
    assert page.locator("#c-trend tbody tr").count() >= 5
    expect(page.locator("#c-biggest .row").first).to_contain_text("Rent")


# ---------------------------------------------------------------- settings and example data

def test_SET01_household_name_currency_and_people(page):
    page.click("#btn-settings")
    page.fill("#f-household", "The Parkers")
    page.select_option("#f-currency", "EUR")
    page.fill("#f-members", "Jo, Max, Kit")
    page.click("#dlg-ok")
    expect(page.locator("#title")).to_have_text("The Parkers")
    expect(page.locator("#balance")).to_contain_text("€")
    page.click("#btn-add")
    assert page.locator("#f-who option").all_inner_texts() == ["Shared", "Jo", "Max", "Kit"]


def test_SET02_clear_examples_needs_a_second_click(page, server):
    page.click('[data-act="clear-ask"]')
    expect(page.locator("#banner")).to_contain_text("Delete")
    page.click('[data-act="clear-no"]')
    assert len(server.docs("transactions")) > 100
    page.click('[data-act="clear-ask"]')
    page.click('[data-act="clear-yes"]')
    expect(page.locator("#toast")).to_contain_text("Examples cleared")
    expect(page.locator("#banner")).to_be_hidden()
    expect(page.locator("#balance")).to_have_text("$0")
    c = server.data()["collections"]
    assert not c["transactions"] and not c["pots"] and not c["recurring"] and not c["budgets"]
    assert c["settings"]["main"]["currency"] == "USD" and "sample" not in c["settings"]["main"]


def test_SET03_clearing_examples_keeps_your_own_entries(page, server):
    add_payment(page, "My real payment", 12)
    page.click('[data-act="clear-ask"]')
    page.click('[data-act="clear-yes"]')
    expect(page.locator("#banner")).to_be_hidden()
    assert [t["desc"] for t in server.docs("transactions").values()] == ["My real payment"]


# ---------------------------------------------------------------- data

def test_DATA01_backup_download(page):
    go(page, "accounts")
    with page.expect_download() as d:
        page.click('#c-data a[href="api/backup.json"]')
    assert d.value.suggested_filename == "finance-backup.json"


# ---------------------------------------------------------------- resilience

def test_NET01_changes_made_elsewhere_appear_without_reloading(page, server):
    go(page, "payments")
    server.call("PUT", "/api/doc/transactions/other-device", {"date": "2026-11-12", "desc": "Added on my phone", "amount": -3, "category": "Dining", "who": ""})
    page.clock.run_for(5000)
    expect(page.locator("#tx-list .row", has_text="Added on my phone")).to_be_visible(timeout=10000)


def test_NET02_server_going_away_is_reported_and_recovers(page, server):
    server.stop()
    page.clock.run_for(5000)
    expect(page.locator("#banner")).to_contain_text("Cannot reach the finances server", timeout=10000)
    page.click("#btn-add")
    page.fill("#f-desc", "Offline")
    page.fill("#f-amount", "1")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Nothing was saved")
    server.start()
    page.clock.run_for(5000)
    expect(page.locator("#banner")).to_contain_text("Example data", timeout=10000)
