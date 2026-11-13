"""Sign-in: password storage, sessions, the lock on password guessing, and the rules the server enforces."""
import json
import re

import pytest

import auth


@pytest.fixture
def store(tmp_path):
    return auth.Auth(tmp_path)


def test_passwords_are_hashed_salted_and_never_written_out(store, tmp_path):
    store.set_password("Una", "correct horse")
    raw = (tmp_path / "users.json").read_text()
    assert "correct horse" not in raw and '"hash"' in raw and '"salt"' in raw
    assert (tmp_path / "users.json").stat().st_mode & 0o077 == 0          # only the owner can read it
    store.set_password("Dos", "correct horse")
    users = json.loads((tmp_path / "users.json").read_text())["users"]
    assert users["una"]["hash"] != users["dos"]["hash"]                    # same password, different salt, different hash


def test_verify_is_case_insensitive_on_names_and_exact_on_passwords(store):
    store.set_password("Una", "correct horse")
    assert store.verify("una", "correct horse") and store.verify("UNA ", "correct horse")
    assert not store.verify("Una", "Correct horse") and not store.verify("nobody", "correct horse") and not store.verify("Una", "")


@pytest.mark.parametrize("bad", ["short", "", None, "x" * 201])
def test_weak_or_absurd_passwords_are_refused(store, bad):
    with pytest.raises(auth.AuthError):
        store.set_password("Una", bad)


def test_session_survives_a_restart_and_logout_ends_it(store, tmp_path):
    store.set_password("Una", "correct horse")
    token, name = store.login("una", "correct horse", "1.1.1.1")
    assert name == "Una" and store.session_user(token) == "Una"
    assert "token" not in (tmp_path / "sessions.json").read_text() and token not in (tmp_path / "sessions.json").read_text()
    again = auth.Auth(tmp_path)
    assert again.session_user(token) == "Una" and again.enabled()
    again.logout(token)
    assert again.session_user(token) is None and auth.Auth(tmp_path).session_user(token) is None


def test_five_wrong_tries_lock_that_address_for_a_minute(store):
    store.set_password("Una", "correct horse")
    for _ in range(5):
        with pytest.raises(auth.AuthError):
            store.login("Una", "wrong wrong", "9.9.9.9")
    with pytest.raises(auth.AuthError, match="Too many tries"):
        store.login("Una", "correct horse", "9.9.9.9")                    # even the right password waits
    token, _ = store.login("Una", "correct horse", "8.8.8.8")             # another address is not affected
    assert token


def test_changing_a_password_ends_other_sessions_but_keeps_this_one(store):
    store.set_password("Una", "correct horse")
    here, _ = store.login("Una", "correct horse", "1.1.1.1")
    elsewhere, _ = store.login("Una", "correct horse", "2.2.2.2")
    with pytest.raises(auth.AuthError):
        store.change_password("Una", "not it", "new password 1", keep_token=here)
    store.change_password("Una", "correct horse", "new password 1", keep_token=here)
    assert store.session_user(here) == "Una" and store.session_user(elsewhere) is None
    assert store.verify("Una", "new password 1") and not store.verify("Una", "correct horse")


def test_removing_the_last_person_turns_sign_in_off(store):
    store.set_password("Una", "correct horse")
    assert store.enabled()
    store.remove_user("Una")
    assert not store.enabled() and store.names() == []


# ---------------------------------------------------------------- through the server

def cookie_of(head):
    m = re.search(r"fd_session=([^;]*)", head.get("Set-Cookie", ""))
    return m.group(1) if m else ""


def test_nothing_is_locked_until_someone_sets_a_password(server):
    assert server.call("GET", "/api/data")[0] == 200
    status, info = server.call("GET", "/api/session")
    assert status == 200 and info["required"] is False and info["user"] is None


def test_setup_locks_everything_and_signs_the_first_person_in(server):
    status, body, head = server.raw("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    assert status == 200 and body["user"] == "Una"
    cookie = head["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    mine = {"Cookie": "fd_session=" + cookie_of(head)}
    assert server.call("GET", "/api/data")[0] == 401                           # no cookie, no data
    assert server.call("PUT", "/api/doc/budgets/x", {"limit": 1})[0] == 401   # and no writes
    assert server.call("POST", "/api/batch", {"writes": []})[0] == 401
    assert server.call("GET", "/api/data", headers=mine)[0] == 200
    assert server.call("GET", "/api/session", headers=mine)[1]["user"] == "Una"
    assert "Sign in" in server.call("GET", "/")[1]                             # the page itself becomes the sign-in page
    assert "<title>Household Money" not in server.call("GET", "/")[1]
    assert server.call("GET", "/app.js")[0] == 401                             # the app's code is not handed out either
    assert server.call("GET", "/app.css")[0] == 200


def test_login_wrong_password_and_the_guessing_brake(server):
    server.call("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    status, body = server.call("POST", "/api/login", {"name": "Una", "password": "nope nope"})
    assert status == 400 and "do not match" in body["error"]
    assert "correct horse" not in json.dumps(body)
    for _ in range(5):
        server.call("POST", "/api/login", {"name": "Una", "password": "nope nope"})
    status, body = server.call("POST", "/api/login", {"name": "Una", "password": "correct horse"})
    assert status == 400 and "Too many tries" in body["error"]


def test_signed_in_person_can_change_password_and_sign_out(server):
    _, _, head = server.raw("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    mine = {"Cookie": "fd_session=" + cookie_of(head)}
    assert server.call("POST", "/api/account/password", {"current": "wrong", "new": "another one 1"}, mine)[0] == 400
    assert server.call("POST", "/api/account/password", {"current": "correct horse", "new": "short"}, mine)[0] == 400
    assert server.call("POST", "/api/account/password", {"current": "correct horse", "new": "another one 1"}, mine)[0] == 200
    assert server.call("GET", "/api/data", headers=mine)[0] == 200             # this device stays signed in
    assert server.call("POST", "/api/login", {"name": "Una", "password": "correct horse"})[0] == 400
    assert server.call("POST", "/api/login", {"name": "Una", "password": "another one 1"})[0] == 200
    assert server.call("POST", "/api/logout", {}, mine)[0] == 200
    assert server.call("GET", "/api/data", headers=mine)[0] == 401


def test_a_signed_in_person_can_give_someone_else_a_first_password_but_not_overwrite_one(server):
    _, _, head = server.raw("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    mine = {"Cookie": "fd_session=" + cookie_of(head)}
    assert server.call("POST", "/api/account/setup", {"name": "Dos", "password": "second person 1"}, mine)[0] == 200
    assert server.call("POST", "/api/account/setup", {"name": "Dos", "password": "hijack hijack 1"}, mine)[0] == 400
    assert server.call("POST", "/api/account/setup", {"name": "Tres", "password": "anonymous pw 1"})[0] == 401   # strangers cannot add people
    assert server.call("POST", "/api/login", {"name": "dos", "password": "second person 1"})[0] == 200


def test_turning_sign_in_off_needs_the_password(server):
    _, _, head = server.raw("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    mine = {"Cookie": "fd_session=" + cookie_of(head)}
    assert server.call("POST", "/api/account/require", {"on": False, "password": "wrong"}, mine)[0] == 400
    assert server.call("POST", "/api/account/require", {"on": False, "password": "correct horse"}, mine)[0] == 200
    assert server.call("GET", "/api/data")[0] == 200                           # open again


def test_cross_site_writes_are_still_refused_when_signed_in(server):
    _, _, head = server.raw("POST", "/api/account/setup", {"name": "Una", "password": "correct horse"})
    mine = {"Cookie": "fd_session=" + cookie_of(head)}
    assert server.call("PUT", "/api/doc/budgets/x", {"limit": 1}, {**mine, "Origin": "https://evil.example"})[0] == 403
