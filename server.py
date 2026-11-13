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
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import statements

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public"
COLLECTIONS = ("settings", "transactions", "budgets", "recurring", "accounts", "rules")
ID_RE = re.compile(r"^[A-Za-z0-9_.~:@+-]{1,200}$")
MAX_BODY = 8 * 1024 * 1024
MIME = {".png": "image/png", ".ico": "image/svg+xml", ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json"}

lock = threading.RLock()
SYNC = {"running": False}
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
    sync.update(running=SYNC["running"], rclone=bool(find_rclone()), pypdf=pypdf_available())
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


def find_rclone():
    """rclone is usually in Homebrew's folder, which a login service does not have on its PATH."""
    return shutil.which("rclone", path=os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin")


def pypdf_available():
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


def sync_settings():
    with lock:
        main = STORE["collections"]["settings"].get("main", {})
    cfg = dict(main.get("sync") or {})
    cfg["fiscalYear"] = main.get("fiscalYear")
    return cfg


def drive_pull(cfg, dest):
    """Copy the PDFs from a Google Drive folder with rclone. The folder id comes from the link; rclone holds the sign-in."""
    link = (cfg.get("driveLink") or "").strip()
    if not link:
        return
    m = re.search(r"/folders/([A-Za-z0-9_-]+)|[?&]id=([A-Za-z0-9_-]+)", link)
    if not m:
        raise SyncError("That does not look like a Google Drive folder link.")
    folder = m.group(1) or m.group(2)
    remote = (cfg.get("rcloneRemote") or "gdrive").strip()
    rclone = find_rclone()
    if not rclone:
        raise SyncError("rclone is not installed. Install it (brew install rclone) or fill in a local folder instead.")
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [rclone, "copy", "%s,root_folder_id=%s:" % (remote, folder), str(dest), "--include", "*.pdf", "--drive-acknowledge-abuse"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired:
        raise SyncError("Google Drive took too long to answer. It will try again at the next sync.")
    if r.returncode:
        err = (r.stderr or "").strip().splitlines()[-1:] or ["rclone failed"]
        if "didn't find section" in r.stderr or "not found in config" in r.stderr:
            raise SyncError("Sign in to Google Drive once: run  rclone config create %s drive scope=drive.readonly  and approve in the browser." % remote)
        raise SyncError("Google Drive said: " + err[0][:200])


def norm_key(date, amount, card):
    return (date, round(abs(float(amount)), 2), card)


def add_statement_rows(parsed, fiscal):
    """Store rows from PDFs that the dashboard does not have yet. Returns (added, skipped_outside_year)."""
    with lock:
        docs = STORE["collections"]["transactions"]
        have = {}
        for t in docs.values():
            k = norm_key(t.get("date", ""), t.get("amount", 0), t.get("card", ""))
            have[k] = have.get(k, 0) + 1
        added = skipped = 0
        seen = {}
        for r in parsed:
            if fiscal and not r["date"].startswith(str(fiscal)):
                skipped += 1
                continue
            k = norm_key(r["date"], r["amount"], r["card"])
            if have.get(k, 0) > 0:
                have[k] -= 1
                continue
            seen[k] = seen.get(k, 0) + 1
            doc = {"date": r["date"], "desc": r["desc"], "amount": r["amount"], "card": r["card"], "who": "", "source": "pdf"}
            if r.get("cash"):
                doc["cash"] = True
            cat = r.get("category")
            if not cat:
                cat = categorize(r["desc"], -abs(r["amount"]))
                if r["amount"] > 0 and not r.get("cash"):
                    doc["refund"] = True
            doc["category"] = cat
            docs["pdf-" + hashlib.sha1(("%s|%s|%s|%s|%d" % (r["date"], r["desc"], r["amount"], r["card"], seen[k])).encode()).hexdigest()[:16]] = doc
            added += 1
        return added, skipped


def run_sync(force=False):
    """One pass: pull from Drive, read every new or changed PDF, add what is missing. Safe to call from any thread."""
    with lock:
        if SYNC["running"]:
            return
        SYNC["running"] = True
    status = {"lastRun": dt.datetime.now().isoformat(timespec="seconds"), "added": 0, "pdfs": 0, "unreadable": [], "message": "", "ok": True}
    try:
        cfg = sync_settings()
        folders = []
        if (cfg.get("driveLink") or "").strip():
            dest = CFG["data"] / "statements"
            drive_pull(cfg, dest)
            folders.append(dest)
        local = (cfg.get("localFolder") or "").strip()
        if local:
            p = Path(local).expanduser()
            if not p.is_dir():
                raise SyncError("The local folder %s does not exist." % local)
            folders.append(p)
        if not folders:
            raise SyncError("Add a Google Drive folder link or a local folder first.")
        if not pypdf_available():
            raise SyncError("Reading PDFs needs pypdf. Install it with: pip install pypdf")
        with lock:
            seen_files = STORE["sync"].setdefault("files", {})
        parsed, total = [], 0
        for folder in folders:
            for f in sorted(folder.rglob("*.pdf")):
                total += 1
                sig = "%d-%d" % (f.stat().st_size, int(f.stat().st_mtime))
                if seen_files.get(str(f)) == sig and not force:
                    continue
                try:
                    rows = statements.parse_pdf(f, f.parent.name)
                except Exception as e:  # a damaged or protected file must not stop the rest
                    status["unreadable"].append("%s (%s)" % (f.name, str(e)[:60]))
                    continue
                if rows is None:
                    status["unreadable"].append("%s (layout not recognised)" % f.name)
                else:
                    parsed.extend(rows)
                seen_files[str(f)] = sig
        added, skipped = add_statement_rows(parsed, cfg.get("fiscalYear"))
        status.update(added=added, pdfs=total)
        status["message"] = "%d new payment%s from %d statement%s%s." % (added, "" if added == 1 else "s", total, "" if total == 1 else "s",
                                                                          ("; %d outside FY%s skipped" % (skipped, cfg["fiscalYear"])) if skipped else "")
    except SyncError as e:
        status.update(ok=False, message=str(e))
    except Exception as e:
        status.update(ok=False, message="Sync failed: %s" % str(e)[:200])
    finally:
        with lock:
            STORE["sync"].update(status)
            SYNC["running"] = False
            persist()


def auto_sync():
    """Check every minute whether a sync is due. It only runs while this computer is awake, which is the point."""
    time.sleep(20)
    while True:
        try:
            cfg = sync_settings()
            if cfg.get("auto", True) and ((cfg.get("driveLink") or "").strip() or (cfg.get("localFolder") or "").strip()):
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

    def route(self):
        return [p for p in self.path.split("?", 1)[0].split("/") if p]

    def do_GET(self):
        if not self.allowed():
            return self.send_json(403, {"error": "forbidden"})
        parts = self.route()
        if parts == ["api", "data"]:
            with lock:
                return self.send_json(200, public_store())
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

    def do_POST(self):
        if not self.allowed():
            return self.send_json(403, {"error": "forbidden"})
        parts, body = self.route(), self.read_body()
        if body is None:
            return self.send_json(400, {"error": "The request needs a JSON object."})
        try:
            if parts == ["api", "batch"]:
                return self.batch(body)
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
    ap.add_argument("--empty", action="store_true", help="start with no example data")
    ap.add_argument("--quiet", action="store_true", help="do not log each request")
    args = ap.parse_args()
    CFG.update(data=Path(args.data).resolve(), empty=args.empty, quiet=args.quiet)
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
