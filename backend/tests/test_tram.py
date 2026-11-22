"""El tros de la frase catalana que respon a cada paraula amaziga (#356).

La glossa diu què vol dir la paraula i ho diu amb la forma de diccionari; la frase la diu d'una
altra manera. Per això la pantalla que segueix la veu només encenia el 41% de les paraules
glossades. Aquí es comprova l'altre camp: el tros exacte, i que no s'hi accepti res que la frase
no digui.
"""
import json

import pytest
from test_api import client
import main
import tram


FRASE = "Hi havia una vegada un xai que pasturava."
GLOSSES = [{"shi": "illa", "ca": "hi havia"},
           {"shi": "yan", "ca": "un"},
           {"shi": "ikru", "ca": "xai"},
           {"shi": "ad", "ca": "partícula de futur"}]


def test_the_span_must_be_in_the_sentence_letter_for_letter():
    assert tram.dins(FRASE, "xai") == "xai"
    assert tram.dins(FRASE, "Hi havia") == "Hi havia"
    assert tram.dins(FRASE, "hi havia") == "Hi havia"   # es desa el tall de la FRASE, no el que escriu el model
    assert tram.dins(FRASE, "confiança") is None        # no hi és: fora
    assert tram.dins(FRASE, "") is None
    assert tram.dins(FRASE, "pastura") == "pastura"     # un tros de paraula també és un tros de la frase


def test_a_word_the_catalan_does_not_say_gets_no_span():
    """«ad» és una partícula que el català no diu. Deixar-ho en blanc és la resposta bona."""
    frases = [{"id": 1, "shi": "illa yan ikru ad", "ca": FRASE, "glosses": GLOSSES}]
    fora = tram.neteja({"1": [["illa", "Hi havia"], ["yan", "un"], ["ikru", "xai"], ["ad", ""]]}, frases)
    tr = {g["shi"]: g.get("ca_tram") for g in fora[1]}
    assert tr == {"illa": "Hi havia", "yan": "un", "ikru": "xai", "ad": None}
    assert [g["ca"] for g in fora[1]] == [g["ca"] for g in GLOSSES]   # «ca» no es toca mai


def test_a_span_that_is_not_in_the_sentence_is_dropped():
    """Un tros que la frase no diu parla d'una altra frase: la mateixa regla que les anàlisis."""
    frases = [{"id": 1, "shi": "illa yan ikru ad", "ca": FRASE, "glosses": GLOSSES}]
    fora = tram.neteja({"1": [["illa", "confiança"], ["ikru", "xai"]]}, frases)
    tr = {g["shi"]: g.get("ca_tram") for g in fora[1]}
    assert tr["illa"] is None and tr["ikru"] == "xai"


def test_the_key_and_the_word_are_both_hints():
    """El model torna «id 1» i escriu la paraula com li sembla: es casa pel mot i, si no, per l'ordre."""
    frases = [{"id": 7801, "shi": "illa yan ikru ad", "ca": FRASE, "glosses": GLOSSES}]
    fora = tram.neteja({"id 1": [["Illa,", "Hi havia"], ["IKRU", "xai"]]}, frases)
    tr = {g["shi"]: g.get("ca_tram") for g in fora[7801]}
    assert tr["illa"] == "Hi havia" and tr["ikru"] == "xai"


def test_only_lines_with_a_gloss_and_a_meaning_are_asked_for():
    """Una línia sense paraula per paraula no es pot marcar, i una que ja ho té no es torna a pagar."""
    amb = client.post("/drills/", json={
        "text_catalan": FRASE, "text_tachelhit": "illa yan ikru",
        "glosses": json.dumps(GLOSSES, ensure_ascii=False)}).json()
    sense = client.post("/drills/", json={"text_catalan": FRASE, "text_tachelhit": "illa yan ikru"}).json()
    feta = client.post("/drills/", json={
        "text_catalan": FRASE, "text_tachelhit": "ikru",
        "glosses": json.dumps([{"shi": "ikru", "ca": "xai", "ca_tram": "xai"}], ensure_ascii=False)}).json()
    with main.SessionLocal() as db:
        quines = {f["id"] for f in tram.frases_de(db, [amb["id"], sense["id"], feta["id"]])}
        assert quines == {amb["id"]}
        totes = {f["id"] for f in tram.frases_de(db, [amb["id"], sense["id"], feta["id"]], refer=True)}
        assert totes == {amb["id"], feta["id"]}


def test_the_spans_are_stored_without_touching_anything_else(monkeypatch):
    d = client.post("/drills/", json={
        "text_catalan": FRASE, "text_tachelhit": "illa yan ikru ad",
        "glosses": json.dumps(GLOSSES, ensure_ascii=False)}).json()
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *a, **k: json.dumps(
        {str(d["id"]): [["illa", "Hi havia"], ["yan", "un"], ["ikru", "xai"], ["ad", ""]]}))
    with main.SessionLocal() as db:
        frases = tram.frases_de(db, [d["id"]])
        assert tram.desa(db, tram.escriu(frases)) == 1
    tornada = json.loads(client.get(f"/drills/{d['id']}").json()["glosses"])
    assert [g["shi"] for g in tornada] == [g["shi"] for g in GLOSSES]
    assert [g["ca"] for g in tornada] == [g["ca"] for g in GLOSSES]
    assert tram.compte(tornada) == (4, 3)
    assert client.get(f"/drills/{d['id']}").json()["text_catalan"] == FRASE


def test_the_route_is_admin_only():
    assert client.post("/stories/no-such-story/trams").status_code in (401, 403)
