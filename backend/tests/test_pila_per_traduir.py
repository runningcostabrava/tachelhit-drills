"""La traducció de màquina només passa al català de la frase si una persona la confirma (#494)."""
import main
from test_api import client


_n = [0]


def _admin():
    _n[0] += 1
    nom = "traduir_admin_%d" % _n[0]
    u = client.post("/users/register", json={"username": nom}).json()
    with main.SessionLocal() as db:
        db.query(main.UserModel).filter(main.UserModel.username == nom).update({"is_admin": True})
        db.commit()
    return {"X-User-Token": u["token"]}


def _drill(proposta):
    db = main.SessionLocal()
    try:
        d = main.DrillModel(text_tachelhit="azul fellawn", text_catalan_suggested=proposta, tag="per-traduir")
        db.add(d)
        db.commit()
        return d.id
    finally:
        db.close()


def _llegeix(i):
    db = main.SessionLocal()
    try:
        d = db.get(main.DrillModel, i)
        return d.text_catalan, d.text_catalan_suggested, d.tag
    finally:
        db.close()


def test_es_desa_el_que_la_persona_deixa_a_la_caixa():
    hdr, i = _admin(), _drill("bon dia a tu")
    r = client.post("/revisa/per-traduir", headers=hdr, json={"drill_id": i, "opcio": "tria", "esborrany": "bon dia"})
    assert r.status_code == 200
    assert _llegeix(i) == ("bon dia", None, None)


def test_no_serveix_treu_la_proposta_i_no_toca_el_catala():
    hdr, i = _admin(), _drill("una altra cosa")
    assert client.post("/revisa/per-traduir", headers=hdr, json={"drill_id": i, "opcio": "fora"}).status_code == 200
    assert _llegeix(i)[1:] == (None, None) and not _llegeix(i)[0]


def test_no_ho_se_no_toca_res():
    hdr, i = _admin(), _drill("potser")
    client.post("/revisa/per-traduir", headers=hdr, json={"drill_id": i, "opcio": "no-ho-se"})
    assert _llegeix(i)[1:] == ("potser", "per-traduir")


def test_sense_sessio_dadministrador_no_es_pot():
    i = _drill("res")
    assert client.post("/revisa/per-traduir", json={"drill_id": i, "opcio": "tria"}).status_code in (401, 403)
    assert _llegeix(i)[1] == "res"
