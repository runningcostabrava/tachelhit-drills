"""
Backend API tests. Run from backend/:  python -m pytest tests -q

Uses an isolated SQLite database and FastAPI's in-process TestClient —
no server, no external services (endpoints that call HF Spaces/Cloudinary
are not exercised here).
"""
import os
import sys

# Isolated DB — must be set before importing main (module reads env at import)
TEST_DB = "test_drills.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"
os.environ.pop("CHECK_SCHEMA", None)
os.environ.pop("API_KEY", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)
client.__enter__()  # run lifespan: create tables + seed samples


def register(username: str) -> str:
    main._register_attempts.clear()  # tests share one client IP
    r = client.post("/users/register", json={"username": username})
    assert r.status_code == 200, r.text
    return r.json()["token"]


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


def test_pronunciation_best_match_is_script_aware():
    class FakeDrill:
        text_tachelhit = "ⵜⴰⵏⵎⵎⵉⵔⵜ"
        text_tachelhit_latin = "tanmmirt"
    # Latin ASR output must match the Latin field, not collapse vs Tifinagh
    script, target, score = main._best_pronunciation_match("tanmmirt", FakeDrill())
    assert script == "latin" and score > 0.9
    # Tifinagh ASR output matches the Tifinagh field
    script, _, score = main._best_pronunciation_match("ⵜⴰⵏⵎⵎⵉⵔⵜ", FakeDrill())
    assert script == "tifinagh" and score > 0.9


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
