"""A capture processed on another backend (agent --process-at) is reported done with its
drill count; the foreign job id is never looked up here."""
from test_api import client


def test_done_with_drills_created_closes_the_request_without_a_job():
    rid = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=abc123def45", "tag": "t"}).json()["request_id"]
    client.get("/capture/pending")  # the agent claims it
    r = client.post(f"/capture/{rid}/done", json={"job_id": 41, "drills_created": 12})
    assert r.status_code == 200
    s = client.get(f"/capture/{rid}").json()
    assert s["status"] == "done" and s["drills_created"] == 12 and s["job_id"] is None and s["job_status"] is None


def test_done_without_drill_count_keeps_the_old_contract():
    rid = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=abc123def46"}).json()["request_id"]
    client.get("/capture/pending")
    client.post(f"/capture/{rid}/done", json={"job_id": 999999})
    s = client.get(f"/capture/{rid}").json()
    assert s["status"] == "processing" and s["job_id"] == 999999


def test_un_video_diu_que_en_vam_treure_i_que_ens_vam_deixar():
    """Once the drills existed there was no way back to the video they came from, although every
    one of them carries where it was cut from. The holes are the point of looking: a stretch
    nothing was taken from means the machine may have skipped something, and two cuts that step
    on each other mean one of them is carrying the other's words -- the fault that made drill
    6854 say «tinc gana» over four seconds that held another phrase."""
    from test_api import client

    url = "https://www.youtube.com/watch?v=TESTcuts001"
    made = []
    for a, b, ca in ((10.0, 13.0, "hola"), (13.0, 16.0, "com est\u00e0s"),
                     (40.0, 43.0, "adeu"), (42.0, 45.0, "fins ara")):
        made.append(client.post("/drills/", json={
            "text_catalan": ca, "text_tachelhit": f"x{a}", "source_url": url,
            "source_title": "Un v\u00eddeo de prova",
            "video_start_time": a, "video_end_time": b}).json())

    r = client.get("/capture/video", params={"url": url}).json()
    assert [c["id"] for c in r["cuts"]] == [d["id"] for d in made], "en ordre de temps"
    assert r["title"] == "Un v\u00eddeo de prova"
    assert r["covered_from"] == 10.0 and r["covered_to"] == 45.0

    # the 24-second stretch between 16 and 40 is a hole; 13->13 and 43->42 are not
    assert len(r["holes"]) == 1, r["holes"]
    assert r["holes"][0]["from"] == 16.0 and r["holes"][0]["to"] == 40.0

    # the last two step on each other by a second
    assert len(r["overlaps"]) == 1, r["overlaps"]
    assert r["overlaps"][0]["by"] == 1.0
    assert {r["overlaps"][0]["a"], r["overlaps"][0]["b"]} == {made[2]["id"], made[3]["id"]}

    assert client.get("/capture/video", params={"url": "https://x/none"}).status_code == 404


def test_tornar_a_tallar_demana_un_video_i_un_tram_que_tingui_sentit():
    """`trim-audio` and `trim-video` cut the clip we already hold, so a cut the machine made too
    short can never be made longer by them. Cutting again goes back to the source video, which
    means there has to BE one -- and the refusals have to say which thing is missing, because the
    person is looking at a slider, not at a database."""
    from test_api import client

    url = "https://www.youtube.com/watch?v=TESTcuts002"
    from_video = client.post("/drills/", json={
        "text_catalan": "aigua", "text_tachelhit": "aman", "source_url": url,
        "video_start_time": 5.0, "video_end_time": 8.0}).json()
    by_hand = client.post("/drills/", json={
        "text_catalan": "pa", "text_tachelhit": "a\u0263rum"}).json()

    nowhere = client.post(f"/drills/{by_hand['id']}/recut",
                          json={"start_time": 1.0, "end_time": 3.0})
    assert nowhere.status_code == 400 and "v\u00eddeo" in nowhere.json()["detail"]

    backwards = client.post(f"/drills/{from_video['id']}/recut",
                            json={"start_time": 9.0, "end_time": 4.0})
    assert backwards.status_code == 400 and "final" in backwards.json()["detail"]

    too_long = client.post(f"/drills/{from_video['id']}/recut",
                           json={"start_time": 0.0, "end_time": 600.0})
    assert too_long.status_code == 400

    # and none of that touched the sentence
    back = client.get(f"/drills/{from_video['id']}").json()
    assert back["text_tachelhit"] == "aman"
    assert back["video_start_time"] == 5.0 and back["video_end_time"] == 8.0
