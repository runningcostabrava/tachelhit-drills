"""L'índex del Mètode no pot tornar a llegir la biblioteca deu vegades (#552).

L'1-11-2026 l'amo va obrir el capítol 3 i va llegir «el servidor s'està despertant». No s'estava
despertant: `GET /method/` trigava **disset segons** i el capítol vint, mesurat a producció.

El motiu: `sentences_for` demanava totes les frases amb text i significat —la mateixa consulta
per als deu capítols— i filtrava després en Python. Mentre la biblioteca era petita no es
notava; en omplir aquella mateixa nit el significat en català de 5.522 frases, les files que
torna la consulta gairebé es van doblar, perquè el filtre demana `text_catalan` no buit.

Dues coses, doncs, que aquesta prova guarda:
  · la consulta es fa UNA vegada per petició i es passa als deu capítols;
  · l'índex té cau, i mentre no es mogui res no la torna a fer.
"""


def test_l_index_demana_la_biblioteca_una_sola_vegada(monkeypatch):
    from test_api import client
    import main
    import method as method_mod

    vegades = {"n": 0}
    de_debo = method_mod.candidates

    def comptant(db):
        vegades["n"] += 1
        return de_debo(db)

    monkeypatch.setattr(method_mod, "candidates", comptant)
    main._INDEX_CACHE.clear()

    r = client.get("/method/")
    assert r.status_code == 200
    capitols = r.json()["chapters"]
    assert len(capitols) >= 10, "els deu capítols hi han de ser"
    assert vegades["n"] == 1, (
        f"la biblioteca s'ha llegit {vegades['n']} vegades per a {len(capitols)} capítols: "
        "és el que feia que el Mètode trigués disset segons")


def test_l_index_no_la_torna_a_demanar_si_no_s_ha_mogut_res(monkeypatch):
    from test_api import client
    import main
    import method as method_mod

    main._INDEX_CACHE.clear()
    client.get("/method/")          # la primera, que omple el cau

    vegades = {"n": 0}
    de_debo = method_mod.candidates

    def comptant(db):
        vegades["n"] += 1
        return de_debo(db)

    monkeypatch.setattr(method_mod, "candidates", comptant)
    r = client.get("/method/")
    assert r.status_code == 200
    assert vegades["n"] == 0, "sense cap canvi, l'índex ha de sortir del cau"


def test_una_frase_nova_refa_l_index():
    from test_api import client, register
    import main

    main._INDEX_CACHE.clear()
    abans = client.get("/method/").json()["chapters"]
    hdr = {"X-User-Token": register("qui_mou_la_biblioteca")}
    fet = client.post("/drills/", headers=hdr,
                      json={"text_tachelhit": "aɣrum", "text_catalan": "pa"})
    assert fet.status_code == 200
    despres = client.get("/method/").json()["chapters"]
    # No es compara el contingut —potser la frase no toca cap capítol— sinó que el cau no
    # s'ha quedat clavat: la marca ha canviat i s'ha tornat a calcular.
    assert len(abans) == len(despres)
    assert main._INDEX_CACHE["method"][0] != ()


def test_sentences_for_accepta_les_candidates_ja_demanades():
    from test_api import client  # noqa: F401  (munta la base de proves)
    import main
    import method as method_mod

    db = main.SessionLocal()
    try:
        totes = method_mod.candidates(db)
        slug = method_mod.index()[0]["slug"]
        amb = method_mod.sentences_for(db, slug, totes)
        sense = method_mod.sentences_for(db, slug)
        assert [d.id for d in amb] == [d.id for d in sense], (
            "passar-li les candidates no pot canviar el que tria")
    finally:
        db.close()
