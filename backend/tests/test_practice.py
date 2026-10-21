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
