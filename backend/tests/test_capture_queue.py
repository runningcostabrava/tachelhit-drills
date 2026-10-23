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


def test_un_reclam_que_no_torna_caduca_i_al_tercer_cop_es_rendeix():
    """La petició 113 va passar a «claimed» a les 09:29 i no va arribar mai ni a «processing».

    L'agent se l'enduu mentre la baixa i la puja; quan ha pujat diu «processing» o «done». Si no
    diu mai res —ha petat, s'ha quedat sense xarxa, la màquina s'ha adormit— la fila es quedava a
    «claimed» per sempre: la cua ensenyava «en curs» indefinidament i l'agent no la tornava a
    agafar mai, perquè ja no era pending.

    I la desfà qui mira. Quan l'agent mor amb una petició a la mà, ningú no consulta
    /capture/pending: l'única cosa que se'n pot assabentar és la pantalla que algú obre per
    preguntar per què s'ha encallat.
    """
    from datetime import datetime, timedelta
    import main
    from test_api import client

    db = main.SessionLocal()
    try:
        # les altres proves deixen peticions esperant, i /capture/pending torna la mes antiga
        for other in db.query(main.CaptureRequestModel).filter(
                main.CaptureRequestModel.status.in_(("pending", "claimed"))).all():
            other.status = "done"
        req = main.CaptureRequestModel(url="https://www.youtube.com/shorts/Ntn-N0tLMmk",
                                       tag="amazigament", status="pending")
        db.add(req); db.commit(); db.refresh(req)
        rid = req.id
    finally:
        db.close()

    # l'agent se l'enduu
    got = client.get("/capture/pending").json()["request"]
    assert got and got["id"] == rid

    def age(minutes):
        d = main.SessionLocal()
        try:
            r = d.query(main.CaptureRequestModel).filter(main.CaptureRequestModel.id == rid).first()
            r.claimed_at = datetime.utcnow() - timedelta(minutes=minutes)
            d.commit()
        finally:
            d.close()

    def state():
        return next(x for x in client.get("/capture/queue").json()["requests"] if x["id"] == rid)

    # encara calenta: no es toca
    age(5)
    assert state()["status"] == "claimed"

    # abandonada: torna a la cua, i l'agent la pot tornar a agafar
    age(45)
    assert state()["status"] == "pending", "mirar la cua ha de desfer un reclam mort"
    assert client.get("/capture/pending").json()["request"]["id"] == rid

    # i no pot girar per sempre: al tercer intent es rendeix amb la raó escrita
    age(45)
    assert state()["status"] == "pending"
    client.get("/capture/pending")
    age(45)
    dead = state()
    assert dead["status"] == "failed", dead
    assert "agent" in (dead.get("error") or "").lower()
