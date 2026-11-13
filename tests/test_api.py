"""Server tests. Standard library plus pytest; no browser needed."""
import json
import stat

CSV_AMOUNT = """Date,Description,Amount
11/03/2026,WHOLE FOODS MARKET #55,-82.14
11/04/2026,ACME CORP PAYROLL,2100.00
11/05/2026,Online Transfer to Savings,-300.00
11/06/2026,Corner Bodega,"(12.50)"
bad row,,
"""
CSV_SPLIT = """Account summary for November

Posted Date;Payee;Withdrawal;Deposit
2026-11-02;City Water Utility;45.10;
2026-11-03;Refund Shoe Store;;25.00
"""


def test_first_run_creates_usd_example_data(server):
    c = server.data()["collections"]
    assert c["settings"]["main"]["currency"] == "USD"
    assert len(c["transactions"]) > 100
    assert all(t.get("sample") for t in c["transactions"].values())
    assert max(t["date"] for t in c["transactions"].values()) <= "2026-11-12"
    assert (server.data_dir / "data.json").exists()


def test_empty_flag_starts_with_nothing(empty_server):
    c = empty_server.data()["collections"]
    assert all(len(docs) == 0 for docs in c.values())


def test_serves_only_the_public_files(server):
    assert server.call("GET", "/")[0] == 200
    assert server.call("GET", "/app.js")[0] == 200
    assert server.call("GET", "/app.css")[0] == 200
    for path in ("/server.py", "/data/data.json", "/../server.py", "/public/app.js", "/%2e%2e/server.py"):
        assert server.call("GET", path)[0] == 404, path


def test_create_update_delete_and_file_on_disk(server):
    assert server.call("PUT", "/api/doc/transactions/t1", {"date": "2026-11-12", "desc": "Test", "amount": -5})[0] == 200
    assert server.call("PATCH", "/api/doc/transactions/t1", {"amount": -7})[0] == 200
    assert server.docs("transactions")["t1"] == {"date": "2026-11-12", "desc": "Test", "amount": -7}
    on_disk = json.loads((server.data_dir / "data.json").read_text())
    assert on_disk["collections"]["transactions"]["t1"]["amount"] == -7
    assert server.call("DELETE", "/api/doc/transactions/t1")[0] == 200
    assert "t1" not in server.docs("transactions")


def test_data_survives_a_restart(server):
    server.call("PUT", "/api/doc/budgets/keep", {"name": "Keep me", "target": 10, "saved": 1})
    server.stop()
    server.start()
    assert server.docs("budgets")["keep"]["name"] == "Keep me"


def test_rejects_bad_requests(server):
    assert server.call("PATCH", "/api/doc/budgets/nope", {"saved": 1})[0] == 404
    assert server.call("PUT", "/api/doc/secrets/x", {"a": 1})[0] == 404
    assert server.call("PUT", "/api/doc/budgets/bad%20id!", {"a": 1})[0] in (400, 404)
    assert server.call("PUT", "/api/doc/budgets/x", b"[1,2]")[0] == 400
    assert server.call("PUT", "/api/doc/budgets/x", b"not json")[0] == 400


def test_other_websites_cannot_write(server):
    before = server.data()["version"]
    assert server.call("PUT", "/api/doc/budgets/x", {"a": 1}, {"Origin": "https://evil.example"})[0] == 403
    assert server.call("PUT", "/api/doc/budgets/x", {"a": 1}, {"Content-Type": "text/plain"})[0] == 403
    assert server.call("POST", "/api/batch", {"writes": []}, {"Origin": "https://evil.example"})[0] == 403
    assert server.data()["version"] == before
    same_origin = {"Origin": server.url}
    assert server.call("PUT", "/api/doc/budgets/x", {"a": 1}, same_origin)[0] == 200


def test_batch_applies_all_writes(server):
    writes = [{"op": "set", "col": "budgets", "id": "a", "data": {"name": "A", "target": 1, "saved": 0}},
              {"op": "update", "col": "budgets", "id": "a", "data": {"saved": 1}},
              {"op": "delete", "col": "budgets", "id": "s-trip"}]
    assert server.call("POST", "/api/batch", {"writes": writes})[0] == 200
    budgets = server.docs("budgets")
    assert budgets["a"]["saved"] == 1 and "s-trip" not in budgets
    assert server.call("POST", "/api/batch", {"writes": [{"op": "set", "col": "nope", "id": "a", "data": {}}]})[0] == 400


def test_csv_preview_then_import_then_no_duplicates(empty_server):
    s = empty_server
    status, dry = s.call("POST", "/api/import/csv", {"text": CSV_AMOUNT, "dry": True})
    assert status == 200 and dry["found"] == 4 and dry["new"] == 4 and dry["unreadable"] == 1 and dry["imported"] == 0
    assert len(s.docs("transactions")) == 0
    assert s.call("POST", "/api/import/csv", {"text": CSV_AMOUNT})[1]["imported"] == 4
    by_desc = {t["desc"]: t for t in s.docs("transactions").values()}
    assert by_desc["WHOLE FOODS MARKET #55"]["category"] == "Groceries" and by_desc["WHOLE FOODS MARKET #55"]["amount"] == -82.14
    assert by_desc["WHOLE FOODS MARKET #55"]["date"] == "2026-11-03"
    assert by_desc["ACME CORP PAYROLL"]["category"] == "Income"
    assert by_desc["Online Transfer to Savings"]["category"] == "Transfer"
    assert by_desc["Corner Bodega"]["amount"] == -12.5
    again = s.call("POST", "/api/import/csv", {"text": CSV_AMOUNT})[1]
    assert again["imported"] == 0 and again["duplicates"] == 4
    assert len(s.docs("transactions")) == 4


def test_csv_with_separate_in_and_out_columns(empty_server):
    r = empty_server.call("POST", "/api/import/csv", {"text": CSV_SPLIT})[1]
    assert r["imported"] == 2 and r["columns"]["money out"] == "Withdrawal"
    amounts = sorted(t["amount"] for t in empty_server.docs("transactions").values())
    assert amounts == [-45.1, 25.0]


def test_csv_reversed_amounts(empty_server):
    text = "Date,Description,Amount\n11/03/2026,Card purchase,40.00\n"
    empty_server.call("POST", "/api/import/csv", {"text": text, "flip": True})
    assert [t["amount"] for t in empty_server.docs("transactions").values()] == [-40.0]


def test_csv_without_usable_columns_is_explained(empty_server):
    status, body = empty_server.call("POST", "/api/import/csv", {"text": "a,b,c\n1,2,3\n"})
    assert status == 400 and "date" in body["error"].lower()
    assert empty_server.call("POST", "/api/import/csv", {"text": "   "})[0] == 400


def test_remembered_rule_wins_on_import(empty_server):
    empty_server.call("PUT", "/api/doc/rules/r-bodega", {"match": "corner bodega", "category": "Dining"})
    empty_server.call("POST", "/api/import/csv", {"text": CSV_AMOUNT})
    by_desc = {t["desc"]: t for t in empty_server.docs("transactions").values()}
    assert by_desc["Corner Bodega"]["category"] == "Dining"


def test_export_and_backup(server):
    status, text = server.call("GET", "/api/export.csv")
    lines = text.strip().splitlines()
    assert status == 200 and lines[0] == "date,description,amount,category,who,account"
    assert len(lines) == len(server.docs("transactions")) + 1
    status, backup = server.call("GET", "/api/backup.json")
    assert status == 200 and set(backup) == {"version", "collections"}
