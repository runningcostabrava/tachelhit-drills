"""Esborrar una presa de veu: només qui la va gravar, o un administrador.

`DELETE /recordings/{id}` no comprovava res: amb el número d'una gravació, qualsevol —ni calia
estar registrat— podia esborrar la veu de qualsevol altre. El seu germà `PATCH`, que només canvia
el text i el poble, sí que ho comprovava.

En aquesta biblioteca una gravació és la cosa que més costa d'aconseguir: algú ha hagut de dir la
frase. No es torna a fer sola.
"""
import io

import main
from test_api import client


def _user(name, **kw):
    r = client.post("/users/register", json={"username": name, **kw}).json()
    return {"X-User-Token": r["token"]}


def _grava(drill_id, headers, monkeypatch, fitxer="rec_x.webm"):
    monkeypatch.setattr(main.cloudinary.uploader, "upload",
                        lambda *a, **k: {"secure_url": f"https://res.cloudinary.com/x/video/upload/v1/tachelhit/recordings/{fitxer}"})
    r = client.post(f"/drills/{drill_id}/recordings",
                    files={"file": ("take.webm", io.BytesIO(b"abc"), "audio/webm")},
                    headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_la_veu_dun_altre_no_la_pot_esborrar_ningu(monkeypatch):
    d = client.post("/drills/", json={"text_catalan": "aigua", "text_tachelhit": "aman"}).json()
    halima = _user("esb_halima", variety="tdl", region="Aït Mraw (Azilal)")
    _grava(d["id"], halima, monkeypatch, "rec_halima.webm")

    totes = client.get(f"/drills/{d['id']}/recordings", headers=halima).json()
    assert len(totes) == 1
    rec_id = totes[0]["id"]

    # un altre registrat: no pot
    driss = _user("esb_driss", variety="shi", region="Taroudant")
    r = client.delete(f"/recordings/{rec_id}", headers=driss)
    assert r.status_code == 403

    # ningú registrat: tampoc
    from test_api import as_stranger
    with as_stranger():
        assert client.delete(f"/recordings/{rec_id}").status_code in (401, 403)

    # i la veu hi segueix sent
    assert len(client.get(f"/drills/{d['id']}/recordings").json()) == 1


def test_qui_la_va_gravar_si_que_la_pot_esborrar(monkeypatch):
    d = client.post("/drills/", json={"text_catalan": "pa", "text_tachelhit": "aɣrum"}).json()
    halima = _user("esb_halima2", variety="tdl", region="Aït Mraw (Azilal)")
    _grava(d["id"], halima, monkeypatch, "rec_halima2.webm")
    rec_id = client.get(f"/drills/{d['id']}/recordings", headers=halima).json()[0]["id"]

    assert client.delete(f"/recordings/{rec_id}", headers=halima).status_code == 200
    assert client.get(f"/drills/{d['id']}/recordings").json() == []


def test_la_presa_diu_si_es_teva_i_no_de_qui_es(monkeypatch):
    d = client.post("/drills/", json={"text_catalan": "sol", "text_tachelhit": "tafukt"}).json()
    halima = _user("esb_halima3", variety="tdl", region="Aït Mraw (Azilal)")
    driss = _user("esb_driss3", variety="shi", region="Taroudant")
    _grava(d["id"], halima, monkeypatch, "rec_h3.webm")

    seva = client.get(f"/drills/{d['id']}/recordings", headers=halima).json()[0]
    altra = client.get(f"/drills/{d['id']}/recordings", headers=driss).json()[0]
    anonim = client.get(f"/drills/{d['id']}/recordings").json()[0]

    assert seva["mine"] is True
    assert altra["mine"] is False and anonim["mine"] is False
    # qui l'ha gravada no es diu mai: només si ets tu
    assert "user_id" not in seva and "user_id" not in altra
