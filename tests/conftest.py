"""Shared fixtures: a throwaway server per test, and a stand-in bank bridge.

Nothing here touches the real ./data folder. Each test gets its own temporary data folder
and its own port, with the date pinned to TODAY so the example figures are predictable.
"""
import base64
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-11-12"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, data_dir, *extra):
        self.port = free_port()
        self.url = "http://127.0.0.1:%d" % self.port
        self.data_dir = Path(data_dir)
        self.extra = extra
        self.proc = None

    def start(self):
        env = dict(os.environ, FINANCES_TODAY=TODAY, FINANCES_ALLOW_HTTP_BANK="1")
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py"), "--port", str(self.port), "--bind", "127.0.0.1",
             "--name", "", "--data", str(self.data_dir), "--quiet", *self.extra],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.url + "/api/data", timeout=1).read()
                return self
            except OSError:
                if self.proc.poll() is not None:
                    raise RuntimeError("server exited: " + self.proc.stderr.read().decode())
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=5)

    def call(self, method, path, body=None, headers=None):
        """Returns (status, parsed JSON or raw text)."""
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                status, raw = res.status, res.read().decode()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode()
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw

    def data(self):
        return self.call("GET", "/api/data")[1]

    def docs(self, collection):
        return self.data()["collections"][collection]

    def balance(self):
        c = self.data()["collections"]
        return c["settings"]["main"]["opening"] + sum(t["amount"] for t in c["transactions"].values())


@pytest.fixture
def server(tmp_path):
    s = Server(tmp_path / "data").start()
    yield s
    s.stop()


@pytest.fixture
def empty_server(tmp_path):
    s = Server(tmp_path / "data", "--empty").start()
    yield s
    s.stop()


class Bank:
    """A minimal SimpleFIN bridge: one claim address, then an accounts address behind basic auth."""
    USER, PASSWORD = "demo-user", "s3cret-pass"

    def __init__(self):
        bank = self
        self.claims = 0
        self.requests = []

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, code, body, ctype="application/json"):
                raw = body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                if self.path == "/claim/ONE-TIME" and bank.claims == 0:
                    bank.claims += 1
                    return self.reply(200, "http://%s:%s@127.0.0.1:%d/simplefin" % (bank.USER, bank.PASSWORD, bank.port), "text/plain")
                self.reply(403, "claimed")

            def do_GET(self):
                want = "Basic " + base64.b64encode(("%s:%s" % (bank.USER, bank.PASSWORD)).encode()).decode()
                if not self.path.startswith("/simplefin/accounts") or self.headers.get("Authorization") != want:
                    return self.reply(403, "{}")
                bank.requests.append(self.path)
                day = 1794268800  # 2026-11-10 00:00 UTC
                self.reply(200, json.dumps({
                    "errlist": [], "connections": [{"conn_id": "c1", "name": "Example Credit Union", "org_id": "ecu", "sfin_url": "x"}],
                    "accounts": [
                        {"id": "ACT-checking 1", "name": "Joint Checking", "conn_id": "c1", "currency": "USD", "balance": "5200.40",
                         "balance-date": day + 86400, "transactions": [
                             {"id": "t1", "posted": day + 43200, "amount": "-54.20", "description": "WHOLE FOODS MARKET #123"},
                             {"id": "t2", "posted": day + 43200, "amount": "2400.00", "description": "ACME CORP PAYROLL"},
                             {"id": "t3", "posted": 0, "amount": "-9.99", "description": "PENDING THING", "pending": True}]},
                        {"id": "ACT-card", "name": "Rewards Card", "conn_id": "c1", "currency": "USD", "balance": "-320.25",
                         "balance-date": day + 86400, "transactions": [
                             {"id": "t1", "posted": day + 43200, "amount": "-18.75", "description": "CHIPOTLE 0456"}]}]}))

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.setup_token = base64.b64encode(("http://127.0.0.1:%d/claim/ONE-TIME" % self.port).encode()).decode()
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def bank():
    b = Bank()
    yield b
    b.close()
