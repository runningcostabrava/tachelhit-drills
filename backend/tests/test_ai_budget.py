"""Gemini meter: every call is priced and recorded; the monthly budget stops calls; the
per-person daily cap stops the interactive endpoints with a 429 and a clear message."""
import pytest
from test_api import client
import main
import ai_budget
import gemini_client
from models import GeminiUsage


FAKE = {"candidates": [{"content": {"parts": [{"text": "ⴰⵣⵓⵍ | Hola"}]}}],
        "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 200, "thoughtsTokenCount": 0}}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_PROXY_URL", raising=False)
    monkeypatch.setenv("GEMINI_MONTHLY_BUDGET_EUR", "10")
    monkeypatch.setenv("AI_DAILY_LIMIT_ANON", "2")
    monkeypatch.setenv("AI_DAILY_LIMIT", "3")
    with main.SessionLocal() as db:
        db.query(GeminiUsage).delete()
        db.commit()
    main.ai_meter._spent_cache = (0.0, 0)
    yield


def _fake_post(ok=True):
    class R:
        status_code = 200 if ok else 500
        text = "boom"
        def json(self):
            return FAKE
    return lambda *a, **k: R()


def test_pricing_flash_tokens():
    # 1000 in + 200 out on gemini-2.5-flash = 0.0003 + 0.0005 USD = 0.0008 USD -> ×0.92
    micro = ai_budget.cost_micro_eur("gemini-2.5-flash", 1000, 200, 0)
    assert micro == round(0.0008 * 0.92 * 1_000_000)
    assert ai_budget.price_for("gemini-2.5-flash-preview-09-2025") == ai_budget.price_for("gemini-2.5-flash")
    assert ai_budget.cost_micro_eur("gemini-2.5-flash-image", 0, 0, 1) == round(0.039 * 0.92 * 1_000_000)


def test_every_call_is_recorded(monkeypatch):
    monkeypatch.setattr(gemini_client.requests, "post", _fake_post())
    gemini_client.gemini_generate("sys", [{"role": "user", "text": "hi"}])
    with main.SessionLocal() as db:
        rows = db.query(GeminiUsage).all()
    assert len(rows) == 1 and rows[0].prompt_tokens == 1000 and rows[0].output_tokens == 200
    assert rows[0].cost_micro_eur > 0 and rows[0].ok and rows[0].feature == "pipeline"


def test_failed_call_is_recorded_without_cost(monkeypatch):
    monkeypatch.setattr(gemini_client.requests, "post", _fake_post(ok=False))
    with pytest.raises(RuntimeError):
        gemini_client.gemini_generate("sys", [{"role": "user", "text": "hi"}])
    with main.SessionLocal() as db:
        row = db.query(GeminiUsage).one()
    assert row.ok is False and row.cost_micro_eur == 0


def test_monthly_budget_stops_calls(monkeypatch):
    monkeypatch.setattr(gemini_client.requests, "post", _fake_post())
    with main.SessionLocal() as db:
        db.add(GeminiUsage(model="gemini-2.5-flash", feature="pipeline", cost_micro_eur=10_000_000))
        db.commit()
    main.ai_meter._spent_cache = (0.0, 0)
    with pytest.raises(gemini_client.BudgetExceeded):
        gemini_client.gemini_generate("sys", [{"role": "user", "text": "hi"}])
    r = client.post("/ai/ask", json={"question": "què vol dir azul?"})
    assert r.status_code == 429 and "Pressupost" in r.json()["detail"]
    assert client.get("/ai/status").json()["available"] is False
    assert client.get("/ai/usage").json()["month"]["remaining_eur"] == 0


def test_anonymous_daily_cap_then_429(monkeypatch):
    monkeypatch.setattr(gemini_client.requests, "post", _fake_post())
    monkeypatch.setattr(main, "_build_system_instruction", lambda db: "sys")
    for _ in range(2):
        assert client.post("/ai/ask", json={"question": "hola?"}).status_code == 200
    r = client.post("/ai/ask", json={"question": "hola?"})
    assert r.status_code == 429 and "entra amb el teu compte" in r.json()["detail"]
    u = client.get("/ai/usage").json()
    assert u["today"] == {"used": 2, "limit": 2, "remaining": 0}
    with main.SessionLocal() as db:
        feats = {r.feature for r in db.query(GeminiUsage).all()}
    assert feats == {"ask"}  # the gate's tag reached the meter


def test_signed_in_user_has_own_cap_and_admin_none(monkeypatch):
    monkeypatch.setattr(gemini_client.requests, "post", _fake_post())
    monkeypatch.setattr(main, "_build_system_instruction", lambda db: "sys")
    tok = client.post("/users/register", json={"username": "ai_budget_user"}).json()["token"]
    h = {"X-User-Token": tok}
    for _ in range(3):
        assert client.post("/ai/ask", json={"question": "hola?"}, headers=h).status_code == 200
    assert client.post("/ai/ask", json={"question": "hola?"}, headers=h).status_code == 429
    assert client.get("/ai/usage", headers=h).json()["today"]["remaining"] == 0
    # admin: unlimited interactions, but still inside the money budget
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.test")
    a = client.post("/auth/signup", json={"email": "boss@example.test", "password": "secret-pass-1", "username": "ai_boss"}).json()
    ha = {"X-User-Token": a["token"]}
    for _ in range(5):
        assert client.post("/ai/ask", json={"question": "hola?"}, headers=ha).status_code == 200
    u = client.get("/ai/usage", headers=ha).json()
    assert u["today"]["limit"] is None and "by_feature" in u["month"] and u["month"]["by_feature"]["ask"]["calls"] >= 5
