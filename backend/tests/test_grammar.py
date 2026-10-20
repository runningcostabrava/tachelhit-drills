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
    # the unit page: lesson written once (cached), recorded examples first
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "_load_grammar", lambda: "## 5. Morfosintaxi verbal\nLa negació es fa amb ur.\n## 7. Sintaxi\n...")
    calls = []
    monkeypatch.setattr(gemini_client, "gemini_generate", lambda sys_, contents, **k: calls.append(contents[0]["text"]) or "# La negació\n\n**ur** nega el verb.\n- ur rad dduɣ — no hi aniré")
    monkeypatch.setattr(grammar, "UNITS_DIR", str(__import__("tempfile").mkdtemp()))
    page = client.get("/grammar/negacio").json()
    assert page["title"].startswith("La negació") and "ur" in page["lesson"] and page["total"] >= 1
    assert page["drills"][0]["id"] == a["id"] and "ur rad dduɣ" in calls[0] and "Morfosintaxi verbal" in calls[0]
    client.get("/grammar/negacio")
    assert len(calls) == 1  # cached on disk
    assert client.get("/grammar/no-such-unit").status_code == 404
    assert client.post("/grammar/run").status_code == 401  # admin only
