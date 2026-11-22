"""La lectura d'una màquina queda escrita, amb qui l'ha dita (#575).

`/transcribe/` no desava res. Ni qui havia llegit, ni què havia dit, ni quan. Mesurat el
9-11-2026 sobre les 12.202 frases: **12** on el text del parlant era idèntic a una lectura
desada, i **0** amb l'empremta de cap lector. La pregunta del #557 —quantes frases de producció
han rebut text de màquina al camp del parlant— no tenia on mirar-se.

Aquestes proves guarden les fronteres, que són la part que importa: el camp del parlant no es
toca mai, un JSON que no s'entén no s'esborra, i una fallada del desat no s'endú la lectura de
qui acaba de gravar.
"""
import json

import main
from test_api import client


def _frase(**camps):
    r = client.post("/drills/", json=camps or {"text_catalan": "prova de rastre"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _llegeix(drill_id):
    from models import Drill as DrillModel
    with main.SessionLocal() as db:
        return db.query(DrillModel).filter(DrillModel.id == drill_id).first()


def _posa(drill_id, **camps):
    from models import Drill as DrillModel
    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
        for k, v in camps.items():
            setattr(d, k, v)
        db.commit()


def _nomes_el_nostre(monkeypatch, diu="ihla ġuri udġar"):
    """El segon lector de la fila contesta i els altres dos no hi són."""
    main._GEMINI_ASR_BUIDES = 0
    main._GEMINI_ASR_FINS = 0.0
    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: None)
    monkeypatch.setattr(main, "_space_mms_text", lambda url: diu)


def test_la_lectura_queda_escrita_amb_qui_l_ha_dita(monkeypatch):
    _nomes_el_nostre(monkeypatch)
    i = _frase()

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a", "drill_id": i})
    assert r.status_code == 200, r.text

    esb = json.loads(_llegeix(i).esborranys)
    assert len(esb) == 1, esb
    assert esb[0]["text"] == "ihla ġuri udġar"
    assert esb[0]["model"] == main.LECTOR_NOSTRE
    assert esb[0]["quan"].endswith("Z"), esb[0]          # i QUAN, que era l'altra pregunta
    # El camp ja desat torna amb la resposta, perquè qui crida pugui construir-hi a sobre
    # en comptes de trepitjar-lo amb la còpia que tenia d'abans.
    assert json.loads(r.json()["esborranys"]) == esb


def test_sense_drill_id_no_s_escriu_enlloc(monkeypatch):
    """La veu d'un vídeo que encara no és de ninguna frase: es llegeix i no es desa res."""
    _nomes_el_nostre(monkeypatch)
    i = _frase()

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a"})
    assert r.status_code == 200, r.text
    assert r.json()["esborranys"] is None
    assert _llegeix(i).esborranys is None


def test_no_toca_mai_el_text_del_parlant(monkeypatch):
    """ADR 0003. La prova que ha de caure si algú tornés a fer-ho fàcil."""
    _nomes_el_nostre(monkeypatch, diu="una cosa que la màquina sent")
    i = _frase()
    _posa(i, text_tachelhit="ⴰⵢⵢⵓⵣ", text_tachelhit_latin="ayyuz",
          text_catalan="gràcies", text_tachelhit_suggested="la proposta de sempre")

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/clip.m4a", "drill_id": i})
    assert r.status_code == 200, r.text

    d = _llegeix(i)
    assert d.text_tachelhit == "ⴰⵢⵢⵓⵣ"
    assert d.text_tachelhit_latin == "ayyuz"
    assert d.text_catalan == "gràcies"
    # La proposta també es deixa estar: qui tria quina de les lectures l'ocupa és el davant.
    assert d.text_tachelhit_suggested == "la proposta de sempre"
    assert json.loads(d.esborranys)[0]["text"] == "una cosa que la màquina sent"


def test_una_relectura_del_mateix_lector_no_fa_dos_testimonis(monkeypatch):
    """Un botó premut dues vegades no és acord entre models: és el mateix dient-ho dues vegades."""
    _nomes_el_nostre(monkeypatch, diu="primera")
    i = _frase()
    client.post("/transcribe/", json={"audio_url": "https://exemple/a.m4a", "drill_id": i})

    _nomes_el_nostre(monkeypatch, diu="segona, que és la bona")
    client.post("/transcribe/", json={"audio_url": "https://exemple/a.m4a", "drill_id": i})

    esb = json.loads(_llegeix(i).esborranys)
    assert len(esb) == 1, esb
    assert esb[0]["text"] == "segona, que és la bona"


def test_la_lectura_d_un_altre_model_s_hi_suma(monkeypatch):
    """Dos lectors independents que coincideixen és tot el valor del camp: no es trepitgen."""
    i = _frase()
    _posa(i, esborranys=json.dumps([{"text": "el que va dir l'altre",
                                     "model": "TutlaytAI/wav2vec2-berber", "acord": None}],
                                   ensure_ascii=False))

    _nomes_el_nostre(monkeypatch, diu="el que hi sent el nostre")
    client.post("/transcribe/", json={"audio_url": "https://exemple/a.m4a", "drill_id": i})

    esb = json.loads(_llegeix(i).esborranys)
    assert [e["model"] for e in esb] == ["TutlaytAI/wav2vec2-berber", main.LECTOR_NOSTRE]
    assert esb[0]["text"] == "el que va dir l'altre"


def test_un_json_que_no_s_enten_no_s_esborra(monkeypatch):
    """Perdre esborranys d'altri per fer-hi lloc és pitjor que no desar res."""
    _nomes_el_nostre(monkeypatch)
    i = _frase()
    _posa(i, esborranys="{això no és una llista, i tampoc és JSON")

    r = client.post("/transcribe/", json={"audio_url": "https://exemple/a.m4a", "drill_id": i})
    assert r.status_code == 200, r.text          # la lectura arriba igual
    assert r.json()["corrected_transcription"] == "ihla ġuri udġar"
    assert r.json()["esborranys"] is None        # i es diu que no s'ha desat
    assert _llegeix(i).esborranys == "{això no és una llista, i tampoc és JSON"


def test_si_el_desat_falla_no_llanca_mai():
    """Qui acaba de gravar ha de rebre la seva lectura encara que la base es queixi.

    El desat va DINS del `return` de l'endpoint: si llancés, la petició cauria amb un 500 i la
    lectura es perdria pel camí. Per això el reraguarda no llança mai i només torna `None`.
    """
    class SessioTrencada:
        def query(self, *a, **k):
            raise RuntimeError("la base no vol")

        def rollback(self):
            pass

    assert main._desa_lectura_de_maquina(SessioTrencada(), 1, "una lectura",
                                         main.LECTOR_NOSTRE) is None

    # I una sessió que ni tan sols sap fer `rollback`: tampoc.
    class PitjorEncara:
        def query(self, *a, **k):
            raise RuntimeError("ni query")

        def rollback(self):
            raise RuntimeError("ni rollback")

    assert main._desa_lectura_de_maquina(PitjorEncara(), 1, "una lectura",
                                         main.LECTOR_NOSTRE) is None


def test_el_que_ha_sentit_i_el_que_proposa_queden_tots_dos(monkeypatch):
    """El NeMo passa pel glossari i per l'aparellament amb el corpus: el que torna pot ser una
    frase NOSTRA que s'hi assembla. Qui decideix ha de poder veure-ho."""
    i = _frase()
    with main.SessionLocal() as db:
        assert main._desa_lectura_de_maquina(db, i, "una frase del corpus",
                                             main.LECTOR_NEMO, cru="una fras del corpos")
    e = json.loads(_llegeix(i).esborranys)[0]
    assert e["text"] == "una frase del corpus"
    assert e["cru"] == "una fras del corpos"

    # I quan són el mateix, no es repeteix.
    with main.SessionLocal() as db:
        assert main._desa_lectura_de_maquina(db, i, "igual", main.LECTOR_NEMO, cru="igual")
    assert "cru" not in json.loads(_llegeix(i).esborranys)[0]
