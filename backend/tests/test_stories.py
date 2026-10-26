"""Whole stories and songs, instead of loose sentences (#189).

A story is not a new kind of row: it is what a group of drills already is when they come from one
source and say when they are spoken. These tests are about what makes a group a story, and about
the one thing that must not be hidden — a line that can be heard but not read.
"""
import main
from test_api import client, register


def _line(hdr, title, at, text, meaning, voiced=True):
    return client.post("/drills/", headers=hdr, json={
        "text_catalan": meaning, "text_tachelhit": text,
        "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/{title}-{at}.mp3" if voiced else None,
        "source_title": title, "video_start_time": at, "video_url": f"https://youtu.be/{title}",
    }).json()


def test_a_group_of_timed_recorded_lines_from_one_source_is_a_story():
    hdr = {"X-User-Token": register("story_teller")}
    title = "El llop i la seva ombra (prova)"
    for i in range(7):
        _line(hdr, title, float(i * 3), f"awal {i}", f"línia {i}")

    stories = client.get("/stories").json()["stories"]
    mine = next((s for s in stories if s["title"] == title), None)
    assert mine, "set línies amb temps i veu són una història"
    assert mine["lines"] == 7 and mine["missing_words"] == 0

    page = client.get(f"/stories/{mine['slug']}").json()
    # in the order they are SPOKEN, not the order they were typed
    assert [d["text_tachelhit"] for d in page["drills"]] == [f"awal {i}" for i in range(7)]
    assert page["source_url"] or page["video_url"]


def test_five_loose_sentences_are_not_a_story():
    """Six lines is the floor: fewer is a pile from the same video, not something to follow."""
    hdr = {"X-User-Token": register("story_short")}
    title = "Massa poca cosa (prova)"
    for i in range(5):
        _line(hdr, title, float(i), f"inna {i}", f"diu {i}")
    assert not any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_a_line_nobody_has_written_down_keeps_its_place_and_says_so():
    """A story with holes is still a story. Dropping the line would hide the work; moving it
    would lie about where it belongs."""
    hdr = {"X-User-Token": register("story_holes")}
    title = "Amb forats (prova)"
    for i in range(6):
        _line(hdr, title, float(i * 2), "" if i == 2 else f"tawal {i}", f"vol dir {i}")

    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["lines"] == 6 and mine["written"] == 5 and mine["missing_words"] == 1

    page = client.get(f"/stories/{mine['slug']}").json()
    assert [bool((d["text_tachelhit"] or "").strip()) for d in page["drills"]] == [True, True, False, True, True, True]


def test_an_unknown_story_is_a_404_not_an_empty_page():
    assert client.get("/stories/aixo-no-existeix").status_code == 404


def test_lines_that_start_at_the_same_second_are_a_pile_not_a_story():
    """Deu frases tallades d'un mateix vídeo no són un conte (#335).

    Va passar de debò: deu frases soltes d'un vídeo del propietari van sortir a la pàgina com a
    «October 2, 2023», que no és cap títol sinó el que YouTube hi posa quan el vídeo no en té.
    Totes portaven temps, de manera que passaven la prova — però tres començaven al segon 0.0.

    Dues línies d'un conte no comencen mai al mateix segon. Comprovat contra la biblioteca abans
    de posar-ho: de les 25 històries que la pàgina ensenyava, les 24 de debò tenien tots els
    temps diferents (776 línies, cap repetida) i només la falsa en repetia.
    """
    hdr = {"X-User-Token": register("story_pile")}
    title = "October 2, 2023 (prova)"
    for i, at in enumerate([0.0, 0.0, 0.0, 7.18, 9.21, 15.99, 20.0, 24.5]):
        _line(hdr, title, at, f"awal {i}", f"frase solta {i}")
    assert not any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_the_same_lines_with_their_own_times_are_a_story_again():
    """Que el que ho treu sigui la col·lisió i no una altra cosa: mateixes línies, temps propis."""
    hdr = {"X-User-Token": register("story_pile_ok")}
    title = "Amb temps propis (prova)"
    for i, at in enumerate([0.0, 3.2, 5.1, 7.18, 9.21, 15.99, 20.0, 24.5]):
        _line(hdr, title, at, f"awal {i}", f"línia {i}")
    assert any(s["title"] == title for s in client.get("/stories").json()["stories"])


def test_the_title_says_which_series_and_which_chapter():
    """El títol del canal porta la sèrie, el capítol i el nom en dos alfabets tot junt (#346)."""
    import stories as st
    assert st.series_of("The Traveller -2- ⴰⵏⵎⴰⴷⴷⵓ - Anmaddu") == ("The Traveller", 2)
    assert st.series_of("The Rivals - 1 - ⵉⵏⴳⴳⵯⴰ - inggʷa") == ("The Rivals", 1)
    assert st.series_of("The Last Warrior- 4 -ⴰⵎⵏⵏⴰⵖ ⴰⵎⴳⴳⴰⵔⵓ") == ("The Last Warrior", 4)
    # Un conte sol no té capítol, i dir que en té seria inventar-se una sèrie.
    assert st.series_of("The Wolf and The Lamb - ⵓⵛⵛⵏ ⴷ ⵉⴽⵔⵓ") == (None, None)


def test_the_chapters_come_back_together_and_in_order():
    """Perquè algú pugui començar un conte pel principi, que és el que la pàgina ha de fer fàcil.

    Abans la llista anava per nombre de línies i els set capítols quedaven escampats per la
    graella, barrejats amb les altres sèries.
    """
    hdr = {"X-User-Token": register("story_series")}
    # A posta en desordre, i amb el capítol 2 més llarg que els altres: si l'ordre fos per
    # llargada, sortiria primer.
    for cap, quantes in ((3, 6), (1, 7), (2, 12)):
        for i in range(quantes):
            _line(hdr, f"La prova -{cap}- ⴰⵡⴰⵍ", float(i * 3), f"awal {i}", f"línia {i}")

    meves = [s for s in client.get("/stories").json()["stories"] if s["series"] == "La prova"]
    assert [s["chapter"] for s in meves] == [1, 2, 3]
    # I vénen de seguit, sense res pel mig: la pàgina els agrupa confiant en aquest ordre.
    totes = [s["series"] for s in client.get("/stories").json()["stories"]]
    primer = totes.index("La prova")
    assert totes[primer:primer + 3] == ["La prova"] * 3


def test_one_chapter_alone_is_not_a_series():
    hdr = {"X-User-Token": register("story_one_chapter")}
    for i in range(7):
        _line(hdr, "Tota sola -1- ⴰⵡⴰⵍ", float(i * 3), f"awal {i}", f"línia {i}")
    sola = next(s for s in client.get("/stories").json()["stories"] if "Tota sola" in s["title"])
    assert sola["series"] is None and sola["chapter"] is None


def test_the_cover_is_the_video_s_own_cover_not_a_drill_illustration():
    """La portada d'un conte que ve d'un vídeo és la portada d'aquell vídeo (#346).

    Les il·lustracions dels drills es van demanar per a una frase, no per al conte: una d'elles
    era una carta d'ajust de televisió i feia de portada d'una faula.
    """
    hdr = {"X-User-Token": register("story_cover")}
    title = "Amb portada (prova)"
    for i in range(6):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": f"línia {i}", "text_tachelhit": f"awal {i}",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/{i}.mp3",
            "image_url": "https://exemple.test/carta-d-ajust.jpg" if i == 0 else None,
            "source_title": title, "video_start_time": float(i * 3),
            "source_url": "https://www.youtube.com/watch?v=p7qlqkDVyNU",
        })
    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["cover"] == "https://i.ytimg.com/vi/p7qlqkDVyNU/hqdefault.jpg"


def test_a_story_with_no_video_keeps_its_own_illustration():
    """Sense vídeo, la il·lustració d'una de les seves línies és millor que res."""
    hdr = {"X-User-Token": register("story_cover_none")}
    title = "Sense vídeo (prova)"
    for i in range(6):
        client.post("/drills/", headers=hdr, json={
            "text_catalan": f"línia {i}", "text_tachelhit": f"awal {i}",
            "audio_url": f"https://res.cloudinary.com/x/video/upload/v1/n{i}.mp3",
            "image_url": "https://exemple.test/dibuix.jpg" if i == 1 else None,
            "source_title": title, "video_start_time": float(i * 3),
        })
    mine = next(s for s in client.get("/stories").json()["stories"] if s["title"] == title)
    assert mine["cover"] == "https://exemple.test/dibuix.jpg"
