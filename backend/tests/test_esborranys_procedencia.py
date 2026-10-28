"""Els esborranys que es revisen han de dir d'on surten.

Una gravació sense text escrit es pot haver llegit per tres models independents. El que fa que
valgui la pena mirar-la no és el text —qualsevol màquina en treu un— sinó que **tres hi
coincideixin**. Si la pantalla ensenya un text sense pare, qui decideix ho fa a cegues.
"""
import json

from test_api import client


def _fes_frase(catala):
    r = client.post("/drills/", json={"text_catalan": catala})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _com_admin():
    """Les piles de revisar són només per a qui administra la biblioteca."""
    import main
    from models import User as UserModel

    u = client.post("/users/register", json={"username": "admin_esborranys"}).json()
    with main.SessionLocal() as db:
        row = db.query(UserModel).filter(UserModel.username == "admin_esborranys").first()
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


def test_els_esborranys_surten_ordenats_i_amb_el_seu_model():
    """Tres lectures de la mateixa gravació: la que més acord té, primera."""
    import revisa

    i = _fes_frase("se'n va anar al bosc")
    _posa(i, tag="per-escriure", esborranys=json.dumps([
        {"text": "iddu s teggʷmma", "model": "wav2vec2-berber", "acord": 0.41},
        {"text": "ⵉⴷⴷⴰ ⵙ ⵜⴰⴳⴰⵏⵜ", "model": "nemo-zgh", "acord": 0.89},
        {"text": "idda s tagant", "model": "nostre", "acord": 0.89},
    ], ensure_ascii=False))

    r = client.get("/revisa/per-escriure", headers=_com_admin())
    assert r.status_code == 200, r.text
    fora = r.json()
    assert fora["drill"] and fora["drill"]["id"] == i, fora

    esb = fora["esborranys"]
    assert len(esb) == 3, esb
    # El de més acord, primer: és el que té més números de ser bo.
    assert esb[0]["acord"] == 0.89
    # I cada un diu de quin model surt: sense això no es pot saber si coincideixen tres de debò.
    assert {e["model"] for e in esb} == {"wav2vec2-berber", "nemo-zgh", "nostre"}

    # I la funció que els llegeix fa el mateix fora de l'API.
    import main
    from models import Drill as DrillModel
    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == i).first()
        assert [e["model"] for e in revisa.esborranys_de(d)][0] in ("nemo-zgh", "nostre")


def test_una_frase_vella_segueix_ensenyant_el_seu_esborrany():
    """Les frases que ja hi havia només tenen `text_tachelhit_suggested` i cap procedència.

    La pantalla ha de seguir funcionant amb elles: si no, afegir la columna nova buidaria la
    pila de tot el que ja hi era.
    """
    import main
    import revisa
    from models import Drill as DrillModel

    i = _fes_frase("una frase de les antigues")
    _posa(i, tag="per-escriure", text_tachelhit_suggested="ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ", esborranys=None)

    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == i).first()
        esb = revisa.esborranys_de(d)
    assert len(esb) == 1
    assert esb[0]["text"] == "ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ"
    assert esb[0]["model"] is None       # no sabem de qui és, i es diu així: no s'inventa


def test_un_json_trencat_no_tomba_la_pantalla():
    """Un esborrany mal desat no pot deixar sense revisar tota la pila."""
    import main
    import revisa
    from models import Drill as DrillModel

    i = _fes_frase("amb els esborranys trencats")
    _posa(i, tag="per-escriure", esborranys="{aixo no es JSON", text_tachelhit_suggested="ⵜⴰⵏⵎⵎⵉⵔⵜ")

    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == i).first()
        esb = revisa.esborranys_de(d)
    # Es cau cap enrere al que sempre hi ha hagut, en comptes de petar.
    assert [e["text"] for e in esb] == ["ⵜⴰⵏⵎⵎⵉⵔⵜ"]
