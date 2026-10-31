"""Una càrrega massiva no engega els efectes de cada frase (#539).

Escriure el català d'una frase fa dues coses més: la traducció a l'àrab i la veu catalana. Fetes
una a una, des de l'app, són el que toca. Fetes a centenars seguides, quan els auditors confirmen
traduccions, tombaven el Render. `quiet: true`, només per a qui administra, desa el text i prou.
"""


def test_quiet_desa_el_text_i_no_engega_ni_traduccio_ni_veu(monkeypatch):
    import main
    from test_api import client, register

    crides = []
    monkeypatch.setattr(main, "generate_catalan_tts", lambda text, drill_id: crides.append(("tts", drill_id)) or "https://x/tts.mp3")
    monkeypatch.setattr(main.translator_ca_to_ar, "translate", lambda text: crides.append(("ar", text)) or "عربي")

    hdr = {"X-User-Token": register("qui_carrega_en_massa")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()
    d = client.post("/drills/", headers=hdr, json={"text_tachelhit": "azul fellawn", "author": "Prova-quiet"}).json()

    r = client.put(f"/drills/{d['id']}", headers=hdr, json={"text_catalan": "hola a tots", "quiet": True})
    assert r.status_code == 200 and r.json()["text_catalan"] == "hola a tots"
    assert crides == [], "amb quiet no s'engega res"
    assert not r.json().get("audio_tts_url")

    r = client.put(f"/drills/{d['id']}", headers=hdr, json={"text_catalan": "hola a tothom"})
    assert r.status_code == 200
    assert ("tts", d["id"]) in crides and any(k == "ar" for k, _ in crides), "sense quiet, els efectes de sempre"


def test_quiet_no_val_per_a_qui_no_administra(monkeypatch):
    import main
    from test_api import client, register

    crides = []
    monkeypatch.setattr(main, "generate_catalan_tts", lambda text, drill_id: crides.append(("tts", drill_id)) or "https://x/tts.mp3")
    monkeypatch.setattr(main.translator_ca_to_ar, "translate", lambda text: "عربي")
    hdr = {"X-User-Token": register("qui_no_administra_quiet")}
    d = client.post("/drills/", headers=hdr, json={"text_tachelhit": "azul", "author": "Prova-quiet-2"}).json()
    r = client.put(f"/drills/{d['id']}", headers=hdr, json={"text_catalan": "hola", "quiet": True})
    assert r.status_code == 200
    assert crides, "qui no administra no pot apagar els efectes"
