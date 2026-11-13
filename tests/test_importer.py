"""tools/import_statements.py: the year loader. Invented merchants, invented amounts."""
import json
import subprocess
import sys

import pytest

from conftest import ROOT
from tools import import_statements as imp


@pytest.fixture(autouse=True)
def clean_rules(monkeypatch):
    """Each test starts from the built-in rules, whatever an earlier test loaded."""
    for name in ("RULES", "SHOPPING", "CARD_PAYMENT", "CASH_TRANSFER", "INCOME", "CASH_RULES", "WHO"):
        monkeypatch.setattr(imp, name, getattr(imp, name))


CARDS = ("2025-01-05|CORNER GROCER|42.50|Groceries|Visa\n2025-01-06|CORNER GROCER|42.50|Groceries|Visa\n"
         "2025-01-07|AUTOPAY PAYMENT - THANK YOU|-100.00||Visa\n2025-01-08|HOTEL SPRINGFIELD|-80.00|Travel|Visa\n"
         "2025-01-09|MYSTERY SHOP|9.99|Uncategorized|Visa\n2025-01-10|WALMART SUPERCENTER|20.00|Shopping|Visa\n"
         "2025-01-11|BAKERY \\* TOWN|5.00|Dining|Visa\n2024-12-31|LAST YEAR|1.00|Dining|Visa\n\n"
         "2025-01-12|COFFEE SHOP|3.00|Food/Drink|Visa\n2025-01-13|GAS COMPANY|60.00||Visa\n")

CASH = ("1/2/2025|Payroll ACME|Deposit|1000.00\n1/3/2025|Interest Payment|Interest|2.50\n1/4/2025|Transfer to savings|Transfer|-200.00\n"
        "1/5/2025|Personal Investment|Transfer|-300.00\n1/6/2025|Venmo-Payment-1234567|Withdrawal|-5000.00\n1/7/2025|Venmo-Payment-9999999|Withdrawal|-20.00\n"
        "1/8/2025|Friend paid back|Deposit|15.00\n1/9/2025|Some Bill-1234567890123|Withdrawal|-33.00\n12/31/2024|Old|Deposit|1.00\n1/10/2025|Tax Refund|Deposit|400.00\n"
        "1/11/2025|Landlord rent|Withdrawal|-900.00\n")


@pytest.fixture
def files(tmp_path):
    (tmp_path / "cards.psv").write_text(CARDS)
    (tmp_path / "cash.psv").write_text(CASH)
    (tmp_path / "bank.psv").write_text("2/1/2025|Payroll ACME|Deposit|10.00\n")
    return tmp_path


def test_card_rows_sign_category_refund_duplicates_and_year(files):
    rows = list(imp.card_rows(str(files / "cards.psv"), 2025))
    by = [(r["desc"], r["amount"], r["category"], r.get("refund", False)) for r in rows]
    assert ("CORNER GROCER", -42.5, "Groceries", False) in by and by.count(("CORNER GROCER", -42.5, "Groceries", False)) == 2     # two identical rows stay two
    assert len({r["id"] for r in rows}) == len(rows)                                                                                 # with different ids
    assert ("Card payment", 100.0, "Transfer", False) in by                                                                          # a payment is a transfer
    assert ("HOTEL SPRINGFIELD", 80.0, "Travel", True) in by                                                                         # a credit is a refund
    assert any(r["desc"] == "MYSTERY SHOP" and r["category"] == "Other" for r in rows)
    assert any(r["desc"] == "WALMART SUPERCENTER" and r["category"] == "Shopping" for r in rows)
    assert any(r["desc"] == "BAKERY * TOWN" for r in rows)                                                                            # markdown backslashes are removed
    assert not any(r["desc"] == "LAST YEAR" for r in rows) and all(r["source"] == "statement" and r["who"] == "" for r in rows)
    assert any(r["desc"] == "COFFEE SHOP" and r["category"] == "Dining" for r in rows)                                              # the bank's own label maps over
    assert any(r["desc"] == "GAS COMPANY" and r["category"] == "Utilities" for r in rows)


def test_cash_rows_cover_every_kind_of_movement(files):
    rows = {r["desc"]: r for r in imp.cash_rows(str(files / "cash.psv"), 2025, "Checking")}
    assert rows["Payroll ACME"]["category"] == "Income" and rows["Interest Payment"]["category"] == "Income" and rows["Tax Refund"]["category"] == "Income"
    assert rows["Transfer to savings"]["category"] == "Transfer"
    assert rows["Personal Investment"]["category"] == "Savings"
    assert rows["Venmo-Payment-1234567"]["category"] == "Transfer"                                         # a big Venmo move is between your own accounts
    assert rows["Venmo-Payment"]["category"] == "Other" and rows["Venmo-Payment"]["amount"] == -20.0     # a small one is spending; the id number is trimmed off
    assert rows["Friend paid back"]["refund"] is True and rows["Friend paid back"]["category"] == "Other"  # money coming back reduces spending
    assert rows["Some Bill"]["category"] == "Other"
    assert "Old" not in rows and all(r["cash"] is True and r["card"] == "Checking" for r in rows.values())
    assert rows["Landlord rent"]["category"] == "Other"                                                    # no rule knows about a landlord yet


def test_your_own_rules_come_first(files, tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"rules": [["CORNER GROCER", "Dining"]], "shopping": "MYSTERY", "card_payment": "NEVER MATCHES", "cash_transfer": "ZZZ", "income": "LANDLORD",
                                 "cash_rules": [["RENT", "Housing", "Rent"]], "who": {"A personal": "A"}}))
    imp.load_rules(str(rules))
    cards = {r["desc"]: r for r in imp.card_rows(str(files / "cards.psv"), 2025)}
    assert cards["CORNER GROCER"]["category"] == "Dining" and cards["MYSTERY SHOP"]["category"] == "Shopping"
    assert "AUTOPAY PAYMENT - THANK YOU" in cards                                                         # no longer recognised as a card payment
    cash = {r["desc"]: r for r in imp.cash_rows(str(files / "cash.psv"), 2025, "Checking")}
    assert cash["Landlord rent"]["category"] == "Income"                                                  # the income rule is checked before the cash rules
    assert cash["Transfer to savings"]["category"] == "Other"                                              # the transfer rule was replaced


def test_a_cash_rule_with_a_description_renames_the_row(files, tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"cash_rules": [["RENT", "Housing", "Rent"], ["BILL", "Utilities", None]]}))
    imp.load_rules(str(rules))
    cash = {r["desc"]: r for r in imp.cash_rows(str(files / "cash.psv"), 2025, "C")}
    assert cash["Rent"]["category"] == "Housing" and cash["Rent"]["amount"] == -900.0
    assert cash["Some Bill-1234567890123"]["category"] == "Utilities" and cash["Some Bill-1234567890123"]["desc"] == "Some Bill-1234567890123"


def test_enrich_copies_who_and_notes_from_an_earlier_reconciliation(files, tmp_path):
    imp.WHO.update({"Person A personal": "Person A"})
    rows = list(imp.card_rows(str(files / "cards.psv"), 2025)) + list(imp.cash_rows(str(files / "cash.psv"), 2025, "Checking"))
    known = {"transactions": [{"date": "2025-01-05", "description": "corner  grocer", "amount": 42.5, "source": "Visa", "ownership": "Person A personal", "special": "K", "note": "gift"},
                              {"date": "2025-01-09", "description": "MYSTERY SHOP", "amount": 9.99, "source": "Visa", "ownership": "Shared", "special": "", "note": ""},
                              {"date": "2030-01-01", "description": "NOT IN THE DATA", "amount": 1, "source": "Visa"}]}
    path = tmp_path / "project.json"
    path.write_text(json.dumps(known))
    assert imp.enrich(rows, str(path)) == 2
    first = next(r for r in rows if r["desc"] == "CORNER GROCER" and r["date"] == "2025-01-05")
    assert first["who"] == "Person A" and first["note"] == "K; gift"
    mystery = next(r for r in rows if r["desc"] == "MYSTERY SHOP")
    assert mystery["who"] == "" and "note" not in mystery
    assert all("note" not in r for r in rows if r.get("cash"))                                           # bank rows are never touched


def test_main_dry_run_prints_a_summary_and_changes_nothing(files, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", "--cards", str(files / "cards.psv"), "--cash", str(files / "cash.psv"), "--extra-cash", "%s=Savings" % (files / "bank.psv"),
                                      "--extra-cash", str(files / "bank.psv"), "--opening", "1000", "--dry", "--year", "2025"])
    imp.main()
    out = capsys.readouterr().out
    assert "cash accounts: opening 1000.00 + movement" in out and "rows | income" in out and "Groceries" in out


def test_main_replaces_the_data_through_a_running_server(files, empty_server, monkeypatch, capsys):
    empty_server.call("PUT", "/api/doc/budgets/old", {"limit": 1})
    empty_server.call("PUT", "/api/doc/transactions/old", {"date": "2020-01-01", "desc": "leftover", "amount": -1})
    rules = files / "rules.json"
    rules.write_text(json.dumps({"who": {"Person A personal": "Person A"}}))
    known = files / "known.json"
    known.write_text(json.dumps({"transactions": [{"date": "2025-01-09", "description": "MYSTERY SHOP", "amount": 9.99, "source": "Visa", "ownership": "Person A personal"}]}))
    monkeypatch.setattr(sys, "argv", ["x", "--cards", str(files / "cards.psv"), "--cash", str(files / "cash.psv"), "--cash-name", "Checking", "--opening", "250.5",
                                      "--server", empty_server.url, "--rules", str(rules), "--enrich", str(known), "--members", "A, B"])
    imp.main()
    assert "loaded" in capsys.readouterr().out
    c = empty_server.data()["collections"]
    assert "old" not in c["transactions"] and "old" not in c["budgets"]
    expected = len(list(imp.card_rows(str(files / "cards.psv"), 2025))) + len(list(imp.cash_rows(str(files / "cash.psv"), 2025, "Checking")))
    assert len(c["transactions"]) == expected
    assert c["settings"]["main"]["opening"] == 250.5 and c["settings"]["main"]["members"] == ["A", "B"] and c["settings"]["main"]["fiscalYear"] == 2025
    assert any(t.get("who") == "Person A" for t in c["transactions"].values())


def test_main_sends_big_loads_in_batches(files, empty_server, monkeypatch):
    big = "\n".join("2025-01-05|SHOP %d|1.00|Shopping|Visa" % i for i in range(4300))
    (files / "cards.psv").write_text(big)
    monkeypatch.setattr(sys, "argv", ["x", "--cards", str(files / "cards.psv"), "--cash", str(files / "cash.psv"), "--server", empty_server.url])
    imp.main()
    assert len(empty_server.docs("transactions")) == 4300 + len(list(imp.cash_rows(str(files / "cash.psv"), 2025, "Cash account")))


def test_the_script_runs_from_the_command_line(files):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "import_statements.py"), "--cards", str(files / "cards.psv"), "--cash", str(files / "cash.psv"), "--dry"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and "rows | income" in r.stdout
