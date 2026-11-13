"""El catàleg sencer es serveix a raigs, i diu exactament el mateix (#566).

El 2-11-2026 producció tornava 502 a **tot** —`/health`, `/version`, una sola frase—: no anava
lenta, s'estava reiniciant. Quan va tornar, `/drills/` va servir **14,1 MB** de 12.195 frases en
una sola resposta, en una instància de 512 MB. Catorze megues no són el problema; el problema és
que per fer-les calia tenir-ho tot dues vegades —els objectes i el JSON— i que això creix sol:
cada lectura de màquina i cada traducció que s'hi desa fa la resposta més gran.

La part delicada d'això no és que vagi a trossos. És que **el que surt sigui idèntic**: un client
d'abans no s'ha d'adonar de res. Per això la prova que manda aquí no mira la forma, compara la
resposta sencera amb la que surt de demanar-la paginada.
"""
import json

from test_api import client


def _fes(n, **camps):
    fets = []
    for i in range(n):
        cos = {"text_catalan": f"frase de raigs {i}", **camps}
        r = client.post("/drills/", json=cos)
        assert r.status_code == 200, r.text
        fets.append(r.json()["id"])
    return fets


def test_el_sencer_diu_el_mateix_que_les_pagines():
    """La prova que ha de caure si la serialització a raigs es desvia un sol camp."""
    _fes(7, tag="raigs-iguals")

    sencer = client.get("/drills/")
    assert sencer.status_code == 200, sencer.text
    de_cop = sencer.json()

    # El mateix, demanat de 3 en 3 (el camí que el davant fa servir des del #489).
    paginat = []
    offset = 0
    while True:
        r = client.get("/drills/", params={"limit": 3, "offset": offset})
        assert r.status_code == 200, r.text
        pagina = r.json()
        if not pagina:
            break
        paginat += pagina
        offset += 3

    assert len(de_cop) == len(paginat) > 7
    # Camp a camp, i en el mateix ordre: això és el contracte.
    assert de_cop == paginat
    assert [d["id"] for d in de_cop] == [d["id"] for d in paginat]


def test_el_sencer_es_un_json_ben_format_i_complet():
    """Un raig que s'oblidés una coma o el claudàtor de tancar donaria un 200 il·legible."""
    ids = _fes(4, tag="raigs-format")

    r = client.get("/drills/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    cos = r.text
    assert cos.startswith("[") and cos.endswith("]")
    llista = json.loads(cos)
    assert isinstance(llista, list)
    for i in ids:
        assert any(d["id"] == i for d in llista), i


def test_el_compte_total_hi_es_igualment():
    """`X-Total-Count` és el que fa que el davant sàpiga quan ha acabat de paginar."""
    _fes(3, tag="raigs-compte")

    r = client.get("/drills/")
    total = int(r.headers["X-Total-Count"])
    assert total == len(r.json())

    # I amb filtre, el compte és el del filtre, no el de la biblioteca.
    r = client.get("/drills/", params={"tag": "raigs-compte"})
    assert int(r.headers["X-Total-Count"]) == len(r.json()) == 3


def test_els_filtres_valen_igual_servint_a_raigs():
    """El filtre es munta dins del generador, amb una sessió nova: si un dia se n'oblida la
    meitat, aquesta prova cau."""
    _fes(2, tag="raigs-filtre-a", author="Qui firma A")
    _fes(3, tag="raigs-filtre-b", author="Qui firma B")

    per_etiqueta = client.get("/drills/", params={"tag": "raigs-filtre-b"}).json()
    assert len(per_etiqueta) == 3
    assert all("raigs-filtre-b" in (d.get("tag") or "") for d in per_etiqueta)

    per_autor = client.get("/drills/", params={"author": "Qui firma A"}).json()
    assert len(per_autor) == 2

    cercat = client.get("/drills/", params={"search": "raigs-filtre-a"}).json()
    assert len(cercat) == 2          # casa per l'etiqueta, que també es cerca

    totes = client.get("/drills/").json()
    assert len(totes) > 5


def test_un_since_mal_escrit_dona_400_i_no_mitja_resposta():
    """El 400 s'ha de donar amb la resposta encara sense començar. Si es donés a mig raig, el
    client rebria un 200 amb un JSON tallat pel mig."""
    r = client.get("/drills/", params={"since": "ahir a la tarda"})
    assert r.status_code == 400, r.text
    assert "ISO-8601" in r.json()["detail"]


def test_de_debo_va_a_trossos(monkeypatch):
    """La prova que guarda el PER QUÈ, no el resultat.

    Tot això es podria «simplificar» un dia a un `query.all()` dins del generador i la resposta
    seria idèntica —totes les altres proves passarien— mentre la memòria torna a ser la d'abans,
    que és l'única cosa que veníem a arreglar. Això compta les consultes: si en fa una de sola,
    cau.

    Mesurat amb 12.200 frases de la mida de les de debò: el pic del servidor passa de 146,7 MB
    a 1,9 MB servint els mateixos 13,3 MB de resposta.
    """
    import main
    from sqlalchemy import event

    _fes(6, tag="raigs-trossos")
    monkeypatch.setattr(main, "LOT_DRILLS", 2)

    consultes = []

    def apunta(conn, cursor, statement, params, context, executemany):
        if "FROM drills" in statement and statement.lstrip().upper().startswith("SELECT"):
            consultes.append(statement)

    event.listen(main.engine, "before_cursor_execute", apunta)
    try:
        r = client.get("/drills/", params={"tag": "raigs-trossos"})
        assert r.status_code == 200
        assert len(r.json()) == 6
    finally:
        event.remove(main.engine, "before_cursor_execute", apunta)

    # Un compte i quatre voltes de dues (la quarta torna buida o curta): mai una sola consulta
    # que es porti les sis files de cop.
    assert len(consultes) >= 4, consultes
    assert any("LIMIT" in c.upper() for c in consultes), consultes


def test_una_fila_que_no_valida_no_s_endu_la_pantalla():
    """El rescat de sempre, que ara el fa servir el camí a raigs també: hi va haver files amb
    URL de mitjans que el validador no acceptava, i perdre tota la biblioteca per una fila és
    pitjor que ensenyar-la amb menys camps."""
    import main
    from models import Drill as DrillModel

    i = _fes(1, tag="raigs-rescat")[0]
    with main.SessionLocal() as db:
        d = db.query(DrillModel).filter(DrillModel.id == i).first()
        # El que el validador mira: una URL de mitjans impossible.
        d.audio_url = "no és cap URL"
        db.commit()

    r = client.get("/drills/")
    assert r.status_code == 200, r.text
    assert any(d["id"] == i for d in r.json())
