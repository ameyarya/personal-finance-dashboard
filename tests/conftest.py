"""Shared fixtures: a throwaway server per test.

Nothing here touches the real ./data folder. Each test gets its own temporary data folder
and its own port, with the date pinned to TODAY so the example figures are predictable.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
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
        self.env = {}

    def start(self):
        env = dict(os.environ, FINANCES_TODAY=TODAY, **self.env)
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

    def start_tls(self):
        """Start a server that serves https (a self-signed certificate) and wait until it answers."""
        import ssl
        self.url = "https://127.0.0.1:%d" % self.port
        env = dict(os.environ, FINANCES_TODAY=TODAY)
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(self.port), "--bind", "127.0.0.1", "--name", "",
                                      "--data", str(self.data_dir), "--quiet", *self.extra], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        for _ in range(100):
            try:
                urllib.request.urlopen(self.url + "/api/session", timeout=1, context=ctx).read()
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("https server did not start")

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

    def fetch(self, path, headers=None):
        """(status, bytes) for a GET, whatever the content type."""
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + path, headers=headers or {}), timeout=10) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def raw(self, method, path, body=None, headers=None):
        """Like call(), but also returns the response headers: (status, parsed body, headers)."""
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                status, text, head = res.status, res.read().decode(), res.headers
        except urllib.error.HTTPError as e:
            status, text, head = e.code, e.read().decode(), e.headers
        try:
            return status, json.loads(text), head
        except ValueError:
            return status, text, head

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




# ---------------------------------------------------------------- JavaScript coverage (only when JS_COVERAGE=1, see tools/coverage.sh)
# app.js is served in an instrumented copy (istanbul). The page reports its counters when it goes away (a reload, a close) and the
# tests add them up, so a page that reloads itself or is closed mid-test still counts.

if os.environ.get("JS_COVERAGE"):
    from playwright.sync_api import BrowserContext, Page

    JS_COVER = {}
    _INSTRUMENTED = {"body": None}
    _REPORT_JS = ("window.addEventListener('pagehide', function () { if (window.__coverage__) navigator.sendBeacon('/__cov', JSON.stringify(window.__coverage__)); });"
                  "document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden' && window.__coverage__) "
                  "navigator.sendBeacon('/__cov', JSON.stringify(window.__coverage__)); });")

    def _merge(report):
        for path, cov in report.items():
            mine = JS_COVER.get(path)
            if mine is None:
                JS_COVER[path] = json.loads(json.dumps(cov))
                continue
            for k in cov["s"]:
                mine["s"][k] = mine["s"].get(k, 0) + cov["s"][k]
            for k in cov["f"]:
                mine["f"][k] = mine["f"].get(k, 0) + cov["f"][k]
            for k, counts in cov["b"].items():
                have = mine["b"].setdefault(k, [0] * len(counts))
                for i, n in enumerate(counts):
                    have[i] += n

    def pytest_configure(config):
        subprocess.run(["node", str(ROOT / "tools" / "js-coverage" / "instrument.js")], check=True)
        _INSTRUMENTED["body"] = (ROOT / ".cov" / "app.js").read_text(encoding="utf-8")

    def _on_report(route):
        try:
            _merge(json.loads(route.request.post_data or "{}"))
        finally:
            route.fulfill(status=204, body="")

    _new_page, _page_close, _ctx_close = BrowserContext.new_page, Page.close, BrowserContext.close

    def new_page(self, *a, **k):
        if not getattr(self, "_js_cov", False):
            self._js_cov = True
            self.route("**/app.js", lambda route: route.fulfill(body=_INSTRUMENTED["body"], content_type="text/javascript; charset=utf-8"))
            self.route("**/__cov", _on_report)
            self.add_init_script(_REPORT_JS)
        return _new_page(self, *a, **k)

    def _collect(page):
        try:
            raw = page.evaluate("JSON.stringify(window.__coverage__ || {})")
            _merge(json.loads(raw))
        except Exception:        # a closed page or one that never loaded the app
            pass

    def page_close(self, *a, **k):
        _collect(self)
        return _page_close(self, *a, **k)

    def ctx_close(self, *a, **k):
        for p in list(self.pages):
            _collect(p)
        return _ctx_close(self, *a, **k)

    BrowserContext.new_page, Page.close, BrowserContext.close = new_page, page_close, ctx_close

    def pytest_sessionfinish(session, exitstatus):
        (ROOT / "js-coverage.json").write_text(json.dumps(JS_COVER))


@pytest.fixture(scope="session")
def browser():
    import playwright.sync_api as pw
    with pw.sync_playwright() as p:
        channel = os.environ.get("PW_CHANNEL")
        b = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        yield b
        b.close()
