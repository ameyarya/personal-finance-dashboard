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
    for card in ("c-balance", "c-flow", "c-cats", "c-tx", "c-noticed", "c-due"):
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
    expect(blank.locator("#c-due")).to_contain_text("No regular bills")
    expect(blank.locator("#c-noticed")).to_contain_text("Nothing stands out")


# ---------------------------------------------------------------- navigation

def test_NAV01_every_page_opens_from_the_sidebar(page):
    for view, title in (("payments", "Payments"), ("bills", "Bills"), ("budgets", "Budgets"), ("cards", "Cards"),
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


def test_NAV05_theme_button_toggles_light_and_dark_and_is_remembered(page, server):
    html = page.locator("html")
    first = html.get_attribute("data-theme")
    assert first in ("light", "dark")
    other = "light" if first == "dark" else "dark"
    page.click("#btn-theme")
    expect(html).to_have_attribute("data-theme", other)
    page.click("#btn-theme")
    expect(html).to_have_attribute("data-theme", first)
    page.click("#btn-theme")
    page.reload()
    expect(html).to_have_attribute("data-theme", other)
    assert server.docs("settings")["main"]["theme"] == other   # kept in the data file too


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


# ---------------------------------------------------------------- budgets, household

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
    assert not c["transactions"] and not c["recurring"] and not c["budgets"]
    assert c["settings"]["main"]["currency"] == "USD" and "sample" not in c["settings"]["main"]


def test_SET03_clearing_examples_keeps_your_own_entries(page, server):
    add_payment(page, "My real payment", 12)
    page.click('[data-act="clear-ask"]')
    page.click('[data-act="clear-yes"]')
    expect(page.locator("#banner")).to_be_hidden()
    assert [t["desc"] for t in server.docs("transactions").values()] == ["My real payment"]


# ---------------------------------------------------------------- cards

def test_CARD01_cards_screen_groups_payments_by_card(blank, empty_server):
    for i, (card, amt) in enumerate([("Visa", -40), ("Visa", -10), ("Store card", -25)]):
        empty_server.call("PUT", "/api/doc/transactions/c%d" % i, {"date": "2026-11-05", "desc": "Thing %d" % i, "amount": amt, "category": "Shopping", "who": "", "card": card})
    blank.reload()
    go(blank, "cards")
    expect(blank.locator("#c-stack .vcard")).to_have_count(2)
    expect(blank.locator("#c-clist .row")).to_have_count(2)
    expect(blank.locator("#c-cdet")).to_contain_text("Visa")
    blank.locator("#c-clist .row", has_text="Store card").click()
    expect(blank.locator("#c-cdet")).to_contain_text("Store card")
    expect(blank.locator("#c-cpay")).to_contain_text("Thing 2")
    blank.locator("#c-stack .vcard[data-act=cflip]").click()
    expect(blank.locator("#c-stack .vcard.flip")).to_have_count(1)


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


# ---------------------------------------------------------------- this round: removed pieces, year view, owners, sync, dropdowns

def test_GONE01_no_pots_no_send_icon(page):
    expect(page.locator("#btn-send")).to_have_count(0)
    expect(page.locator('#nav button[data-id="pots"]')).to_have_count(0)
    page.goto(page.url.split("#")[0] + "#pots")
    expect(page.locator("#greet")).to_have_text("Good morning")      # an unknown page falls back to the overview
    expect(page.locator("#c-pots")).to_have_count(0)


def test_GONE02_fiscal_year_card_is_gone(blank, empty_server):
    empty_server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 0, "members": ["A"], "fiscalYear": 2025})
    empty_server.call("PUT", "/api/doc/transactions/x", {"date": "2025-03-04", "desc": "Thing", "amount": -5, "category": "Dining", "who": ""})
    blank.reload()
    expect(blank.locator("#c-tx")).to_be_visible()
    expect(blank.locator("#safe")).to_be_hidden()
    assert "left after spending" not in blank.locator("body").inner_text()


def seed_year(server):
    server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 1000, "members": ["Amy", "Bo"], "fiscalYear": 2025})
    for i, (d, a, c) in enumerate([("2025-01-10", -100, "Groceries"), ("2025-02-10", -200, "Dining"), ("2025-03-10", -50, "Groceries"), ("2025-03-11", 3000, "Income")]):
        server.call("PUT", "/api/doc/transactions/y%d" % i, {"date": d, "desc": "Row %d" % i, "amount": a, "category": c, "who": ""})


def test_YEAR01_every_screen_has_a_year_view(blank, empty_server):
    seed_year(empty_server)
    blank.reload()
    go(blank, "overview")
    blank.click('#period [data-id="year"]')
    expect(blank.locator("#mlabel")).to_have_text("2025")
    expect(blank.locator("#c-balance")).to_contain_text("Cash balance at the end of 2025")
    expect(blank.locator("#c-balance")).to_contain_text("$3,650")                    # 1000 - 350 + 3000
    expect(blank.locator("#c-balance .tile", has_text="Out")).to_contain_text("$350")
    for view in ("payments", "bills", "budgets", "cards", "insights", "household", "accounts"):
        go(blank, view)
        expect(blank.locator("#mlabel")).to_have_text("2025")
        expect(blank.locator("#view .card").first).to_be_visible()
        assert blank.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), view
    go(blank, "payments")
    expect(blank.locator("#tx-count")).to_contain_text("4 entries")
    go(blank, "bills")
    expect(blank.locator("#c-due")).to_contain_text("Pick a single month")
    go(blank, "insights")
    expect(blank.locator("#heat")).to_contain_text("Mar")
    expect(blank.locator("#c-trend")).to_contain_text("Groceries")
    blank.click('#period [data-id="month"]')
    expect(blank.locator("#mlabel")).to_have_text("March 2025")


def test_YEAR02_year_nav_stays_inside_the_fiscal_year_and_is_remembered(blank, empty_server):
    seed_year(empty_server)
    blank.reload()
    blank.click('#period [data-id="year"]')
    expect(blank.locator("#prev")).to_be_disabled()
    expect(blank.locator("#next")).to_be_disabled()
    blank.reload()
    expect(blank.locator("#mlabel")).to_have_text("2025")          # the choice survived a reload
    assert empty_server.docs("settings")["main"]["prefs"]["period"] == "year"


def test_PERSIST01_names_are_saved_in_the_data_file(page, server):
    page.click("#btn-settings")
    page.fill("#f-household", "The Test House")
    page.fill("#f-members", "Una, Dos")
    page.click("#dlg-ok")
    expect(page.locator("#title")).to_have_text("The Test House")
    s = server.docs("settings")["main"]
    assert s["household"] == "The Test House" and s["members"] == ["Una", "Dos"]
    page.reload()
    expect(page.locator("#title")).to_have_text("The Test House")


def seed_cards(server):
    for i, (card, amt) in enumerate([("Visa", -40), ("Visa", -10), ("Store card", -25)]):
        server.call("PUT", "/api/doc/transactions/c%d" % i, {"date": "2026-11-05", "desc": "Thing %d" % i, "amount": amt, "category": "Shopping", "who": "", "card": card})


def test_CARD02_a_card_can_be_labelled_shared_or_given_to_a_person(blank, empty_server):
    empty_server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 0, "members": ["Una", "Dos"]})
    seed_cards(empty_server)
    blank.reload()
    go(blank, "cards")
    expect(blank.locator("#c-cdet")).to_contain_text("Shared")
    assert blank.locator("#cowner option").all_inner_texts() == ["Shared", "Una", "Dos"]
    blank.select_option("#cowner", "Una")
    expect(blank.locator("#toast")).to_contain_text("Owner saved")
    expect(blank.locator("#c-stack .vcard[data-act=cflip]")).to_contain_text("Una")
    assert empty_server.docs("settings")["main"]["cardMeta"]["Visa"]["owner"] == "Una"
    blank.reload()
    go(blank, "cards")
    expect(blank.locator("#c-clist .row", has_text="Visa")).to_contain_text("Una")


def test_CARD03_limit_slider_saves_and_flags_overspend(blank, empty_server):
    seed_cards(empty_server)
    empty_server.call("PUT", "/api/doc/transactions/c9", {"date": "2026-11-06", "desc": "Big", "amount": -30, "category": "Shopping", "who": "", "card": "Visa"})
    blank.reload()
    go(blank, "cards")
    expect(blank.locator("#c-cdet .pill.ok")).to_have_text("On track")
    blank.locator("#lim").evaluate("e => { e.value = 50; e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})) }")
    expect(blank.locator("#c-cdet .pill.bad")).to_have_text("Over limit")     # Visa spent $80 against a $50 limit
    assert empty_server.docs("settings")["main"]["cardLimits"]["Visa"] == 50


def test_SELECT01_every_dropdown_has_the_same_arrow_and_inset(page):
    checks = """() => [...document.querySelectorAll('select')].map(s => { const c = getComputedStyle(s);
        return [c.appearance, c.backgroundImage.startsWith('url'), c.backgroundPosition, c.backgroundRepeat, parseFloat(c.paddingRight)] })"""
    go(page, "payments")
    seen = page.evaluate(checks)
    page.click("#btn-add")
    seen += page.evaluate(checks)
    page.click("#dlg-cancel")
    assert len(seen) >= 4
    assert all(row == seen[0] for row in seen), seen
    assert seen[0][0] == "none" and seen[0][1] is True and seen[0][4] >= 30


def test_SYNC01_sync_card_saves_its_settings(blank, empty_server):
    go(blank, "accounts")
    expect(blank.locator("#c-sync")).to_contain_text("Statement sync")
    blank.fill("#sy-link", "https://drive.google.com/drive/folders/abc123")
    blank.fill("#sy-every", "30")
    blank.click('[data-act="save-sync"]')
    expect(blank.locator("#toast")).to_contain_text("Sync settings saved")
    sync = empty_server.docs("settings")["main"]["sync"]
    assert sync["driveLink"].endswith("abc123") and sync["everyMinutes"] == 30


def make_pdf(browser, path, body):
    context = browser.new_context()
    page = context.new_page()
    page.set_content("<body style='font:12px sans-serif'>" + body + "</body>")
    page.pdf(path=str(path))
    context.close()


def test_SYNC02_manual_sync_reads_a_pdf_and_adds_only_new_payments(browser, blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    folder = tmp_path / "statements"
    folder.mkdir()
    make_pdf(browser, folder / "bofa.pdf",
             "Bank of America Your Adv Plus Banking for November 13, 2025 to December 15, 2025 Account number: 1<br>"
             "Deposits and other additions Date Description Amount<br>11/24/25 Payroll from ACME CO 2,500.00<br>Total deposits and other additions $2,500.00<br>"
             "Withdrawals and other subtractions Date Description Amount<br>12/02/25 Zelle payment to A FRIEND -40.00<br>Total withdrawals and other subtractions -$40.00")
    empty_server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 0, "members": ["A"], "fiscalYear": 2025,
                                                        "sync": {"localFolder": str(folder), "auto": False}})
    blank.reload()
    go(blank, "accounts")
    blank.click('#c-sync [data-act="sync"]')
    expect(blank.locator("#c-sync #sy-status")).to_contain_text("2 new payments", timeout=20000)
    rows = [t for t in empty_server.docs("transactions").values() if t.get("source") == "pdf"]
    assert sorted(t["amount"] for t in rows) == [-40.0, 2500.0] and all(t["cash"] for t in rows)
    blank.click('#c-sync [data-act="sync"]')
    expect(blank.locator("#c-sync #sy-status")).to_contain_text("0 new payments", timeout=20000)     # nothing is added twice
    assert len([t for t in empty_server.docs("transactions").values() if t.get("source") == "pdf"]) == 2


def test_SYNC03_sync_edge_cases_give_plain_messages(blank, empty_server, tmp_path):
    base = {"household": "H", "currency": "USD", "opening": 0, "members": ["A"]}
    go(blank, "accounts")
    blank.click('#c-sync [data-act="sync"]')
    expect(blank.locator("#c-sync #sy-status")).to_contain_text("Add a Google Drive folder link or a local folder", timeout=20000)
    for sync, message in (({"localFolder": str(tmp_path / "nope")}, "does not exist"), ({"driveLink": "not a link"}, "does not look like a Google Drive folder link")):
        empty_server.call("PUT", "/api/doc/settings/main", dict(base, sync=sync))
        blank.reload()
        go(blank, "accounts")
        blank.click('#c-sync [data-act="sync"]')
        expect(blank.locator("#c-sync #sy-status")).to_contain_text(message, timeout=20000)


def test_SYNC04_a_damaged_pdf_is_reported_and_does_not_stop_the_rest(blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    folder = tmp_path / "s"
    folder.mkdir()
    (folder / "broken.pdf").write_bytes(b"%PDF-1.4 this is not a pdf")
    empty_server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 0, "members": ["A"], "sync": {"localFolder": str(folder), "auto": False}})
    blank.reload()
    go(blank, "accounts")
    blank.click('#c-sync [data-act="sync"]')
    expect(blank.locator("#c-sync")).to_contain_text("broken.pdf", timeout=20000)


# ---------------------------------------------------------------- phone to desktop, edge cases

@pytest.mark.parametrize("width,height", [(320, 640), (375, 812), (768, 1024), (1024, 768), (1440, 900), (1920, 1080)])
def test_FIT01_nothing_spills_sideways_on_any_screen_size(browser, server, width, height):
    p = open_page(browser, server, viewport={"width": width, "height": height})
    for view in ("overview", "cards", "payments", "bills", "budgets", "insights", "household", "accounts"):
        go(p, view)
        over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert over <= 0, (view, width, over)
    p.click('#period [data-id="year"]')
    for view in ("overview", "insights", "cards"):
        go(p, view)
        assert p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0, (view, width, "year")
    p.context.close()


def test_EDGE01_hostile_and_very_long_text_is_shown_as_text_and_does_not_break_the_layout(blank, empty_server):
    empty_server.call("PUT", "/api/doc/settings/main", {"household": "<img src=x onerror=window.__pwned=1>", "currency": "USD", "opening": 0, "members": ["<b>Una</b>"]})
    empty_server.call("PUT", "/api/doc/transactions/x", {"date": "2026-11-05", "desc": "<script>window.__pwned=1</script>" + "W" * 300, "amount": -5,
                                                         "category": "Dining", "who": "", "card": "<i>Card</i>"})
    blank.reload()
    go(blank, "cards")
    go(blank, "payments")
    assert blank.evaluate("window.__pwned") is None
    assert blank.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    expect(blank.locator("#title")).to_contain_text("<img src=x")


def test_EDGE02_empty_data_in_year_view_does_not_error(blank):
    errors = []
    blank.on("pageerror", lambda e: errors.append(str(e)))
    blank.click('#period [data-id="year"]')
    for view in ("overview", "cards", "payments", "bills", "budgets", "insights", "household", "accounts"):
        go(blank, view)
        expect(blank.locator("#view .card").first).to_be_visible()
    assert not errors, errors


def test_EDGE03_keyboard_search_palette_opens_filters_and_navigates(page):
    page.keyboard.press("Control+k")
    expect(page.locator("#pal")).to_be_visible()
    page.keyboard.type("budg")
    page.keyboard.press("Enter")
    expect(page.locator("#greet")).to_have_text("Budgets")
    page.keyboard.press("Control+k")
    page.keyboard.press("Escape")
    expect(page.locator("#pal")).to_be_hidden()
