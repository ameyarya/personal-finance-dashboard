"""The data check: what a statement says about itself, whether the figures add up, and which months are missing. Invented data only."""
import time

import pytest

import statements as st
from pdfs import tiny_pdf
from test_server_unit import configure, lines, srv  # noqa: F401  (fixture)
from test_ui import blank, go, pw  # noqa: F401  (fixtures)

expect = pw.expect
n = st.normalize


# ---------------------------------------------------------------- reading the statement's own figures

def test_to_iso_reads_slash_dates_two_or_four_digit_years_and_long_dates():
    assert st.to_iso("03/18/2025") == "2025-03-18" and st.to_iso("01/14/24") == "2024-01-14"
    assert st.to_iso("January 31, 2025") == "2025-01-31" and st.to_iso("Sept 5, 2025") == "2025-09-05"
    assert st.to_iso("") == "" and st.to_iso("someday") == "" and st.to_iso("Foo 3, 2025") == ""


def test_signed_treats_cr_as_a_credit_balance():
    assert st.signed("$76.58CR") == -76.58 and st.signed("CR$76.58") == -76.58 and st.signed("CR $2.74") == -2.74 and st.signed("$5.00") == 5.0


@pytest.mark.parametrize("text,expected", [
    ("Bank of America Beginning balance on December 14, 2024 $1,000.00 Ending balance on January 15, 2025 $1,496.66",
     {"start": "2024-12-14", "end": "2025-01-15", "opening": 1000.0, "closing": 1496.66}),
    ("Account Summary Previous Balance $100.00 - Payments $100.00 = New Balance $20.00 Statement Period 03/18/2025 to 04/16/2025",
     {"start": "2025-03-18", "end": "2025-04-16", "opening": 100.0, "closing": 20.0}),
    ("Previous Balance $5.00 New Balance: $6.00 OPEN TO CLOSE DATE: 12/05/2023 - 01/04/2024",
     {"start": "2023-12-05", "end": "2024-01-04", "opening": 5.0, "closing": 6.0}),
    ("Previous Balance $5.00 New Balance = $6.00 World Elite Mastercard ending in 1111 Dec 12, 2023 - Jan 11, 2024",
     {"start": "2023-12-12", "end": "2024-01-11", "opening": 5.0, "closing": 6.0}),
    ("Beginning Balance $1.00 December 28, 2023 through January 26, 2024 Ending Balance $2.00",
     {"start": "2023-12-28", "end": "2024-01-26", "opening": 1.0, "closing": 2.0}),
    ("Previous Balance $5.00 Opening/Closing Date 12/15/23 - 01/14/24 New Balance $6.00",
     {"start": "2023-12-15", "end": "2024-01-14", "opening": 5.0, "closing": 6.0}),
    ("Billing Period: 01/01/2025 to 01/31/2025 Previous Balance $1.00", {"start": "2025-01-01", "end": "2025-01-31", "opening": 1.0, "closing": None}),
    ("Statement Period: 02/01/2025 - 02/28/2025", {"start": "2025-02-01", "end": "2025-02-28", "opening": None, "closing": None}),
    ("Closing Date 01/22/24 New Balance $9.00", {"start": None, "end": "2024-01-22", "opening": None, "closing": 9.0}),
    ("January 1, 2025 Starting Balance $10.00 January 31, 2025 Ending Balance $12.00",
     {"start": None, "end": "2025-01-31", "opening": 10.0, "closing": 12.0}),
    ("Account Summary Previous Balance Payments/Credits New Charges Fees Interest Charged CR$2.99 -$1.00 +$0.00 +$0.00 +$0.00 New Balance $9.99CR Closing Date 02/01/25",
     {"start": None, "end": "2025-02-01", "opening": -2.99, "closing": -9.99}),
    ("Account Summary Previous Balance Payments/Credits New Charges Fees Interest Charged $512.21 - $519.21 + $9.00 New Balance $2.00 Minimum Payment Due $0.00",
     {"start": None, "end": None, "opening": 512.21, "closing": 2.0}),
    ("Account Summary Previous Balance Payments/Credits New Charges Fees Interest Charged $5.00 - $5.00 no closing figure here",
     {"start": None, "end": None, "opening": 5.0, "closing": None}),
    ("nothing useful", {"start": None, "end": None, "opening": None, "closing": None}),
])
def test_statement_meta_finds_the_period_and_the_balances_the_statement_prints(text, expected):
    assert st.statement_meta(n(text)) == expected


def test_read_pdf_returns_rows_and_what_the_statement_says_and_marks_payment_reports(tmp_path):
    pdf = tiny_pdf(tmp_path / "a.pdf", "Bank of America Account number: 1 Beginning balance on March 1, 2025 $0.00 Ending balance on March 31, 2025 $100.00\n"
                                       "Deposits and other additions Date Description Amount\n03/05/25 Payroll ACME 100.00\nTotal deposits and other additions $100.00")
    rows, meta = st.read_pdf(pdf)
    assert [r["amount"] for r in rows] == [100.0] and meta["kind"] == "statement" and meta["closing"] == 100.0 and meta["end"] == "2025-03-31"
    rows, meta = st.read_pdf(tiny_pdf(tmp_path / "b.pdf", "Payment History Report for a card"))
    assert rows == [] and meta["kind"] == "payments"
    assert st.read_pdf(tiny_pdf(tmp_path / "c.pdf", "nothing")) is None


# ---------------------------------------------------------------- does it add up?

def test_check_statement_compares_the_closing_balance_with_what_was_read():
    cash = [{"amount": 100.0, "cash": True}, {"amount": -30.0, "cash": True}]
    assert st.check_statement(cash, {"opening": 10.0, "closing": 80.0}) == ("ok", 0.0)
    assert st.check_statement(cash, {"opening": 10.0, "closing": 90.0}) == ("mismatch", 10.0)
    card = [{"amount": -50.0}, {"amount": 20.0}]                          # spending is negative, so it raises what is owed
    assert st.check_statement(card, {"opening": 100.0, "closing": 130.0}) == ("ok", 0.0)
    assert st.check_statement([], {"opening": 5.0, "closing": 5.0}) == ("ok", 0.0)
    assert st.check_statement(card, {"opening": None, "closing": 1.0}) == ("unverified", None)
    assert st.check_statement(card, {"opening": 1.0, "closing": None}) == ("unverified", None)


# ---------------------------------------------------------------- readers that were fixed because the check found gaps

def test_wells_fargo_reads_the_payment_row_that_has_no_card_digits_and_the_last_row_before_the_tear_off():
    text = n("WELLS FARGO ACTIVE CASH VISA Statement Period 03/18/2025 to 04/16/2025 Previous Balance $100.00 New Balance $20.00 "
             "Transactions Card Ending in Trans Date Post Date Reference Number Description Credits Charges Payments "
             "04/11 04/11 F3531003500CHGDDA AUTOMATIC PAYMENT - THANK YOU 100.00 TOTAL PAYMENTS FOR THIS PERIOD $100.00 "
             "Purchases, Balance Transfers & Other Charges 1740 03/19 03/19 24431062E4YNNZXNS CORNER MARKET CA 20.00 Detach and mail with check")
    rows = st.parse_text(text)
    assert sorted((r["amount"], r["desc"][:7]) for r in rows) == [(-20.0, "CORNER "), (100.0, "AUTOMAT")]
    assert st.check_statement(rows, st.statement_meta(text)) == ("ok", 0.0)


def test_chase_card_reads_an_amount_with_no_digit_before_the_point():
    text = n("Chase ACCOUNT SUMMARY Minimum Payment Due: $0.00 Statement Date: 11/10/24 Merchant Name or Transaction Description $ Amount "
             "10/13 CORNER SHOP WA .40 Order Number 112-1 10/20 BOOK SHOP WA 16.22 Order Number 112-2 Total fees charged in 2024 $0.00")
    assert sorted(r["amount"] for r in st.parse_chase_card(text)) == [-16.22, -0.4]


def test_chase_checking_survives_a_page_break_in_the_middle_of_the_list():
    text = n("Chase CHECKING SUMMARY TRANSACTION DETAIL April 25, 2025 through May 27, 2025 DATE DESCRIPTION AMOUNT BALANCE Beginning Balance $100.00 "
             "04/25 Acme Co Direct Dep PPD ID: 123 50.00 150.00 05/05 Some Bank EDI Pymnts 77 Web ID: 9 -20.00 130.00 2 4Page of *start*transactiondetail *end* "
             "April 25, 2025 through May 27, 2025 Account Number: 1 TRANSACTION DETAIL (continued) DATE DESCRIPTION AMOUNT BALANCE "
             "05/06 Money Network Di Deposit PPD ID: 5 30.00 160.00 Ending Balance $160.00 IN CASE OF ERRORS")
    rows = st.parse_chase_checking(text)
    assert [(r["date"], r["amount"]) for r in rows] == [("2025-04-25", 50.0), ("2025-05-05", -20.0), ("2025-05-06", 30.0)]


def test_wealthfront_reads_deposits_and_withdrawals_and_a_year_the_pdf_split_in_two():
    text = n("Wealthfront Monthly Statement II. Account Activity January 1, 2025 Starting Balance $100.00 January 31, 2025 Ending Balance $120.00 "
             "Deposits/Credits to Wealthfront Brokerage Date Method Status Amount 1/2/2025 ACH Received $50.00 1/15/2025 End of day transfer from Green Dot2 Received $5.00 "
             "Total $55.00 Date Method Status Amount 1/7/2025 End of day transfer to Green Dot Disbursed -$10.00 1/16/2025 RTP/FedNow3 Disbursed -$20.00 Total -$30.00 "
             "Date Security Symbol/CUSIP Type Shares Share Price Value 1/6/2025 -- -- Transfer out -- -- -$10.00 1/14/202 5 -- -- Transfer out -- -- -$5.00 "
             "Transfer between Wealthfront and Program Banks Date Method Amount 1/2/2025 Transfer from Program Banks $50.00 "
             "INTEREST5 Date Interest Period Amount 1/1/2025 December 2024 $10.00 Total $10.00")
    rows = st.parse_text(text)
    assert sorted(r["amount"] for r in rows) == [-20.0, -10.0, -10.0, -5.0, 5.0, 10.0, 50.0]
    assert any(r["desc"] == "Green Dot transfer in" for r in rows) and any(r["desc"] == "RTP/FedNow transfer out" for r in rows)
    assert all(r["category"] == "Transfer" for r in rows if "transfer" in r["desc"])
    assert st.check_statement(rows, st.statement_meta(text)) == ("ok", 0.0)


# ---------------------------------------------------------------- finding what is missing

def entry(end, opening=None, closing=None, state="ok", diff=0.0, label="Maple Bank", person="Person A", **more):
    return dict({"file": "s-%s.pdf" % end, "label": label, "person": person, "state": state, "diff": diff, "start": None, "end": end, "opening": opening, "closing": closing}, **more)


def months(prefix_end):
    return {"s%d" % i: entry("2025-%02d-28" % i, opening=float(i - 1), closing=float(i)) for i in range(1, prefix_end + 1)}


def kinds(report, account=0):
    return [i["kind"] for i in report["accounts"][account]["issues"]]


def test_audit_says_complete_when_every_month_is_there_and_balances_chain():
    r = st.audit(months(6), "2025-07-10")
    assert r["complete"] and r["counts"]["statements"] == 6 and r["counts"]["ok"] == 6 and r["counts"]["missing"] == 0
    a = r["accounts"][0]
    assert a["first"] == "2025-01" and a["last"] == "2025-06" and [c["mo"] for c in a["cells"]] == ["2025-0%d" % i for i in range(1, 7)]
    assert a["issues"] == [] and r["problems"] == []


def test_audit_names_the_missing_month_between_two_statements():
    e = months(6)
    del e["s3"]                                                           # no March
    r = st.audit(e, "2025-07-10")
    assert not r["complete"] and r["counts"]["missing"] == 1
    assert kinds(r) == ["missing"] and r["accounts"][0]["issues"][0]["months"] == ["2025-03"]
    assert {c["mo"]: c["state"] for c in r["accounts"][0]["cells"]}["2025-03"] == "missing"


def test_audit_names_every_month_of_a_longer_gap():
    e = months(8)
    for k in ("s3", "s4", "s5"):
        del e[k]
    r = st.audit(e, "2025-09-10")
    assert r["accounts"][0]["issues"][0]["months"] == ["2025-03", "2025-04", "2025-05"] and r["counts"]["missing"] == 3


def test_audit_does_not_mistake_a_shifting_closing_day_for_a_missing_month():
    e = {"a": entry("2025-01-31"), "b": entry("2025-03-01"), "c": entry("2025-03-31"), "d": entry("2025-04-30")}
    assert st.audit(e, "2025-05-10")["complete"] is True                 # Jan 31, Mar 1, Mar 31, Apr 30: a shifting closing day, nothing missing
    e = {"a": entry("2025-01-30"), "b": entry("2025-03-02"), "c": entry("2025-04-01")}
    assert st.audit(e, "2025-04-20")["counts"]["missing"] == 0           # 31 and 30 days: nothing is missing


def test_audit_catches_a_balance_that_does_not_carry_over_even_without_a_visible_date_gap():
    e = months(4)
    e["s3"] = entry("2025-03-28", opening=500.0, closing=3.0)             # opens at 500 but the last one closed at 2
    r = st.audit(e, "2025-05-01")
    assert kinds(r) == ["chain"] and not r["complete"] and r["counts"]["missing"] == 1


def test_audit_reports_a_statement_that_does_not_add_up():
    e = months(3)
    e["s2"] = entry("2025-02-28", opening=1.0, closing=2.0, state="mismatch", diff=-12.5)
    r = st.audit(e, "2025-03-20")
    assert kinds(r) == ["mismatch"] and "12.50" in r["accounts"][0]["issues"][0]["text"] and not r["complete"]
    assert {c["mo"]: c["state"] for c in r["accounts"][0]["cells"]}["2025-02"] == "mismatch" and r["counts"]["mismatch"] == 1


def test_audit_counts_statements_it_could_not_cross_check_but_still_calls_them_complete():
    e = months(3)
    e["s2"] = entry("2025-02-28", state="unverified", diff=None)
    r = st.audit(e, "2025-03-20")
    assert r["complete"] and r["counts"]["unverified"] == 1
    assert {c["mo"]: c["state"] for c in r["accounts"][0]["cells"]}["2025-02"] == "unverified"


def test_audit_shows_the_worse_state_when_a_month_has_two_statements():
    e = {"a": entry("2025-02-10", state="ok"), "b": entry("2025-02-20", state="mismatch", diff=1.0, closing=1.0)}
    assert st.audit(e, "2025-03-01")["accounts"][0]["cells"] == [{"mo": "2025-02", "state": "mismatch"}]
    e = {"a": entry("2025-02-10", state="unverified", diff=None), "b": entry("2025-02-20", state="ok")}
    assert st.audit(e, "2025-03-01")["accounts"][0]["cells"] == [{"mo": "2025-02", "state": "unverified"}]


def test_audit_flags_an_account_whose_newest_statement_is_old():
    r = st.audit(months(3), "2025-09-01")
    assert kinds(r) == ["stale"] and not r["complete"]
    assert st.audit(months(3), "2025-05-15")["complete"]                  # 48 days: the next one is not due yet


def test_audit_notes_an_account_that_starts_months_after_the_others_without_failing_it():
    e = dict(months(6), **{"x%d" % i: entry("2025-%02d-15" % i, label="Pine Card", opening=float(i - 1), closing=float(i)) for i in range(5, 7)})
    r = st.audit(e, "2025-07-01")
    pine = [a for a in r["accounts"] if a["name"] == "Pine Card"][0]
    assert [i["kind"] for i in pine["issues"]] == ["late"] and "2025-05" in pine["issues"][0]["text"]
    assert r["complete"]


def test_audit_reports_unreadable_files_ignored_reports_and_undated_statements():
    e = months(2)
    e["u"] = {"file": "broken.pdf", "label": "Maple Bank", "person": "Person A", "state": "unreadable", "reason": "layout not recognised"}
    e["p"] = {"file": "history.pdf", "label": "Maple Bank", "person": "Person A", "state": "ignored"}
    e["d"] = entry(None, state="unverified", diff=None)
    r = st.audit(e, "2025-03-01")
    assert r["counts"]["unreadable"] == 1 and r["counts"]["ignored"] == 1 and not r["complete"]
    assert r["problems"] == [{"kind": "unreadable", "account": "Maple Bank", "text": "broken.pdf could not be read (layout not recognised)."}]
    assert "nodate" in kinds(r)
    only = st.audit({"u": e["u"]}, "2025-03-01")
    assert only["accounts"] == [] and not only["complete"]
    assert st.audit({}, "2025-03-01") == {"complete": False, "counts": dict.fromkeys(("statements", "ok", "unverified", "mismatch", "missing", "unreadable", "ignored"), 0), "accounts": [], "problems": []}
    one = st.audit({"d": entry(None, state="ok")}, "2025-03-01")
    assert kinds(one) == ["nodate"] and one["accounts"][0]["first"] == ""


def test_audit_keeps_accounts_of_different_people_apart():
    e = {"a": entry("2025-01-28"), "b": entry("2025-03-28"), "c": entry("2025-01-28", person="Person B"), "d": entry("2025-02-28", person="Person B")}
    r = st.audit(e, "2025-04-10")
    assert [(a["person"], [i["kind"] for i in a["issues"]]) for a in r["accounts"]] == [("Person A", ["missing"]), ("Person B", [])]


# ---------------------------------------------------------------- the sync records one ledger line per statement

def bank_pdf(path, opening, closing, end_day, amount):
    return tiny_pdf(path, "Bank of America Account number: 1 Beginning balance on %s $%.2f Ending balance on %s $%.2f\n"
                          "Deposits and other additions Date Description Amount\n%s Payroll ACME %.2f\nTotal deposits and other additions $%.2f"
                          % (end_day[0], opening, end_day[1], closing, end_day[2], amount, amount))


def test_sync_records_each_statement_and_flags_one_that_does_not_add_up(srv, tmp_path):
    folder = tmp_path / "Person A" / "Maple Bank"
    folder.mkdir(parents=True)
    bank_pdf(folder / "jan.pdf", 0, 100, ("January 1, 2025", "January 31, 2025", "01/05/25"), 100)
    bank_pdf(folder / "feb.pdf", 100, 999, ("February 1, 2025", "February 28, 2025", "02/05/25"), 100)      # should close at 200
    tiny_pdf(folder / "history.pdf", "Payment History Report")
    tiny_pdf(folder / "odd.pdf", "a layout nobody has seen")
    configure(srv, localFolder=str(tmp_path / "Person A"))
    srv.run_sync()
    led = srv.STORE["sync"]["ledger"]
    by = {v["file"]: v for v in led.values()}
    assert by["jan.pdf"]["state"] == "ok" and by["jan.pdf"]["end"] == "2025-01-31" and by["jan.pdf"]["count"] == 1
    assert by["feb.pdf"]["state"] == "mismatch" and by["feb.pdf"]["diff"] == 799.0
    assert by["history.pdf"]["state"] == "ignored" and by["odd.pdf"]["state"] == "unreadable"
    assert any("does not add up" in m for m in lines(srv))
    srv.run_sync()                                                         # nothing changed: nothing is read again, the ledger stays
    assert any("unchanged, skipped" in m for m in lines(srv)) and len(srv.STORE["sync"]["ledger"]) == 4


def test_sync_reads_a_statement_again_when_it_has_no_ledger_line_yet(srv, tmp_path):
    folder = tmp_path / "x"
    folder.mkdir()
    bank_pdf(folder / "jan.pdf", 0, 100, ("January 1, 2025", "January 31, 2025", "01/05/25"), 100)
    configure(srv, localFolder=str(folder))
    srv.run_sync()
    srv.STORE["sync"]["ledger"].clear()                                    # as if the statements were read before this feature existed
    srv.run_sync()
    assert len(srv.STORE["sync"]["ledger"]) == 1 and srv.STORE["sync"]["ledger"][next(iter(srv.STORE["sync"]["ledger"]))]["state"] == "ok"


def test_sync_records_a_file_that_could_not_be_opened_and_forgets_deleted_files(srv, tmp_path):
    folder = tmp_path / "x"
    folder.mkdir()
    (folder / "damaged.pdf").write_bytes(b"not a pdf at all")
    gone = bank_pdf(folder / "gone.pdf", 0, 100, ("January 1, 2025", "January 31, 2025", "01/05/25"), 100)
    configure(srv, localFolder=str(folder))
    srv.run_sync()
    led = {v["file"]: v for v in srv.STORE["sync"]["ledger"].values()}
    assert led["damaged.pdf"]["state"] == "unreadable" and led["gone.pdf"]["state"] == "ok"
    gone.unlink()
    srv.run_sync()
    assert {v["file"] for v in srv.STORE["sync"]["ledger"].values()} == {"damaged.pdf"}


def test_a_statement_with_no_printed_period_is_placed_by_its_latest_transaction(srv, tmp_path):
    folder = tmp_path / "x"
    folder.mkdir()
    tiny_pdf(folder / "a.pdf", "Bank of America Account number: 1 Beginning balance on March 1, 2025 $0.00 Ending balance on March 31, 2025 $0.00\nno activity")
    tiny_pdf(folder / "b.pdf", "American Express Closing Date 04/21/25\n04/02/25 ACME CLINIC TOWN CA $30.00")
    configure(srv, localFolder=str(folder))
    srv.run_sync()
    led = {v["file"]: v for v in srv.STORE["sync"]["ledger"].values()}
    assert led["a.pdf"]["end"] == "2025-03-31" and led["b.pdf"]["end"] == "2025-04-21" and led["b.pdf"]["state"] == "unverified"


# ---------------------------------------------------------------- the route and the page

def sync_and_wait(server):
    server.call("POST", "/api/sync", {})
    for _ in range(200):
        j = server.call("GET", "/api/sync/log?since=0")[1]
        if not j["running"] and j.get("message"):
            return j
        time.sleep(0.1)
    raise AssertionError("sync did not finish")


def test_check_route_says_nothing_is_checked_until_a_sync_has_run(empty_server):
    status, body = empty_server.call("GET", "/api/check")
    assert status == 200 and body["checked"] is False and body["complete"] is False and body["accounts"] == []


def seed_statements(server, tmp_path, names=("sep", "oct", "nov")):
    folder = tmp_path / "Person A" / "Maple Bank"
    folder.mkdir(parents=True)
    for name in names:
        add_month(folder, name)
    server.call("PUT", "/api/doc/settings/main", {"household": "H", "currency": "USD", "opening": 0, "members": ["Person A"], "fiscalYear": 2026,
                                                  "sync": {"localFolder": str(tmp_path / "Person A"), "auto": False}})
    return folder


SPEC = {"sep": (0, 100, ("September 1, 2026", "September 30, 2026", "09/05/26")), "oct": (100, 200, ("October 1, 2026", "October 31, 2026", "10/05/26")),
        "nov": (200, 300, ("November 1, 2026", "November 30, 2026", "11/05/26"))}


def add_month(folder, name, closing=None):
    o, c, d = SPEC[name]
    return bank_pdf(folder / (name + ".pdf"), o, closing if closing is not None else c, d, 100)


def test_data_check_page_shows_a_missing_month_then_goes_green_when_it_is_filled(blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    folder = seed_statements(empty_server, tmp_path, ("sep", "nov"))        # October is missing
    blank.reload()
    go(blank, "check")
    expect(blank.locator("#c-check")).to_contain_text("Nothing has been checked yet")
    sync_and_wait(empty_server)
    expect(blank.locator("#c-check")).to_contain_text("to look at", timeout=15000)
    expect(blank.locator("#c-check")).to_contain_text("No statement for 2026-10")
    expect(blank.locator("#c-check .chk-g .cell.missing")).to_have_count(1)
    expect(blank.locator("#c-check .chk-g .cell.ok")).to_have_count(2)
    add_month(folder, "oct")
    sync_and_wait(empty_server)
    expect(blank.locator("#c-check")).to_contain_text("Every statement is here and every balance adds up", timeout=15000)
    expect(blank.locator("#c-check")).to_contain_text("Complete.")
    expect(blank.locator("#c-check .chk-g .cell.ok")).to_have_count(3)
    expect(blank.locator("#c-check .chk-g .cell.missing")).to_have_count(0)


def test_data_check_page_lists_a_statement_that_does_not_add_up_and_an_unreadable_one(blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    folder = seed_statements(empty_server, tmp_path, ("sep",))
    add_month(folder, "oct", closing=250)                                  # closes at 250, not 200
    tiny_pdf(folder / "odd.pdf", "a layout nobody has seen")
    blank.reload()
    sync_and_wait(empty_server)
    go(blank, "check")
    expect(blank.locator("#c-check")).to_contain_text("Not complete yet", timeout=15000)
    expect(blank.locator("#c-check")).to_contain_text("a $50.00 difference")
    expect(blank.locator("#c-check")).to_contain_text("odd.pdf could not be read")
    expect(blank.locator("#c-check .chk-g .cell.mismatch")).to_have_count(1)
    expect(blank.locator("#c-check .chk-tiles")).to_contain_text("Unreadable")


def test_overview_points_to_the_data_check_when_statements_are_not_complete(blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    seed_statements(empty_server, tmp_path, ("sep", "nov"))
    sync_and_wait(empty_server)
    blank.reload()
    go(blank, "overview")
    for _ in range(8):
        if "Your statements are not complete" in blank.locator("#c-noticed").inner_text():
            break
        blank.click('#c-noticed [data-act="note"][data-id="1"]')
    expect(blank.locator("#c-noticed")).to_contain_text("Your statements are not complete")
    blank.click('#c-noticed [data-act="view"]')
    expect(blank.locator("#greet")).to_have_text("Data check")


def test_data_check_page_notes_an_account_that_starts_late_and_statements_it_could_not_cross_check(blank, empty_server, tmp_path):
    pytest.importorskip("pypdf")
    seed_statements(empty_server, tmp_path, ("sep", "oct", "nov"))
    late = tmp_path / "Person A" / "Pine Card"
    late.mkdir()
    tiny_pdf(late / "a.pdf", "American Express Closing Date 11/21/26\n11/02/26 ACME CLINIC TOWN CA $30.00")
    blank.reload()
    sync_and_wait(empty_server)
    go(blank, "check")
    expect(blank.locator("#c-check .chk-n")).to_have_count(1, timeout=15000)
    expect(blank.locator("#c-check .chk-g .cell.unverified")).to_have_count(1)


def test_amex_credit_balance_refund_is_a_row_even_though_its_text_says_balance():
    text = n("American Express Closing Date 01/22/25 Account Summary Previous Balance Payments/Credits New Charges Fees Interest Charged CR$2.47 -$0.00 +$2.47 +$0.00 +$0.00 "
             "New Charges Summary Detail 01/22/25* Credit Balance Refund $2.47 Fees Amount Total Fees for this Period $0.00 New Balance $0.00")
    rows = st.parse_text(text)
    assert [(r["desc"], r["amount"]) for r in rows] == [("Credit Balance Refund", -2.47)]
    assert st.check_statement(rows, st.statement_meta(text)) == ("ok", 0.0)


def test_audit_treats_two_spellings_of_a_folder_name_as_one_account():
    e = {"a": entry("2024-12-11", label="Capital One"), "b": entry("2025-01-11", label="CapitalOne")}
    r = st.audit(e, "2025-02-01")
    assert len(r["accounts"]) == 1 and r["accounts"][0]["name"] in ("Capital One", "CapitalOne") and r["complete"]


def test_audit_lets_a_long_export_cover_every_month_it_spans():
    e = {"a": entry("2024-12-04"), "x": entry("2025-12-23", start="2025-01-02", state="unverified", diff=None)}
    r = st.audit(e, "2026-01-05")
    cells = {c["mo"]: c["state"] for c in r["accounts"][0]["cells"]}
    assert r["counts"]["missing"] == 0 and cells["2025-06"] == "unverified" and cells["2025-12"] == "unverified" and cells["2024-12"] == "ok"
    assert r["complete"]
