"""Lògica pura del cercle virtuós del transcriptor (tools/lm/cercle_virtuos.py): selecció, retall, regla interna, aturada i
comprovacions de sortides velles. Sense Kaggle ni GPU."""
import importlib.util
import json
import os

import pytest

ARREL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _carrega():
    esp = importlib.util.spec_from_file_location("cercle_virtuos_t", os.path.join(ARREL, "tools", "lm", "cercle_virtuos.py"))
    m = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(m)
    return m


cv = _carrega()


def _stat(lo, hi, delta=0.0):
    return {"n": 50, "abans": 0.2, "despres": 0.2 + delta, "delta": delta, "ic_lo": lo, "ic_hi": hi}


def _stats(**kw):
    base = {p: _stat(-0.004, 0.004) for p in cv.PROVES}
    base.update(kw)
    return base


def test_capitols_retinguts_uneix_test_i_dev_de_totes_les_particions():
    ps = [{"capitols": {"test": ["a"], "dev": ["b"], "train": ["c"]}}, {"capitols": {"test": ["d", "a"], "dev": [], "train": ["e"]}}, {}]
    assert cv.capitols_retinguts(ps) == {"a", "b", "d"}


def test_finestra_retall_marge_i_limits():
    assert cv.finestra_retall(10.0, 12.0) == (9.7, 12.3)
    assert cv.finestra_retall(0.1, 2.0, origen=0.0) == (0.0, 2.3)               # no surt de la línia de temps pel davant
    assert cv.finestra_retall(10.0, 12.0, origen=0.0, fi=12.1) == (9.7, 12.1)   # ni pel darrere
    assert cv.finestra_retall(10.0, 10.1) is None                               # 0,7 s < 0,8 s
    assert cv.finestra_retall(10.0, 24.0) is None                               # > 14 s


def test_selecciona_parelles_alta_i_esquelet_i_retinguts():
    conc = {
        "ok": {"alta": True, "hip": "azul imanay", "text": "azul imannay"},
        "esq": {"alta": True, "hip": "qqq ssdd", "text": "azul imannay"},
        "baixa": {"alta": False, "hip": "azul", "text": "azul"},
        "ret": {"alta": True, "hip": "azul", "text": "azul"},
        "sense_ali": {"alta": True, "hip": "azul", "text": "azul"},
    }
    ali = [{"id": "ok", "slug": "s1", "al_ini": 1.0, "al_fi": 3.0},
           {"id": "esq", "slug": "s1", "al_ini": 1.0, "al_fi": 3.0},
           {"id": "baixa", "slug": "s1", "al_ini": 1.0, "al_fi": 3.0},
           {"id": "ret", "slug": "test", "al_ini": 1.0, "al_fi": 3.0},
           {"id": "sense_ali", "slug": "s1", "error": "text massa curt"},
           {"id": "fantasma", "slug": "s1", "al_ini": 1.0, "al_fi": 3.0}]
    sel, motius = cv.selecciona_parelles(conc, ali, {"test"})
    assert [e["id"] for e in sel] == ["ok"]
    assert motius == {"seleccionat": 1, "esquelet": 1, "no alta": 1, "capítol retingut": 1, "alineació fallida": 1, "sense concordança": 1}


def test_esquelet_max_es_configurable():
    conc = {"x": {"alta": True, "hip": "azul imanay", "text": "azul imannay"}}
    ali = [{"id": "x", "slug": "s", "al_ini": 1.0, "al_fi": 3.0}]
    assert cv.selecciona_parelles(conc, ali, set(), esq_max=0.0)[0]
    conc["x"]["hip"] = "bbbbbb"
    assert not cv.selecciona_parelles(conc, ali, set(), esq_max=0.5)[0]


def test_monta_buffer_i_talla_clip_respecten_la_linia_de_temps():
    np = pytest.importorskip("numpy")
    sr = 100
    membres = [{"id": "m0", "a": 10.0, "b": 12.0}, {"id": "m1", "a": 12.0, "b": 15.0}, {"id": "m2", "a": 15.0, "b": 16.0}]
    sons = {"m0": np.full(200, 1.0), "m1": np.full(300, 2.0), "m2": np.full(100, 3.0)}
    origen, buf = cv.monta_buffer(membres, lambda k: sons[k], sr=sr)
    assert origen == 10.0
    assert buf[0] == 1.0 and buf[250] == 2.0 and buf[550] == 3.0
    clip = cv.talla_clip(buf, origen, 11.5, 13.0, sr=sr)       # a cavall de m0 i m1
    assert len(clip) == 150 and clip[0] == 1.0 and clip[-1] == 2.0 and clip[49] == 1.0 and clip[50] == 2.0
    assert len(cv.talla_clip(buf, origen, 9.0, 10.5, sr=sr)) == 50   # abans de l'origen: no s'agafen índexs negatius


def test_regla_interna_cap_empitjora_i_dos_milloren():
    r = cv.regla_interna(_stats(**{"snrt-retingut": _stat(-0.07, -0.02, -0.04), "test-fora": _stat(-0.017, -0.002, -0.009)}))
    assert r["adopta"] and r["milloren"] == ["test-fora", "snrt-retingut"] or set(r["milloren"]) == {"test-fora", "snrt-retingut"}
    # només un millora
    assert not cv.regla_interna(_stats(**{"snrt-retingut": _stat(-0.07, -0.02, -0.04)}))["adopta"]
    # dos milloren però un empitjora amb IC
    r = cv.regla_interna(_stats(**{"snrt-retingut": _stat(-0.07, -0.02), "test-fora": _stat(-0.017, -0.002), "tfa-226": _stat(0.002, 0.02, 0.01)}))
    assert not r["adopta"] and r["empitjoren"] == ["tfa-226"]
    # un empitjora SENSE IC net (el zero és a dins) no vota en contra
    r = cv.regla_interna(_stats(**{"snrt-retingut": _stat(-0.07, -0.02), "test-fora": _stat(-0.017, -0.002), "tfa-226": _stat(-0.002, 0.02, 0.01)}))
    assert r["adopta"]


def test_regla_interna_amb_prova_absent_no_adopta():
    st = _stats(**{"snrt-retingut": _stat(-0.07, -0.02), "test-fora": _stat(-0.017, -0.002)})
    del st["cv-zgh-test"]
    r = cv.regla_interna(st)
    assert not r["adopta"] and r["absents"] == ["cv-zgh-test"]


def test_rondes_sense_millora_i_aturada():
    rs = [{"adopta": False}, {"adopta": True}, {"adopta": False}, {"adopta": False}]
    assert cv.rondes_sense_millora(rs) == 2
    assert cv.motiu_aturada(rs, False, 40.0, {}) is None
    assert cv.motiu_aturada(rs + [{"adopta": False}], False, 40.0, {}) == "3 rondes seguides sense millora"
    assert cv.motiu_aturada(rs, True, 40.0, {}) == "fitxer ATURA"
    assert "disc" in cv.motiu_aturada(rs, False, 14.9, {})
    assert "repetit 2 cops" in cv.motiu_aturada(rs, False, 40.0, {"push-obs": 2})
    assert cv.motiu_aturada(rs, False, 40.0, {"push-obs": 1}) is None
    assert cv.rondes_sense_millora([]) == 0


def test_comprova_observacio_detecta_sortida_vella():
    bona = {"run_id": "abc", "adaptador": "adaptador_inici.pt", "talls": 1000, "alineats": 900}
    assert cv.comprova_observacio(bona, "abc", 1000) == []
    assert any("sortida vella" in x for x in cv.comprova_observacio(bona, "altre", 1000))
    assert cv.comprova_observacio({**bona, "talls": 300}, "abc", 1000)
    assert cv.comprova_observacio({**bona, "alineats": 100}, "abc", 1000)
    assert cv.comprova_observacio({}, "abc", 1000)


def test_comprova_entrenament_detecta_sortida_vella_i_train_que_no_quadra():
    res = {"config": {"run_id": "r1", "seed": 42, "adaptador_inici": "adaptador_inici.pt", "train_snrt": 950, "ritme": 5e-05, "epoques": 3, "recepta": "B"}}
    assert cv.comprova_entrenament(res, "r1", 42, 983, "nou", "vell") == []
    assert any("sortida vella" in x for x in cv.comprova_entrenament(res, "r2", 42, 983, "nou", "vell"))
    assert any("no quadra" in x for x in cv.comprova_entrenament(res, "r1", 42, 2000, "nou", "vell"))      # train de la sortida vella
    assert any("idèntic" in x for x in cv.comprova_entrenament(res, "r1", 42, 983, "x", "x"))
    assert cv.comprova_entrenament({}, "r1", 42, 983, "nou", "vell")
    res2 = {"config": {**res["config"], "adaptador_inici": "adaptador_shi_zouhir_b.pt"}}
    assert any("no de M_r" in x for x in cv.comprova_entrenament(res2, "r1", 42, 983, "nou", "vell"))


def test_prepara_nucli_escriu_run_id_llavor_i_recepta(tmp_path):
    c = cv.Cercle(str(tmp_path), arrel=str(tmp_path))
    d = c.prepara_nucli("train", "idunic123", seed=1042)
    codi = open(os.path.join(d, "snrt-cercle-train.py"), encoding="utf-8").read()
    for esperat in ('RECEPTA = "B"', "RITME = 5e-05", "EPOQUES = 3\n", "SEED = 1042\n", 'RUN_ID = "idunic123"'):
        assert esperat in codi
    meta = json.load(open(os.path.join(d, "kernel-metadata.json")))
    assert meta["id"] == "josepabloucr/snrt-cercle-train" and meta["is_private"] is True
    assert meta["dataset_sources"][0] == "josepabloucr/snrt-cercle"
    d2 = c.prepara_nucli("obs", "obs777")
    assert 'RUN_ID = "obs777"' in open(os.path.join(d2, "snrt-cercle-obs.py"), encoding="utf-8").read()
    assert json.load(open(os.path.join(d2, "kernel-metadata.json")))["dataset_sources"] == [
        "josepabloucr/snrt-cercle-dades", "josepabloucr/snrt-cercle-model"]


def test_espera_ignora_l_estat_vell_just_despres_del_push(tmp_path):
    c = cv.Cercle(str(tmp_path), arrel=str(tmp_path), dorm=lambda s: None)
    estats = iter(["complete", "complete", "queued", "running", "complete"])
    c.estat_nucli = lambda slug: next(estats)
    assert c.espera_nucli("x") == "complete"
    assert next(estats, None) is None           # ha consumit els cinc: els dos «complete» vells s'han ignorat


def test_model_actual_segueix_l_ultima_adoptada(tmp_path):
    c = cv.Cercle(str(tmp_path), arrel=str(tmp_path))
    assert c.model_actual() == (os.path.join(str(tmp_path), "models", "M0.pt"), 0)
    c.apunta({"ronda": 0, "model_idx": 0, "adopta": True, "stats": {}})
    c.apunta({"ronda": 1, "model_idx": 1, "adopta": False, "stats": {}})
    assert c.model_actual()[1] == 1
    assert os.path.exists(os.path.join(str(tmp_path), "ESTAT.md"))
