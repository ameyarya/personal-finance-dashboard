"""Statement parsers, on text shaped like real statements but with invented merchants and amounts."""
import statements as st

WF = ("WELLS FARGO ACTIVE CASH VISA SIGNATURE CARD Account ending in 0000 Statement Period 01/05/2025 to 01/17/2025 "
      "Transactions Card Ending in Trans Date Post Date Reference Number Description Credits Charges Other Credits "
      "0000 01/08 01/08 74240980801QHB71K ACME CAMPSITE BOOKING NM 113.20 TOTAL OTHER CREDITS FOR THIS PERIOD $113.20 "
      "Purchases, Balance Transfers & Other Charges "
      "0000 01/05 01/05 2476501065Y6LXNYR CORNER GROCER SPRINGFIELD CA 42.68 0000 01/07 01/07 24240980700W728FP ACME CAMPSITE BOOKING NM 123.20 "
      "0000 01/14 01/14 24455010E447YNZMS HARDWARE WORLD #12 SPRINGFIELD CA 1,019.60 TOTAL PURCHASES, BALANCE TRANSFERS & OTHER CHARGES FOR THIS PERIOD $1,185.48 Fees Charged")

BOFA = ("Bank of America Your Adv Plus Banking for November 13, 2025 to December 15, 2025 Account number: 0000 0000 0000 "
        "Deposits and other additions Date Description Amount "
        "11/24/25 Transfer WEALTHFRONT BROKERAGE LLC 5,000.00 12/08/25 Zelle payment from A FRIEND Conf# kemq9pkxc 10.00 "
        "Total deposits and other additions $5,010.00 Withdrawals and other subtractions Date Description Amount "
        "11/26/25 Wealthfront DES:EDI PYMNTS ID:X INDN:A PERSON CO ID:1 WEB -4,999.00 Total withdrawals and other subtractions -$4,999.00")

WEALTH = ("Wealthfront Monthly Statement II. Account Activity INTEREST6 Date Interest Period Amount 12/1/2025 November 2025 $343.93 Total $343.93 "
          "TRANSFERS Date Security Symbol/CUSIP Type Shares Share Price Value 12/1/2025 -- -- Transfer out -- -- -$2,000.00 Total -$2,000.00")

CARD = ("Statement Closing Date 03/12/2025 Transactions 02/20 02/21 SPRINGFIELD BAKERY 12.50 02/22 02/23 AUTOPAY PAYMENT - THANK YOU -100.00 "
        "03/01 03/02 STREAMING SERVICE 9.99 Total Purchases 22.49")


def by_desc(rows):
    return {r["desc"]: r for r in rows}


def test_wells_fargo_card_charges_are_negative_and_credits_positive():
    rows = by_desc(st.parse_text(st.normalize(WF)))
    assert rows["ACME CAMPSITE BOOKING NM"]["amount"] in (113.2, -123.2)
    amounts = sorted(r["amount"] for r in st.parse_text(st.normalize(WF)))
    assert amounts == [-1019.6, -123.2, -42.68, 113.2]
    assert all(r["card"] == "Wells Fargo" and r["date"].startswith("2025-01") for r in st.parse_text(st.normalize(WF)))


def test_bank_of_america_rows_are_cash_and_keep_their_signs():
    rows = st.parse_text(st.normalize(BOFA))
    assert [(r["date"], r["amount"]) for r in rows] == [("2025-11-24", 5000.0), ("2025-12-08", 10.0), ("2025-11-26", -4999.0)]
    assert all(r["cash"] and r["card"] == "Bank of America" for r in rows)
    assert rows[0]["category"] == "Transfer" and rows[2]["category"] == "Transfer"


def test_wealthfront_interest_is_income_and_investing_is_savings():
    rows = by_desc(st.parse_text(st.normalize(WEALTH)))
    assert rows["November interest"]["category"] == "Income" and rows["November interest"]["amount"] == 343.93
    assert rows["Personal Investment"]["category"] == "Savings" and rows["Personal Investment"]["amount"] == -2000.0


def test_generic_card_statement_uses_the_closing_date_for_the_year_and_files_payments_as_transfers():
    rows = st.parse_text(st.normalize(CARD), hint="Amex")
    got = {r["desc"]: r for r in rows}
    assert got["SPRINGFIELD BAKERY"]["date"] == "2025-02-20" and got["SPRINGFIELD BAKERY"]["amount"] == -12.5
    assert got["STREAMING SERVICE"]["date"] == "2025-03-01"
    pay = [r for r in rows if r.get("category") == "Transfer"]
    assert len(pay) == 1 and pay[0]["amount"] == 100.0


def test_unrecognised_text_returns_none_not_a_crash():
    assert st.parse_text("nothing that looks like a statement") is None
    assert st.parse_text("") is None


def test_a_real_pdf_goes_through_text_extraction(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("pypdf")
    pw = pytest.importorskip("playwright.sync_api")
    pdf = tmp_path / "bofa.pdf"
    html = "<body style='font:12px sans-serif'>" + BOFA.replace("Deposits and other", "<br>Deposits and other").replace(" 11/26/25", "<br>11/26/25") + "</body>"
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.set_content(html)
        page.pdf(path=str(pdf))
        b.close()
    rows = st.parse_pdf(pdf)
    assert rows and sorted(r["amount"] for r in rows) == [-4999.0, 10.0, 5000.0]
