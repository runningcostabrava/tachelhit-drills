# -*- coding: utf-8 -*-
"""Concordància so<->text (tools/snrt/concordanca.py): l'esquelet ignora vocals i geminació; el rang del text real entre els
controls separa un parell bo d'un d'equivocat, i la falsa acceptació d'un aparellament barrejat és baixa."""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "snrt"))
import concordanca as cc  # noqa: E402


def frases(n=60, llavor=7):
    r = random.Random(llavor)
    return ["".join(r.choice("bdfgklmnqrstwyz") + r.choice("aiu") for _ in range(r.randint(6, 12))) for _ in range(n)]


def test_esquelet_ignora_vocals_geminacio_i_lletres_riques():
    assert cc.esquelet("ttamazirt") == cc.esquelet("tmzrt")
    assert cc.esquelet("aġεḍa") == cc.esquelet("gd")
    assert cc.esquelet("ak i u") == "k"


def test_parell_bo_te_rang_alt_i_marge_i_el_dolent_no():
    t = frases()
    ctrl = cc.controls_de(0, t)
    bo = cc.puntua(t[0].replace("a", "i", 2), t[0], ctrl)      # canvia vocals: l'esquelet no canvia
    assert bo["cer"] == 0 and bo["rang"] >= 0.95 and cc.alta_certesa(bo)
    dolent = cc.puntua(t[5], t[0], ctrl)                       # la hipòtesi és d'una altra frase
    assert not cc.alta_certesa(dolent)


def test_falsa_acceptacio_barrejant_els_parells_es_baixa():
    t = frases(80)
    assert cc.far(t, t) is not None and cc.far(t, t) <= 0.10   # hipòtesi ideal, text d'un altre tall
    assert cc.far(t, t[:2]) is None


def test_controls_son_deterministes_i_no_inclouen_el_text_real():
    t = frases()
    a = cc.controls_de(3, t)
    assert a == cc.controls_de(3, t) and t[3] not in a and len(a) == cc.CONTROLS
