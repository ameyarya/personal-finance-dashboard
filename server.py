#!/usr/bin/env python3
"""Personal Finance Dashboard: a self-hosted household money page.

Run `python3 server.py` and open http://localhost:8770/ (or http://finances.local:8770/
from any device on the same network). Standard library only, no accounts, no cloud.

Everything is stored in one JSON file under ./data. Only devices on the local
network are answered, and other websites cannot write to it.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import urllib.parse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import auth
import statements

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public"
COLLECTIONS = ("settings", "transactions", "budgets", "recurring", "accounts", "rules")
ID_RE = re.compile(r"^[A-Za-z0-9_.~:@+-]{1,200}$")
MAX_BODY = 8 * 1024 * 1024
MIME = {".png": "image/png", ".ico": "image/svg+xml", ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json"}

AUTH = None
lock = threading.RLock()
SYNC = {"running": False, "log": [], "seq": 0, "cancel": threading.Event(), "phase": "", "done": 0, "total": 0, "started": ""}
CFG = {}
STORE = {}


def today():
    """The current date; FINANCES_TODAY=YYYY-MM-DD pins it for tests."""
    fixed = os.environ.get("FINANCES_TODAY")
    return dt.date.fromisoformat(fixed) if fixed else dt.date.today()


# ---------------------------------------------------------------- sample data

RECURRING = [  # id, name, amount, day of month, category, who
    ("pay-a", "Paycheck (Alex)", 4850, 1, "Income", "Alex"),
    ("pay-b", "Paycheck (Sam)", 3900, 20, "Income", "Sam"),
    ("rent", "Rent", -2150, 3, "Housing", ""),
    ("stream", "Streaming", -23, 9, "Fun", ""),
    ("invest", "Index fund transfer", -1500, 10, "Savings", ""),
    ("gym", "Gym", -54, 14, "Health", ""),
    ("power", "Electricity", -96, 15, "Utilities", ""),
    ("net", "Internet", -70, 18, "Utilities", ""),
    ("car-ins", "Car insurance", -138, 21, "Transport", ""),
    ("phone", "Phone plans", -85, 22, "Utilities", ""),
]
SPENDING = [  # day of month, description, typical amount, category, who
    (2, "Farmers market", 64, "Groceries", "Sam"), (4, "Grocery run", 142, "Groceries", "Alex"),
    (5, "Gas", 48, "Transport", "Sam"), (6, "Coffee shop", 7, "Dining", "Alex"),
    (7, "Dinner out", 86, "Dining", "Alex"), (8, "Pharmacy", 23, "Health", "Sam"),
    (9, "Hardware store", 57, "Shopping", "Alex"), (11, "Grocery run", 128, "Groceries", "Sam"),
    (12, "Lunch", 18, "Dining", "Sam"), (13, "Transit pass", 45, "Transport", "Alex"),
    (16, "Movie tickets", 34, "Fun", "Alex"), (17, "Grocery run", 151, "Groceries", "Alex"),
    (19, "Takeout", 42, "Dining", "Sam"), (21, "Clothing", 118, "Shopping", "Sam"),
    (23, "Gas", 51, "Transport", "Sam"), (24, "Grocery run", 136, "Groceries", "Sam"),
    (25, "Concert tickets", 90, "Fun", "Alex"), (26, "Brunch", 58, "Dining", "Alex"),
    (27, "Dentist copay", 40, "Health", "Alex"), (28, "Online order", 73, "Shopping", "Sam"),
]


def make_sample(now):
    """Six months of made-up US household figures ending today. Every entry is flagged sample."""
    tx = {}
    for back in range(5, -1, -1):
        y, m = now.year, now.month - back
        while m < 1:
            y, m = y - 1, m + 12
        ym = "%04d-%02d" % (y, m)
        last = now.day if back == 0 else 31
        rng = random.Random(ym)
        for rid, name, amount, day, cat, who in RECURRING:
            if day <= last:
                tx["s-%s-%s" % (ym, rid)] = {"date": "%s-%02d" % (ym, day), "desc": name, "amount": amount,
                                             "category": cat, "who": who, "recId": rid, "sample": True}
        for n, (day, desc, base, cat, who) in enumerate(SPENDING):
            if day <= last:
                amount = -round(base * rng.uniform(0.8, 1.25), 2)
                tx["s-%s-%02d" % (ym, n)] = {"date": "%s-%02d" % (ym, day), "desc": desc, "amount": amount,
                                             "category": cat, "who": who, "sample": True}
    return {
        "settings": {"main": {"household": "Our household", "currency": "USD", "opening": 1800,
                              "members": ["Alex", "Sam"], "sample": True}},
        "transactions": tx,
        "budgets": {k: {"limit": v, "sample": True} for k, v in
                    {"Groceries": 700, "Dining": 300, "Transport": 320, "Shopping": 250, "Fun": 180,
                     "Utilities": 280, "Health": 150}.items()},
        "recurring": {rid: {"name": name, "amount": amount, "day": day, "category": cat, "sample": True}
                      for rid, name, amount, day, cat, who in RECURRING},
        "accounts": {}, "rules": {},
    }


# ---------------------------------------------------------------- storage

def data_file():
    return CFG["data"] / "data.json"


def load():
    CFG["data"].mkdir(parents=True, exist_ok=True)
    legacy = HERE / "data.json"
    if not data_file().exists() and legacy.exists() and CFG["data"] == HERE / "data":
        shutil.move(str(legacy), str(data_file()))
    if data_file().exists():
        store = json.loads(data_file().read_text("utf-8"))
    else:
        store = {"version": 0, "collections": {} if CFG["empty"] else make_sample(today())}
    store.setdefault("sync", {})
    for name in COLLECTIONS:
        store["collections"].setdefault(name, {})
    return store


def persist():
    STORE["version"] += 1
    tmp = data_file().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(STORE, indent=1, ensure_ascii=False), "utf-8")
    os.replace(tmp, data_file())


def public_store():
    sync = {k: v for k, v in STORE.get("sync", {}).items() if k != "files"}
    sync.update(running=SYNC["running"], phase=SYNC["phase"], done=SYNC["done"], total=SYNC["total"], started=SYNC["started"], pypdf=pypdf_available())
    return {"version": STORE["version"], "collections": STORE["collections"], "sync": sync}


# ---------------------------------------------------------------- categories

KEYWORDS = [
    ("Transfer", ("transfer", "payment thank you", "credit card payment", "autopay payment", "online payment", "zelle to", "venmo cashout")),
    ("Housing", ("rent", "mortgage", "hoa", "property tax", "home depot", "lowe's", "lowes")),
    ("Groceries", ("grocery", "groceries", "market", "trader joe", "whole foods", "safeway", "kroger", "costco", "aldi", "publix", "wegmans", "h-e-b", "instacart")),
    ("Utilities", ("electric", "energy", "water", "gas company", "utility", "internet", "comcast", "xfinity", "verizon", "at&t", "t-mobile", "spectrum", "phone")),
    ("Transport", ("uber", "lyft", "shell", "chevron", "exxon", "bp ", "gas station", "fuel", "parking", "transit", "metro", "toll", "geico", "progressive", "car insurance", "dmv")),
    ("Dining", ("restaurant", "cafe", "coffee", "starbucks", "doordash", "grubhub", "uber eats", "mcdonald", "chipotle", "pizza", "bar ", "grill", "sushi", "taqueria", "bakery", "diner")),
    ("Health", ("pharmacy", "cvs", "walgreens", "doctor", "dental", "dentist", "medical", "clinic", "hospital", "gym", "fitness", "health")),
    ("Kids", ("daycare", "school", "tuition", "toys", "pediatric")),
    ("Fun", ("netflix", "spotify", "hulu", "disney", "cinema", "movie", "theater", "concert", "ticketmaster", "steam", "playstation", "nintendo", "streaming")),
    ("Savings", ("vanguard", "fidelity", "schwab", "brokerage", "investment", "ira ", "401k", "savings")),
    ("Shopping", ("amazon", "target", "walmart", "best buy", "etsy", "ebay", "store", "shop", "clothing", "apparel", "ikea")),
]
INCOME_HINTS = ("payroll", "paycheck", "salary", "direct dep", "deposit", "interest", "refund", "dividend")


def categorize(desc, amount):
    text = " " + desc.lower() + " "
    with lock:
        rules = sorted(STORE["collections"]["rules"].values(), key=lambda r: -len(r.get("match", "")))
    for rule in rules:
        if rule.get("match") and rule["match"] in text:
            return rule.get("category", "Other")
    for cat, words in KEYWORDS:
        if cat == "Transfer" and any(w in text for w in words):
            return cat
    if amount > 0:
        return "Income"
    for cat, words in KEYWORDS:
        if any(w in text for w in words):
            return cat
    return "Other"


def slug(text, limit=70):
    s = re.sub(r"[^A-Za-z0-9_.~:@+-]", "_", str(text))
    return s if len(s) <= limit else s[:limit - 13] + "-" + hashlib.sha1(str(text).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- CSV import

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%B %d, %Y")


def parse_date(text):
    text = text.strip().split(" ")[0] if re.match(r"^\d", text.strip()) and ":" in text else text.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_amount(text):
    t = text.strip().replace("$", "").replace(",", "").replace(" ", "")
    if not t:
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if t.upper().endswith("CR"):
        t = t[:-2]
    elif t.upper().endswith("DR"):
        t, neg = t[:-2], True
    try:
        value = float(t)
    except ValueError:
        return None
    return -abs(value) if neg else value


def find_col(header, patterns, taken=()):
    for pat in patterns:
        for i, name in enumerate(header):
            if i not in taken and re.search(pat, name):
                return i
    return None


def parse_csv(text, flip=False):
    """Read a bank statement export. Returns (rows, columns found) or raises ValueError with a plain message."""
    text = text.lstrip("﻿")
    head = next((ln for ln in text.splitlines() if re.search(r"date|posted", ln.lower())), "")
    delimiter = max(",;\t", key=head.count)
    table = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]
    start = next((i for i, r in enumerate(table) if any(re.search(r"date|posted", c.lower()) for c in r)), None)
    if start is None:
        raise ValueError("No header row with a date column was found. The file needs column names such as Date, Description and Amount.")
    header = [c.strip().lower() for c in table[start]]
    c_date = find_col(header, (r"^date$", r"transaction date", r"posted", r"date"))
    c_desc = find_col(header, (r"description", r"payee", r"merchant", r"^name$", r"details", r"memo", r"narrat"), (c_date,))
    c_amt = find_col(header, (r"^amount$", r"amount"), (c_date, c_desc))
    c_out = find_col(header, (r"debit", r"withdraw", r"money out", r"paid out"), (c_date, c_desc, c_amt))
    c_in = find_col(header, (r"credit", r"deposit", r"money in", r"paid in"), (c_date, c_desc, c_amt, c_out))
    if c_desc is None or (c_amt is None and c_out is None and c_in is None):
        raise ValueError("Could not find description and amount columns. Found: " + ", ".join(table[start]))
    rows, seen, bad = [], {}, 0
    for r in table[start + 1:]:
        cell = lambda i: r[i] if i is not None and i < len(r) else ""
        date, desc = parse_date(cell(c_date)), cell(c_desc).strip()
        if c_amt is not None:
            amount = parse_amount(cell(c_amt))
        else:
            out, inc = parse_amount(cell(c_out)), parse_amount(cell(c_in))
            amount = None if out is None and inc is None else abs(inc or 0) - abs(out or 0)
        if not date or amount is None or amount == 0:
            bad += 1
            continue
        if flip:
            amount = -amount
        amount = round(amount, 2)
        key = "%s|%.2f|%s" % (date, amount, desc)
        seen[key] = seen.get(key, 0) + 1
        rows.append({"id": "csv-" + hashlib.sha1(("%s|%d" % (key, seen[key])).encode()).hexdigest()[:16],
                     "date": date, "desc": desc or "Payment", "amount": amount})
    cols = {"date": table[start][c_date], "description": table[start][c_desc]}
    if c_amt is not None:
        cols["amount"] = table[start][c_amt]
    else:
        cols["money out"], cols["money in"] = (table[start][c_out] if c_out is not None else "none"), (table[start][c_in] if c_in is not None else "none")
    return rows, cols, bad


def import_csv(text, flip, dry):
    rows, cols, bad = parse_csv(text, flip)
    with lock:
        docs = STORE["collections"]["transactions"]
        fresh = [r for r in rows if r["id"] not in docs]
        if not dry and fresh:
            for r in fresh:
                docs[r["id"]] = {"date": r["date"], "desc": r["desc"], "amount": r["amount"],
                                 "category": categorize(r["desc"], r["amount"]), "who": "", "source": "csv"}
            persist()
    preview = [dict(r, category=categorize(r["desc"], r["amount"])) for r in rows[:6]]
    return {"found": len(rows), "new": len(fresh), "duplicates": len(rows) - len(fresh), "unreadable": bad,
            "columns": cols, "preview": preview, "imported": 0 if dry else len(fresh)}



# ---------------------------------------------------------------- statement sync

class SyncError(Exception):
    pass


def pypdf_available():
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


def pick_folder():
    """Ask macOS for a folder with its own chooser window. Works because this server runs on the Mac being used."""
    if not shutil.which("osascript"):
        return {"error": "The folder chooser needs macOS. Type the folder path instead."}
    script = 'POSIX path of (choose folder with prompt "Choose the folder that holds your statement PDFs")'
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"cancelled": True}
    path = r.stdout.strip().rstrip("/") if r.returncode == 0 else ""
    if not path:
        return {"cancelled": True}
    return {"path": path}


def sync_settings():
    with lock:
        main = STORE["collections"]["settings"].get("main", {})
    cfg = dict(main.get("sync") or {})
    return cfg


def slog(msg, level="info"):
    """Add a line to the live log that the page shows while a sync runs."""
    with lock:
        SYNC["seq"] += 1
        SYNC["log"].append({"n": SYNC["seq"], "t": time.strftime("%H:%M:%S"), "l": level, "m": msg})
        del SYNC["log"][:-1500]


class Stopped(Exception):
    pass


def stop_sync():
    SYNC["cancel"].set()


def norm_key(date, amount, card):
    return (date, round(abs(float(amount)), 2), card)


def year_window(cfg):
    """The years to keep, from the sync settings. A blank end means no limit."""
    def num(x):
        try:
            return int(str(x).strip())
        except ValueError:
            return None
    return num(cfg.get("fromYear")), num(cfg.get("toYear"))


def merge_files(per_file):
    """One list of rows from several PDFs. A payment that shows up in two files (a monthly statement and a year-end summary)
    counts once: for each date, amount and card, keep the most copies any single file has."""
    best = {}
    for rows in per_file:
        mine = {}
        for r in rows:
            mine.setdefault(norm_key(r["date"], r["amount"], r["card"]), []).append(r)
        for k, group in mine.items():
            if len(group) > len(best.get(k, [])):
                best[k] = group
    return [r for group in best.values() for r in group]


DATE_SLACK_DAYS = 4      # the same payment is dated a day or two apart by the card (purchase date) and by the bank feed (posting date)


def take_match(have, card, amount, date):
    """If an unmatched existing payment has this card and amount on this date (or within a few days), use it up and say True."""
    dates = have.get((card, round(abs(float(amount)), 2)), [])
    if date in dates:
        dates.remove(date)
        return True
    day = dt.date.fromisoformat(date)
    best = None
    for d in dates:
        gap = abs((dt.date.fromisoformat(d) - day).days) if re.match(r"^\d{4}-\d\d-\d\d$", d) else 999
        if gap <= DATE_SLACK_DAYS and (best is None or gap < best[0]):
            best = (gap, d)
    if best:
        dates.remove(best[1])
        return True
    return False


def add_statement_rows(parsed, window):
    """Store rows from PDFs that the dashboard does not have yet. Returns (added, outside_years, duplicates)."""
    lo, hi = window
    parsed = merge_files(parsed)
    with lock:
        docs = STORE["collections"]["transactions"]
        have = {}
        for t in docs.values():
            have.setdefault((t.get("card", ""), round(abs(float(t.get("amount", 0))), 2)), []).append(t.get("date", ""))
        added = skipped = dupes = 0
        seen = {}
        unowned = {}
        for t in docs.values():
            if t.get("source") == "pdf" and not t.get("who"):
                unowned.setdefault((t.get("card", ""), round(abs(float(t.get("amount", 0))), 2), t.get("date", "")), []).append(t)
        for r in sorted(parsed, key=lambda r: r["date"]):
            year = int(r["date"][:4])
            if (lo and year < lo) or (hi and year > hi):
                skipped += 1
                continue
            if take_match(have, r["card"], r["amount"], r["date"]):
                dupes += 1
                waiting = unowned.get((r["card"], round(abs(r["amount"]), 2), r["date"]))
                if r.get("who") and waiting:
                    waiting.pop()["who"] = r["who"]        # a payment read before the person folders were used gets its owner now
                continue
            k = norm_key(r["date"], r["amount"], r["card"])
            seen[k] = seen.get(k, 0) + 1
            doc = {"date": r["date"], "desc": r["desc"], "amount": r["amount"], "card": r["card"], "who": r.get("who", ""), "source": "pdf"}
            if r.get("cash"):
                doc["cash"] = True
            cat = r.get("category")
            if not cat:
                cat = categorize(r["desc"], r["amount"] if r.get("cash") else -abs(r["amount"]))     # a deposit into a bank account is income
                if r["amount"] > 0 and not r.get("cash"):
                    doc["refund"] = True
            doc["category"] = cat
            docs["pdf-" + hashlib.sha1(("%s|%s|%s|%s|%d" % (r["date"], r["desc"], r["amount"], r["card"], seen[k])).encode()).hexdigest()[:16]] = doc
            added += 1
        return added, skipped, dupes


def drop_pdf_duplicates():
    """Remove payments an earlier PDF pass added that another source already had (the same payment, dated a day or two apart)."""
    with lock:
        docs = STORE["collections"]["transactions"]
        have = {}
        for t in docs.values():
            if t.get("source") != "pdf":
                have.setdefault((t.get("card", ""), round(abs(float(t.get("amount", 0))), 2)), []).append(t.get("date", ""))
        gone = [k for k, t in sorted(docs.items(), key=lambda kv: kv[1].get("date", "")) if t.get("source") == "pdf" and take_match(have, t.get("card", ""), t.get("amount", 0), t.get("date", ""))]
        for k in gone:
            del docs[k]
        return len(gone)


MAX_DEPTH = 12


def files_root(f, folders):
    return next((d for d in folders if d in f.parents), folders[0])


def walk_statements(root, depth=0):
    """Every PDF under root, depth first: a folder is searched all the way down before the next one starts. Hidden and linked folders are skipped."""
    try:
        entries = sorted(os.scandir(root), key=lambda e: e.name.lower())
    except OSError:
        return
    for e in entries:
        if e.is_dir(follow_symlinks=False) and not e.name.startswith(".") and depth < MAX_DEPTH:
            yield from walk_statements(Path(e.path), depth + 1)
        elif e.is_file() and e.name.lower().endswith(".pdf") and not e.name.startswith("."):
            yield Path(e.path)


def describe_path(root, f, members):
    """(person, label) from where a PDF sits: Statements/<person>/<year>/<bank>/file.pdf. The person is the first folder when it is one of the
    household's people; the label is the nearest folder that is not a year (the bank or card), which helps the reader pick a layout."""
    parts = f.relative_to(root).parts[:-1]
    names = {m.lower(): m for m in members}
    person = names.get(parts[0].lower(), "") if parts else ""
    label = next((p for p in reversed(parts) if not re.fullmatch(r"\d{4}", p) and p.lower() not in names), "")
    return person, label or f.parent.name


def run_sync(force=False):
    """One pass: read every new or changed PDF, add what is missing. Safe to call from any thread."""
    with lock:
        if SYNC["running"]:
            return
        SYNC.update(running=True, phase="Starting", done=0, total=0, started=dt.datetime.now().isoformat(timespec="milliseconds"))
        SYNC["cancel"].clear()
        SYNC["log"] = []
    status = {"lastRun": SYNC["started"], "added": 0, "pdfs": 0, "unreadable": [], "message": "", "ok": True}
    slog("Sync started%s" % (" (re-reading every statement)" if force else ""))
    try:
        cfg = sync_settings()
        local = (cfg.get("localFolder") or "").strip()
        if not local:
            raise SyncError("Choose the folder that holds your statement PDFs first.")
        p = Path(local).expanduser()
        if not p.is_dir():
            raise SyncError("The folder %s does not exist." % local)
        slog("Using the folder on this computer: %s" % p)
        folders = [p]
        if not pypdf_available():
            raise SyncError("Reading PDFs needs pypdf. Install it with: pip install pypdf")
        window = year_window(cfg)
        slog("Keeping transactions from %s to %s" % (window[0] or "the earliest year", window[1] or "the latest year"))
        files = [f for folder in folders for f in walk_statements(folder)]
        members = (STORE["collections"]["settings"].get("main") or {}).get("members") or []
        with lock:
            seen_files = STORE["sync"].setdefault("files", {})
            SYNC.update(phase="Reading statements", done=0, total=len(files))
        slog("Found %d statement PDF%s" % (len(files), "" if len(files) == 1 else "s"))
        parsed, pending = [], {}      # parsed: one list of rows per PDF
        for i, f in enumerate(files, 1):
            if SYNC["cancel"].is_set():
                raise Stopped()
            SYNC["done"] = i - 1
            time.sleep(float(os.environ.get("FINANCES_SYNC_DELAY", "0")))   # lets tests watch a slow sync
            sig = "%d-%d|%s-%s" % (f.stat().st_size, int(f.stat().st_mtime), window[0], window[1])      # a new year range means read it again
            person, label = describe_path(files_root(f, folders), f, members)
            name = "%s/%s" % (label, f.name)
            if seen_files.get(str(f)) == sig and not force:
                slog("[%d/%d] %s: unchanged, skipped" % (i, len(files), name))
                continue
            slog("[%d/%d] Reading %s" % (i, len(files), name))
            try:
                rows = statements.parse_pdf(f, label)
            except Exception as e:  # a damaged or protected file must not stop the rest
                status["unreadable"].append("%s (%s)" % (f.name, str(e)[:60]))
                slog("    could not read it: %s" % str(e)[:100], "error")
                continue
            if rows is None:
                status["unreadable"].append("%s (layout not recognised)" % f.name)
                slog("    layout not recognised, left alone", "warn")
            else:
                for r in rows:
                    if person:
                        r["who"] = person
                parsed.append(rows)
                slog("    %d transaction%s found" % (len(rows), "" if len(rows) == 1 else "s"))
            pending[str(f)] = sig
        SYNC.update(done=len(files), phase="Adding transactions")
        if SYNC["cancel"].is_set():
            raise Stopped()
        removed = drop_pdf_duplicates()
        if removed:
            slog("Removed %d transaction%s an earlier pass had added twice" % (removed, "" if removed == 1 else "s"), "warn")
        added, skipped, dupes = add_statement_rows(parsed, window)
        with lock:
            seen_files.update(pending)
        slog("%d new, %d already in the dashboard%s" % (added, dupes, (", %d outside the years you chose ignored" % skipped) if skipped else ""), "ok")
        status.update(added=added, pdfs=len(files))
        status["message"] = "%d new transaction%s from %d statement%s%s." % (added, "" if added == 1 else "s", len(files), "" if len(files) == 1 else "s",
                                                                          ("; %d outside the years you chose skipped" % skipped) if skipped else "")
    except Stopped:
        status.update(ok=False, message="Stopped. Nothing was added.")
        slog("Stopped by you. Nothing was added; statements already read will be read again next time.", "warn")
    except SyncError as e:
        status.update(ok=False, message=str(e))
        slog(str(e), "error")
    except Exception as e:
        status.update(ok=False, message="Sync failed: %s" % str(e)[:200])
        slog("Sync failed: %s" % str(e)[:200], "error")
    finally:
        slog("Finished: " + status["message"], "ok" if status["ok"] else "warn")
        with lock:
            STORE["sync"].update(status)
            SYNC.update(running=False, phase="")
            persist()


def auto_sync():
    """Check every minute whether a sync is due. It only runs while this computer is awake, which is the point."""
    time.sleep(20)
    while True:
        try:
            cfg = sync_settings()
            if cfg.get("auto", True) and (cfg.get("localFolder") or "").strip():
                every = max(5, int(cfg.get("everyMinutes") or 60)) * 60
                last = STORE.get("sync", {}).get("lastRun")
                due = True
                if last:
                    due = (dt.datetime.now() - dt.datetime.fromisoformat(last)).total_seconds() >= every
                if due:
                    run_sync()
        except Exception:
            pass
        time.sleep(60)


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "PersonalFinanceDashboard/1.0"

    def log_message(self, fmt, *args):
        if not CFG.get("quiet"):
            print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def send_bytes(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, obj):
        self.send_bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def allowed(self):
        """Home network only, and no writes from other websites."""
        try:
            ip = ipaddress.ip_address(self.client_address[0])
            if ip.version == 6 and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
        except ValueError:
            return False
        if not (ip.is_private or ip.is_loopback or ip.is_link_local):
            return False
        if self.command != "GET":
            origin = self.headers.get("Origin")
            if origin and origin.split("://", 1)[-1] != self.headers.get("Host", ""):
                return False
            if "application/json" not in self.headers.get("Content-Type", ""):
                return False
        return True

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return None
        try:
            body = json.loads(self.rfile.read(n))
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    def token(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "fd_session":
                return v
        return ""

    def user(self):
        return AUTH.session_user(self.token()) if AUTH else None

    def cookie(self, token, age):
        return {"Set-Cookie": "fd_session=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d%s" % (token, age, "; Secure" if CFG.get("https") else "")}

    def locked_out(self, public):
        """True (after answering) when sign-in is on and this request has no valid session."""
        if not (AUTH and AUTH.enabled()) or self.user():
            return False
        parts = self.route()
        if self.command == "GET" and parts in ([], ["index.html"], ["login"]):
            page = PUBLIC / "login.html"
            self.send_bytes(200, page.read_bytes(), MIME[".html"])
            return True
        if public:
            return False
        self.send_json(401, {"error": "Sign in first.", "signin": True})
        return True

    def route(self):
        return [p for p in self.path.split("?", 1)[0].split("/") if p]

    def do_GET(self):
        if not self.allowed():
            return self.send_json(403, {"error": "forbidden"})
        parts = self.route()
        public = parts in (["api", "session"], ["app.css"], ["favicon.svg"], ["favicon.ico"], ["icon-192.png"])
        if self.locked_out(public):
            return
        if parts == ["api", "session"]:
            return self.send_json(200, self.session_info())
        if parts == ["api", "data"]:
            with lock:
                return self.send_json(200, public_store())
        if parts == ["api", "sync", "log"]:
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:
                since = int((q.get("since") or ["0"])[0])
            except ValueError:
                since = 0
            with lock:
                lines = [x for x in SYNC["log"] if x["n"] > since]
                body = {"lines": lines, "last": SYNC["seq"], "reset": bool(SYNC["log"]) and since > SYNC["seq"],
                        "running": SYNC["running"], "phase": SYNC["phase"], "done": SYNC["done"], "total": SYNC["total"], "started": SYNC["started"],
                        "ok": STORE["sync"].get("ok"), "message": STORE["sync"].get("message", "")}
            return self.send_json(200, body)
        if parts == ["api", "export.csv"]:
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["date", "description", "amount", "category", "who", "account"])
            with lock:
                accounts = STORE["collections"]["accounts"]
                for t in sorted(STORE["collections"]["transactions"].values(), key=lambda t: t.get("date", "")):
                    w.writerow([t.get("date", ""), t.get("desc", ""), t.get("amount", 0), t.get("category", ""), t.get("who", ""),
                                accounts.get(t.get("account", ""), {}).get("name", "")])
            return self.send_bytes(200, out.getvalue().encode("utf-8"), "text/csv; charset=utf-8",
                                   {"Content-Disposition": 'attachment; filename="payments.csv"'})
        if parts == ["api", "backup.json"]:
            with lock:
                body = json.dumps({"version": STORE["version"], "collections": STORE["collections"]}, indent=1, ensure_ascii=False).encode("utf-8")
            return self.send_bytes(200, body, "application/json; charset=utf-8",
                                   {"Content-Disposition": 'attachment; filename="finance-backup.json"'})
        name = "favicon.svg" if parts == ["favicon.ico"] else parts[0] if parts else "index.html"
        target = PUBLIC / name
        if len(parts) <= 1 and target.suffix in MIME and target.is_file() and target.parent == PUBLIC:
            return self.send_bytes(200, target.read_bytes(), MIME[target.suffix])
        self.send_json(404, {"error": "not found"})

    def session_info(self):
        on, user = AUTH.enabled(), self.user()
        info = {"required": on, "user": user, "minLength": auth.MIN_LENGTH}
        if user or not on:
            info["users"] = AUTH.names()
        return info

    def account(self, parts, body):
        """Sign-in, sign-out and password changes. Raises auth.AuthError with a message that is safe to show."""
        user, ip = self.user(), self.client_address[0]
        if parts == ["api", "login"]:
            token, name = AUTH.login(str(body.get("name", "")), str(body.get("password", "")), ip)
            return self.send_bytes(200, json.dumps({"user": name}).encode(), "application/json; charset=utf-8", self.cookie(token, auth.SESSION_DAYS * 86400))
        if parts == ["api", "logout"]:
            AUTH.logout(self.token())
            return self.send_bytes(200, b'{"ok": true}', "application/json; charset=utf-8", self.cookie("", 0))
        if parts == ["api", "account", "setup"]:
            name, password = str(body.get("name", "")).strip(), body.get("password")
            if AUTH.names() and not user:
                return self.send_json(401, {"error": "Sign in first.", "signin": True})
            if AUTH._key(name) in AUTH.users and AUTH.users[AUTH._key(name)]:
                raise auth.AuthError("%s already has a password. Use Change password instead." % name)
            first = not AUTH.names()
            AUTH.set_password(name, password, require=first or AUTH.enabled())
            if first:
                token, who = AUTH.login(name, password, ip)
                return self.send_bytes(200, json.dumps({"user": who}).encode(), "application/json; charset=utf-8", self.cookie(token, auth.SESSION_DAYS * 86400))
            return self.send_json(200, {"ok": True})
        if not user:
            return self.send_json(401, {"error": "Sign in first.", "signin": True})
        if parts == ["api", "account", "password"]:
            AUTH.change_password(user, str(body.get("current", "")), body.get("new"), keep_token=self.token())
            return self.send_json(200, {"ok": True})
        if parts == ["api", "account", "require"]:
            if not body.get("on"):
                if not AUTH.verify(user, str(body.get("password", ""))):
                    raise auth.AuthError("Type your password to turn sign-in off.")
            AUTH.set_required(bool(body.get("on")))
            return self.send_json(200, {"ok": True, "required": AUTH.enabled()})
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self.allowed():
            return self.send_json(403, {"error": "forbidden"})
        parts, body = self.route(), self.read_body()
        if self.locked_out(parts in (["api", "login"], ["api", "account", "setup"], ["api", "logout"])):
            return
        if body is None:
            return self.send_json(400, {"error": "The request needs a JSON object."})
        try:
            if parts[:2] in (["api", "login"], ["api", "logout"]) or parts[:2] == ["api", "account"]:
                return self.account(parts, body)
            if parts == ["api", "batch"]:
                return self.batch(body)
            if parts == ["api", "sync", "stop"]:
                stop_sync()
                return self.send_json(200, {"stopping": True})
            if parts == ["api", "sync", "pick"]:
                return self.send_json(200, pick_folder())
            if parts == ["api", "sync"]:
                if SYNC["running"]:
                    return self.send_json(200, {"running": True})
                threading.Thread(target=run_sync, kwargs={"force": bool(body.get("force"))}, daemon=True).start()
                return self.send_json(200, {"started": True})
            if parts == ["api", "import", "csv"]:
                if not isinstance(body.get("text"), str) or not body["text"].strip():
                    return self.send_json(400, {"error": "The file is empty."})
                return self.send_json(200, import_csv(body["text"], bool(body.get("flip")), bool(body.get("dry"))))
        except ValueError as e:
            return self.send_json(400, {"error": str(e)})
        self.send_json(404, {"error": "not found"})

    def batch(self, body):
        writes = body.get("writes")
        if not isinstance(writes, list) or len(writes) > 5000:
            return self.send_json(400, {"error": "writes must be a list of at most 5000 entries"})
        for w in writes:
            if not (isinstance(w, dict) and w.get("col") in COLLECTIONS and ID_RE.match(str(w.get("id", "")))
                    and w.get("op") in ("set", "update", "delete") and (w["op"] == "delete" or isinstance(w.get("data"), dict))):
                return self.send_json(400, {"error": "invalid write in batch"})
        with lock:
            for w in writes:
                docs = STORE["collections"][w["col"]]
                if w["op"] == "set":
                    docs[w["id"]] = w["data"]
                elif w["op"] == "update":
                    if w["id"] in docs:
                        docs[w["id"]].update(w["data"])
                else:
                    docs.pop(w["id"], None)
            persist()
            self.send_json(200, {"version": STORE["version"]})

    def write(self, mode):
        if not self.allowed():
            return self.send_json(403, {"error": "forbidden"})
        parts = self.route()
        if self.locked_out(False):
            return
        if not (len(parts) == 4 and parts[:2] == ["api", "doc"] and parts[2] in COLLECTIONS and ID_RE.match(parts[3])):
            return self.send_json(404, {"error": "not found"})
        col, doc_id = parts[2], parts[3]
        body = None
        if mode != "delete":
            body = self.read_body()
            if body is None:
                return self.send_json(400, {"error": "The request needs a JSON object."})
        with lock:
            docs = STORE["collections"][col]
            if mode == "set":
                docs[doc_id] = body
            elif mode == "update":
                if doc_id not in docs:
                    return self.send_json(404, {"error": "no such entry"})
                docs[doc_id].update(body)
            else:
                docs.pop(doc_id, None)
            persist()
            self.send_json(200, {"version": STORE["version"]})

    def do_PUT(self):
        self.write("set")

    def do_PATCH(self):
        self.write("update")

    def do_DELETE(self):
        self.write("delete")


# ---------------------------------------------------------------- network name

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def advertise(name, port):
    """Announce <name> on the local network (mDNS) and again whenever this machine's address changes."""
    if shutil.which("dns-sd"):
        cmd = lambda ip: ["dns-sd", "-P", "Personal Finance Dashboard", "_http._tcp", "local", str(port), name, ip]
    elif shutil.which("avahi-publish"):
        cmd = lambda ip: ["avahi-publish", "-a", "-R", name, ip]
    else:
        print("no mDNS tool found (dns-sd or avahi-publish); reach the page by IP address instead", flush=True)
        return
    proc, current = None, None
    while True:
        ip = lan_ip()
        if ip != current or (proc and proc.poll() is not None):
            if proc and proc.poll() is None:
                proc.terminate()
            proc = subprocess.Popen(cmd(ip), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if ip else None
            if ip:
                print("advertising %s:%d at %s" % (name, port, ip), flush=True)
            current = ip
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser(description="Serve the Personal Finance Dashboard on your home network.")
    ap.add_argument("--port", type=int, default=int(os.environ.get("FINANCES_PORT", "8770")))
    ap.add_argument("--bind", default=os.environ.get("FINANCES_BIND", "0.0.0.0"), help="address to listen on; 127.0.0.1 keeps it to this computer")
    ap.add_argument("--name", default=os.environ.get("FINANCES_HOST", "finances.local"), help='network name to announce; "" turns announcing off')
    ap.add_argument("--data", default=os.environ.get("FINANCES_DATA", str(HERE / "data")), help="folder that holds data.json")
    ap.add_argument("--cert", default=os.environ.get("FINANCES_CERT", ""), help="TLS certificate (PEM). With --key, the page is served over https")
    ap.add_argument("--key", default=os.environ.get("FINANCES_KEY", ""), help="TLS private key (PEM)")
    ap.add_argument("--reset-password", metavar="NAME", help="set a new sign-in password for NAME, then exit (for a forgotten password)")
    ap.add_argument("--empty", action="store_true", help="start with no example data")
    ap.add_argument("--quiet", action="store_true", help="do not log each request")
    args = ap.parse_args()
    CFG.update(data=Path(args.data).resolve(), empty=args.empty, quiet=args.quiet)
    global AUTH
    AUTH = auth.Auth(CFG["data"])
    if args.reset_password:
        import getpass
        pw = getpass.getpass("New password for %s: " % args.reset_password)
        if pw != getpass.getpass("Again: "):
            sys.exit("The two passwords differ. Nothing changed.")
        AUTH.set_password(args.reset_password, pw, require=AUTH.required or True)
        print("Password set for %s." % args.reset_password)
        return
    CFG["https"] = bool(args.cert and args.key)
    STORE.update(load())
    if not data_file().exists():
        with lock:
            persist()
    threading.Thread(target=auto_sync, daemon=True).start()
    if args.name:
        threading.Thread(target=advertise, args=(args.name, args.port), daemon=True).start()
    scheme = "https" if args.cert and args.key else "http"
    print("serving on %s://%s:%d/  data in %s" % (scheme, "localhost" if args.bind in ("0.0.0.0", "127.0.0.1") else args.bind, args.port, CFG["data"]), flush=True)
    try:
        httpd = ThreadingHTTPServer((args.bind, args.port), Handler)
        if scheme == "https":
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(args.cert, args.key)
            plain_finish = httpd.finish_request

            def finish_request(request, client_address):
                """Do the TLS handshake on the connection's own thread, so an idle browser connection cannot hold up everyone else."""
                try:
                    request.settimeout(10)
                    request = ctx.wrap_socket(request, server_side=True)
                    request.settimeout(None)
                except (OSError, ssl.SSLError):
                    return
                plain_finish(request, client_address)
            httpd.finish_request = finish_request
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
