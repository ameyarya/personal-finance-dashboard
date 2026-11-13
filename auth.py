"""Sign-in for the dashboard: salted password hashes, server-side sessions, and a brake on password guessing.

Standard library only. Everything lives in two files beside data.json: users.json (names and password hashes)
and sessions.json (hashes of session tokens). Neither ever holds a password or a usable token.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

ITERATIONS = 240_000
MIN_LENGTH = 8
SESSION_DAYS = 30
MAX_FAILS = 5
LOCK_SECONDS = 60


def _hash(password, salt, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()


class AuthError(ValueError):
    """A message that is safe to show the person typing."""


class Auth:
    def __init__(self, folder):
        self.users_file = os.path.join(str(folder), "users.json")
        self.sessions_file = os.path.join(str(folder), "sessions.json")
        self.lock = threading.RLock()
        self.fails = {}
        self.required, self.users, self.sessions = False, {}, {}
        self._dummy = (os.urandom(16), _hash("x", b"0" * 16))
        self._load()

    # ------------------------------------------------------------ storage
    def _load(self):
        try:
            with open(self.users_file, encoding="utf-8") as f:
                data = json.load(f)
            self.required, self.users = bool(data.get("required")), data.get("users", {})
        except (OSError, ValueError):
            pass
        try:
            with open(self.sessions_file, encoding="utf-8") as f:
                self.sessions = json.load(f)
        except (OSError, ValueError):
            pass
        self._purge()

    def _write(self, path, data):
        tmp = path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)

    def _save(self):
        self._write(self.users_file, {"required": self.required, "users": self.users})
        self._write(self.sessions_file, self.sessions)

    def _purge(self):
        now = time.time()
        self.sessions = {k: v for k, v in self.sessions.items() if v.get("exp", 0) > now and v.get("user") in self.users}

    # ------------------------------------------------------------ state
    def enabled(self):
        return bool(self.required and self.users)

    def names(self):
        with self.lock:
            return [u["name"] for u in self.users.values()]

    def _key(self, name):
        return str(name or "").strip().lower()

    # ------------------------------------------------------------ passwords
    def _check_new(self, password):
        if not isinstance(password, str) or len(password) < MIN_LENGTH:
            raise AuthError("Use at least %d characters for the password." % MIN_LENGTH)
        if len(password) > 200:
            raise AuthError("That password is too long.")

    def set_password(self, name, password, require=True):
        name = str(name or "").strip()
        if not name or len(name) > 60:
            raise AuthError("Pick a name first.")
        self._check_new(password)
        salt = os.urandom(16)
        with self.lock:
            self.users[self._key(name)] = {"name": name, "salt": salt.hex(), "hash": _hash(password, salt), "iter": ITERATIONS, "created": int(time.time())}
            if require:
                self.required = True
            self._save()

    def verify(self, name, password):
        """True or False in the same time whether or not the name exists."""
        with self.lock:
            u = self.users.get(self._key(name))
        salt, want = (bytes.fromhex(u["salt"]), u["hash"]) if u else self._dummy
        got = _hash(password if isinstance(password, str) else "", salt, u.get("iter", ITERATIONS) if u else ITERATIONS)
        return bool(u) and hmac.compare_digest(got, want)

    def change_password(self, name, current, new, keep_token=None):
        if not self.verify(name, current):
            raise AuthError("The current password is not right.")
        self.set_password(name, new, require=False)
        self.drop_sessions(name, keep=keep_token)     # other devices must sign in again; this one stays signed in

    def remove_user(self, name):
        with self.lock:
            self.users.pop(self._key(name), None)
            if not self.users:
                self.required = False
            self._purge()
            self._save()

    def set_required(self, on):
        with self.lock:
            self.required = bool(on) and bool(self.users)
            self._save()

    # ------------------------------------------------------------ sessions
    def login(self, name, password, ip):
        now = time.time()
        with self.lock:
            count, until = self.fails.get(ip, (0, 0))
            if until > now:
                raise AuthError("Too many tries. Wait %d seconds and try again." % int(until - now + 1))
        if not self.verify(name, password):
            with self.lock:
                count += 1
                self.fails[ip] = (count, now + LOCK_SECONDS * (count // MAX_FAILS) if count % MAX_FAILS == 0 else 0)
            raise AuthError("That name and password do not match.")
        with self.lock:
            self.fails.pop(ip, None)
            token = secrets.token_urlsafe(32)
            u = self.users[self._key(name)]
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = {"user": self._key(name), "exp": now + SESSION_DAYS * 86400}
            self._purge()
            self._save()
            return token, u["name"]

    def session_user(self, token):
        if not token:
            return None
        with self.lock:
            s = self.sessions.get(hashlib.sha256(token.encode()).hexdigest())
            if not s or s["exp"] < time.time():
                return None
            u = self.users.get(s["user"])
            return u["name"] if u else None

    def logout(self, token):
        with self.lock:
            self.sessions.pop(hashlib.sha256((token or "").encode()).hexdigest(), None)
            self._save()

    def drop_sessions(self, name, keep=None):
        with self.lock:
            k = self._key(name)
            keep_h = hashlib.sha256(keep.encode()).hexdigest() if keep else None
            self.sessions = {h: s for h, s in self.sessions.items() if s["user"] != k or h == keep_h}
            self._save()
