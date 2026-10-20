"""Grammar course: units, classification into units, the unit page with its lesson and examples."""
import grammar
import main
from test_api import client


def test_units_are_ordered_and_endpoint_lists_them():
    r = client.get("/grammar").json()
    assert [u["slug"] for u in r["units"]] == grammar.SLUGS and r["units"][0]["slug"] == "formules"
    assert set(r["counts"]) == set(grammar.SLUGS)


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
        {"type": "explain", "title": "La paraula ur", "text": "Per dir que no, poses **ur** davant del verb.", "example_ids": [a["id"], 999999]},
        {"type": "explain", "title": "Amb el futur", "text": "Amb ad també.", "example_ids": [a["id"]]},
        {"type": "pattern", "title": "Formes", "rows": [["ur", "no", "ur rad dduɣ"]]},
        {"type": "tip", "text": "No oblidis ur."}, {"type": "dialect", "text": "A Beni Mellal s'hi afegeix ša."}]})
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda sys_, contents, **k: calls.append(contents[0]["text"]) or answer)
    page = client.get("/grammar/negacio").json()
    assert page["title"].startswith("La negació") and page["total"] >= 1
    lesson = page["lesson"]
    kinds = [s["type"] for s in lesson["steps"]]
    assert lesson["intro"] == "Sabràs dir que no." and kinds[:2] == ["explain", "explain"] and kinds[-1] == "end"
    assert lesson["steps"][0]["examples"] == [lesson["steps"][0]["examples"][0]] and lesson["steps"][0]["examples"][0]["id"] == a["id"]
    assert lesson["steps"][0]["examples"][0]["audio_url"] == "https://example.test/a.webm"  # the drill's media travel with the step
    assert "pattern" in kinds and "tip" in kinds and "dialect" in kinds
    assert "ur rad dduɣ" in calls[0] and "7.2.1. La partícula negativa" in calls[0] and "7.3. L'oració" not in calls[0]  # only the unit's sections
    assert page["drills"][0]["id"] == a["id"]
    client.get("/grammar/negacio")
    assert len(calls) == 1  # written once, kept in the grammar_lessons table
    assert client.get("/grammar/no-such-unit").status_code == 404
    assert client.post("/grammar/run").status_code == 401  # admin only
    assert client.post("/grammar/negacio/rewrite").status_code == 401


def test_quizzes_and_excluded_language(monkeypatch):
    import grammar
    ex = [{"id": i, "shi": f"frase {i}", "ca": f"sentit {i}", "image_url": None, "audio_url": None, "recorded": False, "author": None, "region": None} for i in range(1, 7)]
    lesson = grammar._with_quizzes({"intro": "", "steps": [
        {"type": "explain", "title": "u", "text": "t", "examples": [ex[0]]}, {"type": "explain", "title": "d", "text": "t", "examples": [ex[1]]},
        {"type": "explain", "title": "t", "text": "t", "examples": []}, {"type": "explain", "title": "q", "text": "t", "examples": [ex[2]]}]}, ex)
    quizzes = [s for s in lesson["steps"] if s["type"] == "quiz"]
    assert len(quizzes) == 2 and lesson["steps"][-1]["type"] == "end"
    q = quizzes[0]
    assert q["example"]["id"] == 2 and len(q["options"]) == 4 and q["options"][q["answer"]] == "frase 2" and q["question"] == "Com es diu «sentit 2»?"
    twin = ex + [{**ex[0], "id": 9, "shi": "una altra frase", "ca": "sentit 2"}]  # same meaning: never a wrong answer
    lesson = grammar._with_quizzes({"intro": "", "steps": [{"type": "explain", "title": "u", "text": "t", "examples": []}, {"type": "explain", "title": "d", "text": "t", "examples": [ex[1]]}]}, twin)
    assert "una altra frase" not in next(s for s in lesson["steps"] if s["type"] == "quiz")["options"]
    # an Irish test drill never enters the course, even when it carries a unit
    irish = client.post("/drills/", json={"text_catalan": "Bon dia", "text_tachelhit": "Maidin Mhaith", "tag": "Irish"}).json()
    client.put(f"/drills/{irish['id']}", json={"grammar": "formules", "grammar_source": "owner"})
    assert not any(s["type"] == "quiz" for s in client.get("/grammar/formules").json()["lesson"]["steps"] if "Maidin" in str(s))
    assert all(d["id"] != irish["id"] for d in client.get("/grammar/formules").json()["drills"])
    # conjugation lists and placeholders are not quotable examples
    class R:  # noqa
        def __init__(self, id, shi, ca): self.id, self.text_tachelhit, self.text_catalan, self.image_url, self.audio_url, self.author, self.region = id, shi, ca, None, None, None, None
    picked = grammar.pick_examples([R(1, "rix, trid, iri, nri", "voler"), R(2, "text", "x"), R(3, "ur ssinɣ", "no ho sé"), R(4, "UR SSINƔ", "no ho sé (bis)")])
    assert [e["id"] for e in picked] == [3]
