"""Whole stories and songs, instead of loose sentences (#189).

A story is not a new kind of row: it is what a group of drills already is when they come from one
source and say when they are spoken. These tests are about what makes a group a story, and about
the one thing that must not be hidden — a line that can be heard but not read.
"""
import main
from test_api import client, register


def _line(hdr, title, at, text, meaning, voiced=True):
    return client.post("/drills/", headers=hdr, json={
        "text_catalan": meaning, "text_tachelhit": text,
        "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/{title}-{at}.mp3" if voiced else None,
        "source_title": title, "video_start_time": at, "video_url": f"https://youtu.be/{title}",
    }).json()


def test_a_group_of_timed_recorded_lines_from_one_source_is_a_story():
    hdr = {"X-User-Token": register("story_teller")}
    title = "El llop i la seva ombra (prova)"
    for i in range(7):
        _line(hdr, title, float(i * 3), f"awal {i}", f"línia {i}")

    stories = client.get("/stories").json()["stories"]
    mine = next((s for s in stories if s["title"] == title), None)
    assert mine, "set línies amb temps i veu són una història"
    assert mine["lines"] == 7 and mine["missing_words"] == 0

    page = client.get(f"/stories/{mine['slug']}").json()
    # in the order they are SPOKEN, not the order they were typed
    assert [d["text_tachelhit"] for d in page["drills"]] == [f"awal {i}" for i in range(7)]
    assert page["source_url"] or page["video_url"]


def test_els_episodis_duna_serie_retallada_pels_subtitols_son_histories():
    """Baba Ali (#535): 3.600 línies amb veu, cada una amb el seu títol «Baba Ali · episodi N · m:ss»
    i cap amb el segon dins del vídeo, perquè no ve de YouTube. La pantalla d'històries no en veia
    cap. L'episodi és la història; el minut del títol, l'ordre; i dues rèpliques del mateix minut
    no són un munt, són veïnes."""
    hdr = {"X-User-Token": register("qui_mira_baba_ali")}
    minuts = ["0:05", "0:09", "0:09", "0:14", "1:02", "1:30", "2:11"]   # dues al mateix minut
    for i, m in enumerate(reversed(minuts)):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": f"rèplica {m}", "text_tachelhit": f"awal {m}",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/baba-{i}.mp3",
            "source_title": f"Prova Baba · episodi 3 · {m}", "source_url": "https://forja.ma/content/baba-ali"})
    client.post("/drills/", headers=hdr, json={   # un altre episodi, amb una línia sola: no és cap història
        "text_catalan": "x", "text_tachelhit": "x", "source_title": "Prova Baba · episodi 4 · 0:01"})

    stories = client.get("/stories").json()["stories"]
    ep = next((s for s in stories if s["title"] == "Prova Baba · episodi 3"), None)
    assert ep, "l'episodi és una història, encara que cap línia no porti el segon del vídeo"
    assert ep["lines"] == 7 and ep["voiced"] == 7 and ep["series"] in (None, "Prova Baba") and (ep["chapter"] in (None, 3))
    assert not any(s["title"].startswith("Prova Baba · episodi 4") for s in stories)

    page = client.get(f"/stories/{ep['slug']}").json()
    assert [d["text_catalan"] for d in page["drills"]] == [f"rèplica {m}" for m in minuts], "en l'ordre del minut del títol"


def test_five_loose_sentences_are_not_a_story():
    """Six lines is the floor: fewer is a pile from the same video, not something to follow."""
    hdr = {"X-User-Token": register("story_short")}
    title = "Massa poca cosa (prova)"
    for i in range(5):
        _line(hdr, title, float(i), f"inna {i}", f"diu {i}")
    assert not any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_a_line_nobody_has_written_down_keeps_its_place_and_says_so():
    """A story with holes is still a story. Dropping the line would hide the work; moving it
    would lie about where it belongs."""
    hdr = {"X-User-Token": register("story_holes")}
    title = "Amb forats (prova)"
    for i in range(6):
        _line(hdr, title, float(i * 2), "" if i == 2 else f"tawal {i}", f"vol dir {i}")

    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["lines"] == 6 and mine["written"] == 5 and mine["missing_words"] == 1

    page = client.get(f"/stories/{mine['slug']}").json()
    assert [bool((d["text_tachelhit"] or "").strip()) for d in page["drills"]] == [True, True, False, True, True, True]


def test_an_unknown_story_is_a_404_not_an_empty_page():
    assert client.get("/stories/aixo-no-existeix").status_code == 404


def test_lines_that_start_at_the_same_second_are_a_pile_not_a_story():
    """Deu frases tallades d'un mateix vídeo no són un conte (#335).

    Va passar de debò: deu frases soltes d'un vídeo del propietari van sortir a la pàgina com a
    «October 2, 2023», que no és cap títol sinó el que YouTube hi posa quan el vídeo no en té.
    Totes portaven temps, de manera que passaven la prova — però tres començaven al segon 0.0.

    Dues línies d'un conte no comencen mai al mateix segon. Comprovat contra la biblioteca abans
    de posar-ho: de les 25 històries que la pàgina ensenyava, les 24 de debò tenien tots els
    temps diferents (776 línies, cap repetida) i només la falsa en repetia.
    """
    hdr = {"X-User-Token": register("story_pile")}
    title = "October 2, 2023 (prova)"
    for i, at in enumerate([0.0, 0.0, 0.0, 7.18, 9.21, 15.99, 20.0, 24.5]):
        _line(hdr, title, at, f"awal {i}", f"frase solta {i}")
    assert not any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_the_same_lines_with_their_own_times_are_a_story_again():
    """Que el que ho treu sigui la col·lisió i no una altra cosa: mateixes línies, temps propis."""
    hdr = {"X-User-Token": register("story_pile_ok")}
    title = "Amb temps propis (prova)"
    for i, at in enumerate([0.0, 3.2, 5.1, 7.18, 9.21, 15.99, 20.0, 24.5]):
        _line(hdr, title, at, f"awal {i}", f"línia {i}")
    assert any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_the_title_says_which_series_and_which_chapter():
    """El títol del canal porta la sèrie, el capítol i el nom en dos alfabets tot junt (#346)."""
    import stories as st
    assert st.series_of("The Traveller -2- ⴰⵏⵎⴰⴷⴷⵓ - Anmaddu") == ("The Traveller", 2)
    assert st.series_of("The Rivals - 1 - ⵉⵏⴳⴳⵯⴰ - inggʷa") == ("The Rivals", 1)
    assert st.series_of("The Last Warrior- 4 -ⴰⵎⵏⵏⴰⵖ ⴰⵎⴳⴳⴰⵔⵓ") == ("The Last Warrior", 4)
    # Un conte sol no té capítol, i dir que en té seria inventar-se una sèrie.
    assert st.series_of("The Wolf and The Lamb - ⵓⵛⵛⵏ ⴷ ⵉⴽⵔⵓ") == (None, None)


def test_the_chapters_come_back_together_and_in_order():
    """Perquè algú pugui començar un conte pel principi, que és el que la pàgina ha de fer fàcil.

    Abans la llista anava per nombre de línies i els set capítols quedaven escampats per la
    graella, barrejats amb les altres sèries.
    """
    hdr = {"X-User-Token": register("story_series")}
    # A posta en desordre, i amb el capítol 2 més llarg que els altres: si l'ordre fos per
    # llargada, sortiria primer.
    for cap, quantes in ((3, 6), (1, 7), (2, 12)):
        for i in range(quantes):
            _line(hdr, f"La prova -{cap}- ⴰⵡⴰⵍ", float(i * 3), f"awal {i}", f"línia {i}")

    meves = [s for s in client.get("/stories").json()["stories"] if s["series"] == "La prova"]
    assert [s["chapter"] for s in meves] == [1, 2, 3]
    # I vénen de seguit, sense res pel mig: la pàgina els agrupa confiant en aquest ordre.
    totes = [s["series"] for s in client.get("/stories").json()["stories"]]
    primer = totes.index("La prova")
    assert totes[primer:primer + 3] == ["La prova"] * 3


def test_one_chapter_alone_is_not_a_series():
    hdr = {"X-User-Token": register("story_one_chapter")}
    for i in range(7):
        _line(hdr, "Tota sola -1- ⴰⵡⴰⵍ", float(i * 3), f"awal {i}", f"línia {i}")
    sola = next(s for s in client.get("/stories").json()["stories"] if "Tota sola" in s["title"])
    assert sola["series"] is None and sola["chapter"] is None


def test_the_cover_is_the_video_s_own_cover_not_a_drill_illustration():
    """La portada d'un conte que ve d'un vídeo és la portada d'aquell vídeo (#346).

    Les il·lustracions dels drills es van demanar per a una frase, no per al conte: una d'elles
    era una carta d'ajust de televisió i feia de portada d'una faula.
    """
    hdr = {"X-User-Token": register("story_cover")}
    title = "Amb portada (prova)"
    for i in range(6):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": f"línia {i}", "text_tachelhit": f"awal {i}",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/{i}.mp3",
            "image_url": "https://exemple.test/carta-d-ajust.jpg" if i == 0 else None,
            "source_title": title, "video_start_time": float(i * 3),
            "source_url": "https://www.youtube.com/watch?v=p7qlqkDVyNU",
        })
    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["cover"] == "https://i.ytimg.com/vi/p7qlqkDVyNU/hqdefault.jpg"


def test_a_story_with_no_video_keeps_its_own_illustration():
    """Sense vídeo, la il·lustració d'una de les seves línies és millor que res."""
    hdr = {"X-User-Token": register("story_cover_none")}
    title = "Sense vídeo (prova)"
    for i in range(6):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": f"línia {i}", "text_tachelhit": f"awal {i}",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/n{i}.mp3",
            "image_url": "https://exemple.test/dibuix.jpg" if i == 1 else None,
            "source_title": title, "video_start_time": float(i * 3),
        })
    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["cover"] == "https://exemple.test/dibuix.jpg"
def test_the_page_carries_the_times_of_each_word_when_we_have_them():
    """Perquè la pantalla pugui seguir la veu i encendre la paraula que sona (#340).

    L'alineament forçat ja va desar quan es diu cada paraula dins cada gravació. La pàgina de la
    història només l'ha d'ensenyar, i ha de distingir les línies que en tenen de les que no: una
    línia sense alineament no hi surt, perquè repartir-la pel rellotge encendria paraules al
    moment equivocat.
    """
    from main import SessionLocal
    from models import WordAudio
    hdr = {"X-User-Token": register("story_times")}
    title = "Amb els temps (prova)"
    fets = [_line(hdr, title, float(i * 3), f"awal {i}", f"línia {i}") for i in range(6)]

    db = SessionLocal()
    try:
        # Dues línies alineades, quatre sense: és el cas de debò, no una història perfecta.
        for d, mots in ((fets[0], [("awal", 120, 540), ("0", 540, 900)]),
                        (fets[3], [("awal", 0, 300), ("3", 300, 610)])):
            for w, a, b in mots:
                db.add(WordAudio(key=w, word=w, drill_id=d["id"], start_ms=a, end_ms=b,
                                 source="library"))
        db.commit()
    finally:
        db.close()

    slug = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)["slug"]
    temps = client.get(f"/stories/{slug}").json()["word_times"]

    assert set(temps) == {str(fets[0]["id"]), str(fets[3]["id"])}, "només les que en tenen"
    assert temps[str(fets[0]["id"])] == [{"w": "awal", "start": 0.12, "end": 0.54},
                                         {"w": "0", "start": 0.54, "end": 0.9}]


def test_a_story_without_any_alignment_says_so_with_an_empty_map():
    """Cap temps no és una resposta vàlida; no és un error ni un camp que falti."""
    hdr = {"X-User-Token": register("story_no_times")}
    title = "Sense temps (prova)"
    for i in range(6):
        _line(hdr, title, float(i * 3), f"inna {i}", f"diu {i}")
    slug = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)["slug"]
    assert client.get(f"/stories/{slug}").json()["word_times"] == {}


def test_an_analysis_is_only_written_for_lines_somebody_has_written(monkeypatch):
    """Desmuntar una oració només té sentit si la frase existeix de debò (#341).

    Una línia que ningú no ha transcrit no es pot analitzar. Demanar-ho igualment faria que la
    màquina se l'inventés primer i l'analitzés després, que és la pitjor de les dues coses que
    podríem fer: una anàlisi convincent d'una frase que no ha dit ningú.
    """
    import analisi
    hdr = {"X-User-Token": register("story_analysis")}
    title = "Per desmuntar (prova)"
    for i in range(6):
        _line(hdr, title, float(i * 3), "" if i in (1, 4) else f"ur ssinɣ {i}", f"no ho sé {i}")
    page_slug = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)["slug"]

    from main import SessionLocal
    import stories as stories_mod
    with SessionLocal() as db:
        ids = stories_mod.one(db, page_slug)["drill_ids"]
        frases = analisi.frases_de(db, ids)
    assert len(frases) == 4, "les dues línies sense paraules escrites no hi entren"
    assert all(f["shi"] for f in frases)


def test_an_analysis_that_quotes_words_the_sentence_does_not_have_is_thrown_away():
    """Una anàlisi que cita un tros que no és a la frase parla d'una altra frase."""
    import analisi
    frases = [{"id": 1, "shi": "ur ssinɣ mani ɣ illa", "ca": "no sé on és"},
              {"id": 2, "shi": "is tssnt?", "ca": "ho saps?"}]
    bo = analisi.neteja({
        "1": {"analisi": "Frase negativa: «ur» davant del verb «ssinɣ» el nega.", "unitats": ["negacio"]},
        "2": {"analisi": "La pregunta la obre «mani», que no hi és.", "unitats": ["preguntes"]},
    }, frases)
    assert set(bo) == {1}, "la que cita «mani», que no és a la seva frase, se'n va"
    assert bo[1]["unitats"] == ["negacio"]


def test_an_analysis_full_of_grammarian_words_is_thrown_away():
    """Val més una frase sense anàlisi que una anàlisi que ningú no entén: és la regla del curs."""
    import analisi
    frases = [{"id": 1, "shi": "ur ssinɣ", "ca": "no ho sé"}]
    assert analisi.neteja(
        {"1": {"analisi": "El morfema «ur» és un clític preverbal.", "unitats": []}}, frases) == {}


def test_invented_units_are_dropped_not_shown():
    import analisi
    frases = [{"id": 1, "shi": "ur ssinɣ", "ca": "no ho sé"}]
    bo = analisi.neteja(
        {"1": {"analisi": "Frase negativa: «ur» nega el verb.",
               "unitats": ["negacio", "la-unitat-que-no-existeix"]}}, frases)
    assert bo[1]["unitats"] == ["negacio"]


def test_the_key_the_model_returns_is_not_trusted():
    """El model torna «id 1» en comptes de «1», copiant el format de la llista que se li passa.

    Buscar la clau literal no trobava res i es llençava tot: 268 anàlisis de 281 la primera
    nit, i semblava que el model no en sabés. És el mateix parany de sempre: l'índex que torna
    un model és una pista, no una clau.
    """
    import analisi
    frases = [{"id": 7801, "shi": "ur ssinɣ", "ca": "no ho sé"},
              {"id": 7802, "shi": "is tssnt?", "ca": "ho saps?"}]
    bo = analisi.neteja({
        "id 1": {"analisi": "Frase negativa: «ur» nega el verb «ssinɣ».", "unitats": ["negacio"]},
        "id 2": {"analisi": "Pregunta oberta amb «is» al davant.", "unitats": ["preguntes"]},
    }, frases)
    assert set(bo) == {7801, 7802}


def test_the_sentence_itself_can_be_the_key():
    import analisi
    frases = [{"id": 99, "shi": "ur ssinɣ", "ca": "no ho sé"}]
    bo = analisi.neteja({"ur ssinɣ": {"analisi": "«ur» nega el verb.", "unitats": []}}, frases)
    assert set(bo) == {99}

def test_a_cut_answer_keeps_the_entries_that_are_whole():
    """Una resposta que s'acaba a mitja clau no pot costar la tanda sencera.

    Això va passar de debò: 37 línies en una crida, 7.874 caràcters que s'acaben en «"id 7», i
    cap JSON que es pogués llegir. Es van perdre les 37 —i hi havia una trentena d'anàlisis
    senceres escrites a dins— i es van pagar igual (#357).
    """
    import analisi
    frases = [{"id": 10, "shi": "ur ssinɣ", "ca": "no ho sé"},
              {"id": 11, "shi": "is tssnt?", "ca": "ho saps?"},
              {"id": 12, "shi": "mani?", "ca": "on?"}]
    tallada = ('{"id 10": {"analisi": "Frase negativa: «ur» nega el verb «ssinɣ».", '
               '"unitats": ["negacio"]}, '
               '"id 11": {"analisi": "Pregunta amb «is» al davant.", "unitats": ["preguntes"]}, '
               '"id 1')
    bo = analisi.neteja(analisi.resposta_json(tallada), frases)
    assert set(bo) == {10, 11}          # les senceres es desen
    assert 12 not in bo                 # la que va quedar a mitges, no


def test_the_sentences_are_asked_for_twelve_at_a_time(monkeypatch):
    """Qui truca no pot saber quant ocupa una anàlisi: el mòdul reparteix la feina."""
    import analisi, gemini_client, json as _json
    frases = [{"id": 100 + i, "shi": "ur ssin%d" % i, "ca": "no ho se %d" % i} for i in range(25)]
    tandes = []

    def respon(sys_, contents, **k):
        text = contents[0]["text"]
        meves = [f for f in frases if ("«%s»" % f["shi"]) in text]
        tandes.append(len(meves))
        return _json.dumps({str(f["id"]): {"analisi": "Frase negativa: «ur» nega el verb.",
                                           "unitats": ["negacio"]} for f in meves})

    monkeypatch.setattr(gemini_client, "gemini_generate", respon)
    bo = analisi.escriu(frases)
    assert tandes == [12, 12, 1]                  # 25 frases, tres crides, cap de més de dotze
    assert len(bo) == 25 and set(bo) == {f["id"] for f in frases}
