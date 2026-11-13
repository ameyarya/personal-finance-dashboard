"""The privacy checks that keep personal information out of git. Every name and number here is invented."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import privacy_scan as ps  # noqa: E402


@pytest.fixture
def terms(tmp_path, monkeypatch):
    f = tmp_path / "terms"
    f.write_text("# comment\nJane Doe\nMaple Street\nre:\\bacct 77\\d\\d\\b\n")
    monkeypatch.setenv("PRIVACY_TERMS_FILE", str(f))
    return ps.load_terms()


@pytest.mark.parametrize("line", [
    "paid by Jane Doe", "lives on MAPLE STREET", "acct 7712 ending", "contact jane@family-mail.org",  # privacy: allow
    "call 415-555-0134", "call (415) 555-0134", "card 4111111111111111", "ssn 123-45-6789",  # privacy: allow
    "open /Users/jane/Documents/x", "server at 192.168.1.50", "token ghp_" + "a" * 30,  # privacy: allow
])
def test_things_that_are_personal_are_caught(line, terms):
    assert ps.scan_line(line, terms), line


@pytest.mark.parametrize("line", [
    "janedoe and mapleville are one word each", "mail 10521352+someone@users.noreply.github.com", "write to a@example.com",
    "http://user:pw@127.0.0.1:8770/", "version 1.2.3 and 12345678", "number 4111111111111112",      # fails the card checksum
    "open /Users/you/Documents", "ip 127.0.0.1", "Jane Doe is a placeholder  # privacy: allow",
])
def test_ordinary_text_is_not_flagged(line, terms):
    assert not ps.scan_line(line, terms), line


@pytest.mark.parametrize("path", ["statement.pdf", "docs/Jan.PDF", "x.csv", "a.xlsx", "data/data.json", "users.json", "sessions.json", "cert.pem", ".env", "rules.local.json", ".privacy-terms.local", "statements/x"])
def test_statement_and_credential_files_are_refused_by_name(path):
    assert ps.scan_path(path), path


@pytest.mark.parametrize("path", ["public/app.js", "README.md", "tools/rules.example.json", "docs/screenshot.png", "tests/test_ui.py", "requirements.txt"])
def test_normal_project_files_pass(path):
    assert not ps.scan_path(path), path


def git(repo, *args, env=None, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env={**os.environ, **(env or {})}, check=check)


@pytest.fixture
def repo(tmp_path, terms):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "T")
    git(r, "config", "core.hooksPath", str(ROOT / ".githooks"))
    return r


def test_commit_with_a_private_term_is_blocked_and_a_clean_one_goes_through(repo):
    (repo / "a.txt").write_text("rent for Jane Doe\n")
    git(repo, "add", "a.txt")
    r = git(repo, "commit", "-m", "add", check=False)
    assert r.returncode != 0 and "check FAILED" in r.stderr and "a.txt" in r.stderr
    assert "Jane" not in r.stderr and "Doe" not in r.stderr           # the report never repeats what it found
    (repo / "a.txt").write_text("rent for Person A\n")
    git(repo, "add", "a.txt")
    assert git(repo, "commit", "-m", "add", check=False).returncode == 0


def test_a_statement_file_cannot_be_committed(repo):
    (repo / "jan.pdf").write_bytes(b"%PDF-1.4")
    git(repo, "add", "jan.pdf")
    r = git(repo, "commit", "-m", "add", check=False)
    assert r.returncode != 0 and "jan.pdf" in r.stderr


def test_a_commit_message_with_a_private_term_is_blocked(repo):
    (repo / "a.txt").write_text("hello\n")
    git(repo, "add", "a.txt")
    r = git(repo, "commit", "-m", "fix for Jane Doe", check=False)
    assert r.returncode != 0 and "commit message" in r.stderr or "text" in r.stderr


def test_push_is_blocked_when_an_earlier_commit_slipped_past(repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    (repo / "ok.txt").write_text("fine\n")
    git(repo, "add", "ok.txt")
    git(repo, "commit", "-q", "-m", "ok")
    assert git(repo, "push", "-q", "origin", "main", check=False).returncode == 0
    (repo / "bad.txt").write_text("Maple Street 12\n")
    git(repo, "add", "bad.txt")
    git(repo, "commit", "-q", "--no-verify", "-m", "sneaky")           # someone skipped the commit check
    (repo / "later.txt").write_text("fine again\n")
    git(repo, "add", "later.txt")
    git(repo, "commit", "-q", "-m", "later")
    r = git(repo, "push", "origin", "main", check=False)
    assert r.returncode != 0 and "bad.txt" in r.stderr
    remote_log = subprocess.run(["git", "-C", str(remote), "log", "--oneline"], capture_output=True, text=True).stdout
    assert "sneaky" not in remote_log and "later" not in remote_log      # nothing reached the remote


def test_this_repository_s_own_history_is_clean(monkeypatch):
    monkeypatch.delenv("PRIVACY_TERMS_FILE", raising=False)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "privacy_scan.py"), "--all"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------- the scanner's own commands and corners

def temp_repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "T")
    monkeypatch.chdir(r)
    return r


def test_terms_file_formats_and_the_environment_override(tmp_path, monkeypatch):
    f = tmp_path / "t"
    f.write_text("\n# a comment\n   \nplain term\nre:^start\\d+$\n")
    monkeypatch.setenv("PRIVACY_TERMS_FILE", str(f))
    terms = ps.load_terms()
    assert len(terms) == 2
    assert ps.scan_line("the Plain Term here", terms) and not ps.scan_line("plainterm", terms) and ps.scan_line("start123", terms)
    monkeypatch.setenv("PRIVACY_TERMS_FILE", str(tmp_path / "missing"))
    assert ps.load_terms() == []


def test_findings_never_repeat_the_matched_text_and_kinds_are_listed_once():
    kinds = ps.scan_line("mail a.b@family-mail.org and c.d@family-mail.org", [])  # privacy: allow
    assert kinds == ["an email address"]
    assert ps.mask("secret-value") == "se…e" and ps.mask("ab") == "…" and ps.mask("  ") == "…"


def test_luhn_accepts_real_card_checksums_only():
    assert ps.luhn("4111111111111111") and ps.luhn("5500005555555559") and not ps.luhn("4111111111111112")  # privacy: allow


def test_scan_staged_range_and_all_in_a_scratch_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("PRIVACY_TERMS_FILE", raising=False)
    monkeypatch.setattr(ps, "TERMS_FILE", tmp_path / "none")
    repo = temp_repo(tmp_path, monkeypatch)
    (repo / "good.txt").write_text("nothing here\n")
    git(repo, "add", ".")
    assert ps.main(["--staged"]) == 0
    git(repo, "commit", "-q", "-m", "first")
    (repo / "bad.txt").write_text("call 415-555-0134 about it\n")  # privacy: allow
    (repo / "old.txt").write_text("x\n")
    git(repo, "add", ".")
    assert ps.main(["--staged"]) == 1
    git(repo, "commit", "-q", "-m", "mail the owner at a.b@family-mail.org", "--no-verify")  # privacy: allow
    assert ps.main(["--all"]) == 1
    assert ps.main(["--range", "HEAD~1..HEAD"]) == 1
    findings = ps.scan_range(["--all"], [])
    where = {w for w, _ in findings}
    assert any(w.startswith("commit message") for w in where) and any(w.endswith("bad.txt") for w in where)
    git(repo, "rm", "-q", "bad.txt")
    assert ps.main(["--staged"]) == 0                                       # a deletion adds nothing personal


def test_text_mode_reads_a_file_or_standard_input(tmp_path, monkeypatch, capsys):
    f = tmp_path / "msg"
    f.write_text("fine message\n")
    assert ps.main(["--text", str(f)]) == 0
    f.write_text("call 415-555-0134\n")  # privacy: allow
    assert ps.main(["--text", str(f)]) == 1 and "text: a phone number" in capsys.readouterr().err
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("ssn 123-45-6789\n"))  # privacy: allow
    assert ps.main(["--text", "-"]) == 1


def test_a_clean_report_is_silent_and_a_dirty_one_explains_how_to_fix_it(capsys):
    assert ps.report([]) == 0 and capsys.readouterr().err == ""
    assert ps.report([("a.txt", "an email address"), ("a.txt", "an email address"), ("b.txt", "a phone number")]) == 1
    err = capsys.readouterr().err
    assert err.count("a.txt: an email address") == 1 and "privacy: allow" in err and "*.local" in err


def test_pre_push_ignores_branch_deletion_and_scans_new_branches(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_TERMS_FILE", str(tmp_path / "none"))
    repo = temp_repo(tmp_path, monkeypatch)
    remote = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "config", "core.hooksPath", str(ROOT / ".githooks"))
    (repo / "a.txt").write_text("fine\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "ok")
    assert git(repo, "push", "-q", "origin", "main:feature", check=False).returncode == 0            # a new branch on the remote
    assert git(repo, "push", "-q", "origin", ":feature", check=False).returncode == 0                # deleting it needs no scan
    (repo / "b.txt").write_text("a.b@family-mail.org\n")  # privacy: allow
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--no-verify", "-m", "slipped")
    r = git(repo, "push", "origin", "main:brandnew", check=False)
    assert r.returncode != 0 and "b.txt" in r.stderr


def test_scan_diff_copes_with_a_header_it_cannot_read():
    assert ps.scan_diff("diff --git unusual header\n+call 415-555-0134\n", []) == [("", "a phone number")]  # privacy: allow


def test_a_statement_file_in_a_diff_is_flagged_by_name_even_with_no_added_lines():
    assert ps.scan_diff("diff --git a/jan.pdf b/jan.pdf\nBinary files differ\n", []) == [("jan.pdf", "a statement, data or credential file")]
