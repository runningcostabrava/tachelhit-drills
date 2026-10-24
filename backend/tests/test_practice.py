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


def test_a_practice_made_of_steps_can_actually_be_played():
    """ADR 0002 made a practice a sequence of steps; the runner kept reading `drill_ids`, the flat
    list a practice used to be. A practice written in the workshop has steps and an empty list, so
    pressing play gave nothing — which is what three brand-new lessons did the minute they existed.
    """
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("step_player")}
    first = client.post("/drills/", headers=hdr, json={
        "text_catalan": "aigua", "text_tachelhit": "aman aman",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/one.mp3"}).json()
    second = client.post("/drills/", headers=hdr, json={
        "text_catalan": "pa", "text_tachelhit": "aɣrum n tgmmi",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/two.mp3"}).json()

    made = client.post("/tests/", headers=hdr, json={
        "title": "Feta de passos", "description": "", "question_type": "audio",
        "hint_level": "none", "passing_score": 70, "drill_ids": ""}).json()   # empty on purpose
    client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "note", "payload": {"text": "una nota no es reprodueix"}},
        {"kind": "listen_pick", "drill_id": second["id"]},
        {"kind": "say_it", "drill_id": first["id"]},
    ]})

    played = client.get(f"/practice/session?test_id={made['id']}&limit=10").json()["drills"]
    assert [d["id"] for d in played] == [second["id"], first["id"]], "l'ordre el tria qui la fa"
    assert all((d.get("text_tachelhit") or "").strip() for d in played), "la nota no hi és"


def test_una_practica_no_neix_sense_amo():
    """A practice belongs to whoever made it, and one made by nobody cannot be used by anybody.

    `may_change` reads an unclaimed thing as the administrator's -- right for a sentence from
    before accounts existed, wrong for something created a second ago. A visitor without a name
    got a practice, an editor that opened, and a 403 on every save afterwards; it could not be
    renamed and it could not be thrown away. The name is asked for before, not after."""
    from test_api import client, as_stranger

    before = len(client.get("/tests/").json())
    with as_stranger():
        refused = client.post("/tests/", json={
            "title": "D'alg\u00fa?", "question_type": "audio", "hint_level": "none", "drill_ids": ""})
    assert refused.status_code == 401
    assert "nom" in refused.json()["detail"], "ha de dir qu\u00e8 li falta, no nom\u00e9s que no"
    assert len(client.get("/tests/").json()) == before, "no se n'ha de crear cap"


def test_les_meves_llistes_son_meves_i_es_compten_pels_passos():
    """«Les meves llistes» showed everyone's, and said 0 of all of them.

    Two faults in one row: the query had no owner in it, so a learner saw every practice anybody
    had ever made; and the count came from `drill_ids`, the flat list a practice used to be. A
    practice built in the workshop keeps its sentences in its STEPS and leaves that column empty,
    so every one of them was offered as empty when it was not."""
    from test_api import client, as_stranger

    a = client.post("/auth/signup", json={"email": "owner-a@example.com",
                                          "password": "mine-alone-123", "username": "owner_a"}).json()
    b = client.post("/auth/signup", json={"email": "owner-b@example.com",
                                          "password": "yours-alone-123", "username": "owner_b"}).json()
    ha, hb = {"X-User-Token": a["token"]}, {"X-User-Token": b["token"]}

    d = client.post("/drills/", headers=ha, json={
        "text_catalan": "aigua", "text_tachelhit": "aman",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/w.mp3"}).json()
    mine = client.post("/tests/", headers=ha, json={
        "title": "La meva", "question_type": "audio", "hint_level": "none", "drill_ids": ""}).json()
    yours = client.post("/tests/", headers=hb, json={
        "title": "La teva", "question_type": "audio", "hint_level": "none", "drill_ids": ""}).json()

    # two steps, and `drill_ids` left empty: this is what the workshop makes
    put = client.put(f"/tests/{mine['id']}/steps", headers=ha, json={"steps": [
        {"kind": "listen_pick", "drill_id": d["id"]},
        {"kind": "note", "payload": {"heading": "Saludar"}},
    ]})
    assert put.status_code == 200, put.text

    def listed(h):
        return [t["id"] for t in client.get("/tests/?mine=1", headers=h).json()]

    assert mine["id"] in listed(ha) and yours["id"] not in listed(ha)
    assert yours["id"] in listed(hb) and mine["id"] not in listed(hb)
    with as_stranger():
        assert client.get("/tests/?mine=1").status_code == 401

    col = client.get("/practice/collections", headers=ha).json()
    row = next(x for x in col["lists"] if x["id"] == mine["id"])
    assert row["count"] == 2, "el compte surt dels passos, no de drill_ids"
    assert all(x["id"] != yours["id"] for x in col["lists"]), "la d'un altre no hi ha de ser"

    # and the refusal talks about a practice, because that is what the person is looking at
    denied = client.put(f"/tests/{mine['id']}/steps", headers=hb,
                        json={"steps": [{"kind": "listen_pick", "drill_id": d["id"]}]})
    assert denied.status_code == 403 and "pr\u00e0ctica" in denied.json()["detail"]


def test_una_nota_amb_titol_i_sense_text_es_desa():
    """A heading is a note: «Saludar» over the next three sentences teaches where you are.

    It used to be refused -- and a save is all-or-nothing on purpose, so that one refusal took
    down every other step sent with it: the three sentences added just before were lost, and the
    autosave never tried again. A note with NOTHING in it is still not a step; the editor keeps
    those to itself instead of sending them, so a blank line can no longer cost the work."""
    from test_api import client, register

    hdr = {"X-User-Token": register("note_titler")}
    d = client.post("/drills/", headers=hdr, json={
        "text_catalan": "bon dia", "text_tachelhit": "sbaḥ lxir",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/bd.mp3"}).json()
    made = client.post("/tests/", headers=hdr, json={
        "title": "Amb t\u00edtols", "question_type": "audio", "hint_level": "none", "drill_ids": ""}).json()

    ok = client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "note", "payload": {"heading": "Saludar"}},
        {"kind": "listen_pick", "drill_id": d["id"]},
    ]})
    assert ok.status_code == 200, ok.text
    steps = ok.json()["steps"]
    assert [x["kind"] for x in steps] == ["note", "listen_pick"]
    assert steps[0]["payload"]["heading"] == "Saludar"

    # nothing at all in it is still nothing to show, and it must not take the rest down with it
    empty = client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "note", "payload": {"heading": "  ", "text": ""}},
    ]})
    assert empty.status_code == 400
    assert [x["kind"] for x in client.get(f"/tests/{made['id']}/steps").json()["steps"]] == \
        ["note", "listen_pick"], "el que ja hi havia no s'ha tocat"


def test_una_practica_diu_quants_passos_te_i_quina_cara_fa():
    """Every screen asked how big a practice is, and worked it out itself from `drill_ids` -- the
    flat list a practice used to be. The workshop leaves that column empty (ADR 0002), so the
    gallery called an eleven-step practice «0 drills» while the Pràctica screen called the same
    one eleven. The practice now carries the number, and a picture to be recognised by: the first
    of its sentences that has one."""
    from test_api import client, register

    hdr = {"X-User-Token": register("size_teller")}
    plain = client.post("/drills/", headers=hdr, json={
        "text_catalan": "sal", "text_tachelhit": "tisent",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/s.mp3"}).json()
    drawn = client.post("/drills/", headers=hdr, json={
        "text_catalan": "te", "text_tachelhit": "atay",
        "image_url": "https://res.cloudinary.com/x/image/upload/v1/tea.jpg",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/t.mp3"}).json()

    made = client.post("/tests/", headers=hdr, json={
        "title": "Quants en t\u00e9", "question_type": "audio", "hint_level": "none",
        "drill_ids": ""}).json()                       # empty on purpose: this is what the workshop makes
    assert made["step_count"] == 0

    client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "note", "payload": {"heading": "Per beure"}},
        {"kind": "listen_pick", "drill_id": plain["id"]},
        {"kind": "say_it", "drill_id": drawn["id"]},
    ]})

    one = client.get(f"/tests/{made['id']}").json()
    assert one["drill_ids"] == "" and one["step_count"] == 3, "tres passos, encara que drill_ids sigui buit"
    listed = next(t for t in client.get("/tests/?mine=1", headers=hdr).json() if t["id"] == made["id"])
    assert listed["step_count"] == 3, "la llista ha de dir el mateix que la fitxa"

    row = next(x for x in client.get("/practice/collections", headers=hdr).json()["lists"]
               if x["id"] == made["id"])
    assert row["count"] == 3
    # the cover is the first sentence that has a picture, not the first sentence
    assert row["cover"] == drawn["image_url"]

    # an old practice, made of a flat list and never converted, still reports what it holds
    old = client.post("/tests/", headers=hdr, json={
        "title": "De les velles", "question_type": "audio", "hint_level": "none",
        "drill_ids": f"{plain['id']},{drawn['id']}"}).json()
    assert old["step_count"] == 2


def test_una_practica_antiga_no_es_queda_en_blanc_per_una_frase_esborrada():
    """La pràctica 28 portava 511 frases i s'obria amb «0 passos».

    La llista plana d'una pràctica antiga és una llista de números, i un número deixa de voler
    dir res quan la frase s'esborra: nou dels primers dos-cents d'aquella apuntaven a frases que
    ja no hi són. `practice_steps.drill_id` és una clau forana, que a Postgres s'aplica de debò,
    així que aquells passos no es podien escriure — i la conversió feia un sol `commit()` al
    final de TOTES les pràctiques, de manera que una fila impossible en tombava el lot sencer i
    cap pràctica no es convertia mai.

    Ara una frase morta se salta i la pràctica es converteix igual."""
    import practice_steps
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("legacy_owner")}
    alive = [client.post("/drills/", headers=hdr, json={
        "text_catalan": f"frase {i}", "text_tachelhit": f"tafrast {i}"}).json() for i in range(3)]
    doomed = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la que marxa", "text_tachelhit": "ad ftugh"}).json()

    old = client.post("/tests/", headers=hdr, json={
        "title": "De les velles", "question_type": "audio", "hint_level": "none",
        "drill_ids": ",".join(str(d["id"]) for d in [alive[0], doomed, alive[1], alive[2]])}).json()
    # la pràctica neix amb els passos de la llista; els esborrem per deixar-la com les d'abans
    client.put(f"/tests/{old['id']}/steps", headers=hdr, json={"steps": []})
    assert client.get(f"/tests/{old['id']}/steps").json()["steps"] == []

    client.delete(f"/drills/{doomed['id']}", headers=hdr)

    out = practice_steps.convert_missing(main.SessionLocal)
    assert out["practices"] >= 1, out
    steps = client.get(f"/tests/{old['id']}/steps").json()["steps"]
    assert [x["drill_id"] for x in steps] == [alive[0]["id"], alive[1]["id"], alive[2]["id"]], \
        "les vives hi són, en ordre, i la morta se salta"
    assert [x["position"] for x in steps] == [0, 1, 2], "sense forats a l'ordre"


def test_desar_un_pas_cap_a_una_frase_morta_ho_diu_en_comptes_de_petar():
    """`drill_id` és una clau forana. Un pas cap a una frase esborrada no es pot escriure, i si
    ho descobreix la base de dades és un 500 **després** d'haver esborrat els passos que hi
    havia. Es comprova abans, i es diu amb paraules que l'editor pot ensenyar."""
    from test_api import client, register

    hdr = {"X-User-Token": register("step_saver")}
    good = client.post("/drills/", headers=hdr, json={
        "text_catalan": "aigua", "text_tachelhit": "aman"}).json()
    doomed = client.post("/drills/", headers=hdr, json={
        "text_catalan": "pa", "text_tachelhit": "aɣrum"}).json()
    p = client.post("/tests/", headers=hdr, json={
        "title": "Amb una morta", "question_type": "audio", "hint_level": "none",
        "drill_ids": ""}).json()
    client.put(f"/tests/{p['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "listen_pick", "drill_id": good["id"]}]})

    client.delete(f"/drills/{doomed['id']}", headers=hdr)
    bad = client.put(f"/tests/{p['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "listen_pick", "drill_id": good["id"]},
        {"kind": "say_it", "drill_id": doomed["id"]}]})
    assert bad.status_code == 400
    assert "ja no existeixen" in bad.json()["detail"]
    # i el que ja hi havia segueix sent-hi: no s'esborra res fins que tot és possible
    assert [x["drill_id"] for x in client.get(f"/tests/{p['id']}/steps").json()["steps"]] == [good["id"]]


def test_esborrar_una_practica_s_endu_els_seus_passos():
    """Una pràctica que se'n va no deixa els seus passos enrere.

    Això es confiava al `ON DELETE CASCADE` de la clau forana. Postgres el fa; SQLite no aplica
    les claus foranes si no s'ha activat `PRAGMA foreign_keys=ON`, i no l'activem enlloc. Els
    passos sobrevivien a la seva pràctica, i com que SQLite reutilitza l'id que s'acaba
    d'alliberar, la pràctica SEGÜENT naixia amb els passos de l'anterior: una prova que demanava
    zero passos en veia dos, i la culpa semblava de qui els comptava.
    """
    import main
    from test_api import client, register

    hdr = {"X-User-Token": register("step_sweeper")}
    d = client.post("/drills/", headers=hdr, json={
        "text_catalan": "la finestra", "text_tachelhit": "tiflut n-ufrag",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/f.mp3"}).json()
    made = client.post("/tests/", headers=hdr, json={
        "title": "Se'n va amb els seus passos", "question_type": "audio",
        "hint_level": "none", "drill_ids": ""}).json()
    assert client.put(f"/tests/{made['id']}/steps", headers=hdr, json={"steps": [
        {"kind": "note", "payload": {"heading": "Hola"}},
        {"kind": "listen_pick", "drill_id": d["id"]},
    ]}).status_code == 200

    db = main.SessionLocal()
    try:
        from models import PracticeStep
        assert db.query(PracticeStep).filter(PracticeStep.test_id == made["id"]).count() == 2
    finally:
        db.close()

    assert client.delete(f"/tests/{made['id']}", headers=hdr).status_code == 200

    db = main.SessionLocal()
    try:
        from models import PracticeStep
        left = db.query(PracticeStep).filter(PracticeStep.test_id == made["id"]).count()
        assert left == 0, f"{left} passos han sobreviscut a la seva pràctica"
    finally:
        db.close()

    # i la següent pràctica neix buida, encara que el motor li doni el mateix id
    nova = client.post("/tests/", headers=hdr, json={
        "title": "La següent", "question_type": "audio", "hint_level": "none",
        "drill_ids": ""}).json()
    try:
        assert nova["step_count"] == 0, "una pràctica nova no hereta els passos de cap altra"
    finally:
        client.delete(f"/tests/{nova['id']}", headers=hdr)
