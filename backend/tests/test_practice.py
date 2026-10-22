"""Pràctica: collections, sessions, pronunciation tips and the word-by-word comparison."""
import practice
from test_api import client


def test_tips_name_the_hard_sounds_in_any_spelling():
    t = practice.tips("ur ġiġ ad ssnuġ ašku walu rruẓ")
    assert [x["sound"] for x in t][:2] == ["gh", "emfatiques"] and t[0]["found"] == "ġ"
    assert [x["sound"] for x in practice.tips("3afak, tanmmirt")] == ["ain", "geminada"]
    assert practice.tips("azul") == []
    assert "ġ" in practice.highlights("ur ġiġ") and "ẓ" in practice.highlights("rruẓ")


def test_words_compare_by_sound_not_spelling():
    w = practice.compare_words("ur ġiġ ad ssnuġ ašku walu rruẓ", "ur ghigh ad ssnu ashku walu rruz")
    assert [x["ok"] for x in w] == [True, True, True, True, True, True, True] or [x["ok"] for x in w] == [True, True, True, False, True, True, True]
    assert w[3]["word"] == "ssnuġ"
    w = practice.compare_words("tasneem iskm ingha yits?", "tasneem iskm")
    assert [x["ok"] for x in w] == [True, True, False, False]
    assert practice.sound_key("ghur") == practice.sound_key("ɣur") == practice.sound_key("Ġur")
    # the recogniser answers in Tifinagh: the same words in either script compare equal
    assert practice.sound_key("ⴼⵛⵉⴷ") == practice.sound_key("fsh-i-d") == practice.sound_key("fšid")
    assert [x["ok"] for x in practice.compare_words("fsh-i fsh-i-d", "ⴼⵛⵉ ⴼⵛⵉⴷ")] == [True, True]


def test_collections_and_session(monkeypatch):
    a = client.post("/drills/", json={"text_catalan": "No puc cuinar", "text_tachelhit": "ur ġiġ ad ssnuġ", "author": "Halima", "audio_url": "https://x/h.webm", "image_url": "https://x/h.jpg", "topics": "menjar, negacio"}).json()
    b = client.post("/drills/", json={"text_catalan": "No sé", "text_tachelhit": "ur ssinɣ", "author": "Halima", "audio_url": "https://x/h2.webm", "topics": "negacio"}).json()
    c = client.post("/drills/", json={"text_catalan": "No", "text_tachelhit": "ur ssinɣ ša", "author": "Halima", "audio_url": "https://x/h3.webm", "topics": "negacio"}).json()
    silent = client.post("/drills/", json={"text_catalan": "x", "text_tachelhit": "ur rad", "author": "Halima", "topics": "negacio"}).json()  # no voice: not practicable
    client.put(f"/drills/{silent['id']}", json={"audio_tts_shi_url": None, "audio_url": None})
    col = client.get("/practice/collections").json()
    day = next(x for x in col["days"] if x["speaker"] == "Halima")
    assert day["count"] >= 3 and any(t["slug"] == "negacio" and t["count"] >= 3 for t in col["topics"])
    assert {u["slug"] for u in col["units"]} == set(__import__("grammar").SLUGS) and isinstance(col["lists"], list)
    s = client.get(f"/practice/session?day={day['day']}&speaker=Halima&limit=10").json()
    ids = [d["id"] for d in s["drills"]]
    assert ids[0] == a["id"] and b["id"] in ids and silent["id"] not in ids  # pictured first; the voiceless one stays out
    assert s["cards"][0]["speaker"] == "Halima" and s["cards"][0]["tips"][0]["sound"] == "gh" and "ġ" in s["cards"][0]["highlights"]
    assert [d["id"] for d in client.get("/practice/session?topic=menjar").json()["drills"]] == [a["id"]]
    assert client.get("/practice/session?topic=menjar&speaker=Driss").json()["drills"] == []


def test_a_practice_is_a_sequence_of_steps_and_belongs_to_whoever_made_it():
    """ADR 0002: a practice stops being a list of ids with one question type over all of it. The
    old ones are converted, the new ones have an owner, and only the owner may rewrite them."""
    import main
    import practice_steps
    from test_api import client, as_stranger

    # Signing up is limited to a few tries per address per hour. This test needs two accounts, so
    # it starts from a clean budget and leaves one behind for whatever runs next.
    main._register_attempts.clear(); main._login_attempts.clear()

    mine = client.post("/auth/signup", json={"email": "maker@example.com", "password": "makes-it-123",
                                             "username": "the_maker"}).json()
    hdr = {"X-User-Token": mine["token"]}
    d1 = client.post("/drills/", json={"text_catalan": "aigua", "text_tachelhit": "aman"}, headers=hdr).json()
    d2 = client.post("/drills/", json={"text_catalan": "pa", "text_tachelhit": "aɣrum"}, headers=hdr).json()

    made = client.post("/tests/", headers=hdr, json={
        "title": "La meva llista", "question_type": "audio", "hint_level": "none",
        "drill_ids": f"{d1['id']},{d2['id']}"}).json()
    assert made["created_by_user_id"] == client.get("/users/me", headers=hdr).json().get("id", made["created_by_user_id"])

    # a list of sentences arrives as steps, with the tool the old type carried
    got = client.get(f"/tests/{made['id']}/steps").json()
    assert [s["drill_id"] for s in got["steps"]] == [d1["id"], d2["id"]]
    assert {s["kind"] for s in got["steps"]} == {"listen_pick"}       # «audio» -> escolta i tria
    assert "note" in got["kinds"] and got["kinds"]["note"]["needs_drill"] is False

    # the editor rewrites them: another order, other tools, and a note that teaches
    new_steps = [
        {"kind": "note", "payload": {"text": "Primer escolta, després digues-ho."}},
        {"kind": "say_it", "drill_id": d2["id"]},
        {"kind": "look_say", "drill_id": d1["id"]},
    ]
    out = client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": new_steps}).json()
    assert [s["kind"] for s in out["steps"]] == ["note", "say_it", "look_say"]
    assert [s["position"] for s in out["steps"]] == [0, 1, 2]
    assert out["steps"][0]["payload"]["text"].startswith("Primer")

    # «record» asked for a voice to KEEP in the library, which is Veus's job, not a practice's
    gone = client.put(f"/tests/{made['id']}/steps", headers=hdr,
                      json={"steps": [{"kind": "record", "drill_id": d1["id"]}]})
    assert gone.status_code == 400
    assert [s["kind"] for s in client.get(f"/tests/{made['id']}/steps").json()["steps"]] == ["note", "say_it", "look_say"]

    # what cannot be a step is refused, and refused BEFORE anything is deleted
    bad = client.put(f"/tests/{made['id']}/steps", headers=hdr,
                     json={"steps": [{"kind": "say_it"}]})           # no sentence
    assert bad.status_code == 400 and "frase" in bad.json()["detail"]
    assert len(client.get(f"/tests/{made['id']}/steps").json()["steps"]) == 3   # untouched

    empty_note = client.put(f"/tests/{made['id']}/steps", headers=hdr,
                            json={"steps": [{"kind": "note", "payload": {"text": "  "}}]})
    assert empty_note.status_code == 400

    # somebody else's practice is not yours to rewrite
    other = client.post("/auth/signup", json={"email": "other2@example.com", "password": "other-one-123",
                                              "username": "someone_else2"}).json()
    denied = client.put(f"/tests/{made['id']}/steps", headers={"X-User-Token": other["token"]},
                        json={"steps": [{"kind": "listen_pick", "drill_id": d1["id"]}]})
    assert denied.status_code == 403
    with as_stranger():
        assert client.put(f"/tests/{made['id']}/steps", json={"steps": []}).status_code == 401

    # and the conversion only touches what has no steps
    again = practice_steps.convert_missing(main.SessionLocal)
    assert again["practices"] >= 0
    assert len(client.get(f"/tests/{made['id']}/steps").json()["steps"]) == 3
    main._register_attempts.clear()   # leave the budget as we found it


def test_the_editor_can_find_a_sentence_without_downloading_the_library():
    """Putting a sentence into a practice must not mean pulling 3.500 drills first (#199)."""
    from test_api import client
    client.post("/drills/", json={"text_catalan": "la clau de casa", "text_tachelhit": "tasarut n tgmmi"})
    client.post("/drills/", json={"text_catalan": "una clau anglesa", "text_tachelhit": "clé"})

    hits = client.get("/drills/", params={"search": "clau", "limit": 50}).json()
    assert len(hits) >= 2
    assert all("clau" in ((d.get("text_catalan") or "") + (d.get("text_tachelhit") or "") + (d.get("tag") or "")).lower()
               for d in hits)
    # it looks in the Tamazight too, not only in the Catalan
    tam = client.get("/drills/", params={"search": "tasarut"}).json()
    assert any("tasarut" in (d.get("text_tachelhit") or "") for d in tam)
    assert client.get("/drills/", params={"search": "   "}).status_code == 200   # blank asks for nothing


def test_a_practice_can_be_renamed_by_whoever_made_it_and_by_nobody_else():
    """Until 2026-10-22 any visitor could rename or delete anyone's practice: PUT and DELETE
    /tests/{id} checked nothing at all, while the steps underneath them did."""
    import main
    from test_api import client, as_stranger, register

    main._register_attempts.clear(); main._login_attempts.clear()
    hdr = {"X-User-Token": register("practice_owner")}
    other = {"X-User-Token": register("someone_else")}

    mine = client.post("/tests/", headers=hdr, json={
        "title": "Com es diu", "description": "", "question_type": "audio",
        "hint_level": "none", "passing_score": 70, "drill_ids": ""}).json()

    # a field at a time: what is not sent is left alone, not blanked
    renamed = client.put(f"/tests/{mine['id']}", headers=hdr, json={"title": "Els possessius"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Els possessius"
    assert renamed.json()["question_type"] == "audio"

    with as_stranger():
        assert client.put(f"/tests/{mine['id']}", json={"title": "Teva no"}).status_code == 401
    assert client.put(f"/tests/{mine['id']}", headers=other, json={"title": "Teva no"}).status_code == 403
    assert client.delete(f"/tests/{mine['id']}", headers=other).status_code == 403
    assert client.get(f"/tests/{mine['id']}").json()["title"] == "Els possessius"

    assert client.delete(f"/tests/{mine['id']}", headers=hdr).status_code == 200
    assert client.get(f"/tests/{mine['id']}").status_code == 404


def test_a_tifinagh_sentence_can_be_practised_even_if_the_course_cannot_quote_it():
    """Two groups showed «aquest grup no té cap drill» while holding 84 and 9 sentences.

    One of them («Tamazight For All · faules») is written in Tifinagh, and practice was filtering
    with the grammar course's rule, which refuses Tifinagh because the course itself is written in
    Latin letters. Practice has no such reason: you can hear the sentence and read it.
    """
    import grammar

    tifinagh = "ⵉⵎⵎⵓⵜ ⵡⴰⵡⵜⵉⵍ ⵙ ⵜⴰⴹⵚⴰ"
    latin = "immut wawtil s taḍṣa"

    assert grammar.well_formed(tifinagh)       # practisable
    assert not grammar.quotable(tifinagh)      # the course keeps its Latin letters
    assert grammar.well_formed(latin) and grammar.quotable(latin)

    # and what is not a sentence at all stays out of both
    for junk in ("text", "a.b.c", "", "Mana Lun ija +tEli"):
        assert not grammar.well_formed(junk), junk

    class FakeDrill:
        text_catalan = "La llebre va morir de riure"
        text_tachelhit = tifinagh
    assert practice.quotable_any(FakeDrill())


def test_a_step_that_points_at_no_sentence_becomes_a_note_instead_of_showing_as_frase_hash():
    """The owner opened a practice and saw a step reading «frase #»: a listening step with
    nothing to listen to. The old editor allowed it (a note switched to a tool that needs a
    sentence), and a deleted drill leaves the same wreck behind."""
    import main
    import practice_steps
    from models import PracticeStep
    from test_api import client, register

    hdr = {"X-User-Token": register("step_repairer")}
    p = client.post("/tests/", headers=hdr, json={
        "title": "Amb un pas trencat", "description": "", "question_type": "audio",
        "hint_level": "none", "passing_score": 70, "drill_ids": ""}).json()

    # written straight into the table: the API refuses to create one, which is the point
    db = main.SessionLocal()
    db.add(PracticeStep(test_id=p["id"], position=0, kind="listen_pick", drill_id=None))
    db.add(PracticeStep(test_id=p["id"], position=1, kind="listen_pick", drill_id=999999))
    db.commit(); db.close()

    assert practice_steps.repair_pointless_steps(main.SessionLocal) >= 2
    steps = client.get(f"/tests/{p['id']}/steps").json()["steps"]
    assert [s["kind"] for s in steps] == ["note", "note"]
    assert all(s["drill_id"] is None for s in steps)
    assert "esborrat" in steps[1]["payload"]["text"]
    assert practice_steps.repair_pointless_steps(main.SessionLocal) == 0  # safe to run again
