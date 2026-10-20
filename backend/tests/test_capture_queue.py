"""GET /capture/queue lists requests newest first without claiming anything."""
from test_api import client


def test_queue_lists_without_claiming():
    a = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=queue00000a", "tag": "q-a"}).json()["request_id"]
    b = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=queue00000b", "tag": "q-b"}).json()["request_id"]
    q = client.get("/capture/queue", params={"limit": 5}).json()
    ids = [r["id"] for r in q["requests"]]
    assert ids[:2] == [b, a] and all(r["status"] == "pending" for r in q["requests"][:2])
    assert "agent" in q and "online" in q["agent"]
    # still pending: the queue endpoint did not claim them
    assert client.get(f"/capture/{a}").json()["status"] == "pending"


def test_queue_reports_a_count_not_the_id_list():
    import json
    import main
    from models import VideoProcessingJob, CaptureRequest
    rid = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=queue00000c", "tag": "q-c"}).json()["request_id"]
    db = main.SessionLocal()
    try:
        job = VideoProcessingJob(status="COMPLETED", processing_log=json.dumps({"drills_created": [467, 468, 469]}))
        db.add(job)
        db.flush()
        req = db.query(CaptureRequest).filter(CaptureRequest.id == rid).first()
        req.job_id = job.id
        db.commit()
    finally:
        db.close()
    row = next(r for r in client.get("/capture/queue", params={"limit": 10}).json()["requests"] if r["id"] == rid)
    assert row["drills_created"] == 3
    assert client.get(f"/capture/{rid}").json()["drills_created"] == 3
