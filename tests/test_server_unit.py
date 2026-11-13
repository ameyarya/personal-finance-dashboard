"""server.py, one function at a time and in this process: parsing, storage, the sync engine, the network helpers.

Slower, end-to-end behaviour (a real server, a real browser) is covered in test_api.py and test_ui.py.
"""
import datetime as dt
import io
import json
import os
import stat
import sys
import threading
import time
from pathlib import Path

import pytest

import server
from pdfs import tiny_pdf


@pytest.fixture
def srv(tmp_path, monkeypatch):
    """The server module pointed at an empty temporary data folder, restored afterwards."""
    saved = (dict(server.CFG), json.loads(json.dumps(server.STORE, default=str)), dict(server.SYNC))
    server.CFG.clear()
    server.CFG.update(data=tmp_path, quiet=True, empty=True)
    server.STORE.clear()
    server.STORE.update({"version": 0, "collections": {n: {} for n in server.COLLECTIONS}, "sync": {}})
    server.SYNC.update(running=False, log=[], seq=0, proc=None, phase="", done=0, total=0, started="")
    server.SYNC["cancel"].clear()
    monkeypatch.setattr(server, "AUTH", server.auth.Auth(tmp_path))
    yield server
    server.CFG.clear()
    server.CFG.update(saved[0])
    server.STORE.clear()
    server.STORE.update(saved[1])


# ---------------------------------------------------------------- sample data and storage

def test_sample_data_wraps_back_across_new_year():
    data = server.make_sample(dt.date(2026, 2, 10))
    months = {t["date"][:7] for t in data["transactions"].values()}
    assert "2025-09" in months and "2026-02" in months                   # six months, crossing the year boundary


def test_load_moves_a_legacy_data_file_into_the_data_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "HERE", tmp_path)
    monkeypatch.setitem(server.CFG, "data", tmp_path / "data")
    monkeypatch.setitem(server.CFG, "empty", True)
    (tmp_path / "data.json").write_text(json.dumps({"version": 7, "collections": {"transactions": {"a": {"date": "2025-01-01", "amount": -1}}}}))
    store = server.load()
    assert store["version"] == 7 and "a" in store["collections"]["transactions"]
    assert not (tmp_path / "data.json").exists() and (tmp_path / "data" / "data.json").exists()
    assert store["sync"] == {} and set(server.COLLECTIONS) <= set(store["collections"])      # missing parts are filled in


def test_load_without_a_file_starts_empty_or_with_examples(tmp_path, monkeypatch):
    monkeypatch.setitem(server.CFG, "data", tmp_path / "d1")
    monkeypatch.setitem(server.CFG, "empty", True)
    assert server.load()["collections"]["transactions"] == {}
    monkeypatch.setitem(server.CFG, "data", tmp_path / "d2")
    monkeypatch.setitem(server.CFG, "empty", False)
    assert len(server.load()["collections"]["transactions"]) > 50


def test_public_store_reports_sync_state_without_the_file_list(srv):
    srv.STORE["sync"] = {"files": {"/x.pdf": "1-2"}, "message": "ok"}
    pub = srv.public_store()
    assert "files" not in pub["sync"] and pub["sync"]["message"] == "ok" and pub["sync"]["running"] is False
    assert set(pub["sync"]) >= {"rclone", "pypdf", "phase", "done", "total", "started"}


def test_today_can_be_pinned(monkeypatch):
    monkeypatch.setenv("FINANCES_TODAY", "2031-05-06")
    assert server.today() == dt.date(2031, 5, 6)
    monkeypatch.delenv("FINANCES_TODAY")
    assert server.today() == dt.date.today()


# ---------------------------------------------------------------- categories and CSV

def test_categorize_prefers_your_rules_then_transfers_then_income_then_keywords(srv):
    srv.STORE["collections"]["rules"]["r1"] = {"match": "acme", "category": "Fun"}
    assert srv.categorize("ACME Corp", -5) == "Fun"                       # a remembered rule wins
    assert srv.categorize("Payment Thank You", -5) == "Transfer"
    assert srv.categorize("Payroll", 100) == "Income"
    assert srv.categorize("Pharmacy run", -5) == "Health"
    assert srv.categorize("zzz", -5) == "Other"
    srv.STORE["collections"]["rules"]["r2"] = {"category": "Dining"}      # a broken rule with no text is ignored
    assert srv.categorize("zzz", -5) == "Other"


def test_slug_keeps_short_ids_and_shortens_long_ones_stably():
    assert server.slug("a b/c") == "a_b_c"
    long = "x" * 200
    assert len(server.slug(long)) <= 70 and server.slug(long) == server.slug(long) and server.slug(long) != server.slug(long + "y")


@pytest.mark.parametrize("text,want", [("12.50", 12.5), ("$1,234.00", 1234.0), ("(12.50)", -12.5), ("12.50CR", 12.5), ("12.50DR", -12.5), ("-3", -3.0),
                                       ("", None), ("abc", None), ("  ", None)])
def test_parse_amount(text, want):
    assert server.parse_amount(text) == want


@pytest.mark.parametrize("text,want", [("2025-03-04", "2025-03-04"), ("03/04/2025", "2025-03-04"), ("3/4/25", "2025-03-04"), ("Mar 4, 2025", "2025-03-04"),
                                       ("2025-03-04 10:11:12", "2025-03-04"), ("nonsense", None)])
def test_parse_date(text, want):
    assert server.parse_date(text) == want


def test_parse_csv_errors_are_plain_sentences():
    with pytest.raises(ValueError, match="No header row"):
        server.parse_csv("a,b\n1,2")
    with pytest.raises(ValueError, match="Could not find description and amount"):
        server.parse_csv("Date,Note\n2025-01-01,x")


def test_parse_csv_reads_debit_credit_columns_semicolons_and_skips_bad_rows():
    text = "Posted;Payee;Debit;Credit\n2025-01-02;Shop;5.00;\n2025-01-03;Salary;;100\nbad;row;;\n2025-01-04;Zero;0;0\n"
    rows, cols, bad = server.parse_csv(text)
    assert [(r["date"], r["amount"]) for r in rows] == [("2025-01-02", -5.0), ("2025-01-03", 100.0)]
    assert bad == 2 and "money out" in cols
    flipped, _, _ = server.parse_csv("Date,Description,Amount\n2025-01-02,Shop,5.00", flip=True)
    assert flipped[0]["amount"] == -5.0
    dup, _, _ = server.parse_csv("Date,Description,Amount\n2025-01-02,Shop,5\n2025-01-02,Shop,5")
    assert dup[0]["id"] != dup[1]["id"]                                       # identical rows on one day stay two payments


def test_import_csv_dry_run_then_real_then_duplicates_skipped(srv):
    csv = "Date,Description,Amount\n2025-01-02,Corner Cafe,-4.50\n2025-01-03,Payroll,1000\n"
    dry = srv.import_csv(csv, False, True)
    assert dry["new"] == 2 and dry["imported"] == 0 and not srv.STORE["collections"]["transactions"]
    real = srv.import_csv(csv, False, False)
    assert real["imported"] == 2 and len(srv.STORE["collections"]["transactions"]) == 2
    again = srv.import_csv(csv, False, False)
    assert again["new"] == 0 and again["duplicates"] == 2 and again["imported"] == 0
    cats = {t["desc"]: t["category"] for t in srv.STORE["collections"]["transactions"].values()}
    assert cats == {"Corner Cafe": "Dining", "Payroll": "Income"}


def test_persist_writes_atomically_and_bumps_the_version(srv):
    srv.persist()
    srv.persist()
    saved = json.loads((srv.CFG["data"] / "data.json").read_text())
    assert saved["version"] == 2 and not (srv.CFG["data"] / "data.json.tmp").exists()


# ---------------------------------------------------------------- the sync engine, piece by piece

def test_pypdf_available_reflects_whether_it_can_be_imported(monkeypatch):
    assert server.pypdf_available() is True
    monkeypatch.setitem(sys.modules, "pypdf", None)
    assert server.pypdf_available() is False


def test_find_rclone_looks_in_homebrew_folders(monkeypatch, tmp_path):
    tool = tmp_path / "rclone"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setattr(server.shutil, "which", lambda name, path=None: str(tool) if path and "/opt/homebrew/bin" in path else None)
    assert server.find_rclone() == str(tool)


def fake_rclone(tmp_path, monkeypatch, script):
    """An 'rclone' that prints what the script says, for testing the download step without Google."""
    path = tmp_path / "rclone-fake"
    path.write_text("#!/bin/sh\n" + script + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(server, "find_rclone", lambda: str(path))
    return path


def test_drive_pull_does_nothing_without_a_link_and_rejects_a_bad_one(srv, tmp_path):
    assert srv.drive_pull({}, tmp_path / "d") is None
    assert srv.drive_pull({"driveLink": "   "}, tmp_path / "d") is None
    with pytest.raises(srv.SyncError, match="does not look like a Google Drive folder link"):
        srv.drive_pull({"driveLink": "https://example.com/x"}, tmp_path / "d")


def test_drive_pull_needs_rclone_installed(srv, tmp_path, monkeypatch):
    monkeypatch.setattr(server, "find_rclone", lambda: None)
    with pytest.raises(srv.SyncError, match="rclone is not installed"):
        srv.drive_pull({"driveLink": "https://drive.google.com/drive/folders/abc123"}, tmp_path / "d")


@pytest.mark.parametrize("link,folder", [("https://drive.google.com/drive/folders/abc-123_X?usp=sharing", "abc-123_X"), ("https://drive.google.com/open?id=idOnly9", "idOnly9")])
def test_drive_pull_passes_the_folder_id_and_streams_a_clean_log(srv, tmp_path, monkeypatch, link, folder):
    log = tmp_path / "args.txt"
    fake_rclone(tmp_path, monkeypatch, """echo "$@" > %s
echo "2025/03/04 10:11:12 NOTICE: gdrive: This remote uses rclone's shared Google Drive client_id, which is being retired"
echo "2025/03/04 10:11:12 INFO  :           0 B / 0 B, -, 0 B/s, ETA -"
echo "2025/03/04 10:11:13 INFO  : Jan.pdf: Copied (new)"
echo "2025/03/04 10:11:13 INFO  : Jan.pdf: Copied (new)"
echo ""
echo "2025/03/04 10:11:14 NOTICE: something to know"
echo "2025/03/04 10:11:15 ERROR : a file failed"
exit 0""" % log)
    srv.drive_pull({"driveLink": link, "rcloneRemote": "mydrive"}, tmp_path / "d")
    args = log.read_text()
    assert "mydrive,root_folder_id=%s:" % folder in args and "--include *.pdf" in args
    lines = [(x["l"], x["m"]) for x in srv.SYNC["log"]]
    messages = [m for _, m in lines]
    assert messages.count("INFO  : Jan.pdf: Copied (new)") == 1               # repeated lines collapse
    assert not any("0 B / 0 B" in m or "client_id" in m for m in messages)    # progress ticks and the retirement notice are noise
    assert ("warn", "NOTICE: something to know") in lines and ("warn", "ERROR : a file failed") in lines
    assert lines[-1] == ("ok", "Download finished") and srv.SYNC["proc"] is None
    assert (tmp_path / "d").is_dir()


@pytest.mark.parametrize("script,expected", [
    ("echo \"Failed to create file system: didn't find section in config file\"; exit 3", "rclone config create mydrive drive scope=drive.readonly"),
    ("echo 'Failed: remote not found in config'; exit 3", "Sign in to Google Drive once"),
    ("echo 'ERROR : quota exceeded'; exit 1", "Google Drive said: ERROR : quota exceeded"),
    ("exit 1", "Google Drive said: rclone failed"),
    ("kill -9 $$", "took too long"),
])
def test_drive_pull_explains_failures_in_plain_words(srv, tmp_path, monkeypatch, script, expected):
    fake_rclone(tmp_path, monkeypatch, script)
    with pytest.raises(srv.SyncError, match=expected.replace("(", r"\(")):
        srv.drive_pull({"driveLink": "https://drive.google.com/drive/folders/abc", "rcloneRemote": "mydrive"}, tmp_path / "d")


def test_drive_pull_can_be_stopped_mid_download(srv, tmp_path, monkeypatch):
    fake_rclone(tmp_path, monkeypatch, "echo started; exec sleep 30")
    outcome = {}

    def run():
        try:
            srv.drive_pull({"driveLink": "https://drive.google.com/drive/folders/abc"}, tmp_path / "d")
        except BaseException as e:           # noqa: BLE001 - we want to see what escaped
            outcome["error"] = e

    t = threading.Thread(target=run)
    t.start()
    for _ in range(100):
        if srv.SYNC["proc"] is not None:
            break
        time.sleep(0.05)
    srv.stop_sync()
    t.join(10)
    assert isinstance(outcome.get("error"), srv.Stopped) and not t.is_alive()


def test_stop_sync_is_harmless_when_nothing_is_running(srv):
    srv.stop_sync()
    assert srv.SYNC["cancel"].is_set()


def test_year_window_reads_blank_and_junk_as_no_limit():
    assert server.year_window({}) == (None, None)
    assert server.year_window({"fromYear": "2024", "toYear": " 2025 "}) == (2024, 2025)
    assert server.year_window({"fromYear": "abc", "toYear": ""}) == (None, None)
    assert server.year_window({"fromYear": 2023, "toYear": None}) == (2023, None)


def test_take_match_uses_exact_dates_first_then_the_nearest_within_four_days():
    have = {("Visa", 5.0): ["2025-03-10", "2025-03-14", "garbage"]}
    assert server.take_match(have, "Visa", -5.0, "2025-03-10") is True                 # exact
    assert server.take_match(have, "Visa", -5.0, "2025-03-12") is True                 # nearest is the 14th (two days away)
    assert server.take_match(have, "Visa", -5.0, "2025-03-12") is False                # only an unreadable date is left
    assert server.take_match(have, "Visa", -5.0, "2026-01-01") is False
    assert server.take_match({}, "Visa", -9.0, "2025-01-01") is False
    near = {("V", 1.0): ["2025-03-10", "2025-03-11"]}
    assert server.take_match(near, "V", 1.0, "2025-03-12") is True and near[("V", 1.0)] == ["2025-03-10"]     # picks the closer one


def test_merge_files_keeps_the_most_copies_any_single_file_has():
    row = lambda d, a, c="V": {"date": d, "desc": "x", "amount": a, "card": c}
    merged = server.merge_files([[row("2025-01-01", -1)], [row("2025-01-01", -1), row("2025-01-01", -1)], [row("2025-01-02", -2, "W")]])
    assert sorted((r["date"], r["card"]) for r in merged) == [("2025-01-01", "V"), ("2025-01-01", "V"), ("2025-01-02", "W")]
    assert server.merge_files([]) == []


def test_add_statement_rows_categorises_flags_refunds_cash_and_honours_the_year_window(srv):
    rows = [[{"date": "2024-12-31", "desc": "Old", "amount": -1.0, "card": "Visa"},
             {"date": "2025-02-01", "desc": "Pharmacy", "amount": -8.0, "card": "Visa"},
             {"date": "2025-02-02", "desc": "Pharmacy", "amount": 8.0, "card": "Visa"},                                  # a refund on a card
             {"date": "2025-02-03", "desc": "Payroll", "amount": 900.0, "card": "Bank", "cash": True},
             {"date": "2025-02-04", "desc": "Card payment", "amount": 50.0, "card": "Visa", "category": "Transfer"},
             {"date": "2026-01-01", "desc": "Future", "amount": -1.0, "card": "Visa"}]]
    added, skipped, dupes = srv.add_statement_rows(rows, (2025, 2025))
    assert (added, skipped, dupes) == (4, 2, 0)
    docs = {t["desc"] + str(t["amount"]): t for t in srv.STORE["collections"]["transactions"].values()}
    assert docs["Pharmacy-8.0"]["category"] == "Health" and "refund" not in docs["Pharmacy-8.0"]
    assert docs["Pharmacy8.0"]["refund"] is True
    assert docs["Payroll900.0"]["cash"] is True and docs["Payroll900.0"]["category"] == "Income" and "refund" not in docs["Payroll900.0"]
    assert docs["Card payment50.0"]["category"] == "Transfer"
    assert all(t["source"] == "pdf" and t["who"] == "" for t in docs.values())
    again = srv.add_statement_rows(rows, (2025, 2025))
    assert again == (0, 2, 4)                                                    # nothing is added twice


def test_drop_pdf_duplicates_keeps_rows_nothing_else_has(srv):
    docs = srv.STORE["collections"]["transactions"]
    docs.update({"a": {"date": "2025-03-18", "amount": -5.0, "card": "V", "source": "statement"},
                 "b": {"date": "2025-03-17", "amount": -5.0, "card": "V", "source": "pdf"},
                 "c": {"date": "2025-03-17", "amount": -6.0, "card": "V", "source": "pdf"}})
    assert srv.drop_pdf_duplicates() == 1 and sorted(docs) == ["a", "c"]
    assert srv.drop_pdf_duplicates() == 0


# ---------------------------------------------------------------- run_sync, every branch

STATEMENT = ("Bank of America Your Adv Plus Banking Account number: 1 Beginning balance on March 1, 2025 $0.00 Ending balance on March 31, 2025 $0.00\n"
             "Deposits and other additions Date Description Amount\n03/05/25 Payroll ACME 100.00\nTotal deposits and other additions $100.00")


def configure(srv, **sync):
    srv.STORE["collections"]["settings"]["main"] = {"household": "H", "sync": dict({"auto": False}, **sync)}


def lines(srv):
    return [x["m"] for x in srv.SYNC["log"]]


def test_run_sync_needs_a_source(srv):
    configure(srv)
    srv.run_sync()
    assert srv.STORE["sync"]["ok"] is False and "Add a Google Drive folder link or a local folder" in srv.STORE["sync"]["message"]
    assert srv.SYNC["running"] is False and srv.SYNC["phase"] == ""


def test_run_sync_reports_a_missing_folder_and_missing_pypdf(srv, tmp_path, monkeypatch):
    configure(srv, localFolder=str(tmp_path / "nope"))
    srv.run_sync()
    assert "does not exist" in srv.STORE["sync"]["message"]
    (tmp_path / "pdfs").mkdir()
    configure(srv, localFolder=str(tmp_path / "pdfs"))
    monkeypatch.setitem(sys.modules, "pypdf", None)
    srv.run_sync()
    assert "needs pypdf" in srv.STORE["sync"]["message"]


def test_run_sync_does_not_start_twice(srv, tmp_path):
    configure(srv, localFolder=str(tmp_path))
    srv.SYNC["running"] = True
    srv.run_sync()
    assert srv.STORE["sync"] == {} and srv.SYNC["log"] == []                 # the second call left no trace


def test_run_sync_end_to_end_with_a_damaged_file_an_unknown_layout_and_a_good_statement(srv, tmp_path):
    folder = tmp_path / "pdfs"
    (folder / "bank").mkdir(parents=True)
    tiny_pdf(folder / "bank" / "good.pdf", STATEMENT)
    tiny_pdf(folder / "bank" / "unknown.pdf", "just some words, no statement here")
    (folder / "bank" / "broken.pdf").write_bytes(b"%PDF-1.4 definitely not a pdf")
    configure(srv, localFolder=str(folder), fromYear="2025", toYear="2025")
    srv.run_sync()
    st = srv.STORE["sync"]
    assert st["ok"] is True and st["added"] == 1 and st["pdfs"] == 3
    reasons = " ".join(st["unreadable"])
    assert "broken.pdf" in reasons and "unknown.pdf (layout not recognised)" in reasons
    log = "\n".join(lines(srv))
    assert "Found 3 statement PDFs" in log and "layout not recognised, left alone" in log and "could not read it" in log
    assert "1 new, 0 already in the dashboard" in log and "Keeping payments from 2025 to 2025" in log
    second = srv.STORE["collections"]["transactions"]
    assert len(second) == 1
    srv.run_sync()                                                            # unchanged files are skipped the second time
    assert "unchanged, skipped" in "\n".join(lines(srv)) and srv.STORE["sync"]["added"] == 0
    srv.run_sync(force=True)
    assert "re-reading every statement" in lines(srv)[0] and "1 already in the dashboard" in " ".join(lines(srv))


def test_run_sync_reports_what_it_removed_and_what_the_year_window_ignored(srv, tmp_path):
    folder = tmp_path / "p"
    folder.mkdir()
    tiny_pdf(folder / "a.pdf", STATEMENT)
    srv.STORE["collections"]["transactions"].update({
        "keep": {"date": "2025-01-10", "amount": -3.0, "card": "V", "source": "statement"},
        "dupe": {"date": "2025-01-09", "amount": -3.0, "card": "V", "source": "pdf"}})
    configure(srv, localFolder=str(folder), fromYear="2026")
    srv.run_sync()
    log = "\n".join(lines(srv))
    assert "Removed 1 payment an earlier pass had added twice" in log
    assert "1 outside the years you chose ignored" in log and "outside the years you chose skipped" in srv.STORE["sync"]["message"]


def test_run_sync_can_be_stopped_between_files_and_just_before_saving(srv, tmp_path, monkeypatch):
    folder = tmp_path / "p"
    folder.mkdir()
    for i in range(3):
        tiny_pdf(folder / ("s%d.pdf" % i), STATEMENT.replace("100.00", "%d.00" % (100 + i)))
    configure(srv, localFolder=str(folder))
    real = server.statements.parse_pdf
    calls = []

    def stop_after_first(path, hint=""):
        calls.append(path)
        server.stop_sync()
        return real(path, hint)

    monkeypatch.setattr(server.statements, "parse_pdf", stop_after_first)
    srv.run_sync()
    assert len(calls) == 1 and srv.STORE["sync"]["ok"] is False and "Stopped" in srv.STORE["sync"]["message"]
    assert not srv.STORE["collections"]["transactions"] and srv.STORE["sync"].get("files", {}) == {}      # nothing kept, so it all gets read again
    # stopping while the last file is being read: the check right before saving catches it
    monkeypatch.setattr(server.statements, "parse_pdf", lambda p, h="": (server.stop_sync(), real(p, h))[1])
    configure(srv, localFolder=str(folder))
    for f in list(folder.glob("s[12].pdf")):
        f.unlink()
    srv.run_sync()
    assert "Stopped by you" in "\n".join(lines(srv)) and not srv.STORE["collections"]["transactions"]


def test_run_sync_turns_surprises_into_a_message(srv, tmp_path, monkeypatch):
    configure(srv, localFolder=str(tmp_path))
    monkeypatch.setattr(server, "drive_pull", lambda cfg, dest: (_ for _ in ()).throw(RuntimeError("disk on fire")))
    configure(srv, driveLink="https://drive.google.com/drive/folders/abc")
    srv.run_sync()
    assert srv.STORE["sync"]["ok"] is False and "Sync failed: disk on fire" in srv.STORE["sync"]["message"]
    assert srv.SYNC["running"] is False


def test_run_sync_downloads_then_reads_with_a_fake_rclone(srv, tmp_path, monkeypatch):
    fake = tmp_path / "bin-rclone"
    pdf_source = tmp_path / "src.pdf"
    tiny_pdf(pdf_source, STATEMENT)
    fake.write_text("#!/bin/sh\nmkdir -p \"$3\"\ncp %s \"$3/drive.pdf\"\necho 'INFO  : drive.pdf: Copied (new)'\n" % pdf_source)
    fake.chmod(0o755)
    monkeypatch.setattr(server, "find_rclone", lambda: str(fake))
    configure(srv, driveLink="https://drive.google.com/drive/folders/abc")
    srv.run_sync()
    assert srv.STORE["sync"]["ok"] is True and srv.STORE["sync"]["added"] == 1
    assert "Copied (new)" in "\n".join(lines(srv))


# ---------------------------------------------------------------- the background loop

class Done(Exception):
    pass


def run_loop(monkeypatch, sleeps=2):
    """Run auto_sync for a few sleeps, then stop it."""
    count = {"n": 0}

    def fake_sleep(seconds):
        count["n"] += 1
        if count["n"] > sleeps:
            raise Done()

    monkeypatch.setattr(server.time, "sleep", fake_sleep)
    with pytest.raises(Done):
        server.auto_sync()


def test_auto_sync_runs_when_due_and_waits_when_not(srv, monkeypatch):
    runs = []
    monkeypatch.setattr(server, "run_sync", lambda *a, **k: runs.append(1))
    configure(srv, localFolder="/x", auto=True)
    run_loop(monkeypatch)                                                     # never synced: due
    assert runs
    runs.clear()
    srv.STORE["sync"]["lastRun"] = dt.datetime.now().isoformat()
    run_loop(monkeypatch)                                                     # just synced: wait
    assert not runs
    srv.STORE["sync"]["lastRun"] = (dt.datetime.now() - dt.timedelta(hours=3)).isoformat()
    configure(srv, driveLink="https://drive.google.com/drive/folders/a", auto=True, everyMinutes="5")
    run_loop(monkeypatch)
    assert runs


@pytest.mark.parametrize("sync", [{"auto": False, "localFolder": "/x"}, {"auto": True}, {"auto": True, "localFolder": "   "}])
def test_auto_sync_stays_quiet_when_switched_off_or_unconfigured(srv, monkeypatch, sync):
    runs = []
    monkeypatch.setattr(server, "run_sync", lambda *a, **k: runs.append(1))
    srv.STORE["collections"]["settings"]["main"] = {"sync": sync}
    run_loop(monkeypatch)
    assert not runs


def test_auto_sync_survives_a_broken_settings_value(srv, monkeypatch):
    srv.STORE["collections"]["settings"]["main"] = {"sync": {"localFolder": "/x", "everyMinutes": "soon"}}
    monkeypatch.setattr(server, "run_sync", lambda *a, **k: None)
    run_loop(monkeypatch)                                                     # int("soon") fails inside the loop; the loop carries on


# ---------------------------------------------------------------- the request handler, without a socket

class Fake(server.Handler):
    def __init__(self, ip="127.0.0.1", command="GET", headers=None, path="/", body=b""):
        self.client_address = (ip, 5555)
        self.command, self.headers, self.path = command, headers or {}, path
        self.rfile = io.BytesIO(body)
        self.sent = []

    def send_bytes(self, code, body, ctype, extra=None):
        self.sent.append((code, body, ctype, extra or {}))

    def send_json(self, code, obj):
        self.sent.append((code, obj))


@pytest.mark.parametrize("ip,ok", [("127.0.0.1", True), ("192.168.1.9", True), ("::1", True), ("::ffff:10.0.0.4", True), ("fe80::1", True),  # privacy: allow
                                   ("8.8.8.8", False), ("not-an-ip", False), ("2001:4860:4860::8888", False)])
def test_only_the_home_network_is_answered(ip, ok):
    assert Fake(ip=ip).allowed() is ok


def test_writes_must_be_json_and_from_the_same_site():
    good = {"Content-Type": "application/json", "Host": "finances.local:8770"}
    assert Fake(command="PUT", headers=dict(good, Origin="http://finances.local:8770")).allowed() is True
    assert Fake(command="PUT", headers=good).allowed() is True                         # no Origin header: not a browser cross-site request
    assert Fake(command="PUT", headers=dict(good, Origin="https://evil.example")).allowed() is False
    assert Fake(command="PUT", headers={"Content-Type": "text/plain", "Host": "x"}).allowed() is False


def test_read_body_accepts_only_a_json_object_of_sane_size():
    j = lambda b, n=None: Fake(headers={"Content-Length": str(len(b) if n is None else n)}, body=b).read_body()
    assert j(b'{"a": 1}') == {"a": 1}
    assert j(b"[1,2]") is None and j(b"not json") is None and j(b"") is None
    assert Fake(headers={}, body=b"{}").read_body() is None
    assert j(b"{}", n=server.MAX_BODY + 1) is None


def test_log_lines_are_printed_unless_quiet(capsys, monkeypatch):
    h = Fake()
    monkeypatch.setitem(server.CFG, "quiet", True)
    h.log_message("%s done", "x")
    assert capsys.readouterr().out == ""
    monkeypatch.setitem(server.CFG, "quiet", False)
    h.log_message("%s done", "x")
    assert "x done" in capsys.readouterr().out


def test_a_stranger_gets_forbidden_on_get_and_write():
    h = Fake(ip="8.8.8.8")
    h.do_GET()
    assert h.sent == [(403, {"error": "forbidden"})]
    p = Fake(ip="8.8.8.8", command="POST")
    p.do_POST()
    assert p.sent == [(403, {"error": "forbidden"})]
    w = Fake(ip="8.8.8.8", command="PUT")
    w.write("set")
    assert w.sent == [(403, {"error": "forbidden"})]


def test_session_info_hides_the_names_from_strangers_when_sign_in_is_on(srv):
    srv.AUTH.set_password("Una", "correct horse")
    stranger = Fake()
    assert stranger.session_info() == {"required": True, "user": None, "minLength": server.auth.MIN_LENGTH}
    srv.AUTH.set_required(False)
    assert Fake().session_info()["users"] == ["Una"]
