"""Gravar una frase que ja existeix: la meva presa, els meus sons (#332).

Quan algú grava una frase que ja hi és, poden estar passant coses diferents i no totes volen dir
el mateix. Les dues que faltaven:

· **«Sóc jo altra vegada».** Cada gravació feia una fila nova, sempre. Si la mateixa persona
  tornava a gravar la mateixa frase —la primera va sortir malament, o ara té un micròfon millor—
  se n'acumulaven dues de la mateixa veu i ningú no sabia quina valia.
· **Les mateixes paraules, dites d'una altra manera.** No són altres paraules —això ja fa néixer
  una variant— sinó la mateixa paraula amb uns altres sons. Això es perdia.
"""
import io

import main
from test_api import client


def _user(name, **kw):
    r = client.post("/users/register", json={"username": name, **kw}).json()
    return {"X-User-Token": r["token"]}


def _grava(drill_id, headers, monkeypatch, fitxer, **camps):
    monkeypatch.setattr(main.cloudinary.uploader, "upload",
                        lambda *a, **k: {"secure_url": f"https://res.cloudinary.com/x/video/upload/v1/tachelhit/recordings/{fitxer}"})
    r = client.post(f"/drills/{drill_id}/recordings",
                    files={"file": ("take.webm", io.BytesIO(b"abc"), "audio/webm")},
                    data={k: str(v) for k, v in camps.items()},
                    headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_soc_jo_altra_vegada_substitueix_la_meva_presa_i_nomes_la_meva(monkeypatch):
    d = client.post("/drills/", json={"text_catalan": "aigua", "text_tachelhit": "aman"}).json()
    halima = _user("presa_halima", variety="tdl", region="Aït Mraw (Azilal)")
    driss = _user("presa_driss", variety="shi", region="Taroudant")

    primera = _grava(d["id"], halima, monkeypatch, "halima_1.webm")
    assert primera["substituida"] is False and primera["meves"] == 1
    _grava(d["id"], driss, monkeypatch, "driss_1.webm")

    # La primera veu d'una frase muda passa a ser la seva veu principal: aquí la frase ja en
    # tenia, així que mirem que la substitució la segueixi si era la seva.
    abans = client.get(f"/drills/{d['id']}").json()["audio_url"]
    assert "halima_1" in abans

    segona = _grava(d["id"], halima, monkeypatch, "halima_2.webm", substitueix=True)
    assert segona["substituida"] is True
    assert segona["id"] == primera["id"], "és la mateixa fila, no una de nova"
    assert "halima_2" in segona["audio_url"]

    totes = client.get(f"/drills/{d['id']}/recordings", headers=halima).json()
    assert len(totes) == 2, "dues persones, dues preses: no se n'ha acumulat cap de la mateixa veu"
    meva = next(r for r in totes if r["mine"])
    altra = next(r for r in totes if not r["mine"])
    assert "halima_2" in meva["audio_url"], "la meva és la nova"
    assert "driss_1" in altra["audio_url"], "i la d'un altre no s'ha tocat"

    despres = client.get(f"/drills/{d['id']}").json()["audio_url"]
    assert "halima_2" in despres, "la veu principal era la seva presa: ara apunta a la nova"


def test_sense_demanar_ho_la_presa_sacumula_com_sempre(monkeypatch):
    """Substituir és una decisió de qui grava, no una cosa que passi sola: qui vol deixar-hi les
    dues preses (la del matí i la de la tarda, per comparar-les) ha de poder."""
    d = client.post("/drills/", json={"text_catalan": "pa", "text_tachelhit": "aɣrum"}).json()
    jo = _user("presa_dues", variety="tdl", region="Aït Mraw (Azilal)")
    _grava(d["id"], jo, monkeypatch, "jo_1.webm")
    segona = _grava(d["id"], jo, monkeypatch, "jo_2.webm")
    assert segona["substituida"] is False and segona["meves"] == 2
    assert len(client.get(f"/drills/{d['id']}/recordings", headers=jo).json()) == 2


def test_les_mateixes_paraules_dites_duna_altra_manera_queden_marcades(monkeypatch):
    """La fitxa no pot dir que una frase es diu d'una manera mentre la veu en diu una altra sense
    que consti enlloc."""
    d = client.post("/drills/", json={"text_catalan": "la botiga", "text_tachelhit": "thanut"}).json()
    jo = _user("presa_sons", variety="tdl", region="Aït Mraw (Azilal)")
    r = _grava(d["id"], jo, monkeypatch, "sons.webm", sons_diferents=True)
    assert r["sounds_differ"] is True
    assert r["text"] is None, "no són altres paraules: no neix cap variant"
    assert r["variant_id"] is None

    llista = client.get(f"/drills/{d['id']}/recordings", headers=jo).json()
    assert llista[0]["sounds_differ"] is True


def test_qui_grava_pot_dir_que_la_seva_veu_sigui_la_de_la_targeta(monkeypatch):
    """`drill.audio_url` és el que sona al Mètode i a la pràctica, i el que la puntuació de
    pronunciació fa servir de referència. Amb diverses preses hi ha d'haver una manera de dir
    quina mana, i no pot ser «la més nova»."""
    d = client.post("/drills/", json={"text_catalan": "el cap", "text_tachelhit": "ixf"}).json()
    halima = _user("principal_halima", variety="tdl", region="Aït Mraw (Azilal)", is_native=True)
    driss = _user("principal_driss", variety="shi", region="Taroudant", is_native=True)

    una = _grava(d["id"], halima, monkeypatch, "principal_h.webm", is_native=True)
    altra = _grava(d["id"], driss, monkeypatch, "principal_d.webm", is_native=True)
    assert "principal_h" in client.get(f"/drills/{d['id']}").json()["audio_url"]

    # un desconegut no pot decidir quina veu mana
    assert client.post(f"/recordings/{altra['id']}/principal").status_code == 403
    # i jo no puc posar la d'un altre
    assert client.post(f"/recordings/{una['id']}/principal", headers=driss).status_code == 403

    r = client.post(f"/recordings/{altra['id']}/principal", headers=driss)
    assert r.status_code == 200, r.text
    assert "principal_d" in client.get(f"/drills/{d['id']}").json()["audio_url"]


def test_una_veu_daprenent_no_passa_davant_duna_de_nadiu(monkeypatch):
    """No és un judici sobre ningú: aquella veu es converteix en l'objectiu que els altres han
    d'encertar (#288). La gravació hi és igual i s'escolta igual."""
    d = client.post("/drills/", json={"text_catalan": "la clau", "text_tachelhit": "tasarut"}).json()
    nadiu = _user("aprenent_nadiu", variety="tdl", region="Aït Mraw (Azilal)", is_native=True)
    qui_apren = _user("aprenent_jo", variety="tdl", region="Barcelona", is_native=False)

    _grava(d["id"], nadiu, monkeypatch, "nadiu.webm", is_native=True)
    seva = _grava(d["id"], qui_apren, monkeypatch, "aprenent.webm", is_native=False)

    r = client.post(f"/recordings/{seva['id']}/principal", headers=qui_apren)
    assert r.status_code == 409, r.text
    assert "de tota la vida" in r.json()["detail"]
    assert "nadiu" in client.get(f"/drills/{d['id']}").json()["audio_url"]


def test_un_sinonim_no_es_una_variant_dialectal(monkeypatch):
    """Les dues coses anaven al mateix calaix i per a qui aprèn no són el mateix: «ho diem igual
    però ho escrivim diferent» li diu com sona la paraula que està estudiant, i «al meu poble en
    diem una altra» li ensenya una paraula nova (#332)."""
    d = client.post("/drills/", json={"text_catalan": "la noia", "text_tachelhit": "tafruxt"}).json()
    un = _user("mena_un", variety="tdl", region="Aït Mraw (Azilal)")
    altre = _user("mena_altre", variety="shi", region="Taroudant")

    r1 = _grava(d["id"], un, monkeypatch, "mena_so.webm", text="tafruxt", mena="so")
    assert r1["variant_id"] is None, "el mateix text no fa néixer cap variant"

    r2 = _grava(d["id"], un, monkeypatch, "mena_so2.webm", text="tafroxt", mena="so")
    assert r2["variant_id"], "una altra grafia sí"
    r3 = _grava(d["id"], altre, monkeypatch, "mena_paraula.webm", text="tabrat", mena="paraula")

    # Les altres maneres, cadascuna amb la seva mena, perquè la pantalla les pugui separar.
    maneres = {m["text"]: m for m in client.get(f"/drills/{d['id']}/recordings", headers=un).json()}
    assert maneres["tafroxt"]["variant_kind"] == "so"
    assert maneres["tabrat"]["variant_kind"] == "paraula"

    # i la frase variant que n'ha nascut s'ho queda
    variants = client.get(f"/drills/{d['id']}/variants").json()["variants"]
    per_text = {v["text_tachelhit"]: v for v in variants}
    assert per_text["tafroxt"]["variant_kind"] == "so"
    assert per_text["tabrat"]["variant_kind"] == "paraula", r3["variant_id"]

    # Una mena que no existeix no s'accepta: val més no saber-ho que apuntar-ho malament.
    dolenta = client.post(f"/drills/{d['id']}/recordings",
                          files={"file": ("t.webm", io.BytesIO(b"abc"), "audio/webm")},
                          data={"text": "tafruxtt", "mena": "dialecte"}, headers=un)
    assert dolenta.status_code == 400 and "mena de variant" in dolenta.json()["detail"]


def test_escriure_com_ho_dius_tu_sense_gravar_tambe_diu_de_quina_mena_es():
    d = client.post("/drills/", json={"text_catalan": "el llibre", "text_tachelhit": "lktab"}).json()
    jo = _user("mena_escrita", variety="tdl", region="Aït Mraw (Azilal)")
    r = client.post(f"/drills/{d['id']}/variant", headers=jo,
                    json={"text_tachelhit": "adlis", "mena": "paraula"})
    assert r.status_code == 200, r.text
    assert r.json()["variant_kind"] == "paraula"
