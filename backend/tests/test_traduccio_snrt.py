# -*- coding: utf-8 -*-
"""Etapes 04 (traducció àrab -> català) i 05 (portes) de la fàbrica de Tamazight TV (#601), sense xarxa: els models són mocks.

Es comprova: acord Qwen + DeepSeek («confirmat»), tercer auditor (Gemini) només quan discrepen («tercer»), que les rèpliques amb `arab_dubtos`
no es tradueixen ni són aptes per al traductor (sí per a l'ASR), i el límit de cost amb el comptador d'`_costos.json` (l'etapa s'atura sense
tocar les files i reprèn quan es puja el límit).
"""
import importlib.util
import json
import os
import sys

import pytest

pytest.importorskip("scipy.ndimage")
FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")
sys.path.insert(0, FABRICA)
import comu  # noqa: E402


def _carrega(nom):
    spec = importlib.util.spec_from_file_location("snrt_" + nom, os.path.join(FABRICA, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def etapa04(tmp_path, monkeypatch):
    m = _carrega("04_tradueix")
    monkeypatch.setenv("TD_TV", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    for v in ("TD_LIMIT_DEEPSEEK_USD", "TD_LIMIT_GEMINI_USD", "TD_LIMIT_QWEN_FITXES"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(comu, "carrega_env", lambda: None)
    crides = []
    TRAD = {("qwen3.8-max", "ar-ok"): "bé", ("deepseek-chat", "ar-ok"): "bé",
            ("qwen3.8-max", "ar-dub"): "A", ("deepseek-chat", "ar-dub"): "B",
            ("qwen3.8-max", "ar-pendent"): "pa", ("deepseek-chat", "ar-pendent"): "pb",
            ("qwen3.8-max", "ar-1"): "u", ("deepseek-chat", "ar-1"): "u", ("qwen3.8-max", "ar-2"): "d", ("deepseek-chat", "ar-2"): "d"}

    def xat(model, msgs, **k):
        text = msgs[-1]["content"].split("Àrab: ")[1].split("\n")[0]
        crides.append((model, text))
        return TRAD[(model, text)], {"total_tokens": 100}

    def gemini(model, msgs, intents=4):
        text = msgs[-1]["content"].split("Àrab: ")[1].split("\n")[0]
        crides.append((model, text))
        return "A", {"total_tokens": 50}      # el tercer dona la versió d'a

    monkeypatch.setattr(comu, "xat", xat)
    monkeypatch.setattr(m, "gemini", gemini)
    # chrF controlat: igual = 1; A i B = 0,4 (zona de dubte); la resta 0
    monkeypatch.setattr(comu, "chrf", lambda h, r, *a, **k: 1.0 if h == r else 0.4 if {h, r} == {"A", "B"} else 0.0)
    return m, crides


def _capitol(tmp_path, files):
    car = tmp_path / "cap"
    car.mkdir()
    comu.desa_subtitols(str(car), files)
    return str(car)


def _fila(i, arab, **k):
    return {"id": "c_%04d" % i, "k": i, "arab": arab, "durada": 2.0, "credits": False, **k}


def _executa(m, car, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["04_tradueix.py", car, "--fils", "1", *args])
    m.main()
    return comu.subtitols(car)


def test_acord_tercer_i_dubtoses(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    car = _capitol(tmp_path, [_fila(1, "ar-ok"), _fila(2, "ar-dub"), _fila(3, "ar-ok", arab_dubtos=True), _fila(4, "ar-ok", credits=True)])
    files = _executa(m, car, monkeypatch)
    per_id = {f["id"]: f for f in files}
    assert per_id["c_0001"]["catala_estat"] == "confirmat" and per_id["c_0001"]["catala"] == "bé"
    assert per_id["c_0002"]["catala_estat"] == "tercer" and per_id["c_0002"]["catala"] == "A"          # a i b discrepen, el tercer (Gemini) dona la raó a a
    assert "catala_estat" not in per_id["c_0003"] and not per_id["c_0003"].get("catala")                  # dubtosa: no es tradueix
    assert "catala_estat" not in per_id["c_0004"]                                                         # crèdits: no es tradueixen
    gemini = [c for c in crides if c[0].startswith("gemini")]
    assert gemini == [("gemini-2.5-flash", "ar-dub")]                                                     # el tercer auditor NOMÉS quan discrepen
    est = comu.estat_llegeix(car)["04_tradueix"]["comptes"]
    assert est["estats"]["confirmat"] == 1 and est["estats"]["tercer"] == 1
    assert est["fitxes_text"]["gemini-2.5-flash"] == 50


def test_les_dubtoses_no_fan_cap_crida(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    car = _capitol(tmp_path, [_fila(1, "ar-ok", arab_dubtos=True)])
    _executa(m, car, monkeypatch)
    assert crides == []


def test_limit_de_cost_atura_l_etapa_i_reprèn(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    # DeepSeek: 100 fitxes = 0,000028 $; amb un límit d'1e-5 $ la primera crida ja esgota el pressupost
    monkeypatch.setenv("TD_LIMIT_DEEPSEEK_USD", "0.00001")
    car = _capitol(tmp_path, [_fila(1, "ar-1"), _fila(2, "ar-2")])
    files = _executa(m, car, monkeypatch)
    comptes = comu.estat_llegeix(car)["04_tradueix"]["comptes"]
    assert comptes["saltades_pressupost"] >= 1 and comptes["pressupost_esgotat"] == ["deepseek-chat"]
    assert sum(1 for f in files if f.get("catala_estat")) == 1                 # només la primera; l'altra queda sense tocar
    antic = len(crides)
    costos = json.load(open(os.path.join(str(tmp_path), "_costos.json"), encoding="utf-8"))["fitxes"]
    assert costos["deepseek-chat"] == 100 and costos["qwen3.8-max"] == 100
    # ja esgotat: una segona execució no fa cap crida
    _executa(m, car, monkeypatch)
    assert len(crides) == antic
    # es puja el límit: reprèn el que faltava
    monkeypatch.setenv("TD_LIMIT_DEEPSEEK_USD", "3.6")
    files = _executa(m, car, monkeypatch)
    assert all(f.get("catala_estat") == "confirmat" for f in files)


def test_el_primer_auditor_rota_a_un_altre_qwen(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    # qwen3.8-max ja és a 800.000: la fila va al següent de la cascada (qwen4-max), amb el seu comptador
    json.dump({"fitxes": {"qwen3.8-max": 800_000}}, open(os.path.join(str(tmp_path), "_costos.json"), "w"))
    orig = comu.xat
    monkeypatch.setattr(comu, "xat", lambda model, msgs, **k: orig("qwen3.8-max" if model == "qwen4-max" else model, msgs, **k))
    car = _capitol(tmp_path, [_fila(1, "ar-ok")])
    files = _executa(m, car, monkeypatch)
    assert files[0]["model_a"] == "qwen4-max" and files[0]["catala_estat"] == "confirmat"
    costos = json.load(open(os.path.join(str(tmp_path), "_costos.json"), encoding="utf-8"))["fitxes"]
    assert costos["qwen3.8-max"] == 800_000 and costos["qwen4-max"] == 100      # el comptador de cada model és propi


def test_sense_cap_qwen_acord_deepseek_gemini_nomes_amb_confianca_alta(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    json.dump({"fitxes": {q: 800_000 for q in m.MODELS_A}}, open(os.path.join(str(tmp_path), "_costos.json"), "w"))
    monkeypatch.setattr(comu, "chrf", lambda h, r, *a, **k: 1.0 if h == r else 0.0)
    # DeepSeek i Gemini diuen el mateix per a ar-ok; per a ar-dub, coses diferents
    monkeypatch.setattr(m, "gemini", lambda model, msgs, intents=4: (crides.append((model, msgs[-1]["content"])) or ("bé" if "ar-ok" in msgs[-1]["content"] else "G", {"total_tokens": 50})))
    car = _capitol(tmp_path, [_fila(1, "ar-ok", arab_conf=0.95), _fila(2, "ar-ok", arab_conf=0.7), _fila(3, "ar-dub", arab_conf=0.9)])
    per_id = {f["id"]: f for f in _executa(m, car, monkeypatch)}
    assert per_id["c_0001"]["catala_estat"] == "confirmat" and per_id["c_0001"]["via"] == "deepseek+gemini" and per_id["c_0001"]["model_a"] is None
    assert "catala_estat" not in per_id["c_0002"]                                   # confiança < 0,8: no es tradueix sense Qwen
    assert per_id["c_0003"]["catala_estat"] == "descartat"                          # DeepSeek i Gemini no coincideixen
    assert not any(c[0].startswith("qwen") for c in crides)                         # cap crida a Qwen
    comptes = comu.estat_llegeix(car)["04_tradueix"]["comptes"]
    assert comptes["saltades_sense_qwen_confianca_baixa"] == 1 and comptes["qwen_actual"] is None


def test_pressupost_cost_i_limits(tmp_path, monkeypatch):
    m = _carrega("04_tradueix")
    p = m.Pressupost(str(tmp_path / "c.json"))
    p.suma("deepseek-chat", 1_000_000)
    p.suma("gemini-2.5-flash", 720_000)
    p.suma("qwen3.8-max", 849_999)
    assert round(p.cost("deepseek-chat"), 2) == 0.28 and round(p.cost("gemini-2.5-flash"), 2) == 1.8
    assert p.esgotat(["deepseek-chat", "qwen3.8-max"]) == []
    assert p.esgotat(["gemini-2.5-flash"]) == ["gemini-2.5-flash"]            # 720.000 fitxes a 2,5 $/M = 1,8 $ = el límit
    p.suma("qwen3.8-max", 1)
    assert p.esgotat(["qwen3.8-max"]) == ["qwen3.8-max"]
    assert m.Pressupost(str(tmp_path / "c.json")).fitxes["deepseek-chat"] == 1_000_000      # persistit


def test_05_dubtoses_no_aptes_pel_traductor_si_per_l_asr():
    m = _carrega("05_informe")
    base = {"credits": False, "tifinag_conf": 0.9, "tifinag_dubtosos": 0, "arab_acord": 1.0, "arab_lectures": 2, "arab": "x",
            "catala_estat": "confirmat", "tifinag": "ⴰ ⴱ", "durada": 2.0}
    bona, dubtosa = dict(base), dict(base, arab_dubtos=True)
    assert m.apta_traductor(bona) and not m.apta_traductor(dubtosa)
    assert m.apta_traductor(dubtosa, dubtos_ok=True)
    n, aptes = m.numeros([bona, dubtosa], {"02_llegeix": {"comptes": {}}})
    assert n["aptes_traductor"] == 1 and n["arab_dubtoses"] == 1
    assert n["aptes_asr_durada"] == 2                                          # per a l'ASR la dubtosa sí que val
    assert n["aptes_so_tifinag"] == 2


def test_reconcilia_amb_els_capitols_si_el_comptador_va_per_sota(tmp_path):
    """El 18-11-2026 una 04 sense comptador (el capítol en curs d'un desplegament) va gastar 55 k que `_costos.json` no sabia."""
    m = _carrega("04_tradueix")
    json.dump({"fitxes": {"qwen3.8-max": 800_000}}, open(tmp_path / "_costos.json", "w"))
    for i, n in enumerate((600_000, 255_430)):
        (tmp_path / ("cap%d" % i)).mkdir()
        json.dump({"04_tradueix": {"comptes": {"fitxes_text": {"qwen3.8-max": n}}}}, open(tmp_path / ("cap%d" % i) / "estat.json", "w"))
    p = m.Pressupost(str(tmp_path / "_costos.json"))
    assert p.fitxes["qwen3.8-max"] == 855_430                          # el màxim dels dos: la suma dels capítols
    assert p.esgotat(["qwen3.8-max"]) == ["qwen3.8-max"]


def test_el_limit_es_comprova_abans_de_cada_crida(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    m.PRESSUPOST = m.Pressupost(str(tmp_path / "_costos.json"))
    m.PRESSUPOST.fitxes["qwen3.8-max"] = 850_000
    with pytest.raises(m.PressupostEsgotat):
        m.tradueix("qwen3.8-max", "ar-ok")
    assert crides == []                                                 # ni una crida al model esgotat
    m.PRESSUPOST.fitxes["qwen3.8-max"] = 849_900
    assert m.tradueix("qwen3.8-max", "ar-ok")[0] == "bé"                # per sota: crida
    assert m.PRESSUPOST.fitxes["qwen3.8-max"] == 850_000                # i el comptador s'actualitza a cada crida


def test_fila_a_mig_quan_un_model_arriba_al_limit_queda_intacta(etapa04, tmp_path, monkeypatch):
    m, crides = etapa04
    json.dump({"fitxes": {"deepseek-chat": 20_000_000}}, open(tmp_path / "_costos.json", "w"))    # DeepSeek ja és al límit
    real = m.Pressupost.esgotat
    estat = {"n": 0}

    def esgotat(self, models):          # la primera consulta (la de la fila, `aturat()`) passa; la de DeepSeek dins la crida ja no (cursa entre fils)
        estat["n"] += 1
        return [] if estat["n"] == 1 else real(self, models)
    monkeypatch.setattr(m.Pressupost, "esgotat", esgotat)
    car = _capitol(tmp_path, [_fila(1, "ar-ok")])
    f = _executa(m, car, monkeypatch)[0]
    assert "catala_estat" not in f and "arab_traduit" not in f and not f.get("catala")      # ni «descartat» ni mig traduïda: es refarà
    assert comu.estat_llegeix(car)["04_tradueix"]["comptes"]["saltades_pressupost"] >= 1
