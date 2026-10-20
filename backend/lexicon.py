"""Lexicon grounding for the tutor and the word explanations.

Two published resources, fetched from HuggingFace on first use into backend/knowledge/lexicon/
(gitignored, like the grammar text):
- Lahcen Oulhaj's English–Tashlhit dictionary (Tamazight-NLP/English-Tashlhit-Dictionary):
  50k Tashlhit translations with Tifinagh and example sentences. All rights to the content
  belong to the author; used here only as private grounding for a personal learning app.
- IRCAM "Manuel de conjugaison de l'amazighe" tables (Tamazight-NLP/ircam-conjugations,
  CC BY-NC 4.0): 3,507 verbs, 6 tenses, 12 person/gender forms, with French/Arabic meanings.
- IRCAM DGLAI, the general dictionary of standard Moroccan Amazigh (Tamazight-NLP/ircam-dglai,
  CC BY-NC 4.0): 18,491 entries with Tifinagh, Latin, grammar and French/Arabic meanings. It
  covers the Central Atlas side of the vocabulary that the Tashlhit dictionary lacks.

Words are matched across scripts and spellings through transliteration.to_forms(): first on
the exact spelling (clean_latin, gemination kept: «mayd» ≠ «maydd»), then, only when that
finds nothing, on the loose key (gemination collapsed: «afous» = «afus» = «ⴰⴼⵓⵙ»).
"""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Dict, List, Optional

from transliteration import to_forms

LEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge", "lexicon")
DICT_REPO = "Tamazight-NLP/English-Tashlhit-Dictionary"
CONJ_REPO = "Tamazight-NLP/ircam-conjugations"
DGLAI_REPO = "Tamazight-NLP/ircam-dglai"
DGLAI_FILE = "dglai_clean (1).json"
ATTRIBUTION = ("Diccionari anglès–taixelhit de Lahcen Oulhaj (tots els drets de l'autor); "
               "conjugacions del Manuel de conjugaison de l'amazighe, IRCAM 2012 (CC BY-NC 4.0); "
               "Dictionnaire Général de la Langue Amazighe Informatisé, IRCAM (CC BY-NC 4.0)")

_lock = threading.Lock()
_state = {"loaded": False, "loading": False, "error": None, "dict_forms": 0, "conj_forms": 0, "verbs": 0, "dglai_forms": 0}
# strict key (exact spelling) -> entries; loose key -> entries
_dict_strict: Dict[str, List[dict]] = {}
_dict_loose: Dict[str, List[dict]] = {}
_conj_strict: Dict[str, List[dict]] = {}
_conj_loose: Dict[str, List[dict]] = {}
_verb_meta: Dict[str, dict] = {}
_dglai_strict: Dict[str, List[dict]] = {}
_dglai_loose: Dict[str, List[dict]] = {}

_WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)
_STOP = {"d", "n", "s", "a", "i", "u", "ad", "ar", "ur", "da", "is", "ma", "mi", "g", "f"}
_PERSON = re.compile(r"^[123](sg|pl)(_[mf])?$")
_LABIAL = str.maketrans("", "", "ʷʸ°")


def _keys(s: Optional[str]) -> tuple:
    """(strict, loose) keys of one form; ('', '') when it has no letters."""
    try:
        f = to_forms(s or "")
        return f["clean_latin"].strip().lower().translate(_LABIAL), f["key"].strip()
    except Exception:
        return "", ""


def _fetch(repo: str, fname: str) -> str:
    from huggingface_hub import hf_hub_download
    os.makedirs(LEX_DIR, exist_ok=True)
    return hf_hub_download(repo, fname, repo_type="dataset", local_dir=LEX_DIR)


def _add(strict_idx, loose_idx, sk, lk, item, cap):
    if sk and len(strict_idx.setdefault(sk, [])) < cap:
        strict_idx[sk].append(item)
    if lk and len(loose_idx.setdefault(lk, [])) < cap:
        loose_idx[lk].append(item)


def load(force: bool = False) -> bool:
    """Download (once) and index both resources. Safe to call from several threads."""
    with _lock:
        if _state["loaded"] and not force:
            return True
        _state["loading"] = True
        try:
            # dictionary: one entry per Tashlhit form, collecting its English senses
            by_form: Dict[str, dict] = {}
            with open(_fetch(DICT_REPO, "data/translations.jsonl"), encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r.get("needs_review"):
                        continue
                    forms = [f.strip() for f in re.split(r"[,/;]", r.get("tashlhit") or "") if f.strip()]
                    for f in forms[:3]:
                        e = by_form.get(f)
                        if e is None:
                            e = by_form[f] = {"tashlhit": f, "tifinagh": r.get("tashlhit_tifinagh") or "", "english": [],
                                              "pos": [], "example": r.get("example") or "",
                                              "example_tifinagh": r.get("example_tifinagh") or ""}
                        en = (r.get("english") or "").strip()
                        if en and en.lower() not in {x.lower() for x, _ in e["english"]} and len(e["english"]) < 60:
                            e["english"].append((en, int(r.get("sense") or 1)))
                        for p in r.get("pos") or []:
                            if p not in e["pos"]:
                                e["pos"].append(p)
                        if not e["example"] and r.get("example"):
                            e["example"], e["example_tifinagh"] = r["example"], r.get("example_tifinagh") or ""
            ds: Dict[str, List[dict]] = {}
            dl: Dict[str, List[dict]] = {}
            for f, e in by_form.items():
                e["pos"] = ", ".join(e["pos"])
                # basic senses first: the dictionary's own sense number (1 = primary meaning of
                # that English word), then short headwords («Hand», «Arm») before idiom glosses
                # («Applause», «Busy»), so the 12 kept are the ones a learner needs
                e["english"] = [x for x, _ in sorted(e["english"], key=lambda t: (t[1], len(t[0]), t[0].lower()))][:12]
                sk, lk = _keys(f)
                _add(ds, dl, sk, lk, e, 6)
            # verbs
            meta: Dict[str, dict] = {}
            for v in json.load(open(_fetch(CONJ_REPO, "verb_type_index.json"), encoding="utf-8")):
                sk, _ = _keys(v.get("verb"))
                if sk:
                    meta.setdefault(sk, {"verb": v.get("verb"), "french": v.get("french") or "", "arabic": v.get("arabic") or ""})
            cs: Dict[str, List[dict]] = {}
            cl: Dict[str, List[dict]] = {}
            for v in json.load(open(_fetch(CONJ_REPO, "amazigh_conjugations.json"), encoding="utf-8")):
                vk, _ = _keys(v.get("verb"))
                m = meta.get(vk, {"verb": v.get("verb"), "french": "", "arabic": ""})
                for tense, persons in (v.get("tenses") or {}).items():
                    forms: Dict[str, List[str]] = {}
                    for person, form in persons.items():
                        if _PERSON.match(person) and form:
                            forms.setdefault(form, []).append(person)
                    for form, plist in forms.items():
                        sk, lk = _keys(form)
                        if sk and sk != vk:
                            _add(cs, cl, sk, lk, {"form": form, "verb": m["verb"], "french": m["french"],
                                                  "arabic": m["arabic"], "tense": tense, "persons": plist}, 4)
            # IRCAM general dictionary (standard Amazigh): optional, the rest works without it
            gs: Dict[str, List[dict]] = {}
            gl: Dict[str, List[dict]] = {}
            try:
                raw = json.load(open(_fetch(DGLAI_REPO, DGLAI_FILE), encoding="utf-8"))
                def _s(v) -> str:  # fields come as strings or lists of strings
                    if isinstance(v, (list, tuple)):
                        return "; ".join(str(x).strip() for x in v if x)
                    return str(v or "").strip()
                for rec in (raw.values() if isinstance(raw, dict) else raw):
                    if not isinstance(rec, dict):
                        continue
                    tif, lat = _s(rec.get("tifinagh")), _s(rec.get("latin"))
                    if not (tif or lat):
                        continue
                    e = {"tifinagh": tif, "latin": lat, "grammar": _s(rec.get("grammar")), "french": _s(rec.get("meaning_fr")),
                         "arabic": _s(rec.get("meaning_ar")), "construct": _s(rec.get("construct_state"))}
                    for form in {tif, lat, e["construct"]} - {""}:
                        sk, lk = _keys(form)
                        _add(gs, gl, sk, lk, e, 6)
            except Exception as e:  # dataset missing or renamed: Oulhaj + conjugations still serve
                print(f"[LEXICON] DGLAI not available: {e}")
            _dict_strict.clear(); _dict_strict.update(ds)
            _dict_loose.clear(); _dict_loose.update(dl)
            _conj_strict.clear(); _conj_strict.update(cs)
            _conj_loose.clear(); _conj_loose.update(cl)
            _verb_meta.clear(); _verb_meta.update(meta)
            _dglai_strict.clear(); _dglai_strict.update(gs)
            _dglai_loose.clear(); _dglai_loose.update(gl)
            _state.update({"loaded": True, "error": None, "dict_forms": len(ds), "conj_forms": len(cs), "verbs": len(meta), "dglai_forms": len(gs)})
            print(f"[LEXICON] ready: {len(ds)} dictionary forms, {len(cs)} conjugated forms, {len(meta)} verbs, {len(gs)} DGLAI forms")
            return True
        except Exception as e:  # offline, HF down, …: the tutor simply works without it
            _state.update({"error": str(e)[:200]})
            print(f"[LEXICON] not available: {e}")
            return False
        finally:
            _state["loading"] = False


def warm_up_async() -> None:
    threading.Thread(target=load, daemon=True).start()


def status() -> dict:
    return dict(_state, attribution=ATTRIBUTION)


def lookup(text: Optional[str], max_words: int = 12) -> List[dict]:
    """Dictionary entries and conjugation hits for each content word of `text`
    (Latin or Tifinagh). [] when the lexicon is not loaded."""
    if not (text or "").strip() or not _state["loaded"]:
        return []
    out, seen = [], set()
    for w in _WORD.findall(text):
        sk, lk = _keys(w)
        if not sk or sk in seen or lk in _STOP or len(sk) < 2:
            continue
        seen.add(sk)
        d = _dict_strict.get(sk) or []
        c = _conj_strict.get(sk) or []
        g = _dglai_strict.get(sk) or []
        verb = _verb_meta.get(sk)
        exact = bool(d or c or verb or g)
        if not exact:
            d = _dict_loose.get(lk) or []
            c = _conj_loose.get(lk) or []
            g = _dglai_loose.get(lk) or []
        if d or c or verb or g:
            out.append({"word": w, "key": sk, "exact": exact, "dictionary": d[:4], "conjugation": c[:3], "verb": verb, "ircam": g[:3]})
        if len(out) >= max_words:
            break
    return out


_PERSON_CA = {"1sg": "jo", "2sg": "tu", "3sg": "ell/ella", "1pl": "nosaltres", "2pl": "vosaltres", "3pl": "ells/elles"}


def _persons_ca(plist: List[str]) -> str:
    names = []
    for p in plist:
        base, _, g = p.partition("_")
        n = _PERSON_CA.get(base, base) + ({"m": " (m.)", "f": " (f.)"}.get(g, "") if base != "1sg" else "")
        if n not in names:
            names.append(n)
    return ", ".join(names)


def grounding_lines(text: Optional[str]) -> List[str]:
    """Compact lines for a prompt: what the dictionary and the tables say about each word.
    A loose (spelling-normalised) match is marked, so the tutor can doubt it."""
    lines = []
    for hit in lookup(text):
        w = hit["word"]
        approx = "" if hit["exact"] else " (coincidència aproximada de grafia; pot ser una altra paraula)"
        for e in hit["dictionary"][:2]:
            ex = f" — ex. «{e['example']}»" if e.get("example") else ""
            lines.append(f"- «{w}» ≈ {e['tashlhit']} / {e['tifinagh']} ({e['pos'] or 'diccionari'}): "
                         f"{'; '.join(e['english'])}{ex}{approx} [Oulhaj]")
        for g in (hit.get("ircam") or [])[:2]:
            lines.append(f"- «{w}» ≈ {g['latin']} / {g['tifinagh']} ({g['grammar'] or 'diccionari'}): "
                         f"{g['french']}{(' · ' + g['arabic']) if g['arabic'] else ''}{approx} [IRCAM-DGLAI]")
        if hit.get("verb") and not hit["dictionary"]:
            v = hit["verb"]
            lines.append(f"- «{w}» = verb {v['verb']} «{v['french']}»{approx} [IRCAM]")
        for cj in hit["conjugation"][:2]:
            lines.append(f"- «{w}» ≈ {cj['form']}, forma del verb {cj['verb']} «{cj['french']}»: {cj['tense']}, "
                         f"{_persons_ca(cj['persons'])}{approx} [IRCAM]")
    return lines[:14]
