"""Dictionary + conjugation grounding (lexicon.py) with small fixtures instead of the HF download."""
import json
import os

import lexicon
from test_api import client, main  # noqa: F401


def _fixture(tmp_path, monkeypatch):
    d = tmp_path / "lex"; d.mkdir()
    (d / "translations.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"entry_id": 1, "english": "hand", "pos": ["n."], "sense": 1, "tashlhit": "afus", "tashlhit_tifinagh": "ⴰⴼⵓⵙ",
         "example": "ifka-yi afus", "example_tifinagh": "ⵉⴼⴽⴰ ⵢⵉ ⴰⴼⵓⵙ", "needs_review": False},
        {"entry_id": 2, "english": "abandon", "pos": ["v."], "sense": 1, "tashlhit": "fel", "tashlhit_tifinagh": "ⴼⵍ",
         "example": "ifel tarwa nnes", "example_tifinagh": "", "needs_review": False},
        {"entry_id": 3, "english": "bad row", "pos": [], "sense": 1, "tashlhit": "xxx", "needs_review": True},
    ]), encoding="utf-8")
    (d / "verb_type_index.json").write_text(json.dumps([{"verb": "ⴼⵍ", "type": 1, "french": "laisser", "arabic": "ترك"}], ensure_ascii=False), encoding="utf-8")
    (d / "amazigh_conjugations.json").write_text(json.dumps([{"verb": "ⴼⵍ", "type": 1, "tenses": {
        "Accompli": {"1sg_m": "ⴼⵍⵖ", "1sg_f": "ⴼⵍⵖ", "3sg_m": "ⵉⴼⵍ", "3sg_f": "ⵜⴼⵍ"}}}], ensure_ascii=False), encoding="utf-8")
    (d / "dglai.json").write_text(json.dumps({"1": {"id": "1", "tifinagh": "ⴰⴳⵓⴷⴰⵍ", "latin": "agudal", "grammar": "nom masculin",
        "meaning_fr": "pâturage réservé, mis en défens", "meaning_ar": "محمية رعوية", "lang": "amz"}}, ensure_ascii=False), encoding="utf-8")
    files = {"dglai_clean (1).json": "dglai.json", "data/translations.jsonl": "translations.jsonl", "verb_type_index.json": "verb_type_index.json", "amazigh_conjugations.json": "amazigh_conjugations.json"}
    monkeypatch.setattr(lexicon, "_fetch", lambda repo, fname: str(d / files[fname]))
    assert lexicon.load(force=True)


def test_lookup_matches_across_scripts_and_finds_conjugated_forms(tmp_path, monkeypatch):
    _fixture(tmp_path, monkeypatch)
    hits = lexicon.lookup("wana yijlan fkas ⴰⴼⵓⵙ")
    words = {h["word"]: h for h in hits}
    assert "ⴰⴼⵓⵙ" in words and "hand" in words["ⴰⴼⵓⵙ"]["dictionary"][0]["english"]
    hits = lexicon.lookup("ifel tarwa")
    assert any(c["tense"] == "Accompli" and "3sg_m" in c["persons"] for h in hits for c in h["conjugation"])
    lines = lexicon.grounding_lines("afus ifel")
    assert any("[Oulhaj]" in l and "hand" in l for l in lines) and any("[IRCAM]" in l for l in lines)


def test_ircam_general_dictionary_grounds_central_atlas_words(tmp_path, monkeypatch):
    _fixture(tmp_path, monkeypatch)
    hits = lexicon.lookup("agoudal ⴰⴳⵓⴷⴰⵍ")
    assert hits and hits[0]["ircam"][0]["french"].startswith("pâturage")
    assert any("[IRCAM-DGLAI]" in l and "agudal" in l for l in lexicon.grounding_lines("agudal"))
    assert lexicon.status()["dglai_forms"] == 1


def test_endpoint_and_drill_context_carry_the_grounding(tmp_path, monkeypatch):
    _fixture(tmp_path, monkeypatch)
    r = client.get("/lexicon/lookup", params={"q": "afus"})
    assert r.status_code == 200 and r.json()["hits"][0]["dictionary"][0]["tifinagh"] == "ⴰⴼⵓⵙ"
    r = client.post("/drills/", json={"text_catalan": "la mà", "text_tachelhit": "ⴰⴼⵓⵙ"})
    did = r.json()["id"]
    db = main.SessionLocal()
    try:
        ctx = main._drill_context(db.query(main.DrillModel).filter(main.DrillModel.id == did).first())
    finally:
        db.close()
    assert "DICCIONARI I CONJUGACIONS" in ctx and "[Oulhaj]" in ctx
