"""The optional local-model fallback, with the model replaced by a stub (no model is ever called in tests)."""
import json
import pytest
import llm
import statements as st

TEXT = "Account Summary Previous Balance $100.00 Closing Date 03/12/2025 New Balance $125.00 Total 25.00"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("FINANCES_LLM", "tiny")


def stub(monkeypatch, rows):
    monkeypatch.setattr(llm, "ask", lambda text, name: rows)


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("FINANCES_LLM", raising=False)
    assert llm.model() == "" and llm.read(TEXT) is None


def test_rows_are_kept_only_when_the_balances_reconcile(on, monkeypatch):
    monkeypatch.setattr(st, "statement_meta", lambda t: {"start": None, "end": None, "opening": 100.0, "closing": 125.0})
    stub(monkeypatch, [{"date": "2025-03-01", "desc": "SHOP", "amount": -25.0}])
    rows, meta = llm.read(TEXT, "Visa")                       # a card: spending raises the balance
    assert rows[0]["amount"] == -25.0 and not rows[0].get("cash") and meta["kind"] == "statement"
    stub(monkeypatch, [{"date": "2025-03-01", "desc": "DEPOSIT", "amount": 25.0}])
    rows, _ = llm.read(TEXT, "Bank")                          # a bank account: deposits raise it
    assert rows[0]["cash"] is True
    stub(monkeypatch, [{"date": "2025-03-01", "desc": "SHOP", "amount": -30.0}])
    assert llm.read(TEXT, "Visa") is None                      # does not add up: rejected


def test_no_printed_balances_or_no_answer_means_no_trust(on, monkeypatch):
    stub(monkeypatch, [{"date": "2025-03-01", "desc": "SHOP", "amount": -25.0}])
    assert llm.read("nothing printed here") is None
    monkeypatch.setattr(st, "statement_meta", lambda t: {"start": None, "end": None, "opening": 1.0, "closing": 2.0})
    stub(monkeypatch, None)
    assert llm.read(TEXT) is None


class Reply:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self): return self.body


def test_ask_parses_the_models_json_and_drops_malformed_rows(monkeypatch):
    content = json.dumps({"rows": [{"date": "2025-03-01", "desc": "A", "amount": -1}, {"date": "bad", "desc": "B", "amount": 2}, {"date": "2025-03-02", "desc": "", "amount": 2}, "x"]})
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: Reply(json.dumps({"message": {"content": content}}).encode()))
    assert llm.ask("t", "tiny") == [{"date": "2025-03-01", "desc": "A", "amount": -1}]


def test_ask_gives_none_when_the_model_is_unreachable_or_answers_nonsense(monkeypatch):
    def down(req, timeout): raise OSError("refused")
    monkeypatch.setattr(llm.urllib.request, "urlopen", down)
    assert llm.ask("t", "tiny") is None
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: Reply(b"not json"))
    assert llm.ask("t", "tiny") is None
