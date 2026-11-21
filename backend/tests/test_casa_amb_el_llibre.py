"""La pila que aparella una gravació del CD amb una línia del llibre (#476).

Aquesta pila és d'una altra naturalesa que les altres i les proves han de guardar justament
això: el text **no** és d'una màquina —és la línia escrita per l'autor del mètode— i el que va
fer una màquina és dir que aquella gravació diu aquella línia. Per tant:

· mentre ningú no ho hagi confirmat, la línia viu a `text_tachelhit_suggested`, mai al camp
  del parlant;
· quan una persona ho confirma, hi pot anar, perquè ja no és una màquina qui ho afirma;
· i si una persona diu que no, la proposta s'ha d'esborrar —deixar-la seria deixar escrit que
  la gravació diu una cosa que no diu—, però la gravació es queda.
"""
import json

from test_api import client


def _fes_frase(catala=None):
    r = client.post("/drills/", json={"text_catalan": catala or "del CD del Mètode"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _com_admin(nom):
    import main
    from models import User as UserModel

    u = client.post("/users/register", json={"username": nom}).json()
    with main.SessionLocal() as db:
        row = db.query(UserModel).filter(UserModel.username == nom).first()
        row.is_admin = True
        db.commit()
    return {"X-User-Token": u["token"]}


def _posa(drill_id, **camps):
    import main
    from models import Drill as DrillModel
    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
        for k, v in camps.items():
            setattr(d, k, v)
        db.commit()


def _llegeix(drill_id):
    import main
    from models import Drill as DrillModel
    with main.SessionLocal() as db:
        return db.query(DrillModel).filter(DrillModel.id == drill_id).first()


def _demana(drill_id, cap):
    """La nostra frase dins de la pila, saltant les que hi hagi deixat una altra prova.

    La pila serveix sempre la de l'identificador més baix, i «no ho sé» deixa l'etiqueta posada
    a posta. Donar per fet que la primera és la nostra faria que la prova passés o caigués
    segons l'ordre en què pytest les executa, que és aleatori.
    """
    saltats = []
    for _ in range(40):
        r = client.get("/revisa/casa-amb-el-llibre",
                       params={"saltats": ",".join(str(x) for x in saltats)} if saltats else {},
                       headers=cap)
        assert r.status_code == 200, r.text
        fora = r.json()
        if not fora.get("drill"):
            raise AssertionError("la frase #%d no surt a la pila" % drill_id)
        if fora["drill"]["id"] == drill_id:
            return fora
        saltats.append(fora["drill"]["id"])
    raise AssertionError("massa frases a la pila abans de la nostra")


def _prepara(nom, linia="is tskrm ibrin i-Zinb d-Yamna?", pagina=59):
    """Una gravació del CD amb la línia del llibre proposada i la seva procedència."""
    i = _fes_frase()
    _posa(i, tag="casa-amb-el-llibre",
          video_url="https://www.youtube.com/watch?v=zkvUblbTdws",
          video_start_time=12.4, video_end_time=14.5,
          text_tachelhit_suggested=linia,
          esborranys=json.dumps([
              {"text": linia, "model": "el llibre, pàgina %d" % pagina,
               "acord": 0.95, "font": "Mètode d'El Mountassir, pàgina %d" % pagina},
          ], ensure_ascii=False))
    return i, _com_admin(nom)


def test_el_parentesi_del_llibre_no_sona_i_la_proposta_el_treu():
    """En Pablo va escoltar 30 talls (29/10): «(dar)», «(afasi)», «(lbɛd n-tkal)» no sonen mai,
    són indicacions de l'exercici. La proposta que s'edita els ha de dur trets; el text original
    es conserva al costat per poder anar a mirar el llibre."""
    i, cap = _prepara("admin_casa_parentesi", linia="iskr Brahim ttilifun i-gʷma-s. (lbɛd n-tkal)")
    cos = _demana(i, cap)
    e = cos["esborranys"][0]
    assert e["text"] == "iskr Brahim ttilifun i-gʷma-s. (lbɛd n-tkal)"
    assert e["text_net"] == "iskr Brahim ttilifun i-gʷma-s."


def test_la_pila_existeix_i_pregunta_pel_so_no_pel_text():
    """La pregunta ha de ser si la gravació DIU això: és el que es pot respondre escoltant."""
    import revisa

    pila = revisa.PILES["casa-amb-el-llibre"]
    assert "diu" in pila["pregunta"].lower()
    assert {o["id"] for o in pila["opcions"]} == {"tria", "fora", "no-ho-se"}


def test_abans_de_confirmar_la_linia_no_es_al_camp_del_parlant():
    i, cap = _prepara("admin_casa_abans")
    d = _llegeix(i)
    assert not (d.text_tachelhit or "").strip(), "cap màquina no escriu el text del parlant"
    assert (d.text_tachelhit_suggested or "").strip()

    cos = _demana(i, cap)
    #: La procedència ha de ser visible: qui decideix ha de poder anar a mirar la pàgina.
    assert cos["esborranys"], cos
    assert "pàgina" in (cos["esborranys"][0]["font"] or "")


def test_quan_una_persona_ho_confirma_la_linia_passa_al_camp_del_parlant():
    """Ja no és una màquina qui diu que la gravació diu allò: ho ha dit algú escoltant-la."""
    i, cap = _prepara("admin_casa_si")
    r = client.post("/revisa/casa-amb-el-llibre",
                    json={"drill_id": i, "opcio": "tria",
                          "esborrany": "is tskrm ibrin i-Zinb d-Yamna?"}, headers=cap)
    assert r.status_code == 200, r.text
    d = _llegeix(i)
    assert d.text_tachelhit == "is tskrm ibrin i-Zinb d-Yamna?"
    #: La línia és en llatí, i el camp del llatí s'ha d'omplir sol perquè el transliterador
    #: pugui ensenyar el tifinag al seu lloc d'honor.
    assert d.text_tachelhit_latin == "is tskrm ibrin i-Zinb d-Yamna?"
    assert not (d.text_tachelhit_suggested or "")
    assert "casa-amb-el-llibre" not in (d.tag or "")


def test_si_diu_que_no_la_proposta_s_esborra_i_la_gravacio_es_queda():
    i, cap = _prepara("admin_casa_no")
    r = client.post("/revisa/casa-amb-el-llibre",
                    json={"drill_id": i, "opcio": "fora"}, headers=cap)
    assert r.status_code == 200, r.text
    d = _llegeix(i)
    assert d is not None, "la gravació és real: no s'esborra mai"
    assert not (d.text_tachelhit_suggested or ""), \
        "deixar-la seria deixar escrit que diu una cosa que no diu"
    assert not (d.esborranys or "")
    assert not (d.text_tachelhit or ""), "dir que no, no escriu res al camp del parlant"
    assert "casa-amb-el-llibre" not in (d.tag or "")


def test_no_ho_se_no_toca_res_i_la_frase_torna_un_altre_dia():
    i, cap = _prepara("admin_casa_potser")
    r = client.post("/revisa/casa-amb-el-llibre",
                    json={"drill_id": i, "opcio": "no-ho-se"}, headers=cap)
    assert r.status_code == 200, r.text
    d = _llegeix(i)
    assert (d.text_tachelhit_suggested or "").strip(), "el que no se sap no es decideix"
    assert "casa-amb-el-llibre" in (d.tag or ""), "ha de tornar a sortir un altre dia"


def test_confirmar_sense_linia_no_escriu_un_camp_buit():
    """Una crida sense text no ha de poder buidar el camp del parlant."""
    i, cap = _prepara("admin_casa_buit")
    _posa(i, text_tachelhit_suggested=None, esborranys=None)
    r = client.post("/revisa/casa-amb-el-llibre",
                    json={"drill_id": i, "opcio": "tria"}, headers=cap)
    assert r.status_code == 400, r.text
    d = _llegeix(i)
    assert not (d.text_tachelhit or "")


def test_la_pila_compta_i_s_encongeix():
    """El compte de l'etiqueta ÉS la barra de progrés."""
    i, cap = _prepara("admin_casa_compte")
    abans = next(p["queden"] for p in client.get("/revisa", headers=cap).json()["piles"]
                 if p["id"] == "casa-amb-el-llibre")
    assert abans >= 1
    client.post("/revisa/casa-amb-el-llibre",
                json={"drill_id": i, "opcio": "fora"}, headers=cap)
    despres = next(p["queden"] for p in client.get("/revisa", headers=cap).json()["piles"]
                   if p["id"] == "casa-amb-el-llibre")
    assert despres == abans - 1
