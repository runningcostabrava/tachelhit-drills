"""Un text amazic que l'app mostra sense veu, si la biblioteca ja el té gravat, ha de sonar (#504)."""
from test_api import client
import main
from models import Drill


def _drill(text, audio="https://res.cloudinary.com/x/a.mp3"):
    db = main.SessionLocal()
    try:
        d = Drill(text_tachelhit=text, text_catalan="prova 504", audio_url=audio, speaker="Halima")
        db.add(d)
        db.commit()
        return d.id
    finally:
        db.close()


def _esborra(*ids):
    db = main.SessionLocal()
    try:
        db.query(Drill).filter(Drill.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_troba_la_veu_per_la_frase_i_per_cada_variant():
    """«I cg? / I ck?»: la veu diu les dues, i una pantalla que mostri «I ck?» l'ha de trobar."""
    a = _drill("Zzyq cg? / Zzyq ck?")
    b = _drill("tamzzyqt n wakal", audio=None)
    try:
        r = client.get("/library/voiced", params=[("form", "zzyq ck"), ("form", "ZZYQ CG?"),
                                                  ("form", "tamzzyqt n wakal"), ("form", "res de res")])
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["zzyq ck"]["drill_id"] == a
        assert v["ZZYQ CG?"]["drill_id"] == a, "majúscules i puntuació no compten"
        assert v["zzyq ck"]["speaker"] == "Halima", "la veu va amb qui la diu"
        assert v["tamzzyqt n wakal"] is None, "una frase sense veu no és cap veu"
        assert v["res de res"] is None
    finally:
        _esborra(a, b)


def test_una_paraula_dins_d_una_frase_no_passa_per_la_paraula_sola():
    a = _drill("zzyqlam d ufus n tmazirt")
    try:
        assert client.get("/library/voiced", params={"form": "zzyqlam"}).json()["zzyqlam"] is None
    finally:
        _esborra(a)
