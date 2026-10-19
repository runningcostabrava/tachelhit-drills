"""read_page_text: a narrated page becomes «line | meaning» lines (deduplicated, no titles)."""
import main


def test_page_lines_parsed_and_deduplicated(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "gemini_available", lambda: True)
    monkeypatch.setattr(main, "extract_frames", lambda *a, **k: [(0.0, str(tmp_path / "f.jpg")), (6.0, str(tmp_path / "f.jpg"))])
    (tmp_path / "f.jpg").write_bytes(b"\xff\xd8\xff")
    import gemini_client
    answer = ("ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ | L'home i el temps\n"
              "- ⵉⵙⵙⵏ ⵓⴼⴳⴰⵏ ⴰⵣⵎⵣ ⵏⵏⵙ. | L'home coneix el seu temps.\n"
              "ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ | L'home i el temps\n"
              "no pipe here\n")
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": answer}]}}]})
    lines = main.read_page_text("video.mp4", str(tmp_path))
    assert lines == ["ⴰⴼⴳⴰⵏ ⴷ ⵓⵣⵎⵣ | L'home i el temps", "ⵉⵙⵙⵏ ⵓⴼⴳⴰⵏ ⴰⵣⵎⵣ ⵏⵏⵙ. | L'home coneix el seu temps."]


def test_detect_text_mode_knows_page(monkeypatch, tmp_path):
    (tmp_path / "f.jpg").write_bytes(b"\xff\xd8\xff")
    import gemini_client
    monkeypatch.setattr(gemini_client, "_generate_content", lambda payload, timeout: {"candidates": [{"content": {"parts": [{"text": "page"}]}}]})
    assert main.detect_text_mode([(0.0, str(tmp_path / "f.jpg"))]) == "page"
