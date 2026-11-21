# -*- coding: utf-8 -*-
"""tools/lm/transcriptor_bucle.py (#601, §6.5): portes d'aptitud, partició per capítol, tall de repetits, tall de wavs vells,
regla de decisió i parada. Sense xarxa, sense Kaggle i sense ECS: tot amb carpetes temporals i sortides fabricades."""
import json
import os
import struct
import sys
import time
import wave

import pytest

LM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "lm")
sys.path.insert(0, LM)
import transcriptor_bucle as tb  # noqa: E402
import cercle_virtuos as cv  # noqa: E402


def fila(i, tif="ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ", **k):
    return {"id": f"c_{i:04d}", "slug": "c", "tifinag": tif, "tifinag_conf": 0.95, "tifinag_dubtosos": 0, "durada": 3,
            "credits": False, "tall": f"talls/c_{i:04d}.wav", **k}


def escriu_wav(cami, segons, sr=16000):
    os.makedirs(os.path.dirname(cami), exist_ok=True)
    with wave.open(cami, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack("<h", 0) * int(segons * sr))


# ------------------------------------------------------------------ portes de §5
def test_apta_passa_una_fila_neta():
    assert tb.apta(fila(1)) == (True, "")


@pytest.mark.parametrize("canvi,motiu", [
    ({"credits": True}, "crèdit"),
    ({"tifinag": ""}, "sense tifinag"),
    ({"tifinag_conf": 0.84}, "confiança"),
    ({"tifinag_dubtosos": 3}, "dubtosos"),
    ({"durada": 0.7}, "curta"),
    ({"tifinag": "ⴰⵣⵓⵍ"}, "paraules"),
    ({"tifinag": " ".join(["ⴰⵣⵓⵍ"] * 31)}, "paraules"),
])
def test_apta_rebutja_i_diu_per_que(canvi, motiu):
    assert tb.apta(fila(1, **canvi)) == (False, motiu)


def test_apta_limits_exactes_passen():
    assert tb.apta(fila(1, tifinag_conf=0.85, tifinag_dubtosos=2, durada=0.8))[0]


def test_apta_sense_so_no_es_apta():
    assert tb.apta(fila(1), wav_ok=False) == (False, "sense so")


def test_rica_no_plega_les_lletres():
    # ⵖ ⵄ ⵃ ⴹ ⵚ no es plegueu a g a h d s: regla tachelhit-asr-plegat-esborrava-lletres
    assert tb.rica("ⵖⵄⵃⴹⵚ ⵜⵡ") == "ġεḥḍṣ tw"
    assert tb.rica("ⴰ, ⴱ.") == "a b"


# ------------------------------------------------------------------ partició per capítol
def test_particio_per_capitol_sense_solapament_i_determinista():
    slugs = [f"cap{i:02d}" for i in range(20)]
    p = tb.particio(slugs)
    assert len(p["test"]) == 2 and len(p["dev"]) == 1 and len(p["train"]) == 17
    tots = p["test"] + p["dev"] + p["train"]
    assert sorted(tots) == sorted(slugs)
    assert p == tb.particio(list(reversed(slugs)))          # no depèn de l'ordre d'entrada
    assert p != tb.particio(slugs, llavor=7)                # i sí de la llavor


def test_particio_amb_pocs_capitols_deixa_un_a_test_i_un_a_dev():
    p = tb.particio(["a", "b", "c", "d", "e", "f"])
    assert len(p["test"]) == 1 and len(p["dev"]) == 1 and len(p["train"]) == 4
    with pytest.raises(ValueError):
        tb.particio(["a", "b"])


# ------------------------------------------------------------------ repetits entre parts
def test_treu_repetits_del_train_i_dev_contra_el_test():
    f = lambda t: {"tifinag": t}
    parts = {"train": [f("ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ"), f("ⵉⵙⵎ ⵉⵏⵓ")], "dev": [f("ⴰⵣⵓⵍ  ⴼⵍⵍⴰⵡⵏ,"), f("ⵜⴰⵎⵖⴰⵔⵜ ⵜⴰⵎⵣⵡⴰⵔⵓ")], "test": [f("ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ")]}
    nou, treta = tb.treu_repetits(parts)
    assert [r["tifinag"] for r in nou["train"]] == ["ⵉⵙⵎ ⵉⵏⵓ"]
    assert len(nou["dev"]) == 1
    assert treta == {"dev": 1, "train": 1}
    assert nou["test"] == parts["test"]


def test_treu_repetits_del_train_contra_el_dev_tambe():
    f = lambda t: {"tifinag": t}
    nou, _ = tb.treu_repetits({"train": [f("ⵉⵙⵎ ⵉⵏⵓ")], "dev": [f("ⵉⵙⵎ ⵉⵏⵓ")], "test": [f("ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ")]})
    assert nou["train"] == [] and len(nou["dev"]) == 1


# ------------------------------------------------------------------ wavs vells (la 03 no refà el que ja hi és)
def test_wav_quadra_i_rebutja_durada_o_mtime_que_no_casen(tmp_path):
    c = str(tmp_path)
    r = fila(1)
    escriu_wav(os.path.join(c, r["tall"]), 3.5)
    assert tb.wav_quadra(r, c)
    escriu_wav(os.path.join(c, r["tall"]), 6.5)              # un altre tall: durada diferent
    assert not tb.wav_quadra(r, c)
    assert not tb.wav_quadra(fila(2), c)                       # no existeix


def test_wav_mes_vell_que_la_02_no_serveix_encara_que_duri_el_mateix(tmp_path):
    c = str(tmp_path)
    r = fila(1)
    cami = os.path.join(c, r["tall"])
    escriu_wav(cami, 3.5)
    ara = time.time()
    os.utime(cami, (ara - 7200, ara - 7200))
    assert not tb.wav_quadra(r, c, t02=ara - 3600)             # 02 va acabar fa 1 h: el wav és d'abans
    assert tb.wav_quadra(r, c, t02=ara - 10000)
    assert tb.wav_quadra(r, c, t02=None)


def test_fi_02_llegeix_l_estat_i_tolera_que_falti():
    assert tb.fi_02({"02_llegeix": {"fi": "2026-11-18 02:53:25"}}) is not None
    assert tb.fi_02({}) is None
    assert tb.fi_02({"02_llegeix": {"fi": None}}) is None


def _unic(slug, i):
    """Text de tifinag únic per (capítol, fila): la rica() esborra els dígits, així que s'escriu amb lletres."""
    lletres = "ⴰⴱⴳⴷⴹⴼⴽⵀⵃⵄⵅⵇⵉⵊⵍⵎⵏⵓⵔⵖ"
    n = sum(ord(c) * 31 ** k for k, c in enumerate(slug)) * 1000 + i
    out = ""
    while True:
        out += lletres[n % len(lletres)]
        n //= len(lletres)
        if not n:
            return out + "ⵜⵜ"


def _capitol(arrel, slug, n, vells=0):
    c = os.path.join(arrel, slug)
    files = [dict(fila(i), id=f"{slug}_{i:04d}", slug=slug, tall=f"talls/{slug}_{i:04d}.wav", tifinag=f"ⴰⵣⵓⵍ {_unic(slug, i)}") for i in range(n)]
    for i, r in enumerate(files):
        escriu_wav(os.path.join(c, r["tall"]), 3.5 if i >= vells else 5.0)    # els «vells» no quadren
    with open(os.path.join(c, "subtitols.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in files))
    json.dump({"talls": {r["id"]: {"v": "ok"} for r in files}}, open(os.path.join(c, "talls", "alineacio.json"), "w"))   # porta d'alineació
    json.dump({"slug": slug, "titol": slug, "02_llegeix": {"fi": "2020-01-01 00:00:00", "error": None},
               "03_talla": {"fi": "2020-01-01 00:01:00", "error": None}}, open(os.path.join(c, "estat.json"), "w"))


def test_construeix_particiona_per_capitol_i_deixa_els_vells_fora(tmp_path):
    arrel, sortida = str(tmp_path / "tv"), str(tmp_path / "out")
    for k in range(8):
        _capitol(arrel, f"cap{k}", 130, vells=30 if k == 0 else 0)
    r = tb.construeix(arrel, sortida, copia_audio=False)
    assert sum(len(v) for v in r["capitols"].values()) == 8
    assert len(r["capitols"]["test"]) == 1 and len(r["capitols"]["dev"]) == 1
    assert r["files"]["test"] > 0 and r["files"]["dev"] > 0 and r["files"]["train"] > 0
    # cap id en dues parts
    ids = r["ids"]
    assert not set(ids["train"]) & set(ids["test"]) and not set(ids["dev"]) & set(ids["test"]) and not set(ids["train"]) & set(ids["dev"])
    # un capítol sencer a cada part: tots els ids d'un capítol són a la mateixa part
    for part, slugs in r["capitols"].items():
        assert all(i.split("_")[0] in slugs for i in ids[part])
    assert r["diagnostic"]["cap0"]["descartades"]["sense so"] == 30
    assert os.path.exists(os.path.join(sortida, "ds", "rows.json")) and os.path.exists(os.path.join(sortida, "particio.json"))
    # congelada: el mateix resultat dues vegades
    assert tb.construeix(arrel, sortida, copia_audio=False)["hash_ids"] == r["hash_ids"]


def test_capitol_amb_massa_poques_aptes_queda_fora(tmp_path):
    arrel = str(tmp_path / "tv")
    _capitol(arrel, "curt", 30)
    _capitol(arrel, "llarg", 150)
    aptes, diag = tb.selecciona(tb.llegeix_capitols(arrel))
    assert list(aptes) == ["llarg"] and "fora" in diag["curt"]


def test_capitol_sense_03_feta_no_es_llegeix(tmp_path):
    arrel = str(tmp_path / "tv")
    _capitol(arrel, "mig", 5)
    est = os.path.join(arrel, "mig", "estat.json")
    d = json.load(open(est))
    del d["03_talla"]
    json.dump(d, open(est, "w"))
    assert tb.llegeix_capitols(arrel) == {}


# ------------------------------------------------------------------ regla de decisió
def _sortides(prova, parells, video="v"):
    out = []
    for i, (o, a, b) in enumerate(parells):
        out.append({"prova": prova, "video": video, "de": float(i), "or": o, "dit": a, "model": "abans"})
        out.append({"prova": prova, "video": video, "de": float(i), "or": o, "dit": b, "model": "després"})
    return out


def _tres_proves(cv, fora, ret):
    return _sortides("cv-zgh-test", cv) + _sortides("test-fora", fora) + _sortides("snrt-retingut", ret)


def _gran(n, abans, despres, ref="abcdefghij"):
    return [(ref, abans, despres)] * n


def _per_capitols(capitols):
    """[(nom, quants, abans, despres)] -> parelles amb el capítol, com les dona el bucle."""
    fora = []
    for nom, quants, abans, despres in capitols:
        fora += [("abcdefghij", abans, despres, nom)] * quants
    return fora


def test_bootstrap_remostreja_capitols_quan_els_talls_hi_estan_agrupats():
    """Tota la millora és d'UN capítol de quatre: per talls sembla certa, per capítols no.

    És el cas de `snrt-retingut`: 1.127 frases que surten de quatre capítols."""
    p = (_per_capitols([("a", 9, "abcdefghix", "abcdefghij")])
         + _per_capitols([("a", 1, "abcdefghij", "abcdefghij")]))
    for cap in "bcd":
        p += _per_capitols([(cap, 10, "abcdefghij", "abcdefghij")])
    s = tb.bootstrap(p, n=600)
    assert s["unitat"] == "capitol" and s["unitats"] == 4
    assert s["ic_hi"] >= 0, "amb la millora en un sol capítol de quatre, l'interval ha de tocar zero"
    #: les mateixes dades sense el capítol (com es feia) donen un interval que NO toca zero:
    #: això és exactament l'estretor falsa
    assert tb.bootstrap([x[:3] for x in p], n=600)["ic_hi"] < 0


def test_una_prova_d_un_sol_capitol_es_remostreja_per_talls():
    """El `cv-zgh-test` són 256 clips independents amb un sol valor de capítol."""
    p = (_per_capitols([("cv", 20, "abcdefghix", "abcdefghij")])
         + _per_capitols([("cv", 20, "abcdefghij", "abcdefghij")]))
    s = tb.bootstrap(p, n=400)
    assert s["unitat"] == "tall" and s["unitats"] == 40
    assert s["ic_lo"] < s["ic_hi"], "un sol capítol no pot donar un interval d'amplada zero"
    assert s["ic_hi"] < 0


def test_el_punt_estimat_no_depen_de_la_unitat():
    p = _per_capitols([("a", 10, "abcdefghix", "abcdefghij"),
                       ("b", 10, "abcdefghij", "abcdefghix"),
                       ("c", 10, "abcdefghij", "abcdefghij")])
    assert tb.bootstrap(p, n=200)["delta"] == tb.bootstrap([x[:3] for x in p], n=200)["delta"]


def test_el_wer_veu_l_enganxada_que_el_cer_dilueix():
    """El cas real `asywmmpqztvnotxd:52`: l'ull diu quatre paraules, l'orella n'enganxa dues.

    Tres de les quatre estan ben sentides; el que les amaga és que no hi ha espais. El CER es
    mou un 29 % i el WER un 50 %, i per això la regla, que decideix amb CER, gairebé no ho veu.
    """
    ull = "nkkin massa fatni hsna"
    enganxat = [(ull, "nkkinmassattn ihsna", "nkkinmassattn ihsna", "cap")] * 12
    espaiat = [(ull, "nkkinmassattn ihsna", "nkkin massa ttn ihsna", "cap")] * 12
    a, b = tb.bootstrap(enganxat, n=100), tb.bootstrap(espaiat, n=100)
    assert a["despres"] > b["despres"], "posar els espais ha de baixar el CER"
    assert a["wer_despres"] > b["wer_despres"], "i el WER molt més"
    #: el WER es mou més del doble que el CER
    cer = (a["despres"] - b["despres"]) / a["despres"]
    wer = (a["wer_despres"] - b["wer_despres"]) / a["wer_despres"]
    #: el WER es mou 1,5 vegades el que es mou el CER (al cas real, 50 % contra 29 %)
    assert wer >= 1.4 * cer


def test_la_regla_diu_quan_el_wer_no_diu_el_mateix():
    """Una ronda pot baixar el CER i empitjorar el que es llegeix: la regla ho ha de dir."""
    bo = {"ic_lo": -0.02, "ic_hi": -0.01, "wer_ic_lo": -0.03, "wer_ic_hi": -0.01, "unitats": 9}
    traidor = {"ic_lo": -0.02, "ic_hi": -0.01, "wer_ic_lo": 0.01, "wer_ic_hi": 0.04, "unitats": 9}
    proves = ("a", "b", "c")
    net = cv.regla_interna({"a": bo, "b": bo, "c": bo}, proves=proves)
    assert net["adopta"] and not net["discrepen"]

    r = cv.regla_interna({"a": bo, "b": bo, "c": traidor}, proves=proves)
    #: la condició NO canvia: segueix adoptant amb el CER
    assert r["adopta"], "el WER informa, no decideix"
    assert r["discrepen"] == ["c: CER millora, WER empitjora"]
    assert "WER no diu el mateix" in r["motiu"]


def test_la_regla_calla_quan_no_hi_ha_wer():
    """Estadístiques velles, sense els camps de WER: ni peta ni inventa discrepàncies."""
    vell = {"ic_lo": -0.02, "ic_hi": -0.01}
    r = cv.regla_interna({"a": vell, "b": vell}, proves=("a", "b"))
    assert r["adopta"] and r["discrepen"] == []


def test_bootstrap_delta_i_ic():
    s = tb.bootstrap(_gran(60, "abcdefghix", "abcdefghij"), n=300)
    assert s["n"] == 60 and s["delta"] < 0 and s["ic_hi"] < 0 and s["milloren"] == 60 and s["empitjoren"] == 0
    assert tb.bootstrap(_gran(60, "abcdefghij", "abcdefghij"), n=300)["delta"] == 0


def test_bootstrap_es_reprodible():
    p = _gran(30, "abcdefghix", "abcdefghij") + _gran(30, "abcdefghij", "abcdefghix")
    assert tb.bootstrap(p, n=200) == tb.bootstrap(p, n=200)


def test_decisio_adopta_quan_cv_millora_amb_ic_i_la_resta_aguanta(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps(_tres_proves(_gran(80, "abcdefghix", "abcdefghij"), _gran(30, "abcdefghij", "abcdefghij"), _gran(30, "abcdefghix", "abcdefghij"))))
    v = tb.avalua(str(f))
    assert v["decisio"]["adopta"], v["decisio"]["motius"]


def test_decisio_rebutja_si_cv_no_millora():
    st = {p: tb.bootstrap(g, n=200) for p, g in {"cv-zgh-test": _gran(80, "abcdefghij", "abcdefghij"), "test-fora": _gran(30, "abcdefghij", "abcdefghij"),
                                                  "snrt-retingut": _gran(30, "abcdefghix", "abcdefghij")}.items()}
    d = tb.decideix(st)
    assert not d["adopta"] and "NO millora" in d["motius"][0]


def test_decisio_rebutja_si_el_test_fora_empitjora_mes_de_0_005():
    cv = _gran(80, "abcdefghix", "abcdefghij")
    fora = _gran(100, "abcdefghij", "abcdefghij") + _gran(2, "abcdefghij", "abcdefghix")      # Δ = 2 / 1020 ~ +0,002: aguanta
    d = tb.decideix({"cv-zgh-test": tb.bootstrap(cv, n=200), "test-fora": tb.bootstrap(fora, n=200), "snrt-retingut": tb.bootstrap(_gran(10, "abcdefghix", "abcdefghij"), n=200)})
    assert d["adopta"]
    fora2 = _gran(100, "abcdefghij", "abcdefghij") + _gran(10, "abcdefghij", "abcdefghxx")    # Δ = 20 / 1100 ~ +0,018
    d2 = tb.decideix({"cv-zgh-test": tb.bootstrap(cv, n=200), "test-fora": tb.bootstrap(fora2, n=200), "snrt-retingut": tb.bootstrap(_gran(10, "abcdefghix", "abcdefghij"), n=200)})
    assert not d2["adopta"] and any("test-fora empitjora" in m for m in d2["motius"])


def test_decisio_rebutja_si_els_capitols_retinguts_empitjoren():
    cv = tb.bootstrap(_gran(80, "abcdefghix", "abcdefghij"), n=200)
    ok = tb.bootstrap(_gran(30, "abcdefghij", "abcdefghij"), n=200)
    ret = tb.bootstrap(_gran(30, "abcdefghij", "abcdefghix"), n=200)
    d = tb.decideix({"cv-zgh-test": cv, "test-fora": ok, "snrt-retingut": ret})
    assert not d["adopta"] and any("retinguts empitjoren" in m for m in d["motius"])


def test_decisio_sense_proves_no_adopta():
    assert not tb.decideix({})["adopta"]
    cv = tb.bootstrap(_gran(80, "abcdefghix", "abcdefghij"), n=200)
    assert not tb.decideix({"cv-zgh-test": cv})["adopta"]       # sense test-fora ni retinguts no es dona per bo


# ------------------------------------------------------------------ parada i registre
def test_parada_a_dos_cicles_sense_millora(tmp_path):
    s = str(tmp_path)
    assert tb.cicles_sense_millora(s) == 0
    tb.registra(s, {"adopta": True})
    tb.registra(s, {"adopta": False})
    assert tb.cicles_sense_millora(s) == 1
    tb.registra(s, {"adopta": False})
    assert tb.cicles_sense_millora(s) == 2
    with pytest.raises(SystemExit):
        tb.main(["cicle", "--sortida", s, "--arrel", str(tmp_path / "no")])


def test_nucli_porta_la_recepta_a_la_linia_i_cap_secret(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    d = tb.prepara_nucli(str(tmp_path), "B", repo)
    codi = open(os.path.join(d, "snrt-transcriptor-b.py"), encoding="utf-8").read()
    linies = codi.splitlines()
    assert 'RECEPTA = "B"' in linies and 'RECEPTA = "A"' not in linies
    meta = json.load(open(os.path.join(d, "kernel-metadata.json")))
    assert meta["is_private"] is True and "josepabloucr/snrt-transcriptor" in meta["dataset_sources"]
    assert not any(w in codi.lower() for w in ("api_key", "access_token", "secret", "password", "hf_"))


def test_espera_avisa_si_no_comença_en_90_min(monkeypatch, tmp_path):
    estats = iter(["queued", "queued", "queued", "running", "complete"])
    monkeypatch.setattr(tb, "estat_nucli", lambda r: next(estats))
    monkeypatch.setattr(tb, "kaggle", lambda *a, **k: "")
    rellotge = [0.0]
    monkeypatch.setattr(tb.time, "time", lambda: rellotge[0])
    avisos = []
    e, _ = tb.espera(str(tmp_path), "A", avisa=avisos.append, dorm=lambda s: rellotge.__setitem__(0, rellotge[0] + 3600))
    assert e == "complete" and len(avisos) == 1 and "90 min" in avisos[0]


def test_mostra_a_ull_es_reprodible_i_porta_referencia_abans_i_despres():
    sort = _sortides("snrt-retingut", [("abc", "abd", "abc")] * 50, video="cap")
    m = tb.mostra_a_ull(sort)
    assert len(m) == 30 and m == tb.mostra_a_ull(sort)
    assert set(m[0]) == {"video", "id", "ref", "abans", "despres"} and m[0]["ref"] == "abc" and m[0]["abans"] == "abd" and m[0]["despres"] == "abc"
    assert tb.mostra_a_ull(sort, prova="altra") == []


def test_el_nucli_no_filtra_per_cer_per_omissio():
    nucli = open(os.path.join(os.path.dirname(LM), "lm", "kaggle", "transcriptor_snrt.py"), encoding="utf-8").read().splitlines()
    assert "FILTRE_CER = None" in nucli and tb.FILTRE_CER is None


def test_un_tall_dubtos_per_alineacio_no_entra(tmp_path):
    _capitol(str(tmp_path), "llarg", 60)
    c = os.path.join(str(tmp_path), "llarg")
    al = json.load(open(os.path.join(c, "talls", "alineacio.json")))
    al["talls"]["llarg_0000"]["v"] = "dubtosa"
    json.dump(al, open(os.path.join(c, "talls", "alineacio.json"), "w"))
    aptes, diag = tb.selecciona(tb.llegeix_capitols(str(tmp_path)))
    assert len(aptes["llarg"]) == 59 and diag["llarg"]["descartades"]["alineació"] == 1


def test_alta_certesa_nomes_amb_el_flag_i_amb_concordanca(tmp_path, monkeypatch):
    _capitol(str(tmp_path), "llarg", 60)
    c = os.path.join(str(tmp_path), "llarg")
    json.dump({"llarg_0000": {"alta": True}, "llarg_0001": {"alta": False}}, open(os.path.join(c, "talls", "concordanca.json"), "w"))
    monkeypatch.delenv("SNRT_ALTA", raising=False)
    assert tb.alineacio_ok({"id": "llarg_0001"}, c) is True            # sense flag, només la porta d'alineació
    monkeypatch.setenv("SNRT_ALTA", "1")
    assert tb.alineacio_ok({"id": "llarg_0000"}, c) is True
    assert tb.alineacio_ok({"id": "llarg_0001"}, c) is False
    assert tb.alineacio_ok({"id": "llarg_0002"}, c) is False           # sense entrada a la concordància


def test_esquelet_estricte_i_parametres_suaus(tmp_path, monkeypatch):
    """SNRT_ESQ_MAX deixa passar només els «alta» amb consonants coincidents; SNRT_RITME/EPOQUES reescriuen el nucli."""
    import json as _j
    import os as _o
    sys_mod = __import__("tools.lm.transcriptor_bucle", fromlist=["x"]) if False else None  # noqa: F841
    import importlib.util
    arrel = _o.path.abspath(_o.path.join(_o.path.dirname(__file__), "..", ".."))
    esp = importlib.util.spec_from_file_location("tb", _o.path.join(arrel, "tools", "lm", "transcriptor_bucle.py"))
    tb = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(tb)
    talls = tmp_path / "talls"
    talls.mkdir()
    (talls / "alineacio.json").write_text(_j.dumps({"talls": {"a": {"v": "ok"}, "b": {"v": "ok"}}}))
    (talls / "concordanca.json").write_text(_j.dumps({
        "a": {"alta": True, "hip": "azul imanay", "text": "azul imannay"},
        "b": {"alta": True, "hip": "qqq ssdd", "text": "azul imannay"}}))
    monkeypatch.setenv("SNRT_ALTA", "1")
    assert tb.alineacio_ok({"id": "b"}, str(tmp_path)) is True
    monkeypatch.setenv("SNRT_ESQ_MAX", "0.4")
    assert tb.alineacio_ok({"id": "a"}, str(tmp_path)) is True
    assert tb.alineacio_ok({"id": "b"}, str(tmp_path)) is False
    monkeypatch.setenv("SNRT_RITME", "3e-05")
    monkeypatch.setenv("SNRT_EPOQUES", "3")
    d = tb.prepara_nucli(str(tmp_path / "s"), "B", arrel)
    codi = open(_o.path.join(d, "snrt-transcriptor-b.py"), encoding="utf-8").read()
    assert "RITME = 3e-05" in codi and "EPOQUES = 3\n" in codi and 'RECEPTA = "B"' in codi
