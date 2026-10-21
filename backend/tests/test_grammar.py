"""Grammar course: units, classification into units, the unit page with its lesson and examples."""
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
    assert client.post("/grammar/run").status_code == 401  # admin only
    assert client.post("/grammar/negacio/rewrite").status_code == 401


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
    assert u["aitmraw_voiced"] == 1 and wanted[0] == sent["id"] and not {ours["id"], word["id"], lst["id"]} & set(wanted)  # the deck's sentence before a pictured-and-voiced one from elsewhere
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
    voiced = [{**e, "audio_url": "https://x/a.webm", "image_url": "https://x/i.jpg"} for e in ex]
    lesson = grammar._with_quizzes({"intro": "", "steps": [{"type": "explain", "title": "u", "text": "t", "examples": [voiced[0]]}] * 6}, voiced)
    kinds = [(s["kind"], s["options"][s["answer"]]) for s in lesson["steps"] if s["type"] == "quiz"]
    assert [k for k, _ in kinds] == ["meaning", "listen", "picture", "meaning", "listen", "picture"]
    assert kinds[1][1].startswith("sentit") and kinds[2][1].startswith("frase")  # listening: pick the meaning; picture: pick the sentence
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
