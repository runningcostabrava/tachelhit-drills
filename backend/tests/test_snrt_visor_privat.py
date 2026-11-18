"""El visor privat de Tamazight TV: només administradors; res a les exportacions (docs/adr/0012)."""
import main
from test_api import client

EP = {"titol": "TADFI N TSKLA - PROVA", "url_pagina": "https://forja.ma/player/x", "durada": 60.0,
      "linies": [{"k": 0, "t_ini": 1.0, "t_fi": 4.0, "tifinag": "ⴰⵣⵓⵍ", "arab": "مرحبا", "catala": "hola", "catala_estat": "acord"},
                 {"k": 1, "t_ini": 4.0, "t_fi": 6.0, "tifinag": "ⵜⴰⵎⴰⵣⵉⵖⵜ", "arab": "الأمازيغية", "catala": None}]}


def _entra(email, username, monkeypatch, admin):
    main._register_attempts.clear(); main._login_attempts.clear()
    monkeypatch.setenv("ADMIN_EMAILS", "boss-snrt@example.com" if admin else "ningu@example.com")
    r = client.post("/auth/signup", json={"email": email, "password": "secret-123", "username": username})
    if r.status_code == 409:   # el compte ja existeix d'una altra prova: entra-hi
        r = client.post("/auth/login", json={"login": email, "password": "secret-123"})
    assert r.status_code == 200, r.text
    return {"X-User-Token": r.json()["token"]}


def test_anonim_i_usuari_normal_no_hi_entren(monkeypatch):
    assert client.get("/snrt-privat/").status_code in (401, 403)
    assert client.get("/snrt-privat/x").status_code in (401, 403)
    assert client.post("/snrt-privat/x/importa", json=EP).status_code in (401, 403)
    h = _entra("simple-snrt@example.com", "simplesnrt", monkeypatch, admin=False)
    if client.get("/users/me", headers=h).json().get("is_admin"):   # el primer usuari d'una base buida és admin: no és aquest cas
        return
    assert client.get("/snrt-privat/", headers=h).status_code == 403
    assert client.post("/snrt-privat/x/importa", json=EP, headers=h).status_code == 403


def test_admin_importa_llista_i_llegeix(monkeypatch):
    h = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    assert client.get("/users/me", headers=h).json()["is_admin"] is True
    assert client.post("/snrt-privat/prova-1/importa", json={"titol": "", "linies": []}, headers=h).status_code == 400
    assert client.post("/snrt-privat/prova-1/importa", json=EP, headers=h).json() == {"slug": "prova-1", "linies": 2}
    assert client.post("/snrt-privat/prova-1/importa", json=EP, headers=h).status_code == 200   # idempotent: substitueix
    ll = client.get("/snrt-privat/", headers=h).json()["episodis"]
    e = [x for x in ll if x["slug"] == "prova-1"][0]
    assert e["linies"] == 2 and e["amb_catala"] == 1
    d = client.get("/snrt-privat/prova-1", headers=h).json()
    assert [l["catala"] for l in d["linies"]] == ["hola", None] and "sense revisar" in d["avis"]
    assert client.get("/snrt-privat/no-existeix", headers=h).status_code == 404


def test_no_surt_a_cap_exportacio_ni_al_corpus(monkeypatch):
    h = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    client.post("/snrt-privat/prova-2/importa", json=EP, headers=h)
    for ruta in ("/corpus/flywheel?format=jsonl", "/drills", "/corpus"):
        r = client.get(ruta)
        assert "TADFI N TSKLA - PROVA" not in r.text, ruta
        assert "الأمازيغية" not in r.text, ruta
