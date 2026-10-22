"""The copilot's hands inside the practice workshop.

The tools are tested through the executor, not through Gemini: what matters here is what the
tools DO when the model asks for them — which sentences they are willing to offer, in what order,
and who they let write.
"""
import main
from test_api import client, register


def _run(user=None):
    db = main.SessionLocal()
    return main._agent_executor(db, user), db


def test_the_copilot_only_offers_whole_sentences_and_the_short_ones_first():
    """A practice must never be built out of half-made sentences: that is how a list of nine
    «text» sentences came to exist. And «compra» should bring «compra pa» before a paragraph
    that happens to contain the word."""
    hdr = {"X-User-Token": register("copilot_sentences")}
    good_short = client.post("/drills/", headers=hdr, json={
        "text_catalan": "aigua", "text_tachelhit": "aman aman",
        "audio_url": "https://res.cloudinary.com/x/audio/upload/v1/a.mp3", "tag": "copilot-test"}).json()
    good_long = client.post("/drills/", headers=hdr, json={
        "text_catalan": "vull una mica d'aigua freda ara mateix si et plau",
        "text_tachelhit": "riɣ imik n waman ismmiḍnin ɣilad",
        "audio_url": "https://res.cloudinary.com/x/audio/upload/v1/b.mp3", "tag": "copilot-test"}).json()
    no_voice = client.post("/drills/", headers=hdr, json={
        "text_catalan": "pa", "text_tachelhit": "aɣrum n tgmmi", "tag": "copilot-test"}).json()
    no_text = client.post("/drills/", headers=hdr, json={
        "text_catalan": "sense paraules", "text_tachelhit": "",
        "audio_url": "https://res.cloudinary.com/x/audio/upload/v1/c.mp3", "tag": "copilot-test"}).json()

    run, db = _run()
    try:
        out = run("find_sentences_for_practice", {"tag": "copilot-test", "limit": 20})
    finally:
        db.close()
    offered = [s["drill_id"] for s in out["sentences"]]

    assert good_short["id"] in offered and good_long["id"] in offered
    assert no_voice["id"] not in offered, "una frase sense veu no s'ofereix"
    assert no_text["id"] not in offered, "una frase sense paraules escrites no s'ofereix"
    assert offered.index(good_short["id"]) < offered.index(good_long["id"]), "primer la curta"


def test_the_copilot_builds_a_practice_but_not_somebody_elses():
    mine = {"X-User-Token": register("copilot_builder")}
    other = register("copilot_outsider")
    d = client.post("/drills/", headers=mine, json={
        "text_catalan": "bon dia", "text_tachelhit": "azul fllawn",
        "audio_url": "https://res.cloudinary.com/x/audio/upload/v1/d.mp3"}).json()
    p = client.post("/tests/", headers=mine, json={
        "title": "La feia el copilot", "description": "", "question_type": "audio",
        "hint_level": "none", "passing_score": 70, "drill_ids": ""}).json()

    me = main.SessionLocal().query(main.UserModel).filter(main.UserModel.username == "copilot_builder").first()
    stranger = main.SessionLocal().query(main.UserModel).filter(main.UserModel.username == "copilot_outsider").first()
    assert stranger and other

    steps = [
        {"kind": "note", "heading": "Saludar", "text": "Com es diu bon dia."},
        {"kind": "listen_pick", "drill_id": d["id"]},
    ]
    run, db = _run(me)
    try:
        out = run("build_practice", {"test_id": p["id"], "steps": steps})
        assert out.get("written") == 2, out
        back = run("read_practice", {"test_id": p["id"]})
        assert [s["kind"] for s in back["steps"]] == ["note", "listen_pick"]
        assert back["steps"][0]["payload"]["heading"] == "Saludar"
    finally:
        db.close()

    # somebody else's practice, and nobody at all: refused, and nothing is touched
    for who in (stranger, None):
        run, db = _run(who)
        try:
            out = run("build_practice", {"test_id": p["id"], "steps": [{"kind": "note", "text": "meva"}]})
            assert "error" in out, out
        finally:
            db.close()
    assert [s["kind"] for s in client.get(f"/tests/{p['id']}/steps").json()["steps"]] == ["note", "listen_pick"]


def test_the_copilot_refuses_a_step_it_cannot_run():
    """A listening step with no sentence is the «frase #» bug: it must not be writable at all."""
    mine = {"X-User-Token": register("copilot_careful")}
    p = client.post("/tests/", headers=mine, json={
        "title": "Mig feta", "description": "", "question_type": "audio",
        "hint_level": "none", "passing_score": 70, "drill_ids": ""}).json()
    me = main.SessionLocal().query(main.UserModel).filter(main.UserModel.username == "copilot_careful").first()
    run, db = _run(me)
    try:
        assert "error" in run("build_practice", {"test_id": p["id"], "steps": [{"kind": "listen_pick"}]})
        assert "error" in run("build_practice", {"test_id": p["id"], "steps": [{"kind": "record", "drill_id": 1}]})
    finally:
        db.close()
