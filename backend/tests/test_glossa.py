"""El paraula per paraula (#361): les regles que abans vivien en un guió del bloc de notes.

La que es comprova amb més insistència és la primera: **la paraula que es desa és la de la
frase**. És la clau que fan servir el so d'una paraula (#271), el tros de la frase catalana
(#356) i la cerca; si aquí s'escriu d'una altra manera, allò no la troba.
"""
import json

from test_api import client
import main
import glossa


FRASE = "ur ssinɣ ad dduɣ"
CA = "no sé si hi aniré"


def test_the_word_stored_is_the_one_the_sentence_writes():
    """El model escriu «Ur,» i la frase diu «ur»: es desa el de la frase."""
    frases = [{"id": 1, "shi": FRASE, "ca": CA}]
    fora = glossa.neteja({"1": [["Ur,", "no"], ["SSINƔ", "sé"], ["ad", "partícula de futur"],
                                ["dduɣ", "aniré"]]}, frases)
    assert [g["shi"] for g in fora[1]] == ["ur", "ssinɣ", "ad", "dduɣ"]
    assert [g["ca"] for g in fora[1]] == ["no", "sé", "partícula de futur", "aniré"]


def test_a_word_the_sentence_does_not_say_is_dropped():
    """Glossar una paraula que la frase no diu seria posar un significat a una paraula que el
    parlant no ha dit mai. Amb un parell de més, el nombre ja no coincideix i el lloc no val."""
    frases = [{"id": 1, "shi": FRASE, "ca": CA}]
    fora = glossa.neteja({"1": [["ur", "no"], ["tigmmi", "casa"], ["dduɣ", "aniré"]]}, frases)
    assert [g["shi"] for g in fora[1]] == ["ur", "dduɣ"]


def test_the_word_as_its_own_meaning_is_not_a_meaning():
    frases = [{"id": 1, "shi": FRASE, "ca": CA}]
    fora = glossa.neteja({"1": [["ur", "ur"], ["ssinɣ", ""], ["ad", "partícula de futur"],
                                ["dduɣ", "aniré"]]}, frases)
    tr = {g["shi"]: g["ca"] for g in fora[1]}
    assert tr["ur"] == glossa.NO_HO_SABEM and tr["ssinɣ"] == glossa.NO_HO_SABEM
    assert tr["dduɣ"] == "aniré"


def test_the_tifinagh_comes_from_the_house_not_from_the_model():
    """És el mateix codi que pinta les frases a la pantalla: les dues cares no se separen mai."""
    import transliteration
    frases = [{"id": 1, "shi": FRASE, "ca": CA}]
    fora = glossa.neteja({"1": [["ur", "no"], ["ssinɣ", "sé"], ["ad", "partícula"], ["dduɣ", "aniré"]]}, frases)
    assert fora[1][0]["tif"] == transliteration.to_forms("ur")["tifinagh"]
    assert all(g["tif"] for g in fora[1])


def test_the_key_the_model_returns_is_only_a_hint():
    frases = [{"id": 7801, "shi": FRASE, "ca": CA}]
    fora = glossa.neteja({"id 1": [["ur", "no"], ["ssinɣ", "sé"], ["ad", "p"], ["dduɣ", "aniré"]]}, frases)
    assert set(fora) == {7801}


def test_only_lines_that_can_be_glossed_are_asked_for():
    """Escrita, amb significat, d'una llargada de frase, i que no en tingui ja."""
    bona = client.post("/drills/", json={"text_catalan": CA, "text_tachelhit": FRASE}).json()
    sense_ca = client.post("/drills/", json={"text_tachelhit": FRASE, "text_catalan": ""}).json()
    sense_shi = client.post("/drills/", json={"text_catalan": CA, "text_tachelhit": ""}).json()
    massa = client.post("/drills/", json={"text_catalan": CA,
                                          "text_tachelhit": " ".join(["ur"] * (glossa.MAX_PARAULES + 1))}).json()
    feta = client.post("/drills/", json={
        "text_catalan": CA, "text_tachelhit": FRASE,
        "glosses": json.dumps([{"shi": "ur", "ca": "no"}], ensure_ascii=False)}).json()
    ids = [bona["id"], sense_ca["id"], sense_shi["id"], massa["id"], feta["id"]]
    with main.SessionLocal() as db:
        assert {f["id"] for f in glossa.frases_de(db, ids)} == {bona["id"]}
        assert {f["id"] for f in glossa.frases_de(db, ids, refer=True)} == {bona["id"], feta["id"]}


def test_the_glosses_are_stored_without_touching_the_speaker_text(monkeypatch):
    d = client.post("/drills/", json={"text_catalan": CA, "text_tachelhit": FRASE}).json()
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *a, **k: json.dumps(
        {str(d["id"]): [["ur", "no"], ["ssinɣ", "sé"], ["ad", "partícula de futur"], ["dduɣ", "aniré"]]}))
    with main.SessionLocal() as db:
        assert glossa.desa(db, glossa.escriu(glossa.frases_de(db, [d["id"]]))) == 1
    tornat = client.get(f"/drills/{d['id']}").json()
    assert tornat["text_tachelhit"] == FRASE and tornat["text_catalan"] == CA
    assert [g["shi"] for g in json.loads(tornat["glosses"])] == ["ur", "ssinɣ", "ad", "dduɣ"]


def test_the_route_is_admin_only():
    assert client.post("/stories/no-such-story/glosses").status_code in (401, 403)
