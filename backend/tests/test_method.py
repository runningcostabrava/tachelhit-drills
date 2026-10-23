"""El Mètode: el catàleg dels deu capítols, i com s'omplen amb la nostra biblioteca.

El que aquestes proves guarden no és que el curs sigui bo —això ho diu una persona— sinó que no
hi entri res que no hi hagi d'entrar, i que el que un capítol diu que té sigui el que té.
"""
import method
from test_api import client


def test_el_cataleg_nomena_unitats_i_temes_que_existeixen():
    """Un slug mal escrit aquí no peta res: el capítol surt buit, i això es llegeix com «d'això
    encara no en tenim» quan el que passa és que el tema es diu d'una altra manera. Per això el
    catàleg es comprova sol, i per això la comprovació és una prova."""
    assert method.check() == []
    assert len(method.CHAPTERS) == 10
    assert [c["n"] for c in method.CHAPTERS] == list(range(1, 11))
    assert len(set(method.SLUGS)) == 10, "dos capítols amb el mateix nom curt"
    for c in method.CHAPTERS:
        assert c["functions"], f"el capítol {c['n']} no diu què en sabràs fer"
        assert c["title"] and c["about"]


def test_un_capitol_s_omple_amb_la_nostra_biblioteca_i_deixa_fora_el_que_toca():
    """Un capítol no porta ni una frase del manual: porta les NOSTRES que fan el que demana.

    El que queda fora és el que docs/SCOPE.md diu que queda fora: una llengua exclosa. El recull
    de Beni Mellal («private») SÍ que hi entra — l'amo en té permís, i aquella etiqueta protegeix
    la redistribució, no l'ensenyament (decisió de 23-10-2026).

    I l'ordre importa: les frases de la Halima i d'en Driss van davant. Són 69 de 3.390, i sense
    aquesta regla no es veurien mai entre les dues mil del recull.
    """
    hdr = {"X-User-Token": __import__("test_api").register("method_filler")}
    mine = client.post("/drills/", headers=hdr, json={
        "text_catalan": "bon dia", "text_tachelhit": "sbaḥ lxir", "grammar": "formules",
        "grammar_source": "owner", "topics": "salutacions", "topics_source": "owner",
        "author": "Halima",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/bd.mp3"}).json()
    from_deck = client.post("/drills/", headers=hdr, json={
        "text_catalan": "bona tarda", "text_tachelhit": "mslxir", "grammar": "formules",
        "grammar_source": "owner", "tag": "benimellal-anki, private",
        "author": "Anki: Tamazight - Beni Mellal Morocco",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/bt.mp3"}).json()
    foreign = client.post("/drills/", headers=hdr, json={
        "text_catalan": "hola", "text_tachelhit": "dia duit", "grammar": "formules",
        "grammar_source": "owner", "tag": "irish"}).json()

    r = client.get("/method/salutacions").json()
    here = {d["id"] for s in r["sections"] for d in s["sentences"]} | {d["id"] for d in r["also"]}
    assert mine["id"] in here
    assert from_deck["id"] in here, "el recull hi entra: n'hi ha permís"
    assert foreign["id"] not in here, "una llengua exclosa, no"

    # i les nostres veus davant: la de la Halima abans que la del recull
    order = [d["id"] for s in r["sections"] if s["slug"] == "formules" for d in s["sentences"]]
    assert order.index(mine["id"]) < order.index(from_deck["id"]),         "primer qui el projecte coneix"

    assert r["n"] == 2 and r["name"] == "Timinsiwin"
    assert [s["slug"] for s in r["sections"]] == ["formules", "pronoms-personals"]
    assert r["functions"], "ha de dir què en sabràs fer"


def test_el_capitol_diu_sempre_d_on_surt():
    """El Mètode és una adaptació d'un manual publicat (ADR 0004). La citació no és una nota a
    peu de la pàgina de crèdits: viatja amb cada capítol, de manera que no es pot ensenyar un
    capítol sense ensenyar d'on surt.

    I el que es llegeix és «Basat en…» i res més: la targeta d'un capítol diu d'on ve el
    material, no quins permisos tenim. Això és del registre intern, no de la pantalla."""
    r = client.get("/method/la-botiga").json()
    src = r["source"]
    assert "El Mountassir" in src["author"] and src["year"] == 2009
    assert src["based_on"] == "Basat en"
    assert "permís" not in " ".join(str(v) for v in src.values()).lower()
    assert "veus" in src["did_not_take"], "el que no ve del llibre són les veus"

    index = client.get("/method/").json()
    assert len(index["chapters"]) == 10 and index["source"]["author"] == src["author"]


def test_el_text_d_un_capitol_es_desa_a_la_base_de_dades_i_el_corregeix_qui_administra():
    """El text d'un capítol —l'explicació, el diàleg, el vocabulari— viu a la base de dades i no
    al repositori.

    Dues raons. El repositori és públic, i una traducció capítol per capítol penjada allà és una
    altra cosa que fer-la servir a l'app. I perquè així es corregeix des de la mateixa app: qui
    administra pot arreglar una frase sense desplegar res, que és la meitat de l'issue #238.

    Un capítol sense text no és un error: ensenya igualment les frases de la biblioteca."""
    import main
    from test_api import client, register, as_stranger

    before = client.get("/method/el-viatge").json()
    assert before["content"] is None, "un capítol sense escriure no en té"
    assert before["sections"], "i tot i així ensenya les frases que li toquen"

    body = {
        "intro": "Anar d'un lloc a un altre.",
        "sections": [{"id": "s", "title": "Com s'hi va",
                      "examples": [{"shi": "s-uxam", "ca": "cap a casa"}]}],
        "vocabulary": [{"shi": "amuddu", "ca": "viatge"}],
    }

    # no és de qualsevol: el text d'un capítol el canvia qui administra
    with as_stranger():
        assert client.put("/method/el-viatge/content", json=body).status_code == 401
    plain = {"X-User-Token": register("not_an_admin")}
    assert client.put("/method/el-viatge/content", headers=plain, json=body).status_code == 403

    boss = {"X-User-Token": main._make_admin_token()} if hasattr(main, "_make_admin_token") else None
    if boss is None:
        db = main.SessionLocal()
        try:
            me = client.get("/users/me", headers=plain).json()
            row = db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first()
            row.is_admin = True
            db.commit()
        finally:
            db.close()
        boss = plain

    ok = client.put("/method/el-viatge/content", headers=boss, json=body)
    assert ok.status_code == 200, ok.text
    assert ok.json()["sections"] == 1

    back = client.get("/method/el-viatge").json()
    assert back["content"]["intro"] == "Anar d'un lloc a un altre."
    assert back["content"]["sections"][0]["examples"][0]["shi"] == "s-uxam"
    assert back["content"]["updated_by"], "qui l'ha tocat queda escrit"
    assert back["sections"], "i les frases de la biblioteca segueixen on eren"

    # l'índex diu quins capítols ja s'han escrit
    index = {c["slug"]: c for c in client.get("/method/").json()["chapters"]}
    assert index["el-viatge"]["written"] is True
    assert index["els-convidats"]["written"] is False

    assert client.put("/method/no-existeix/content", headers=boss, json=body).status_code == 404


def test_cada_seccio_ensenya_les_nostres_frases_al_costat_del_que_explica():
    """El Mètode no és el llibre traduït amb un munt de frases nostres al final.

    Cada secció explica una cosa i tot seguit ensenya com la diu la gent que coneixem: amb la
    seva veu, la seva imatge, el seu poble i la seva varietat. La secció diu de quina unitat de
    gramàtica va i d'allà surten les seves frases; les que es poden ESCOLTAR i MIRAR van davant,
    perquè una targeta amb veu i imatge ensenya més que una línia de text.

    I una línia del llibre encara no és una frase nostra: ho esdevé quan algú la grava.

    Hi entra la frase que DIU el que la secció ensenya, no la que és de la mateixa unitat de
    gramàtica: la unitat `noms-genere-nombre` és certa de 683 frases, i omplir-hi amb això feia
    que «Pesos i mesures» ensenyés «Oriol està molt enfadat»."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("chapter_filler")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    rich = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la clau", "text_tachelhit": "tasarut", "author": "Halima",
        "grammar": "clitics-objecte", "grammar_source": "owner",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/k.mp3",
        "image_url": "https://res.cloudinary.com/x/image/upload/v1/k.jpg"}).json()
    mute = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la porta", "text_tachelhit": "fkiγ-as tiflut",
        "grammar": "clitics-objecte", "grammar_source": "owner"}).json()
    # de la mateixa unitat, i no diu res del que la secció ensenya: no hi ha de sortir
    apart = client.post("/drills/", headers=hdr, json={
        "text_catalan": "Oriol està molt enfadat", "text_tachelhit": "luryl yaġht ljnn",
        "grammar": "clitics-objecte", "grammar_source": "owner"}).json()

    client.put("/method/la-botiga/content", headers=hdr, json={
        "intro": "A la botiga.",
        "sections": [{"id": "datius", "unit": "clitics-objecte", "title": "Els datius",
                      "examples": [{"shi": "fkiγ-as tasarut", "ca": "Li he donat la clau"}]}],
    })

    sec = client.get("/method/la-botiga").json()["content"]["sections"][0]
    ours = [d["id"] for d in sec["ours_drills"]]
    assert rich["id"] in ours, "la frase de la secció hi ha de ser"
    assert ours.index(rich["id"]) < (ours.index(mute["id"]) if mute["id"] in ours else 99), \
        "amb veu i imatge, davant"
    assert sec["ours_total"] >= 2
    assert apart["id"] not in ours, "la unitat sola no fa entrar una frase que no ho ensenya"
    assert all(d.get("why") for d in sec["ours_drills"]), "cada frase diu què hi fa"

    # i la línia del llibre: encara no és nostra, i gravar-la la converteix
    assert "drill_id" not in sec["examples"][0]
    made = client.post("/method/la-botiga/line", headers=hdr,
                       json={"kind": "example", "section": "datius", "index": 0})
    assert made.status_code == 200, made.text
    assert made.json()["created"] is True
    born = made.json()["drill"]
    assert born["text_tachelhit"] == "fkiγ-as tasarut"
    assert "metode-la-botiga" in (born.get("tag") or ""), "diu d'on surt"
    assert born.get("voice_wanted") is True, "neix demanant una veu"
    # i NO es queda etiquetada amb la gramàtica ni el tema del capítol: una línia del llibre no
    # és un exemple de les quatre unitats del capítol, i amb el segell «owner» entrava a les
    # seves lliçons i feia que el capítol es certifiqués a si mateix (auditor dialectòleg)
    assert not born.get("grammar") and not born.get("topics")

    # la segona vegada no se'n fa una altra: s'hi afegeix una veu
    again = client.post("/method/la-botiga/line", headers=hdr,
                        json={"kind": "example", "section": "datius", "index": 0}).json()
    assert again["created"] is False and again["drill_id"] == born["id"]

    back = client.get("/method/la-botiga").json()["content"]["sections"][0]
    assert back["examples"][0]["drill_id"] == born["id"], "el capítol se'n recorda"

    # i una línia que no hi és, no
    assert client.post("/method/la-botiga/line", headers=hdr,
                       json={"kind": "example", "section": "datius", "index": 99}).status_code == 400


def test_el_que_falta_es_mesura_amb_la_veu_no_amb_el_text():
    """Una secció amb vint frases i cap gravada no ensenya a dir res: ensenya a llegir-les, que
    no és el que fa un mètode. Per això «a punt» es compta amb les que es poden escoltar, i una
    unitat que cap frase de la biblioteca no porta es diu que no és enlloc en comptes de
    comptar com un forat d'aquest capítol."""
    r = client.get("/method/sons").json()
    thin = {t["slug"]: t for t in r["missing"]["thin"]}
    assert "sons-i-escriptura" in thin, "la fonètica no s'etiqueta a cap frase"
    assert thin["sons-i-escriptura"]["nowhere"] is True
    assert r["sections_ready"] <= r["sections_total"]

    assert client.get("/method/no-existeix").status_code == 404


def test_cada_linia_porta_la_seva_tifinagh_i_el_seu_paraula_per_paraula():
    """Dues coses que l'amo ha demanat i que valen per a tot el Mètode.

    La TIFINAGH: el capítol s'escriu en llatí perquè així és el manual i així escriu qui grava,
    però l'escriptura de la llengua va amb la llengua. No es desa: es calcula en servir, i per
    això millora sola quan millora el transliterador.

    El PARAULA PER PARAULA: igual que al curs de gramàtica. Una frase que s'ensenya i no es pot
    desmuntar és una frase que només es pot repetir. Aquest sí que s'escriu amb el capítol,
    perquè el significat de cada tros no es pot endevinar."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("tif_filler")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    client.put("/method/la-botiga/content", headers=hdr, json={
        "sections": [{"id": "dar", "title": "dar", "examples": [
            {"shi": "dar ugzzar", "ca": "a la carnisseria",
             "gloss": [{"shi": "dar", "ca": "a cal"}, {"shi": "ugzzar", "ca": "carnisser"}]}]}],
        "dialogue": {"title": "A la botiga", "turns": [{"who": "la dona", "shi": "is dar-k tudit?",
                                                        "ca": "Que tens oli d'argan?"}]},
        "vocabulary": [{"shi": "aγrum", "ca": "pa"}],
    })

    body = client.get("/method/la-botiga").json()["content"]
    line = body["sections"][0]["examples"][0]
    assert line["tif"] and line["tif"] != line["shi"], "la línia porta la seva tifinagh"
    assert [g["ca"] for g in line["gloss"]] == ["a cal", "carnisser"], "i el paraula per paraula"
    assert line["gloss"][0].get("tif"), "cada paraula també la porta"
    assert body["dialogue"]["turns"][0]["tif"], "les rèpliques del diàleg també"
    assert body["vocabulary"][0]["tif"], "i les paraules"


def test_el_que_el_servidor_calcula_no_es_desa_amb_el_capitol():
    """Qui administra corregeix una línia i el navegador torna el capítol tal com el tenia a la
    pantalla: amb la tifinagh i amb les frases nostres repartides per dins. Desar-ho congelaria
    el capítol amb les frases d'aquell dia, i la tifinagh deixaria de millorar quan millora el
    transliterador. El que el servidor posa en servir, el servidor l'ha de treure en desar."""
    import json

    import main
    import method as method_mod
    from models import MethodChapter
    from test_api import client, register

    hdr = {"X-User-Token": register("round_tripper")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    client.put("/method/la-botiga/content", headers=hdr, json={
        "sections": [{"id": "dar", "title": "dar", "examples": [{"shi": "dar ugzzar", "ca": "a cal carnisser"}]}]})
    served = client.get("/method/la-botiga").json()["content"]
    assert served["sections"][0]["examples"][0]["tif"], "servit, porta la tifinagh"

    # i això mateix és el que el navegador torna en corregir una línia
    client.put("/method/la-botiga/content", headers=hdr, json=served)
    db = main.SessionLocal()
    try:
        stored = json.loads(db.query(MethodChapter).filter(MethodChapter.slug == "la-botiga").first().body)
    finally:
        db.close()
    sec = stored["sections"][0]
    assert "ours_drills" not in sec and "ours_total" not in sec, "les frases nostres no es desen"
    assert "tif" not in sec["examples"][0], "la tifinagh tampoc: es calcula"
    assert sec["examples"][0]["shi"] == "dar ugzzar", "i el que s'escriu, s'hi queda"
    assert method_mod.strip_computed({"a": [{"tif": 1, "shi": "x"}]}) == {"a": [{"shi": "x"}]}


def test_cada_capitol_pot_portar_el_seu_dibuix():
    """«I think some ilustrations and style would be nice here», va dir l'amo mirant la llista de
    capítols. Un dibuix diu de què va el capítol abans de llegir-ne una paraula.

    Els dibuixos viuen a `/artwork` i no al codi, perquè es puguin tornar a dibuixar sense
    desplegar res. Un capítol sense dibuix segueix sent un capítol: no se n'inventa cap."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_dibuixa_capitols")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    drawn = "https://res.cloudinary.com/du26ppvh0/image/upload/v1/tachelhit/app/capitol-la-botiga.webp"
    client.put("/artwork/method", headers=hdr, json={"covers": {"la-botiga": drawn}})

    chapters = {c["slug"]: c for c in client.get("/method/").json()["chapters"]}
    assert chapters["la-botiga"]["cover"] == drawn
    assert chapters["sons"]["cover"] is None, "el que no en té, no se n'inventa cap"
    assert client.get("/method/la-botiga").json()["cover"] == drawn


def test_una_seccio_es_pot_corregir_i_es_pot_proposar_un_canvi():
    """L'amo: «aquí hauria d'haver-hi un llapis per editar el text si sóc administrador, o
    suggerir el canvi per qualsevol altre usuari».

    Una secció és una explicació, i una explicació es pot millorar. Qui administra la canvia
    allà mateix; qui no, ho proposa, i va a la MATEIXA cua que les propostes del curs de
    gramàtica — amb el capítol al davant del nom, «metode:la-botiga», que és el que diu on
    s'escriu quan s'accepta."""
    import main
    from test_api import client, register

    boss = {"X-User-Token": register("qui_mana_al_metode")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=boss).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()
    client.put("/method/la-botiga/content", headers=boss, json={
        "sections": [{"id": "preu", "title": "mnckk a…: quant val?", "text": "Per preguntar el preu es fa servir skr."}]})

    # qualsevol que tingui nom pot proposar un canvi
    someone = {"X-User-Token": register("qui_hi_vol_dir_la_seva")}
    sent = client.post("/grammar/metode:la-botiga/proposals", headers=someone,
                       json={"step": 0, "text": "Aquí es diu mšta, no mnckk."})
    assert sent.status_code == 200, sent.text

    # qui administra les veu; qui les ha fetes, les seves
    assert len(client.get("/grammar/metode:la-botiga/proposals", headers=boss).json()) == 1
    assert len(client.get("/grammar/metode:la-botiga/proposals").json()) == 0

    # i acceptar-la escriu al capítol, no a cap lliçó de gramàtica
    pid = sent.json()["id"]
    assert client.post(f"/grammar/proposals/{pid}/decide", headers=boss, json={"accept": True}).status_code == 200
    body = client.get("/method/la-botiga").json()["content"]
    assert body["sections"][0]["text"] == "Aquí es diu mšta, no mnckk."

    # un capítol que no existeix, no
    assert client.post("/grammar/metode:no-existeix/proposals", headers=someone,
                       json={"step": 0, "text": "hola que tal"}).status_code == 404

def test_una_altra_manera_de_dir_ho_es_veu_amb_qui_la_diu():
    """L'amo: «si jo gravo i canvio el text, el sistema hauria de mostrar també l'altra versió de
    la mateixa frase amb la seva gravació, i hauria de mostrar l'autor i la zona».

    Ja es desava —la gravadora pregunta «com ho dius tu?»— i no es veia enlloc fora del
    reproductor. Una frase dita d'una altra manera no és una correcció de l'altra: són dues
    maneres, i totes dues porten el nom de qui la diu i el seu poble.

    I una gravació que escriu la MATEIXA frase no és cap altra manera: `ghur` i `ɣur` són la
    mateixa paraula escrita de dues maneres, i allò ja ho diu el reproductor."""
    import main
    from models import Recording
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_ho_diu_daltra_manera")}
    d = client.post("/drills/", headers=hdr, json={
        "text_catalan": "Que tens oli d'argan?", "text_tachelhit": "is dar-k tudit?",
        "grammar": "ser-tenir", "grammar_source": "owner"}).json()

    db = main.SessionLocal()
    try:
        db.add(Recording(drill_id=d["id"], audio_url="https://res.cloudinary.com/x/video/upload/v1/h.mp3",
                         text="is ɣur-k tudit?", speaker="Halima Akajji",
                         variety="Central Atlas", region="Aït Mraw (Boutharar, Azilal)"))
        db.add(Recording(drill_id=d["id"], audio_url="https://res.cloudinary.com/x/video/upload/v1/i.mp3",
                         text="is dark tudit?", speaker="Driss Akajji", region="Aït Mraw"))
        db.commit()
    finally:
        db.close()

    said = main.other_ways(main.SessionLocal())
    mine = said[d["id"]]
    assert len(mine) == 2
    assert [v["speaker"] for v in mine] == ["Halima Akajji", "Driss Akajji"]
    assert mine[0]["tif"], "l'altra manera també porta la seva tifinagh"
    assert mine[0]["region"], "i d'on és qui la diu"

    # la d'en Driss és la mateixa frase escrita d'una altra manera: no és cap altra manera de dir-ho
    assert main._another_way("is ɣur-k tudit?", "is dar-k tudit?") is True
    assert main._another_way("is dark tudit?", "is dar-k tudit?") is False
    assert main._another_way("", "is dar-k tudit?") is False


def test_el_capitol_es_pot_escoltar_i_les_paraules_porten_imatge():
    """L'amo: «recorda que haig de poder posar play a la lliçó».

    Un capítol és per escoltar-lo. Les línies que algú ja ha gravat porten la seva veu enganxada
    en servir el capítol, i per això es poden sentir una a una o totes seguides. I una paraula
    del vocabulari que la biblioteca ja té surt amb la seva imatge i la seva veu: una paraula amb
    la seva imatge s'aprèn d'una altra manera que una paraula dins d'una llista.

    El que no s'ha gravat no s'inventa: es queda com era, esperant el micròfon."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_escolta_el_capitol")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    # Una frase de la biblioteca que diu exactament una paraula del capítol, amb veu i imatge.
    # Res de menjar: el catàleg de temes el classificaria i es colaria a les llistes de pràctica
    # d'una altra prova, que comparteix aquesta base de dades (ens va passar: `[81, 13] == [81]`).
    word = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la porta", "text_tachelhit": "tiflut", "author": "Prova-veu",
        "grammar": "noms-genere-nombre", "grammar_source": "owner",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/porta.mp3",
        "image_url": "https://res.cloudinary.com/x/image/upload/v1/tachelhit/illustrations/porta.webp"}).json()

    client.put("/method/la-botiga/content", headers=hdr, json={
        "sections": [{"id": "dar", "title": "dar", "examples": [{"shi": "dar ugzzar", "ca": "a cal carnisser"}]}],
        "dialogue": {"title": "A la botiga", "turns": [{"who": "la dona", "shi": "is dar-k tudit?", "ca": "Que tens oli?"}]},
        "vocabulary": [{"shi": "tiflut", "ca": "la porta"}, {"shi": "zzaytun", "ca": "olives"}]})

    body = client.get("/method/la-botiga").json()["content"]
    porta, olives = body["vocabulary"]
    assert porta["audio_url"] and porta["image_url"], "la paraula que la biblioteca té surt amb veu i imatge"
    assert "/illustrations/" in porta["image_url"], "i només si és un dibuix nostre, no una foto buscada"
    assert porta["speaker"] == "Prova-veu", "i amb qui la diu"
    assert not olives.get("audio_url") and not olives.get("image_url"), "la que no hi és, es queda com era"

    # gravar una línia del diàleg la fa sonar al capítol
    made = client.post("/method/la-botiga/line", headers=hdr,
                       json={"kind": "turn", "index": 0}).json()
    db = main.SessionLocal()
    try:
        d = db.query(main.DrillModel).filter(main.DrillModel.id == made["drill_id"]).first()
        d.audio_url = "https://res.cloudinary.com/x/video/upload/v1/dialeg.mp3"
        d.speaker = "Driss"
        db.commit()
    finally:
        db.close()
    turn = client.get("/method/la-botiga").json()["content"]["dialogue"]["turns"][0]
    assert turn["audio_url"].endswith("dialeg.mp3") and turn["speaker"] == "Driss"

    # i res d'això es desa: es calcula en servir, com la tifinagh
    client.put("/method/la-botiga/content", headers=hdr, json=client.get("/method/la-botiga").json()["content"])
    import json

    from models import MethodChapter
    db = main.SessionLocal()
    try:
        stored = json.loads(db.query(MethodChapter).filter(MethodChapter.slug == "la-botiga").first().body)
    finally:
        db.close()
    assert "audio_url" not in stored["dialogue"]["turns"][0]
    assert "image_url" not in stored["vocabulary"][0]

    # I es recull el que ha embrutat. Aquestes proves comparteixen UNA base de dades, i una frase
    # amb veu i imatge que es queda per aquí entra a les llistes de pràctica d'una altra prova i
    # la fa caure (ens va passar: `[14, 13] == [13]`).
    for drill_id in (word["id"], made["drill_id"]):
        client.delete(f"/drills/{drill_id}", headers=hdr)


def test_el_capitol_servit_es_guarda_fet_fins_que_alguna_cosa_es_mou():
    """Servir un capítol vol dir llegir les frases que hi poden anar i puntuar-les secció per
    secció: a producció, deu segons cada vegada que algú l'obre. I entre una visita i la següent
    no canvia res si no ha canviat ni el text del capítol ni la biblioteca.

    Així que es guarda fet. El que el torna a fer és que es mogui una de les dues coses: una
    frase nova o tocada, o el capítol reescrit. Res de temps: una frase gravada ara s'ha de
    veure ara."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_mira_dos_cops")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()
    client.put("/method/la-botiga/content", headers=hdr, json={
        "sections": [{"id": "dar", "title": "dar", "examples": [{"shi": "dar ugzzar", "ca": "a cal carnisser"}]}]})

    first = client.get("/method/la-botiga").json()
    assert client.get("/method/la-botiga").json() == first, "sense tocar res, el mateix"

    # una frase nova a la biblioteca i el capítol es torna a fer
    made = client.post("/drills/", headers=hdr, json={
        "text_catalan": "a cal fuster", "text_tachelhit": "dar unjjar",
        "grammar": "clitics-objecte", "grammar_source": "owner"}).json()
    assert client.get("/method/la-botiga").json()["sentences"] != first["sentences"]

    # i tocar el text del capítol també
    before = client.get("/method/la-botiga").json()
    client.put("/method/la-botiga/content", headers=hdr, json={
        "sections": [{"id": "dar", "title": "dar: a cal", "examples": [{"shi": "dar ugzzar", "ca": "a cal carnisser"}]}]})
    assert client.get("/method/la-botiga").json()["content"]["sections"][0]["title"] != before["content"]["sections"][0]["title"]

    client.delete(f"/drills/{made['id']}", headers=hdr)


def test_corregir_el_capitol_no_desvincula_les_veus():
    """Una línia del capítol es torna una frase de la biblioteca quan algú la grava, i el capítol
    se'n recorda amb un `drill_id`. Qui corregeix el text puja el capítol tal com l'escriu, sense
    aquells números — i si no es recuperessin, cada correcció desvincularia totes les veus: la
    gravació seguiria existint i la línia tornaria a dir «grava-la», com si ningú no l'hagués
    dita mai.

    Ho va trobar un auditor comparant dues lectures del capítol 4 amb cinc hores de diferència:
    l'única línia d'exemple amb veu de tot el capítol l'havia perduda, i la va perdre jo, en
    tornar a pujar el text."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_corregeix_el_text")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    escrit = {"sections": [{"id": "iri", "title": "iri", "examples": [{"shi": "is trit aman?", "ca": "Que vols aigua?"}]}],
              "dialogue": {"title": "A la botiga", "turns": [{"who": "la dona", "shi": "is dar-k tudit?", "ca": "Que tens mantega?"}]},
              "vocabulary": [{"shi": "aman", "ca": "aigua"}]}
    client.put("/method/la-botiga/content", headers=hdr, json=escrit)

    made = client.post("/method/la-botiga/line", headers=hdr,
                       json={"kind": "example", "section": "iri", "index": 0}).json()
    assert made["created"] is True

    # i ara algú torna a pujar el capítol tal com el té escrit, sense cap número
    escrit["sections"][0]["examples"][0]["ca"] = "Que en vols, d'aigua?"
    client.put("/method/la-botiga/content", headers=hdr, json=escrit)

    back = client.get("/method/la-botiga").json()["content"]["sections"][0]["examples"][0]
    assert back["ca"] == "Que en vols, d'aigua?", "la correcció s'ha desat"
    assert back.get("drill_id") == made["drill_id"], "i la veu no s'ha desvinculat"

    client.delete(f"/drills/{made['drill_id']}", headers=hdr)
