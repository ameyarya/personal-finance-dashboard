#!/usr/bin/env python3
"""Personal Finance Dashboard: a self-hosted household money page.

Run `python3 server.py` and open http://localhost:8770/ (or http://finances.local:8770/
from any device on the same network). Standard library only, no accounts, no cloud.

Everything is stored in one JSON file under ./data. Only devices on the local
network are answered, and other websites cannot write to it.
"""
import argparse
import base64
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
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public"
COLLECTIONS = ("settings", "transactions", "budgets", "pots", "recurring", "accounts", "rules")
ID_RE = re.compile(r"^[A-Za-z0-9_.~:@+-]{1,200}$")
MAX_BODY = 8 * 1024 * 1024
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json"}

lock = threading.RLock()
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
        "pots": {"s-emergency": {"name": "Emergency fund", "target": 15000, "saved": 9600, "sample": True},
                 "s-trip": {"name": "Summer trip", "target": 3000, "saved": 1150, "sample": True},
                 "s-laptop": {"name": "New laptop", "target": 1800, "saved": 1080, "sample": True}},
        "recurring": {rid: {"name": name, "amount": amount, "day": day, "category": cat, "sample": True}
                      for rid, name, amount, day, cat, who in RECURRING},
        "accounts": {}, "rules": {},
    }


# ---------------------------------------------------------------- storage

def data_file():
    return CFG["data"] / "data.json"


def secrets_file():
    return CFG["data"] / "secrets.json"


def load():
    CFG["data"].mkdir(parents=True, exist_ok=True)
    legacy = HERE / "data.json"
    if not data_file().exists() and legacy.exists() and CFG["data"] == HERE / "data":
        shutil.move(str(legacy), str(data_file()))
    if data_file().exists():
        store = json.loads(data_file().read_text("utf-8"))
    else:
        store = {"version": 0, "collections": {} if CFG["empty"] else make_sample(today())}
    store.setdefault("bank", {})
    for name in COLLECTIONS:
        store["collections"].setdefault(name, {})
    return store


def persist():
    STORE["version"] += 1
    tmp = data_file().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(STORE, indent=1, ensure_ascii=False), "utf-8")
    os.replace(tmp, data_file())


def public_store():
    bank = dict(STORE.get("bank", {}))
    bank["connected"] = secrets_file().exists()
    return {"version": STORE["version"], "collections": STORE["collections"], "bank": bank}


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


# ---------------------------------------------------------------- bank sync (SimpleFIN)

class BankError(Exception):
    pass


def bank_request(url, method="GET"):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" and not os.environ.get("FINANCES_ALLOW_HTTP_BANK"):
        raise BankError("The bank bridge address must use https.")
    host = parts.hostname + (":%d" % parts.port if parts.port else "")
    req = urllib.request.Request(urllib.parse.urlunsplit((parts.scheme, host, parts.path, parts.query, "")), method=method,
                                 headers={"User-Agent": "personal-finance-dashboard", "Content-Length": "0"} if method == "POST" else {"User-Agent": "personal-finance-dashboard"})
    if parts.username:
        token = base64.b64encode(("%s:%s" % (urllib.parse.unquote(parts.username), urllib.parse.unquote(parts.password or ""))).encode()).decode()
        req.add_header("Authorization", "Basic " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise BankError("The bridge refused the request (403). The token may already have been used or access was revoked. Create a new setup token.")
        if e.code == 402:
            raise BankError("The bridge says payment is required (402). Check your SimpleFIN subscription.")
        raise BankError("The bridge answered with error %d." % e.code)
    except (urllib.error.URLError, OSError) as e:
        raise BankError("Could not reach the bridge: %s" % getattr(e, "reason", e))


def bank_connect(setup_token):
    try:
        claim = base64.b64decode(setup_token.strip() + "=" * (-len(setup_token.strip()) % 4)).decode("utf-8").strip()
    except Exception:
        raise BankError("That does not look like a SimpleFIN setup token.")
    if not re.match(r"^https?://", claim):
        raise BankError("That does not look like a SimpleFIN setup token.")
    access = bank_request(claim, "POST").strip()
    if not re.match(r"^https?://", access):
        raise BankError("The bridge did not return an access address.")
    secrets_file().write_text(json.dumps({"accessUrl": access, "connectedAt": dt.datetime.now().isoformat(timespec="seconds")}), "utf-8")
    os.chmod(secrets_file(), 0o600)
    return bank_sync(first=True)


def bank_sync(first=False):
    if not secrets_file().exists():
        raise BankError("No bank connection is set up.")
    access = json.loads(secrets_file().read_text("utf-8"))["accessUrl"].rstrip("/")
    with lock:
        last = STORE.get("bank", {}).get("lastSyncEpoch")
    now = int(time.time())
    start = now - 85 * 86400 if first or not last else max(last - 5 * 86400, now - 85 * 86400)
    payload = json.loads(bank_request("%s/accounts?version=2&start-date=%d" % (access, start)))
    conns = {c.get("conn_id"): c.get("name") or c.get("org_name") for c in payload.get("connections", [])}
    errors = [e.get("msg", "") for e in payload.get("errlist", []) if isinstance(e, dict)] or [str(e) for e in payload.get("errors", [])]
    added = 0
    with lock:
        accounts, txs = STORE["collections"]["accounts"], STORE["collections"]["transactions"]
        for acct in payload.get("accounts", []):
            aid = "sf-" + slug(acct.get("id", ""))
            org = conns.get(acct.get("conn_id")) or (acct.get("org") or {}).get("name") or ""
            old = accounts.get(aid, {})
            accounts[aid] = {"name": acct.get("name", "Account"), "org": org, "currency": acct.get("currency", ""),
                             "balance": float(acct.get("balance", 0) or 0),
                             "balanceDate": dt.date.fromtimestamp(int(acct.get("balance-date", now) or now)).isoformat(),
                             "source": "simplefin", "include": old.get("include", True)}
            for t in acct.get("transactions", []) or []:
                stamp = int(t.get("transacted_at") or t.get("posted") or 0)
                if t.get("pending") or not stamp:
                    continue
                tid = "sf-%s-%s" % (slug(acct.get("id", ""), 40), slug(t.get("id", ""), 80))
                amount, desc = round(float(t.get("amount", 0) or 0), 2), (t.get("description") or "Payment").strip()
                date = dt.date.fromtimestamp(stamp).isoformat()
                if tid in txs:
                    txs[tid].update({"date": date, "amount": amount})
                else:
                    txs[tid] = {"date": date, "desc": desc, "amount": amount, "category": categorize(desc, amount),
                                "who": "", "account": aid, "source": "simplefin"}
                    added += 1
        STORE["bank"] = {"lastSync": dt.datetime.now().isoformat(timespec="seconds"), "lastSyncEpoch": now, "errors": errors[:10]}
        persist()
    return {"accounts": len(payload.get("accounts", [])), "added": added, "errors": errors[:10]}


def bank_disconnect():
    if secrets_file().exists():
        secrets_file().unlink()
    with lock:
        STORE["bank"] = {}
        persist()


def auto_sync():
    """Refresh from the bank about once a day. The bridge allows roughly 24 requests a day."""
    while True:
        time.sleep(1800 + random.randint(0, 600))
        try:
            with lock:
                last = STORE.get("bank", {}).get("lastSyncEpoch", 0)
            if secrets_file().exists() and time.time() - last > 20 * 3600:
                bank_sync()
        except Exception as e:  # keep the loop alive; the next attempt may succeed
            with lock:
                STORE.setdefault("bank", {})["errors"] = [str(e)]
                persist()


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
        name = parts[0] if parts else "index.html"
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
            if parts == ["api", "import", "csv"]:
                if not isinstance(body.get("text"), str) or not body["text"].strip():
                    return self.send_json(400, {"error": "The file is empty."})
                return self.send_json(200, import_csv(body["text"], bool(body.get("flip")), bool(body.get("dry"))))
            if parts == ["api", "bank", "connect"]:
                return self.send_json(200, bank_connect(str(body.get("setupToken", ""))))
            if parts == ["api", "bank", "sync"]:
                with lock:
                    last = STORE.get("bank", {}).get("lastSyncEpoch", 0)
                if time.time() - last < 60:
                    return self.send_json(429, {"error": "Synced less than a minute ago. The bridge limits how often it can be asked."})
                return self.send_json(200, bank_sync())
            if parts == ["api", "bank", "disconnect"]:
                bank_disconnect()
                return self.send_json(200, {"ok": True})
        except ValueError as e:
            return self.send_json(400, {"error": str(e)})
        except BankError as e:
            return self.send_json(502, {"error": str(e)})
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
                print("advertising http://%s:%d/ at %s" % (name, port, ip), flush=True)
            current = ip
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser(description="Serve the Personal Finance Dashboard on your home network.")
    ap.add_argument("--port", type=int, default=int(os.environ.get("FINANCES_PORT", "8770")))
    ap.add_argument("--bind", default=os.environ.get("FINANCES_BIND", "0.0.0.0"), help="address to listen on; 127.0.0.1 keeps it to this computer")
    ap.add_argument("--name", default=os.environ.get("FINANCES_HOST", "finances.local"), help='network name to announce; "" turns announcing off')
    ap.add_argument("--data", default=os.environ.get("FINANCES_DATA", str(HERE / "data")), help="folder that holds data.json")
    ap.add_argument("--empty", action="store_true", help="start with no example data")
    ap.add_argument("--quiet", action="store_true", help="do not log each request")
    args = ap.parse_args()
    CFG.update(data=Path(args.data).resolve(), empty=args.empty, quiet=args.quiet)
    STORE.update(load())
    if not data_file().exists():
        with lock:
            persist()
    if args.name:
        threading.Thread(target=advertise, args=(args.name, args.port), daemon=True).start()
    threading.Thread(target=auto_sync, daemon=True).start()
    print("serving on http://%s:%d/  data in %s" % ("localhost" if args.bind in ("0.0.0.0", "127.0.0.1") else args.bind, args.port, CFG["data"]), flush=True)
    try:
        ThreadingHTTPServer((args.bind, args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
