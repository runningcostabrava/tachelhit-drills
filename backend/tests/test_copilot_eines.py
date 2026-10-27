"""Les eines del copilot: mira la biblioteca abans que la seva memòria (#374).

El copilot sabia molta gramàtica i **no coneixia la biblioteca**: deia que no podia ensenyar les
frases més noves (i l'API sempre ho ha sabut fer), contestava amb números d'identificador, i es
va inventar una paraula per «enfadat» —una arrel que no surt enlloc del nostre corpus— i tot
seguit es va oferir a **sintetitzar-ne la veu**. Això últim és la línia que aquest projecte no
travessa: una veu de màquina damunt d'una paraula inventada sona com si algú l'hagués dita.

Aquí es prova el que ho impedeix, que són les eines mateixes i no la bona voluntat del model.
"""
import main
from test_api import client, register


def _eines():
    db = main.SessionLocal()
    return db, main._agent_executor(db)


def test_la_cerca_sap_el_que_lapi_ja_sabia():
    """«Ensenya'm els últims drills creats» era la pregunta que el copilot deia que no podia
    contestar. Sense cap filtre, l'eina torna les més NOVES; i sap filtrar per qui ho diu, per
    etiqueta i per les que encara no tenen veu."""
    hdr = {"X-User-Token": register("copilot_cerca")}
    vella = client.post("/drills/", headers=hdr, json={
        "text_catalan": "una frase vella", "text_tachelhit": "awal aqdim", "tag": "copilot-prova"}).json()
    nova = client.post("/drills/", headers=hdr, json={
        "text_catalan": "una frase nova", "text_tachelhit": "awal amaynu", "tag": "copilot-prova",
        "author": "Halima", "audio_url": "https://res.cloudinary.com/x/video/upload/v1/c.mp3"}).json()

    db, run = _eines()
    try:
        ultimes = run("search_drills", {"limit": 5})
        assert ultimes["drills"], "sense filtres, torna les últimes"
        assert ultimes["drills"][0]["id"] >= nova["id"], "les més noves primer"

        per_etiqueta = run("search_drills", {"tag": "copilot-prova", "limit": 10})
        assert {d["id"] for d in per_etiqueta["drills"]} >= {vella["id"], nova["id"]}

        de_halima = run("search_drills", {"author": "Halima", "limit": 10})
        assert nova["id"] in {d["id"] for d in de_halima["drills"]}

        mudes = run("search_drills", {"tag": "copilot-prova", "without_voice": True, "limit": 10})
        quines = {d["id"] for d in mudes["drills"]}
        assert vella["id"] in quines and nova["id"] not in quines

        # i cada frase surt sencera, per poder-la ENSENYAR en comptes de dir-ne el número
        una = next(d for d in per_etiqueta["drills"] if d["id"] == nova["id"])
        assert una["tachelhit"] and una["catalan"] and una["tif"], una
        assert "speaker" in una and "audio_url" in una

        # i que no n'hi hagi cap també és una resposta
        cap = run("search_drills", {"query": "zzzzz-aixo-no-hi-es", "limit": 5})
        assert cap["count"] == 0 and cap["diu"] == "la biblioteca no en té cap"
    finally:
        db.close()


def test_no_es_pot_fer_sonar_una_paraula_que_ningu_no_ha_dit():
    """La paraula inventada («iɣḍdn» per «enfadat») no és a cap frase nostra: l'eina no la fa
    sonar i diu per què, de manera que el copilot ho ha de dir en comptes d'oferir-ho."""
    hdr = {"X-User-Token": register("copilot_veu")}
    client.post("/drills/", headers=hdr, json={
        "text_catalan": "el pa", "text_tachelhit": "aɣrum",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/pa.mp3", "author": "Halima"}).json()

    db, run = _eines()
    try:
        no = run("speak_tachelhit", {"text": "iɣḍdn"})
        assert "error" in no and "no és a la biblioteca" in no["error"], no

        # el que SÍ que hi és, sona amb la veu de qui el va dir, no amb la de màquina
        si = run("speak_tachelhit", {"text": "aɣrum"})
        assert si.get("veu") == "d'una persona" and si["speaker"] == "Halima", si
        assert "pa.mp3" in si["audio_url"]

        # i escrit d'una altra manera, és la mateixa paraula: es casa pel so
        igual = run("speak_tachelhit", {"text": "aghrum"})
        assert igual.get("audio_url") and "error" not in igual, igual
    finally:
        db.close()
