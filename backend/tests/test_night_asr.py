# -*- coding: utf-8 -*-
"""El transcriptor de nit: proposa, no decideix."""
import night_asr


def test_una_gravacio_sense_text_entra_a_la_cua(monkeypatch):
    """La cua són les gravacions que ningú no ha escrit, les curtes primer.

    Les curtes primer no és una manià: una gravació de dos segons es transcriu bé i es confirma
    de pressa, i una de dos minuts es menja la nit sense que ningú la confirmi.
    """
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("night_asr_user")}
    muda = client.post("/drills/", headers=hdr, json={
        "text_catalan": "sense veu", "text_tachelhit": "ur illi"}).json()
    espera = client.post("/drills/", headers=hdr, json={
        "text_arabic": "مرحبا",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/espera.mp3"}).json()
    feta = client.post("/drills/", headers=hdr, json={
        "text_tachelhit": "azul", "text_catalan": "hola",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/feta.mp3"}).json()

    db = main.SessionLocal()
    try:
        ids = [d.id for d in night_asr._pending(db, 50, redo=False)]
    finally:
        db.close()
    assert espera["id"] in ids, "una gravació sense text amazic espera"
    assert feta["id"] not in ids, "una que ja té text no es torna a transcriure"
    assert muda["id"] not in ids, "i una frase sense veu no es pot transcriure"

    for i in (muda["id"], espera["id"], feta["id"]):
        client.delete(f"/drills/{i}", headers=hdr)


def test_el_que_diu_la_maquina_no_es_el_text_del_parlant(monkeypatch):
    """La proposta va a `text_tachelhit_suggested` amb la seva certesa, i el text es queda buit.

    És la regla de la casa i aquí és tota la raó de ser del camp: una màquina pot encertar i pot
    inventar, i qui llegeix ha de saber què està llegint.
    """
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("night_asr_writer")}
    d = client.post("/drills/", headers=hdr, json={
        "text_arabic": "شكرا",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/gracies.mp3"}).json()

    monkeypatch.setattr(night_asr, "transcribe_one",
                        lambda url: {"text": "ⵜⴰⵏⵎⵎⵉⵔⵜ", "confidence": 0.82, "segments": []})
    night_asr._work(main.SessionLocal, limit=10, redo=False)

    back = client.get(f"/drills/{d['id']}").json()
    try:
        assert back["text_tachelhit_suggested"] == "ⵜⴰⵏⵎⵎⵉⵔⵜ", "la proposta es desa"
        assert not back.get("text_tachelhit"), "el text del parlant es queda buit"
        assert back.get("suggested_confidence") == 0.82, "i la certesa es desa al costat"
        assert night_asr.state()["written"] >= 1
    finally:
        client.delete(f"/drills/{d['id']}", headers=hdr)


def test_una_gravacio_que_no_es_pot_transcriure_no_es_cap_error(monkeypatch):
    """Es queda esperant i es compta, i ningú no veu cap error: el Space pot estar adormit."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("night_asr_fail")}
    d = client.post("/drills/", headers=hdr, json={
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/muda.mp3"}).json()
    monkeypatch.setattr(night_asr, "transcribe_one", lambda url: None)
    night_asr._work(main.SessionLocal, limit=10, redo=False)
    back = client.get(f"/drills/{d['id']}").json()
    try:
        assert not back.get("text_tachelhit_suggested")
        assert night_asr.state()["failed"] >= 1
    finally:
        client.delete(f"/drills/{d['id']}", headers=hdr)
