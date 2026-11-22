"""Gravar primer i escriure després (#450).

Al telèfon, els dos micròfons són el primer que es fa servir: es prem, es parla, i el text ve
després —o no ve mai, i la gravació val igual. Per pujar el fitxer cal l'id de la frase, i per
crear la frase calia contingut: la frase no podia néixer i el micròfon donava «cal text».
"""


def test_qui_captura_pot_crear_la_frase_buida_i_pujar_hi_la_veu():
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_grava_primer")}

    buit = client.post("/drills/", headers=hdr, json={"text_catalan": "", "text_tachelhit": ""})
    assert buit.status_code == 422, "una frase sense res segueix sense poder-se crear"

    r = client.post("/drills/", headers=hdr, json={"capturing": True, "tag": "captura"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] and not (d.get("text_tachelhit") or "").strip()
    assert "capturing" not in d, "«capturing» és una manera de demanar-ho, no un camp de la fila"

    # i tot seguit hi arriba la gravació, que és el que la fa valer
    posat = client.put(f"/drills/{d['id']}", headers=hdr,
                       json={"audio_url": "https://res.cloudinary.com/x/video/upload/v1/rec.m4a"})
    assert posat.status_code == 200 and posat.json()["audio_url"].endswith("rec.m4a")
