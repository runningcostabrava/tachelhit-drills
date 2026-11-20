"""El visor de Tamazight TV: el TEXT és obert, el vídeo i l'escriptura no; res a les exportacions.

Des del 20-11-2026 (ADR 0013, decisió d'en Pablo) la llista i el text d'un episodi els pot
llegir qualsevol, perquè el vídeo no el serveix ningú: el posa qui mira, des del seu disc. El que
segueix tancat és `/video` —que dóna un enllaç signat al vídeo que tenim allotjat— i `importa`,
que escriu.
"""
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


def test_el_text_el_llegeix_qualsevol_pero_escriure_no(monkeypatch):
    """Sense cap compte es pot MIRAR; per escriure-hi segueix calent ser administrador."""
    assert client.get("/snrt-privat/").status_code == 200
    assert client.get("/snrt-privat/x").status_code == 404          # no existeix, no «no hi entres»
    assert client.post("/snrt-privat/x/importa", json=EP).status_code in (401, 403)
    h = _entra("simple-snrt@example.com", "simplesnrt", monkeypatch, admin=False)
    if client.get("/users/me", headers=h).json().get("is_admin"):   # el primer usuari d'una base buida és admin: no és aquest cas
        return
    assert client.get("/snrt-privat/", headers=h).status_code == 200
    assert client.post("/snrt-privat/x/importa", json=EP, headers=h).status_code == 403


def test_el_video_allotjat_segueix_tancat(monkeypatch):
    """Obrir el text no obre el vídeo: `/video` dóna un enllaç signat al que tenim allotjat.

    Aquesta és la ratlla de l'ADR 0013. El vídeo d'un episodi el posa qui mira des del seu disc;
    el que tenim nosaltres no es reparteix a qui passi per l'adreça.
    """
    h = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    client.post("/snrt-privat/prova-0/importa", json=EP, headers=h)
    assert client.get("/snrt-privat/prova-0").status_code == 200    # el text, sí
    assert client.get("/snrt-privat/prova-0/video").status_code in (401, 403)


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


def test_convidat_de_la_snrt_veu_el_visor_pero_no_importa(monkeypatch):
    h_admin = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    client.post("/snrt-privat/prova-3/importa", json=EP, headers=h_admin)
    monkeypatch.setenv("SNRT_VIEWER_EMAILS", "convidat-snrt@example.com")
    h = _entra("convidat-snrt@example.com", "convidatsnrt", monkeypatch, admin=False)
    monkeypatch.setenv("SNRT_VIEWER_EMAILS", "convidat-snrt@example.com")
    assert client.get("/snrt-privat/", headers=h).status_code == 200
    assert client.get("/snrt-privat/prova-3", headers=h).status_code == 200
    assert client.post("/snrt-privat/prova-3/importa", json=EP, headers=h).status_code == 403   # no és administrador
    #: el text ja el veu tothom; el que li dóna ser convidat de la SNRT és el vídeo allotjat
    monkeypatch.setenv("SNRT_VIDEO_BASE", "https://v.example.org/")
    monkeypatch.setenv("SNRT_VIDEO_SECRET", "s3cret")
    assert client.get("/snrt-privat/prova-3/video", headers=h).json()["url"].startswith("https://v.example.org/")
    assert client.get("/snrt-privat/prova-3/video").status_code in (401, 403)


def test_video_signat_nomes_amb_base_i_secret(monkeypatch):
    import hashlib, hmac
    h = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    client.post("/snrt-privat/prova-4/importa", json=EP, headers=h)
    monkeypatch.delenv("SNRT_VIDEO_BASE", raising=False); monkeypatch.delenv("SNRT_VIDEO_SECRET", raising=False)
    assert client.get("/snrt-privat/prova-4/video", headers=h).json() == {"url": None}
    monkeypatch.setenv("SNRT_VIDEO_BASE", "https://v.example.org/"); monkeypatch.setenv("SNRT_VIDEO_SECRET", "s3cret")
    j = client.get("/snrt-privat/prova-4/video", headers=h).json()
    base, q = j["url"].split("?")
    assert base == "https://v.example.org/v/prova-4"
    par = dict(x.split("=") for x in q.split("&"))
    assert par["sig"] == hmac.new(b"s3cret", f"prova-4.{par['exp']}".encode(), hashlib.sha256).hexdigest()
    assert client.get("/snrt-privat/no-existeix/video", headers=h).status_code == 404
    assert client.get("/snrt-privat/prova-4/video").status_code in (401, 403)


def test_el_que_sent_el_nostre_model_va_en_un_camp_a_part(monkeypatch):
    """El subtitol de la cadena i el que sent el transcriptor NO es barregen.

    El text de la SNRT va en norma de l'IRCAM i el transcriptor sent la parla dialectal: sovint
    no diuen el mateix, i aquesta diferencia es justament el que es vol poder mirar. Si una cosa
    sobreescrivis l'altra, es perdria el material; per aixo son dos camps.
    """
    h = _entra("boss-snrt@example.com", "bosssnrt", monkeypatch, admin=True)
    ep = {"titol": "Amb el que sentim", "linies": [
        {"k": 0, "t_ini": 1.0, "t_fi": 4.0, "tifinag": "ⴰⵣⵓⵍ", "catala": "hola",
         "sentit": "ⴰⵣⵓ"},
        {"k": 1, "t_ini": 5.0, "t_fi": 7.0, "tifinag": "ⴰⵣⵓⵍ"}]}
    assert client.post("/snrt-privat/prova-sentit/importa", json=ep, headers=h).json()["linies"] == 2
    linies = client.get("/snrt-privat/prova-sentit", headers=h).json()["linies"]
    assert [l["sentit"] for l in linies] == ["ⴰⵣⵓ", None]
    #: i el de la cadena no s'ha mogut
    assert [l["tifinag"] for l in linies] == ["ⴰⵣⵓⵍ", "ⴰⵣⵓⵍ"]
