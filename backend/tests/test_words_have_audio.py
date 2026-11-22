"""Saber quines paraules es poden sentir ABANS de prémer (#271).

El paraula per paraula demanava el tall en prémer, i si no n'hi havia cap ho deia quan ja havies
premut. El pedagog ho va comptar al capítol 4 del Mètode: de vuit paraules centrals només dues
tenien tall. **Vuit pressions i dos sons és el que desensenya a prémer.**
"""
import word_audio
from main import SessionLocal
from models import WordAudio
from test_api import client, register


def _drill(hdr, shi):
    return client.post("/drills/", headers=hdr, json={
        "text_tachelhit": shi, "text_catalan": "una frase",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/w.mp3"}).json()


def test_one_trip_says_which_words_can_be_heard():
    hdr = {"X-User-Token": register("words_have")}
    d = _drill(hdr, "aman d tiglay")
    with SessionLocal() as db:
        db.add(WordAudio(key=word_audio.key_of("aman"), word="aman", drill_id=d["id"],
                         start_ms=0, end_ms=400, source="library"))
        db.commit()

    r = client.get("/words/have-audio", params={"words": "aman,tudit,tiglay"}).json()["words"]
    assert r["aman"] is True
    assert r["tudit"] is False and r["tiglay"] is False


def test_the_same_word_written_another_way_is_the_same_word():
    """«afus», «afous» i «ⴰⴼⵓⵙ» són la mateixa paraula dita per tres persones que escriuen
    diferent, i qui aprèn no sap quina de les tres va teclejar qui la va gravar."""
    hdr = {"X-User-Token": register("words_have_spell")}
    d = _drill(hdr, "afus")
    with SessionLocal() as db:
        db.add(WordAudio(key=word_audio.key_of("afus"), word="afus", drill_id=d["id"],
                         start_ms=0, end_ms=300, source="library"))
        db.commit()
    r = client.get("/words/have-audio", params={"words": "afous,ⴰⴼⵓⵙ,afus"}).json()["words"]
    assert all(r.values()), r


def test_asking_for_nothing_answers_nothing_instead_of_failing():
    assert client.get("/words/have-audio", params={"words": " , ,"}).json()["words"] == {}
