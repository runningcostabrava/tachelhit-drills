"""En pujar una veu, el servidor diu si és la de la targeta (#556).

Qui grava vol saber què hi ha entès la màquina —és per això que serveix: per saber si el que ha
quedat val o cal tornar-ho a dir. Però la lectura només té on desar-se quan aquella presa és la
veu de la targeta: `text_tachelhit_suggested` és un sol camp i parla de `drill.audio_url`. Si es
desés la lectura d'una presa qualsevol, la fitxa diria que la màquina hi ha entès una cosa que
no és del so que hi sona.

La regla de qui passa a principal ja viu al servidor (la primera veu d'una frase muda, i no si és
d'algú que aprèn). Dir-ho a la resposta estalvia al davant tornar-la a endevinar, que és com es
desincronitzen les dues.
"""
import io

import main


def _sense_cloudinary(monkeypatch, nom="rec_prova.webm"):
    """A la CI no hi ha Cloudinary: la pujada es fa de mentida, que no és el que es mesura aquí."""
    monkeypatch.setattr(
        main.cloudinary.uploader, "upload",
        lambda *a, **k: {"secure_url":
                         f"https://res.cloudinary.com/x/video/upload/v1/tachelhit/recordings/{nom}"})


def _fitxer(nom="veu.webm"):
    return (nom, io.BytesIO(b"RIFF....WEBM" + b"0" * 2048), "audio/webm")


def test_la_primera_veu_duna_frase_muda_es_la_principal(monkeypatch):
    from test_api import client, register
    _sense_cloudinary(monkeypatch)

    hdr = {"X-User-Token": register("qui_grava_la_primera")}
    muda = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la clau", "text_tachelhit": "tasarut"}).json()
    client.put(f"/drills/{muda['id']}", headers=hdr,
               json={"audio_url": None, "audio_tts_shi_url": None})

    r = client.post(f"/drills/{muda['id']}/recordings", headers=hdr,
                    files={"file": _fitxer()}, data={"is_native": "true"})
    assert r.status_code == 200, r.text
    assert r.json()["es_principal"] is True, r.json()
    # I ho diu perquè és veritat.
    assert (client.get(f"/drills/{muda['id']}").json().get("audio_url") or "")

    client.delete(f"/drills/{muda['id']}", headers=hdr)


def test_una_presa_de_mes_no_es_la_principal(monkeypatch):
    """La frase ja té veu: la presa s'hi suma, i la lectura no es desa a la fitxa."""
    from test_api import client, register
    _sense_cloudinary(monkeypatch)

    hdr = {"X-User-Token": register("qui_hi_suma_la_seva")}
    amb_veu = client.post("/drills/", headers=hdr, json={
        "text_catalan": "el camí", "text_tachelhit": "aġaras",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/ja_hi_era.webm"}).json()

    r = client.post(f"/drills/{amb_veu['id']}/recordings", headers=hdr,
                    files={"file": _fitxer("altra.webm")}, data={"is_native": "true"})
    assert r.status_code == 200, r.text
    assert r.json()["es_principal"] is False, r.json()
    assert (client.get(f"/drills/{amb_veu['id']}").json()["audio_url"]).endswith("ja_hi_era.webm")

    client.delete(f"/drills/{amb_veu['id']}", headers=hdr)


def test_la_veu_de_qui_apren_no_mana_i_ho_diu(monkeypatch):
    """Una primera presa d'algú que aprèn no passa a principal, i la resposta no diu que sí."""
    from test_api import client, register
    _sense_cloudinary(monkeypatch)

    hdr = {"X-User-Token": register("qui_apren_i_ho_diu")}
    muda = client.post("/drills/", headers=hdr, json={
        "text_catalan": "el pa", "text_tachelhit": "aġrum"}).json()
    client.put(f"/drills/{muda['id']}", headers=hdr,
               json={"audio_url": None, "audio_tts_shi_url": None})

    r = client.post(f"/drills/{muda['id']}/recordings", headers=hdr,
                    files={"file": _fitxer()}, data={"is_native": "false"})
    assert r.status_code == 200, r.text
    assert r.json()["es_principal"] is False, r.json()

    client.delete(f"/drills/{muda['id']}", headers=hdr)
