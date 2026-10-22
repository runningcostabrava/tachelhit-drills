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
