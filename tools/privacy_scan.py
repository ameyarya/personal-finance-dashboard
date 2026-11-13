#!/usr/bin/env python3
"""Stop personal information from reaching git.

Run by the git hooks in .githooks/ before every commit and push, and by CI. It looks at what is about to be
committed (added lines, file names, commit messages) for:

  * your own terms, listed one per line in .privacy-terms.local (names, employer, landlord, street, merchants,
    account digits; a line starting with "re:" is a regular expression). That file is ignored by git;
  * patterns that are personal in any project: email addresses, phone numbers, card numbers, SSNs, tokens,
    home-folder paths, home-network addresses;
  * files that hold statements or credentials (pdf, csv, xlsx, certificates, users.json, ...).

Usage:
  privacy_scan.py --staged            what `git commit` would record
  privacy_scan.py --range A..B        commits in a range (messages and changes)
  privacy_scan.py --all               every commit on every branch
  privacy_scan.py --text FILE|-       check some text, for example a draft commit message

Exit status 1 when anything is found. A finding never prints the whole match, only where it is and what kind.
A line that carries the words  privacy: allow  is skipped.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS_FILE = ROOT / ".privacy-terms.local"

EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![A-Za-z0-9-])")
SAFE_EMAIL = re.compile(r"(@users\.noreply\.github\.com|@example\.(com|org|net)|@(localhost|test|invalid)$|^(git|noreply|no-reply)@)", re.I)
PHONE = re.compile(r"(?<![\w.])(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w.])")
SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
LONG_DIGITS = re.compile(r"(?<![\d.])\d{13,19}(?![\d.])")
HOME_PATH = re.compile(r"(/Users/|/home/|C:\\Users\\)(?!you\b|name\b|user\b|me\b|someone\b|runner\b|<)[A-Za-z0-9._-]{2,}")
LAN_IP = re.compile(r"(?<![\d.])(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?![\d.])")
TOKEN = re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----)")
BAD_FILES = re.compile(r"(\.(pdf|csv|psv|xlsx?|ofx|qfx|pem|key|p12|pfx|bak|bundle)$|(^|/)(users|sessions|data|secrets)\.json$|(^|/)\.env|\.local(\.json)?$|(^|/)data/|(^|/)statements/)", re.I)
BAD_FILE_OK = re.compile(r"(^|/)(\.privacy-terms\.local\.example|rules\.example\.json|requirements.*\.txt)$")


def luhn(digits):
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total, alt = total + d, not alt
    return total % 10 == 0


def load_terms():
    path = Path(os.environ.get("PRIVACY_TERMS_FILE") or TERMS_FILE)
    terms = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            terms.append(re.compile(line[3:], re.I) if line.startswith("re:") else re.compile(r"(?<![A-Za-z0-9])" + re.escape(line) + r"(?![A-Za-z0-9])", re.I))
    return terms


def mask(s):
    s = s.strip()
    return s[:2] + "…" + s[-1:] if len(s) > 4 else "…"


def scan_line(line, terms):
    """What looks personal in one line of text: a list of kinds."""
    if "privacy: allow" in line:
        return []
    found = []
    for t in terms:
        if t.search(line):
            found.append("one of your private terms")
    for m in EMAIL.finditer(line):
        if not SAFE_EMAIL.search(m.group(0)):
            found.append("an email address")
    if PHONE.search(line) and len(re.sub(r"\D", "", PHONE.search(line).group(0))) >= 10:
        found.append("a phone number")
    if SSN.search(line):
        found.append("a social security number pattern")
    for m in LONG_DIGITS.finditer(line):
        if luhn(m.group(0)):
            found.append("a card number")
    if HOME_PATH.search(line):
        found.append("a folder path with a user name")
    if LAN_IP.search(line):
        found.append("a home-network address")
    if TOKEN.search(line):
        found.append("a token or private key")
    return sorted(set(found))


def scan_path(path):
    if BAD_FILES.search(path) and not BAD_FILE_OK.search(path):
        return ["a statement, data or credential file"]
    return []


def run(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout     # the repository we were started in


def scan_diff(text, terms, label=""):
    """Scan unified diff text (git diff -U0 or git log -p -U0). Returns findings as (where, kind)."""
    findings, current = [], ""
    for line in text.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            current = m.group(1) if m else ""
            for kind in scan_path(current):
                findings.append(("%s%s" % (label, current), kind))
        elif line.startswith("+") and not line.startswith("+++"):
            for kind in scan_line(line[1:], terms):
                findings.append(("%s%s" % (label, current), kind))
    return findings


def scan_staged(terms):
    names = run("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    out = [(p, k) for p in names.splitlines() for k in scan_path(p)]
    return out + scan_diff(run("diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR"), terms)


def scan_range(rng, terms):
    findings = []
    for sha in run("rev-list", "--reverse", *rng).split():
        short = sha[:7]
        for line in run("log", "-1", "--format=%B", sha).splitlines():
            for kind in scan_line(line, terms):
                findings.append(("commit message " + short, kind))
        findings += scan_diff(run("show", "--format=", "-U0", "--no-color", "--diff-filter=ACMR", sha), terms, short + ":")
    return findings


def report(findings):
    if not findings:
        return 0
    print("\nPersonal information check FAILED. Nothing was committed or pushed.\n", file=sys.stderr)
    seen = set()
    for where, kind in findings:
        if (where, kind) not in seen:
            seen.add((where, kind))
            print("  %s: %s" % (where, kind), file=sys.stderr)
    print("\nRemove it (use invented names and numbers), or keep it in a *.local file that git ignores.\n"
          "If it is a false alarm, add 'privacy: allow' to that line.\n", file=sys.stderr)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--range", nargs="+", metavar="REV")
    g.add_argument("--all", action="store_true")
    g.add_argument("--text", metavar="FILE")
    a = ap.parse_args(argv)
    terms = load_terms()
    if a.staged:
        found = scan_staged(terms)
    elif a.all:
        found = scan_range(["--all"], terms)
    elif a.range:
        found = scan_range(a.range, terms)
    else:
        text = sys.stdin.read() if a.text == "-" else Path(a.text).read_text(encoding="utf-8")
        found = [("text", k) for line in text.splitlines() for k in scan_line(line, terms)]
    return report(found)


if __name__ == "__main__":
    sys.exit(main())
