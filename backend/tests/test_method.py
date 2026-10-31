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
        # Aquest test comprova que una línia del llibre ENCARA no és una frase nostra, i això
        # només és cert si el capítol surt sense escriure. La base de proves no es llença entre
        # execucions i desar un capítol conserva el `drill_id` de les línies que ja s'han gravat
        # (keep_voices), de manera que la segona vegada la línia ja en portava un i el test queia
        # segons l'ordre. S'esborra el capítol abans de començar, i així cada execució parteix
        # d'on diu que parteix.
        from models import MethodChapter
        db.query(MethodChapter).filter(MethodChapter.slug == "la-botiga").delete()
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
    # El text desat és el que va escriure la persona; el que se serveix hi afegeix la tifinag de
    # les paraules amazigues («mšta» → «mšta ⵎⵛⵜⴰ»), que és el que fa la pàgina a tot arreu.
    servit = body["sections"][0]["text"]
    assert servit.startswith("Aquí es diu mšta") and servit.endswith("no mnckk.")
    assert "ⵎⵛⵜⴰ" in servit, "la paraula amaziga porta la seva tifinag"

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

    # (tant li fa si la línia ja era una frase d'una altra prova: el que es mira és que hi segueixi)
    made = client.post("/method/la-botiga/line", headers=hdr,
                       json={"kind": "example", "section": "iri", "index": 0}).json()
    assert made["drill_id"]

    # i ara algú torna a pujar el capítol tal com el té escrit, sense cap número
    escrit["sections"][0]["examples"][0]["ca"] = "Que en vols, d'aigua?"
    client.put("/method/la-botiga/content", headers=hdr, json=escrit)

    back = client.get("/method/la-botiga").json()["content"]["sections"][0]["examples"][0]
    assert back["ca"] == "Que en vols, d'aigua?", "la correcció s'ha desat"
    assert back.get("drill_id") == made["drill_id"], "i la veu no s'ha desvinculat"

    client.delete(f"/drills/{made['drill_id']}", headers=hdr)


def test_el_capitol_porta_a_la_seva_practica():
    """La sortida del capítol.

    Un capítol s'acabava i no tornava mai: es llegia i prou. La pràctica és el que ho arregla
    —puntua cada frase i el repàs espaiat les fa tornar soles—, i fins ara no hi havia cap
    manera d'arribar-hi des del capítol: s'havia de saber que existia i buscar-la a «Pràctica».

    El capítol la troba pel seu nom («Capítol 4 · …») i diu quants passos té. I l'ha de trobar
    de seguida: la pàgina del capítol es serveix d'una memòria que fins ara només es renovava
    quan es tocava una frase, i una pràctica nova no és una frase (el capítol l'hauria ensenyada
    l'endemà).
    """
    from test_api import client, register

    hdr = {"X-User-Token": register("chapter_exit")}
    abans = client.get("/method/la-botiga").json()
    assert abans.get("practice_test") is None, "cap pràctica encara"

    test = client.post("/tests/", headers=hdr, json={
        "title": "Capítol 4 · prova d'aquesta prova",
        "description": "d'usar i llençar", "question_type": "audio",
        "hint_level": "none", "hint_percentage": 30, "hint_tries_before_reveal": 3,
        "passing_score": 70, "drill_ids": "", "visibility": "shared"}).json()
    try:
        steps = [{"kind": "note", "payload": {"heading": "Hola", "text": "Dues passes."}},
                 {"kind": "note", "payload": {"heading": "Adeu", "text": "I ja està."}}]
        assert client.put(f"/tests/{test['id']}/steps", headers=hdr,
                          json={"steps": steps}).status_code == 200

        out = client.get("/method/la-botiga").json()
        assert out["practice_test"], "el capítol ha de portar a la pràctica tot seguit"
        assert out["practice_test"]["id"] == test["id"]
        assert out["practice_test"]["steps"] == 2, "i dir quants passos té"
    finally:
        client.delete(f"/tests/{test['id']}", headers=hdr)

    assert client.get("/method/la-botiga").json().get("practice_test") is None, \
        "i deixa de portar-hi quan la pràctica ja no hi és"


def test_la_segona_zona_en_posa_dues_i_el_credit_diu_d_on_es():
    """Dues coses de l'auditoria pedagògica, i la segona és un canvi de criteri.

    LES DUES TARGETES. El pedagog va demanar retallar les seccions de la segona zona i després
    ho va retirar ell mateix, amb el principi que val per a tot el projecte: «no esborris mai el
    que ha escrit una persona; limita lliurement el que ha produït una consulta». Els exemples
    del manual són triats i traduïts a mà i es queden tots; les targetes «dit per les nostres
    veus» són el resultat d'una cerca que es torna a executar a cada càrrega, i allà sí que hi va
    el límit. El total segueix sent el de debò, perquè és el que fa la línia «i N més a la
    biblioteca»: no desapareix cap frase.

    EL CRÈDIT. El nom de qui diu una línia no és un indicador d'estat: és un crèdit a una
    persona, i un crèdit sense poble deixa la varietat amagada, que és justament el que aquest
    projecte no fa.
    """
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("zona_aside")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    nats = []
    for n, (shi, ca) in enumerate((("imi n-tgmmi", "la porta de casa"),
                                   ("imi ad", "aquesta boca"),
                                   ("imi nns", "la seva boca"),
                                   ("imi lli", "aquella boca"))):
        nats.append(client.post("/drills/", headers=hdr, json={
            "text_catalan": ca, "text_tachelhit": shi, "author": "Veu-zona",
            "speaker": "Veu-zona", "region": "Aït Mraw (Azilal)",
            "grammar": "possessius", "grammar_source": "owner",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/imi{n}.mp3"}).json())

    # El capítol que s'escriu aquí s'esborra al final: un capítol escrit canvia el que veuen
    # els altres tests —un d'ells comprova justament que un capítol sense escriure no té text—
    # i amb l'ordre aleatori això es paga una vegada de cada deu.
    try:
        client.put("/method/que-fas/content", headers=hdr, json={
            "sections": [
                {"id": "oberta", "title": "La boca, oberta", "keys": ["imi"],
                 "examples": [{"shi": "imi", "ca": "la boca"}]},
                {"id": "plegada", "title": "La boca, al voltant", "zone": "aside",
                 "summary": "El que l'escena deixa veure.", "keys": ["imi"]},
            ],
            "vocabulary": [{"shi": "imi n-tgmmi", "ca": "la porta de casa"}],
        })
        body = client.get("/method/que-fas").json()["content"]
        oberta, plegada = body["sections"]

        assert len(plegada["ours_drills"]) <= 2, "la zona plegada en posa dues, no quatre"
        assert plegada["ours_total"] >= len(plegada["ours_drills"]), \
            "i el total segueix sent el de debò: és el que porta a la biblioteca"
        assert len(oberta["ours_drills"]) >= len(plegada["ours_drills"]), \
            "la zona oberta no es retalla: allà s'estudia"

        # el crèdit: qui ho diu i d'on és, a la paraula que la biblioteca ja té
        word = body["vocabulary"][0]
        assert word.get("audio_url"), "la paraula que la biblioteca té surt amb veu"
        assert word.get("speaker") == "Veu-zona"
        assert word.get("region") == "Aït Mraw (Azilal)", "i d'on és qui la diu"
    finally:
        from models import MethodChapter
        db = main.SessionLocal()
        try:
            db.query(MethodChapter).filter(MethodChapter.slug == "que-fas").delete()
            for d in nats:
                db.query(main.DrillModel).filter(main.DrillModel.id == d["id"]).delete()
            db.commit()
        finally:
            db.close()


def test_els_sons_citats_al_metode_porten_la_seva_tifinag():
    """Una lliçó que ensenya un so citant-lo en llatí ensenya el so i no ensenya la lletra.

    El curs de gramàtica ja hi passava des de fa temps; el Mètode no, i es notava al capítol 1,
    que és el DELS SONS: deia «cinc consonants: kʷ, gʷ, ɣʷ…» sense ensenyar-ne cap en tifinag.
    """
    import method

    cos = method.with_letters_everywhere({
        "intro": "La «ɛ» no existeix en català.",
        "sections": [{
            "id": "x",
            "text": "Cinc consonants s'arrodoneixen: «kʷ», «gʷ».",
            "table": {"title": "Com es diuen", "rows": [{"p": "ɣ", "v": "com la r francesa"}]},
        }],
    })
    assert "ⵄ" in cos["intro"], "el so citat a l'entradeta porta la seva tifinag"
    assert "ⴽⵯ" in cos["sections"][0]["text"], "i els del text també"
    # la fila de la taula de l'alfabet: allà la lletra NO va citada, és la fila sencera
    assert cos["sections"][0]["table"]["rows"][0]["p"].startswith("ɣ ⵖ")


def test_i_no_s_inventa_lletres_on_no_n_hi_ha():
    """Només el que és citat i curt. Una paraula catalana citada no porta tifinag."""
    import method

    cos = method.with_letters_everywhere({"sections": [{"text": "Això vol dir «mantega», no «oli»."}]})
    text = cos["sections"][0]["text"]
    assert "mantega»" in text and "ⵣ" not in text


def test_un_capitol_sense_frases_propies_troba_la_veu_a_la_biblioteca():
    """El capítol 1 —el DELS SONS— no té cap frase assignada, i per això sortia mut: ni els
    exemples ni les parelles mínimes es podien escoltar. Un capítol que diu «no passis d'aquí
    fins que distingeixis `imi` de `immi`» i no deixa sentir cap de les dues no es pot fer servir.

    Ara qualsevol línia del capítol —exemple, paraula o fila d'una columna— busca a TOTA la
    biblioteca la frase que diu exactament això, i se'n queda la veu. El que ningú no ha gravat
    es queda com era."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_escolta_els_sons")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    # dues frases de la biblioteca SENSE cap unitat de gramàtica: no són «del capítol dels sons»
    for ca, shi in (("la boca", "imi"), ("la mare", "immi")):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": ca, "text_tachelhit": shi, "author": "Prova-sons",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/{shi}.mp3"})

    client.put("/method/sons/content", headers=hdr, json={
        "sections": [{"id": "tensio", "title": "La doble dura més",
                      "examples": [{"shi": "imi", "ca": "boca"}],
                      "columns": [{"title": "simple", "rows": [{"shi": "imi", "ca": "boca"}]},
                                  {"title": "doble", "rows": [{"shi": "immi", "ca": "mare"},
                                                              {"shi": "tissi", "ca": "beguda"}]}]}],
        "vocabulary": [{"shi": "immi", "ca": "mare"}]})

    body = client.get("/method/sons").json()["content"]
    sec = body["sections"][0]
    assert sec["examples"][0].get("audio_url"), "l'exemple del capítol es pot escoltar"
    simple, doble = sec["columns"]
    assert simple["rows"][0].get("audio_url"), "la parella mínima, també"
    assert doble["rows"][0].get("audio_url") and doble["rows"][0].get("speaker") == "Prova-sons"
    assert not doble["rows"][1].get("audio_url"), "«tissi», que ningú no ha gravat, es queda com era"
    assert body["vocabulary"][0].get("audio_url"), "i la paraula del vocabulari"


def test_la_parella_minima_es_pot_escoltar_i_no_es_desa_la_veu_dins_del_text():
    """Les files de les columnes són les parelles mínimes del capítol dels sons. El servidor els
    enganxa la veu en servir-les, i aquesta veu NO s'ha de desar dins del text del capítol: és
    una cosa calculada, i desar-la el congelaria amb les frases d'aquell dia."""
    import main, method
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_escolta_la_parella")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    client.post("/drills/", headers=hdr, json={
        "text_catalan": "espiar", "text_tachelhit": "mdi", "author": "Prova-parella",
        "region": "Aït Mraw (Azilal)",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/mdi.mp3"})

    client.put("/method/sons/content", headers=hdr, json={
        "sections": [{"id": "emfatiques", "title": "El punt a sota",
                      "columns": [{"title": "sense punt", "rows": [{"shi": "mdi", "ca": "espiar"}]},
                                  {"title": "amb punt", "rows": [{"shi": "mḍi", "ca": "tastar"}]}]}]})

    fila = client.get("/method/sons").json()["content"]["sections"][0]["columns"][0]["rows"][0]
    assert fila["audio_url"] and fila["speaker"] == "Prova-parella"
    assert fila["region"] == "Aït Mraw (Azilal)", "i d'on és qui la diu"

    net = method.strip_computed({"sections": [{"columns": [{"rows": [dict(fila)]}]}]})
    desada = net["sections"][0]["columns"][0]["rows"][0]
    assert set(desada) == {"shi", "ca"}, f"només el que algú ha escrit, i hi ha {sorted(desada)}"


def test_una_seccio_pot_acabar_amb_una_pregunta_i_la_seva_resposta():
    """Una secció que explica i no et demana res es llegeix i no es fixa. El «Comprova-ho» és
    la pregunta i la resposta que s'escriuen AMB el capítol —cap màquina no se les inventa— i
    passen pel mateix tracte que la resta de la prosa: les paraules amazigues hi porten la seva
    tifinag, i el que és calculat no es desa dins del text."""
    import main, method
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_pregunta_al_capitol")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    client.put("/method/sons/content", headers=hdr, json={
        "sections": [{"id": "emfatiques", "title": "El punt a sota", "text": "Les del punt.",
                      "questions": [{"q": "Quina de les dues porta punt a sota, aḍar o adan?",
                                     "a": "aḍar. L'altra té una d normal."}]}]})

    sec = client.get("/method/sons").json()["content"]["sections"][0]
    assert len(sec["questions"]) == 1
    q = sec["questions"][0]
    assert q["q"].startswith("Quina de les dues")
    assert "ⴰⴹⴰⵔ" in q["q"] and "ⴰⴹⴰⵔ" in q["a"], "la paraula amaziga porta la seva tifinag"
    # i el que s'ha desat és el que va escriure la persona, sense la tifinag calculada
    net = method.strip_computed({"sections": [{"questions": [dict(q)]}]})
    assert set(net["sections"][0]["questions"][0]) == {"q", "a"}


def test_la_tifinag_de_la_prosa_no_sacumula_quan_algu_torna_a_desar_el_capitol():
    """La tifinag de les paraules amazigues es calcula en SERVIR el capítol, i qui administra el
    desa tal com el veu a la pantalla. Sense cap comprovació, cada correcció hi afegia una còpia
    més i «aḍar» acabava sent «aḍar ⴰⴹⴰⵔ ⴰⴹⴰⵔ ⴰⴹⴰⵔ»."""
    import copy
    import method
    body = {"sections": [{"id": "x", "text": "Mira aḍar i awraɣ.",
                          "questions": [{"q": "Quina porta punt, aḍar?", "a": "aḍar."}]}]}
    una = method.with_letters_everywhere(copy.deepcopy(body))
    dues = method.with_letters_everywhere(copy.deepcopy(una))
    assert una == dues, "servir-ho dues vegades ha de donar el mateix"
    assert una["sections"][0]["text"].count("ⴰⴹⴰⵔ") == 1


def test_una_frase_citada_porta_la_tifinag_una_vegada_al_final():
    """El capítol 3 servia «ɣur-i ⵖⵓⵔⵉ yan gʷma ⴳⵯⵎⴰ»: la tifinag escampada entre les paraules
    deixa la frase il·legible. Una paraula solta sí que la porta al costat; una frase citada
    sencera la porta tota junta al final."""
    import method
    frase = method.amazigh_words_in("Si «ɣur-i yan gʷma» és «tinc un germà», digues-ho tu.")
    assert "«ɣur-i yan gʷma» ⵖⵓⵔⵉ ⵢⴰⵏ ⴳⵯⵎⴰ" in frase, frase
    assert "ɣur-i ⵖⵓⵔⵉ yan" not in frase, "res de tifinag entremig de la frase"

    solta = method.amazigh_words_in("Mira «aḍar» i prou.")
    assert solta == "Mira «aḍar ⴰⴹⴰⵔ» i prou.", solta

    # i el cas de l'amo del capítol 1 segueix igual
    cap1 = method.amazigh_words_in("com la r francesa de «Paris» — aɣyul «ase»")
    assert "aɣyul ⴰⵖⵢⵓⵍ" in cap1 and "ⴱⴰⵔⵉⵙ" not in cap1

    # servir-ho dues vegades dona el mateix
    assert method.amazigh_words_in(frase) == frase


def test_una_lletra_que_cap_paraula_nostra_no_diu_se_sent_dins_duna_frase():
    """El capítol dels sons ensenyava trenta-una lletres i no en deixava sentir cap.

    No era un descuit: de les 3.430 frases, cap paraula sola gravada no porta ɛ ḥ ṛ ɣ ṣ ṭ ẓ ḍ
    (#302), i la fila de la ɛ no tenia veu possible. Però el so hi és igualment DINS de frases
    que sí que estan gravades. Ara una línia que ensenya un so en demana una, i la frase va al
    costat de la paraula —mai al seu lloc— amb qui la diu i d'on és.

    Això es calcula en servir: `heard` no s'ha de desar mai dins del text del capítol, com la
    resta del que el servidor hi afegeix."""
    import main, method
    from test_api import client, register

    hdr = {"X-User-Token": register("qui_vol_sentir_la_lletra")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        db.commit()
    finally:
        db.close()

    client.post("/drills/", headers=hdr, json={
        "text_catalan": "Adeu!", "text_tachelhit": "Ac yɛawn buytran!", "author": "Prova-so",
        "region": "Aït Mraw (Azilal)",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/adeu.mp3"})

    client.put("/method/sons/content", headers=hdr, json={
        "sections": [{"id": "alfabet", "title": "L'alfabet del manual",
                      "examples": [{"shi": "ɛmmi", "ca": "oncle patern", "sound": "ɛ"},
                                   {"shi": "kʷti", "ca": "recordar-se", "sound": "kʷ"}],
                      "table": {"title": "Com es diuen",
                                "rows": [{"p": "ɛ", "v": "com la ḥ però fent vibrar la gola",
                                          "sound": "ɛ"}]}}]})

    body = client.get("/method/sons").json()["content"]
    sec = body["sections"][0]
    heard = sec["examples"][0]["heard"]
    assert "ɛ" in heard["shi"], "la frase porta la lletra escrita, no només el so"
    assert heard["audio_url"] and heard["speaker"] == "Prova-so"
    assert heard["region"] == "Aït Mraw (Azilal)", "el crèdit porta el poble"
    assert not sec["examples"][1].get("heard"), "la kʷ no la diu cap frase nostra: no se n'inventa cap"
    assert heard["shi"] != "text", "un drill que va perdre la transcripció no és un exemple de res"
    assert sec["table"]["rows"][0].get("heard"), "la fila de la taula també se sent"

    assert "heard" not in method.strip_computed(body)["sections"][0]["examples"][0], \
        "el que el servidor calcula no es desa dins del text del capítol"


def test_el_text_perdut_dun_drill_no_pot_fer_dexemple_dun_so():
    """170 drills van perdre el text amazic i s'hi va desar la paraula `text` o la lletra `n`
    (115 amb veu, #320). Buscant la frase més curta amb una `t`, la guanyadora era `text`, i
    amb una `n`, `n`: una errada nostra ensenyada com si fos la llengua."""
    import method

    class D:
        def __init__(self, i, shi, ca):
            self.id, self.text_tachelhit, self.text_catalan = i, shi, ca
            self.audio_url, self.speaker, self.author = "x.mp3", "Prova", None
            self.region = self.variety = None

    pot = [D(1, "text", "t'han tornat els diners"), D(2, "n", "Em dic Joan"),
           D(6, "tex", "Quan era petit…"),          # el mateix rastre, escurçat
           D(3, "ttu", "oblidar"), D(4, "nkki", "jo")]
    assert method.heard_in("t", pot, set()).text_tachelhit == "ttu"
    assert method.heard_in("n", pot, set()).text_tachelhit == "nkki"
    assert method.heard_in("t", [D(5, "tazerbit", "")], set()) is None,         "sense traducció no ensenya el so de res"


def test_el_proces_que_retalla_una_frase_no_es_qui_la_diu():
    """43 gravacions porten «Auto Capture» com a parlant: és el nom del procés que les va
    retallar d'un vídeo, no una persona. El capítol deia «ho diu Auto Capture» a la fila de la
    ḍ. Hi ha una veu humana, i el que passa és que no sabem de qui és: això s'ha de dir."""
    import method

    class D:
        def __init__(self, i, shi, ca, qui):
            self.id, self.text_tachelhit, self.text_catalan = i, shi, ca
            self.audio_url, self.speaker, self.author = "x.mp3", qui, None
            self.region = self.variety = None

    body = {"sections": [{"id": "x", "examples": [{"shi": "aḍar", "sound": "ḍ"}]}]}

    class DB:
        def query(self, *a):
            return self

        def filter(self, *a):
            return self

        def all(self):
            return [D(1, "a-bḍu d umazir", "deixa la meva llar", "Auto Capture")]

    out = method.attach_heard(DB(), body, [])
    h = out["sections"][0]["examples"][0]["heard"]
    assert h["speaker"] is None and h["captured"] is True


def test_la_veu_del_manual_va_amb_el_seu_credit_i_no_es_desa():
    """El Mètode adapta el manual d'El Mountassir, i el manual porta un CD on l'autor diu el que
    el llibre ensenya —justament el que les nostres veus de l'Atles central no diuen.

    Dues coses que han de ser certes sempre:

    · el crèdit viatja DINS del mateix objecte que l'àudio, de manera que qui dibuixa el botó no
      el pugui deixar fora: qui prem per sentir una frase ha de veure de qui és la veu;
    · una línia sense `url` no en porta cap: el servidor no s'inventa cap veu, com a tot arreu.

    I `cd` és calculat: no s'ha de desar mai dins del text del capítol."""
    import json
    import method
    from pathlib import Path

    index = {"capitols": {"sons": {
        "vocals:example:0": {"pista": "p1", "start": 46.63, "end": 47.2,
                             "url": "/method/cd/p1/46.63/47.2"},
        "vocals:example:1": {"pista": "p1", "start": 50.0, "end": 50.6},
    }}}
    fitxer = Path(method.__file__).parent / "data" / "_prova_cd.json"
    fitxer.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    abans = method.CD_FITXER
    try:
        method.CD_FITXER = fitxer
        body = {"sections": [{"id": "vocals", "examples": [
            {"shi": "aɣaras", "ca": "camí"}, {"shi": "argaz", "ca": "home"}]}]}
        out = method.attach_cd(body, "sons")
        cd = out["sections"][0]["examples"][0]["cd"]
        assert cd["qui"] == "Abdallah El Mountassir"
        # El llibre que la veu llegeix és «Initiation au tachelhit» (1999), no la «Méthode»
        # (#380). Posar-hi l'altre títol atribuïa a una obra el que surt d'una altra.
        assert cd["obra"].startswith("Initiation au tachelhit")
        assert cd["start"] == 46.63 and cd["url"].endswith("46.63/47.2")
        assert "cd" not in out["sections"][0]["examples"][1], \
            "sense fitxer penjat no hi ha botó"
        assert out is method.attach_cd(out, "un-capitol-que-no-hi-es")
        assert "cd" not in method.strip_computed(out)["sections"][0]["examples"][0]
    finally:
        method.CD_FITXER = abans
        fitxer.unlink(missing_ok=True)
def test_totes_les_linies_dun_capitol_es_tornen_frases_duna_passada():
    """El Mètode no es pot gravar si les seves línies no existeixen com a frases.

    Fins ara una línia només es tornava frase quan algú la volia gravar, de manera que el que
    ningú no havia demanat no existia: no es podia comptar, no sortia a «falta veu» i no es
    podia demanar a un parlant. Això fa la passada sencera.

    Dues coses que ha de respectar, i per això són aquí:

    1. **No duplicar.** Si la biblioteca ja diu exactament això —amb veu o sense— la línia s'hi
       lliga. Dues files que diuen el mateix són dues peticions de veu i dos llocs on corregir
       el català.
    2. **Dir d'on ve.** Cada frase nova neix amb la font, la varietat i el lloc: el manual d'El
       Mountassir, taixelhit, Souss. Una frase del sud desada sense varietat es confon amb una
       de l'Atles l'endemà.
    """
    import main
    from test_api import client, register

    db = main.SessionLocal()
    try:
        from models import MethodChapter
        db.query(MethodChapter).filter(MethodChapter.slug == "els-convidats").delete()
        db.commit()
    finally:
        db.close()

    plain = {"X-User-Token": register("convidats_admin")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=plain).json()
        row = db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first()
        row.is_admin = True
        db.commit()
    finally:
        db.close()
    boss = plain

    try:
        # una frase que la biblioteca JA diu: la línia s'hi ha de lligar, no fer-ne una bessona
        ja = client.post("/drills/", headers=boss, json={
            "text_catalan": "Benvingut", "text_tachelhit": "ansuf"}).json()

        body = {
            "intro": "Rebre algú a casa.",
            "sections": [{"id": "rebre", "title": "Rebre",
                          "examples": [{"shi": "ansuf", "ca": "benvingut"},
                                       {"shi": "kcm s uxam", "ca": "entra a casa"}]}],
            "vocabulary": [{"shi": "anbgi", "ca": "convidat"}],
        }
        assert client.put("/method/els-convidats/content",
                          headers=boss, json=body).status_code == 200

        # no és de qualsevol
        altre = {"X-User-Token": register("convidats_ningu")}
        assert client.post("/method/els-convidats/drills", headers=altre).status_code == 403

        out = client.post("/method/els-convidats/drills", headers=boss)
        assert out.status_code == 200, out.text
        fet = out.json()
        assert fet["linies"] == 3
        assert fet["lligades"] == 1, "la que la biblioteca ja deia"
        assert fet["creades"] == 2
        assert fet["ja_hi_eren"] == 0

        back = client.get("/method/els-convidats").json()["content"]
        sec = back["sections"][0]
        assert sec["examples"][0]["drill_id"] == ja["id"], "s'hi lliga, no en crea una altra"
        nou = sec["examples"][1]["drill_id"]
        assert nou and nou != ja["id"]

        d = client.get(f"/drills/{nou}", headers=boss).json()
        assert d["text_tachelhit"] == "kcm s uxam"
        assert d["variety"] == "shi" and d["region"] == "Souss", "la varietat del llibre"
        assert "El Mountassir" in (d.get("source_channel") or ""), "qui n'és l'autor"
        assert "Méthode de Tachelhit" in (d.get("source_title") or "")
        assert not d.get("license"),             "el crèdit sí, l'estat del permís no: això viu a docs/PERMISOS.md"
        assert d.get("voice_wanted") is True, "neix demanant una veu"
        assert "metode-els-convidats" in (d.get("tag") or "")
        assert not d.get("grammar") and not d.get("topics"), \
            "una línia del llibre no és un exemple de les unitats del capítol"

        # segona passada: no en fa cap més
        altra = client.post("/method/els-convidats/drills", headers=boss).json()
        assert altra["creades"] == 0 and altra["lligades"] == 0
        assert altra["ja_hi_eren"] == 3
    finally:
        db = main.SessionLocal()
        try:
            from models import MethodChapter
            db.query(MethodChapter).filter(MethodChapter.slug == "els-convidats").delete()
            db.commit()
        finally:
            db.close()


def test_lindex_del_cd_nomes_fa_sonar_el_que_ha_sentit_una_persona():
    """Un botó que sona una altra cosa ensenya un so equivocat (#329, #380).

    L'índex es va omplir fent sentir el CD a la màquina i buscant quina línia del capítol
    s'assembla al que havia sentit. Una d'aquelles entrades deia `aẓur` on el CD diu `tiṭṭ`, i
    venia amb un **100% de semblança**: el número no mesura si la línia és aquella, mesura si
    s'assembla al que la màquina creu haver sentit, de manera que pujar el llistó només deixa
    passar les equivocacions més segures d'elles mateixes.

    Per això, mentre no hi hagi una prova que no surti de la màquina sentint sola, només sona el
    que ha comprovat una persona. La feina de la màquina no es llença: es desa a `per_comprovar`,
    i allà no porta adreça de tall, que és el que fa que no soni.

    L'ADR 0010 (31-10) hi afegeix UNA prova que no surt de la màquina sola: la lectura rica
    (ADR 0009) aparellada per ordre del llibre i calibrada amb les 130 escoltes d'en Pablo. En el
    tram d'acord ≥ 0,80, 39 de 40 escoltes eren «sí». Aquestes entrades sonen i ho diuen a `com`.
    """
    import json
    from pathlib import Path
    import method

    dades = json.loads(Path(method.CD_FITXER).read_text(encoding="utf-8"))
    for slug, linies in (dades.get("capitols") or {}).items():
        for on, d in linies.items():
            com = d.get("com") or ""
            assert com == "sentit" or com.startswith("lectura rica ≥0,80"), \
                "%s/%s sona sense que l'hagi sentida ningú ni la lectura calibrada: «%s»" % (slug, on, com)
            assert d.get("url"), "%s/%s diu que sona i no porta tall" % (slug, on)
            # #495: una adreça /method/cd/... només sona a la màquina que té el CD; a la web el
            # botó hi era i no sonava res
            assert d["url"].startswith("https://"),                 "%s/%s apunta a un tall que només existeix en aquesta màquina: %s" % (slug, on, d["url"])
    for slug, linies in (dades.get("per_comprovar") or {}).items():
        for on, d in linies.items():
            assert "url" not in d, \
                "%s/%s està per comprovar i porta adreça de tall: sonaria" % (slug, on)
            assert d.get("per_que_fora"), "%s/%s no diu per què no sona" % (slug, on)


def test_una_seccio_pot_dir_que_el_que_ensenya_es_diu_sencer():
    """«Decompon el que es recombina, i no decomponguis el que no» (#289).

    La marca va per secció i no global: a les fórmules desmuntar convida a fer-ne de noves, i a
    la secció del «com estàs?» i als pronoms desmuntar és justament el que cal. Es desa amb el
    capítol i sobreviu a una correcció, com la resta del que s'escriu."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("formula_sencera")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        from models import MethodChapter
        db.query(MethodChapter).filter(MethodChapter.slug == "els-convidats").delete()
        db.commit()
    finally:
        db.close()

    try:
        client.put("/method/els-convidats/content", headers=hdr, json={
            "intro": "Rebre algú a casa.",
            "sections": [
                {"id": "acomiadar", "title": "Acomiadar-se", "formula": True,
                 "examples": [{"shi": "add yawi ṛbbi sslamt", "ca": "Que Déu t'acompanyi"}]},
                {"id": "com-estas", "title": "Com estàs?",
                 "examples": [{"shi": "manza k-inn?", "ca": "Com estàs?"}]},
            ]})

        seccions = {s["id"]: s for s in client.get("/method/els-convidats").json()["content"]["sections"]}
        assert seccions["acomiadar"]["formula"] is True, "la fórmula es diu sencera"
        assert "formula" not in seccions["com-estas"], "i la secció on desmuntar cal, no ho diu"

        # i una correcció del text no s'endú la marca
        client.put("/method/els-convidats/content", headers=hdr, json={
            "intro": "Rebre algú a casa, i acomiadar-lo.",
            "sections": [dict(seccions["acomiadar"], text="El que es diu en marxar."),
                         seccions["com-estas"]]})
        tornada = {s["id"]: s for s in client.get("/method/els-convidats").json()["content"]["sections"]}
        assert tornada["acomiadar"]["formula"] is True
    finally:
        # La base de proves no es llença entre execucions, i hi ha una prova que diu
        # «index["els-convidats"]["written"] is False»: el capítol que s'escriu aquí s'ha de
        # treure, passi el que passi. En local no es veia —el fitxer ja venia escrit d'abans—;
        # a la CI, amb la base buida, queia la prova de l'altre.
        db = main.SessionLocal()
        try:
            from models import MethodChapter
            db.query(MethodChapter).filter(MethodChapter.slug == "els-convidats").delete()
            db.commit()
        finally:
            db.close()


def test_sota_les_nostres_veus_no_hi_va_cap_targeta_muda_ni_cap_veu_de_canal():
    """Trobat auditant el capítol 2 i val per a tota l'app (#288).

    Hi sortia «Tifawin!» —sense àudio i d'un canal— sota «Dit per les nostres veus», en una
    secció que precisament no tenia cap veu: una contradicció en tres paraules. Ara el bloc
    només ensenya frases que es poden ESCOLTAR, i la veu que no és d'una persona que coneguem ho
    diu, perquè es vegi abans de prémer: per escoltar-la, benvinguda; per imitar-la, no."""
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("veus_de_fora")}
    db = main.SessionLocal()
    try:
        me = client.get("/users/me", headers=hdr).json()
        db.query(main.UserModel).filter(main.UserModel.id == me["id"]).first().is_admin = True
        from models import MethodChapter
        db.query(MethodChapter).filter(MethodChapter.slug == "el-viatge").delete()
        db.commit()
    finally:
        db.close()

    # Amb la unitat del capítol dita a mà: una frase entra al capítol pel que ensenya, i aquí el
    # que es prova és una altra cosa.
    muda = client.post("/drills/", headers=hdr, json={
        "text_catalan": "el tren", "text_tachelhit": "lmasina",
        "grammar": "preposicions", "grammar_source": "owner"}).json()
    de_canal = client.post("/drills/", headers=hdr, json={
        "text_catalan": "el tren arriba", "text_tachelhit": "lmasina tlkm",
        "grammar": "preposicions", "grammar_source": "owner",
        "author": "ILoveLanguages (parlant nadiu)", "variety": "tzm",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/canal-lmasina.mp3"}).json()

    try:
        client.put("/method/el-viatge/content", headers=hdr, json={
            "intro": "El viatge.",
            "sections": [{"id": "el-tren", "title": "El tren", "text": "Per anar-hi.",
                          "examples": [{"shi": "lmasina", "ca": "el tren"}]}]})

        sec = client.get("/method/el-viatge").json()["content"]["sections"][0]
        ids = [d["id"] for d in sec["ours_drills"]]
        assert muda["id"] not in ids, "una targeta muda no surt sota un títol que promet veus"
        assert de_canal["id"] in ids, "i una que SÍ que sona hi surt, encara que sigui d'un canal"
        assert sec["ours_total"] >= 2, "el total segueix sent el de debò: no desapareix cap frase"

        veu = next(d["veu"] for d in sec["ours_drills"] if d["id"] == de_canal["id"])
        assert veu["mena"] == "canal" and veu["per_imitar"] is False, veu
        nostra_muda = next((d for d in sec["ours_drills"] if d["id"] == muda["id"]), None)
        assert nostra_muda is None
    finally:
        # La base de proves no es llença entre execucions: un capítol escrit aquí és un capítol
        # escrit per a les altres proves, i n'hi ha una que diu «un capítol sense escriure no en
        # té». Es treu al final passi el que passi.
        db = main.SessionLocal()
        try:
            from models import MethodChapter
            db.query(MethodChapter).filter(MethodChapter.slug == "el-viatge").delete()
            db.commit()
        finally:
            db.close()
