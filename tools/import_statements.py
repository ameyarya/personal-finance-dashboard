#!/usr/bin/env python3
"""Load one financial year of statements into a running dashboard.

Two kinds of input, both pipe-separated text, one row per line (descriptions may contain commas):
  --cards         date|description|amount|source-category|card      credit cards, positive = spending
  --cash          m/d/yyyy|description|type|amount                   a cash account, positive = money in
  --extra-cash    same layout, another cash account (repeat for each one)
Cash rows count towards the balance; card rows do not (cards are settled by the card payments in the cash account).

Everything already in the dashboard's data is replaced (the example data and any earlier import go).
Card payments and moves between your own accounts are filed as Transfer so they are not counted twice.
Refunds are kept as refunds so they reduce spending instead of counting as income.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.request

# Generic defaults. Put your own merchants, payroll names and account names in a rules file
# (see --rules and tools/rules.example.json); it is read from disk and stays out of git.
RULES = [
    (r"RENT|MORTGAGE|HOA", "Housing"),
    (r"GROCER|SUPERMARKET|WHOLE ?FOODS|TRADER JOE|SAFEWAY|KROGER|ALDI|COSTCO WHSE", "Groceries"),
    (r"ELECTRIC|WATER|GAS CO|UTILIT|INTERNET|COMCAST|XFINITY|VERIZON|AT&T|T-MOBILE", "Utilities"),
    (r"INSURANCE", "Insurance"),
    (r"PET", "Pets"),
    (r"AIRLINE|HOTEL|MOTEL|AIRBNB", "Travel"),
    (r"UBER|LYFT|SHELL|CHEVRON|PARKING|TOLL|CHARGING", "Transport"),
    (r"PHARMACY|WALGREENS|CVS|CLINIC|DENTAL|MEDICAL", "Health"),
    (r"NETFLIX|SPOTIFY|HULU|CINEMA|THEATER|SUBSCRIPTION", "Fun"),
    (r"DOORDASH|GRUBHUB|RESTAURANT|CAFE|COFFEE|PIZZA", "Dining"),
]
SHOPPING = r"WALMART|TARGET|AMAZON|DOLLAR TREE"
FALLBACK = {"Dining": "Dining", "Food/Drink": "Dining", "Food & Drink": "Dining", "Shopping": "Shopping", "Merchandise": "Shopping",
            "Personal Care": "Health", "Health": "Health", "Entertainment": "Fun", "Travel": "Travel", "Pets": "Pets",
            "Insurance/Financial": "Insurance", "Auto/Transportation": "Transport", "Automotive": "Transport", "Bills/Utilities": "Utilities"}
CARD_PAYMENT = r"PAYMENT THANK YOU|AUTOPAY|AUTOMATIC PAYMENT|DIRECTPAY"
CASH_TRANSFER = r"CREDIT CARD|CRCARDPMT|E-?PAYMENT|JOINT|TRANSFER"
INCOME = r"PAYROLL|DIRECT DEP|INTEREST|TAX REFUND|SALARY"
CASH_RULES = [(r"PERSONAL INVESTMENT|BROKERAGE", "Savings", None)]   # regex, category, description (None keeps the original)
WHO = {}   # ownership label in the reconciliation file -> name shown in "Who"


def load_rules(path):
    """Add the rules in a JSON file in front of the defaults. Anything the file leaves out keeps its default."""
    global RULES, SHOPPING, CARD_PAYMENT, CASH_TRANSFER, INCOME, CASH_RULES, WHO
    r = json.load(open(path))
    RULES = [tuple(x) for x in r.get("rules", [])] + RULES
    SHOPPING = r.get("shopping", SHOPPING)
    CARD_PAYMENT = r.get("card_payment", CARD_PAYMENT)
    CASH_TRANSFER = r.get("cash_transfer", CASH_TRANSFER)
    INCOME = r.get("income", INCOME)
    CASH_RULES = [tuple(x) for x in r.get("cash_rules", [])] + CASH_RULES
    WHO = r.get("who", WHO)


def categorize(desc, source_cat):
    up = desc.upper()
    for pattern, cat in RULES:
        if re.search(pattern, up):
            return cat
    if re.search(SHOPPING, up):
        return "Shopping"
    return FALLBACK.get(source_cat, "Other")


def doc_id(*parts):
    return "fy-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                yield [c.replace("\\", "").strip() for c in line.split("|")]


def card_rows(path, year):
    seen = {}
    for date, desc, amount, source_cat, card in read_rows(path):
        if not date.startswith(str(year)):
            continue
        amount = float(amount)
        if re.search(CARD_PAYMENT, desc.upper()):
            row = {"category": "Transfer", "amount": abs(amount), "desc": "Card payment"}
        elif amount < 0:   # a credit or refund from the merchant
            row = {"category": categorize(desc, source_cat), "amount": abs(amount), "refund": True, "desc": desc}
        else:
            row = {"category": categorize(desc, source_cat), "amount": -amount, "desc": desc}
        key = (date, desc, amount, card)
        seen[key] = seen.get(key, 0) + 1
        row.update(date=date, card=card, who="", source="statement", id=doc_id(*key, seen[key]))
        yield row


def cash_rows(path, year, card_name):
    seen = {}
    for raw_date, desc, kind, amount in read_rows(path):
        date = dt.datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
        if not date.startswith(str(year)):
            continue
        amount, up = float(amount), desc.upper()
        out = {"desc": desc, "amount": amount}
        rule = next((r for r in CASH_RULES if re.search(r[0], up)), None)
        if re.search(CASH_TRANSFER, up) or (up.startswith("VENMO") and abs(amount) >= 1000):
            out.update(category="Transfer")
        elif rule and rule[1] == "Savings":
            out.update(category="Savings")
        elif re.search(INCOME, up):
            out.update(category="Income")
        elif amount > 0:   # reimbursements and cash-outs: keep them as refunds so they reduce spending
            out.update(category="Other", refund=True)
        elif rule:
            out.update(category=rule[1], **({"desc": rule[2]} if rule[2] else {}))
        else:
            out.update(category="Other", desc=re.sub(r"-\d{6,}.*$", "", desc))
        key = (date, desc, amount)
        seen[key] = seen.get(key, 0) + 1
        out.update(date=date, card=card_name, cash=True, who="", source="statement", id=doc_id(*key, seen[key], "cash", card_name))
        yield out


def enrich(rows, path):
    """Copy who-paid and notes from an earlier reconciliation (project-data.json) onto matching card rows."""
    data = json.load(open(path))
    key = lambda date, desc, amount, card: (date, re.sub(r"\s+", " ", desc).upper(), round(abs(float(amount)), 2), card)
    known = {}
    for t in data.get("transactions", []):
        known[key(t["date"], t["description"], t["amount"], t["source"])] = t
    hit = 0
    for r in rows:
        if r.get("cash"):
            continue
        t = known.get(key(r["date"], r["desc"], r["amount"], r["card"]))
        if not t:
            continue
        hit += 1
        r["who"] = WHO.get(t.get("ownership"), "")
        notes = [n for n in (t.get("special"), t.get("note")) if n]
        if notes:
            r["note"] = "; ".join(notes)
    return hit


def call(server, method, path, body):
    req = urllib.request.Request(server + path, data=json.dumps(body).encode(), method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cards", required=True)
    ap.add_argument("--cash", required=True)
    ap.add_argument("--cash-name", default="Cash account")
    ap.add_argument("--extra-cash", action="append", default=[], metavar="FILE=NAME", help="another cash account, e.g. savings.psv=Savings")
    ap.add_argument("--opening", type=float, default=0.0, help="total cash in all cash accounts on 1 January")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--server", default="http://localhost:8770")
    ap.add_argument("--enrich", metavar="JSON", help="project-data.json from an earlier reconciliation: adds who-paid and notes")
    ap.add_argument("--members", default="Me", help="comma-separated names for the Who list")
    ap.add_argument("--rules", metavar="JSON", help="your own category and account rules (see tools/rules.example.json); keep this file out of git")
    ap.add_argument("--dry", action="store_true", help="print a summary and change nothing")
    a = ap.parse_args()
    if a.rules:
        load_rules(a.rules)

    rows = list(card_rows(a.cards, a.year)) + list(cash_rows(a.cash, a.year, a.cash_name))
    for spec in a.extra_cash:
        path, _, name = spec.partition("=")
        rows += list(cash_rows(path, a.year, name or path))
    if a.enrich:
        print("enriched %d card rows from %s" % (enrich(rows, a.enrich), a.enrich))
    cash_net = sum(r["amount"] for r in rows if r.get("cash"))
    print("cash accounts: opening %.2f + movement %.2f = closing %.2f" % (a.opening, cash_net, a.opening + cash_net))
    income = sum(r["amount"] for r in rows if r["category"] == "Income")
    spend = sum(-r["amount"] for r in rows if r["amount"] < 0 and r["category"] != "Transfer")
    refunds = sum(r["amount"] for r in rows if r.get("refund"))
    print("%d rows | income %.2f | spending %.2f | refunds %.2f | transfers %d" % (
        len(rows), income, spend, refunds, sum(r["category"] == "Transfer" for r in rows)))
    by = {}
    for r in rows:
        if r["amount"] < 0 and r["category"] != "Transfer":
            by[r["category"]] = by.get(r["category"], 0) - r["amount"]
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print("  %-10s %10.2f" % (k, v))
    if a.dry:
        return

    store = json.load(urllib.request.urlopen(a.server + "/api/data"))["collections"]
    writes = [{"op": "delete", "col": col, "id": i} for col in ("transactions", "pots", "recurring", "budgets", "accounts", "rules") for i in store.get(col, {})]
    writes.append({"op": "set", "col": "settings", "id": "main",
                   "data": {"household": "Household", "currency": "USD", "opening": a.opening, "members": [m.strip() for m in a.members.split(",") if m.strip()], "fiscalYear": a.year}})
    for r in rows:
        i = r.pop("id")
        writes.append({"op": "set", "col": "transactions", "id": i, "data": r})
    for k in range(0, len(writes), 4000):
        call(a.server, "POST", "/api/batch", {"writes": writes[k:k + 4000]})
    print("loaded", len(rows), "transactions for FY%d" % a.year)


if __name__ == "__main__":
    main()
