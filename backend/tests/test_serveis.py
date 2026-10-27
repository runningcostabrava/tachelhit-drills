"""Quina màquina fa cada feina, i si ara mateix contesta (#295).

El que es prova és la regla 5 de la casa: **cap servei no és l'únic, i una feina que es queda
sense ningú ho ha de DIR en comptes de callar.** El 24-10-2026 tres proveïdors van caure el
mateix dia i qui feia servir l'app només veia que «no anava».
"""
import serveis
from test_api import client


def test_una_feina_sense_ningu_que_la_pugui_fer_ho_diu():
    tot_be = serveis.quina_feina_fa_qui(
        spaces={"asr": {"state": "up"}, "translation": {"state": "up"}, "image": {"state": "up"}},
        gemini_ok=True, gemini_clau=True, deepseek_clau=True)
    assert tot_be["aturades"] == [], tot_be["aturades"]
    assert all(f["funciona"] for f in tot_be["feines"])

    tot_caigut = serveis.quina_feina_fa_qui(
        spaces={"asr": {"state": "down"}, "translation": {"state": "down"}, "image": {"state": "down"}},
        gemini_ok=False, gemini_clau=False, deepseek_clau=False)
    quines = {f["id"]: f for f in tot_caigut["feines"]}
    assert "traduir-amazic" in tot_caigut["aturades"]
    assert quines["traduir-amazic"]["funciona"] is False
    assert [q["diu"] for q in quines["traduir-amazic"]["qui"]] == [
        "sense clau configurada", "sense clau configurada"]

    # Escriure amazic no depèn de cap màquina: ho fa qui parla la llengua, i per això aquesta
    # feina no s'atura mai.
    assert quines["escriure-amazic"]["funciona"] is True
    assert quines["escriure-amazic"]["qui"][0]["diu"] == "ho fa una persona"


def test_no_shan_mirat_no_es_el_mateix_que_no_contesten():
    """Amb `prova=0` no es truca a cap Space. Dir-ne «no contesta» seria inventar-se una mesura
    que no s'ha fet, i aquesta app no fa això enlloc."""
    sense_mirar = serveis.quina_feina_fa_qui(spaces=None, gemini_ok=True, gemini_clau=True, deepseek_clau=True)
    transcriure = {f["id"]: f for f in sense_mirar["feines"]}["transcriure"]
    assert transcriure["qui"][0]["diu"] == "no s'ha mirat"

    mirat = serveis.quina_feina_fa_qui(spaces={"asr": {"state": "down"}}, gemini_ok=True,
                                       gemini_clau=True, deepseek_clau=True)
    assert {f["id"]: f for f in mirat["feines"]}["transcriure"]["qui"][0]["diu"] == "no contesta"


def test_dun_servei_de_pagament_no_es_diu_que_contesta():
    """El 24-10-2026 Gemini tenia clau, tenia pressupost i contestava «402 prepayment credits are
    depleted». De la nostra banda només se sap que hi ha clau i que queda pressupost nostre."""
    r = serveis.quina_feina_fa_qui(spaces={}, gemini_ok=True, gemini_clau=True, deepseek_clau=True)
    escriure = {f["id"]: f for f in r["feines"]}["escriure"]
    assert [q["diu"] for q in escriure["qui"]] == [
        "hi ha clau i pressupost (si contesta, no se sap fins que se li truca)"] * 2
    assert escriure["funciona"] is True, "amb clau i pressupost, la feina es pot fer"


def test_distingeix_no_tenir_clau_de_haver_gastat_el_pressupost():
    """Dues coses que no es poden confondre: no tenir el servei configurat, i tenir-lo i haver
    arribat al pressupost del mes. La primera és feina de muntatge; la segona, una decisió."""
    sense = serveis.quina_feina_fa_qui(spaces={}, gemini_ok=False, gemini_clau=False, deepseek_clau=True)
    gastat = serveis.quina_feina_fa_qui(spaces={}, gemini_ok=False, gemini_clau=True, deepseek_clau=True)
    de = lambda r, feina, i: {f["id"]: f for f in r["feines"]}[feina]["qui"][i]["diu"]  # noqa: E731
    assert de(sense, "escriure", 1) == "sense clau configurada"
    assert de(gastat, "escriure", 1) == "ha arribat al pressupost del mes"


def test_la_porta_serveix_la_taula_sencera_sense_trucar_a_ningu():
    """Amb `prova=0` no es truca a cap Space: la taula es pot llegir igualment, i el que no se
    sap no s'inventa."""
    r = client.get("/serveis?prova=0").json()
    assert [f["id"] for f in r["feines"]] == [f["id"] for f in serveis.FEINES]
    assert all(f["titol"] and f["explica"] and f["regla"] for f in r["feines"])
    assert len(r["regles"]) == 6 and "suggerit" in r["regles"][0]
    assert "crèdit" in r["avis"], "es diu el que NO es pot saber sense trucar-hi"
    # transcriure té el nostre Space de primer, i «per contrastar» de segon: la regla 4.
    transcriure = next(f for f in r["feines"] if f["id"] == "transcriure")
    assert transcriure["qui"][0]["paper"] == "primer"
    assert "contrastar" in transcriure["qui"][1]["paper"]
