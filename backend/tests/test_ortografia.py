"""La nota que diu que «rix» i «riɣ» són la mateixa paraula (#364).

Es comprova que arriba als dos llocs on algú hi topa, i que no es converteix en un text qualsevol
que algú pugui buidar sense adonar-se'n: si un dia hi falten les parelles, la nota deixa de ser
una prova i passa a ser una afirmació.
"""
import ortografia


def test_la_nota_porta_les_parelles_que_la_demostren():
    n = ortografia.nota()
    assert n["titol"] and len(n["cos"]) >= 3
    assert len(n["parelles"]) >= 4, "sense parelles això és una afirmació, no una prova"
    for p in n["parelles"]:
        assert "x" in p["x"], "la forma amb x ha de portar una x: %r" % p
        assert "ɣ" in p["g"], "la forma amb ɣ ha de portar una ɣ: %r" % p
        # La mateixa paraula escrita de dues maneres: canviant la lletra, han de coincidir.
        assert p["x"].replace("x", "ɣ") == p["g"], "%r i %r no són la mateixa paraula" % (p["x"], p["g"])
        assert p["x_n"] >= 1 and p["g_n"] >= 1, "una parella sense compte no demostra res"
        assert p["ca"], "cada parella ha de dir què vol dir"


def test_la_nota_diu_de_quantes_frases_parla():
    n = ortografia.nota()
    assert 0 < n["quantes"] < n["de_quantes"], "el compte ha de ser una part del total"


def test_la_unitat_dels_sons_i_el_capitol_dels_sons_la_porten():
    """Als dos llocs, i no a tots: a cada frase seria soroll."""
    from test_api import client
    u = client.get("/grammar/%s" % __import__("grammar").SOUNDS_UNIT)
    assert u.status_code == 200, u.text
    assert u.json().get("ortografia"), "la unitat dels sons no porta la nota"
    altra = client.get("/grammar/pronoms-personals")
    if altra.status_code == 200:
        assert not altra.json().get("ortografia"), "només la unitat dels sons l'ha de portar"
