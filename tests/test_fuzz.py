"""Random inputs for the parts that must never crash or contradict themselves."""
import datetime as dt
import random
import statements as st

STATES = ["ok", "mismatch", "unverified", "ignored", "unreadable"]


def entry(rng):
    state = rng.choice(STATES)
    end = dt.date(2024, 1, 1) + dt.timedelta(days=rng.randrange(0, 900))
    e = {"file": "f%d.pdf" % rng.randrange(99), "label": rng.choice(["Maple Bank", "Maple  Bank", "Oak Card", "Elm"]), "person": rng.choice(["", "Person A", "Person B"]),
         "state": state, "diff": round(rng.uniform(-9, 9), 2), "count": rng.randrange(0, 40), "opening": rng.choice([None, 10.0, 0.0]), "closing": rng.choice([None, 10.0, 25.5])}
    if rng.random() < .9:
        e["end"] = end.isoformat()
        e["start"] = (end - dt.timedelta(days=rng.choice([0, 20, 30, 31, 60, 365]))).isoformat() if rng.random() < .8 else None
    else:
        e["end"] = e["start"] = None
    if state == "mismatch" and e["closing"] is None:
        e["closing"] = 1.0
    return e


def test_audit_never_crashes_and_its_counts_and_cells_agree_with_each_other():
    for seed in range(300):
        rng = random.Random(seed)
        entries = {"p%d" % i: entry(rng) for i in range(rng.randrange(0, 25))}
        r = st.audit(entries, "2026-11-14")
        c = r["counts"]
        assert c["unreadable"] == sum(e["state"] == "unreadable" for e in entries.values())
        assert c["ignored"] == sum(e["state"] == "ignored" for e in entries.values())
        assert c["statements"] == sum(e["state"] in ("ok", "mismatch", "unverified") for e in entries.values())
        for a in r["accounts"]:
            months = [x["mo"] for x in a["cells"]]
            assert months == sorted(months) and len(months) == len(set(months)), (seed, months)         # in order, none twice
            assert all(x["state"] in ("ok", "mismatch", "unverified", "missing", "chain") for x in a["cells"])
            if months:
                assert a["first"] <= months[0] and a["last"] >= months[-1], (seed, a["first"], months)
                assert all(i["kind"] for i in a["issues"])
        missing = sum(x["state"] == "missing" for a in r["accounts"] for x in a["cells"])
        jumps = sum(i["kind"] == "chain" for a in r["accounts"] for i in a["issues"])
        assert c["missing"] == missing + jumps, seed
        for a in r["accounts"]:
            for i in a["issues"]:
                if i["kind"] == "chain":
                    assert any(x["state"] in ("chain", "mismatch", "missing") for x in a["cells"]), seed      # a problem that blocks "complete" must show on the grid
        if r["complete"]:
            assert not missing and not c["mismatch"] and not c["unreadable"]


def test_statement_meta_and_parsers_survive_garbage():
    rng = random.Random(7)
    words = ["Statement", "Period", "Balance", "01/02/2025", "$1,234.56", "-$5.00", "to", "Closing", "Date", "Previous", "New", "Account", "CR", "Beginning", "Ending", "on", "January", "1,", "2025"]
    for _ in range(500):
        text = " ".join(rng.choice(words) for _ in range(rng.randrange(0, 60)))
        st.statement_meta(text)
        rows = st.parse_text(text)
        assert rows is None or all({"date", "desc", "amount", "card"} <= set(r) for r in rows)


def test_a_balance_jump_shows_on_the_grid_and_the_range_covers_every_cell():
    e = {"a": {"file": "a", "label": "Oak", "person": "", "state": "ok", "start": "2026-01-01", "end": "2026-01-31", "opening": 0.0, "closing": 100.0, "count": 1},
         "b": {"file": "b", "label": "Oak", "person": "", "state": "ok", "start": "2026-02-01", "end": "2026-02-28", "opening": 150.0, "closing": 200.0, "count": 1},
         "long": {"file": "c", "label": "Oak", "person": "", "state": "ok", "start": "2025-06-01", "end": "2026-01-30", "opening": None, "closing": None, "count": 1}}
    r = st.audit(e, "2026-03-01")
    a = r["accounts"][0]
    assert {x["mo"]: x["state"] for x in a["cells"]}["2026-02"] == "chain" and not r["complete"]
    assert a["first"] == "2025-06" and a["last"] == "2026-02"


def test_the_api_survives_bad_requests(empty_server):
    call = empty_server.call
    for method, path, body in [("POST", "/api/batch", "nonsense"), ("PUT", "/api/doc/transactions/x", [1, 2]), ("PUT", "/api/doc/nope/x", {}), ("GET", "/api/doc/transactions/missing", None),
                               ("DELETE", "/api/doc/transactions/missing", None), ("GET", "/../server.py", None), ("GET", "/%2e%2e/server.py", None), ("POST", "/api/sync", "x"), ("GET", "/api/nothing", None)]:
        status, _ = call(method, path, body)
        assert status < 500, (method, path, status)
    assert call("GET", "/api/data")[0] == 200
