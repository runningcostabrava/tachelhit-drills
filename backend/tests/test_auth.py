"""Accounts: sign-up, sign-in, sessions, attach, change password, forgot without SMTP."""
import pytest
import main
from test_api import client


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Sign-up and sign-in are rate-limited per address; the whole suite shares one."""
    main._register_attempts.clear(); main._login_attempts.clear()
    yield
    main._register_attempts.clear(); main._login_attempts.clear()


def test_signup_login_me_logout(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    r = client.post("/auth/signup", json={"email": "Boss@Example.com", "password": "secret-123", "username": "boss", "display_name": "The Boss"})
    assert r.status_code == 200, r.text
    j = r.json(); tok = j["token"]
    assert j["is_admin"] is True and j["email"] == "boss@example.com" and j["has_password"] is True
    me = client.get("/users/me", headers={"X-User-Token": tok}).json()
    assert me["username"] == "boss" and me["is_admin"] is True
    # wrong password
    assert client.post("/auth/login", json={"login": "boss@example.com", "password": "nope-nope"}).status_code == 401
    # login by username, second device
    r2 = client.post("/auth/login", json={"login": "BOSS", "password": "secret-123", "device": "phone"})
    assert r2.status_code == 200 and r2.json()["token"] != tok
    tok2 = r2.json()["token"]
    assert client.get("/users/me", headers={"X-User-Token": tok2}).status_code == 200
    # logout forgets only that device
    client.post("/auth/logout", headers={"X-User-Token": tok2})
    assert client.get("/users/me", headers={"X-User-Token": tok2}).status_code == 401
    assert client.get("/users/me", headers={"X-User-Token": tok}).status_code == 200
    # duplicates
    assert client.post("/auth/signup", json={"email": "boss@example.com", "password": "secret-123", "username": "boss2"}).status_code == 409
    assert client.post("/auth/signup", json={"email": "x@example.com", "password": "short", "username": "shorty"}).status_code == 400


def test_token_identity_attaches_credentials_and_changes_password():
    main._register_attempts.clear()
    reg = client.post("/users/register", json={"username": "legacy_one"}).json()
    tok = reg["token"]
    assert client.get("/users/me", headers={"X-User-Token": tok}).json()["has_password"] is False
    r = client.post("/auth/attach", json={"email": "legacy@example.com", "password": "legacy-pass-1"}, headers={"X-User-Token": tok})
    assert r.status_code == 200 and r.json()["has_password"] is True
    assert client.post("/auth/login", json={"login": "legacy@example.com", "password": "legacy-pass-1"}).status_code == 200
    bad = client.post("/auth/password", json={"old_password": "wrong", "new_password": "another-pass-1"}, headers={"X-User-Token": tok})
    assert bad.status_code == 401
    ok = client.post("/auth/password", json={"old_password": "legacy-pass-1", "new_password": "another-pass-1"}, headers={"X-User-Token": tok})
    assert ok.status_code == 200
    assert client.post("/auth/login", json={"login": "legacy_one", "password": "another-pass-1"}).status_code == 200


def test_forgot_without_mail_says_so_and_reset_takes_a_code(monkeypatch):
    """A library whose server sends no mail is not broken: it recovers accounts with a code an
    admin hands over, so «forgot» answers calmly instead of raising a fault nobody can act on."""
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        monkeypatch.delenv(k, raising=False)
    main._register_attempts.clear(); main._login_attempts.clear()
    client.post("/auth/signup", json={"email": "r@example.com", "password": "reset-me-123", "username": "resetter"})
    r = client.post("/auth/forgot", json={"email": "r@example.com"})
    assert r.status_code == 200 and r.json() == {"ok": True, "mail": False}
    # with a (fake) sender configured, a code is stored and resets the password
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com"); monkeypatch.setenv("SMTP_USER", "u"); monkeypatch.setenv("SMTP_PASS", "p")
    sent = {}
    monkeypatch.setattr(main, "_send_email", lambda to, subject, body: sent.update(to=to, body=body) or True)
    assert client.post("/auth/forgot", json={"email": "r@example.com"}).status_code == 200
    import re
    code = re.search(r"codi és: (\d{6})", sent["body"]).group(1)
    assert client.post("/auth/reset", json={"email": "r@example.com", "code": "000000", "new_password": "newpass-123"}).status_code == 400
    old_token = client.post("/auth/login", json={"login": "r@example.com", "password": "reset-me-123"}).json()["token"]
    r = client.post("/auth/reset", json={"email": "r@example.com", "code": code, "new_password": "newpass-123"})
    assert r.status_code == 200 and r.json()["token"]
    assert client.post("/auth/login", json={"login": "r@example.com", "password": "newpass-123"}).status_code == 200
    # the session that was open before the reset is dead: a stolen or borrowed one dies here
    assert client.get("/users/me", headers={"X-User-Token": old_token}).status_code == 401


def test_admin_dependency():
    main._register_attempts.clear()  # the tests above used the per-address registration budget
    reg = client.post("/users/register", json={"username": "plain_user"}).json()
    assert "token" in reg, reg
    # require_admin is a dependency; exercise it directly
    from fastapi import HTTPException
    db = main.SessionLocal()
    try:
        u = db.query(main.UserModel).filter(main.UserModel.username == "plain_user").first()
        try:
            main.require_admin(u); assert False, "plain user must not be admin"
        except HTTPException as e:
            assert e.status_code == 403
    finally:
        db.close()
