"""Starting server.py from the command line: options, forgotten passwords, Ctrl-C, https, the network name."""
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

import server
from conftest import ROOT, free_port


def run(args, **kw):
    return subprocess.run([sys.executable, str(ROOT / "server.py"), *args], capture_output=True, text=True, timeout=30, **kw)


def start(args, env=None):
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(port), "--bind", "127.0.0.1", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=dict(os.environ, **(env or {})))
    for _ in range(100):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/api/session" % port, timeout=1).read()
            return proc, port
        except OSError:
            time.sleep(0.05)
    proc.kill()
    raise RuntimeError("did not start: " + proc.stdout.read())


def test_reset_password_sets_a_password_and_turns_sign_in_on(tmp_path):
    r = run(["--data", str(tmp_path), "--reset-password", "Una"], input="correct horse\ncorrect horse\n")
    assert r.returncode == 0 and "Password set for Una." in r.stdout
    users = json.loads((tmp_path / "users.json").read_text())
    assert users["required"] is True and "una" in users["users"] and "correct horse" not in json.dumps(users)


def test_reset_password_stops_when_the_two_entries_differ(tmp_path):
    r = run(["--data", str(tmp_path), "--reset-password", "Una"], input="correct horse\nsomething else\n")
    assert r.returncode != 0 and "differ" in r.stderr and not (tmp_path / "users.json").exists()


def test_ctrl_c_stops_the_server_cleanly(tmp_path):
    proc, port = start(["--data", str(tmp_path), "--name", "", "--empty", "--quiet"])
    proc.send_signal(signal.SIGINT)
    assert proc.wait(timeout=10) == 0


def test_without_an_mdns_tool_it_says_so_and_keeps_serving(tmp_path):
    empty_path = tmp_path / "nothing"
    empty_path.mkdir()
    proc, port = start(["--data", str(tmp_path / "d"), "--name", "finances.test", "--empty"], env={"PATH": str(empty_path)})
    try:
        time.sleep(0.5)
        assert urllib.request.urlopen("http://127.0.0.1:%d/api/session" % port, timeout=5).status == 200
    finally:
        proc.terminate()
        out = proc.communicate(timeout=10)[0]
    assert "no mDNS tool found" in out


@pytest.mark.parametrize("tool", ["dns-sd", "avahi-publish"])
def test_with_an_mdns_tool_it_announces_the_name(tmp_path, tool):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / tool
    fake.write_text("#!/bin/sh\nexec sleep 30\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    proc, port = start(["--data", str(tmp_path / "d"), "--name", "finances.test", "--empty"], env={"PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]})
    try:
        for _ in range(60):
            time.sleep(0.1)
            if proc.poll() is not None:
                break
    finally:
        proc.terminate()
        out = proc.communicate(timeout=10)[0]
    assert "advertising finances.test:%d at " % port in out or "no mDNS tool" not in out


def test_a_named_bind_address_is_printed_as_given(tmp_path):
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(port), "--bind", "localhost", "--name", "", "--data", str(tmp_path), "--empty"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        line = proc.stdout.readline()
    finally:
        proc.terminate()
        proc.communicate(timeout=10)
    assert "serving on http://localhost:%d/" % port in line


def test_a_wildcard_bind_is_shown_as_localhost(tmp_path):
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(port), "--bind", "0.0.0.0", "--name", "", "--data", str(tmp_path), "--empty"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        line = proc.stdout.readline()
    finally:
        proc.terminate()
        proc.communicate(timeout=10)
    assert "serving on http://localhost:%d/" % port in line and str(tmp_path) in line


# ---------------------------------------------------------------- the network helpers, in this process

class Done(Exception):
    pass


def test_lan_ip_returns_the_outgoing_address_or_none(monkeypatch):
    class Sock:
        def __init__(self, *a): pass
        def connect(self, addr): pass
        def getsockname(self): return ("10.1.2.3", 5)  # privacy: allow
        def close(self): self.closed = True

    monkeypatch.setattr(server.socket, "socket", Sock)
    assert server.lan_ip() == "10.1.2.3"  # privacy: allow

    class NoNet(Sock):
        def connect(self, addr): raise OSError("unreachable")

    monkeypatch.setattr(server.socket, "socket", NoNet)
    assert server.lan_ip() is None


class FakeProc:
    def __init__(self, alive=True):
        self.alive, self.terminated = alive, False

    def poll(self):
        return None if self.alive else 1

    def terminate(self):
        self.terminated, self.alive = True, False


def run_advertise(monkeypatch, which, ips, procs, rounds):
    ips, started = list(ips), []
    monkeypatch.setattr(server.shutil, "which", which)
    monkeypatch.setattr(server, "lan_ip", lambda: ips.pop(0) if len(ips) > 1 else ips[0])
    monkeypatch.setattr(server.subprocess, "Popen", lambda cmd, **kw: (started.append(cmd), procs.pop(0))[1])
    count = {"n": 0}

    def sleep(s):
        count["n"] += 1
        if count["n"] >= rounds:
            raise Done()

    monkeypatch.setattr(server.time, "sleep", sleep)
    with pytest.raises(Done):
        server.advertise("finances.test", 8770)
    return started


def test_advertise_without_a_tool_returns_immediately(monkeypatch, capsys):
    assert server.advertise.__name__ == "advertise"
    monkeypatch.setattr(server.shutil, "which", lambda name: None)
    server.advertise("finances.test", 8770)
    assert "no mDNS tool found" in capsys.readouterr().out


def test_advertise_restarts_the_tool_when_the_address_changes_or_the_tool_dies(monkeypatch):
    first, second, third = FakeProc(), FakeProc(), FakeProc()
    started = run_advertise(monkeypatch, lambda name: "/bin/dns-sd" if name == "dns-sd" else None, ["10.0.0.1", "10.0.0.2", "10.0.0.2", "10.0.0.2"], [first, second, third], rounds=4)  # privacy: allow
    assert [c[-1] for c in started] == ["10.0.0.1", "10.0.0.2"] and first.terminated is True  # privacy: allow
    assert started[0][:2] == ["dns-sd", "-P"]
    dead = FakeProc(alive=False)
    again = FakeProc()
    started = run_advertise(monkeypatch, lambda name: "/bin/dns-sd" if name == "dns-sd" else None, ["10.0.0.1"], [dead, again], rounds=3)  # privacy: allow
    assert len(started) == 2                                                    # the tool exited by itself, so it is started again


def test_advertise_with_avahi_and_with_no_address(monkeypatch):
    started = run_advertise(monkeypatch, lambda name: "/bin/x" if name == "avahi-publish" else None, ["10.0.0.5"], [FakeProc()], rounds=2)  # privacy: allow
    assert started[0][:3] == ["avahi-publish", "-a", "-R"]
    none = run_advertise(monkeypatch, lambda name: "/bin/dns-sd" if name == "dns-sd" else None, [None], [], rounds=2)
    assert none == []                                                           # no network yet: nothing is announced, nothing crashes


def test_advertise_when_the_network_disappears_stops_announcing(monkeypatch):
    first = FakeProc()
    started = run_advertise(monkeypatch, lambda name: "/bin/dns-sd" if name == "dns-sd" else None, ["10.0.0.9", None, None], [first], rounds=3)  # privacy: allow
    assert len(started) == 1 and first.terminated is True                      # the old announcement is withdrawn and no new one is made
