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

    def start(self):
        env = dict(os.environ, FINANCES_TODAY=TODAY)
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


