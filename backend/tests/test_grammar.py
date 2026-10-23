"""Grammar course: units, classification into units, the unit page with its lesson and examples."""
import json

import grammar
import main
from test_api import client


def test_units_are_ordered_and_endpoint_lists_them():
    r = client.get("/grammar").json()
    assert [u["slug"] for u in r["units"]] == grammar.SLUGS and r["units"][0]["slug"] == grammar.SOUNDS_UNIT and r["units"][1]["slug"] == "formules"
    assert set(r["counts"]) == set(grammar.SLUGS)


def _wait_lesson(slug: str, secs: float = 20.0) -> dict:
    """The lesson a unit page asked for in the background, once the writer has finished."""
    import time
    for _ in range(int(secs * 10)):
        if slug not in grammar.writing():
            body = client.get(f"/grammar/{slug}/lesson").json()
            if not body["lesson"].get("writing"):
                return body["lesson"]
        time.sleep(0.1)
    raise AssertionError(f"lesson {slug} was never written")


def test_classification_fills_grammar_and_unit_page_shows_lesson_and_examples(monkeypatch):
    a = client.post("/drills/", json={"text_catalan": "No hi aniré", "text_tachelhit": "ur rad dduɣ", "audio_url": "https://example.test/a.webm"}).json()
    b = client.post("/drills/", json={"text_catalan": "la casa del meu pare", "text_tachelhit": "tigmmi n baba"}).json()
    c = client.post("/drills/", json={"text_catalan": "x", "text_tachelhit": "text"}).json()  # placeholder: never classified
    answers = {str(a["id"]): ["negacio", "aorist-ad"], str(b["id"]): ["possessius", "estat-annexio"], str(c["id"]): ["formules"]}
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *x, **k: __import__("json").dumps(answers))
    res = grammar.run(main.SessionLocal, only_ids=[a["id"], b["id"], c["id"]])
    assert res["done"] == 2
    assert client.get(f"/drills/{a['id']}").json()["grammar"] == "negacio, aorist-ad"
    assert client.get(f"/drills/{c['id']}").json()["grammar"] is None
    counts = client.get("/grammar").json()["counts"]
    assert counts["negacio"] >= 1 and counts["possessius"] >= 1
    # the unit page: the lesson is steps with the library's examples attached, written once (kept in the DB)
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "_load_grammar", lambda: "## 7. Sintaxi\n7.2.1. La partícula negativa\nLa negació es fa amb ur.\n7.2.2. La negació discontínua\n...\n7.3. L'oració interrogativa\n")
    calls = []
    answer = __import__("json").dumps({"intro": "Sabràs dir que no.", "steps": [
        {"type": "explain", "title": "La paraula ur", "text": "Per dir que no, poses **ur** davant del verb.", "example_ids": [a["id"], 999999], "focus": {str(a["id"]): "ur rad", "999999": "x"}},
        {"type": "explain", "title": "Amb el futur", "text": "Amb ad també.", "example_ids": [a["id"]]},
        {"type": "pattern", "title": "Formes", "rows": [["ur", "no", "ur rad dduɣ"]]},
        {"type": "tip", "text": "No oblidis ur."}, {"type": "dialect", "text": "A Beni Mellal s'hi afegeix ša."}]})
    sheet = "1. RULES: ur davant del verb."
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda sys_, contents, **k: calls.append(contents[0]["text"]) or (sheet if "STUDY SHEET in" in contents[0]["text"] else answer))
    # What is being tested is the FIRST open of a unit, so the unit has to have no lesson yet:
    # another test may have written this one already, and then the page quite rightly serves it (#191).
    from models import GrammarLesson
    db = main.SessionLocal()
    db.query(GrammarLesson).filter(GrammarLesson.id.in_(("negacio", "negacio:deep"))).delete(synchronize_session=False)
    db.commit(); db.close()

    page = client.get("/grammar/negacio").json()
    assert page["title"].startswith("La negació") and page["total"] >= 1
    assert page["lesson"]["writing"] and page["lesson"]["steps"][-1]["type"] == "end"  # never a wait for Gemini
    lesson = _wait_lesson("negacio")
    kinds = [s["type"] for s in lesson["steps"]]
    assert lesson["intro"] == "Sabràs dir que no." and kinds[:2] == ["explain", "explain"] and kinds[-1] == "end"
    assert lesson["steps"][0]["examples"] == [lesson["steps"][0]["examples"][0]] and lesson["steps"][0]["examples"][0]["id"] == a["id"]
    assert lesson["steps"][0]["examples"][0]["audio_url"] == "https://example.test/a.webm"  # the drill's media travel with the step
    assert lesson["steps"][0]["examples"][0]["focus"] == "ur rad"  # the piece of OUR sentence that shows the rule
    assert "pattern" in kinds and "tip" in kinds and "dialect" in kinds
    # two passes: the study sheet reads only the unit's sections; the lesson gets the sheet and our sentences
    assert len(calls) == 2 and "7.2.1. La partícula negativa" in calls[0] and "7.3. L'oració" not in calls[0]
    assert "ur rad dduɣ" in calls[1] and sheet in calls[1] and lesson["study"] == sheet
    assert page["drills"][0]["id"] == a["id"]
    assert client.get("/grammar/negacio").json()["lesson"]["intro"] == "Sabràs dir que no."  # kept, and now served at once
    assert len(calls) == 2  # written once, kept in the grammar_lessons table
    assert client.get("/grammar/no-such-unit").status_code == 404
    assert client.post("/grammar/run").status_code in (401, 403)  # admin only
    assert client.post("/grammar/negacio/rewrite").status_code in (401, 403)


def test_the_wishlist_asks_for_the_sentences_the_lesson_shows(monkeypatch):
    """Recording a sentence the course quotes changes what a learner hears; recording any other
    sentence of the unit does not."""
    import json as _json, main as _main
    from models import GrammarLesson
    quoted = client.post("/drills/", json={"text_catalan": "No ho sé", "text_tachelhit": "ur ssinɣ", "tag": "benimellal-anki"}).json()
    other = client.post("/drills/", json={"text_catalan": "No hi és", "text_tachelhit": "ur illi", "tag": "benimellal-anki"}).json()
    for d in (quoted, other):
        client.put(f"/drills/{d['id']}", json={"grammar": "negacio", "grammar_source": "owner"})
    with _main.SessionLocal() as db:
        body = _json.dumps({"intro": "", "steps": [{"type": "explain", "title": "ur", "text": "x",
                                                    "examples": [{"id": quoted["id"], "shi": "ur ssinɣ", "ca": "No ho sé"}]}]})
        row = db.query(GrammarLesson).filter(GrammarLesson.id == "negacio").first()
        if row is None:
            db.add(GrammarLesson(id="negacio", body=body, version=grammar.LESSON_VERSION))
        else:
            row.body = body
        db.commit()
    unit = next(u for u in client.get("/grammar/wishlist").json()["units"] if u["slug"] == "negacio")
    ids = [d["id"] for d in unit["wanted"]]
    assert ids and ids[0] == quoted["id"] and unit["in_lesson"] >= 1
    assert ids.index(quoted["id"]) < (ids.index(other["id"]) if other["id"] in ids else 99)


def test_practice_is_sentences_only_and_wishlist_names_what_our_speakers_could_record(monkeypatch):
    import grammar
    assert [grammar.kind(t) for t in ("ur ssinɣ", "argaz", "rix, trid, iri, nri", "text", "", "ad // rad")] == ["sentence", "word", "list", "placeholder", "placeholder", "list"]
    word = client.post("/drills/", json={"text_catalan": "pa", "text_tachelhit": "aɣrum", "tag": "benimellal-anki"}).json()
    lst = client.post("/drills/", json={"text_catalan": "voler", "text_tachelhit": "rix, trid, iri, nri"}).json()
    sent = client.post("/drills/", json={"text_catalan": "vull pa", "text_tachelhit": "rix aɣrum", "tag": "benimellal-anki", "image_url": "https://x/i.jpg"}).json()
    ours = client.post("/drills/", json={"text_catalan": "vull aigua", "text_tachelhit": "rix aman", "author": "Halima", "audio_url": "https://x/h.webm"}).json()
    for d in (word, lst, sent, ours):
        client.put(f"/drills/{d['id']}", json={"grammar": "aorist-ad", "grammar_source": "owner"})
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *x, **k: '{"intro": "x", "steps": [{"type": "explain", "title": "t", "text": "t", "example_ids": []}]}')
    page = client.get("/grammar/aorist-ad").json()
    # the test is made of real sentences only; the unit page still lists everything
    assert {sent["id"], ours["id"]} <= set(page["practice"]) and not {word["id"], lst["id"]} & set(page["practice"])
    assert {d["id"] for d in page["drills"]} >= {word["id"], lst["id"], sent["id"], ours["id"]}
    # the wishlist: the unit's Aït Mraw voices, and the sentences from elsewhere worth recording (pictured first)
    w = client.get("/grammar/wishlist").json()["units"]
    u = next(x for x in w if x["slug"] == "aorist-ad")
    other = client.post("/drills/", json={"text_catalan": "vull te", "text_tachelhit": "rix atay", "image_url": "https://x/t.jpg", "audio_url": "https://x/t.webm"}).json()
    client.put(f"/drills/{other['id']}", json={"grammar": "aorist-ad", "grammar_source": "owner"})
    wanted = [d["id"] for d in next(x for x in client.get("/grammar/wishlist").json()["units"] if x["slug"] == "aorist-ad")["wanted"]]
    assert other["id"] in wanted
    # the deck's sentence before a pictured-and-voiced one from elsewhere. Relative, not first in
    # the list: the sentences a lesson quotes are ranked ahead, and other tests leave lessons behind
    assert u["aitmraw_voiced"] == 1 and wanted.index(sent["id"]) < wanted.index(other["id"])
    assert not {ours["id"], word["id"], lst["id"]} & set(wanted)
    assert [x["aitmraw_voiced"] for x in w] == sorted(x["aitmraw_voiced"] for x in w)  # the units lacking voices first
    # a lesson whose quoted sentence leaves the unit is written again; one still quoting the unit is kept
    assert grammar.quoted_ids({"steps": [{"type": "explain", "examples": [{"id": 5}]}, {"type": "quiz", "example": {"id": 7}}]}) == {5, 7}
    class Row:  # noqa
        version = grammar.LESSON_VERSION; body = __import__("json").dumps({"steps": [{"type": "explain", "examples": [{"id": 5}]}]})
    assert grammar._current(Row(), {5, 6}) is None and grammar._current(Row(), {6}) is None and grammar._current(Row(), None) is not None  # no unit_size yet: written again once
    # a unit that grew by 30% (and 5 drills) since the lesson was written gets it written again
    class Grown:  # noqa
        version = grammar.LESSON_VERSION; body = __import__("json").dumps({"unit_size": 10, "steps": [{"type": "explain", "examples": [{"id": 5}]}]})
    assert grammar._current(Grown(), set(range(5, 17))) is not None  # 12 drills: +2, kept
    assert grammar._current(Grown(), set(range(5, 21))) is None       # 16 drills: +6, rewritten


def test_lessons_start_basic_and_skip_capture_artefacts():
    import grammar
    assert grammar.quotable("azul", "formules") and not grammar.quotable("azul", "perfectiu")  # a word only where the word is the point
    assert grammar.quotable("ur ssinɣ", "perfectiu") and not grammar.quotable("rix, trid, iri, nri", "formules")
    assert not grammar.quotable("ⵜ.ⵅⵙ.ⵛ ⵙⵙ ⵉⵙⵙ", "formules") and not grammar.quotable("ⴰⵣⵓⵍ", "formules")  # Tifinagh-only captures
    assert not grammar.quotable("a.z.ul fllawn", "formules")  # dots inside words
    class R:  # noqa
        def __init__(self, id, shi, ca): self.id, self.text_tachelhit, self.text_catalan, self.image_url, self.audio_url, self.author, self.region, self.tag = id, shi, ca, None, None, None, None, None
    rows = [R(1, "jigh labas, tanmmirt", "estic bé, gràcies"), R(2, "azul", "hola"), R(3, "ⵜ.ⵅⵙ.ⵛ ⵙⵙ", "hola, encàrrec'm")]
    ex = grammar.pick_examples(rows, slug="formules")
    assert [e["id"] for e in ex] == [2, 1] and [e["id"] for e in grammar.pick_examples(rows, slug="negacio")] == [1]  # shortest first
    assert [d.id for d in grammar.practice_rows(rows, slug="formules")] == [1, 2]
    unit = next(u for u in grammar.UNITS if u["slug"] == "formules")
    p = grammar._lesson_prompt(unit, ex, "sheet")
    assert p.index("«azul»") < p.index("«jigh labas") and "START WITH THE MOST BASIC" in p  # the writer sees the basics first


def test_level_one_units_quote_only_short_examples():
    import grammar
    class R:  # noqa
        def __init__(self, id, shi, ca): self.id, self.text_tachelhit, self.text_catalan, self.image_url, self.audio_url, self.author, self.region, self.tag = id, shi, ca, None, None, None, None, None
    long = R(1, "waxxa, isul-yan g-usawn n-tuwrirt-in", "D'acord, encara n'hi ha una al vessant")
    rows = [long, R(2, "3afaš", "gràcies"), R(3, "Adeu", "Adeu"), R(4, "jigh labas, tanmmirt", "estic bé, gràcies")]
    assert [e["id"] for e in grammar.pick_examples(rows, slug="formules")] == [2, 4]  # level 1: a few words; «Adeu»=«Adeu» never
    assert [e["id"] for e in grammar.pick_examples(rows, slug="subordinades")] == [4, 1]  # level 3: the long one is fine, last
    assert grammar.fits_level("ur ssinɣ ša", "formules") and not grammar.fits_level("a b c d e", "formules") and grammar.fits_level("a b c d e", "negacio")
    assert not grammar.fits_level("tex", "formules", "Quan era petit els meus pares van anar a viure a la ciutat")  # a long meaning is not level 1 either
    unit = next(u for u in grammar.UNITS if u["slug"] == "formules")
    assert "LEVEL 1 UNIT" in grammar._lesson_prompt(unit, [], "sheet")
    assert "LEVEL 1 UNIT" not in grammar._lesson_prompt(next(u for u in grammar.UNITS if u["slug"] == "negacio"), [], "sheet")


def test_classifier_may_find_no_unit(monkeypatch):
    import grammar, json
    d = client.post("/drills/", json={"text_catalan": "sí", "text_tachelhit": "wayh"}).json()
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda *x, **k: json.dumps({str(d["id"]): []}))
    assert grammar.run(main.SessionLocal, only_ids=[d["id"]])["done"] == 1
    assert client.get(f"/drills/{d['id']}").json()["grammar"] == grammar.NO_UNIT and grammar.parse(grammar.NO_UNIT) == []
    assert "ONLY a real command" in grammar._prompt([]) and "EMPTY" in grammar._prompt([])


def test_lesson_prose_has_no_tifinagh_and_examples_have_no_capture_noise():
    import grammar
    assert grammar._clean_prose("sovint es fa servir el verb \u2d45 g") == "sovint es fa servir el verb g"
    assert grammar._clean_prose("la forma \u00abell \u00e9s\u00bb \u00e9s \u2d44\u2d45\u00b0 iga.") == "la forma \u00abell \u00e9s\u00bb \u00e9s iga."
    assert not grammar.quotable("Mana Lun ija +tEli", "ser-tenir")  # a capture artefact is never an example
    assert grammar.quotable("iga argaz", "ser-tenir")
    unit = next(u for u in grammar.UNITS if u["slug"] == "ser-tenir")
    p = grammar._lesson_prompt(unit, [], "sheet")
    assert "example_ids (4-6" in p and "focus must be the rule itself" in p
    assert "fewer than seven is not acceptable" in p  # the lesson must cover the whole point


def test_lesson_prose_is_latin_only_and_never_cites_ids():
    import grammar
    assert grammar._clean_prose("Pots dir 'marhaba' (مرحبا), que vol dir benvingut.") == "Pots dir 'marhaba', que vol dir benvingut."
    assert grammar._clean_prose("Ho fan servir, com es veu en els exemples 5813 i 5914. També 'waxxa' (exemple 5863).") == "Ho fan servir, com es veu. També 'waxxa'."


def test_lesson_json_tolerates_trailing_commas():
    import grammar
    ex = [{"id": 1, "shi": "ur ssinɣ", "ca": "no ho sé", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None}]
    lesson = grammar._parse_lesson('{"intro": "x", "steps": [{"type": "explain", "title": "t", "text": "ur davant.", "example_ids": [1,],},],}', ex)
    assert lesson["steps"][0]["examples"][0]["id"] == 1


def test_the_lesson_never_uses_a_word_a_beginner_would_look_up():
    import grammar
    assert grammar._clean_prose("el tema d'inacomplert") == "el tema d'inacabat"
    assert grammar._clean_prose("els clítics van davant") == "els pronoms enganxats al verb van davant"
    assert grammar._clean_prose("un díctic marca el lloc") == "un mot que assenyala marca el lloc"
    for w in ("inacomplert", "clítics", "díctic", "morfema", "lexema", "sintagma"):
        assert w not in grammar._clean_prose(f"text amb {w} dins").lower()


def test_an_explanation_never_shows_fewer_than_four_sentences():
    """The writer quotes three; the library has thirty more that carry the same piece."""
    import grammar, json as _json
    ex = [{"id": 1, "shi": "ɣur-i yat", "ca": "en tinc una", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None, "origin": ""},
          {"id": 2, "shi": "ghori tigmmi", "ca": "tinc una casa", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None, "origin": ""},
          {"id": 3, "shi": "ɣur-i aman", "ca": "tinc aigua", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None, "origin": ""},
          {"id": 4, "shi": "ur ɣur-i walu", "ca": "no tinc res", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None, "origin": ""},
          {"id": 5, "shi": "izri wass", "ca": "el dia ha passat", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None, "origin": ""}]
    answer = _json.dumps({"intro": "x", "steps": [{"type": "explain", "title": "ɣur-i", "text": "Per dir que tens una cosa.",
                                                   "example_ids": [1], "focus": {"1": "ɣur-i"}}]})
    lesson = grammar._parse_lesson(answer, ex)
    got = [e["id"] for e in lesson["steps"][0]["examples"]]
    assert got[0] == 1 and len(got) == 4 and 5 not in got  # «izri wass» does not carry the rule
    assert 2 in got  # «ghori», the same word spelled another way, does
    assert lesson["steps"][0]["examples"][2]["focus"] == "ɣur-i"  # the piece is marked where it is written
    marked = {e["id"]: e.get("focus") for e in lesson["steps"][0]["examples"]}
    assert marked[2] == "ghori"  # another spelling of the same word is marked as the speaker wrote it
    assert grammar._mark("hla ghori udghar", "ɣur-i") == "ghori" and grammar._mark("izri wass", "ɣur-i") is None


def test_conjugation_lists_become_the_lessons_tables():
    """The deck wrote out 299 paradigms; they are no example, but they are what a table is made of."""
    import grammar
    class R:  # noqa
        def __init__(self, id, shi, ca): self.id, self.text_tachelhit, self.text_catalan = id, shi, ca
    rows = [R(1, "rgl, rglkh, trgld, irgl, nrgl, trglm(t), rgln(t)", "tancar"),
            R(2, "adhadh / idhudhan afus / ifasn", "dit / dits mà / mans"), R(3, "ur rgliɣ", "no he tancat")]
    tables = grammar.paradigms(rows)
    assert [t["id"] for t in tables] == [1, 2]  # the fullest list first, and never the sentence
    assert not any(t["id"] == 3 for t in tables)
    unit = next(u for u in grammar.UNITS if u["slug"] == "perfectiu")
    p = grammar._lesson_prompt(unit, [], "sheet", tables)
    assert "OUR LISTS" in p and "trglm(t)" in p and "build the table from THEM" in p  # the writer is told to copy the forms
    assert "OUR LISTS" not in grammar._lesson_prompt(unit, [], "sheet", [])


def test_every_deck_reaches_the_examples():
    """A unit with hundreds of Aït Mraw sentences used to hide the Beni Mellal deck completely."""
    import grammar
    class R:  # noqa
        def __init__(self, id, shi, ca, tag=None, author=None):
            self.id, self.text_tachelhit, self.text_catalan, self.tag, self.author = id, shi, ca, tag, author
            self.image_url = self.audio_url = self.region = None
    words = ["aman", "argaz", "tamghart", "afus", "ixf", "tigmmi", "ighrm", "amud", "izm", "ul",
             "akal", "tafukt", "ayyur", "itri", "adrar", "asif", "tazart", "agharas", "ikchm", "afullus"]
    rows = [R(i, f"ur ɣriɣ {words[i % 20]} {i}", f"no he llegit {i}", author="Halima") for i in range(1, 200)]
    rows += [R(1000 + i, f"ur ufiɣ {words[i % 20]} {i} walu", f"no he trobat {i}", tag="benimellal-anki, private") for i in range(1, 200)]
    rows += [R(2000 + i, f"ur sawlɣ {words[i % 20]} {i} ša", f"no he parlat {i}") for i in range(1, 60)]
    picked = grammar.pick_examples(rows, slug="negacio")
    by_source = [sum(1 for e in picked if grammar.origin_rank(e) == r) for r in (0, 1, 2)]
    assert all(n >= 15 for n in by_source), by_source  # all three decks, every time
    assert len({e["shi"].lower() for e in picked}) == len(picked)  # and no sentence twice


def test_a_quick_check_after_every_explanation_and_a_review_at_the_end():
    import grammar
    ex = [{"id": i, "shi": f"frase {i}", "ca": f"sentit {i}", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None} for i in range(1, 16)]
    steps = [{"type": "explain", "title": f"t{i}", "text": "x", "examples": [ex[i]]} for i in range(5)]
    lesson = grammar._with_quizzes({"intro": "", "steps": steps}, ex)
    kinds = [s["type"] for s in lesson["steps"]]
    assert kinds.count("quiz") >= 7  # one per explanation plus the review
    assert kinds[-1] == "end" and kinds[-2] == "quiz"
    asked = [s["example"]["id"] for s in lesson["steps"] if s["type"] == "quiz"]
    assert len(asked) == len(set(asked))  # never the same sentence twice
    assert sum(1 for s in lesson["steps"] if s["type"] == "quiz" and s["question"].startswith("Repàs")) == 3


def test_quizzes_and_excluded_language(monkeypatch):
    import grammar
    ex = [{"id": i, "shi": f"frase {i}", "ca": f"sentit {i}", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None} for i in range(1, 7)]
    lesson = grammar._with_quizzes({"intro": "", "steps": [
        {"type": "explain", "title": "u", "text": "t", "examples": [ex[0]]}, {"type": "explain", "title": "d", "text": "t", "examples": [ex[1]]},
        {"type": "explain", "title": "t", "text": "t", "examples": []}, {"type": "explain", "title": "q", "text": "t", "examples": [ex[2]]}]}, ex)
    quizzes = [s for s in lesson["steps"] if s["type"] == "quiz"]
    assert len(quizzes) > 4 and lesson["steps"][-1]["type"] == "end"  # one per explanation, plus the review
    q = quizzes[0]
    assert q["kind"] == "meaning" and q["example"]["id"] == 1 and len(q["options"]) == 4 and q["options"][q["answer"]] == "frase 1" and q["question"] == "Com es diu «sentit 1»?"
    assert quizzes[1]["kind"] == "meaning"  # no voice in this pool: the listening check falls back to reading
    voiced = [{**e, "audio_url": "https://x/a.webm",
               "image_url": f"https://res.cloudinary.com/du26ppvh0/image/upload/v1/tachelhit/illustrations/ill_{e['id']}.webp"} for e in ex]
    lesson = grammar._with_quizzes({"intro": "", "steps": [{"type": "explain", "title": "u", "text": "t", "examples": [voiced[0]]}] * 6}, voiced)
    kinds = [(s["kind"], s["options"][s["answer"]]) for s in lesson["steps"] if s["type"] == "quiz"]
    assert [k for k, _ in kinds] == ["meaning", "listen", "picture", "meaning", "listen", "picture"]
    assert kinds[1][1].startswith("sentit") and kinds[2][1].startswith("frase")  # listening: pick the meaning; picture: pick the sentence
    # i una imatge TROBADA per la xarxa no fa cap pregunta: il·lustra com a molt una paraula, i
    # com a enunciat no es pot contestar («ɣuri … / dari …» amb una estàtua d'un casino de Macau)
    found = [{**e, "audio_url": "https://x/a.webm", "image_url": "https://thumb.wikimedia.org/x/golden_statue.jpg"} for e in ex]
    lesson = grammar._with_quizzes({"intro": "", "steps": [{"type": "explain", "title": "u", "text": "t", "examples": [found[0]]}] * 6}, found)
    assert "picture" not in [s["kind"] for s in lesson["steps"] if s["type"] == "quiz"]
    assert grammar.our_picture("https://res.cloudinary.com/du26ppvh0/image/upload/v1/x.webp")
    assert not grammar.our_picture("https://thumb.wikimedia.org/x.jpg") and not grammar.our_picture(None)
    # i un motlle no és una frase: no es pot ni dir ni endevinar
    assert not grammar.well_formed("ɣuri … / dari …") and not grammar.well_formed("ɣuri ... / dari ...")
    twin = ex + [{**ex[0], "id": 9, "shi": "una altra frase", "ca": "sentit 2"}]  # same meaning: never a wrong answer
    lesson = grammar._with_quizzes({"intro": "", "steps": [{"type": "explain", "title": "u", "text": "t", "examples": []}, {"type": "explain", "title": "d", "text": "t", "examples": [ex[1]]}]}, twin)
    asked = next(s for s in lesson["steps"] if s["type"] == "quiz" and s["example"]["id"] == 2)
    assert "una altra frase" not in asked["options"]
    # an Irish test drill never enters the course, even when it carries a unit
    irish = client.post("/drills/", json={"text_catalan": "Bon dia", "text_tachelhit": "Maidin Mhaith", "tag": "Irish"}).json()
    client.put(f"/drills/{irish['id']}", json={"grammar": "formules", "grammar_source": "owner"})
    assert not any(s["type"] == "quiz" for s in client.get("/grammar/formules").json()["lesson"]["steps"] if "Maidin" in str(s))
    assert all(d["id"] != irish["id"] for d in client.get("/grammar/formules").json()["drills"])
    # conjugation lists and placeholders are not quotable examples
    class R:  # noqa
        def __init__(self, id, shi, ca): self.id, self.text_tachelhit, self.text_catalan, self.image_url, self.audio_url, self.author, self.region, self.tag = id, shi, ca, None, None, None, None, None
    picked = grammar.pick_examples([R(1, "rix, trid, iri, nri", "voler"), R(2, "text", "x"), R(3, "ur ssinɣ", "no ho sé"), R(4, "UR SSINƔ", "no ho sé (bis)")])
    assert [e["id"] for e in picked] == [3]
    # our speakers from Aït Mraw come first, then the Beni Mellal deck, then the rest
    h = R(5, "ur ssinx", "no sé"); h.author = "Halima"
    b = R(6, "ur ssinɣ ša", "no sé pas"); b.tag = "benimellal-anki, private"
    o = R(7, "ur ssin", "no sap"); o.audio_url = "https://x/a.webm"
    assert [e["id"] for e in grammar.pick_examples([o, b, h])] == [5, 6, 7]
    assert grammar.pick_examples([h])[0]["origin"] == grammar.AIT_MRAW
    t = R(8, "ur ssinx", "no sé"); t.tag = "frase, Driss"  # the owner tags Driss's recordings by name
    assert grammar.our_speaker(t) == "Driss" and grammar.origin(t) == grammar.AIT_MRAW and grammar.our_speaker(o) is None


def test_the_lesson_shows_the_library_word_by_word():
    """The glosses are written once for the whole library; a lesson must show them without a call,
    and a gloss that improves must reach a lesson already written."""
    import grammar

    class R:  # noqa
        def __init__(self, id, shi, ca, glosses=None):
            self.id, self.text_tachelhit, self.text_catalan, self.glosses = id, shi, ca, glosses
            self.image_url = self.audio_url = self.region = self.author = self.tag = None

    good = '[{"shi": "ad", "tif": null, "ca": "part\u00edcula de futur"}, {"shi": "ddu\u0263", "tif": null, "ca": "anir\u00e9"}]'
    noise = '[{"shi": "ad", "ca": "ad"}, {"shi": "?", "ca": "?"}, {"shi": "ddu\u0263", "ca": "anir\u00e9"}]'
    assert [g["ca"] for g in grammar.gloss_of(R(1, "ad dduɣ", "hi anire", good))] == ["partícula de futur", "aniré"]
    assert [g["shi"] for g in grammar.gloss_of(R(2, "ad dduɣ", "hi anire", noise))] == ["dduɣ"]  # the parrot and the «?» are not shown
    assert grammar.gloss_of(R(3, "ad dduɣ", "hi anire", None)) is None
    assert grammar.gloss_of(R(4, "ad dduɣ", "hi anire", "not json")) is None

    e = grammar.example_dict(R(5, "ad dduɣ", "hi aniré", good))
    assert {k: e["gloss"][0][k] for k in ("shi", "ca")} == {"shi": "ad", "ca": "partícula de futur"}

    kept = {"intro": "", "steps": [
        {"type": "explain", "title": "t", "text": "x", "examples": [{"id": 5, "shi": "ad dduɣ", "ca": "hi aniré"}]},
        {"type": "quiz", "kind": "meaning", "question": "q", "options": ["a"], "answer": 0,
         "example": {"id": 5, "shi": "ad dduɣ", "ca": "hi aniré"}},
        {"type": "end"}]}
    fresh = grammar._with_glosses(kept, [e])
    assert fresh["steps"][0]["examples"][0]["gloss"][1]["ca"] == "aniré"
    assert fresh["steps"][1]["example"]["gloss"][0]["ca"] == "partícula de futur"


def test_a_thin_step_is_filled_with_kin_and_never_with_decoys():
    """When the piece taught is spelt that way nowhere else, the step takes the unit's sentences
    that share a word with it AND that the library can say something about — and nothing else: a
    lone example beats four the learner cannot place."""
    import grammar, json as _json
    def e(i, shi, ca):
        return {"id": i, "shi": shi, "ca": ca, "image_url": None, "audio_url": None, "recorded": False,
                "author": None, "region": None, "origin": ""}
    ex = [e(1, "tigmmi-nu", "la meva casa"), e(2, "tigmmi-nk", "la teva casa"),
          e(3, "tigmmi ixatr", "la casa es gran"), e(4, "wa d tigmmi", "aquesta es la casa"),
          e(5, "izri wass", "el dia ha passat"), e(6, "ssbah lxir", "bon dia")]
    answer = _json.dumps({"intro": "x", "steps": [{"type": "explain", "title": "-nu", "text": "El meu.",
                                                   "example_ids": [1], "focus": {"1": "-nu"}}]})
    notes = {2: "«-nk» és el teu.", 3: "Aquí «tigmmi» va sola.", 4: "«wa» assenyala la casa.",
             5: "Res a veure.", 6: "Res a veure."}
    got = [x["id"] for x in grammar._parse_lesson(answer, ex, notes)["steps"][0]["examples"]]
    assert got[0] == 1 and len(got) == 4           # one example is no explanation
    assert set(got) == {1, 2, 3, 4}                # the sentences about a house, nearest first
    assert 5 not in got and 6 not in got           # the day and the greeting share no word

    alone = _json.dumps({"intro": "x", "steps": [{"type": "explain", "title": "t", "text": "x",
                                                  "example_ids": [5], "focus": {"5": "izri"}}]})
    kept = grammar._parse_lesson(alone, [ex[4], ex[5]])["steps"][0]["examples"]
    assert [x["id"] for x in kept] == [5]          # nothing is kin: left short rather than padded


def test_an_ending_is_marked_where_it_is_written():
    """The writer marks an ending «-an», the way an ending is written; the old matcher took only a
    literal piece, so the mark vanished and the learner saw a bare word under the rule."""
    import grammar
    assert grammar._mark("šan", "-an") == "an"
    assert grammar._mark("sġan", "-an") == "an"
    assert grammar._mark("nša", "-n") == "n"
    assert grammar._mark("da trsamgh", "da-") == "da"      # a particle is written with the hyphen after
    assert grammar._mark("ssbbat", "ss-") == "ss"
    assert grammar._mark("izri wass", "-an") is None       # never a mark where the piece is not
    assert grammar._mark("tigmmi-nu", "-nu") == "-nu"      # a piece written with its hyphen still wins


def test_a_sentence_with_nothing_marked_and_nothing_said_is_not_shown():
    """Filling a short step with kin sentences may only add a sentence the learner can read: one
    with the piece marked, or one the library can say something about."""
    import grammar, json as _json
    def e(i, shi, ca):
        return {"id": i, "shi": shi, "ca": ca, "image_url": None, "audio_url": None, "recorded": False,
                "author": None, "region": None, "origin": ""}
    ex = [e(1, "tigmmi-nu", "la meva casa"), e(2, "tigmmi ixatr", "la casa es gran"),
          e(3, "tigmmi n baba", "la casa del pare")]
    answer = _json.dumps({"intro": "x", "steps": [{"type": "explain", "title": "-nu", "text": "El meu.",
                                                   "example_ids": [1], "focus": {"1": "-nu"}}]})
    bare = grammar._parse_lesson(answer, ex)["steps"][0]["examples"]
    assert [x["id"] for x in bare] == [1]  # neither 2 nor 3 carries «-nu» and nothing is said of them
    with_notes = grammar._parse_lesson(answer, ex, {2: "Aquí «tigmmi» va sola, sense el possessiu."})
    got = with_notes["steps"][0]["examples"]
    assert [x["id"] for x in got] == [1, 2] and got[1]["why"].startswith("Aquí")


def test_why_this_sentence_is_here_is_kept_per_sentence_and_unit():
    """The note is stored per (sentence, unit) — the same sentence shows something different in
    another unit — and reaches a lesson already written, like the glosses do."""
    import grammar, main
    db = main.SessionLocal()
    try:
        grammar.store_notes(db, "possessius", {77: "«-nu» diu que la casa és meva.", 78: grammar.NO_NOTE})
        grammar.store_notes(db, "noms-genere-nombre", {77: "«tigmmi» és un nom femení."})
        assert grammar.notes_for(db, "possessius") == {77: "«-nu» diu que la casa és meva."}  # NO_NOTE hidden
        assert grammar.notes_for(db, "noms-genere-nombre")[77].startswith("«tigmmi»")
        assert grammar.asked_notes(db, "possessius") == {77, 78}  # asked, so never asked again
        grammar.store_notes(db, "possessius", {77: "Millor dit: «-nu» és el meu."})
        assert grammar.notes_for(db, "possessius")[77].startswith("Millor dit")
    finally:
        db.close()

    kept = {"intro": "", "steps": [
        {"type": "explain", "title": "t", "text": "x", "examples": [{"id": 77, "shi": "tigmmi-nu", "ca": "la meva casa"}]},
        {"type": "quiz", "kind": "meaning", "question": "q", "options": ["a"], "answer": 0,
         "example": {"id": 77, "shi": "tigmmi-nu", "ca": "la meva casa"}},
        {"type": "end"}]}
    fresh = grammar._with_notes(kept, {77: "«-nu» diu que la casa és meva."})
    assert fresh["steps"][0]["examples"][0]["why"].startswith("«-nu»")
    assert fresh["steps"][1]["example"]["why"].startswith("«-nu»")


def test_the_second_level_asks_for_more_and_quotes_what_the_first_left():
    """«A fons» is the same unit taken further: more steps, and the sentences the first lesson does
    not use come first, so the two levels do not teach with the same examples."""
    import grammar
    unit = next(u for u in grammar.UNITS if u["slug"] == "possessius")
    ex = [{"id": i, "shi": f"frase {i}", "ca": f"sentit {i}", "origin": "Beni Mellal", "recorded": False} for i in range(1, 6)]
    base = grammar._lesson_prompt(unit, ex, "FULL")
    deep = grammar._lesson_prompt(unit, ex, "FULL", deep=True)
    assert "7 to 9 steps" in base and "SECOND LEVEL" not in base
    assert "10 to 14 steps" in deep and "SECOND LEVEL" in deep and "7 to 9 steps" not in deep
    assert 'Answer ONLY with a JSON object' in deep and '"dialect"' in deep
    assert grammar._row_id("possessius") == "possessius"
    assert grammar._row_id("possessius", deep=True) == "deep:possessius"


def test_the_second_level_leaves_the_first_lesson_alone():
    """Writing «a fons» must not touch the lesson the unit opens with: different row, own version."""
    import grammar, main
    db = main.SessionLocal()
    try:
        grammar._store_lesson(db, "numerals", {"intro": "la primera", "steps": [{"type": "end"}]})
        grammar._store_lesson(db, "numerals", {"intro": "a fons", "steps": [{"type": "end"}]}, deep=True)
        from models import GrammarLesson
        rows = {r.id: r for r in db.query(GrammarLesson).filter(GrammarLesson.id.in_(["numerals", "deep:numerals"])).all()}
        assert json.loads(rows["numerals"].body)["intro"] == "la primera"
        assert json.loads(rows["deep:numerals"].body)["intro"] == "a fons"
        assert rows["numerals"].version == grammar.LESSON_VERSION and rows["deep:numerals"].version == grammar.DEEP_VERSION
    finally:
        db.close()


def test_the_wrong_answers_can_pass_for_the_right_one():
    """A one-word answer among three long sentences gives itself away by its shape, and the four
    together read as nonsense: «tu (masc.)» next to «Menjo el dinar» is not a question."""
    import grammar
    def e(i, shi, ca, audio=True):
        return {"id": i, "shi": shi, "ca": ca, "image_url": None, "audio_url": "u" if audio else None,
                "recorded": audio, "author": None, "region": None, "origin": ""}
    pool = [e(1, "kyy", "tu (masc.)"), e(2, "kmm", "tu (fem.)"), e(3, "nkk", "jo"), e(4, "ntta", "ell"),
            e(5, "da ttɣ imkli", "Menjo el dinar"), e(6, "hak ad gan", "Així són ells."),
            e(7, "bla tili", "sense ombra"), e(8, "ur ssinɣ mani", "no sé on")]
    steps = [{"type": "explain", "title": "t", "text": "x", "examples": [pool[0]]}]
    lesson = grammar._with_quizzes({"intro": "", "steps": steps}, pool)
    quiz = next(s for s in lesson["steps"] if s["type"] == "quiz")
    field = "ca" if quiz["kind"] == "listen" else "shi"
    answer = quiz["example"][field]
    lengths = {grammar._words(o) for o in quiz["options"]}
    assert quiz["options"][quiz["answer"]] == answer
    assert max(lengths) - min(lengths) <= 1, quiz["options"]   # all of a kind: words with words
    assert len(set(quiz["options"])) == 4


def test_the_language_shows_its_own_script():
    """Tifinagh belongs with the sentence: under the speaker's own spelling and under each word of
    the word-by-word reading. The PROSE of a lesson stays in Latin — that rule does not change."""
    import grammar

    class D:  # noqa
        id, text_tachelhit, text_catalan = 7, "ɣur-i yat", "en tinc una"
        image_url = audio_url = author = region = tag = None
        glosses = '[{"shi": "\u0263ur-i", "tif": "\u2d96\u2d53\u2d54\u2d49", "ca": "tinc"}]'

    e = grammar.example_dict(D())
    assert e["tif"] and all("\u2d30" <= ch <= "\u2d7f" or ch == " " for ch in e["tif"])  # Tifinagh only
    assert e["gloss"][0]["tif"] == "\u2d96\u2d53\u2d54\u2d49"
    assert grammar.tifinagh("nkk") == "\u2d4f\u2d3d\u2d3d"
    assert grammar.tifinagh("") is None
    # the prose is still cleaned of it: an explanation a beginner reads stays in Latin
    assert grammar._clean_prose("El pronom \u2d4f\u2d3d\u2d3d vol dir jo").strip() == "El pronom vol dir jo"


def test_a_lesson_written_by_hand_is_never_overwritten_by_the_machine():
    """#187: lessons are written by Gemini and rewritten whenever the format version moves or the
    unit changes. That is right until somebody edits one — then a rewrite throws their work away.
    """
    import json
    import main
    import grammar
    from models import GrammarLesson
    from test_api import client, as_stranger, register

    slug = grammar.UNITS[0]["slug"]
    mine = {"X-User-Token": register("lesson_editor")}
    db = main.SessionLocal()
    me = db.query(main.UserModel).filter(main.UserModel.username == "lesson_editor").first()
    me.is_admin = True
    db.commit(); db.close()

    lesson = {"intro": "Una lliçó escrita a mà.", "steps": [
        {"type": "explain", "title": "El punt", "text": "Això ho ha escrit una persona."},
        {"type": "quiz", "question": "Quina és la bona?", "options": ["aquesta", "aquella"], "answer": 0},
        {"type": "end"},
    ]}
    r = client.put(f"/grammar/{slug}/lesson", headers=mine, json={"lesson": lesson})
    assert r.status_code == 200, r.text

    # the row says so, and the freshness check now always keeps it, whatever the version says
    db = main.SessionLocal()
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    assert row.hand_written is True
    row.version = 0            # as if the format had moved on without it
    db.commit()
    kept = grammar._current(row, unit_ids=None)
    assert kept and kept["intro"] == "Una lliçó escrita a mà."
    db.close()

    assert client.get(f"/grammar/{slug}/lesson").json()["hand_written"] is True

    # what the course cannot draw is refused, so a learner never meets a blank card
    bad = client.put(f"/grammar/{slug}/lesson", headers=mine,
                     json={"lesson": {"intro": "", "steps": [{"type": "cançó", "text": "x"}]}})
    assert bad.status_code == 400
    half = client.put(f"/grammar/{slug}/lesson", headers=mine, json={"lesson": {"intro": "", "steps": [
        {"type": "quiz", "question": "I la resposta?", "options": ["una"]}]}})
    assert half.status_code == 400

    # and it is an admin's doing, not anybody's
    with as_stranger():
        assert client.put(f"/grammar/{slug}/lesson", json={"lesson": lesson}).status_code == 401

    # handing it back to the machine makes it ordinary again
    assert client.post(f"/grammar/{slug}/lesson/release", headers=mine).status_code == 200
    db = main.SessionLocal()
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    assert not row.hand_written
    row.version = 0
    db.commit()
    assert grammar._current(row, unit_ids=None) is None   # out of date again, so it gets rewritten
    json.loads(row.body)
    db.close()


def test_una_fila_duna_taula_de_formes_es_pot_gravar():
    """Una taula de formes és on la gramàtica es veu d'un cop d'ull —ɣur-i, ɣur-k, ɣur-s— i era
    l'únic lloc de la lliçó que no es podia DIR. L'amo: «crec que aquí s'hauria de poder gravar
    la veu». La primera vegada, la fila es torna una frase de la biblioteca que demana veu; la
    segona, s'hi afegeix una veu en comptes de crear-ne una altra."""
    import json

    import main
    from models import GrammarLesson
    from test_api import client, register

    hdr = {"X-User-Token": register("taula_gravadora")}
    db = main.SessionLocal()
    try:
        db.add(GrammarLesson(id="ser-tenir", version=0, body=json.dumps({
            "intro": "", "steps": [
                {"type": "explain", "title": "u", "text": "t", "examples": []},
                {"type": "pattern", "title": "Formes de «tenir»",
                 "rows": [["ɣur-i", "tinc", "ɣur-i yan wuccn"], ["ɣur-k", "tens (home)", ""]]},
            ]}, ensure_ascii=False)))
        db.commit()
    finally:
        db.close()

    r = client.post("/grammar/ser-tenir/row", headers=hdr, json={"step": 1, "row": 0})
    assert r.status_code == 200, r.text
    made = r.json()
    assert made["created"] is True
    d = made["drill"]
    assert d["text_tachelhit"] == "ɣur-i" and d["text_catalan"] == "tinc"
    assert d["voice_wanted"] is True, "neix demanant una veu"
    assert "taula de formes" in (d.get("tag") or ""), "diu d'on surt"
    assert "ser-tenir" in (d.get("grammar") or "")

    again = client.post("/grammar/ser-tenir/row", headers=hdr, json={"step": 1, "row": 0}).json()
    assert again["created"] is False and again["drill_id"] == made["drill_id"], "la segona vegada, una veu més"

    # i la lliçó se'n recorda, perquè el micròfon pugui canviar de color
    assert client.get("/grammar/ser-tenir/lesson", headers=hdr).json()["lesson"]["steps"][1]["drill_ids"]["0"] == made["drill_id"]

    # el que no és una taula, o una fila que no hi és, no fa res
    assert client.post("/grammar/ser-tenir/row", headers=hdr, json={"step": 0, "row": 0}).status_code == 400
    assert client.post("/grammar/ser-tenir/row", headers=hdr, json={"step": 1, "row": 9}).status_code == 400


def test_un_so_citat_porta_la_seva_tifinagh():
    """L'amo: «és important que fem servir la lletra tifinagh… la tifinagh ha de ser present a
    tot arreu, també al títol de l'explicació dels sons».

    Una lliçó que ensenya un so citant-lo en llatí ensenya el so i no ensenya la lletra. Ara, un
    so citat entre cometes porta la seva tifinagh al costat, al títol i al text.

    El que NO fa: penjar una tifinagh a una paraula catalana citada. Un so és una lletra sola o
    un dels parells que la llengua escriu junts; «fer» i «cas» es queden com són."""
    import grammar

    assert grammar.with_letters('El so «3» o «ɛ»') == 'El so «3 ⵄ» o «ɛ ⵄ»'
    assert grammar.with_letters('la «gh» sona com la «ɣ»') == 'la «gh ⵖ» sona com la «ɣ ⵖ»'
    assert grammar.with_letters('Vol dir «fer», no «cas»') == 'Vol dir «fer», no «cas»'
    assert grammar.with_letters('ja porta ⵣ i «ɛ»') == 'ja porta ⵣ i «ɛ»', "si ja n'hi ha, no s'hi torna"
    assert grammar.with_letters('') == ''

    # i la lliçó servida la porta, encara que s'hagués escrit abans
    import json

    import main
    from models import GrammarLesson
    db = main.SessionLocal()
    try:
        row = db.query(GrammarLesson).filter(GrammarLesson.id == "sons-i-escriptura").first()
        if row is None:
            row = GrammarLesson(id="sons-i-escriptura", version=0, body="")
            db.add(row)
        row.hand_written = True
        row.body = json.dumps({"intro": "", "steps": [
            {"type": "explain", "title": 'El so «ɛ»', "text": 'La «ɛ» és faringi.', "examples": []},
            {"type": "end"}]}, ensure_ascii=False)
        db.commit()
    finally:
        db.close()
    step = client.get("/grammar/sons-i-escriptura").json()["lesson"]["steps"][0]
    assert step["title"] == 'El so «ɛ ⵄ»' and "ⵄ" in step["text"]
