"""The HTTP surface of a real server process: every route, the awkward requests, and sign-in on top of all of them."""
import json
import re
import ssl
import time
import urllib.error
import urllib.request

import pytest

from conftest import Server
from pdfs import tiny_pdf


def cookie_of(head):
    m = re.search(r"fd_session=([^;]*)", head.get("Set-Cookie", ""))
    return m.group(1) if m else ""


def sign_in(server, name="Una", password="correct horse"):
    _, _, head = server.raw("POST", "/api/account/setup", {"name": name, "password": password})
    return {"Cookie": "fd_session=" + cookie_of(head)}


# ---------------------------------------------------------------- plain routes

def test_static_files_and_what_is_not_served(server):
    for path, kind in (("/", "text/html"), ("/index.html", "text/html"), ("/app.css", "text/css"), ("/app.js", "javascript"), ("/favicon.svg", "image/svg+xml"),
                       ("/favicon.ico", "image/svg+xml"), ("/icon-192.png", "image/png"), ("/login.html", "text/html")):
        req = urllib.request.Request(server.url + path)
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200 and kind in r.headers["Content-Type"], path
            assert r.headers["Cache-Control"] == "no-store" and r.headers["X-Content-Type-Options"] == "nosniff"
    for path in ("/nope", "/../server.py", "/%2e%2e/server.py", "/data/data.json", "/tests/conftest.py", "/auth.py", "/api/nope"):
        assert server.call("GET", path)[0] in (404, 403), path


def test_export_and_backup_downloads(server):
    status, body = server.call("GET", "/api/export.csv")
    assert status == 200 and body.splitlines()[0] == "date,description,amount,category,who,account" and len(body.splitlines()) > 50
    status, backup = server.call("GET", "/api/backup.json")
    assert status == 200 and "collections" in backup and "sync" not in backup                      # a backup is the data, not the sync bookkeeping
    server.call("PUT", "/api/doc/accounts/a1", {"name": "Main"})
    server.call("PUT", "/api/doc/transactions/withacct", {"date": "2026-01-01", "desc": "X", "amount": -1, "account": "a1"})
    assert "Main" in server.call("GET", "/api/export.csv")[1]


def test_csv_import_endpoint(empty_server):
    s = empty_server
    assert s.call("POST", "/api/import/csv", {"text": ""})[0] == 400
    assert s.call("POST", "/api/import/csv", {"text": 5})[0] == 400
    status, body = s.call("POST", "/api/import/csv", {"text": "nothing useful"})
    assert status == 400 and "No header row" in body["error"]
    csv = "Date,Description,Amount\n2025-01-02,Cafe,-4.50\n"
    assert s.call("POST", "/api/import/csv", {"text": csv, "dry": True})[1]["imported"] == 0
    assert s.call("POST", "/api/import/csv", {"text": csv})[1]["imported"] == 1
    assert s.call("POST", "/api/import/csv", {"text": csv, "flip": True})[1]["new"] == 1       # the same row, flipped, is a different payment


def test_requests_that_are_wrong_get_plain_errors(server):
    assert server.call("POST", "/api/batch", b"not json")[0] == 400
    assert server.call("POST", "/api/batch", b"")[0] == 400
    assert server.call("POST", "/api/unknown", {})[0] == 404
    assert server.call("PUT", "/api/doc/budgets", {"a": 1})[0] == 404                         # no id
    assert server.call("PUT", "/api/doc/nothere/x", {"a": 1})[0] == 404
    assert server.call("PUT", "/api/doc/budgets/bad%20id!", {"a": 1})[0] in (400, 404)
    assert server.call("PATCH", "/api/doc/budgets/missing", {"a": 1})[0] == 404
    assert server.call("DELETE", "/api/doc/budgets/missing")[0] == 200                       # deleting what is not there is fine
    assert server.call("PUT", "/api/doc/budgets/x", {"limit": 1})[0] == 200
    assert server.call("PATCH", "/api/doc/budgets/x", {"limit": 2})[0] == 200 and server.docs("budgets")["x"]["limit"] == 2
    assert server.call("DELETE", "/api/doc/budgets/x")[0] == 200 and "x" not in server.docs("budgets")


def test_batch_validation_and_each_operation(empty_server):
    s = empty_server
    for bad in ({"writes": "no"}, {"writes": [1]}, {"writes": [{"op": "set", "col": "nope", "id": "a", "data": {}}]},
                {"writes": [{"op": "frobnicate", "col": "budgets", "id": "a", "data": {}}]}, {"writes": [{"op": "set", "col": "budgets", "id": "bad id", "data": {}}]},
                {"writes": [{"op": "set", "col": "budgets", "id": "a", "data": []}]}, {"writes": [{"op": "set", "col": "budgets", "id": "a"}]},
                {"writes": [{"op": "set", "col": "budgets", "id": "a", "data": {}}] * 5001}):
        assert s.call("POST", "/api/batch", bad)[0] == 400, str(bad)[:60]
    ok = {"writes": [{"op": "set", "col": "budgets", "id": "a", "data": {"limit": 1}}, {"op": "update", "col": "budgets", "id": "a", "data": {"limit": 5}},
                     {"op": "update", "col": "budgets", "id": "ghost", "data": {"limit": 5}}, {"op": "delete", "col": "budgets", "id": "nothing"}]}
    assert s.call("POST", "/api/batch", ok)[0] == 200
    assert s.docs("budgets") == {"a": {"limit": 5}}                                              # updating a missing doc does nothing


# ---------------------------------------------------------------- sync routes

def test_sync_log_stop_and_start_routes(empty_server, tmp_path):
    s = empty_server
    status, log = s.call("GET", "/api/sync/log")
    assert status == 200 and log["lines"] == [] and log["running"] is False and log["last"] == 0
    assert s.call("GET", "/api/sync/log?since=abc")[0] == 200                                    # a junk 'since' means "from the start"
    assert s.call("GET", "/api/sync/log?since=")[0] == 200
    assert s.call("POST", "/api/sync/stop", {})[1] == {"stopping": True}
    assert s.call("POST", "/api/sync", {})[1] == {"started": True}                              # no source: it fails fast, but it did start
    for _ in range(100):
        log = s.call("GET", "/api/sync/log?since=0")[1]
        if not log["running"] and log["lines"] and log["ok"] is not None:
            break
        time.sleep(0.05)
    assert any("Add a Google Drive folder link" in x["m"] for x in log["lines"]) and log["ok"] is False
    later = s.call("GET", "/api/sync/log?since=%d" % log["last"])[1]
    assert later["lines"] == []                                                                  # only new lines come back


def test_second_sync_while_running(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCES_SYNC_DELAY", "1.5")
    folder = tmp_path / "pdfs"
    folder.mkdir()
    tiny_pdf(folder / "a.pdf", "nothing")
    tiny_pdf(folder / "b.pdf", "nothing")
    server = Server(tmp_path / "data", "--empty").start()
    try:
        server.call("PUT", "/api/doc/settings/main", {"household": "H", "sync": {"localFolder": str(folder), "auto": False}})
        assert server.call("POST", "/api/sync", {"force": True})[1] == {"started": True}
        for _ in range(60):
            if server.call("GET", "/api/sync/log")[1]["running"]:
                break
            time.sleep(0.05)
        assert server.call("POST", "/api/sync", {})[1] == {"running": True}
        assert server.call("POST", "/api/sync/stop", {})[0] == 200
        for _ in range(100):
            if server.call("GET", "/api/sync/log")[1]["ok"] is False:
                break
            time.sleep(0.1)
        assert server.call("GET", "/api/sync/log")[1]["ok"] is False                           # stopped
    finally:
        server.stop()


# ---------------------------------------------------------------- sign-in, route by route

def test_unknown_account_routes_and_bad_logins(empty_server):
    s = empty_server
    assert s.call("POST", "/api/account/nothing", {})[0] == 401                                              # not signed in: no account routes at all
    assert s.call("POST", "/api/login", {"name": "nobody", "password": "x"})[0] == 400                       # nothing set up yet
    assert s.call("POST", "/api/account/setup", {"name": "", "password": "correct horse"})[0] == 400
    assert s.call("POST", "/api/account/setup", {"name": "Una", "password": "short"})[0] == 400
    assert s.call("POST", "/api/logout", {})[0] == 200                                                       # signing out when not signed in is fine
    assert s.call("POST", "/api/account/password", {"current": "x", "new": "y" * 9})[0] == 401
    assert s.call("POST", "/api/account/require", {"on": False})[0] == 401


def test_signed_in_requests_cover_every_account_route(empty_server):
    s = empty_server
    me = sign_in(s)
    assert s.call("POST", "/api/account/unknown", {}, me)[0] == 404
    assert s.call("POST", "/api/account/require", {"on": True}, me)[1]["required"] is True              # turning it on needs no password
    assert s.call("POST", "/api/account/require", {"on": False, "password": "wrong"}, me)[0] == 400
    assert s.call("POST", "/api/account/password", {"current": "correct horse", "new": "x"}, me)[0] == 400
    anonymous = {"Cookie": "fd_session=not-a-real-token"}
    assert s.call("GET", "/api/data", headers=anonymous)[0] == 401
    assert s.call("POST", "/api/account/password", {"current": "a", "new": "b" * 9}, anonymous)[0] == 401
    assert s.call("POST", "/api/account/require", {"on": False}, anonymous)[0] == 401
    for method, path in (("PUT", "/api/doc/budgets/x"), ("PATCH", "/api/doc/budgets/x"), ("DELETE", "/api/doc/budgets/x"), ("POST", "/api/sync"), ("POST", "/api/sync/stop"),
                         ("POST", "/api/import/csv"), ("GET", "/api/export.csv"), ("GET", "/api/backup.json"), ("GET", "/api/sync/log")):
        assert s.call(method, path, {} if method != "GET" else None, anonymous)[0] == 401, (method, path)
        assert s.call(method, path, {} if method != "GET" else None, me)[0] != 401, (method, path)


def test_the_page_is_the_sign_in_page_until_you_sign_in(empty_server):
    s = empty_server
    me = sign_in(s)
    for path in ("/", "/index.html", "/login"):
        page = s.call("GET", path)[1]
        assert "Sign in" in page and "balance" not in page, path
        assert "<title>Household Money</title>" in s.call("GET", path, headers=me)[1] or path == "/login"
    assert s.call("GET", "/api/session")[1] == {"required": True, "user": None, "minLength": 8}
    assert s.call("GET", "/api/session", headers=me)[1]["users"] == ["Una"]
    for public in ("/app.css", "/favicon.svg", "/favicon.ico", "/icon-192.png"):
        assert s.fetch(public)[0] == 200, public
    for private in ("/app.js", "/login.html", "/api/data"):
        assert s.fetch(private)[0] == 401, private


def test_cookies_are_secure_only_over_https(tmp_path):
    import shutil
    import subprocess
    if not shutil.which("openssl"):
        pytest.skip("openssl is not installed")
    cert, key = tmp_path / "c.pem", tmp_path / "k.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=localhost"],
                   check=True, capture_output=True)
    server = Server(tmp_path / "data", "--empty", "--cert", str(cert), "--key", str(key)).start_tls()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        req = urllib.request.Request(server.url + "/api/account/setup", data=json.dumps({"name": "Una", "password": "correct horse"}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            assert "; Secure" in r.headers["Set-Cookie"] and "HttpOnly" in r.headers["Set-Cookie"]
        # a client that connects and says nothing must not hold up anyone else
        import socket
        idle = socket.create_connection(("127.0.0.1", server.port), timeout=5)
        try:
            with urllib.request.urlopen(urllib.request.Request(server.url + "/app.css"), context=ctx, timeout=5) as r:
                assert r.status == 200
            # plain http to a TLS port fails that one connection and nothing else
            bad = socket.create_connection(("127.0.0.1", server.port), timeout=5)
            bad.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
            bad.close()
            with urllib.request.urlopen(urllib.request.Request(server.url + "/app.css"), context=ctx, timeout=5) as r:
                assert r.status == 200
        finally:
            idle.close()
    finally:
        server.stop()
