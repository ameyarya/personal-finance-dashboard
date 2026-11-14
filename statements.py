"""Read bank and card statement PDFs into transactions.

Text comes out of each PDF (pypdf, installed separately), then one parser per statement layout turns it into
rows: {date, desc, amount, card, cash}. Amounts follow the dashboard's convention: negative is money out.
Nothing here talks to the network or the dashboard's storage; server.py calls parse_pdf() and stores the rows.
"""
import datetime as dt
import re

PAYMENT = re.compile(r"PAYMENT THANK YOU|AUTOPAY|AUTOMATIC PAYMENT|DIRECTPAY|ONLINE PAYMENT|CRCARDPMT|E-?PAYMENT", re.I)
NUM = r"[\d,]+\.\d\d"


def extract_text(path):
    """All the text in a PDF as one line of single-spaced words. Raises RuntimeError if pypdf is missing."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Reading PDFs needs pypdf. Install it with: pip install pypdf")
    reader = PdfReader(str(path))
    return normalize("\n".join((p.extract_text() or "") for p in reader.pages))


def normalize(text):
    text = text.replace("\\", "").replace("−", "-").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def money(s):
    return float(s.replace(",", "").replace("$", ""))


def iso(y, m, d):
    return "%04d-%02d-%02d" % (y, m, d)


def with_year(month, day, end):
    """A statement shows 'MM/DD' only: use the period's end date to pick the year (a December row on a January statement is last year)."""
    year = end.year - (1 if month > end.month else 0)
    return iso(year, month, day)


def row(date, desc, amount, card, cash=False):
    desc = re.sub(r"\s+", " ", desc).strip(" -")
    out = {"date": date, "desc": desc, "amount": round(amount, 2), "card": card}
    if cash:
        out["cash"] = True
    return out


# ---------------------------------------------------------------- Wells Fargo card

WF_ROW = re.compile(r"(\d{4}) (\d\d)/(\d\d) (\d\d)/(\d\d) ([A-Z0-9]{8,}) (.+?) (%s)(?= \d{4} \d\d/\d\d \d\d/\d\d |$| TOTAL| Fees| NOTICE| Continued| Detach)" % NUM)


WF_PAYMENT = re.compile(r"(?<!\d )(\d\d)/(\d\d) (\d\d)/(\d\d) ([A-Z0-9]{8,}) (.+?) (%s)(?= TOTAL PAYMENTS)" % NUM)


def parse_wells_fargo(text):
    m = re.search(r"Statement Period (\d\d)/(\d\d)/(\d{4}) to (\d\d)/(\d\d)/(\d{4})", text)
    if not (m and "WELLS FARGO" in text.upper()):
        return None
    end = dt.date(int(m.group(6)), int(m.group(4)), int(m.group(5)))
    marks = [(x.start(), kind) for kind, pat in (("credit", r"Payments(?= \d{4} \d\d/\d\d| TOTAL)|Other Credits"), ("charge", r"Purchases, Balance Transfers & Other Charges"), ("fee", r"Fees Charged"))
             for x in re.finditer(pat, text)]
    marks.sort()
    card = "Wells Fargo"
    out = []
    for r in WF_ROW.finditer(text):
        kind = "charge"
        for pos, k in marks:
            if pos <= r.start():
                kind = k
        amount = money(r.group(8))
        desc = r.group(7)
        out.append(row(with_year(int(r.group(2)), int(r.group(3)), end), desc, amount if kind == "credit" else -amount, card))
    for r in WF_PAYMENT.finditer(text):                    # payments carry no card digits in front, so the row pattern above misses them
        out.append(row(with_year(int(r.group(1)), int(r.group(2)), end), r.group(6), money(r.group(7)), card))
    return out


# ---------------------------------------------------------------- Bank of America deposit account

BOFA_ROW = re.compile(r"(\d\d)/(\d\d)/(\d\d) (.+?) (-?%s)(?= \d\d/\d\d/\d\d |$| Total )" % NUM)


def parse_bofa(text):
    if "Bank of America" not in text or "Beginning balance on" not in text or "Ending balance on" not in text:
        return None                    # card statements mention Bank of America too, as the place payments come from
    start = min([i for i in (text.find("Deposits and other additions Date"), text.find("Withdrawals and other subtractions Date")) if i >= 0] or [-1])
    if start < 0:
        return []
    body = text[start:]
    out = []
    for r in BOFA_ROW.finditer(body):
        desc = r.group(4)
        if desc.startswith("Date Description"):
            continue
        out.append(row(iso(2000 + int(r.group(3)), int(r.group(1)), int(r.group(2))), desc, money(r.group(5)), "Bank of America", cash=True))
    return out


# ---------------------------------------------------------------- Wealthfront cash account

def parse_wealthfront(text):
    if "Wealthfront" not in text or "Account Activity" not in text:
        return None
    out, card = [], "Wealthfront Cash"
    text = re.sub(r"(\d{1,2}/\d{1,2}/\d{3}) (\d) ", r"\1\2 ", text)           # the PDF sometimes splits a year: "10/14/202 5"
    for r in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{4}) (\w+ \d{4}) \$(%s)" % NUM, text[text.find("INTEREST"):] if "INTEREST" in text else ""):
        out.append(row(iso(int(r.group(3)), int(r.group(1)), int(r.group(2))), "%s interest" % r.group(4).split()[0], money(r.group(5)), card, cash=True))
    for r in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{4}) (ACH|End of day transfer (?:from|to) Green Dot|RTP/FedNow)\d? (Received|Disbursed) -?\$(%s)" % NUM, text):
        sign = 1 if r.group(5) == "Received" else -1                              # money in or out of the account, not the moves between its partner banks
        name = "Green Dot" if "Green Dot" in r.group(4) else r.group(4)
        out.append(row(iso(int(r.group(3)), int(r.group(1)), int(r.group(2))), "%s transfer %s" % (name, "in" if sign > 0 else "out"), sign * money(r.group(6)), card, cash=True))
    for r in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{2,4})? ?-- -- Transfer out -- -- -\$(%s)" % NUM, text):
        y = int(r.group(3)) if r.group(3) and len(r.group(3)) == 4 else None
        if y:
            out.append(row(iso(y, int(r.group(1)), int(r.group(2))), "Personal Investment", -money(r.group(4)), card, cash=True))
    return out


# ---------------------------------------------------------------- Capital One year-end summary and generic card statements

def parse_capital_one_year_end(text):
    m = re.search(r"Year-End Summary (\d{4})", text)
    if not (m and "Capital One" in text and "Transaction Details" in text):
        return None
    year = int(m.group(1))
    body = text[text.find("Transaction Details"):]
    out = []
    for r in re.finditer(r"(\d\d)/(\d\d) (.+?) (-?\$%s)(?= \d\d/\d\d |$| TOTAL)" % NUM, body):
        desc = re.sub(r"\s+[A-Z][a-z]+( [A-Z][a-z]+)* [A-Z]{2}$", "", r.group(3))
        out.append(row(iso(year, int(r.group(1)), int(r.group(2))), desc, -money(r.group(4)), "Capital One"))
    return out


GENERIC_ROW = re.compile(r"(?<!\d)(\d\d)/(\d\d)(?:/(\d\d(?:\d\d)?))? (?:\d\d/\d\d(?:/\d\d(?:\d\d)?)? )?((?:(?!\d\d/\d\d).)+?) (-?\$? ?%s)(?= \d\d/\d\d| TOTAL|$| Total)" % NUM)
ISSUERS = (("Capital One", "Capital One"), ("American Express", "Amex"), ("Amex", "Amex"), ("Discover", "Discover"), ("Chase", "Chase"), ("Citi", "Citi"), ("Apple Card", "Apple Card"))


def parse_generic_card(text, hint=""):
    """A best-effort reader for card statements with 'MM/DD description amount' lines. Charges are positive on the statement."""
    name = next((label for key, label in ISSUERS if key.lower() in (text[:3000] + " " + hint).lower()), hint or "Card")
    period = re.search(r"(?:Statement|Closing|Billing) (?:Period|Date)[^0-9]{0,40}(\d\d)/(\d\d)/(\d{2,4})(?: ?(?:to|-) ?(\d\d)/(\d\d)/(\d{2,4}))?", text, re.I)
    end = None
    if period:
        g = period.groups()
        y, mo, d = (g[5], g[3], g[4]) if g[5] else (g[2], g[0], g[1])
        y = int(y) + (2000 if int(y) < 100 else 0)
        end = dt.date(y, int(mo), int(d))
    out = []
    for r in GENERIC_ROW.finditer(text):
        month, day, yr, desc, amt = int(r.group(1)), int(r.group(2)), r.group(3), r.group(4), r.group(5)
        if not (1 <= month <= 12 and 1 <= day <= 31) or len(desc) < 3 or re.search(r"balance|total|minimum|limit|apr", desc, re.I):
            continue
        if yr:
            date = iso(int(yr) + (2000 if int(yr) < 100 else 0), month, day)
        elif end:
            date = with_year(month, day, end)
        else:
            continue
        value = money(amt.replace(" ", ""))
        if value == 0:
            continue
        out.append(row(date, desc, -value, name))
    return out or None


# ---------------------------------------------------------------- American Express

AMEX_ROW = re.compile(r"(?<![\d/])(\d\d)/(\d\d)/(\d\d)(?!\d)\*? ((?:(?!\d\d/\d\d/\d\d).)+?) (-?\$[\d,]+\.\d\d)(?=\s|$)")


def parse_amex(text):
    if "american express" not in text[:6000].lower():
        return None
    out = []
    for r in AMEX_ROW.finditer(text):
        desc = r.group(4)
        if len(desc) < 4 or desc[0] in ",(" or re.search(r"late fee|%|variable|may have|minimum|payment due|(?<!credit )balance|limit|account ending|card ending|customer care|closing date|posting date|indicates", desc, re.I) or not re.search(r"[A-Za-z]{3}", desc):
            continue
        value = money(r.group(5))
        if value == 0:
            continue
        out.append(row(iso(2000 + int(r.group(3)), int(r.group(1)), int(r.group(2))), desc, -value, "Amex"))
    return out


# ---------------------------------------------------------------- Capital One monthly statements

MON = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
MONTHS = {m: i + 1 for i, m in enumerate(MON.split("|"))}
C1_ROW = re.compile(r"(%s) (\d{1,2}) (?:%s) \d{1,2} ([^$]+?) (-?\$[\d,]+\.\d\d)(?=\s|$)" % (MON, MON))


def parse_capital_one_monthly(text):
    if "capital one" not in text.lower() or "Post Date Description Amount" not in text:
        return None
    m = re.search(r"as of (%s)\w* (\d{1,2}), (\d{4})" % MON, text)
    if not m:
        return None
    end = dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    credits_at = text.find("Payments, Credits and Adjustments Trans Date")
    charges_at = text.find("Transactions Trans Date")
    stop = text.find("Fees Trans Date")
    if charges_at < 0:
        return []
    out = []
    for name, lo, hi, sign in (("credit", credits_at, charges_at, 1), ("charge", charges_at, stop if stop > charges_at else len(text), -1)):
        if lo < 0:
            continue
        seg = re.sub(r"[A-Z][A-Z ]+ #\d{4}: (?:Payments, Credits and Adjustments|Transactions|Total Transactions)( Trans Date Post Date Description Amount)?", " ", text[lo:hi])
        for r in C1_ROW.finditer(seg):
            month, day = MONTHS[r.group(1)], int(r.group(2))
            out.append(row(with_year(month, day, end), r.group(3), sign * abs(money(r.group(4))), "Capital One"))
    return out


# ---------------------------------------------------------------- Chase checking account

CHASE_ROW = re.compile(r"(\d\d)/(\d\d) (.+?) (-?%s) (-?%s)(?= \d\d/\d\d |\s*Ending Balance|$)" % (NUM, NUM))


def parse_chase_checking(text):
    if "CHECKING SUMMARY" not in text or "TRANSACTION DETAIL" not in text or "Chase" not in text:
        return None
    period = re.search(r"(\w+) (\d{1,2}), (\d{4}) through (\w+) (\d{1,2}), (\d{4})", text)
    if not period or period.group(4)[:3] not in MONTHS:
        return []
    end = dt.date(int(period.group(6)), MONTHS[period.group(4)[:3]], int(period.group(5)))
    body = text[text.find("TRANSACTION DETAIL"):]
    body = (body[:body.find("Ending Balance")] if "Ending Balance" in body else body).rstrip()
    body = re.sub(r"\d+ ?\d*Page of .*?DESCRIPTION AMOUNT BALANCE", " ", body)
    body = re.sub(r"\s+", " ", body)          # the page break in the middle of the list
    out = []
    for r in CHASE_ROW.finditer(body):
        desc = re.sub(r"\s+(?:PPD|CTX|WEB)? ?ID: ?\d+| Web ID: \d+", "", r.group(3))
        out.append(row(with_year(int(r.group(1)), int(r.group(2)), end), desc, money(r.group(4)), "Chase Checking", cash=True))
    return out


# ---------------------------------------------------------------- Discover, Chase credit cards

DISCOVER_CATEGORIES = r"(?:Services|Merchandise|Restaurants|Supermarkets|Gasoline|Travel/Entertainment|Medical Services|Education|Home Improvement|Government Services|Awards and Rebate Credits|Payments and Credits)"


DIRECTPAY_NOTE = r"\s*SEE DETAILS OF YOUR NEXT DIRECTPAY BELOW.*$"


def parse_discover(text):
    """Discover monthly statements and the 'Last 12 Months' export. Charges are shown as $ 12.34, credits as -$ 12.34."""
    if "discover" not in text.lower():
        return None
    out = []
    if "Last 12 Months Summary" in text:
        for r in re.finditer(r"(\d\d)/(\d\d)/(\d\d) \d\d/\d\d/\d\d (.+?) \$ (-?%s)(?: %s)?(?= \d\d/\d\d/\d\d \d\d/\d\d/\d\d|$)" % (NUM, DISCOVER_CATEGORIES), text):
            out.append(row(iso(2000 + int(r.group(3)), int(r.group(1)), int(r.group(2))), re.sub(DIRECTPAY_NOTE, "", r.group(4)), -money(r.group(5)), "Discover"))
        return out
    period = re.search(r"OPEN TO CLOSE DATE: (\d\d)/(\d\d)/(\d{4}) - (\d\d)/(\d\d)/(\d{4})", text)
    if not period:
        return None
    end = dt.date(int(period.group(6)), int(period.group(4)), int(period.group(5)))
    body = text[text.find("TRANS. DATE"):] if "TRANS. DATE" in text else ""
    for r in re.finditer(r"(\d\d)/(\d\d) ([A-Za-z*#][^$]*?) (-?)\$(%s)" % NUM, body):
        desc = re.sub(DIRECTPAY_NOTE, "", re.sub(r"\s*%s$" % DISCOVER_CATEGORIES, "", r.group(3)))
        amount = money(r.group(5))
        out.append(row(with_year(int(r.group(1)), int(r.group(2)), end), desc, amount if r.group(4) else -amount, "Discover"))
    return out


CHASE_CARD_ROW = re.compile(r"(?<![\d/])(\d\d)/(\d\d) (.+?) (-?%s)(?= \d\d/\d\d | [A-Z][A-Z ]{7,}|\s*$)" % r"(?:[\d,]+)?\.\d\d")


def parse_chase_card(text):
    """Chase credit cards (Amazon Prime and similar): 'MM/DD merchant amount' lines, purchases positive, payments negative."""
    if not ("Chase" in text and "ACCOUNT SUMMARY" in text and "Minimum Payment Due" in text):
        return None
    start = text.find("Merchant Name or Transaction Description")
    if start < 0:
        return []                                         # a month with no activity
    stop = min([i for i in (text.find("Total fees charged in", start), text.find("INTEREST CHARGES", start)) if i >= 0] or [len(text)])
    when = re.search(r"Opening/Closing Date \d\d/\d\d/\d\d - (\d\d)/(\d\d)/(\d\d)", text) or re.search(r"Statement Date: (\d\d)/(\d\d)/(\d\d)", text)
    if not when:
        return []
    end = dt.date(2000 + int(when.group(3)), int(when.group(1)), int(when.group(2)))
    body = re.sub(r"\s+", " ", re.sub(r"Order Number \S+", "", text[start:stop])).rstrip()
    out = []
    for r in CHASE_CARD_ROW.finditer(body):
        out.append(row(with_year(int(r.group(1)), int(r.group(2)), end), r.group(3), -money(r.group(4)), "Chase"))
    return out


def parse_payment_history(text):
    """A card's list of payments made TO it. Those payments already appear on the card statements and on the bank side, so there is nothing new here."""
    return [] if "Payment History Report" in text else None


PARSERS = (parse_payment_history, parse_chase_checking, parse_wells_fargo, parse_bofa, parse_wealthfront, parse_capital_one_year_end, parse_capital_one_monthly, parse_amex, parse_discover, parse_chase_card)


def parse_text(text, hint=""):
    """Rows from a statement's text, or None when no parser recognises it."""
    for p in PARSERS:
        rows = p(text)
        if rows is not None:
            return finish(rows)
    rows = parse_generic_card(text, hint)
    return finish(rows) if rows else None


def finish(rows):
    for r in rows:
        if not r.get("cash") and PAYMENT.search(r["desc"]):
            r["category"] = "Transfer"
            r["amount"] = abs(r["amount"])
        elif r.get("cash") and re.search(r"WEALTHFRONT|ALLY|APPLE GS|BANK OF AMERICA|TRANSFER|CREDIT CARD|CREDIT CRD|AUTOPAY|ACH PMT|CRCARDPMT|E-?PAYMENT", r["desc"], re.I) and "Personal Investment" not in r["desc"]:
            r["category"] = "Transfer"
        elif "Personal Investment" in r["desc"]:
            r["category"] = "Savings"
        elif "interest" in r["desc"].lower() and r["amount"] > 0:
            r["category"] = "Income"
    return rows


def parse_pdf(path, hint=""):
    return parse_text(extract_text(path), hint)


# ---------------------------------------------------------------- what the statement says about itself

AMT = r"(-?\$?-?[\d,]+\.\d\d)"
MONTH_NAMES = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
LONG_DATE = r"((?:%s)[a-z]* \d{1,2}, \d{4})" % MONTH_NAMES
OPENING = re.compile(r"(?:Previous|Beginning|Starting|Opening) Balance(?: on %s)?:? %s" % (LONG_DATE, AMT), re.I)
CLOSING = re.compile(r"(?:New|Ending|Closing) Balance(?: on %s)?:? ?=? ?%s" % (LONG_DATE, AMT), re.I)
PERIODS = (
    re.compile(r"OPEN TO CLOSE DATE:? (\d\d/\d\d/\d{2,4}) - (\d\d/\d\d/\d{2,4})", re.I),
    re.compile(r"%s (?:-|through|to) %s" % (LONG_DATE, LONG_DATE)),
    re.compile(r"Statement Period (\d\d/\d\d/\d{2,4}) (?:to|-|through) (\d\d/\d\d/\d{2,4})", re.I),
    re.compile(r"Opening/Closing Date (\d\d/\d\d/\d{2,4}) - (\d\d/\d\d/\d{2,4})", re.I),
    re.compile(r"Billing Period:? (\d\d/\d\d/\d{2,4}) (?:to|-|through) (\d\d/\d\d/\d{2,4})", re.I),
    re.compile(r"Statement Period:? (\d\d/\d\d/\d{2,4}) (?:to|-|through) (\d\d/\d\d/\d{2,4})", re.I),
)


def to_iso(s):
    """'03/18/2025', '01/14/24' or 'January 31, 2025' as 2025-03-18; '' when it is none of those."""
    m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{2,4})", s.strip())
    if m:
        y = int(m.group(3))
        return iso(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s.strip())
    if m:
        for i, name in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1):
            if m.group(1).lower().startswith(name):
                return iso(int(m.group(3)), i, int(m.group(2)))
    return ""


def signed(text):
    """'$76.58CR' and 'CR$76.58' are a credit balance, so negative."""
    return -money(re.sub(r"[A-Za-z ]", "", text)) if "CR" in text else money(text)


AMEX_OPENING = re.compile(r"Account Summary Previous Balance Payments/Credits New Charges Fees Interest Charged (CR ?\$[\d,]+\.\d\d|\$[\d,]+\.\d\d)")
AMEX_CLOSING = re.compile(r"New Balance (CR ?\$[\d,]+\.\d\d|\$[\d,]+\.\d\d(?:CR)?)")


def statement_meta(text):
    """What the statement prints about itself: {start, end, opening, closing}. A key is None when the layout does not show it."""
    meta = {"start": None, "end": None, "opening": None, "closing": None}
    m = OPENING.search(text)
    if m:
        meta["opening"] = money(m.group(2).replace("$", ""))
        meta["start"] = to_iso(m.group(1) or "") or None
    m = CLOSING.search(text)
    if m:
        meta["closing"] = money(m.group(2).replace("$", ""))
        meta["end"] = to_iso(m.group(1) or "") or None
    m = AMEX_OPENING.search(text)
    if m:
        meta["opening"] = signed(m.group(1))
        m = AMEX_CLOSING.search(text)
        meta["closing"] = signed(m.group(1)) if m else None
    for p in PERIODS:
        m = p.search(text)
        if m:
            meta["start"], meta["end"] = to_iso(m.group(1)) or meta["start"], to_iso(m.group(2)) or meta["end"]
            break
    else:
        m = re.search(r"Closing Date (\d\d/\d\d/\d{2,4})", text) or re.search(r"%s Ending Balance" % LONG_DATE, text)
        if m and not meta["end"]:
            meta["end"] = to_iso(m.group(1)) or None
    return meta


def read_pdf(path, hint=""):
    """(rows, meta) for one statement, or None when no parser recognises it. meta also says kind: 'statement' or 'payments'."""
    text = extract_text(path)
    rows = parse_text(text, hint)
    if rows is None:
        return None
    meta = statement_meta(text)
    meta["kind"] = "payments" if parse_payment_history(text) is not None else "statement"
    return rows, meta


# ---------------------------------------------------------------- checking the figures

def check_statement(rows, meta):
    """(state, difference): does the opening balance plus what we read equal the closing balance the statement prints?
    state is 'ok', 'mismatch' or 'unverified' (the statement does not print both balances). difference is closing minus what we expected."""
    if meta.get("opening") is None or meta.get("closing") is None:
        return "unverified", None
    net = sum(r["amount"] for r in rows)
    expected = meta["opening"] + net if any(r.get("cash") for r in rows) else meta["opening"] - net   # a card balance grows with spending
    diff = round(meta["closing"] - expected, 2)
    return ("ok" if abs(diff) < 0.015 else "mismatch"), diff


def _days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def _add_days(d, n):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


def audit(entries, today):
    """What is missing or does not add up. entries: {path: {person, label, file, state, diff, start, end, opening, closing, reason}}.
    Returns {complete, counts, accounts: [{name, person, first, last, cells: [{mo, state}], issues: [...]}], problems: [...]}."""
    groups, problems, counts = {}, [], {"statements": 0, "ok": 0, "unverified": 0, "mismatch": 0, "missing": 0, "unreadable": 0, "ignored": 0}
    for e in entries.values():
        if e.get("state") == "ignored":
            counts["ignored"] += 1
        elif e.get("state") == "unreadable":
            counts["unreadable"] += 1
            problems.append({"kind": "unreadable", "account": e.get("label", ""), "text": "%s could not be read (%s)." % (e.get("file", "A file"), e.get("reason", "unknown reason"))})
        else:
            groups.setdefault((e.get("person") or "", re.sub(r"[^a-z0-9]", "", (e.get("label") or "").lower())), []).append(e)      # "CapitalOne" and "Capital One" are one account
    firsts = [min(x["end"] for x in g if x.get("end"))[:7] for g in groups.values() if any(x.get("end") for x in g)]
    earliest = min(firsts) if firsts else ""
    accounts = []
    for (person, _), g in sorted(groups.items()):
        label = g[0].get("label") or ""
        dated = sorted((x for x in g if x.get("end")), key=lambda x: x["end"])
        counts["statements"] += len(g)
        issues, cells = [], {}
        for x in g:
            counts[x["state"]] = counts.get(x["state"], 0) + 1
        for x in g:
            if x["state"] == "mismatch":
                issues.append({"kind": "mismatch", "text": "The statement ending %s says %s but the transactions read from it come to %s%s." % (
                    x.get("end") or "(date unknown)", "$%.2f" % x["closing"], "$%.2f" % (x["closing"] - x["diff"]), " (a $%.2f difference)" % abs(x["diff"]))})
        if len(dated) < len(g):
            issues.append({"kind": "nodate", "text": "%d statement%s have no readable date, so they are not placed on the timeline." % (len(g) - len(dated), "" if len(g) - len(dated) == 1 else "s")})
        for x in dated:
            if x.get("start") and _days(x["start"], x["end"]) > 45:       # a "last 12 months" export covers every month it spans
                mo = x["start"][:7]
                while mo < x["end"][:7]:
                    cells[mo] = x["state"]
                    y, m = int(mo[:4]), int(mo[5:]) + 1
                    mo = "%04d-%02d" % (y + (m > 12), (m - 1) % 12 + 1)
        for x in dated:
            mo = x["end"][:7]
            worst = ("mismatch", "unverified", "ok")                        # a month with two statements shows the worse of the two
            cells[mo] = min(filter(None, (cells.get(mo), x["state"])), key=worst.index)
        prev = None
        for x in dated:
            if prev:
                days = _days(prev["end"], x["end"])
                gap = []
                if days > 45:                                                  # statements are about a month apart; a shifting closing day never makes 45
                    mo = prev["end"][:7]
                    while True:
                        y, m = int(mo[:4]), int(mo[5:]) + 1
                        mo = "%04d-%02d" % (y + (m > 12), (m - 1) % 12 + 1)
                        if mo >= x["end"][:7]:
                            break
                        if mo not in cells:
                            gap.append(mo)
                if gap:
                    for mo in gap:
                        cells[mo] = "missing"
                    counts["missing"] += len(gap)
                    issues.append({"kind": "missing", "months": gap, "text": "No statement for %s (between the ones ending %s and %s)." % (", ".join(gap), prev["end"], x["end"])})
                elif prev.get("closing") is not None and x.get("opening") is not None and abs(prev["closing"] - x["opening"]) > 0.015:
                    counts["missing"] += 1
                    issues.append({"kind": "chain", "text": "The balance jumps from $%.2f (statement ending %s) to $%.2f (statement ending %s). A statement between them may be missing." % (prev["closing"], prev["end"], x["opening"], x["end"])})
            prev = x
        if dated and _days(dated[-1]["end"], today) > 62:
            issues.append({"kind": "stale", "text": "The newest statement ends %s, %d days ago. Newer ones may be missing." % (dated[-1]["end"], _days(dated[-1]["end"], today))})
        if dated and earliest and dated[0]["end"][:7] > _add_days(earliest + "-15", 45)[:7]:
            issues.append({"kind": "late", "text": "Statements begin with %s. Anything before that is not in the dashboard." % dated[0]["end"][:7]})
        accounts.append({"name": label, "person": person, "first": dated[0]["end"][:7] if dated else "", "last": dated[-1]["end"][:7] if dated else "",
                         "cells": [{"mo": mo, "state": cells[mo]} for mo in sorted(cells)], "issues": issues})
    broken = ("missing", "chain", "mismatch", "stale", "nodate")          # "late" is a note: the account may simply be newer
    complete = bool(accounts) and not counts["unreadable"] and not any(i["kind"] in broken for a in accounts for i in a["issues"])
    return {"complete": complete, "counts": counts, "accounts": accounts, "problems": problems}
