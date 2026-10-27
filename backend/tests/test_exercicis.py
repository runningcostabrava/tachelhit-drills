"""Els exercicis del llibre dins d'un capítol del Mètode (#380).

Tres coses que han de passar i que, si es trenquen, no es veurien fins que algú obrís el capítol:

- que el capítol **se'ls guardi**: `strip_computed` treu del cos tot el que el servidor hi afegeix
  en servir-lo, i una clau nova que hi caigués per descuit desapareixeria en desar;
- que **cada frase porti la seva tifinag**, posada pel servidor i no escrita a mà, com a tot
  arreu de l'app;
- que un ítem **sense resposta** segueixi sortint. El llibre en deixa 160 en blanc a posta perquè
  els faci qui aprèn, i una neteja que els llencés convertiria «fes-ho tu» en «no n'hi ha».
"""
import json

import main
from test_api import client


def _admin(nom):
    """Un administrador per prova.

    Amb un sol nom per a totes, el segon registre xocava amb el primer i tornava un error sense
    testimoni: les proves queien per aixo i no pel que miraven.
    """
    r = client.post("/users/register", json={"username": nom}).json()
    h = {"X-User-Token": r["token"]}
    from models import User
    db = main.SessionLocal()
    try:
        u = db.query(User).filter(User.username == nom).first()
        u.is_admin = True
        db.commit()
    finally:
        db.close()
    return h


COS = {
    "intro": "Un capítol de prova.",
    "sections": [],
    "exercises": [
        {
            "id": "prova-ex1",
            "kind": "ordena",
            "consigna": "Posa les paraules en ordre.",
            "consigna_fr": "Remettez les mots dans l'ordre",
            "model": {"pregunta": {"shi": "aman"}, "resposta": {"shi": "riɣ aman"}},
            "items": [
                {"pregunta": {"shi": "dar-k, is, tudit"},
                 "resposta": {"shi": "is dar-k tudit?"}, "sense_solucio": False},
                {"pregunta": {"shi": "tigmmi, tlla, mani-ɣ"},
                 "resposta": None, "sense_solucio": True},
            ],
            "font": {"obra": "Initiation au tachelhit", "autor": "Abdallah El Mountassir",
                     "any": 1999},
        }
    ],
}


def test_un_capitol_es_guarda_els_exercicis_i_els_serveix_amb_tifinag():
    h = _admin("ex_admin_1")
    r = client.put("/method/salutacions/content", json=COS, headers=h)
    assert r.status_code == 200, r.text

    d = client.get("/method/salutacions").json()["content"]
    ex = d.get("exercises")
    assert ex and len(ex) == 1, "el capítol no s'ha guardat els exercicis"
    e = ex[0]
    assert e["kind"] == "ordena" and e["consigna_fr"] == "Remettez les mots dans l'ordre"
    assert e["font"]["any"] == 1999, "la font de l'exercici s'ha perdut"

    # La tifinag la posa el servidor, a la pregunta i a la resposta.
    it = e["items"][0]
    assert it["pregunta"].get("tif"), "la pregunta ha de portar la seva tifinag"
    assert it["resposta"].get("tif"), "la resposta ha de portar la seva tifinag"
    assert "ⵉⵙ" in it["resposta"]["tif"]

    # I el model, també.
    assert e["model"]["resposta"].get("tif")


def test_un_item_sense_resposta_no_es_llenca():
    h = _admin("ex_admin_2")
    client.put("/method/salutacions/content", json=COS, headers=h)
    e = client.get("/method/salutacions").json()["content"]["exercises"][0]
    assert len(e["items"]) == 2, "l'ítem que el llibre deixa en blanc ha desaparegut"
    buit = e["items"][1]
    assert buit["resposta"] is None and buit["sense_solucio"] is True
    assert buit["pregunta"].get("tif"), "encara que no tingui resposta, la pregunta es llegeix"


def test_desar_dues_vegades_no_duplica_ni_escriu_la_tifinag_al_cos():
    """El capítol es desa tal com es veu, i el que es veu porta la tifinag afegida.

    Sense treure-la en desar, cada correcció del capítol n'hi deixaria una còpia més i el text
    aniria creixent amb tifinag repetida a dins.
    """
    h = _admin("ex_admin_3")
    client.put("/method/salutacions/content", json=COS, headers=h)
    servit = client.get("/method/salutacions").json()["content"]
    client.put("/method/salutacions/content", json=servit, headers=h)

    from models import MethodChapter
    db = main.SessionLocal()
    try:
        row = db.query(MethodChapter).filter(MethodChapter.slug == "salutacions").first()
        cru = json.loads(row.body)
    finally:
        db.close()
    it = cru["exercises"][0]["items"][0]
    assert "tif" not in it["pregunta"], "la tifinag s'ha desat al cos en comptes de calcular-se"
    assert "tif" not in it["resposta"]
