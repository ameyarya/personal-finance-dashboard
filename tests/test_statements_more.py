"""Every branch of the statement readers, on invented text, plus the small helpers around them."""
import datetime as dt
import sys

import pytest

import statements as st
from pdfs import tiny_pdf

n = st.normalize


def test_normalize_collapses_space_and_removes_markdown_leftovers():
    assert n("a \\* b c\n\n d − 5") == "a * b c d - 5"
    assert st.money("$1,234.50") == 1234.5 and st.money("-7.00") == -7.0


def test_with_year_puts_a_december_row_on_a_january_statement_in_the_year_before():
    end = dt.date(2025, 1, 15)
    assert st.with_year(12, 28, end) == "2024-12-28" and st.with_year(1, 3, end) == "2025-01-03" and st.with_year(1, 15, end) == "2025-01-15"


def test_row_cleans_the_description_and_only_marks_cash_when_asked():
    assert st.row("2025-01-01", "  - Corner Cafe  ", -4.5, "V") == {"date": "2025-01-01", "desc": "Corner Cafe", "amount": -4.5, "card": "V"}
    assert st.row("2025-01-01", "Pay", 1, "B", cash=True)["cash"] is True


def test_extract_text_explains_a_missing_pypdf_and_reads_a_real_pdf(tmp_path, monkeypatch):
    pdf = tiny_pdf(tmp_path / "a.pdf", "hello\nworld (with brackets) \\ backslash")
    assert "hello world (with brackets)" in st.extract_text(pdf)
    monkeypatch.setitem(sys.modules, "pypdf", None)
    with pytest.raises(RuntimeError, match="needs pypdf"):
        st.extract_text(pdf)


def test_parse_pdf_goes_from_file_to_rows(tmp_path):
    pdf = tiny_pdf(tmp_path / "w.pdf", "American Express Closing Date 04/21/25\n04/02/25 ACME CLINIC TOWN CA $30.00")
    assert [(r["desc"], r["amount"], r["card"]) for r in st.parse_pdf(pdf)] == [("ACME CLINIC TOWN CA", -30.0, "Amex")]
    assert st.parse_pdf(tiny_pdf(tmp_path / "x.pdf", "nothing")) is None


# ---------------------------------------------------------------- Wells Fargo card

WF = ("WELLS FARGO ACTIVE CASH VISA Account ending in 0000 Statement Period 01/05/2025 to 01/17/2025 Payments 0000 01/06 01/06 11111AAAAA PAYMENT THANK YOU 200.00 TOTAL PAYMENTS $200.00 "
      "Other Credits 0000 01/08 01/08 22222BBBBB ACME REFUND 13.20 TOTAL OTHER CREDITS $13.20 Purchases, Balance Transfers & Other Charges "
      "0000 01/05 01/05 33333CCCCC CORNER GROCER 42.68 0000 12/30 12/30 44444DDDDD LATE BUY LAST YEAR 7.00 TOTAL PURCHASES $49.68 Fees Charged "
      "0000 01/17 01/17 55555EEEEE ANNUAL FEE 25.00 TOTAL FEES CHARGED FOR THIS PERIOD $25.00")


def test_wells_fargo_sections_decide_the_sign_and_the_year():
    rows = {r["desc"]: r for r in st.parse_text(n(WF))}
    assert rows["PAYMENT THANK YOU"]["amount"] == 200.0 and rows["PAYMENT THANK YOU"]["category"] == "Transfer"
    assert rows["ACME REFUND"]["amount"] == 13.2
    assert rows["CORNER GROCER"]["amount"] == -42.68 and rows["CORNER GROCER"]["date"] == "2025-01-05"
    assert rows["LATE BUY LAST YEAR"]["date"] == "2024-12-30"                       # December on a January statement
    assert rows["ANNUAL FEE"]["amount"] == -25.0                                      # fees are charges, not credits


def test_wells_fargo_needs_its_name_and_a_statement_period():
    assert st.parse_wells_fargo(n("Statement Period 01/05/2025 to 01/17/2025 but not the bank")) is None
    assert st.parse_wells_fargo(n("WELLS FARGO no period here")) is None
    assert st.parse_wells_fargo(n("WELLS FARGO Statement Period 01/05/2025 to 01/17/2025 and no transactions")) == []


# ---------------------------------------------------------------- Bank of America

BOFA = ("Bank of America Account number: 1 Account summary Beginning balance on June 1, 2025 $10.00 Ending balance on June 30, 2025 $5.00 "
        "Withdrawals and other subtractions Date Description Amount 06/03/25 CHECKCARD PURCHASE ACME -12.00 Total withdrawals and other subtractions -$12.00 "
        "Deposits and other additions Date Description Amount 06/20/25 Zelle payment from A FRIEND 7.00 Total deposits and other additions $7.00")


def test_bank_of_america_reads_both_sections_in_any_order_and_marks_rows_as_cash():
    rows = st.parse_text(n(BOFA))
    assert sorted((r["date"], r["amount"]) for r in rows) == [("2025-06-03", -12.0), ("2025-06-20", 7.0)]
    assert all(r["cash"] and r["card"] == "Bank of America" for r in rows)


def test_bank_of_america_edge_cases():
    quiet = "Bank of America Account summary Beginning balance on June 1, 2025 $0.00 Ending balance on June 30, 2025 $0.00 nothing happened"
    assert st.parse_text(n(quiet)) == []                                              # a statement with no activity is not an error
    assert st.parse_bofa(n("Bank of America card payment from Bank of America, NA")) is None     # a card statement that mentions the bank
    assert st.parse_bofa(n("some other bank Beginning balance on x Ending balance on y")) is None
    only_header = n("Bank of America Beginning balance on June 1, 2025 $0 Ending balance on June 30, 2025 $0 Deposits and other additions Date Description Amount "
                    "Date Description Amount 06/20/25 Interest 1.00")
    assert [r["desc"] for r in st.parse_bofa(only_header)] == ["Interest"]


# ---------------------------------------------------------------- Wealthfront

WEALTH = ("Wealthfront Monthly Statement II. Account Activity INTEREST6 Date Interest Period Amount 12/1/2025 November 2025 $343.93 Total $343.93 "
          "TRANSFERS Date Security Symbol/CUSIP Type Shares Share Price Value 12/1/2025 -- -- Transfer out -- -- -$2,000.00 "
          "1/8/25 -- -- Transfer out -- -- -$50.00 Total -$2,050.00")


def test_wealthfront_reads_interest_and_investing_and_ignores_short_years():
    rows = {r["desc"]: r for r in st.parse_text(n(WEALTH))}
    assert rows["November interest"]["amount"] == 343.93 and rows["November interest"]["category"] == "Income"
    assert rows["Personal Investment"]["amount"] == -2000.0 and rows["Personal Investment"]["category"] == "Savings"
    assert len([r for r in st.parse_text(n(WEALTH)) if r["desc"] == "Personal Investment"]) == 1        # the two-digit-year row is not guessed at


def test_wealthfront_without_interest_and_not_wealthfront():
    text = n("Wealthfront Account Activity nothing else")
    assert st.parse_wealthfront(text) == []
    assert st.parse_wealthfront(n("a different company Account Activity")) is None
    assert st.parse_wealthfront(n("Wealthfront without the activity section")) is None


# ---------------------------------------------------------------- Capital One

C1_YEAR = ("Year-End Summary 2025 Capital One Transaction Details Dining Date Merchant Name Merchant Location Card Ending in 1111 "
           "01/05 NOODLE BAR Springfield CA $12.50 02/03 SPICY PLACE SAN JOSE CA $20.00 03/04 REFUND SHOP Town CA -$5.00 TOTAL DINING $27.50")


def test_capital_one_year_end_summary_strips_the_location_and_signs_the_amounts():
    rows = st.parse_text(n(C1_YEAR))
    by = {r["desc"]: r["amount"] for r in rows}
    assert by["NOODLE BAR"] == -12.5                                                   # "Springfield CA" is stripped
    assert by["SPICY PLACE SAN JOSE CA"] == -20.0                                      # an all-capitals location is left as it was written
    assert by["REFUND SHOP"] == 5.0                                                    # a credit comes back positive
    assert all(r["date"].startswith("2025-") and r["card"] == "Capital One" for r in rows)


@pytest.mark.parametrize("text", ["Year-End Summary 2025 and Transaction Details but another bank", "Capital One Transaction Details with no summary heading",
                                  "Year-End Summary 2025 Capital One without the details section"])
def test_capital_one_year_end_needs_all_of_its_markers(text):
    assert st.parse_capital_one_year_end(n(text)) is None


C1_MONTH = ("Capital One Account Summary Available Credit (as of Jan 11, 2025) $9,000.00 PERSON A #1111: Payments, Credits and Adjustments Trans Date Post Date Description Amount "
            "Jan 2 Jan 3 ONLINE PAYMENT -$40.00 PERSON A #1111: Transactions Trans Date Post Date Description Amount Dec 28 Dec 29 NOODLE BARTownCA $12.00 "
            "Jan 4 Jan 5 BOWLING ALLEYTownCA $8.50 PERSON A #1111: Total Transactions $20.50 Fees Trans Date Post Date Description Amount Total Fees $0.00")


def test_capital_one_monthly_puts_december_rows_in_the_year_before_and_credits_positive():
    rows = {r["desc"]: r for r in st.parse_text(n(C1_MONTH))}
    assert rows["NOODLE BARTownCA"]["date"] == "2024-12-28" and rows["NOODLE BARTownCA"]["amount"] == -12.0
    assert rows["ONLINE PAYMENT"]["amount"] == 40.0 and rows["ONLINE PAYMENT"]["category"] == "Transfer"
    assert rows["BOWLING ALLEYTownCA"]["date"] == "2025-01-04"


def test_capital_one_monthly_edge_cases():
    assert st.parse_capital_one_monthly(n("not a card statement")) is None
    assert st.parse_capital_one_monthly(n("Capital One Post Date Description Amount but no closing date")) is None
    assert st.parse_capital_one_monthly(n("Capital One Post Date Description Amount Available Credit (as of Jan 11, 2025) $1 and no transactions heading")) == []
    no_credits = ("Capital One Post Date Description Amount (as of Mar 11, 2025) PERSON A #1: Transactions Trans Date Post Date Description Amount Mar 2 Mar 4 SHOPTownCA $3.00")
    assert [(r["desc"], r["amount"]) for r in st.parse_text(n(no_credits))] == [("SHOPTownCA", -3.0)]       # no payments section, no fees section


# ---------------------------------------------------------------- Amex and the general reader

def test_amex_filters_and_unknown_text():
    assert st.parse_amex(n("some other company 04/02/25 THING $5.00")) is None
    text = n("American Express 04/02/25 ACME CLINIC $30.00 04/03/25 Minimum payment due $25.00 04/04/25 ZZ $5.00 04/05/25 (note) $9.00 04/06/25 FREE ITEM $0.00 "
             "04/07/25 BALANCE FORWARD $3.00 04/08/25 REAL SHOP $7.50")
    assert [(r["desc"], r["amount"]) for r in st.parse_amex(text)] == [("ACME CLINIC", -30.0), ("REAL SHOP", -7.5)]


def test_generic_reader_dates_issuer_names_and_filters():
    text = n("Discover it Statement Period 01/10/2025 to 02/09/2025 01/12 01/13 CORNER CAFE $4.00 12/30 01/02 OLD SHOP $5.00 02/01/2025 EXPLICIT YEAR 6.00 "
             "01/20 ZZ $2.00 01/21 Total new balance $99.00 13/40 BAD DATE $1.00 01/22 FREE $0.00 02/02/25 TWO DIGIT YEAR 7.00")
    rows = st.parse_text(text, hint="Statements")
    by = {r["desc"]: r for r in rows}
    assert by["CORNER CAFE"]["date"] == "2025-01-12" and by["OLD SHOP"]["date"] == "2024-12-30" and by["EXPLICIT YEAR"]["date"] == "2025-02-01"
    assert by["TWO DIGIT YEAR"]["date"] == "2025-02-02"
    assert not {"ZZ", "Total new balance", "BAD DATE", "FREE"} & set(by)
    assert all(r["card"] == "Discover" for r in rows)


def test_generic_reader_without_a_closing_date_skips_rows_that_have_no_year():
    text = n("Some Card 01/12 CORNER CAFE $4.00 02/03/2025 DATED SHOP $9.00")
    assert [r["desc"] for r in st.parse_text(text, hint="Mine")] == ["DATED SHOP"]
    assert st.parse_text(n("Some Card 01/12 CORNER CAFE $4.00"), hint="Mine") is None
    assert st.parse_text(n("no rows at all"), hint="Mine") is None
    assert st.parse_generic_card(n("Billing Date 03/09/2025 03/01 SHOP ONE $1.00"), "")[0]["card"] == "Card"      # no hint and no issuer name


@pytest.mark.parametrize("name,issuer", [("Capital One", "Capital One"), ("American Express", "Amex"), ("Amex", "Amex"), ("Discover", "Discover"), ("Chase", "Chase"),
                                         ("Citi", "Citi"), ("Apple Card", "Apple Card")])
def test_issuer_names_come_from_the_statement(name, issuer):
    rows = st.parse_generic_card(n(name + " Closing Date 03/09/2025 03/01 SHOP $1.00"), "")
    assert rows[0]["card"] == issuer


# ---------------------------------------------------------------- finishing touches

def test_finish_files_payments_transfers_interest_and_investments():
    rows = st.finish([
        {"date": "d", "desc": "AUTOPAY PAYMENT - THANK YOU", "amount": -50.0, "card": "V"},
        {"date": "d", "desc": "Transfer to savings", "amount": -5.0, "card": "Bank", "cash": True},
        {"date": "d", "desc": "Personal Investment", "amount": -9.0, "card": "Bank", "cash": True},
        {"date": "d", "desc": "May interest", "amount": 3.0, "card": "Bank", "cash": True},
        {"date": "d", "desc": "Payroll ACME", "amount": 3.0, "card": "Bank", "cash": True},
        {"date": "d", "desc": "Interest charge", "amount": -2.0, "card": "Bank", "cash": True}])
    assert [(r.get("category"), r["amount"]) for r in rows] == [("Transfer", 50.0), ("Transfer", -5.0), ("Savings", -9.0), ("Income", 3.0), (None, 3.0), (None, -2.0)]


def test_parse_text_tries_each_reader_in_turn():
    assert st.parse_text("") is None
    assert st.parse_text(n(BOFA))[0]["card"] == "Bank of America"
    assert st.parse_text(n(WF))[0]["card"] == "Wells Fargo"


def test_a_stray_column_heading_in_front_of_a_bank_row_is_not_taken_as_a_payment():
    text = n("Bank of America Beginning balance on June 1, 2025 $0 Ending balance on June 30, 2025 $0 Deposits and other additions Date Description Amount "
             "06/01/25 Date Description Amount 06/02/25 Interest 1.00 06/03/25 Real deposit 2.00")
    assert [r["desc"] for r in st.parse_text(text)] == ["Real deposit"]
