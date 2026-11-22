"""Dues coses que una pràctica havia de fer i no feia (#219).

Totes dues venien del mateix lloc: des de l'ADR 0002 una pràctica **és** una seqüència de
passos, però hi havia camins que només tocaven la llista plana `drill_ids` o la taula de passos,
i mai les dues coses alhora.
"""
from datetime import datetime, timedelta

from test_api import client


def _fes_frase(text, catala):
    r = client.post("/drills/", json={"text_tachelhit": text, "text_catalan": catala})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_punts_febles_neix_amb_passos():
    """«Punts febles» naixia amb la llista plana i CAP pas, i el taller l'ensenyava buida.

    Qui la demana té targetes que li costen i vol practicar-les; obrir-la i no trobar-hi res és
    pitjor que no haver-la pogut crear.
    """
    for i in range(3):
        _fes_frase(f"ⴰⵣⵓⵍ {i}", f"hola {i}")

    r = client.post("/tests/from-weakest", json={"count": 3})
    assert r.status_code == 200, r.text
    fora = r.json()
    assert fora["drill_count"] >= 3

    # El que importa: la pràctica té passos, i tants com frases.
    assert fora["step_count"] == fora["drill_count"], fora
    passos = client.get(f"/tests/{fora['test_id']}/steps")
    assert passos.status_code == 200, passos.text
    assert len(passos.json()) == fora["step_count"]


def test_els_passos_automatics_no_demanen_imitar_veus_anonimes():
    """«Escolta i escriu» demana repetir el que se sent: només val amb una veu amb nom (#273).

    Una frase sense gravació —o amb una veu d'un canal— no pot ser model de pronúncia, i una
    pràctica que ho demanés estaria enganyant qui la fa.
    """
    import main
    import practice_steps

    muda = _fes_frase("ⵜⴰⵣⵣⵍⴰ ⵏ ⵓⵎⵓⴷⴷⵓ", "la carrera del viatge")
    with main.SessionLocal() as db:
        passos = practice_steps.passos_automatics(db, [muda])

    assert len(passos) == 1
    assert passos[0]["drill_id"] == muda
    # Sense veu de persona, l'eina ha de ser la d'escoltar i triar, no la d'imitar.
    assert passos[0]["kind"] not in practice_steps.PER_IMITAR, passos


def test_canviar_els_passos_mou_la_data_de_la_practica():
    """`GET /tests/?since=` mira `tests.updated_at`: si reescriure els passos no la mou, qui té
    l'app oberta fora de línia es queda amb la versió vella i res no li diu que ha canviat."""
    a = _fes_frase("ⵉⵎⵉⴽ", "una mica")
    b = _fes_frase("ⴰⵟⵟⴰⵚ", "molt")

    r = client.post("/tests/", json={
        "title": "Provar la data", "question_type": "text_input", "hint_level": "none",
        "passing_score": 70.0, "drill_ids": f"{a}",
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]

    abans = client.get(f"/tests/{tid}").json().get("updated_at")
    assert abans, "una pràctica ha de portar la data de l'últim canvi"

    # Es reescriuen els passos amb una frase diferent: la pràctica ha canviat de debò.
    r = client.put(f"/tests/{tid}/steps", json={
        "steps": [{"kind": "listen_pick", "drill_id": b, "payload": None}]})
    assert r.status_code == 200, r.text

    despres = client.get(f"/tests/{tid}").json().get("updated_at")
    assert despres and despres != abans, (
        "canviar els passos és canviar la pràctica: la data s'ha de moure")

    # I `since` l'ha de veure: demanant el que ha canviat des d'un moment anterior, hi ha de ser.
    marca = (datetime.fromisoformat(str(abans).replace("Z", ""))
             - timedelta(seconds=1)).isoformat()
    canviades = client.get("/tests/", params={"since": marca})
    assert canviades.status_code == 200, canviades.text
    ids = [t["id"] for t in canviades.json()]
    assert tid in ids, "la pràctica que acaba de canviar ha de sortir a `since`"
