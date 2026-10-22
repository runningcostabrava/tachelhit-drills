"""Hearing ONE word, from the recordings we already have.

A sentence recording plus the text it says is enough: forced alignment knows when each word is
spoken, so a word becomes a drill id and two times. Nothing is uploaded and no sound file is made
— which is also why these tests never need a Space: `align_one` is the only part that talks to
one, and it is replaced here by the answer a Space would give.
"""
import main
import word_audio
from test_api import client, register


def test_one_word_is_the_same_word_however_it_is_spelled():
    """«afus», «afous» and «ⴰⴼⵓⵙ» are three people writing the same word. Somebody asking to hear
    it does not care which of the three they typed."""
    assert word_audio.key_of("afus") == word_audio.key_of("afous") == word_audio.key_of("ⴰⴼⵓⵙ")
    assert word_audio.key_of("afus") != word_audio.key_of("aghrum")
    assert word_audio.key_of("") == ""


def test_a_word_is_a_span_inside_a_recording_that_already_exists(monkeypatch):
    hdr = {"X-User-Token": register("word_aligner")}
    drill = client.post("/drills/", headers=hdr, json={
        "text_catalan": "Vull pa", "text_tachelhit": "riɣ aɣrum",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/riɣ.mp3",
        "author": "Halima"}).json()

    db = main.SessionLocal()
    row = db.query(main.DrillModel).filter(main.DrillModel.id == drill["id"]).first()
    kept = word_audio.store(db, row, [
        {"word": "riɣ", "start": 0.0, "end": 0.42},
        {"word": "aɣrum", "start": 0.5, "end": 1.1},
    ])
    db.close()
    assert kept == 2

    r = client.get("/words/audio", params={"word": "aɣrum"}).json()
    assert r["count"] == 1
    clip = r["clips"][0]
    assert clip["drill_id"] == drill["id"]
    assert clip["audio_url"].endswith(".mp3"), "sona la gravació que ja hi ha, no cap fitxer nou"
    assert (clip["start"], clip["end"]) == (0.5, 1.1)
    assert clip["speaker"] == "Halima", "qui ho diu ha de venir amb la paraula"
    assert clip["sentence"] == "riɣ aɣrum" and clip["meaning"] == "Vull pa"

    # the same word written another way finds the same recording
    assert client.get("/words/audio", params={"word": "aghrum"}).json()["count"] == 1
    # and a word nobody has said is not an error, just silence
    assert client.get("/words/audio", params={"word": "zzzzzz"}).json()["count"] == 0


def test_our_own_voices_come_before_the_open_corpus():
    """A word said by somebody with a name and a place is worth more than the same word said by
    nobody in particular. The open corpus fills gaps; it does not take the front."""
    hdr = {"X-User-Token": register("word_ranker")}
    ours = client.post("/drills/", headers=hdr, json={
        "text_catalan": "mare", "text_tachelhit": "imma",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/ours.mp3", "author": "Driss"}).json()
    theirs = client.post("/drills/", headers=hdr, json={
        "text_catalan": "mare (corpus)", "text_tachelhit": "imma",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/theirs.mp3"}).json()

    db = main.SessionLocal()
    for drill_id, source in ((theirs["id"], "tosd"), (ours["id"], "library")):
        row = db.query(main.DrillModel).filter(main.DrillModel.id == drill_id).first()
        word_audio.store(db, row, [{"word": "imma", "start": 0.0, "end": 0.5}], source=source)
    db.close()

    clips = client.get("/words/audio", params={"word": "imma"}).json()["clips"]
    assert [c["source"] for c in clips][0] == "library"
    assert clips[0]["speaker"] == "Driss"


def test_a_recording_that_will_not_align_is_silence_not_an_error(monkeypatch):
    """Best effort on purpose: a sentence whose words cannot be timed is one whose words cannot be
    played yet — never something anybody has to see."""
    monkeypatch.setattr(word_audio.requests, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("xarxa")))
    assert word_audio.align_one("https://x/clip.mp3", "riɣ aɣrum") is None
    assert word_audio.align_one("", "riɣ aɣrum") is None
    assert word_audio.align_one("https://x/clip.mp3", "") is None
