"""tts_text: the synthetic voice reads standard Tifinagh, never raw Latin."""
import tts_text
from test_lexicon import _fixture  # dictionary fixture (afus, fel)


def test_tifinagh_passes_through(monkeypatch):
    assert tts_text.tts_text("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ") == ("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", "tifinagh")


def test_dictionary_word_takes_its_dictionary_spelling(tmp_path, monkeypatch):
    _fixture(tmp_path, monkeypatch)
    assert tts_text.tts_text("afus") == ("ⴰⴼⵓⵙ", "lexicon")


def test_phrase_with_meaning_is_normalised_by_gemini(monkeypatch):
    monkeypatch.setattr(tts_text, "_lexicon_form", lambda t: None)
    calls = {}
    def fake(system, contents, **kw):
        calls["prompt"] = contents[0]["text"]
        return "ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ\n"
    import gemini_client
    monkeypatch.setattr(gemini_client, "gemini_generate", fake)
    spoken, how = tts_text.tts_text("righ srdgh ifsn", "Vull rentar-me les mans")
    assert (spoken, how) == ("ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", "gemini") and "righ srdgh ifsn" in calls["prompt"]


def test_bad_gemini_answers_fall_back_to_transliteration(monkeypatch):
    monkeypatch.setattr(tts_text, "_lexicon_form", lambda t: None)
    import gemini_client
    for bad in ("riɣ ad ssirdɣ ifassn", "ⵔⵉⵖ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ ⴰⴷ ⵙⵙⵉⵔⴷⵖ ⵉⴼⴰⵙⵙⵏ", ""):
        monkeypatch.setattr(gemini_client, "gemini_generate", lambda *a, **k: bad)
        spoken, how = tts_text.tts_text("righ srdgh ifsn", "Vull rentar-me les mans")
        assert how == "transliteration" and tts_text.is_tifinagh(spoken)
    def boom(*a, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(gemini_client, "gemini_generate", boom)
    assert tts_text.tts_text("righ srdgh ifsn", "x")[1] == "transliteration"
    assert tts_text.tts_text("righ srdgh ifsn")[1] == "transliteration"  # no meaning: no Gemini call


def test_prefill_tts_makes_and_stores_a_voice_once(monkeypatch):
    import main
    from test_api import client
    calls = []
    monkeypatch.setattr(main, "generate_tachelhit_tts_hf", lambda spoken, did: calls.append(spoken) or f"https://res.cloudinary.com/x/tachelhit_tts_{main.VOICE_VERSION}_{did}.mp3")
    d = client.post("/drills/", json={"text_catalan": "Ha llaurat", "text_tachelhit": "ⵉⵙ ⵉⴽⵔⵣ"}).json()
    db = main.SessionLocal()
    try:
        drill = db.query(main.DrillModel).filter(main.DrillModel.id == d["id"]).first()
        url = main.prefill_tts(drill, db)
        assert url and f"tts_{main.VOICE_VERSION}_" in url and calls == ["ⵉⵙ ⵉⴽⵔⵣ"]
        assert main.prefill_tts(drill, db) == url and len(calls) == 1  # already made: no second call
        placeholder = db.query(main.DrillModel).filter(main.DrillModel.id == client.post("/drills/", json={"text_catalan": "x", "text_tachelhit": "text"}).json()["id"]).first()
        assert main.prefill_tts(placeholder, db) is None and len(calls) == 1
    finally:
        db.close()
    assert client.post("/tts/prefill", json={"limit": 5}).status_code in (401, 403)  # admin only
