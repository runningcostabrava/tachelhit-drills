"""L'anàlisi d'una frase es paga una vegada (#458).

Cada clic a «analitza» cridava el Gemini i tornava a pagar la mateixa resposta; quan el Gemini es
quedava sense crèdit, el botó no feia res ni per a les frases ja analitzades.
"""
import main
from test_api import client, register


def _drill(nom):
    hdr = {"X-User-Token": register(nom)}
    return hdr, client.post("/drills/", headers=hdr, json={"text_catalan": "bon dia", "text_tachelhit": "azul fellawn"}).json()


def _gemini(monkeypatch):
    crides = []
    def fals(system, turns, **kw):
        crides.append(turns)
        return f"resposta {len(crides)}"
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "gemini_generate", fals)
    monkeypatch.setattr(main, "_build_system_instruction", lambda db: "")
    return crides


def test_la_segona_vegada_no_crida_el_model(monkeypatch):
    crides = _gemini(monkeypatch)
    _, d = _drill("analisi_una")
    primera = client.post(f"/ai/analyze-drill/{d['id']}").json()
    segona = client.post(f"/ai/analyze-drill/{d['id']}").json()
    assert primera["analysis"] == segona["analysis"] == "resposta 1"
    assert len(crides) == 1


def test_analisi_i_explicacio_no_es_barregen(monkeypatch):
    crides = _gemini(monkeypatch)
    _, d = _drill("analisi_dues")
    a = client.post(f"/ai/analyze-drill/{d['id']}").json()["analysis"]
    e = client.post(f"/ai/explain/{d['id']}").json()
    assert a != e["explanation"] and len(crides) == 2
    assert client.post(f"/ai/explain/{d['id']}").json()["explanation"] == e["explanation"]
    assert len(crides) == 2


def test_es_llegeix_sense_clau_ni_pressupost(monkeypatch):
    _gemini(monkeypatch)
    _, d = _drill("analisi_sense_clau")
    desada = client.post(f"/ai/analyze-drill/{d['id']}").json()["analysis"]
    monkeypatch.setattr(main, "gemini_available", lambda: False)
    def sense_cap(*a, **kw):
        raise AssertionError("una lectura no ha de passar pel pressupost")
    monkeypatch.setattr(main.ai_meter, "check_person", sense_cap)
    r = client.post(f"/ai/analyze-drill/{d['id']}")
    assert r.status_code == 200 and r.json()["analysis"] == desada


def test_si_el_text_canvia_es_torna_a_escriure(monkeypatch):
    crides = _gemini(monkeypatch)
    hdr, d = _drill("analisi_canvi")
    client.post(f"/ai/analyze-drill/{d['id']}")
    db = main.SessionLocal()
    try:
        fila = db.get(main.DrillModel, d["id"])
        fila.text_tachelhit = "azul fellak"
        db.commit()
    finally:
        db.close()
    assert client.post(f"/ai/analyze-drill/{d['id']}").json()["analysis"] == "resposta 2"
    assert len(crides) == 2


def test_una_fallada_no_es_desa(monkeypatch):
    _gemini(monkeypatch)
    def cau(*a, **kw):
        raise RuntimeError("402")
    monkeypatch.setattr(main, "gemini_generate", cau)
    _, d = _drill("analisi_fallada")
    assert client.post(f"/ai/analyze-drill/{d['id']}").status_code == 502
    db = main.SessionLocal()
    try:
        assert main._ai_desat(db, d["id"], "analyze") is None
    finally:
        db.close()
