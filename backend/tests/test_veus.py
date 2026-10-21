"""Veus: petitions (a learner asks, a speaker answers with their voice and their spelling), the
sounds unit, and proposals to change a lesson card."""
import io
import json
import grammar
import main
from test_api import client


def _user(name, **kw):
    r = client.post("/users/register", json={"username": name, **kw}).json()
    return {"X-User-Token": r["token"]}


def test_petition_is_filled_by_the_first_speakers_recording(monkeypatch):
    learner = _user("veus_learner")
    assert client.post("/petitions", json={"text_catalan": "Com es diu «bon profit»?"}).status_code == 401
    p = client.post("/petitions", json={"text_catalan": "bon profit", "note": "per dir-ho a taula"}, headers=learner).json()
    assert p["tag"] == "petició" and p["requested_by"] == "veus_learner" and not p["text_tachelhit"]
    opened = client.get("/petitions?kind=open").json()
    assert any(x["drill"]["id"] == p["id"] and x["note"] == "per dir-ho a taula" for x in opened["items"])
    # a speaker from Aït Mraw answers with their own spelling
    monkeypatch.setattr(main.cloudinary.uploader, "upload", lambda *a, **k: {"secure_url": "https://res.cloudinary.com/x/video/upload/v1/tachelhit/recordings/rec_1.webm"})
    speaker = _user("veus_speaker", variety="tdl", region="Aït Mraw (Azilal)")
    r = client.post(f"/drills/{p['id']}/recordings", files={"file": ("take.webm", io.BytesIO(b"abc"), "audio/webm")}, data={"text": "bismillah"}, headers=speaker)
    assert r.status_code == 200
    d = client.get(f"/drills/{p['id']}").json()
    assert d["text_tachelhit"] == "bismillah" and d["audio_url"].endswith("rec_1.webm") and d["region"] == "Aït Mraw (Azilal)" and d["variety"] == "tdl"
    assert all(x["drill"]["id"] != p["id"] for x in client.get("/petitions?kind=open").json()["items"])  # answered: no longer open
    # the synthetic list: drills with a text but no human voice, basic units first
    s = client.post("/drills/", json={"text_catalan": "gràcies", "text_tachelhit": "tanmmirt", "tag": "Curs bàsic (sintètic)"}).json()
    client.put(f"/drills/{s['id']}", json={"grammar": "formules", "grammar_source": "owner", "audio_url": None})
    syn = client.get("/petitions?kind=synthetic&limit=200").json()["items"]
    me = next(x for x in syn if x["drill"]["id"] == s["id"])
    assert me["level"] == 1 and me["units"] == ["formules"]
    assert client.get("/petitions?kind=aitmraw").status_code == 200 and client.get("/petitions?kind=x").status_code == 400


def test_sounds_unit_is_first_and_quotes_short_recorded_words():
    assert grammar.SLUGS[0] == grammar.SOUNDS_UNIT and grammar.UNITS[0]["level"] == 1
    a = client.post("/drills/", json={"text_catalan": "gràcies", "text_tachelhit": "tanmmirt", "audio_url": "https://x/t.webm", "image_url": "https://x/t.jpg"}).json()
    b = client.post("/drills/", json={"text_catalan": "sí", "text_tachelhit": "yah", "audio_url": "https://x/y.webm"}).json()  # no hard sound
    c = client.post("/drills/", json={"text_catalan": "no puc cuinar perquè no tinc arròs", "text_tachelhit": "ur ġiġ ad ssnuġ ašku walu rruẓ", "audio_url": "https://x/l.webm"}).json()  # too long
    ids = [d.id for d in grammar.sound_rows(main.SessionLocal())]
    assert a["id"] in ids and b["id"] not in ids and c["id"] not in ids
    assert client.get("/grammar").json()["counts"][grammar.SOUNDS_UNIT] >= 1
    unit = grammar.UNITS[0]
    assert "SOUNDS and SPELLING" in grammar._lesson_prompt(unit, [], "sheet") and "1.1" in grammar.SECTIONS[grammar.SOUNDS_UNIT]


def test_lesson_proposals_are_reviewed_by_an_admin(monkeypatch):
    from models import GrammarLesson, User as UserModel
    db = main.SessionLocal()
    db.merge(GrammarLesson(id="manlleus", body=json.dumps({"intro": "Sabràs dir que no.", "steps": [{"type": "explain", "title": "ur", "text": "Posa ur davant.", "examples": []}, {"type": "end"}]}), version=grammar.LESSON_VERSION)); db.commit()
    learner = _user("veus_proposer", region="Girona")
    r = client.post("/grammar/manlleus/proposals", json={"step": 0, "text": "Posa «ur» just davant del verb, sense res entremig."}, headers=learner).json()
    assert r["status"] == "pending"
    assert client.post("/grammar/no-such/proposals", json={"step": 0, "text": "x y z"}, headers=learner).status_code == 404
    mine = client.get("/grammar/manlleus/proposals", headers=learner).json()
    assert len(mine) == 1 and mine[0]["display_name"] == "veus_proposer" and mine[0]["region"] == "Girona"
    assert client.post(f"/grammar/proposals/{r['id']}/decide", json={"accept": True}, headers=learner).status_code == 403
    admin = _user("veus_admin")
    u = db.query(UserModel).filter(UserModel.username == "veus_admin").first(); u.is_admin = True; db.commit()
    assert client.post(f"/grammar/proposals/{r['id']}/decide", json={"accept": True}, headers=admin).json()["status"] == "accepted"
    body = json.loads(db.query(GrammarLesson).filter(GrammarLesson.id == "manlleus").first().body)
    assert body["steps"][0]["text"].startswith("Posa «ur» just davant")
    assert client.get("/grammar/manlleus/proposals", headers=admin).json() == []
    db.close()
