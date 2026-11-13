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

WF_ROW = re.compile(r"(\d{4}) (\d\d)/(\d\d) (\d\d)/(\d\d) ([A-Z0-9]{8,}) (.+?) (%s)(?= \d{4} \d\d/\d\d \d\d/\d\d |$| TOTAL| Fees| NOTICE| Continued)" % NUM)


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
    return out


# ---------------------------------------------------------------- Bank of America deposit account

BOFA_ROW = re.compile(r"(\d\d)/(\d\d)/(\d\d) (.+?) (-?%s)(?= \d\d/\d\d/\d\d |$| Total )" % NUM)


def parse_bofa(text):
    if "Bank of America" not in text or "Account number" not in text and "Account #" not in text:
        return None
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
    for r in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{4}) (\w+ \d{4}) \$(%s)" % NUM, text[text.find("INTEREST"):] if "INTEREST" in text else ""):
        out.append(row(iso(int(r.group(3)), int(r.group(1)), int(r.group(2))), "%s interest" % r.group(4).split()[0], money(r.group(5)), card, cash=True))
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
        out.append(row(date, desc, -value, name))
    return out or None


PARSERS = (parse_wells_fargo, parse_bofa, parse_wealthfront, parse_capital_one_year_end)


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
        elif r.get("cash") and re.search(r"WEALTHFRONT|ALLY|APPLE GS|BANK OF AMERICA|TRANSFER|CREDIT CARD|CRCARDPMT|E-?PAYMENT", r["desc"], re.I) and "Personal Investment" not in r["desc"]:
            r["category"] = "Transfer"
        elif "Personal Investment" in r["desc"]:
            r["category"] = "Savings"
        elif "interest" in r["desc"].lower() and r["amount"] > 0:
            r["category"] = "Income"
    return rows


def parse_pdf(path, hint=""):
    return parse_text(extract_text(path), hint)
