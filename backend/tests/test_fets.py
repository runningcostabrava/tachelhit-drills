# -*- coding: utf-8 -*-
"""El filtre dels fets: res que no tingui un token darrere no es desa.

Les dues trampes que el va fer néixer (14-11-2026): una frase pot OMETRE un token (`islman` =
«peix» glossat bé, i la frase parla d'una altra cosa) i pot ESCRIURE UNA RELACIÓ («és diferent
de» amb la glossa dient «lligat»). La interlineal no pot ometre; el marc no pot relacionar.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fets  # noqa: E402

TROS = "tagurin islman tga tamaziġt"          # 4 tokens


def resposta(**k):
    base = {
        "interlineal": ["paraules", "peix", "és", "amazic"],
        "marc": {"tema": "les paraules del peix", "mena": "afirmació",
                 "polaritat": "afirmatiu", "qui_hi_surt": []},
        "cita": None,
        "frase": "Les paraules del peix són amazigues.",
        "soste": {"paraules": [0], "peix": [1], "amazigues": [3]},
    }
    base.update(k)
    return json.dumps(base, ensure_ascii=False)


def test_una_resposta_ben_sostinguda_passa_sencera():
    f, motius = fets.comprova(resposta(), TROS)
    assert f and not motius
    assert f["interlineal"] == ["paraules", "peix", "és", "amazic"]
    assert f["frase"] == "Les paraules del peix són amazigues."
    assert f["marc"]["tema"] == "les paraules del peix"


def test_la_interlineal_ha_de_fer_la_llargada_dels_tokens():
    #: Si pot saltar-se'n un, el filtre no serveix: es rebutja TOT, no es poda.
    f, motius = fets.comprova(resposta(interlineal=["paraules", "peix", "és"]), TROS)
    assert f is None and "interlineal de 3" in motius[0]


def test_una_frase_amb_una_paraula_sense_token_cau():
    #: «poques» no surt de cap token: és la invenció del #9.
    f, motius = fets.comprova(
        resposta(frase="Les paraules amazigues són poques.",
                 soste={"paraules": [0], "amazigues": [3]}), TROS)
    assert f["frase"] is None
    assert any("poques" in m for m in motius)
    #: i la interlineal i el marc sobreviuen: la frase va A PART
    assert f["interlineal"][1] == "peix"


def test_el_tema_sense_token_cau_a_interrogant():
    f, motius = fets.comprova(resposta(marc={"tema": "la lingüística comparada",
                                              "mena": "afirmació", "polaritat": "afirmatiu",
                                              "qui_hi_surt": []}), TROS)
    assert f["marc"]["tema"] == "?"
    assert any("tema sense token" in m for m in motius)


def test_la_cita_ha_de_ser_un_token_copiat():
    f, _ = fets.comprova(resposta(cita="islman"), TROS)
    assert f["cita"] == "islman"
    f, motius = fets.comprova(resposta(cita="imikk"), TROS)
    assert f["cita"] is None and any("cita" in m for m in motius)


def test_una_persona_sense_token_no_surt():
    #: «qui hi surt» només si una forma verbal o un pronom ho sosté.
    f, motius = fets.comprova(resposta(
        marc={"tema": "?", "mena": "?", "polaritat": "?", "qui_hi_surt": ["jo", "ells/elles"]},
        soste={"qui:ells/elles": [2]}), TROS)
    assert f["marc"]["qui_hi_surt"] == ["ells/elles"]
    assert any("persona sense token: jo" in m for m in motius)


def test_mena_i_polaritat_fora_de_la_llista_cauen_a_interrogant():
    f, _ = fets.comprova(resposta(marc={"tema": "?", "mena": "exclamació",
                                         "polaritat": "dubtós", "qui_hi_surt": []}), TROS)
    assert f["marc"]["mena"] == "?" and f["marc"]["polaritat"] == "?"


def test_el_json_pot_venir_entre_cometes_de_bloc():
    f, motius = fets.comprova("```json\n" + resposta() + "\n```", TROS)
    assert f and not motius


def test_el_que_no_es_json_es_rebutja_i_es_diu():
    f, motius = fets.comprova("CATALA: Les paraules del peix.\nCERTESA: probable", TROS)
    assert f is None and motius == ["la resposta no és JSON"]


def test_els_indexos_fora_de_rang_no_sostenen_res():
    f, motius = fets.comprova(resposta(soste={"paraules": [0], "peix": [9], "amazigues": [3]}),
                              TROS)
    #: `peix` apuntava al token 9, que no existeix: la frase i el tema que el fan servir cauen
    assert f["frase"] is None and f["marc"]["tema"] == "?"


def test_una_clau_de_dues_paraules_sosté_totes_dues():
    #: El #30 de la mostra: «al sud diuen una mica», amb la clau «una mica» → token 4. El
    #: filtre buscava «mica» com a clau sencera i podava la frase. Era el filtre qui mentia.
    f, motius = fets.comprova(resposta(
        frase="Al sud diuen una mica.",
        soste={"sud": [1], "diuen": [3], "una mica": [1]}), TROS)
    assert f["frase"] == "Al sud diuen una mica."
    assert not any("mica" in m for m in motius)
