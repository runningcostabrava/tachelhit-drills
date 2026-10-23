"""Dialect-aware transcription: the variety picks the engine, the prompt carries the profile, the
corpus examples, the NeMo hint and the speaker's text; the result goes to *_suggested only."""
import json
import dialect
import main
from test_api import client


def _fake_gemini(captured):
    def gen(payload, timeout):
        captured.append(payload)
        return {"candidates": [{"content": {"parts": [{"text": "Nta ija xali Jaume, yan uymas n ma. Nta ija xali Jaume, yan uymas n ma."}]}}]}
    return gen


def test_profiles_and_engines():
    assert dialect.profile("tdl")["engine"] == "ensemble"
    assert dialect.profile("zgh")["engine"] == "nemo"
    assert dialect.profile("shi")["engine"] == "gemini"
    assert dialect.profile("other") is None and dialect.profile(None) is None
    assert any(v["code"] == "tdl" for v in client.get("/varieties").json())


def test_dedupe_takes():
    assert dialect.dedupe_takes("Mana wa? Mana wa?") == "Mana wa?"
    assert dialect.dedupe_takes("nta ija pa hlu inu nta ija pa hlu inu") == "nta ija pa hlu inu"
    assert dialect.dedupe_takes("abrid ibrdan") == "abrid ibrdan"


def test_transitional_variety_uses_hint_profile_and_examples(monkeypatch, tmp_path):
    captured = []
    monkeypatch.setattr(dialect, "_prepare_wav", lambda src, d, tempo: str(tmp_path / "c.wav"))
    (tmp_path / "c.wav").write_bytes(b"RIFF")
    monkeypatch.setattr(dialect, "_duration", lambda p: 4.0)
    monkeypatch.setattr(dialect, "_nemo", lambda wav: "ⵏⵜⴰ ⵉⵊⴰ ⵅⴰⵍⵉ")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    import gemini_client
    monkeypatch.setattr(gemini_client, "_generate_content", _fake_gemini(captured))
    out = dialect.transcribe("clip.webm", "tdl", meaning="És el meu oncle Jaume", speaker_text="nta ija khali Jaume",
                             examples=["Mana wi? — Qui són?"])
    assert out["engine"] == "ensemble" and out["hint"] == "ⵏⵜⴰ ⵉⵊⴰ ⵅⴰⵍⵉ"
    assert out["latin"] == "Nta ija xali Jaume, yan uymas n ma"  # the second take is dropped
    assert out["tifinagh"].startswith("ⵏⵜⴰ ⵉⵊⴰ ⵅⴰⵍⵉ")
    sysmsg = captured[0]["systemInstruction"]["parts"][0]["text"]
    user = captured[0]["contents"][0]["parts"][1]["text"]
    assert "TRANSITIONAL" in sysmsg and "Mana wi?" in sysmsg
    assert "ⵏⵜⴰ ⵉⵊⴰ ⵅⴰⵍⵉ" in user and "És el meu oncle Jaume" in user and "nta ija khali Jaume" in user


def test_standard_variety_keeps_nemo(monkeypatch, tmp_path):
    monkeypatch.setattr(dialect, "_prepare_wav", lambda src, d, tempo: str(tmp_path / "c.wav"))
    (tmp_path / "c.wav").write_bytes(b"RIFF")
    monkeypatch.setattr(dialect, "_duration", lambda p: 4.0)
    monkeypatch.setattr(dialect, "_nemo", lambda wav: "ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ")
    out = dialect.transcribe("clip.webm", "zgh")
    assert out["engine"] == "nemo" and out["tifinagh"] == "ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ" and out["latin"] == "azul fllawn"


def test_retranscribe_endpoint_writes_suggestion_only(monkeypatch):
    r = client.post("/drills/", json={"text_catalan": "És el meu oncle", "text_tachelhit": "nta ija khali", "variety": "tdl",
                                       "audio_url": "https://example.test/a.webm", "author": "Halima"})
    did = r.json()["id"]
    monkeypatch.setattr(dialect, "transcribe", lambda src, v, **kw: {"latin": "Nta ija xali.", "tifinagh": "ⵏⵜⴰ ⵉⵊⴰ ⵅⴰⵍⵉ", "engine": "ensemble", "hint": ""})
    r = client.post(f"/drills/{did}/retranscribe", json={})
    assert r.status_code == 200 and r.json()["latin"] == "Nta ija xali." and r.json()["variety"] == "tdl"
    d = client.get(f"/drills/{did}").json()
    assert d["text_tachelhit"] == "nta ija khali" and d["text_tachelhit_suggested"] == "Nta ija xali."
    # no variety and no override -> told to choose one
    r2 = client.post("/drills/", json={"text_catalan": "x", "text_tachelhit": "y", "audio_url": "https://example.test/b.webm"})
    assert client.post(f"/drills/{r2.json()['id']}/retranscribe", json={}).status_code == 400
    assert client.post(f"/drills/{r2.json()['id']}/retranscribe", json={"variety": "shi"}).status_code == 200


def test_transcribe_returns_latin_and_tifinagh_together(monkeypatch):
    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: {"latin": "mana lun tja ttfḥti", "tifinagh": "ⵎⴰⵏⴰ ⵍⵓⵏ ⵜⵊⴰ ⵜⵜⴼⵃⵜⵉ"})
    r = client.post("/transcribe/", json={"audio_url": "https://example.test/a.webm"})
    assert r.status_code == 200 and r.json()["corrected_transcription"] == "mana lun tja ttfḥti · ⵎⴰⵏⴰ ⵍⵓⵏ ⵜⵊⴰ ⵜⵜⴼⵃⵜⵉ"
    monkeypatch.setattr(main, "_transcribe_short_clip_with_gemini", lambda *a, **k: {"latin": "ⵃⵓ", "tifinagh": "ⵃⵓ"})
    assert client.post("/transcribe/", json={"audio_url": "https://example.test/a.webm"}).status_code == 502


def test_el_transcriptor_no_llegeix_les_linies_cantades():
    """A sung line's words come from the video, never from the transcriber (ruling 2026-10-23).

    Our transcriber cannot do singing, and it does not fail politely: on the 92 sung cuts of the
    blind-reading audit it answered with things that read like sentences and were not, and on two
    of them it looped on one word fifty times. Those drafts go to `text_tachelhit_suggested`,
    which is the verify queue -- so the machine was asking a person to judge noise, ninety-odd
    times. A sung drill is only used when its text can be had from the video itself: the burned-in
    lyrics or a subtitle track.

    The refusal happens before the recording is fetched, so no transcriber is mocked here: not
    attempting the reading is the whole point."""
    from test_api import client

    sung = client.post("/drills/", json={
        "text_catalan": "el meu cor", "text_tachelhit": "ul inu",
        "variety": "tzm", "topics": "canco",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/song.mp3"}).json()
    r = client.post(f"/drills/{sung['id']}/retranscribe", json={"variety": "tzm"})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert "cantada" in detail and ("subt\u00edtols" in detail or "sobreimpr\u00e8s" in detail), detail

    # and the draft is left exactly as it was: empty
    back = client.get(f"/drills/{sung['id']}").json()
    assert not (back.get("text_tachelhit_suggested") or "").strip()
    assert back["text_tachelhit"] == "ul inu", "el text del parlant no es toca mai"
