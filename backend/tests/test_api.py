"""
Backend API tests. Run from backend/:  python -m pytest tests -q

Uses an isolated SQLite database and FastAPI's in-process TestClient —
no server, no external services (endpoints that call HF Spaces/Cloudinary
are not exercised here).
"""
import os
import sys
import time

# Isolated DB — must be set before importing main (module reads env at import)
TEST_DB = "test_drills.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"
os.environ.pop("CHECK_SCHEMA", None)
os.environ.pop("API_KEY", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

from datetime import datetime, timezone  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)


class as_stranger:
    """Act with no identity at all. The shared client carries one (every real client does), so a
    test about what an OUTSIDER may do has to put it down for a moment."""

    def __enter__(self):
        self._token = client.headers.pop("X-User-Token", None)
        return client

    def __exit__(self, *exc):
        if self._token:
            client.headers["X-User-Token"] = self._token
        return False
client.__enter__()  # run lifespan: create tables + seed samples


def register(username: str) -> str:
    main._register_attempts.clear()  # tests share one client IP
    r = client.post("/users/register", json={"username": username})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_varieties_vocabulary():
    r = client.get("/varieties")
    assert r.status_code == 200
    codes = {v["code"] for v in r.json()}
    # the varieties stay distinct — Tarifit is present, not collapsed into zgh
    assert {"shi", "tzm", "rif", "zgh"} <= codes


def test_profile_variety_defaults_onto_new_drill():
    main._register_attempts.clear()
    reg = client.post("/users/register", json={"username": "rifi.speaker", "variety": "rif", "region": "Nador"})
    assert reg.status_code == 200
    token = reg.json()["token"]
    hdr = {"X-User-Token": token}
    me = client.get("/users/me", headers=hdr).json()
    assert me["variety"] == "rif" and me["region"] == "Nador"
    # a drill this contributor creates inherits their variety/region
    d = client.post("/drills/", json={"text_catalan": "hola"}, headers=hdr).json()
    assert d["variety"] == "rif" and d["region"] == "Nador"
    # they can update their declared variety
    upd = client.put("/users/me", json={"variety": "tzm"}, headers=hdr).json()
    assert upd["variety"] == "tzm"


def test_recordings_multi_speaker_listing_empty_then_404_delete():
    # a fresh drill has no extra takes yet; deleting a missing take 404s
    d = client.post("/drills/", json={"text_catalan": "x"}).json()
    assert client.get(f"/drills/{d['id']}/recordings").json() == []
    assert client.delete("/recordings/99999999").status_code == 404


# ---------- basics ----------

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_seeded_drills_exist():
    r = client.get("/drills/")
    assert r.status_code == 200
    assert len(r.json()) >= 3  # lifespan seeds three samples


# ---------- helpers (pure logic) ----------

def test_resolve_hf_space_host():
    assert main.resolve_hf_space_host("https://huggingface.co/spaces/Owner/My_Space") == \
        "https://owner-my-space.hf.space"
    assert main.resolve_hf_space_host("https://my-space.hf.space/") == "https://my-space.hf.space"


def test_extract_cloudinary_public_id():
    url = "https://res.cloudinary.com/demo/video/upload/v123456/tachelhit/shorts/abc123.mp4"
    assert main.extract_cloudinary_public_id(url) == "tachelhit/shorts/abc123"
    assert main.extract_cloudinary_public_id("https://example.com/x.mp4") is None


def test_align_lyrics_lines():
    segments = [
        {"start": 0.0, "end": 2.0, "text": "rough guess one"},
        {"start": 2.0, "end": 4.0, "text": "rough guess two"},
    ]
    out = main._align_lyrics_lines(segments, "Real line one\nReal line two\n")
    assert out[0]["text"] == "Real line one"
    assert out[1]["text"] == "Real line two"
    assert out[0]["text_asr"] == "rough guess one"  # original preserved
    assert out[0]["start"] == 0.0  # timestamps untouched


# ---------- users & auth ----------

def test_register_login_and_hashing():
    token = register("testuser")
    # raw token works
    me = client.get("/users/me", headers={"X-User-Token": token})
    assert me.status_code == 200
    assert me.json()["username"] == "testuser"
    # wrong token rejected
    assert client.get("/users/me", headers={"X-User-Token": "bogus"}).status_code == 401
    # stored value is a hash, not the raw token
    db = main.SessionLocal()
    row = db.query(main.UserModel).filter_by(username="testuser").first()
    db.close()
    assert row.token != token
    assert row.token == main._hash_token(token)


def test_register_validation():
    main._register_attempts.clear()
    assert client.post("/users/register", json={"username": "x"}).status_code == 400
    register("taken.name")
    assert client.post("/users/register", json={"username": "taken.name"}).status_code == 409


def test_register_rate_limit():
    main._register_attempts.clear()
    for i in range(5):
        client.post("/users/register", json={"username": f"ratelimit{i}"})
    r = client.post("/users/register", json={"username": "ratelimit-final"})
    assert r.status_code == 429


# ---------- spaced repetition ----------

def test_srs_scheduling_and_isolation():
    token = register("learner")
    drills = client.get("/drills/").json()
    drill_id = drills[0]["id"]

    # good -> 1 day, rep 1
    r = client.post(f"/reviews/{drill_id}/grade", json={"grade": 2},
                    headers={"X-User-Token": token}).json()
    assert r["interval_days"] == 1.0 and r["repetitions"] == 1

    # easy on rep 1 -> 8 days, ease grows
    r = client.post(f"/reviews/{drill_id}/grade", json={"grade": 3},
                    headers={"X-User-Token": token}).json()
    assert r["interval_days"] == 8.0 and r["ease"] > 2.5

    # again -> lapse: reps reset, tiny interval, ease drops
    r = client.post(f"/reviews/{drill_id}/grade", json={"grade": 0},
                    headers={"X-User-Token": token}).json()
    assert r["repetitions"] == 0 and r["interval_days"] < 0.1 and r["ease"] < 2.65

    # isolation: learner has 1 tracked card, anonymous has none of it
    mine = client.get("/reviews/stats", headers={"X-User-Token": token}).json()
    anon = client.get("/reviews/stats").json()
    assert mine["learning"] >= 1
    assert anon["learning"] == 0


def test_grade_validation():
    drill_id = client.get("/drills/").json()[0]["id"]
    assert client.post(f"/reviews/{drill_id}/grade", json={"grade": 9}).status_code == 400
    assert client.post("/reviews/999999/grade", json={"grade": 2}).status_code == 404


# ---------- corpus & verification ----------

def test_create_drill_attribution_and_corpus():
    token = register("contributor")
    r = client.post("/drills/", json={"text_catalan": "hola prova", "text_tachelhit": "ⴰⵣⵓⵍ ⵜⴻⵙⵜ",
                                      "variety": "tashelhit", "region": "Souss"},
                    headers={"X-User-Token": token})
    assert r.status_code == 200
    drill = r.json()
    assert drill["author"] == "contributor"

    # searchable by text and variety
    hits = client.get("/corpus/search", params={"q": "ⴰⵣⵓⵍ ⵜⴻⵙⵜ"}).json()
    assert any(d["id"] == drill["id"] for d in hits)
    hits = client.get("/corpus/search", params={"variety": "tashelhit"}).json()
    assert any(d["id"] == drill["id"] for d in hits)

    # verification requires identity, then flips the flag
    with as_stranger():  # nobody verifies anonymously
        assert client.post(f"/drills/{drill['id']}/verify", json={"verified": True}).status_code == 401
    v = client.post(f"/drills/{drill['id']}/verify", json={"verified": True},
                    headers={"X-User-Token": token})
    assert v.status_code == 200 and v.json()["verified"] is True
    stats = client.get("/corpus/stats").json()
    assert stats["verified"] >= 1


def test_corpus_export_csv():
    r = client.get("/corpus/export", params={"format": "csv"})
    assert r.status_code == 200
    header = r.text.splitlines()[0]
    for col in ("variety", "region", "license", "source_url", "verified", "text_tachelhit_latin"):
        assert col in header


def test_flywheel_respects_privacy():
    token = register("privateperson")
    r = client.post("/drills/", json={"text_tachelhit": "ⵜⴰⵏⵎⵎⵉⵔⵜ ⵜⴻⵙⵜ",
                                      "audio_url": "https://res.cloudinary.com/demo/video/upload/a.mp3",
                                      "license": "private"},
                    headers={"X-User-Token": token})
    private_id = r.json()["id"]
    pairs = client.get("/corpus/flywheel").json()["pairs"]
    assert all(p["drill_id"] != private_id for p in pairs)


def test_streak_tracking():
    token = register("streaker")
    drill_id = client.get("/drills/").json()[0]["id"]
    client.post(f"/reviews/{drill_id}/grade", json={"grade": 2},
                headers={"X-User-Token": token})
    s = client.get("/reviews/streak", headers={"X-User-Token": token}).json()
    assert s["streak_days"] == 1
    assert s["reviews_today"] >= 1
    assert s["active_days"] == 1


def test_smart_test_from_weakest():
    token = register("weakuser")
    drills = client.get("/drills/").json()
    # Create some review history: lapse one drill so it's clearly weakest
    client.post(f"/reviews/{drills[0]['id']}/grade", json={"grade": 0},
                headers={"X-User-Token": token})
    r = client.post("/tests/from-weakest", json={"count": 5},
                    headers={"X-User-Token": token})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["drill_count"] >= 1
    # The lapsed drill must lead the test
    test = client.get(f"/tests/{data['test_id']}").json()
    assert str(drills[0]["id"]) == test["drill_ids"].split(",")[0]


def test_glossary_word_boundaries():
    pairs = [("anayr", "anaygh")]
    # whole word replaced
    assert main.apply_glossary("is anayr dik", pairs) == "is anaygh dik"
    # NOT inside a longer word
    assert main.apply_glossary("tanayrit", pairs) == "tanayrit"


def test_version_endpoint():
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert "commit" in data
    assert data["features"]["srs"] is True


def test_flywheel_jsonl_export():
    import json as _json
    token = register("jsonluser")
    client.post("/drills/", json={"text_tachelhit": "ⴰⵣⵓⵍ ⴼⵍⴰⵡⵉⵍ",
                                  "audio_url": "https://res.cloudinary.com/demo/video/upload/fw.mp3"},
                headers={"X-User-Token": token})
    r = client.get("/corpus/flywheel", params={"format": "jsonl"})
    assert r.status_code == 200
    assert "x-ndjson" in r.headers["content-type"]
    lines = [l for l in r.text.splitlines() if l.strip()]
    assert lines, "expected at least one training pair"
    first = _json.loads(lines[0])
    assert "audio_url" in first and "text_tachelhit" in first


def test_corpus_gaps():
    token = register("gapuser")
    # A drill with Tachelhit but no audio/latin -> should show in gaps
    client.post("/drills/", json={"text_tachelhit": "ⴰⵣⵓⵍ ⴳⴰⵒ"}, headers={"X-User-Token": token})
    summary = client.get("/corpus/gaps").json()
    kinds = {g["kind"]: g["count"] for g in summary["gaps"]}
    assert kinds["no_audio"] >= 1
    assert kinds["no_latin"] >= 1
    # verified defaults to NULL -> must count as unverified (regression: SQL
    # `!= True` excludes NULLs, which zeroed the review queue in production)
    assert kinds["unverified"] >= 1
    # kind filter returns the drills, serialized cleanly (no _sa_instance_state)
    r = client.get("/corpus/gaps", params={"kind": "no_audio"}).json()
    assert r["kind"] == "no_audio"
    assert len(r["drills"]) >= 1
    assert "_sa_instance_state" not in r["drills"][0]
    # bad kind rejected
    assert client.get("/corpus/gaps", params={"kind": "nonsense"}).status_code == 400


def test_corpus_sources_catalog():
    src = "https://www.youtube.com/watch?v=catalog1"
    for t0, text in ((0.0, "ⴰⵣⵓⵍ"), (4.0, "ⵜⴰⵏⵎⵎⵉⵔⵜ")):
        client.post("/drills/", json={"text_tachelhit": text, "source_url": src, "source_title": "Lesson 1",
                                      "source_channel": "Chan", "source_playlist": "Course", "variety": "shi",
                                      "tag": "lesson-1", "video_url": "https://x/v.mp4", "video_start_time": t0,
                                      "video_end_time": t0 + 2.5})
    r = client.get("/corpus/sources").json()
    v = next(x for x in r["videos"] if x["source_url"] == src)
    assert (v["drills"], v["with_video"], v["channel"], v["playlist"], v["title"]) == (2, 2, "Chan", "Course", "Lesson 1")
    assert v["varieties"] == ["shi"] and v["tags"] == ["lesson-1"] and (v["from_s"], v["to_s"]) == (0.0, 6.5)
    assert r["from_sources"] >= 2 and r["without_source"] + r["from_sources"] == r["total_drills"]


# ---------- P4: backend basics a native client needs ----------

def test_get_drill_by_id_404_and_ids_param():
    a = client.post("/drills/", json={"text_catalan": "p4 a"}).json()
    b = client.post("/drills/", json={"text_catalan": "p4 b"}).json()
    c = client.post("/drills/", json={"text_catalan": "p4 c"}).json()
    # single
    r = client.get(f"/drills/{a['id']}")
    assert r.status_code == 200 and r.json()["id"] == a["id"]
    # missing -> 404 with the envelope code
    r = client.get("/drills/99999999")
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    # ids= returns only those, in the GIVEN order, ignoring unknown ids
    r = client.get("/drills/", params={"ids": f"{c['id']},{a['id']},99999999,{b['id']}"})
    assert r.status_code == 200
    assert [d["id"] for d in r.json()] == [c["id"], a["id"], b["id"]]
    assert r.headers["X-Total-Count"] == "3"
    # garbage ids -> 400
    assert client.get("/drills/", params={"ids": "1,x"}).status_code == 400


def test_pagination_and_total_count():
    for i in range(3):
        client.post("/drills/", json={"text_catalan": f"page {i}"})
    everything = client.get("/drills/")
    total = len(everything.json())
    # no limit/offset -> all rows (current frontend contract) + the header
    assert everything.headers["X-Total-Count"] == str(total)
    assert total > 2
    # limit paginates, header still carries the unpaginated count
    r = client.get("/drills/", params={"limit": 2})
    assert len(r.json()) == 2 and r.headers["X-Total-Count"] == str(total)
    # offset alone -> default limit (100) from that offset
    r = client.get("/drills/", params={"offset": total - 1})
    assert len(r.json()) == 1
    # limit capped at 500
    r = client.get("/drills/", params={"limit": 10000})
    assert len(r.json()) == min(total, 500)
    # same contract on the other list routes
    for path in ("/tests/", "/test-attempts/", "/shorts/"):
        r = client.get(path, params={"limit": 1})
        assert r.status_code == 200, (path, r.text)
        assert "X-Total-Count" in r.headers, path
        assert len(r.json()) <= 1


def test_stale_token_401_and_no_header_anonymous():
    # no header -> anonymous works on an optional-identity route
    assert client.get("/reviews/stats").status_code == 200
    # present-but-unknown token -> 401 everywhere identity is resolved
    r = client.get("/reviews/stats", headers={"X-User-Token": "stale-token"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid token" and r.json()["code"] == "unauthorized"
    assert client.get("/drills/", headers={"X-User-Token": "stale-token"}).status_code == 200  # no identity needed
    assert client.post("/drills/", json={"text_catalan": "x"},
                       headers={"X-User-Token": "stale-token"}).status_code == 401


def test_delete_drill_with_review_writes_tombstone_and_since_sync():
    token = register("deleter")
    hdr = {"X-User-Token": token}
    marker = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    d = client.post("/drills/", json={"text_catalan": "to delete"}, headers=hdr).json()
    # review state + log rows on the drill
    assert client.post(f"/reviews/{d['id']}/grade", json={"grade": 2}, headers=hdr).status_code == 200
    # updated_at is set and serialized with Z; since= sees the new drill
    got = client.get(f"/drills/{d['id']}").json()
    assert got["updated_at"] and got["updated_at"].endswith("Z")
    changed = client.get("/drills/", params={"since": marker}).json()
    assert any(x["id"] == d["id"] for x in changed)
    # delete succeeds despite the dependent rows — done by whoever made it
    r = client.delete(f"/drills/{d['id']}", headers=hdr)
    assert r.status_code == 200, r.text
    assert client.get(f"/drills/{d['id']}").status_code == 404
    db = main.SessionLocal()
    try:
        assert db.query(main.DrillReviewModel).filter_by(drill_id=d["id"]).count() == 0
        assert db.query(main.ReviewLogModel).filter_by(drill_id=d["id"]).count() == 0
    finally:
        db.close()
    stones = client.get("/drills/tombstones", params={"since": marker}).json()
    assert any(t["drill_id"] == d["id"] and t["deleted_at"].endswith("Z") for t in stones)
    assert client.get("/drills/tombstones", params={"since": "not-a-date"}).status_code == 400


def test_grade_batch_applies_once_and_resend_is_skipped():
    token = register("offline.grader")
    hdr = {"X-User-Token": token}
    d1 = client.post("/drills/", json={"text_tachelhit": "ⴱ1"}).json()
    d2 = client.post("/drills/", json={"text_tachelhit": "ⴱ2"}).json()
    batch = [
        {"drill_id": d1["id"], "grade": 2, "graded_at": "2026-10-16T08:00:00Z"},
        {"drill_id": d1["id"], "grade": 3, "graded_at": "2026-10-16T09:30:00Z"},
        {"drill_id": d2["id"], "grade": 0, "graded_at": "2026-10-16T09:31:00+02:00"},
        {"drill_id": 99999999, "grade": 1, "graded_at": "2026-10-16T09:32:00Z"},  # unknown drill
    ]
    r = client.post("/reviews/grade-batch", json=batch, headers=hdr)
    assert r.status_code == 200, r.text
    assert r.json() == {"applied": 3, "skipped": 1}
    # the SM-2 state matches grading good then easy on d1 (rep 2, 8-day interval)
    db = main.SessionLocal()
    try:
        me = db.query(main.UserModel).filter_by(username="offline.grader").first()
        rv = db.query(main.DrillReviewModel).filter_by(drill_id=d1["id"], user_id=me.id).first()
        assert rv.repetitions == 2 and rv.interval_days == 8.0
        logs = db.query(main.ReviewLogModel).filter_by(user_id=me.id).count()
        assert logs == 3
    finally:
        db.close()
    # re-sending the whole queue changes nothing
    r = client.post("/reviews/grade-batch", json=batch, headers=hdr)
    assert r.json() == {"applied": 0, "skipped": 4}
    # validation: grade out of range -> 422 envelope
    r = client.post("/reviews/grade-batch", json=[{"drill_id": d1["id"], "grade": 7, "graded_at": "2026-10-16T10:00:00Z"}],
                    headers=hdr)
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


def test_error_envelope_and_z_datetimes():
    # 422: detail is a string, code is set, field errors kept under "errors"
    r = client.post("/tests/", json={"title": "no type"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], str) and "question_type" in body["detail"]
    assert isinstance(body["errors"], list)
    # datetimes render as UTC with a trailing Z on list + detail responses
    d = client.get("/drills/").json()[0]
    assert d["date_created"].endswith("Z")
    t = client.post("/tests/", json={"title": "z", "question_type": "text_input", "hint_level": "none",
                                     "drill_ids": str(d["id"])}).json()
    assert t["date_created"].endswith("Z") and t["updated_at"].endswith("Z")
    # HTTPException keeps its shape and gains a code
    r = client.get("/tests/99999999")
    assert r.json() == {"detail": "Test not found", "code": "not_found"}


def test_test_attempts_keyed_by_user_and_mine_filter():
    token = register("attempter")
    hdr = {"X-User-Token": token}
    d = client.get("/drills/").json()[0]
    t = client.post("/tests/", json={"title": "mine", "question_type": "text_input", "hint_level": "none",
                                     "drill_ids": str(d["id"])}).json()
    payload = {"test_id": t["id"], "user_name": None, "score": 100.0, "time_taken_seconds": 5,
               "total_questions": 1, "correct_answers": 1}
    with as_stranger():  # somebody practising without an account leaves no name on the attempt
        anon = client.post("/test-attempts/", json=payload).json()
    mine = client.post("/test-attempts/", json=payload, headers=hdr).json()
    assert anon["user_id"] is None and mine["user_id"] is not None
    assert mine["date_taken"].endswith("Z")
    r = client.get("/test-attempts/", params={"mine": 1}, headers=hdr)
    assert [a["id"] for a in r.json()] == [mine["id"]]
    with as_stranger():  # «mine» means nothing without a name
        assert client.get("/test-attempts/", params={"mine": 1}).status_code == 401


def test_streak_today_follows_user_tz():
    token = register("tz.user")
    hdr = {"X-User-Token": token}
    me = client.get("/users/me", headers=hdr).json()
    assert me["tz"] == "Europe/Madrid"
    assert client.put("/users/me", json={"tz": "Mars/Olympus"}, headers=hdr).status_code == 400
    assert client.put("/users/me", json={"tz": "Pacific/Kiritimati"}, headers=hdr).json()["tz"] == "Pacific/Kiritimati"
    d = client.get("/drills/").json()[0]
    client.post(f"/reviews/{d['id']}/grade", json={"grade": 2}, headers=hdr)
    s = client.get("/reviews/streak", headers=hdr).json()
    from zoneinfo import ZoneInfo as _Z
    expected_today = datetime.now(timezone.utc).astimezone(_Z("Pacific/Kiritimati")).date().isoformat()
    assert s["tz"] == "Pacific/Kiritimati" and s["today"] == expected_today
    assert s["streak_days"] == 1 and s["reviews_today"] == 1
    st = client.get("/reviews/stats", headers=hdr).json()
    assert st["reviewed_today"] == 1 and st["today"] == expected_today


def test_generate_short_returns_pollable_job_id(monkeypatch):
    # The render Space is stubbed to fail — the point is that the job row
    # exists, its id is returned, and the worker records the outcome on it.
    def _space_offline(payload):
        raise RuntimeError("space offline (test stub)")
    monkeypatch.setattr(main, "call_huggingface_space", _space_offline)
    d = client.get("/drills/").json()[0]
    r = client.post(f"/generate-short/{d['id']}")
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    j = client.get(f"/video-analysis/job/{job_id}").json()
    assert j["kind"] == "short"
    assert j["status"] in ("FAILED", "COMPLETED", "IN_PROGRESS", "PENDING")
    assert j["status"] == "FAILED" and "space offline" in (j["error_message"] or "")


# ---- P1.9: a drill needs content ------------------------------------------
def test_create_drill_requires_text_or_media():
    r = client.post("/drills/", json={})
    assert r.status_code == 422, r.text
    r = client.post("/drills/", json={"text_catalan": "   ", "tag": "x"})
    assert r.status_code == 422, r.text
    r = client.post("/drills/", json={"text_tachelhit": "azul"})
    assert r.status_code == 200, r.text
    assert r.json()["text_tachelhit"] == "azul"


# ---- P5.2: junk ASR guard ---------------------------------------------------
def test_looks_like_junk_asr():
    assert main.looks_like_junk_asr("Is ghorsh lan ait mash? Is ghorom lan aitmam") is None
    assert main.looks_like_junk_asr("ⴰⵣⵓⵍ ⴼⵍⵍⴰⵡⵏ") is None
    assert main.looks_like_junk_asr("L.A.R.R.R.R.R.R.R.R.R.R.R.R.R.R.R.R") == "repeated-run"
    assert main.looks_like_junk_asr("I'm going to get a little bit of a little bit of a little bit") in ("repeated-tokens", "looks-english")
    assert main.looks_like_junk_asr("I actually grab a bus to the station with them and they tell me") == "looks-english"
    # foreign-source draft mode: English is expected, only repeats are junk
    assert main.looks_like_junk_asr("I actually grab a bus to the station with them and they tell me", attested=False) is None
    assert main.looks_like_junk_asr("", attested=True) is None
    # job 20 (2026-10-17): Whisper on a vocabulary video with music
    assert main.looks_like_junk_asr("I can't bear to fall asleep") == "looks-english"
    assert main.looks_like_junk_asr("Emoidar Emoidar Agmar Agmar Therefore, lost, therefore, lost. I can't bear to fall asleep") == "looks-english"
    # real Tachelhit in Latin script with short tokens must pass
    assert main.looks_like_junk_asr("ur ssinegh is d iyi d yusa, mani gh illa uzddar") is None
    assert main.looks_like_junk_asr("Manza ait zdan? Is tsnt?") is None


def test_capture_agent_liveness():
    """The web app asks whether a local capture agent is polling before it queues a URL.

    Polling /capture/pending CLAIMS a request, so this starts from an empty queue: otherwise it
    takes a request another test left waiting and asserts on it by accident (#191).
    """
    from models import CaptureRequest

    main._capture_agent_seen.update({"at": None, "version": None})
    db = main.SessionLocal()
    db.query(CaptureRequest).filter(CaptureRequest.status == "pending").delete()
    db.commit(); db.close()
    r = client.get("/capture/agent")
    assert r.status_code == 200 and r.json()["online"] is False
    # an agent poll (with its version header) marks it online
    r = client.get("/capture/pending", headers={"X-Agent-Version": "2.0.0"})
    assert r.status_code == 200 and r.json()["request"] is None
    r = client.get("/capture/agent")
    assert r.json()["online"] is True and r.json()["version"] == "2.0.0"
    assert r.json()["last_seen"].endswith("Z")


def test_split_bilingual_cue():
    """Caption cues from teaching videos: Tamazight word + gloss on two lines."""
    assert main.split_bilingual_cue("agmar\nhorse") == ("agmar", "horse", "en")
    assert main.split_bilingual_cue("horse\nagmar") == ("agmar", "horse", "en")
    assert main.split_bilingual_cue("agḍiḍ\nbird") == ("agḍiḍ", "bird", "en")
    assert main.split_bilingual_cue("imudar\nAnimals") == ("imudar", "Animals", "en")
    assert main.split_bilingual_cue("amawal n tamaziɣt\nVocabuary of Tamazight") == ("amawal n tamaziɣt", "Vocabuary of Tamazight", "en")
    assert main.split_bilingual_cue("ⴰⴳⵎⴰⵔ\nhorse") == ("ⴰⴳⵎⴰⵔ", "horse", "en")
    # ordinary one-line cue: untouched, no gloss
    assert main.split_bilingual_cue("Is ghorsh lan ait mash?") == ("Is ghorsh lan ait mash?", None, None)
    assert main.split_bilingual_cue(None) == ("", None, None)


def test_parse_vtt_keeps_lines_and_storage_join():
    from video_utils import parse_vtt
    segs = parse_vtt("WEBVTT\n\n00:00:18.801 --> 00:00:23.379\nagmar\nhorse\n\n00:00:24.800 --> 00:00:28.072\ntafullust\n")
    assert segs[0]["lines"] == ["agmar", "horse"] and segs[0]["text"] == "agmar horse"
    assert main.cue_text_for_storage(segs[0]) == "agmar\nhorse"
    assert main.cue_text_for_storage(segs[1]) == "tafullust"


def test_parse_gloss_json():
    ans = 'Sure:\n```json\n{"horse": {"ca": "cavall", "ar": "حصان"}, "Owl": {"ca": "mussol", "ar": "بومة"}}\n```'
    t = main._parse_gloss_json(ans)
    assert t["horse"] == {"ca": "cavall", "ar": "حصان"} and t["owl"]["ca"] == "mussol"
    assert main._parse_gloss_json("no json here") == {}


def test_merge_frame_items():
    items = [
        {"t": 0, "kind": "none"},
        {"t": 2, "kind": "letter", "tifinagh": "ⴱ", "latin": "b", "meaning_en": ""},
        {"t": 4, "kind": "letter", "tifinagh": "ⴱ", "latin": "b"},
        {"t": 6, "kind": "word", "tifinagh": "ⴰⵟⵟⵓⵍ", "latin": "aṭṭul", "meaning_en": "long"},
        {"t": 8, "kind": "word", "tifinagh": "ⴰⵟⵟⵓⵍ", "latin": "", "meaning_en": ""},
        {"t": 10, "kind": "none"},
        {"t": 14, "kind": "word", "tifinagh": "ⴰⵟⵟⵓⵍ", "latin": "aṭṭul", "meaning_en": "long"},
    ]
    segs = main.merge_frame_items(items, every=2.0)
    assert [(x["text"], x["start"], x["end"]) for x in segs] == [("ⴱ", 2.0, 6.0), ("ⴰⵟⵟⵓⵍ", 6.0, 10.0), ("ⴰⵟⵟⵓⵍ", 14.0, 16.0)]
    assert segs[1]["gloss"] == "long" and segs[1]["latin"] == "aṭṭul" and segs[1]["gloss_lang"] == "en"
    assert segs[0]["gloss"] is None and segs[0]["kind"] == "letter"


def test_merge_frame_items_lookalikes_and_slogan():
    items = [
        {"t": 8, "kind": "phrase", "tifinagh": "ⴰⵎⴰⵣⵉⵖ ⵉⴳⴰ ⵉⵎⴷⴷⵏ", "latin": "Amaziɣ iga imddn", "meaning_en": "Amazigh for all"},
        {"t": 36, "kind": "letter", "tifinagh": "Θ", "latin": "b", "meaning_en": "letter yab (b)"},
        {"t": 168, "kind": "word", "tifinagh": "ⴰⵖⵔⵓⵎ", "latin": "aɣrum", "meaning_en": "bread"},
        {"t": 170, "kind": "word", "tifinagh": "ⴰⵖⵓⵔⵓ", "latin": "aɣuru", "meaning_en": "bread"},
    ]
    segs = main.merge_frame_items(items, every=2.0, ignore="Tamazight For All")
    assert [x["text"] for x in segs] == ["ⴱ", "ⴰⵖⵔⵓⵎ"]
    assert segs[1]["end"] == 172.0  # the misread frame extended the span instead of making a drill


def test_apply_lesson_vocabulary():
    vocab = {"letters": [{"name": "yab", "latin": "b"}],
             "words": [{"latin": "ibba", "meaning_en": "my father"}, {"latin": "abghan", "meaning_en": "black"},
                       {"latin": "ibbi", "meaning_en": "to cut"}, {"latin": "abgur", "meaning_en": "squirrel"}]}
    segs = [  # what the frame reader actually produced on Lesson #02 (misreads included)
        {"start": 36, "end": 40, "text": "ⴱ", "tifinagh": "ⴱ", "latin": "b", "gloss": None, "gloss_lang": None, "kind": "letter"},
        {"start": 48, "end": 66, "text": "ⵄⴱⵔ", "tifinagh": "ⵄⴱⵔ", "latin": "ɛbr", "gloss": "april", "gloss_lang": "en", "kind": "word"},
        {"start": 96, "end": 120, "text": "ⴰⴱⵅⵅⵍ", "tifinagh": "ⴰⴱⵅⵅⵍ", "latin": "abxxl", "gloss": "unknown", "gloss_lang": "en", "kind": "word"},
        {"start": 134, "end": 142, "text": "ⵄⴱⴱ", "tifinagh": "ⵄⴱⴱ", "latin": "ɛbb", "gloss": "carry", "gloss_lang": "en", "kind": "word"},
        {"start": 168, "end": 196, "text": "ⴱⵅⵔⵓ", "tifinagh": "ⴱⵅⵔⵓ", "latin": "bxru", "gloss": "none", "gloss_lang": "en", "kind": "word"},
    ]
    out = main.apply_lesson_vocabulary(segs, vocab)
    assert [(x["tifinagh"], x["latin"], x["gloss"]) for x in out] == [
        ("ⴱ", "b", "letter yab (b)"), ("ⵉⴱⴱⴰ", "ibba", "my father"), ("ⴰⴱⵖⴰⵏ", "abɣan", "black"),
        ("ⵉⴱⴱⵉ", "ibbi", "to cut"), ("ⴰⴱⴳⵓⵔ", "abgur", "squirrel")]
    assert [x["start"] for x in out] == [36, 48, 96, 134, 168]


def test_merge_frame_items_spelling_out():
    items = [{"t": 48, "kind": "partial", "tifinagh": "ⵉ", "latin": "i"},
             {"t": 50, "kind": "word", "tifinagh": "ⵉⴱ", "latin": "ib"},
             {"t": 52, "kind": "word", "tifinagh": "ⵉⴱⴱ", "latin": "ibb"},
             {"t": 54, "kind": "word", "tifinagh": "ⵉⴱⴱⴰ", "latin": "ibba", "meaning_en": "my father"},
             {"t": 56, "kind": "word", "tifinagh": "ⵉⴱⴱⴰ", "latin": "ibba", "meaning_en": "my father"}]
    segs = main.merge_frame_items(items, every=2.0)
    assert len(segs) == 1 and segs[0]["latin"] == "ibba" and segs[0]["start"] == 48.0 and segs[0]["end"] == 58.0


def test_gloss_key_tolerates_bidi_marks_and_dots():
    assert main._gloss_key("‫- ثم جاء صاحب البستان....") == main._gloss_key("ثم جاء صاحب البستان")
    t = main._parse_gloss_json('{"ثم جاء صاحب البستان": {"ca": "Llavors va arribar l’amo de l’hort", "ar": "x"}}')
    assert t[main._gloss_key("‫- ثم جاء صاحب البستان....")]["ca"].startswith("Llavors")


def test_apply_lesson_vocabulary_windows():
    """With audio chunk windows, each spoken word takes the on-screen span inside its window."""
    vocab = {"letters": [{"name": "yab", "latin": "b", "t0": 30, "t1": 60}],
             "words": [{"latin": "ibba", "meaning_en": "my father", "t0": 30, "t1": 60},
                       {"latin": "abghan", "meaning_en": "black", "t0": 90, "t1": 120},
                       {"latin": "ibbi", "meaning_en": "to cut", "t0": 150, "t1": 180},
                       {"latin": "abgur", "meaning_en": "squirrel", "t0": 180, "t1": 210}]}
    segs = [
        {"start": 36, "end": 40, "text": "ⴱ", "tifinagh": "ⴱ", "latin": "b", "gloss": None, "gloss_lang": None, "kind": "letter"},
        {"start": 48, "end": 66, "text": "x", "tifinagh": "ⵄⴱⵔ", "latin": "ɛbr", "gloss": "", "gloss_lang": None, "kind": "word"},
        {"start": 96, "end": 120, "text": "x", "tifinagh": "ⴰⴱⵅⵅⵍ", "latin": "abxxl", "gloss": "", "gloss_lang": None, "kind": "word"},
        {"start": 156, "end": 170, "text": "x", "tifinagh": "ⵄⴱⴱ", "latin": "ɛbb", "gloss": "", "gloss_lang": None, "kind": "word"},
        {"start": 182, "end": 196, "text": "x", "tifinagh": "ⴱⵅⵔⵓ", "latin": "bxru", "gloss": "", "gloss_lang": None, "kind": "word"},
    ]
    out = main.apply_lesson_vocabulary(segs, vocab)
    assert [(x["latin"], x["start"]) for x in out] == [("b", 36), ("ibba", 48), ("abɣan", 96), ("ibbi", 156), ("abgur", 182)]


def test_merge_subtitle_frames():
    items = [
        {"t": 60, "lines": [{"lang": "en", "text": "The cracks on their skin is filled with soil"}, {"lang": "fr", "text": "De terre, leurs gerçures remplies"},
                            {"lang": "ar", "text": "حتى امتلأت تشققات جلدهم بالتراب"}, {"lang": "shi", "text": "ifurskln nnsn kturn s wakal"}]},
        {"t": 61, "lines": [{"lang": "en", "text": "The cracks on their skin is filled with soil"}, {"lang": "shi", "text": "Ifurskln nnsn kturn s wakal"}]},
        {"t": 62, "lines": []},
        {"t": 63, "lines": [{"lang": "shi", "text": "ar ttaddun s uzmz"}, {"lang": "en", "text": "They go on in time"}]},
        {"t": 64, "lines": [{"lang": "shi", "text": "ar ttaddun s uzmz"}, {"lang": "en", "text": "They go on in time"}]},
        {"t": 70, "lines": [{"lang": "shi", "text": "misread once"}]},
        {"t": 75, "lines": [{"lang": "shi", "text": "Tamraght"}]},
        {"t": 76, "lines": [{"lang": "shi", "text": "Tamraght"}]},
        {"t": 77, "lines": [{"lang": "shi", "text": "Tamraght"}]},
        {"t": 80, "lines": [{"lang": "shi", "text": "ar ttaddun s uzmz."}, {"lang": "en", "text": "They go on in time"}]},
        {"t": 81, "lines": [{"lang": "shi", "text": "ar ttaddun s uzmz"}, {"lang": "en", "text": "They go on in time"}]},
    ]
    cues = main.merge_subtitle_frames(items, every=1.0)
    # the repeated chorus line at 80 s collapses into the first occurrence; the title card (no translation) is dropped
    assert [(c["start"], c["end"], c["text"]) for c in cues] == [(60.0, 62.0, "ifurskln nnsn kturn s wakal"), (63.0, 65.0, "ar ttaddun s uzmz")]
    assert cues[0]["gloss_lang"] == "en" and cues[0]["lines"]["ar"].startswith("حتى") and cues[0]["kind"] == "subtitle"


# ---------- speaker verification queue ----------

def test_verify_queue_reasons_and_resolve():
    au = "https://x/clip.mp3"
    mk = lambda **kw: client.post("/drills/", json=kw).json()["id"]
    agreed = mk(text_catalan="q agreed", text_tachelhit="azul fellawn", text_tachelhit_suggested="[azul fellawn]", audio_url=au)
    contested = mk(text_catalan="q contested", text_tachelhit="tanmmirt", text_tachelhit_suggested="[? tanmmirt bahra | ar timlilit]", audio_url=au)
    differs = mk(text_catalan="q differs", text_tachelhit="tanmmirt", text_tachelhit_suggested="[azul fellawn] · nota", audio_url=au)
    empty = mk(text_catalan="q empty", text_tachelhit="", text_tachelhit_suggested="[awal]", audio_url=au)
    subtitle = mk(text_catalan="q subtitle", text_tachelhit="", text_tachelhit_latin="kad lgudinu", text_tachelhit_suggested="ⴽⴰⴷ ⵍⴳⵓⴷⵉⵏⵓ", video_url="https://x/v.mp4")
    silent = mk(text_catalan="q no recording", text_tachelhit="", text_tachelhit_suggested="[? a | b]")

    r = client.get("/corpus/verify-queue", params={"limit": 500}).json()
    by = {d["id"]: d for d in r["drills"]}
    assert silent not in by
    assert by[agreed]["reason"] == "confirm" and by[agreed]["heard"] == ["azul fellawn"]
    assert by[contested]["reason"] == "contested" and by[contested]["heard"] == ["tanmmirt bahra", "ar timlilit"]
    assert by[differs]["reason"] == "differs" and by[differs]["heard"] == ["azul fellawn"]
    assert by[empty]["reason"] == "empty" and by[empty]["heard"] == ["awal"]
    assert by[subtitle]["reason"] == "subtitle" and by[subtitle]["heard"] == ["ⴽⴰⴷ ⵍⴳⵓⴷⵉⵏⵓ", "kad lgudinu"]
    ids = [d["id"] for d in r["drills"]]
    assert ids.index(differs) < ids.index(contested) < ids.index(empty) < ids.index(subtitle) < ids.index(agreed)  # most doubtful first
    assert all(r["counts"][k] >= 1 for k in ("differs", "contested", "empty", "subtitle"))
    only = client.get("/corpus/verify-queue", params={"limit": 0}).json()
    assert only["drills"] == [] and only["total"] == r["total"]
    assert client.get("/corpus/verify-queue", params={"reason": "nope"}).status_code == 400

    # resolving needs a registered user
    with as_stranger():  # settling which words a drill carries needs a name behind it
        assert client.post(f"/drills/{contested}/resolve", json={"text_tachelhit": "ar timlilit"}).status_code == 401
    token = register("verifier")
    h = {"X-User-Token": token}
    # accept one of the heard readings: text set, Latin filled, bracket dropped, verified
    d = client.post(f"/drills/{contested}/resolve", json={"text_tachelhit": "ar timlilit"}, headers=h).json()
    assert (d["text_tachelhit"], d["text_tachelhit_latin"], d["text_tachelhit_suggested"], d["verified"]) == ("ar timlilit", "ar timlilit", None, True)
    # keep the stored text: only the bracket goes, the rest of the suggestion stays
    d = client.post(f"/drills/{differs}/resolve", json={}, headers=h).json()
    assert (d["text_tachelhit"], d["text_tachelhit_suggested"], d["verified"]) == ("tanmmirt", "nota", True)
    # a drill without text cannot be "kept"
    assert client.post(f"/drills/{empty}/resolve", json={}, headers=h).status_code == 400
    # Tifinagh accepted on a subtitle drill keeps the existing Latin
    d = client.post(f"/drills/{subtitle}/resolve", json={"text_tachelhit": "ⴽⴰⴷ ⵍⴳⵓⴷⵉⵏⵓ"}, headers=h).json()
    assert (d["text_tachelhit"], d["text_tachelhit_latin"], d["text_tachelhit_suggested"]) == ("ⴽⴰⴷ ⵍⴳⵓⴷⵉⵏⵓ", "kad lgudinu", None)
    left = {x["id"] for x in client.get("/corpus/verify-queue", params={"limit": 500}).json()["drills"]}
    assert not ({contested, differs, subtitle} & left) and empty in left


def test_catalog_display_title_and_no_latin_gap():
    assert main.display_title("Inerzaf - Ha l3ar a bu R12 (With English, French, Arabic and Tachelhit subtitles)") == "Inerzaf - Ha l3ar a bu R12"
    assert main.display_title("Tasuta N-Imal (ⵜⵏⵉ) - Fadma - ⴼⴰⴹⵎⴰ (official music video 2021 )") == "Tasuta N-Imal (ⵜⵏⵉ) - Fadma - ⴼⴰⴹⵎⴰ"
    assert main.display_title("Learn Tamazight Language - Lesson #02 (Alphabets#02)") == "Learn Tamazight Language - Lesson #02 (Alphabets#02)"
    latin_only = client.post("/drills/", json={"text_tachelhit": "azul fellawn", "text_catalan": "gap latin a"}).json()["id"]
    tifinagh = client.post("/drills/", json={"text_tachelhit": "ⴰⵣⵓⵍ", "text_catalan": "gap latin b"}).json()["id"]
    ids = {d["id"] for d in client.get("/corpus/gaps", params={"kind": "no_latin", "limit": 500}).json()["drills"]}
    assert tifinagh in ids and latin_only not in ids


def test_recording_keeps_the_speakers_own_words(monkeypatch):
    """A take can carry the sentence as its speaker says it; same words as the drill are not kept."""
    import main
    monkeypatch.setattr(main.cloudinary.uploader, "upload", lambda *a, **k: {"secure_url": "https://res.cloudinary.com/x/video/upload/v1/tachelhit/recordings/rec_1.webm"})
    d = client.post("/drills/", json={"text_catalan": "Ensenya'm què faré", "text_tachelhit": "sn3t-i mayd-ddix ad igx", "variety": "tdl"}).json()
    r = client.post(f"/drills/{d['id']}/recordings", files={"file": ("take.webm", b"RIFF", "audio/webm")},
                    data={"text": "mlid mad rad skrɣ", "variety": "shi", "region": "Tiznit"})
    assert r.status_code == 200 and r.json()["text"] == "mlid mad rad skrɣ" and r.json()["variety"] == "shi"
    same = client.post(f"/drills/{d['id']}/recordings", files={"file": ("take2.webm", b"RIFF", "audio/webm")},
                       data={"text": "sn3t-i mayd-ddix ad igx"})
    assert same.json()["text"] is None
    lst = client.get(f"/drills/{d['id']}/recordings").json()
    assert [x["text"] for x in lst] == ["mlid mad rad skrɣ", None] and lst[0]["region"] == "Tiznit"
    # the drill's own words are untouched; an anonymous take can be edited by anyone
    assert client.get(f"/drills/{d['id']}").json()["text_tachelhit"] == "sn3t-i mayd-ddix ad igx"
    up = client.patch(f"/recordings/{lst[0]['id']}", json={"text": "mlid mad rad skrɣ ɣilad"})
    assert up.status_code == 200 and up.json()["text"] == "mlid mad rad skrɣ ɣilad"
    assert client.post(f"/drills/{d['id']}/recordings", files={"file": ("t.webm", b"RIFF", "audio/webm")}, data={"variety": "nope"}).status_code == 400


def test_catalan_voice_is_made_once_for_a_drill_that_lacks_it(monkeypatch):
    import main
    calls = []
    monkeypatch.setattr(main, "generate_catalan_tts", lambda text, did: calls.append(text) or f"https://x/tts_{did}.mp3")
    d = client.post("/drills/", json={"text_catalan": "Tinc mal de cap", "text_tachelhit": "ixxa iyi uqlal", "audio_url": "https://x/h.webm"}).json()
    client.put(f"/drills/{d['id']}", json={"audio_tts_url": None})
    before = len(calls)
    r = client.post("/tts/catalan", json={"drill_id": d["id"]}).json()
    assert r["url"].endswith(f"tts_{d['id']}.mp3") and r["cached"] is False and len(calls) == before + 1
    assert client.get(f"/drills/{d['id']}").json()["audio_tts_url"] == r["url"]
    assert client.post("/tts/catalan", json={"drill_id": d["id"]}).json()["cached"] is True and len(calls) == before + 1
    assert client.post("/tts/catalan", json={"drill_id": 999999}).status_code == 404


def test_startup_reaper_fails_dead_jobs_and_requeues_their_captures():
    from models import VideoProcessingJob as JobModel, CaptureRequest as ReqModel
    db = main.SessionLocal()
    job = JobModel(status="TRANSLATING", kind="auto"); db.add(job); db.commit(); db.refresh(job)
    done = JobModel(status="COMPLETED"); db.add(done); db.commit(); db.refresh(done)
    req = ReqModel(url="https://www.youtube.com/watch?v=x", status="claimed", job_id=job.id); db.add(req); db.commit(); db.refresh(req)
    n_jobs, n_req = main.reap_dead_jobs(db)
    assert n_jobs >= 1 and n_req == 1
    db.refresh(job); db.refresh(req); db.refresh(done)
    assert job.status == "FAILED" and "died with the server" in job.error_message
    assert req.status == "pending" and req.job_id is None and req.claimed_at is None
    assert done.status == "COMPLETED"
    db.close()


def test_admin_can_issue_a_reset_code_when_there_is_no_mail_server(monkeypatch):
    from models import User as UserModel
    monkeypatch.setattr(main, "_send_email", lambda *a, **k: False)  # no mail server
    u = client.post("/auth/signup", json={"email": "needs.reset@example.test", "password": "firstpass1", "username": "needsreset"}).json()
    admin = client.post("/users/register", json={"username": "reset_admin"}).json()
    db = main.SessionLocal(); row = db.query(UserModel).filter(UserModel.username == "reset_admin").first(); row.is_admin = True; db.commit(); db.close()
    h = {"X-User-Token": admin["token"]}
    assert client.post("/auth/admin-reset-code", json={"login": "needsreset"}).status_code in (401, 403)
    r = client.post("/auth/admin-reset-code", json={"login": "needs.reset@example.test"}, headers=h).json()
    assert len(r["code"]) == 6 and r["username"] == "needsreset" and r["mailed"] is False
    assert client.post("/auth/admin-reset-code", json={"login": "nobody-at-all"}, headers=h).status_code == 404
    # the person uses the code on the sign-in page
    assert client.post("/auth/reset", json={"email": "needs.reset@example.test", "code": "000000", "new_password": "secondpass1"}).status_code == 400
    done = client.post("/auth/reset", json={"email": "needs.reset@example.test", "code": r["code"], "new_password": "secondpass1"}).json()
    assert done["username"] == "needsreset" and done["token"]
    assert client.post("/auth/login", json={"login": "needsreset", "password": "secondpass1"}).status_code == 200
    assert u["username"] == "needsreset"


def test_admin_sets_the_mail_sender_from_the_app(monkeypatch):
    from models import User as UserModel, AppSetting as AppSettingModel
    admin = client.post("/users/register", json={"username": "mail_admin"}).json()
    db = main.SessionLocal(); row = db.query(UserModel).filter(UserModel.username == "mail_admin").first(); row.is_admin = True
    row.email = "mail.admin@example.test"; db.commit()
    h = {"X-User-Token": admin["token"]}
    assert client.get("/admin/mail").status_code in (401, 403)
    r = client.post("/admin/mail", json={"settings": {"SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": "587",
                                                      "SMTP_USER": "sender@example.test", "SMTP_PASS": "app-password",
                                                      "SMTP_FROM": "sender@example.test"}}, headers=h).json()
    assert r["ready"] is True and r["has_password"] is True and r["SMTP_HOST"] == "smtp.gmail.com"
    assert "SMTP_PASS" not in r  # the password never comes back
    assert main.mail_setting("SMTP_PASS") == "app-password"
    # the forgot flow no longer refuses for lack of a sender
    sent = []
    monkeypatch.setattr(main, "_send_email", lambda to, s, b: sent.append((to, s)) or True)
    client.post("/auth/signup", json={"email": "wants.code@example.test", "password": "firstpass1", "username": "wantscode"})
    assert client.post("/auth/forgot", json={"email": "wants.code@example.test"}).status_code == 200
    assert sent and sent[0][0] == "wants.code@example.test"
    assert client.post("/admin/mail/test", json={"to": None}, headers=h).json()["sent_to"] == "mail.admin@example.test"
    db.query(AppSettingModel).delete(); db.commit(); db.close()


def test_the_first_account_of_an_empty_library_can_administer_it():
    from models import User as UserModel
    db = main.SessionLocal()
    was = db.query(UserModel).filter(UserModel.is_admin.is_(True)).all()
    for u in was:
        u.is_admin = False
    db.commit()
    import secrets as _s
    main._register_attempts.clear()  # the suite has already used this IP's signup allowance
    tag = _s.token_hex(3)
    first = client.post("/auth/signup", json={"email": f"first.owner.{tag}@example.test", "password": "ownerpass1", "username": f"firstowner{tag}"}).json()
    assert first["is_admin"] is True  # nobody could administer the library: this account can
    second = client.post("/auth/signup", json={"email": f"later.person.{tag}@example.test", "password": "laterpass1", "username": f"laterperson{tag}"}).json()
    assert second["is_admin"] is False  # an admin exists now: everyone else is an ordinary user
    for u in was:
        u.is_admin = True
    db.commit(); db.close()


def test_the_drills_list_travels_compressed_and_without_empty_fields():
    """Issue #190: the list was 5,7 MB on every load, and 43% of that was field names.

    Two cheap habits keep it down, and both are easy to undo by accident:
    gzip on the way out, and no `"field":null` for the thirty-odd fields a drill usually
    leaves empty. A missing key and a null key mean the same thing to every reader we have.
    """
    plain = client.get("/drills/", headers={"Accept-Encoding": "identity"})
    assert plain.status_code == 200
    for drill in plain.json():
        assert None not in drill.values(), f"empty fields are being written out: {drill}"

    # TestClient decodes for us, so the header is what proves it was compressed.
    zipped = client.get("/drills/", headers={"Accept-Encoding": "gzip"})
    assert zipped.status_code == 200
    assert zipped.headers.get("content-encoding") == "gzip" or len(plain.content) < 1024
    assert zipped.json() == plain.json()  # same answer, fewer bytes


def test_asking_for_one_drill_does_not_return_the_whole_library():
    """Issue #190: editing a drill pulled every row a second time to find one of them."""
    everything = client.get("/drills/").json()
    assert everything, "the suite seeds drills"
    wanted = everything[0]["id"]
    one = client.get(f"/drills/?ids={wanted}").json()
    assert [d["id"] for d in one] == [wanted]


def test_the_credits_are_readable_from_inside_the_app():
    """Some of what this app is built on asks to be named where the work is used (CC BY, and the
    Awal set says it outright). A file in a repository nobody opens does not do that, so the app
    serves the same file — one source, so the two can never drift apart."""
    r = client.get("/credits")
    assert r.status_code == 200
    md = r.json()["markdown"]
    for owed in ("CIEMEN", "Awal", "IRCAM", "Common Voice", "amazic.cat"):
        assert owed in md, f"els crèdits no nomenen {owed}"
    assert r.json()["source"] == "docs/CREDITS.md", "s'ha llegit el fitxer de debò, no el text de reserva"


def test_a_newcomer_who_adds_something_is_told_what_to_do():
    """#202: since #184 adding needs a name, and a first-time visitor has none. The answer was
    401 «Sign in first (X-User-Token)» — in English, from a server, to somebody who pressed a
    button. The app asks first now, and if a path is ever missed, this is what they read."""
    with as_stranger():
        r = client.post("/drills/", json={"text_catalan": "aigua", "text_tachelhit": "aman"})
    assert r.status_code == 401
    said = r.json()["detail"]
    assert "perfil" in said.lower(), said
    assert "X-User-Token" not in said, "no li expliquem capçaleres a qui acaba d'arribar"


def test_a_failed_capture_can_be_retried_and_a_finished_one_forgotten():
    """#197: the queue could only be watched. A capture fails for reasons that pass — a video
    private for an hour, an old agent, the network — and the only way back was to paste the URL
    again. What is still running stays: forgetting it would leave the agent working for nobody."""
    from models import CaptureRequest

    db = main.SessionLocal()
    failed = CaptureRequest(url="https://youtu.be/failed-one", tag="prova", status="failed",
                            error="HTTP Error 403: Forbidden")
    running = CaptureRequest(url="https://youtu.be/running-one", tag="prova", status="processing")
    db.add(failed); db.add(running); db.commit()
    failed_id, running_id = failed.id, running.id
    db.close()

    rows = client.get("/capture/queue").json()
    assert rows["agent"]["latest"], "no sabem quina versió de l'agent s'ha publicat"
    mine = next(r for r in rows["requests"] if r["id"] == failed_id)
    assert mine["url"].endswith("failed-one"), "la fila ha de dir QUIN vídeo és"
    assert mine["error"] == "HTTP Error 403: Forbidden"

    assert client.post(f"/capture/{failed_id}/retry").json()["status"] == "pending"
    back = next(r for r in client.get("/capture/queue").json()["requests"] if r["id"] == failed_id)
    assert back["status"] == "pending" and not back["error"]

    assert client.delete(f"/capture/{failed_id}").status_code == 200
    assert client.delete(f"/capture/{running_id}").status_code == 409   # encara s'està fent

    db = main.SessionLocal()
    db.query(CaptureRequest).filter(CaptureRequest.id == running_id).delete()
    db.commit(); db.close()


def test_drafting_the_missing_words_never_touches_the_speakers_own_text(monkeypatch):
    """101 recordings have a voice and a meaning but nobody has written what is said, which is
    what blocks whole stories from becoming lessons. The listener can DRAFT them; it cannot
    decide them. A machine reading goes to text_tachelhit_suggested and waits for a person."""
    import dialect

    hdr = {"X-User-Token": register("text_drafter")}
    db = main.SessionLocal()
    me = db.query(main.UserModel).filter(main.UserModel.username == "text_drafter").first()
    me.is_admin = True
    db.commit(); db.close()

    mute = client.post("/drills/", headers=hdr, json={
        "text_catalan": "El llop i la seva ombra", "text_tachelhit": "",
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/wolf.mp3", "variety": "tzm"}).json()
    spoken = client.post("/drills/", headers=hdr, json={
        "text_catalan": "aigua", "text_tachelhit": "aman",   # a speaker wrote this one
        "audio_url": "https://res.cloudinary.com/x/video/upload/v1/aman.mp3", "variety": "tzm"}).json()

    monkeypatch.setattr(dialect, "transcribe", lambda *a, **k: {"latin": "uššn d umalu nns", "tifinagh": ""})
    assert client.post("/drills/transcribe-missing?limit=5", headers=hdr).json()["status"] == "started"
    for _ in range(100):                      # it runs on a thread
        if not client.get("/drills/transcribe-missing/status").json()["running"]:
            break
        time.sleep(0.05)

    drafted = client.get(f"/drills/{mute['id']}").json()
    assert drafted["text_tachelhit_suggested"] == "uššn d umalu nns"
    assert not (drafted.get("text_tachelhit") or ""), "la paraula del parlant no la toca cap màquina"

    kept = client.get(f"/drills/{spoken['id']}").json()
    assert kept["text_tachelhit"] == "aman"
    assert not kept.get("text_tachelhit_suggested"), "qui ja té paraules escrites no es toca"


def test_la_biblioteca_diu_si_ja_te_una_frase_que_soni_igual():
    """Three doors create sentences and none looked whether the library already held this one.

    The comparison is by SOUND, not by spelling, because a text search would never put «aghrum»
    and «aɣrum» together -- and those are the copies that actually happen. Nothing is forbidden:
    saying the same sentence another way is what the variants are for. This only lets the person
    know before writing a second copy of what we have."""
    from test_api import client

    first = client.post("/drills/", json={
        "text_catalan": "el pa", "text_tachelhit": "a\u0263rum",
        "author": "Halima"}).json()

    # the same words in another spelling: no LIKE would find this
    r = client.get("/drills/similar", params={"text": "aghrum", "field": "tachelhit"}).json()
    assert first["id"] in [m["id"] for m in r["matches"]], r

    # and in Tifinagh
    r = client.get("/drills/similar", params={"text": "\u2d30\u2d56\u2d54\u2d53\u2d4e"}).json()
    assert first["id"] in [m["id"] for m in r["matches"]]

    # what it is not: another sentence
    r = client.get("/drills/similar", params={"text": "aman d waman"}).json()
    assert first["id"] not in [m["id"] for m in r["matches"]]

    # the sentence being written does not match itself
    r = client.get("/drills/similar", params={"text": "a\u0263rum", "exclude_id": first["id"]}).json()
    assert first["id"] not in [m["id"] for m in r["matches"]]

    # too short to mean anything
    assert client.get("/drills/similar", params={"text": "a"}).json()["matches"] == []

    # by meaning too, for when only the Catalan is written yet
    r = client.get("/drills/similar", params={"text": "el pa", "field": "catalan"}).json()
    assert first["id"] in [m["id"] for m in r["matches"]]


def test_canviar_una_etiqueta_no_reescriu_el_text_del_parlant():
    """The edit sheet used to PUT the whole row, so a new tag carried a stale copy of every other
    field -- the speaker's own words included -- and quietly reverted anything changed meanwhile.
    It now sends only what it touched. This is the server half: a partial body must leave the
    rest exactly as it was."""
    from test_api import client

    d = client.post("/drills/", json={
        "text_catalan": "la casa", "text_tachelhit": "tigmmi", "tag": "primer",
        "text_tachelhit_suggested": "esborrany de la m\u00e0quina"}).json()

    client.put(f"/drills/{d['id']}", json={"tag": "segon"})
    back = client.get(f"/drills/{d['id']}").json()
    assert back["tag"] == "segon"
    assert back["text_tachelhit"] == "tigmmi", "el text del parlant no es toca"
    assert back["text_catalan"] == "la casa"
    assert back["text_tachelhit_suggested"] == "esborrany de la m\u00e0quina"


def test_qui_pregunta_sap_quin_numero_te():
    """The screen has to know whose a sentence is to say so before the work rather than after the
    save; `may_change` compares ids, and /users/me did not give one."""
    from test_api import client

    me = client.get("/users/me").json()
    assert isinstance(me.get("id"), int) and me["id"] > 0, me


def test_cap_resposta_de_l_api_es_pot_reaprofitar():
    """Una llista demanada just després d'escriure-hi no pot arribar d'abans d'escriure-hi.

    Va passar de debò: una petició creada correctament a «Posa-hi veu» va aparèixer com a «res
    pendent aquí», perquè la llista que es va tornar a demanar venia de just abans de crear-la.
    Cap resposta d'aquesta API portava `Cache-Control`, i sense cap directiva un navegador aplica
    el seu propi criteri.

    Res del que torna val per a dues persones diferents ni per a dos moments diferents: les
    llistes depenen de qui pregunta i canvien així que algú escriu."""
    from test_api import client, register

    for path in ("/health", "/petitions?kind=open", "/drills/?limit=1", "/method/"):
        r = client.get(path)
        assert r.headers.get("cache-control") == "no-store", (path, dict(r.headers))

    # i el cas que ho va destapar, de punta a punta: demanar-ho i veure-ho
    hdr = {"X-User-Token": register("petition_asker")}
    before = client.get("/petitions?kind=open").json()["total"]
    made = client.post("/petitions", headers=hdr,
                       json={"text_catalan": "Em sap molt de greu", "note": None})
    assert made.status_code == 200, made.text
    after = client.get("/petitions?kind=open").json()
    assert after["total"] == before + 1
    assert made.json()["id"] in [x["drill"]["id"] for x in after["items"]], \
        "el que acabes de demanar ha de sortir a la llista"
