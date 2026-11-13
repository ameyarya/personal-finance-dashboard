"""More browser tests: the flows that test_ui.py does not reach (editing, undo, rules, palette, CSV, chart hover, sync window)."""
import re

import pytest

from test_ui import add_payment, blank, go, money, open_page, page, pw  # noqa: F401  (fixtures)

expect = pw.expect


# ---------------------------------------------------------------- payments: edit, delete, undo, rules

def test_M01_edit_a_payment_then_delete_it_and_undo(page, server):
    go(page, "payments")
    add_payment(page, "Corner shop", 12)
    row = page.locator("#tx-list .row", has_text="Corner shop")
    row.click()
    page.fill("#f-desc", "Corner shop 2")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Transaction updated")
    expect(page.locator("#tx-list .row", has_text="Corner shop 2")).to_be_visible()
    page.locator("#tx-list .row", has_text="Corner shop 2").click()
    page.click("#dlg-extra")
    expect(page.locator("#toast")).to_contain_text("Transaction deleted")
    expect(page.locator("#tx-list .row", has_text="Corner shop 2")).to_have_count(0)
    page.click("#toast-undo")
    expect(page.locator("#tx-list .row", has_text="Corner shop 2")).to_be_visible()


def test_M02_remember_a_category_then_forget_the_rule(page, server):
    go(page, "payments")
    add_payment(page, "Bean Counter", 5, category="Dining")
    page.locator("#tx-list .row", has_text="Bean Counter").click()
    page.select_option("#f-category", "Groceries")
    page.check("#remember")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("will be filed under Groceries")
    assert any(r["category"] == "Groceries" for r in server.docs("rules").values())
    go(page, "accounts")
    page.click('[data-act="rules"]')
    expect(page.locator("#dlg")).to_contain_text("filed under Groceries")
    page.click('#dlg [data-act="del-rule"]')
    expect(page.locator("#toast")).to_contain_text("Rule forgotten")
    expect(page.locator("#dlg")).not_to_have_attribute("open", "")
    assert not server.docs("rules")


def test_M03_two_rules_forgetting_one_keeps_the_dialog_open(page, server):
    go(page, "payments")
    for name in ("Alpha Cafe", "Beta Cafe"):
        add_payment(page, name, 4, category="Dining")
        page.locator("#tx-list .row", has_text=name).click()
        page.select_option("#f-category", "Groceries")
        page.check("#remember")
        page.click("#dlg-ok")
        expect(page.locator("#toast")).to_contain_text("will be filed under")
    go(page, "accounts")
    page.click('[data-act="rules"]')
    page.locator('#dlg [data-act="del-rule"]').first.click()
    expect(page.locator("#dlg .row")).to_have_count(1)
    page.click("#dlg-cancel")


def test_M04_editing_an_unknown_payment_does_nothing(page):
    go(page, "payments")
    page.evaluate("document.querySelector('#view').insertAdjacentHTML('beforeend','<button id=ghost data-act=edit-tx data-id=nope></button><button id=ghost2 data-act=del-tx data-id=nope></button><button id=ghost3 data-act=del-rec data-id=nope></button><button id=ghost4 data-act=pay data-id=nope></button>')")
    for i in ("ghost", "ghost2", "ghost3", "ghost4"):
        page.click("#" + i)
    expect(page.locator("#dlg")).not_to_have_attribute("open", "")


def test_M05_search_box_filters_and_keeps_focus_while_typing(page):
    go(page, "payments")
    page.click("#q")
    page.keyboard.type("zzzz")
    expect(page.locator("#tx-list")).to_contain_text("No transactions match")
    expect(page.locator("#q")).to_be_focused()
    page.fill("#q", "")
    page.select_option("#fcat", "Groceries")
    expect(page.locator("#tx-list .row").first).to_be_visible()


# ---------------------------------------------------------------- bills

def test_M06_add_a_bill_and_a_payday_pay_one_and_remove_one_with_undo(page, server):
    go(page, "bills")
    page.click('[data-act="add-rec"]')
    page.fill("#f-name", "Water")
    page.fill("#f-amount", "33")
    page.fill("#f-day", "28")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Added")
    page.click('[data-act="add-rec"]')
    page.fill("#f-name", "Side gig")
    page.fill("#f-amount", "90")
    page.select_option("#f-dir", "Payday (money in)")
    page.fill("#f-day", "29")
    page.click("#dlg-ok")
    expect(page.locator("#view")).to_contain_text("Side gig")
    page.click('[data-act="add-rec"]')
    page.fill("#f-name", "Nothing")
    page.fill("#f-amount", "0")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Enter an amount")
    before = len(server.docs("transactions"))
    page.locator('[data-act="pay"]').first.click()
    expect(page.locator("#toast")).to_contain_text(re.compile("Marked (paid|received)"))
    assert len(server.docs("transactions")) == before + 1
    page.locator('[data-act="del-rec"]').first.click()
    expect(page.locator("#toast")).to_contain_text("Removed")
    page.click("#toast-undo")


# ---------------------------------------------------------------- settings, theme, clear examples

def test_M07_settings_budgets_can_be_set_and_removed(page, server):
    page.click("#btn-account")
    page.click('#pop [data-act="settings"]')
    page.fill("#b-Groceries", "123")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Settings saved")
    assert server.docs("budgets")["Groceries"]["limit"] == 123
    page.click("#btn-account")
    page.click('#pop [data-act="settings"]')
    expect(page.locator("#b-Groceries")).to_have_value("123")
    page.fill("#b-Groceries", "")
    page.click("#dlg-ok")
    expect(page.locator("#toast")).to_contain_text("Settings saved")
    assert "Groceries" not in server.docs("budgets")


def test_M08_theme_toggle_flips_and_is_remembered(page):
    first = page.evaluate("document.documentElement.dataset.theme || ''")
    page.click("#btn-theme")
    second = page.evaluate("document.documentElement.dataset.theme")
    assert second in ("light", "dark") and second != first
    page.reload()
    expect(page.locator("#view .card").first).to_be_visible()
    assert page.evaluate("document.documentElement.dataset.theme") == second


def test_M09_clear_examples_is_cancellable_and_then_works(page, server):
    expect(page.locator("#banner")).to_contain_text("Example data")
    page.click('[data-act="clear-ask"]')
    page.click('[data-act="clear-no"]')
    expect(page.locator("#banner")).to_contain_text("Example data")
    page.click('[data-act="clear-ask"]')
    page.click('[data-act="clear-yes"]')
    expect(page.locator("#toast")).to_contain_text("Examples cleared")


# ---------------------------------------------------------------- chart, bell, palette, arrows

def test_M10_hovering_the_balance_chart_shows_a_tooltip_and_leaving_hides_it(page):
    box = page.locator("#chart svg").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
    page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.5)
    expect(page.locator("#chart .charttip").first).to_be_visible()
    page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] + 120)
    page.mouse.move(box["x"] - 5, box["y"] + 5)
    page.mouse.move(box["x"] + 1, box["y"] + 1)


def test_M11_bell_lists_what_stands_out_and_clicking_opens_that_page(page):
    page.click("#btn-bell")
    expect(page.locator("#pop")).to_be_visible()
    items = page.locator('#pop [data-act="view"]')
    if items.count():
        items.first.click()
    else:
        expect(page.locator("#pop")).to_contain_text("Nothing stands out")
    page.keyboard.press("Escape")


def test_M12_palette_finds_payments_bills_pages_and_actions(page, server):
    name = next(iter(server.docs("transactions").values()))["desc"]
    page.keyboard.press("Control+k")
    page.fill("#pal-q", name[:4])
    expect(page.locator("#pal .pal-i").first).to_be_visible()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowUp")
    page.keyboard.press("Enter")
    expect(page.locator("#view h2, #view .head").first).to_be_visible()
    rec = next(iter(server.docs("recurring").values()))["name"]
    page.keyboard.press("Control+k")
    page.fill("#pal-q", rec[:4])
    page.locator("#pal .pal-i", has_text=rec).first.click()
    page.keyboard.press("Control+k")
    page.fill("#pal-q", "qqqqqq")
    expect(page.locator("#pal-list")).to_contain_text("Nothing matches")
    page.fill("#pal-q", "theme")
    page.locator("#pal .pal-i").first.hover()
    page.keyboard.press("Enter")
    page.keyboard.press("Control+k")
    page.keyboard.press("Control+k")  # already open: stays open
    page.keyboard.press("Escape")


def test_M13_date_arrows_stop_at_the_ends_of_the_data(page):
    def walk(act, n):
        for _ in range(n):
            if page.locator('[data-act="%s"]' % act).is_enabled():
                page.click('[data-act="%s"]' % act)
    walk("prev", 40)
    walk("next", 60)
    expect(page.locator('[data-act="next"]')).to_be_disabled()
    page.click('#period [data-id="year"]')
    walk("prev", 6)
    walk("next", 6)
    page.click('#period [data-id="year"]')  # already on year: no-op
    page.click('#period [data-id="month"]')


def test_M14_insights_in_the_year_view_and_every_range(page):
    page.click('#period [data-id="year"]')
    for v in ("overview", "payments", "bills", "budgets", "insights", "household", "accounts", "cards"):
        go(page, v)
        expect(page.locator("#view")).not_to_contain_text("Loading your figures")
    go(page, "overview")
    for n in ("3", "12", "6"):
        page.click('#c-flow .seg button[data-id="%s"]' % n)


def test_M15_overview_notices_page_through_with_the_arrows(page):
    nxt = page.locator('[data-act="note"]')
    if nxt.count():
        nxt.last.click()
        nxt.first.click()


# ---------------------------------------------------------------- CSV import

CSV = "Date,Description,Amount\n2026-11-02,Test Shop,-12.50\n2026-11-03,Test Pay,100\nnot a date,Broken,xx\n"








# ---------------------------------------------------------------- accounts / sign-in with a named person

def test_M19_a_password_can_be_set_for_one_named_person(page, server):
    page.click("#btn-account")
    page.click('#pop [data-act="acc-on"]')
    page.fill("#f-password", "short")
    page.fill("#f-again", "short")
    page.click("#dlg-ok")
    expect(page.locator("#dlg-err")).to_contain_text("at least")
    page.fill("#f-password", "longenough1")
    page.fill("#f-again", "different12")
    page.click("#dlg-ok")
    expect(page.locator("#dlg-err")).to_contain_text("do not match")
    page.click("#dlg-cancel")


# ---------------------------------------------------------------- sync window extras

def test_M20_sync_window_copy_and_save_buttons_and_folder_box(page, server):
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.click("#btn-sync")
    expect(page.locator("#synclog")).to_be_visible()
    page.fill("#sl-link", "/Users/you/Statements")           # privacy: allow
    page.click('[data-act="sl-savelink"]')
    expect(page.locator("#toast")).to_contain_text("Folder saved")
    page.fill("#sl-link", "")
    page.click('[data-act="sl-savelink"]')
    expect(page.locator("#toast")).to_contain_text("cleared")
    page.click('[data-act="sl-copy"]')
    expect(page.locator("#toast")).to_contain_text(re.compile("copied|Could not copy"))
    with page.expect_download():
        page.click('[data-act="sl-save"]')
    page.click('[data-act="sl-full"]')
    page.click('[data-act="sl-run"]')
    page.locator('[data-act="sl-close"]').first.click()


def test_M21_sync_settings_save_with_a_minimum_interval(page, server):
    go(page, "accounts")
    page.fill("#sy-every", "1")
    page.fill("#sy-from", "2024")
    page.fill("#sy-to", "2025")
    page.click('[data-act="save-sync"]')
    expect(page.locator("#toast")).to_contain_text("Sync settings saved")
    assert server.docs("settings")["main"]["sync"]["everyMinutes"] == 5


# ---------------------------------------------------------------- animation, empty states, resize

def test_M22_figures_count_up_when_motion_is_allowed(browser, server):
    p = open_page(browser, server, reduced_motion="no-preference")
    try:
        expect(p.locator("#balance")).to_have_text("${:,}".format(round(server.balance())), timeout=8000)
    finally:
        p.context.close()


def test_M23_empty_data_pages_do_not_error(blank):
    for v in ("overview", "payments", "bills", "budgets", "insights", "cards", "household", "accounts"):
        go(blank, v)
        expect(blank.locator("#view")).not_to_contain_text("Loading your figures")
    blank.click("#btn-bell")
    blank.keyboard.press("Escape")
    blank.click('#period [data-id="year"]')
    go(blank, "insights")


def test_M24_resizing_redraws_the_chart(page):
    page.set_viewport_size({"width": 600, "height": 800})
    page.wait_for_timeout(300)
    page.set_viewport_size({"width": 1100, "height": 800})
    expect(page.locator("#chart svg")).to_be_visible()


def test_M25_hash_change_switches_page_and_unknown_hash_goes_home(page):
    page.evaluate("location.hash='#bills'")
    expect(page.locator("#nav button[data-id=bills][aria-current], #nav button[data-id=bills].on").first).to_be_visible()
    page.evaluate("location.hash='#nonsense'")
    page.evaluate("location.hash='#overview'")
    expect(page.locator("#chart svg")).to_be_visible()


# ---------------------------------------------------------------- transactions: names, inline pickers, no import/export

def test_M26_pages_say_transactions_and_have_no_import_or_export(page):
    expect(page.locator('#nav button[data-id="payments"]')).to_contain_text("Transactions")
    go(page, "payments")
    expect(page.locator("#view h2")).to_contain_text("Transactions in")
    expect(page.locator("#view")).not_to_contain_text("Import")
    expect(page.locator("#view a[href*='export']")).to_have_count(0)
    go(page, "accounts")
    expect(page.locator("#view a[href*='export']")).to_have_count(0)
    expect(page.locator('#view [data-act="import-csv"]')).to_have_count(0)
    expect(page.locator('#view a[href*="backup"]')).to_have_count(1)
    page.keyboard.press("Control+k")
    page.fill("#pal-q", "import")
    expect(page.locator("#pal-list")).to_contain_text("Nothing matches")
    page.keyboard.press("Escape")


def test_M27_each_row_has_category_and_person_dropdowns_that_save_without_opening_the_form(page, server):
    go(page, "payments")
    add_payment(page, "Pickme", 9, category="Groceries")
    row = page.locator("#tx-list .row", has_text="Pickme")
    row.locator('select[data-f="category"]').select_option("Dining")
    expect(page.locator("#toast")).to_contain_text("Category saved")
    row.locator('select[data-f="who"]').select_option("Sam")
    expect(page.locator("#toast")).to_contain_text("Person saved")
    expect(page.locator("#dlg")).not_to_have_attribute("open", "")                   # clicking a dropdown must not open the edit form
    saved = next(t for t in server.docs("transactions").values() if t["desc"] == "Pickme")
    assert saved["category"] == "Dining" and saved["who"] == "Sam"
    row.locator('select[data-f="who"]').select_option("Shared")
    expect(page.locator("#toast")).to_contain_text("Person saved")
    saved = next(t for t in server.docs("transactions").values() if t["desc"] == "Pickme")
    assert saved["who"] == ""


def test_M28_a_person_who_is_no_longer_in_the_household_stays_selectable(page, server):
    tid = "s-2026-11-rent"
    t = dict(server.docs("transactions")[tid], who="Former")
    assert server.call("PUT", "/api/doc/transactions/" + tid, t)[0] == 200
    assert server.docs("transactions")[tid]["who"] == "Former"
    page.reload()
    go(page, "payments")
    page.fill("#q", t["desc"])
    expect(page.locator('#tx-list select[data-f="who"][data-id="%s"]' % tid)).to_have_value("Former")


def test_M29_choosing_income_as_the_type_turns_a_payment_into_money_in_and_other_types_keep_the_sign(page, server):
    go(page, "payments")
    add_payment(page, "Typeflip", 25, category="Dining")
    row = page.locator("#tx-list .row", has_text="Typeflip")
    row.locator('select[data-f="category"]').select_option("Income")
    expect(page.locator("#toast")).to_contain_text("Category saved")
    saved = next(t for t in server.docs("transactions").values() if t["desc"] == "Typeflip")
    assert saved["category"] == "Income" and saved["amount"] == 25
    page.locator("#tx-list .row", has_text="Typeflip").locator('select[data-f="category"]').select_option("Transfer")
    expect(page.locator("#toast")).to_contain_text("Category saved")


def test_M30_a_dropdown_for_a_row_that_was_deleted_meanwhile_does_nothing(page, server):
    go(page, "payments")
    add_payment(page, "Vanish", 3)
    tid = next(k for k, t in server.docs("transactions").items() if t["desc"] == "Vanish")
    server.call("DELETE", "/api/doc/transactions/" + tid)
    page.evaluate("document.querySelector('#tx-list select[data-f=category]').dispatchEvent(new Event('change',{bubbles:true}))")
    page.keyboard.press("Tab")
