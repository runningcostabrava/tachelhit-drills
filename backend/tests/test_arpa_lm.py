# -*- coding: utf-8 -*-
"""El lector d'ARPA: que compti el que toca, i que el lèxic arribi de debò al feix.

Cap d'aquestes proves demana GPU ni model acústic: els logits es fabriquen a mà.
"""
import io
import os
import sys

import pytest

LM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                  "tools", "lm")
sys.path.insert(0, LM)
import arpa_lm  # noqa: E402


ARPA = """\\data\\
ngram 1=5
ngram 2=2

\\1-grams:
-1.000000\t</s>
-99.000000\t<s>\t-0.500000
-3.000000\t<unk>\t0.000000
-1.300000\tnkkin\t-0.400000
-1.600000\tmassa\t-0.200000

\\2-grams:
-0.200000\t<s> nkkin
-0.300000\tnkkin massa

\\end\\
"""


@pytest.fixture()
def model(tmp_path):
    f = tmp_path / "petit.arpa"
    f.write_text(ARPA, encoding="utf-8")
    return arpa_lm.Model(str(f))


def test_llegeix_l_arpa(model):
    assert model.order == 2
    assert len(model) == 5 and "nkkin" in model and "ineixpas" not in model


def test_el_bigrama_que_hi_es_val_el_seu_valor(model):
    e, s = arpa_lm.State(), arpa_lm.State()
    model.BeginSentenceWrite(e)
    assert model.BaseScore(e, "nkkin", s) == pytest.approx(-0.2)
    #: i el context que queda és la paraula que s'acaba de dir
    assert model.BaseScore(s, "massa", arpa_lm.State()) == pytest.approx(-0.3)


def test_el_bigrama_que_no_hi_es_paga_el_backoff(model):
    """`massa nkkin` no és al model: backoff(massa) + p(nkkin) = -0,2 + -1,3."""
    e, s = arpa_lm.State(), arpa_lm.State()
    model.NullContextWrite(e)
    model.BaseScore(e, "massa", s)
    assert model.BaseScore(s, "nkkin", arpa_lm.State()) == pytest.approx(-1.5)


def test_la_paraula_desconeguda_cau_a_unk(model):
    e = arpa_lm.State()
    model.NullContextWrite(e)
    assert model.BaseScore(e, "xyzzy", arpa_lm.State()) == pytest.approx(-3.0)


def test_una_frase_del_model_puntua_mes_que_una_que_no_ho_es(model):
    assert model.score("nkkin massa") > model.score("massa nkkin")


def test_un_arpa_que_no_hi_es_o_que_no_ho_es(tmp_path):
    with pytest.raises(OSError):
        arpa_lm.Model(str(tmp_path / "enlloc.arpa"))
    buit = tmp_path / "buit.arpa"
    buit.write_text("hola\n", encoding="utf-8")
    with pytest.raises(ValueError):
        arpa_lm.Model(str(buit))


def test_el_lexic_arriba_al_feix_amb_logits_fabricats(tmp_path):
    """La prova que importa: amb el model endollat, el feix tria la paraula del lèxic.

    Es fabriquen uns logits on «nkkin» i «nkkim» estan gairebé empatats acústicament. Sense
    model de llengua el feix es queda amb el que va mig punt per davant; amb el model, que
    només coneix «nkkin», ha de canviar d'opinió. És exactament el que ha de passar perquè el
    lèxic serveixi de res al feix: sense un ARPA, pyctcdecode **ignora** la llista de paraules.
    """
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyctcdecode")
    import pyctcdecode.decoder as pdec
    import pyctcdecode.language_model as plm

    f = tmp_path / "petit.arpa"
    f.write_text(ARPA, encoding="utf-8")

    #: quan kenlm no esta instal·lat l'atribut no existeix -- que es el cas d'aquesta
    #: maquina i el de Kaggle, i la rao de ser d'aquest modul
    SENSE = object()
    vell_plm = getattr(plm, "kenlm", SENSE)
    vell_pdec = getattr(pdec, "kenlm", SENSE)
    plm.kenlm = arpa_lm
    pdec.kenlm = arpa_lm
    try:
        from pyctcdecode import build_ctcdecoder
        lletres = ["", " ", "n", "k", "i", "m", "a", "s"]
        pas = {c: lletres.index(c) for c in lletres[1:]}
        #: CTC col·lapsa dues lletres iguals seguides si no hi ha un buit entremig: la paraula
        #: `nkkin` demana un fotograma de buit entre les dues `k`
        marcs = []
        for i, c in enumerate("nkkin"):
            if i and c == "nkkin"[i - 1]:
                marcs.append("")
            marcs.append(c)
        logits = np.full((len(marcs), len(lletres)), -12.0, dtype=np.float32)
        for t, c in enumerate(marcs):
            logits[t, lletres.index(c)] = 0.0
        #: l'última lletra: «n» i «m» gairebé empatades, amb la «m» mig punt per davant
        logits[-1, pas["n"]] = 0.0
        logits[-1, pas["m"]] = 0.5

        sense = build_ctcdecoder(lletres).decode(logits).strip()
        amb = build_ctcdecoder(lletres, kenlm_model_path=str(f),
                               alpha=2.0, beta=0.0).decode(logits).strip()
    finally:
        for modul, vell in ((plm, vell_plm), (pdec, vell_pdec)):
            if vell is SENSE:
                delattr(modul, "kenlm")
            else:
                modul.kenlm = vell

    assert sense == "nkkim", f"sense model de llengua hauria de guanyar l'acústica, i surt {sense!r}"
    assert amb == "nkkin", f"amb el lèxic hauria de guanyar la paraula coneguda, i surt {amb!r}"
