"""The Gemini egress proxy: when the configured host is gone (the web app was renamed), the
project's other hosts are tried and the working one is remembered."""
import gemini_client


def test_proxy_falls_back_to_the_projects_other_hosts(monkeypatch):
    monkeypatch.setenv("GEMINI_PROXY_URL", "https://old-name.vercel.app/api/gemini")
    monkeypatch.setattr(gemini_client, "_proxy_ok", None)
    seen = []

    class R:
        def __init__(self, code, text="", data=None): self.status_code, self.text, self._d = code, text, data or {}
        def json(self): return self._d

    def fake_post(url, **kw):
        seen.append(url)
        if "old-name" in url:
            return R(404, "The deployment could not be found on Vercel. DEPLOYMENT_NOT_FOUND")
        if "tamazight-drills" in url:
            return R(200, "", {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
        return R(500, "nope")

    monkeypatch.setattr(gemini_client.requests, "post", fake_post)
    out = gemini_client._generate_content({"contents": []}, 30)
    assert out["candidates"][0]["content"]["parts"][0]["text"] == "ok"
    assert seen[0].startswith("https://old-name") and any("tamazight-drills" in u for u in seen)
    assert gemini_client._proxy_ok and "tamazight-drills" in gemini_client._proxy_ok
    # the working host is used first next time
    seen.clear()
    gemini_client._generate_content({"contents": []}, 30)
    assert "tamazight-drills" in seen[0]


def test_direct_google_when_no_proxy_answers(monkeypatch):
    monkeypatch.setenv("GEMINI_PROXY_URL", "https://old-name.vercel.app/api/gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_client, "_proxy_ok", None)
    seen = []

    class R:
        def __init__(self, code, text="", data=None): self.status_code, self.text, self._d = code, text, data or {}
        def json(self): return self._d

    def fake_post(url, **kw):
        seen.append(url)
        if "generativelanguage" in url:
            return R(200, "", {"candidates": [{"content": {"parts": [{"text": "direct"}]}}]})
        return R(404, "DEPLOYMENT_NOT_FOUND")

    monkeypatch.setattr(gemini_client.requests, "post", fake_post)
    out = gemini_client._generate_content({"contents": []}, 30)
    assert out["candidates"][0]["content"]["parts"][0]["text"] == "direct"
    assert any("generativelanguage" in u for u in seen)
