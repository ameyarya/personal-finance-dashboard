"""Optional fallback reader: a small local model (Ollama) reads a statement the regex parsers could not.

Nothing leaves this computer: the model runs on localhost. Off unless FINANCES_LLM names a model (for example qwen2.5:3b).
Its answer is never trusted on its own: the rows are kept only if the statement's own opening and closing balances reconcile."""
import json
import os
import urllib.request

import statements

URL = os.environ.get("FINANCES_LLM_URL", "http://127.0.0.1:11434")
MAX_CHARS = 24000

SCHEMA = {"type": "object", "required": ["rows"], "properties": {"rows": {"type": "array", "items": {
    "type": "object", "required": ["date", "desc", "amount"],
    "properties": {"date": {"type": "string"}, "desc": {"type": "string"}, "amount": {"type": "number"}}}}}}

PROMPT = ("Below is the text of one bank or credit-card statement. List every transaction (purchases, payments, deposits, withdrawals, fees, interest), "
          "one entry per line item, copied exactly as printed. Skip summaries, totals, balances and the interest-rate tables. "
          "Give date as YYYY-MM-DD (use the statement period for the year), desc as printed, and amount as a positive number for money received or a credit, "
          "negative for money spent or a charge.\n\nStatement:\n")


def model():
    return os.environ.get("FINANCES_LLM", "").strip()


def ask(text, name):
    """The model's list of {date, desc, amount}, or None when it cannot be reached or answers badly."""
    body = json.dumps({"model": name, "stream": False, "format": SCHEMA, "options": {"temperature": 0, "num_ctx": 16384},
                       "messages": [{"role": "user", "content": PROMPT + text[:MAX_CHARS]}]}).encode()
    try:
        req = urllib.request.Request(URL + "/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            out = json.loads(json.loads(r.read())["message"]["content"])["rows"]
    except Exception:
        return None
    good = [x for x in out if isinstance(x, dict) and isinstance(x.get("amount"), (int, float)) and isinstance(x.get("date"), str) and len(x["date"]) == 10 and x.get("desc")]
    return good or None


def read(text, hint=""):
    """(rows, meta) when the model's rows reconcile with the statement's printed balances, else None."""
    name = model()
    if not name:
        return None
    meta = statements.statement_meta(text)
    if meta["opening"] is None or meta["closing"] is None:
        return None                              # nothing to check the answer against, so do not trust it
    got = ask(text, name)
    if not got:
        return None
    for cash in (False, True):                   # cards and bank accounts count in opposite directions: keep whichever reconciles
        rows = statements.finish([statements.row(x["date"], x["desc"], x["amount"], hint, cash) for x in got])
        if statements.check_statement(rows, meta)[0] == "ok":
            meta["kind"] = "statement"
            return rows, meta
    return None
