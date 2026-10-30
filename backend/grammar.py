"""Grammar course: the library organised as a sequence of grammar units.

`topics` says what a drill is ABOUT (food, family); `grammar` says which grammar point the
drill shows (the perfective, the construct state, negation). A fixed curriculum of units in
pedagogical order (the amazic.cat compendium's chapters, cut into teachable steps); each drill
carries up to 3 unit slugs, filled by Gemini from the Tamazight text and the Catalan meaning
(`grammar_source = "auto"`), overridable by hand (`"owner"`). Each unit's LESSON is a sequence
of steps (explanations with the library's own examples -pictures and voices-, a pattern table,
quick checks, a tip, a dialect note), written once by Gemini from the compendium's sections
named by the unit (SECTIONS) and kept in the `grammar_lessons` table so deploys don't lose it.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from typing import Dict, List, Optional

# slug, Catalan title, chapters of the compendium that explain it, hint for the classifier
SOUNDS_UNIT = "sons-i-escriptura"
UNITS: List[dict] = [
    {"slug": SOUNDS_UNIT, "title": "Els sons de l'amazic i com els escrivim", "chapters": [1], "level": 1,
     "hint": "NEVER choose this unit: it is about sounds and spelling, not grammar",
     "brief": "This unit is about SOUNDS and SPELLING, not grammar, for someone who has never heard the language: each "
              "step presents one or two sounds Catalan speakers find hard (ɣ, ḥ, ɛ, q, x, the emphatic ṭ ḍ ṣ ẓ, long "
              "consonants, š), says in plain words how to make the sound with the mouth and throat, shows how our "
              "speakers spell it (gh / ġ / ɣ, kh / x, 3 / ɛ, sh / š) and quotes our short words that contain it; the "
              "focus of each example is the letter or letters of that sound. No grammar at all."},
    {"slug": "formules", "title": "Fórmules bàsiques: salutar, agrair, acomiadar-se", "chapters": [7], "level": 1,
     "hint": "ONLY a fixed social formula used as a whole: greetings, how are you, thank you, goodbye, welcome, "
             "blessings and polite replies (azul, manzakin, tanmmirt, bslama, mrḥba, lla yɛawn). NOT 'yes' / 'no' / 'ok' / "
             "'well' particles (wayh, uhu, waxxa, aywa, safi) and NOT ordinary words: those are not formulas"},
    {"slug": "pronoms-personals", "title": "Els pronoms personals (nkk, kyy, ntta…)", "chapters": [4], "level": 1,
     "hint": "independent personal pronouns as subject or in isolation: I, you (m/f), he, she, we, you (pl), they"},
    {"slug": "demostratius", "title": "Demostratius: aquest, aquell (wa, ta, wi, -a, -nn)", "chapters": [4], "level": 1,
     "hint": "this/that, these/those, the demonstrative suffixes -a / -ad / -nn, 'who is this?'"},
    {"slug": "noms-genere-nombre", "title": "Els noms: masculí i femení, singular i plural", "chapters": [3], "level": 1,
     "hint": "noun forms: masculine a-, feminine ta-…-t, plurals i-…-n, ti-…-in, broken plurals; a bare noun or noun pair"},
    {"slug": "estat-annexio", "title": "L'estat d'annexió (u-, w-, t-) després de preposició i subjecte", "chapters": [3], "level": 2,
     "hint": "ONLY when a noun VISIBLY changes its first letters after a preposition (n, g/ɣ, s, f, dar, ɣur, zg) or as a "
             "subject placed after the verb: a- > u-/w- (argaz > urgaz, n wass), ta- > t- (tamɣart > tmɣart), i- > y- (n yirgazn). "
             "A noun that keeps its a-/ta- (tigmmi, n tigmmi), an Arabic loan with l- (n lḥanut) or a bare noun does NOT show it"},
    {"slug": "possessius", "title": "Els possessius (-inu, -nnk, -nns) i el genitiu n", "chapters": [4], "level": 1,
     "hint": "my, your, his/her, our house; kinship possessives (baba, mma, gma-s); 'of' with n"},
    {"slug": "preposicions", "title": "Les preposicions (s, g/ɣ, dar/ɣur, d, i, f, zg)", "chapters": [6], "level": 2,
     "hint": "in, to, at, with, for, from, on, under, before/after, and their pronoun forms (dar-i, fll-as)"},
    {"slug": "ser-tenir", "title": "«Ser», «estar» i «tenir»: iga, illa, ɣur-i, dar-i", "chapters": [5, 7], "level": 1,
     "hint": "to be / there is / to have: iga, illa, ɣur-i / dar-i (I have), ur illi, nominal sentences without a verb"},
    {"slug": "aorist-ad", "title": "L'aorist amb ad: futur, voluntat i ordre indirecte", "chapters": [5], "level": 2,
     "hint": "ad + aorist for future, wish or purpose: ad dduɣ (I will go), rad / ad, 'I want to'"},
    {"slug": "perfectiu", "title": "El perfectiu: accions acabades (passat)", "chapters": [5], "level": 2,
     "hint": "the perfective (accomplished): I went, she said, we ate; a finished action"},
    {"slug": "imperfectiu-habitual", "title": "L'imperfectiu i l'habitual (da / ar + verb)", "chapters": [5], "level": 2,
     "hint": "habitual or ongoing actions with da / ar / la + intensive stem: I usually go, he is eating, every day"},
    {"slug": "imperatiu", "title": "L'imperatiu: ordres i peticions", "chapters": [5], "level": 1,
     "hint": "ONLY a real command or request said to someone, in a sentence: come here!, give me water, sit down, don't go "
             "(ur + aorist / imperfective). A verb given alone as a dictionary entry ('to eat' = šš, 'to go' = ddu) or a "
             "conjugation list is vocabulary, NOT a command: never 'imperatiu'"},
    {"slug": "negacio", "title": "La negació: ur …, ur … ša / bu", "chapters": [5, 7], "level": 2,
     "hint": "negative sentences: not, never, nothing, nobody, no longer (ur, ur jjun, walu, ur ta)"},
    {"slug": "preguntes", "title": "Les preguntes: is, ma, mani, manik, mšta, maymi", "chapters": [6, 7], "level": 1,
     "hint": "yes/no questions with is; question words: what, who, where, how, how much, when, why"},
    {"slug": "clitics-objecte", "title": "Els pronoms d'objecte (-t, -tt, -i, -ak, -as) i la seva posició", "chapters": [4], "level": 3,
     "hint": "direct and indirect object clitics attached to the verb or attracted before it: give it to me, he saw her, tell him"},
    {"slug": "relatiu-participi", "title": "El relatiu i el participi: lli, ay-, verb en -n", "chapters": [4, 7], "level": 3,
     "hint": "relative clauses and participles: the man who came (argaz lli d yuškan), what, the one that"},
    {"slug": "adjectius-qualitat", "title": "Qualitats: adjectius, verbs d'estat i comparació", "chapters": [3, 5], "level": 2,
     "hint": "big, small, good, beautiful, more than; stative verbs of quality (imqqur, iḥla)"},
    {"slug": "numerals", "title": "Els numerals i la quantitat", "chapters": [3], "level": 1,
     "hint": "ONLY when a number word is visible in the Tamazight (yan/yat, sin/snat, kraḍ, kuẓ, smmus… mraw, ɛšrin, mya, "
             "alf), or counting / how many (mnšk, mšta n), half, once / twice, 'the first'. General quantity words alone "
             "(bzzaf 'a lot', imik 'a little', kullu 'all', kra 'some') are NOT numerals"},
    {"slug": "temps-adverbis", "title": "Adverbis de temps i lloc: avui, demà, ja, encara, aquí", "chapters": [6], "level": 2,
     "hint": "today, yesterday, tomorrow, now, still / not yet (ur ta), already, here, there, always"},
    {"slug": "subordinades", "title": "Oracions subordinades: perquè, si, quan, per a què", "chapters": [7], "level": 3,
     "hint": "because (ašku), if (iɣ / mš), when (lliɣ, aylliɣ), so that (bašš / afad), that (is, ad), until (ar)"},
    {"slug": "derivacio-verbal", "title": "Verbs derivats: causatiu s-, passiu tt-, recíproc m-", "chapters": [5], "level": 3,
     "hint": "derived verb forms: make someone do (ss-), be done (ttu-/tty-), each other (m-/my-)"},
    {"slug": "manlleus", "title": "Els manlleus de l'àrab i l'article l-", "chapters": [3], "level": 2,
     "hint": "Arabic loanwords with the article l- / ll- (lxdmt, ṭṭumubil, lḥal), their plurals and how they take Amazigh prefixes"},
]
SLUGS = [u["slug"] for u in UNITS]
TITLES = {u["slug"]: u["title"] for u in UNITS}
BATCH = 40
DEEP_VERSION = 1   # the «a fons» level of a unit, kept under «deep:<slug>» in the same table
LESSON_VERSION = 18  # bump when the lesson format or prompt changes: old rows are rewritten on next open

# Drills whose tag names another language are never part of the course (the owner's old Irish tests).
EXCLUDED_TAGS = ("irish",)

# The compendium's own sections (N.N / N.N.N) that explain each unit: what the lesson writer reads.
SECTIONS: Dict[str, List[str]] = {
    SOUNDS_UNIT: ["1.1", "1.1.2", "1.2.1", "1.4.1", "1.4.2", "1.5.2"],
    "formules": ["7.1.1", "6.4", "7.3.3", "7.2.3"],
    "pronoms-personals": ["4.1", "4.1.1", "4.1.2", "5.1.1"],
    "demostratius": ["4.2", "4.2.1", "4.2.2", "4.3.1", "4.3.3"],
    "noms-genere-nombre": ["3.1", "3.1.1", "3.1.2", "3.2", "3.2.1", "3.2.2", "3.2.3", "3.2.4"],
    "estat-annexio": ["3.3", "3.3.1", "3.3.2"],
    "possessius": ["4.1.2", "4.3.2", "4.3.4", "3.3.2"],
    "preposicions": ["6.2", "6.2.1", "6.2.2", "6.2.3", "3.3.2"],
    "ser-tenir": ["7.1.1", "6.5", "7.2.3", "6.4", "7.1.3"],
    "aorist-ad": ["5.2", "5.2.1", "5.1.1", "7.5.5"],
    "perfectiu": ["5.1.1", "5.2.2", "5.1.2", "5.2.3"],
    "imperfectiu-habitual": ["5.2", "5.2.4", "5.2.5"],
    "imperatiu": ["5.1.3", "7.2.4"],
    "negacio": ["7.2", "7.2.1", "7.2.2", "7.2.3", "5.2.3", "5.2.5"],
    "preguntes": ["7.3", "7.3.1", "7.3.2", "4.3.6", "7.5.4"],
    "clitics-objecte": ["4.1.2", "7.1.2", "4.2.2"],
    "relatiu-participi": ["4.3.5", "5.1.4", "7.5.1", "7.5.2", "7.5.3", "7.5.6"],
    "adjectius-qualitat": ["3.6", "7.4.1", "5.1.2", "7.7.8"],
    "numerals": ["3.5.1", "3.5.2", "3.5.3"],
    "temps-adverbis": ["6.1", "7.4.2", "7.7.1", "7.7.2"],
    "subordinades": ["7.6.1", "7.6.3", "7.7.2", "7.7.3", "7.7.4", "7.7.5", "7.7.6", "7.7.7", "7.7.9"],
    "derivacio-verbal": ["5.3", "5.3.2", "5.3.3", "5.3.4", "5.3.5"],
    "manlleus": ["3.4.1", "3.4.2", "3.1.1"],
}

_state = {"running": False, "done": 0, "pending": 0, "errors": 0, "started_at": None, "finished_at": None, "last_error": None}
_lock = threading.Lock()
_explain_lock = threading.Lock()


def parse(s: Optional[str]) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip() and x.strip() in TITLES]


def not_excluded(query, DrillModel):
    """Keep drills whose tag doesn't name an excluded language."""
    from sqlalchemy import or_
    for t in EXCLUDED_TAGS:
        query = query.filter(or_(DrillModel.tag.is_(None), ~DrillModel.tag.ilike(f"%{t}%")))
    return query


def _prompt(rows: List[dict]) -> str:
    vocab = "\n".join(f"- {u['slug']}: {u['title']} — {u['hint']}" for u in UNITS)
    items = "\n".join(
        f"- id {r['id']}: Tamazight «{r.get('shi') or ''}» | Catalan «{r.get('ca') or ''}»" for r in rows)
    return (
        "For each Tamazight (Tachelhit / Central Atlas) drill, say which GRAMMAR UNITS of a course it illustrates: "
        "1 to 3 slugs from this fixed list, the most clearly shown point first. Judge from the Tamazight form "
        "(verb aspect, pronouns, clitics, construct state, negation, question particle…), with the Catalan meaning "
        "as a guide. A bare noun or noun phrase goes to 'noms-genere-nombre' (or 'numerals', 'manlleus' when that "
        "is the point); a fixed greeting goes to 'formules'. Use ONLY these slugs. Tag a unit ONLY when its marker is "
        "visible in the Tamazight text (never from the Catalan alone). A single word that is not a noun, a number, a loan "
        "or a greeting (an interjection, 'yes', 'no', a proper name), or a drill that shows no unit at all, gets an EMPTY "
        "array [].\n\n"
        f"UNITS:\n{vocab}\n\nDRILLS:\n{items}\n\n"
        "Answer ONLY with a JSON object mapping each id (as a string) to an array of slugs, e.g. "
        "{\"12\": [\"perfectiu\", \"clitics-objecte\"], \"13\": [\"formules\"]}."
    )


def classify_batch(rows: List[dict]) -> Dict[int, List[str]]:
    from gemini_client import gemini_generate
    answer = gemini_generate("You are a careful Amazigh grammar teacher cataloguing examples for a course.",
                             [{"role": "user", "text": _prompt(rows)}], max_output_tokens=6000, temperature=0.1, timeout=180)
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        raise ValueError(f"no JSON in answer: {(answer or '')[:120]}")
    out: Dict[int, List[str]] = {}
    for k, v in json.loads(m.group(0)).items():
        try:
            did = int(str(k).strip())
        except ValueError:
            continue
        slugs = [s.strip() for s in (v if isinstance(v, list) else [v]) if isinstance(s, str) and s.strip() in TITLES]
        out[did] = list(dict.fromkeys(slugs))[:3]  # [] = Gemini says the drill shows no unit (kept as NO_UNIT)
    return out


NO_UNIT = "-"  # stored in `grammar` when the classifier found no unit: not re-asked, never listed


def status() -> dict:
    return dict(_state)


def run(session_factory, force: bool = False, limit: int = 4000, only_ids: Optional[List[int]] = None) -> dict:
    """Fill `grammar` for drills that lack it (all auto-classified ones with force), in batches."""
    from models import Drill as DrillModel
    with _lock:
        if _state["running"]:
            return {"started": False, "reason": "already running"}
        _state.update({"running": True, "done": 0, "errors": 0, "started_at": time.time(), "finished_at": None, "last_error": None})
    try:
        db = session_factory()
        try:
            q = not_excluded(db.query(DrillModel).filter(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != ""), DrillModel)
            if only_ids:
                q = q.filter(DrillModel.id.in_(only_ids))
            elif not force:
                q = q.filter((DrillModel.grammar.is_(None)) | (DrillModel.grammar == ""))
            drills = q.order_by(DrillModel.id).limit(limit).all()
            if force and not only_ids:
                drills = [d for d in drills if (d.grammar_source or "auto") == "auto"]
            drills = [d for d in drills if (d.text_tachelhit or "").strip().lower() != "text"]
            _state["pending"] = len(drills)
            for i in range(0, len(drills), BATCH):
                part = drills[i:i + BATCH]
                rows = [{"id": d.id, "ca": d.text_catalan, "shi": d.text_tachelhit} for d in part]
                try:
                    got = classify_batch(rows)
                except Exception as e:
                    _state["errors"] += len(part); _state["last_error"] = str(e)[:200]
                    print(f"[GRAMMAR] batch failed: {e}")
                    continue
                for d in part:
                    if d.id in got:
                        d.grammar = ", ".join(got[d.id]) or NO_UNIT; d.grammar_source = "auto"; _state["done"] += 1
                    else:
                        _state["errors"] += 1
                db.commit()
                _state["pending"] = max(0, len(drills) - i - len(part))
                print(f"[GRAMMAR] {_state['done']} classified, {_state['errors']} without answer, {_state['pending']} pending")
        finally:
            db.close()
    finally:
        _state["running"] = False
        _state["finished_at"] = time.time()
    return {"started": True, "done": _state["done"], "errors": _state["errors"]}


def sound_rows(db, limit: int = 300) -> List:
    """The sounds unit's examples: our speakers' short recorded words and phrases (≤ 3 words) that
    contain a sound Catalan speakers find hard, the pictured ones first."""
    from models import Drill as DrillModel
    import practice
    q = not_excluded(db.query(DrillModel).filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "",
                                                  DrillModel.text_tachelhit.isnot(None), DrillModel.text_tachelhit != ""), DrillModel)
    out = []
    for d in q.order_by(DrillModel.image_url.isnot(None).desc(), DrillModel.id.asc()).all():
        shi = _clean_text(d.text_tachelhit)
        if kind(shi) not in ("word", "sentence") or len(re.findall(r"[^\W\d_]+", shi)) > 3 or not quotable(shi, SOUNDS_UNIT):
            continue
        if practice.tips(shi, limit=1):
            out.append(d)
            if len(out) >= limit:
                break
    return out


def counts(session_factory) -> Dict[str, int]:
    from models import Drill as DrillModel
    db = session_factory()
    try:
        c: Dict[str, int] = {s: 0 for s in SLUGS}
        for (g,) in db.query(DrillModel.grammar).filter(DrillModel.grammar.isnot(None)).all():
            for s in parse(g):
                c[s] = c.get(s, 0) + 1
        c[SOUNDS_UNIT] = len(sound_rows(db))
        return c
    finally:
        db.close()


def _section_text(grammar_md: str, sections: List[str], each: int = 12000, total: int = 70000) -> str:
    """The compendium's numbered sections (e.g. 7.2.1) named by the unit, each cut at `each` chars."""
    lines = (grammar_md or "").split("\n")
    heads = []  # (line index, number)
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*(\d+(?:\.\d+){1,2})\.\s+\S", ln)
        if m and len(ln) < 110:
            heads.append((i, m.group(1)))
    out = []
    for want in sections:
        for k, (i, num) in enumerate(heads):
            if num != want:
                continue
            depth = num.count(".")
            end = len(lines)
            for j, n2 in heads[k + 1:]:
                if n2.count(".") <= depth and not n2.startswith(want + "."):
                    end = j; break
            out.append("\n".join(lines[i:end])[:each]); break
    text = "\n\n".join(out)
    return text[:total]


def _chapter_text(grammar_md: str, numbers: List[int], limit: int = 60000) -> str:
    """Fallback when a unit names no sections: whole chapters (## N. …)."""
    parts = re.split(r"(?m)^## (?=\d+\.)", grammar_md)
    out = []
    for p in parts:
        m = re.match(r"(\d+)\.", p)
        if m and int(m.group(1)) in numbers:
            out.append(p[:limit])
    return "\n\n".join(out)


def reference_text(slug: str, grammar_md: str) -> str:
    unit = next((u for u in UNITS if u["slug"] == slug), None)
    if unit is None or not grammar_md:
        return ""
    return _section_text(grammar_md, SECTIONS.get(slug) or []) or _chapter_text(grammar_md, unit["chapters"], limit=30000)


def _clean_text(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\r", "")).strip()


# The grammarian's words a beginner does not have, and what the lesson says instead. The writer is
# told not to use them; this is the net under that, because three lessons used them anyway.
PLAIN_WORDS = [
    (r"\binacomplert\b", "inacabat"), (r"\bacomplert\b", "acabat"),
    (r"\bdíctics\b", "mots que assenyalen"), (r"\bdíctic\b", "mot que assenyala"),
    (r"\bclítics\b", "pronoms enganxats al verb"), (r"\bclític\b", "pronom enganxat al verb"),
    (r"\bmorfemes\b", "trossos de paraula"), (r"\bmorfema\b", "tros de paraula"),
    (r"\blexemes\b", "arrels"), (r"\blexema\b", "arrel"),
    (r"\bsintagmes\b", "grups de paraules"), (r"\bsintagma\b", "grup de paraules"),
    (r"\bapofonia\b", "canvi de vocal a dins de la paraula"),
    (r"\btema verbal\b", "forma del verb"), (r"\bdiàtesi\b", "manera de dir qui fa l'acció"),
]


#: Els sons que la llengua escriu amb dues lletres: així «gh» també rep la seva tifinagh.
PAIRS = {"gh", "kh", "sh", "ch", "gw", "kw", "qw", "tt", "kk", "ll", "dj",
         # els mateixos sons arrodonits escrits com els escriu el llibre: kʷ, gʷ, qʷ, xʷ, ɣʷ
         "kʷ", "gʷ", "qʷ", "xʷ", "ɣʷ"}

#: Un so citat al text d'una lliçó, entre cometes: «ɛ», «gh», 'ẓ'.
#:
#: L'apòstrof només obre una citació si al davant NO hi ha una lletra. En català l'apòstrof
#: viu dins les paraules —«ajuda'm», «l'home», «dóna'm»— i si es prenia per una cometa, una
#: nota com «vol dir 'ajuda'm'» es llegia com si hi hagués citat el so «m» i en sortia
#: «vol dir 'ajuda'm ⵎ'». La ⵎ no la volia ningú.
_QUOTED = re.compile(
    r"[«\"‘“]([^«»\"'’”]{1,3})[»\"’”]"
    r"|(?<![^\W\d_])['’]([^«»\"'’”]{1,3})['’](?![^\W\d_])"
)


def with_letters(t: str) -> str:
    """El mateix text amb la tifinagh de cada so citat al costat: «ɛ» → «ɛ ⵄ».

    L'amo: «la tifinagh ha de ser present a tot arreu, també al títol de l'explicació dels sons».
    Una lliçó que ensenya un so citant-lo en llatí ensenya el so i no ensenya la lletra, i aquesta
    app ensenya les dues coses.

    Només toca el que és CITAT i curt —un so, no una paraula—, i només si el transliterador en
    treu una tifinagh diferent del que ja hi ha. Si no, el text es queda tal com és: val més una
    lliçó sense una lletra que una lliçó amb una lletra inventada.
    """
    if not t or "ⵣ" in t:
        return t

    def one(m):
        raw = (m.group(1) or m.group(2) or "").strip()
        # Nom\u00E9s un SO: una lletra sola, o un dels parells que la llengua escriu junts. Dues o
        # tres lletres qualssevol serien paraules catalanes citades \u2014\u00ABno\u00BB, \u00ABfer\u00BB, \u00ABcas\u00BB\u2014 i els
        # penjar\u00EDem al costat una tifinagh que no vol dir res.
        if len(raw) != 1 and raw.lower() not in PAIRS:
            return m.group(0)
        if not raw or re.search(r"[\u2D30-\u2D7F]", raw):
            return m.group(0)
        try:
            import transliteration
            tif = (transliteration.to_forms(raw)["tifinagh"] or "").strip()
        except Exception:
            return m.group(0)
        if not tif or tif == raw:
            return m.group(0)
        return m.group(0).replace(raw, f"{raw} {tif}", 1)

    return _QUOTED.sub(one, t)


def _plain(t: str) -> str:
    """Say it as a lesson would: no word the learner would have to look up."""
    for pat, rep in PLAIN_WORDS:
        t = re.sub(pat, rep, t, flags=re.I)
    return t


def _clean_prose(s: Optional[str]) -> str:
    """Lesson prose: Latin letters only (no Arabic, no Tifinagh), no example ids."""
    t = _clean_text(s)
    t = re.sub(r"\s*\([^()]*[\u0600-\u06FF\u2D30-\u2D7F][^()]*\)", "", t)   # (مرحبا) or (ⴳ)
    t = re.sub(r"[\u0600-\u06FF][\u0600-\u06FF\s\-؟]*", "", t)         # bare Arabic script
    t = re.sub(r"[\u2D30-\u2D7F][\u2D30-\u2D7F\s\u00B0\u2218]*", "", t)  # bare Tifinagh: the course is in Latin letters
    t = re.sub(r"\s*\((?:exemples?|ids?)\s*[\d,\s]+(?:i\s*\d+)?\)", "", t, flags=re.I)
    t = re.sub(r"\b(?:en\s+|a\s+)?(?:als?|els?|l')\s*exemples?\s+\d+(?:\s*(?:,|i)\s*\d+)*", "", t, flags=re.I)
    t = re.sub(r"\bexemples?\s+\d+(?:\s*(?:,|i)\s*\d+)*", "", t, flags=re.I)
    return with_letters(_plain(re.sub(r"\s+", " ", t).replace(" ,", ",").replace(" .", ".").strip()))


def gloss_of(d) -> Optional[List[dict]]:
    """The word-by-word reading the library already stores for the sentence (`glosses`), so a
    lesson can show it under the example instead of asking the copilot for it."""
    raw = (getattr(d, "glosses", None) or "").strip()
    if not raw:
        return None
    try:
        got = json.loads(raw)
    except Exception:
        return None
    if not isinstance(got, list):
        return None
    out = []
    for g in got:
        if not isinstance(g, dict):
            continue
        w, ca = str(g.get("shi") or "").strip(), str(g.get("ca") or "").strip()
        if w and ca and ca != "?" and ca.lower() != w.lower():
            out.append({"shi": w, "ca": ca, "tif": (str(g.get("tif") or "").strip() or None)})
    return out or None


NOTE_VERSION = 1       # bump to rewrite every «why this sentence is here» note
NOTES_BATCH = 12       # sentences per Gemini call: ~160 calls cover the whole course
NOTES_PAUSE = 4.0      # seconds between calls: the free instance serves pages with the same CPU
NO_NOTE = "-"          # asked, and the honest answer was that the sentence shows nothing of the unit

_notes_state = {"running": False, "done": 0, "pending": 0, "errors": 0, "unit": None,
                "started_at": None, "finished_at": None, "last_error": None}
_notes_lock = threading.Lock()


def notes_status() -> dict:
    return dict(_notes_state)


def notes_for(db, slug: str, texts: Optional[Dict[int, tuple]] = None) -> Dict[int, str]:
    """What the library can say about each sentence of ONE unit: why it is there. By drill id, and
    without the ones whose honest answer was «it shows nothing of this unit».

    També es queden fora, aquí mateix, les notes ja desades que no passarien avui: les que parlen
    com un llibre de fonètica i les que citen un tros que no és a la frase. Es filtren en SERVIR
    i no només en escriure, perquè les que hi ha escrites no es poden refer d'un dia per l'altre
    i mentrestant la persona que aprèn les llegeix. `texts` són les frases per id, quan qui
    pregunta les té; sense elles només es comprova el jargó."""
    from models import GrammarNote
    rows = db.query(GrammarNote.drill_id, GrammarNote.body).filter(GrammarNote.slug == slug).all()
    out: Dict[int, str] = {}
    for i, b in rows:
        if not b or b == NO_NOTE:
            continue
        shi, ca = (texts or {}).get(int(i)) or ("", "")
        if note_problem(b, shi, ca) is None:
            out[int(i)] = b
    return out


def asked_notes(db, slug: str) -> set:
    """The drills already asked about for this unit, so a pass never asks twice."""
    from models import GrammarNote
    return {int(i) for (i,) in db.query(GrammarNote.drill_id).filter(
        GrammarNote.slug == slug, GrammarNote.version >= NOTE_VERSION).all()}


def _notes_prompt(unit: dict, sheet: str, batch: List[dict]) -> str:
    lines = "\n".join(f"- id {e['id']}: «{e['shi']}» — {e['ca']}" for e in batch)
    return (
        f"Ensenyes amazic (tamazight de l'Atles central) a catalanoparlants que comencen. La unitat "
        f"del curs és «{unit['title']}»: {unit.get('hint') or ''}\n\n"
        f"FULL DE REGLES DE LA UNITAT\n{sheet}\n\n"
        "Per a cada frase de sota, digues QUÈ MOSTRA AQUESTA FRASE d'aquesta unitat: quin tros de la "
        "frase és el que ensenya el punt i què hi fa. De 25 a 45 paraules, en català planer, com ho "
        "diria un mestre al costat de la frase.\n"
        "- anomena el tros tal com està escrit a la frase, entre cometes;\n"
        "- no facis servir mots de gramàtic ni de fonetista: res de «clític», «morfema», "
        "«inacomplert», «díctic», «uvular», «faringal», «al·lòfon», «nucli sil·làbic», "
        "«tautosil·làbic», «fricativa», «fonema». Digues-ho a la manera planera: «el so que es fa "
        "al fons de la gola», «la lletra enganxada al final»;\n"
        "- el tros que citis ha de ser DINS la frase, lletra per lletra. Si no hi és, no el citis;\n"
        "- no citis mai números d'identificació ni diguis «aquesta frase» dues vegades;\n"
        "- si la frase no mostra res d'aquesta unitat, respon exactament «-» i prou. Val més dir-ho "
        "que inventar-s'ho.\n\n"
        f"FRASES\n{lines}\n\n"
        'Respon NOMÉS amb un objecte JSON {"<id>": "<el que mostra, 25-45 paraules>"}.'
    )


#: Paraules de gramàtic i de fonetista. La nota que en porta una no s'arriba a desar: val més
#: una frase sense nota que una frase amb una nota que ningú no entén. (BANNED_TERMS són les
#: que es demanen al redactor; aquestes són les que es comproven DESPRÉS, perquè demanar-ho no
#: ha bastat: les lliçons servides parlen de nuclis sil·làbics a una unitat de nivell 1.)
NOTE_JARGON = (
    "uvular", "faringal", "faringi", "al·lòfon", "alòfon", "al·lofòn", "tautosil", "nucli sil",
    "atac sil", "coda sil", "sil·labic", "sil·làbic", "fonològic", "fonologic", "fonema",
    "fricativa", "oclusiva", "africada", "sonoritat", "ultrabreu", "schwa", "morfema", "lexema",
    "al·lomorf", "alomorf", "clític", "clitic", "díctic", "dictic", "deíctic", "sintagma",
    "desinència", "flexiu", "apofonia", "diàtesi", "tema verbal",
)

#: Un tros citat entre cometes dins la nota: «3wn», «-nnx», «ad».
_QUOTED_BIT = re.compile(r"«([^»]{1,24})»|'([^']{1,24})'")

#: Tot el que no és lletra: guionets, cometes, punts, espais. Comparar «-nnx» amb «nnx» o
#: «ajuda'm» amb «ajudam» ha de donar igual.
_NOT_A_LETTER = re.compile(r"[^\wƀ-ɏʰ-˿]+")


def _letters_only(s: Optional[str]) -> str:
    return _NOT_A_LETTER.sub("", (s or "").lower())


def note_problem(note: str, shi: str = "", ca: str = "") -> Optional[str]:
    """Per què aquesta nota no es pot servir — o None si es pot.

    Una sola cosa, i segura: el jargó. «La 'x' és una consonant uvular… un al·lòfon de la vocal
    bàsica» és el que la unitat dels sons, de nivell 1, serveix avui. La frase i el seu
    significat es demanen per si un dia fa falta mirar-hi dins; de moment no s'hi mira, perquè
    una nota ben feta cita el significat català tant com el tros amazic i no es pot distingir
    una cita bona d'una d'inventada sense endevinar.

    Les paraules inventades sí que es comproven on van aparèixer de debò: a les taules de formes
    (`table_words_not_in_library`).
    """
    low = (note or "").lower()
    for w in NOTE_JARGON:
        if w in low:
            return f"paraula de gramàtic: «{w}»"
    return None


def table_words_not_in_library(step: dict, examples: List[dict]) -> List[str]:
    """Les paraules amazigues d'una taula de formes que no surten a cap frase de la unitat.

    La taula «Sons difícils i la seva escriptura» citava `meddn` per a la ḍ (que no en té, de ḍ)
    i `Tabrat` per a la ṭ: dues paraules que no són enlloc de la unitat ni, de fet, de la
    biblioteca. Una taula de numerals pot ensenyar el «sis» encara que no el tinguem gravat
    —és una taula, ha de ser sencera—, però el que no pot fer és citar una paraula que no
    existeix com si fos un exemple."""
    pool = set()
    for e in examples or []:
        for w in re.findall(r"[^\W\d_]+", (e.get("shi") or "").lower()):
            pool.add(w)
    out = []
    for row in (step.get("rows") or []):
        for cell in (row if isinstance(row, list) else [row]):
            text = str(cell or "").strip()
            words = re.findall(r"[^\W\d_]+", text.lower())
            if len(words) != 1 or len(words[0]) < 4:
                continue
            if _looks_catalan(words[0]):
                continue
            if words[0] not in pool:
                out.append(text)
    return out


#: Les caselles catalanes d'una taula («encara», «vosaltres», «febre»): accent, ce trencada, o
#: una de les poques paraules planes que hi surten. No cal que sigui perfecte —això és una
#: comprovació per mirar-s'hi, no una cosa que esborri res— però sí que ha de deixar passar
#: `meddn`, `Tabrat`, `smmus`, `allig`, `nttat`.
_CATALAN_PLAIN = {
    "aquest", "aquesta", "aquells", "aquelles", "nosaltres", "vosaltres", "ells", "elles",
    "encara", "sempre", "avui", "ahir", "demà", "ara", "aqui", "allà", "massa", "molt", "poc",
    "gran", "petit", "negre", "blanc", "febre", "mare", "pare", "peixos", "ulls", "casa",
    "aigua", "home", "dona", "quant", "quants", "quina", "quines", "perque", "perquè", "sobre",
    "sota", "dins", "amb", "sense", "primer", "segon", "tercer", "cinc", "sis", "set", "vuit",
    "nou", "deu", "onze", "dotze", "tretze", "catorze", "vint", "trenta", "cent", "mil",
    "tinc", "tens", "tenim", "teniu", "tenen", "una", "dues", "tres", "quatre",
}


def _looks_catalan(word: str) -> bool:
    return bool(re.search(r"[àèéíòóúïüç]", word)) or word in _CATALAN_PLAIN


def write_notes(unit: dict, sheet: str, batch: List[dict]) -> Dict[int, str]:
    """One call: why each of these sentences is in this unit."""
    from gemini_client import gemini_generate
    answer = gemini_generate(
        "Ets un mestre d'amazic que explica, frase a frase, què ensenya cada exemple.",
        [{"role": "user", "text": _notes_prompt(unit, sheet, batch)}],
        max_output_tokens=2000, temperature=0.2, timeout=180)
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        raise ValueError("notes without JSON")
    got = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
    by_id = {e["id"]: e for e in batch}
    out: Dict[int, str] = {}
    for k, v in (got or {}).items():
        try:
            i = int(str(k).strip())
        except ValueError:
            continue
        body = _clean_prose(str(v or "").strip())
        if i not in by_id or not body:
            continue
        if body.strip(" .-") == "":
            out[i] = NO_NOTE
            continue
        why_not = note_problem(body, by_id[i].get("shi") or "", by_id[i].get("ca") or "")
        if why_not:
            # es desa com a «no en tenim»: així no es torna a demanar en cada passada i, sobretot,
            # la frase surt sense nota en comptes de sortir amb una nota que diu una cosa falsa
            print(f"[NOTES] {unit['slug']} {i}: nota descartada ({why_not})")
            out[i] = NO_NOTE
            continue
        out[i] = body
    return out


def store_notes(db, slug: str, notes: Dict[int, str]) -> int:
    from datetime import datetime
    from models import GrammarNote
    n = 0
    for drill_id, body in notes.items():
        key = f"{slug}:{drill_id}"
        row = db.query(GrammarNote).filter(GrammarNote.id == key).first()
        if row is None:
            db.add(GrammarNote(id=key, slug=slug, drill_id=drill_id, body=body, version=NOTE_VERSION))
        else:
            row.body, row.version, row.updated_at = body, NOTE_VERSION, datetime.utcnow()
        n += 1
    db.commit()
    return n


def fill_notes(session_factory, rows_for, grammar_md: str = "", only: Optional[str] = None,
               per_unit: int = 90) -> dict:
    """Write «why this sentence is here» for every sentence each unit can quote, unit by unit and
    NOTES_BATCH sentences per call. Resumable: a pair already asked is never asked again, so the
    pass can stop and start, and a lesson rewritten later finds its notes waiting.

    `rows_for(db, slug)` gives a unit's drills (main.py owns that query)."""
    with _notes_lock:
        if _notes_state["running"]:
            return {"started": False, "reason": "already running"}
        _notes_state.update(running=True, done=0, pending=0, errors=0, unit=None,
                            started_at=time.time(), finished_at=None, last_error=None)
    try:
        for unit in [u for u in UNITS if not only or u["slug"] == only]:
            slug = unit["slug"]
            _notes_state["unit"] = slug
            db = session_factory()
            try:
                examples = pick_examples(rows_for(db, slug), limit=per_unit, slug=slug)
                todo = [e for e in examples if e["id"] not in asked_notes(db, slug)]
                if not todo:
                    continue
                _notes_state["pending"] += len(todo)
                sheet = sheet_for(db, slug, grammar_md)
                for i in range(0, len(todo), NOTES_BATCH):
                    batch = todo[i:i + NOTES_BATCH]
                    # a lesson being written is what a learner is waiting for: let it go first
                    for _ in range(60):
                        if not writing():
                            break
                        time.sleep(5)
                    try:
                        notes = write_notes(unit, sheet, batch)
                        for e in batch:  # a sentence the writer passed over is marked asked, once
                            notes.setdefault(e["id"], NO_NOTE)
                        store_notes(db, slug, notes)
                        _notes_state["done"] += len(batch)
                    except Exception as e:
                        db.rollback()
                        _notes_state["errors"] += 1
                        _notes_state["last_error"] = f"{slug}: {str(e)[:160]}"
                        print(f"[NOTES] {slug}: {e}")
                    time.sleep(NOTES_PAUSE)  # half a CPU is also serving pages
                print(f"[NOTES] {slug}: {len(todo)} sentences explained")
            except Exception as e:
                _notes_state["errors"] += 1
                _notes_state["last_error"] = f"{slug}: {str(e)[:160]}"
                print(f"[NOTES] {slug}: {e}")
            finally:
                try:
                    db.close()
                except Exception:
                    pass
    finally:
        with _notes_lock:
            _notes_state["running"] = False
            _notes_state["unit"] = None
            _notes_state["finished_at"] = time.time()
    return {"started": True, **notes_status()}


def tifinagh(shi: str) -> Optional[str]:
    """The sentence in Tifinagh, from the app's own transliterator. Shown under the speaker's own
    spelling: the prose of a lesson stays in Latin, but the language's own script belongs with the
    language. Never raises: a sentence we cannot transliterate simply shows none."""
    try:
        import transliteration
        return (transliteration.to_forms(shi or "")["tifinagh"] or "").strip() or None
    except Exception:
        return None


def example_dict(d) -> dict:
    """What a lesson step shows of a drill: both texts, the picture, a voice (speaker's first),
    the word-by-word reading when the library has one, and the sentence in Tifinagh."""
    # Tamazight only. `audio_tts_url` is the CATALAN reading of the meaning: in a lesson it would
    # say the answer out loud in the wrong language, and «escolta i tria el sentit» would be a joke.
    audio = d.audio_url
    return {"id": d.id, "shi": _clean_text(d.text_tachelhit), "ca": _clean_text(d.text_catalan),
            "image_url": d.image_url, "audio_url": audio, "recorded": bool(d.audio_url),
            "author": (d.author or "").strip() or None, "region": d.region, "origin": origin(d),
            "gloss": gloss_of(d), "tif": tifinagh(_clean_text(d.text_tachelhit)),
            "source_url": getattr(d, "source_url", None), "source_channel": getattr(d, "source_channel", None)}


AIT_MRAW = "Aït Mraw (Boutharar, Tinghir)"

OUR_SPEAKERS = ("Halima", "Driss")


def our_speaker(d) -> Optional[str]:
    """Halima or Driss when the drill is theirs: by author, or by a tag naming them (the owner tags
    their recordings «Driss», «frase, Driss», «Biografia, Driss»…)."""
    author = (d.author or "").strip()
    if author in OUR_SPEAKERS:
        return author
    for part in (d.tag or "").split(","):
        if part.strip() in OUR_SPEAKERS:
            return part.strip()
    return None


#: Noms que hi ha al lloc del parlant i que no són ningú: el procés que va retallar la frase.
PROCESSOS = ("auto capture", "autocapture")


def qui_ho_diu(d) -> Dict:
    """Qui diu aquesta frase, i si la seva veu es pot posar com a model a imitar (#273, #288).

    La regla, del pedagog i confirmada pel propietari: **per escoltar, totes les veus són
    benvingudes i omplen forats; per imitar, només una veu amb nom.** «Compara't amb la veu de
    debò» només és veritat si la veu és d'algú.

    Les quatre coses que es poden trobar al lloc del parlant, i que no es poden confondre:

      `nostra`   la Halima o en Driss, o una gravació del seu poble: la veu del curs.
      `persona`  algú altre amb nom, que també es pot imitar.
      `canal`    un canal de vídeo —«ILoveLanguages (parlant nadiu)»—, que no és una persona que
                 el projecte conegui i que sovint parla una altra varietat.
      `captura`  «Auto Capture», que és el procés que va retallar el tall, no ningú.
      `cap`      no hi ha veu.
    """
    veu = (getattr(d, "audio_url", "") or "").strip()
    qui = (getattr(d, "speaker", None) or getattr(d, "author", None) or "").strip()
    if not veu:
        return {"qui": qui or None, "mena": "cap", "per_imitar": False}
    if our_speaker(d) or "mraw" in (getattr(d, "region", "") or "").lower():
        return {"qui": qui or None, "mena": "nostra", "per_imitar": True}
    if not qui or qui.lower() in PROCESSOS:
        return {"qui": None, "mena": "captura", "per_imitar": False}
    # Un canal al lloc del parlant: o ve dit amb un parèntesi —«ILoveLanguages (parlant nadiu)»—
    # o és literalment el nom del canal d'on vam treure el tall.
    canal = (getattr(d, "source_channel", "") or "").strip()
    if "(" in qui or (canal and qui.lower() == canal.lower()):
        return {"qui": qui, "mena": "canal", "per_imitar": False}
    return {"qui": qui, "mena": "persona", "per_imitar": True}


def per_imitar(d) -> bool:
    """Si aquesta gravació es pot fer servir com a model per repetir-la."""
    return bool(qui_ho_diu(d)["per_imitar"])


def origin(d) -> str:
    """Where a drill's sentence comes from, for the lesson writer and the card."""
    tag = (d.tag or "").lower(); region = (d.region or "").strip()
    if our_speaker(d) or "mraw" in region.lower():
        return AIT_MRAW
    if "benimellal" in tag or region.lower().startswith("beni mellal"):
        return "Beni Mellal"
    # I si no en sabem el poble, no se n'inventa cap. Abans aquí hi deia «gravació», que a la
    # targeta sortia com «veu de parlant · gravació»: ocupava el lloc de la procedència sense
    # dir-ne res. Qui ho llegeix ha de poder distingir una frase d'un poble d'una frase que no
    # sabem d'on és —són dues coses diferents, i la segona és feina pendent, no un lloc.
    return region


def origin_rank(e: dict) -> int:
    o = e.get("origin") or ""
    return 0 if o == AIT_MRAW else 1 if o == "Beni Mellal" else 2


def kind(shi: Optional[str]) -> str:
    """What a drill's Tamazight text is: 'sentence', 'word' (one word), 'list' (the deck's conjugation
    lists and alternatives) or 'placeholder'."""
    t = _clean_text(shi)
    if not t or t.lower() == "text":
        return "placeholder"
    if "//" in t or t.count(",") >= 3 or t.count("/") >= 2:
        return "list"
    if len(re.findall(r"[^\W\d_]+", t)) <= 1:
        return "word"
    return "sentence"


# Units whose point is the word itself: a single word is a valid example and a valid exercise
# there («azul», «tanmmirt», «yan», «nkk»), where elsewhere only sentences show the rule.
WORD_UNITS = {SOUNDS_UNIT, "formules", "noms-genere-nombre", "numerals", "pronoms-personals", "demostratius", "manlleus", "temps-adverbis"}


def well_formed(shi: str, slug: Optional[str] = None) -> bool:
    """A text somebody can work with: a sentence (or a word, in the units about words) with no
    capture artefacts — dots inside words, a stray «+». Says nothing about the script it is
    written in."""
    k = kind(shi)
    if k not in ("sentence", "word") or (k == "word" and slug not in WORD_UNITS):
        return False
    t = _clean_text(shi)
    if re.search(r"\w\.\w", t) or "+" in t:
        return False  # «ⵜ.ⵅⵙ.ⵛ», «a.b.c», «Mana Lun ija +tEli»: capture artefacts
    if "…" in t or "..." in t:
        return False  # «ɣuri … / dari …» és un motlle, no una frase: no es pot ni dir ni endevinar
    return True


def quotable(shi: str, slug: Optional[str] = None) -> bool:
    """A text a LESSON can quote: well formed, and in Latin letters as the course is written.

    Practice must NOT borrow this. A sentence you can hear and read in Tifinagh is perfectly
    practisable, and this app teaches Tifinagh. Until 2026-10-22 the practice filter called this
    very function, which silently emptied every list captured in Tifinagh: the «Tamazight For
    All» fables, 84 sentences, showed up as «aquest grup no té cap drill»."""
    if not well_formed(shi, slug):
        return False
    t = _clean_text(shi)
    if not re.search(r"[A-Za-zɣḥṣṭẓɛšḍčǧ]", t) or re.search(r"[\u2D30-\u2D7F]", t):
        return False  # Tifinagh-only captures: not readable in a Latin-script course
    return True


def paradigms(rows: List, limit: int = 14) -> List[dict]:
    """The unit's conjugation and plural lists — «rgl, rglkh, trgld, irgl…», «afus / ifasn» — as the
    Beni Mellal deck wrote them. They are not sentences, so no lesson quotes them as an example and
    no test asks about them; but they are the paradigms of the very variety we teach, so the lesson
    builds its tables from them instead of inventing forms. The fullest lists first."""
    out, seen = [], set()
    for d in rows:
        shi = _clean_text(d.text_tachelhit); ca = _clean_text(d.text_catalan)
        if kind(shi) != "list" or not ca or len(shi) > 170 or re.search(r"[\u2D30-\u2D7F]", shi):
            continue
        k = shi.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append({"id": d.id, "shi": shi, "ca": ca})
    out.sort(key=lambda e: (-(e["shi"].count(",") + e["shi"].count("/")), len(e["shi"])))
    return out[:limit]


def practice_rows(rows: List, limit: int = 200, slug: Optional[str] = None) -> List:
    """The drills a unit's practice test is made of: real sentences (plus single words in the units
    about words), no conjugation lists, no placeholders, no capture artefacts; in the rows' order."""
    return [d for d in rows if quotable(d.text_tachelhit, slug)][:limit]


# The longest example a unit may quote or ask about, by level: a level-1 card is for someone who
# knows nothing yet, so its examples (and its quiz options) are a few words long.
MAX_WORDS = {1: 4, 2: 8, 3: 14}
MAX_CHARS = {1: 32, 2: 60, 3: 90}
MAX_CHARS_CA = {1: 48, 2: 90, 3: 110}  # the Catalan meaning too: a level-1 quiz never shows a long sentence


def level_of(slug: Optional[str]) -> int:
    return next((u["level"] for u in UNITS if u["slug"] == slug), 3)


def fits_level(shi: str, slug: Optional[str], ca: str = "") -> bool:
    lv = level_of(slug)
    return len(re.findall(r"[^\W\d_]+", shi)) <= MAX_WORDS[lv] and len(shi) <= MAX_CHARS[lv] and len(ca) <= MAX_CHARS_CA[lv]


def simplicity(e: dict) -> int:
    """How basic an example is: fewer words first, then shorter."""
    return len(re.findall(r"[^\W\d_]+", e["shi"])) * 100 + len(e["shi"])


def pick_examples(rows: List, limit: int = 90, slug: Optional[str] = None) -> List[dict]:
    """The drills a lesson can quote: short real sentences (and words, in the units about words),
    the ones with a picture and a voice first, no duplicates."""
    cands = []
    for d in rows:
        shi = _clean_text(d.text_tachelhit); ca = _clean_text(d.text_catalan)
        if not ca or not quotable(shi, slug) or len(shi) > 90 or len(ca) > 110 or not fits_level(shi, slug, ca):
            continue
        if shi.lower() == ca.lower():
            continue  # «Adeu» = «Adeu»: the Catalan typed in the Tamazight field
        cands.append(example_dict(d))
    # within each source, the pictured-and-voiced sentences first, then the shortest
    cands.sort(key=lambda e: (not (e["image_url"] and e["audio_url"]), not e["audio_url"], not e["image_url"], simplicity(e), e["id"]))
    return _spread(cands, limit)


def _spread(cands: List[dict], limit: int) -> List[dict]:
    """Take from all three sources at once — our own Aït Mraw speakers, the Beni Mellal deck and the
    rest — instead of filling the whole pool with the first one: a unit with 300 Aït Mraw sentences
    used to hide its 500 Beni Mellal ones from the lesson entirely. Two Aït Mraw sentences for every
    two from Beni Mellal and one from elsewhere, and a source that runs out leaves its turns to the
    others. Sentences that sound nearly the same («ihla ghori udghar» twice over) count as one."""
    import practice
    buckets: List[List[dict]] = [[], [], []]
    seen = set()
    for e in cands:
        key = " ".join(practice.sound_key(w) for w in re.findall(r"[^\W\d_]+", e["shi"].lower()))
        if not key or key in seen:
            continue
        seen.add(key)
        buckets[origin_rank(e)].append(e)
    # Primer les que es poden ESCOLTAR, repartides igual entre les tres fonts; i només quan
    # s'han acabat, les mudes. Repartir-les totes barrejades feia que una font que ja no tenia
    # veus seguís posant frases mudes mentre una altra encara en tenia de gravades: «numerals»
    # servia 18 exemples sense veu de 42, i 10 d'aquests sortien de la font que n'havia exhaurit
    # les gravades. Dins de cada tanda el repartiment és el de sempre.
    voiced = [[e for e in b if e.get("audio_url")] for b in buckets]
    silent = [[e for e in b if not e.get("audio_url")] for b in buckets]
    out: List[dict] = []
    for pool in (voiced, silent):
        turns, k = (0, 0, 1, 1, 2), 0
        while len(out) < limit and any(pool):
            b = pool[turns[k % len(turns)]]
            k += 1
            if b:
                out.append(b.pop(0))
    return out


BANNED_TERMS = ("apofonia", "díctic", "diàtesi", "morfema", "lexema", "radical", "acomplert", "inacomplert",
                "sintagma", "tema verbal", "al·lomorf", "clític")

def _study_prompt(unit: dict, reference: str) -> str:
    return (
        f"Study these sections of an Amazigh grammar reference (amazic.cat compendium, in Catalan, centred on the "
        f"Souss Tachelhit with notes on other varieties) for the lesson «{unit['title']}». Write a STUDY SHEET in "
        "Catalan, at most 900 words, that a teacher will use to explain this point with real sentences from the "
        "Central Atlas (Aït Mraw near Boutharar, Tinghir; Beni Mellal):\n"
        "1. RULES: the rules of this point, numbered, one or two sentences each, in plain words.\n"
        "2. FORMS: the forms (prefixes, suffixes, particles, pronouns…) as a compact table in standard Latin "
        "spelling (ɣ, ḥ, ṣ, ṭ, ẓ, ɛ, š), with what each one means.\n"
        "3. VARIETIES: which rules or forms the reference marks as Souss-only, Central Atlas (tamazight) or "
        "general; what the reference says the Central Atlas does differently, if anything.\n"
        "4. WHAT TO LOOK FOR in a sentence to recognise this point (the visible clues).\n"
        "5. STEPS: the point cut into 7 to 9 teachable steps, in the order a beginner meets them, one line each "
        "(«pas 3: el plural en i…n»), so a lesson can follow them one card at a time.\n"
        "6. MISTAKES: two or three mistakes a Catalan speaker makes with this point.\n"
        "Keep only what the reference says; do not add rules from elsewhere. Spell the reference's variety "
        "abbreviations out (CLḤ = taixelhit del Souss, MZƔ = tamazight del Marroc Central, QBYL = cabilenc, RIF = "
        "rifeny, ZNT = zenata). Start directly with «1. REGLES»: no preamble, no closing remark.\n\n"
        f"REFERENCE:\n{reference}"
    )


SHEET_VERSION = 2  # the sheet's shape; a change here reads the compendium again


def sheet_for(db, slug: str, grammar_md: str, force: bool = False) -> str:
    """The unit's rule sheet, read from the compendium once and kept in `grammar_lessons` under
    «sheet:<slug>»: writing a lesson again then costs one call, not two, and the sheet only changes
    when its shape or the unit's sections do."""
    from datetime import datetime
    from models import GrammarLesson
    key, want = f"sheet:{slug}", ",".join(SECTIONS.get(slug) or [])
    row = db.query(GrammarLesson).filter(GrammarLesson.id == key).first() if db is not None else None
    if row is not None and not force and (row.version or 0) >= SHEET_VERSION:
        try:
            kept = json.loads(row.body)
            if kept.get("sections") == want and kept.get("sheet"):
                return kept["sheet"]
        except Exception:
            pass
    sheet = study(slug, grammar_md)
    if db is not None and sheet:
        body = json.dumps({"sheet": sheet, "sections": want}, ensure_ascii=False)
        if row is None:
            db.add(GrammarLesson(id=key, body=body, version=SHEET_VERSION))
        else:
            row.body, row.version, row.updated_at = body, SHEET_VERSION, datetime.utcnow()
        db.commit()
    return sheet


def study(slug: str, grammar_md: str) -> str:
    """The rule sheet for a unit: the compendium's sections read and condensed once."""
    unit = next((u for u in UNITS if u["slug"] == slug), None)
    reference = reference_text(slug, grammar_md) if unit else ""
    if not reference:
        return ""
    from gemini_client import gemini_generate
    return _clean_sheet(gemini_generate("You are a careful reader of Amazigh grammar, writing notes in Catalan.",
                                        [{"role": "user", "text": _study_prompt(unit, reference)}],
                                        max_output_tokens=3500, temperature=0.2, timeout=300))


def _clean_sheet(s: Optional[str]) -> str:
    """Drop a chatty preamble: the sheet starts at its first numbered or bold heading."""
    t = (s or "").replace("\r", "")
    m = re.search(r"(?m)^(\*\*|#+ |1\.\s)", t)
    return (t[m.start():] if m else t).strip()


def _lesson_prompt(unit: dict, examples: List[dict], sheet: str, tables: Optional[List[dict]] = None,
                   deep: bool = False) -> str:
    """The lesson the unit opens with, or — with `deep` — its second level: the same method and the
    same sources, more steps, and the fine points the first lesson leaves out."""
    # the writer sees the simplest examples first: a one-word greeting before a full sentence
    ex = "\n".join(f"- id {e['id']} ({e.get('origin') or 'origen desconegut'}{', gravat' if e.get('recorded') else ''}): «{e['shi']}» — {e['ca']}" for e in sorted(examples, key=simplicity))
    return (
        f"Write the lesson «{unit['title']}» of a course of Central Atlas Tamazight (the speech of Aït Mraw near "
        "Boutharar, Tinghir, and of Beni Mellal) for Catalan-speaking adults who are NOT linguists: a curious "
        "traveller, a partner of a Tamazight speaker. Plain, warm Catalan; short sentences; explain every grammatical "
        "word the first time you use it («el perfectiu, la forma que es fa servir per a accions acabades…»). Never use "
        "these words: " + ", ".join(BANNED_TERMS) + ". Say «pronom enganxat al verb» instead of clític, «forma de "
        "passat / acció acabada» instead of acomplert, and so on.\n\n"
        "METHOD. The study sheet below condenses the grammar reference and ends with the steps the point breaks "
        "into: follow them, one explanation each. The sentences below are what OUR speakers "
        "actually say. Your job is to show how the rules of the sheet appear in OUR sentences: every explanation "
        "states one rule, quotes 4-6 of our sentences that show it, and names the exact piece of each sentence that "
        "shows the rule (the \"focus\": a substring copied character for character from the sentence as written). The "
        "focus must be the rule itself (the particle, the ending, the pronoun being taught), never another word of the "
        "sentence; a sentence that does not visibly contain the rule must not be quoted at all. "
        "Quote from BOTH of our sources across the lesson: the Aït Mraw sentences (our own recorded speakers) "
        "first inside each step, and the Beni Mellal deck's sentences too — a lesson that never quotes Beni Mellal "
        "is wasting half of what we have. If our sentences show "
        "the rule differently from the sheet (another form, another spelling, a particle missing), say so plainly: "
        "the speakers are right about their own speech, and the sheet describes mainly the Souss. If no sentence of "
        "ours shows a rule, leave that rule out or say we have no example yet; never invent a sentence.\n\n"
        + ((unit.get("brief") + " ") if unit.get("brief") else "")
        + ("LEVEL 1 UNIT, for someone who knows NOTHING yet: only the most basic forms, each step one thing to say or "
           "recognise, no grammar vocabulary at all, no rule that needs a term to be explained. If the examples only "
           "allow 2-3 steps, write 2-3 steps. "
           if unit.get("level") == 1 else
           "LEVEL 2 UNIT: short sentences, one rule per step, every term explained in plain words. "
           if unit.get("level") == 2 else "")
        + ("SECOND LEVEL. The learner has already read the first lesson of this unit and has answered its "
           "questions: do not teach its basics again. Take the point further — the forms the first lesson left "
           "aside, what changes after a particle or in a question, what our speakers do that the sheet does not "
           "describe, the places where the two decks differ — and quote the sentences the first lesson did not "
           "use (they come first in the list below). Say «ja saps que…» when you build on something known.\n\n"
           if deep else "")
        + "Build the lesson as STEPS, each one a card the learner reads in a few seconds:\n"
        + ("- 10 to 14 steps of type \"explain\": a title (3-6 words), a text of 35-70 words, example_ids (4-6, "
           "ONLY from the sentences below) and \"focus\": {id: substring} for each quoted sentence, the same rules "
           "as always. Cut the point finer than the first lesson did: one narrow rule per step.\n"
           if deep else
        "- 7 to 9 steps of type \"explain\" (eight when the unit allows it; with 40 sentences or more below, fewer "
        "than seven is not acceptable — cut the point into smaller rules rather than writing fewer steps): a title "
        "(3-6 words), a text of 35-70 words, example_ids (4-6, ONLY from "
        "the sentences below) and \"focus\": {id: substring} for each quoted sentence. Fewer than four sentences in a "
        "step is not acceptable: if four of our sentences do not show the rule, teach a rule they do show. "
        "START WITH THE MOST BASIC: "
        "the first step uses the shortest examples (a single word or a two-word formula when there is one, e.g. a "
        "bare greeting, a bare noun, a bare number) and each step builds on the previous one, so the longest "
        "sentences come last. Never open a unit with a long sentence.\n")
        + "- 1 or 2 steps of type \"pattern\" (one after the first explanations, one near the end): a title and 3-8 rows of [form, meaning, "
        "example], the forms in standard Latin spelling (ɣ, ḥ, ṣ, ṭ, ẓ, ɛ, š). The THIRD cell, the example, must be "
        "a word COPIED from one of OUR SENTENCES below, letter for letter. If no sentence of this unit shows that "
        "form, leave the third cell empty — never invent a word to fill it. (A sounds table once cited «meddn» for "
        "ḍ, a word with no ḍ in it, and «Tabrat» for ṭ: neither is anywhere in the library.)"
        + (" OUR LISTS below are the paradigms our own speakers wrote for this unit: build the table from THEM, "
           "form by form as they are written, and never put in a form that is in neither the lists nor our "
           "sentences." if tables else "")
        + "\n"
        "- 1 step of type \"tip\": a text of 30-60 words on the mistake Catalan speakers make most, or a memory trick.\n"
        "- 1 step of type \"dialect\": 25-70 words on how our speakers (Aït Mraw, Beni Mellal) do it versus what the "
        "sheet says for the Souss, with the evidence from our sentences; leave it out only if there is no difference.\n"
        "Also an \"intro\" of 25-45 words: what the learner will be able to do after this unit.\n"
        "The sentences are written as their speakers wrote them (spelling varies: 3 for ɛ, gh for ɣ, kh for x, "
        "capitals for emphatics): when your text names a form, give the standard spelling and, if the sentence spells "
        "it differently, say so in a few words.\n"
        # Dues errades que el curs ha fet de debò, i que un lector les ha vistes (2026-10-23):
        # la targeta «iga» deia que serveix «per al passat» i anomenava el verb `g` mentre totes
        # les frases citades el diuen amb j (ija, nja, jan).
        "TRUTH: a state verb in the perfective means NOW, not the past: «iga» is «he is», «ira» "
        "«he wants», «illa» «there is». Never call such a form a past tense. And when the "
        "sentences you quote pronounce or spell the form differently from the name you give it "
        "(our speakers say ija, nja, jan where the sheet writes iga, nga, gan), say so in the "
        "same breath, in the same step: a reader who sees a rule about one letter and six "
        "sentences with another letter cannot follow the lesson.\n"
        "STYLE: Latin script only (never Arabic script, never transliterations in brackets). Never mention example "
        "ids or numbers in the texts: refer to a sentence by quoting a few of its words. Talk to the learner («veuràs», "
        "«fixa't»), never about «the sheet» or «the reference».\n\n"
        "Answer ONLY with a JSON object: {\"intro\": str, \"steps\": [{\"type\": \"explain\", \"title\": str, \"text\": str, "
        "\"example_ids\": [int], \"focus\": {\"<id>\": str}}, {\"type\": \"pattern\", \"title\": str, \"rows\": [[str, str, str]]}, "
        "{\"type\": \"tip\", \"text\": str}, {\"type\": \"dialect\", \"text\": str}]}.\n\n"
        f"OUR SENTENCES (real speakers; origin in brackets):\n{ex}\n\n"
        + (("OUR LISTS (paradigms our own speakers wrote out: all the forms of one verb or one noun, in their "
            "spelling; never quote these as sentences, they are tables):\n"
            + "\n".join(f"- «{t['shi']}» — {t['ca']}" for t in (tables or [])) + "\n\n") if tables else "")
        + f"STUDY SHEET (from the amazic.cat compendium):\n{sheet}"
    )


def _parse_lesson(answer: str, examples: List[dict], notes: Optional[Dict[int, str]] = None) -> dict:
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        raise ValueError(f"no JSON in answer: {(answer or '')[:120]}")
    raw = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))  # Gemini sometimes leaves a trailing comma
    by_id = {e["id"]: e for e in examples}
    steps = []
    for s in raw.get("steps") or []:
        t = (s.get("type") or "").strip()
        if t == "explain":
            ids = [int(i) for i in (s.get("example_ids") or []) if str(i).strip().lstrip("-").isdigit() and int(i) in by_id]
            if not _clean_text(s.get("text")):
                continue
            focus = s.get("focus") if isinstance(s.get("focus"), dict) else {}
            exs = []
            for i in list(dict.fromkeys(ids))[:6]:
                e = dict(by_id[i]); frag = _clean_text(str(focus.get(str(i)) or focus.get(i) or ""))
                if frag and frag.lower() in e["shi"].lower() and len(frag) < len(e["shi"]):
                    e["focus"] = frag
                exs.append(e)
            steps.append({"type": "explain", "title": _clean_text(s.get("title")) or "", "text": _clean_prose(s.get("text")), "examples": exs})
        elif t == "pattern":
            rows = [[_clean_text(c) for c in r][:3] for r in (s.get("rows") or []) if isinstance(r, list) and r]
            if rows:
                steps.append({"type": "pattern", "title": _clean_text(s.get("title")) or "", "rows": rows[:8]})
        elif t in ("tip", "dialect") and _clean_text(s.get("text")):
            steps.append({"type": t, "text": _clean_prose(s.get("text"))})
    if not any(s["type"] == "explain" for s in steps):
        raise ValueError("lesson without explain steps")
    return _top_up({"intro": _clean_prose(raw.get("intro")), "steps": steps}, examples, notes=notes)


def _fold(t: str) -> str:
    """A text as it sounds, so «ghori» and «ɣur-i» are the same piece of language: our speakers
    spell the same word three ways."""
    import practice
    # whole words, hyphens kept: «ɣur-i» is one piece of language, not «ɣur» and «i»
    return "".join(practice.sound_key(w) for w in re.split(r"\s+", (t or "").lower()) if w)


def _mark(shi: str, frag: str) -> Optional[str]:
    """Where `frag` is written inside `shi`: the piece itself when it is there letter for letter,
    then the same piece without the hyphen that marks an affix («-an» is how an ending is written,
    «da-» how a particle is), and last the word that sounds like it («ghori» for «ɣur-i»)."""
    if not shi or not frag:
        return None
    low, fl = shi.lower(), frag.lower()
    if fl in low and len(frag) < len(shi):
        return shi[low.index(fl):low.index(fl) + len(fl)]
    bare = fl.strip("-–—.·_ ")
    if bare and bare != fl and len(bare) < len(shi):
        # an ENDING is marked where a word ends with it, not at the first letters that match
        if fl.startswith("-"):
            for w in re.split(r"\s+", shi):
                clean = w.strip(".,;:!?«»()")
                if clean and clean.lower().endswith(bare) and len(bare) < len(clean):
                    i = len(clean) - len(bare)
                    return clean[i:]
        elif fl.endswith("-"):
            for w in re.split(r"\s+", shi):
                clean = w.strip(".,;:!?«»()")
                if clean and clean.lower().startswith(bare):
                    return clean[:len(bare)]
        if bare in low:
            return shi[low.index(bare):low.index(bare) + len(bare)]
    key = _fold(frag)
    if not key:
        return None
    for w in re.split(r"\s+", shi):
        if w and (key == _fold(w) or (len(key) > 2 and key in _fold(w))):
            return w.strip(".,;:!?«»()") or None
    return None


def _kin(e: dict) -> set:
    """The words of an example, for measuring how close two sentences of the unit are."""
    return {w for w in re.findall(r"[^\W\d_]+", (e.get("shi") or "").lower()) if len(w) > 2}


def _top_up(lesson: dict, examples: List[dict], want: int = 4, notes: Optional[Dict[int, str]] = None) -> dict:
    """An explanation that quotes fewer than `want` sentences gets more from the unit's own pool:
    first the sentences that really contain the piece being taught (by sound, so another spelling of
    the same word counts); then, if the step is still short, the unit's sentences that share a word
    with what it already shows — kin, not padding, so a step is never filled with sentences that
    have nothing to do with it. Never a sentence the lesson already shows."""
    used = quoted_ids(lesson)
    for s in lesson["steps"]:
        if s["type"] != "explain" or len(s["examples"]) >= want:
            continue
        frags = [e["focus"] for e in s["examples"] if e.get("focus")]
        for e in s["examples"]:  # a sentence the writer quoted without saying where the rule is
            if not e.get("focus"):
                for frag in frags:
                    mark = _mark(e["shi"], frag)
                    if mark:
                        e["focus"] = mark
                        break
        for frag in frags:
            key = _fold(frag)
            if not key:
                continue
            for e in examples:
                if len(s["examples"]) >= want:
                    break
                if e["id"] in used or not e["shi"]:
                    continue
                if key not in _fold(e["shi"]) and frag.lower() not in e["shi"].lower():
                    continue
                add = dict(e)
                mark = _mark(e["shi"], frag)
                if mark:
                    add["focus"] = mark
                s["examples"].append(add); used.add(e["id"])
        if len(s["examples"]) >= want or not s["examples"]:
            continue
        near = set().union(*(_kin(e) for e in s["examples"]))
        kin = [(len(near & _kin(e)), e) for e in examples if e["id"] not in used and e.get("shi")]
        kin = sorted(((n, e) for n, e in kin if n), key=lambda p: (-p[0], simplicity(p[1])))
        for _n, e in kin:
            if len(s["examples"]) >= want:
                break
            add = dict(e)
            for frag in frags:
                mark = _mark(e["shi"], frag)
                if mark:
                    add["focus"] = mark
                    break
            # a sentence with nothing marked and nothing said about it is noise under an
            # explanation: the learner sees a bare sentence and cannot tell why it is there
            why = (notes or {}).get(e["id"])
            if not add.get("focus") and not why:
                continue
            if why:
                add["why"] = why
            s["examples"].append(add); used.add(e["id"])
    return lesson


def _words(t: str) -> int:
    """How many words a text has: what tells a one-word answer from a whole sentence."""
    return len(re.findall(r"[^\W\d_]+", t or ""))


#: On viuen les imatges que hem triat nosaltres: les il·lustracions que fem per a una frase i el
#: que puja l'amo. La resta són imatges trobades per la xarxa amb llicència lliure.
OUR_MEDIA = ("res.cloudinary.com",)


def our_picture(url: Optional[str]) -> bool:
    """Si aquesta imatge la vam triar per a AQUESTA frase.

    Una imatge trobada il·lustra com a molt una paraula, i de vegades ni això: a «ɣuri … / dari …»
    «tinc …» li havia tocat una estàtua daurada d'un casino de Macau. Serveix per acompanyar una
    frase que ja es llegeix; no serveix per a una pregunta on la imatge és l'enunciat, perquè
    llavors la pregunta no es pot contestar. L'amo ho va dir així: «aquí no entenc la pregunta,
    potser la imatge està malament»."""
    u = (url or "").strip().lower()
    return bool(u) and any(h in u for h in OUR_MEDIA)


def _askable(kind: str, e: dict) -> bool:
    """Si d'aquesta frase se'n pot fer una pregunta d'aquesta mena."""
    if kind == "listen":
        return bool(e.get("audio_url"))
    if kind == "picture":
        return our_picture(e.get("image_url"))
    return True


def _with_quizzes(lesson: dict, examples: List[dict]) -> dict:
    """A quick check after every explanation and a short review before the end, three kinds in turn:
    read the meaning and pick the sentence; listen to the voice and pick the meaning; look at the
    picture and pick the sentence. Wrong answers come from the same unit and never mean the same
    thing, and no sentence is asked about twice."""
    import random
    pool = [e for e in examples if e["shi"] and e["ca"]]
    same = lambda a, b: a[:10].lower() == b[:10].lower()
    out, n_explain, n_quiz, used = [], 0, 0, set()
    for s in lesson["steps"]:
        out.append(s)
        if s["type"] != "explain":
            continue
        n_explain += 1
        if len(pool) < 4:
            continue
        kind = ("meaning", "listen", "picture")[n_quiz % 3]
        fresh = [e for e in s["examples"] if e["id"] not in used] + [e for e in pool if e["id"] not in used]
        target = next((e for e in fresh if e in pool and _askable(kind, e)), None)
        if target is None:
            kind, target = "meaning", next((e for e in fresh if e in pool), None)
        if target is None:
            continue
        used.add(target["id"]); n_quiz += 1
        rnd = random.Random(target["id"])
        field = "ca" if kind == "listen" else "shi"
        cands = [e for e in pool if e["id"] != target["id"] and e["shi"].lower() != target["shi"].lower()
                 and not same(e["ca"], target["ca"])]
        rnd.shuffle(cands)
        # The wrong answers must be able to pass for the right one. A single word among three long
        # sentences is given away by its shape alone, and the four together read as nonsense: so
        # the nearest in length come first, and the choice stays random among equals.
        n_target = _words(target[field])
        cands.sort(key=lambda e: (abs(_words(e[field]) - n_target), (_words(e[field]) > 1) != (n_target > 1)))
        wrong = list(dict.fromkeys(e[field] for e in cands))
        if len(wrong) < 3:
            continue
        options = [target[field]] + wrong[:3]
        rnd.shuffle(options)
        question = {"meaning": f"Com es diu «{target['ca']}»?", "listen": "Escolta. Què vol dir?", "picture": "Quina frase va amb la imatge?"}[kind]
        out.append({"type": "quiz", "kind": kind, "question": question, "options": options,
                    "answer": options.index(target[field]), "example": target})
    out += _review_quizzes(pool, used, n_quiz, 3)
    out.append({"type": "end"})
    return {**lesson, "steps": out}


def _review_quizzes(pool: List[dict], used: set, n_quiz: int, how_many: int) -> List[dict]:
    """A last round over sentences the lesson did not already ask about."""
    import random
    same = lambda a, b: a[:10].lower() == b[:10].lower()
    out = []
    for _ in range(how_many):
        kind = ("meaning", "listen", "picture")[n_quiz % 3]
        target = next((e for e in pool if e["id"] not in used and _askable(kind, e)), None)
        if target is None:
            kind = "meaning"
            target = next((e for e in pool if e["id"] not in used), None)
        if target is None:
            break
        used.add(target["id"]); n_quiz += 1
        rnd = random.Random(target["id"] * 7)
        field = "ca" if kind == "listen" else "shi"
        cands = [e for e in pool if e["id"] != target["id"] and e["shi"].lower() != target["shi"].lower()
                 and not same(e["ca"], target["ca"])]
        rnd.shuffle(cands)
        n_target = _words(target[field])   # the wrong answers look like the right one (see _with_quizzes)
        cands.sort(key=lambda e: (abs(_words(e[field]) - n_target), (_words(e[field]) > 1) != (n_target > 1)))
        wrong = list(dict.fromkeys(e[field] for e in cands))
        if len(wrong) < 3:
            break
        options = [target[field]] + wrong[:3]
        rnd.shuffle(options)
        question = {"meaning": f"Repàs: com es diu «{target['ca']}»?", "listen": "Repàs: escolta. Què vol dir?",
                    "picture": "Repàs: quina frase va amb la imatge?"}[kind]
        out.append({"type": "quiz", "kind": kind, "question": question, "options": options,
                    "answer": options.index(target[field]), "example": target})
    return out


def write_lesson(slug: str, grammar_md: str, examples: List[dict], sheet: Optional[str] = None,
                 tables: Optional[List[dict]] = None, notes: Optional[Dict[int, str]] = None,
                 deep: bool = False) -> dict:
    """Ask Gemini for the unit's steps and attach the examples and the quick checks. With `deep`,
    the unit's second level: more steps, finer rules, and the sentences the first lesson left."""
    unit = next((u for u in UNITS if u["slug"] == slug), None)
    if unit is None:
        raise ValueError("unknown unit")
    from gemini_client import gemini_generate
    sheet = study(slug, grammar_md) if sheet is None else sheet
    answer = gemini_generate("You are a patient, clear teacher of Amazigh for beginners, writing in Catalan.",
                             [{"role": "user", "text": _lesson_prompt(unit, examples, sheet, tables, deep=deep)}],
                             max_output_tokens=9000, temperature=0.3, timeout=420)
    lesson = _parse_lesson(answer, examples, notes)
    lesson["study"] = sheet  # the rule sheet travels with the lesson (shown to admins)
    return _with_quizzes(lesson, examples)


def quoted_ids(lesson: dict) -> set:
    """The drills a lesson's steps quote."""
    ids = set()
    for s in lesson.get("steps") or []:
        for e in s.get("examples") or []:
            ids.add(e.get("id"))
        if s.get("example"):
            ids.add(s["example"].get("id"))
    return {i for i in ids if i is not None}


def drill_for_row(db, slug: str, step: int, row: int, user, deep: bool = False) -> dict:
    """La frase de la biblioteca que hi ha darrere una fila d'una taula de formes.

    Una taula de formes és el lloc on la gramàtica es veu d'un cop d'ull —ɣur-i, ɣur-k, ɣur-s—
    i fins ara era l'únic lloc de la lliçó que no es podia **dir**. L'amo: «crec que aquí
    s'hauria de poder gravar la veu». Té raó: una forma que no s'ha sentit mai no se sap dir.

    Funciona com les línies del Mètode: la primera vegada la fila es torna una frase de la
    biblioteca (amb la seva unitat i demanant veu), i d'aleshores ençà s'hi afegeixen veus. La
    lliçó se'n recorda, i per això el micròfon canvia de color quan ja és nostra.
    """
    import json

    from models import Drill as DrillModel, GrammarLesson
    r = db.query(GrammarLesson).filter(GrammarLesson.id == _row_id(slug, deep)).first()
    if r is None:
        raise ValueError("aquesta unitat encara no té lliçó")
    lesson = json.loads(r.body)
    steps = lesson.get("steps") or []
    if not (0 <= step < len(steps)) or steps[step].get("type") != "pattern":
        raise ValueError("aquí no hi ha cap taula de formes")
    rows = steps[step].get("rows") or []
    if not (0 <= row < len(rows)):
        raise ValueError("aquí no hi ha cap fila")

    ids = steps[step].get("drill_ids") or {}
    got = ids.get(str(row))
    if got:
        d = db.query(DrillModel).filter(DrillModel.id == got).first()
        if d:
            return {"drill_id": d.id, "created": False}

    cells = list(rows[row]) + ["", ""]
    shi, ca = _clean_text(cells[0]), _clean_text(cells[1])
    if not shi:
        raise ValueError("aquesta fila no té cap forma per dir")

    d = DrillModel(
        text_tachelhit=shi, text_catalan=ca or None,
        # D'on surt, dit a la cara: és una forma d'una taula del curs, no una frase que hagi dit ningú.
        tag=f"gramatica-{slug}, taula de formes",
        grammar=slug, grammar_source="owner",
        voice_wanted=True,
        voice_wanted_by=(getattr(user, "display_name", None) or getattr(user, "username", None)),
        created_by_user_id=getattr(user, "id", None),
    )
    db.add(d)
    db.commit()
    db.refresh(d)

    ids[str(row)] = d.id
    steps[step]["drill_ids"] = ids
    r.body = json.dumps(lesson, ensure_ascii=False)
    db.commit()
    return {"drill_id": d.id, "created": True}


GROWTH = 0.3  # a unit that gained this share of drills (and at least 5) gets its lesson written again


def _row_id(slug: str, deep: bool = False) -> str:
    """Where a unit's lesson is kept. The second level sits in the same table under «deep:», the
    way the rule sheet sits under «sheet:»."""
    return f"deep:{slug}" if deep else slug


def _current(row, unit_ids: Optional[set], deep: bool = False) -> Optional[dict]:
    """The stored lesson when it is up to date: right version; when the unit's drills are given,
    every sentence it quotes still in the unit (a reclassified unit gets its lesson written again)
    and the unit has not grown much since the lesson was written (new recordings and captures join
    the lesson, instead of waiting for a format change)."""
    if row is None:
        return None
    if getattr(row, "hand_written", False):
        # Somebody wrote this one. It is current by definition, whatever the version says (#187).
        try:
            return json.loads(row.body)
        except Exception:
            return None
    if (row.version or 0) < (DEEP_VERSION if deep else LESSON_VERSION):
        return None
    try:
        lesson = json.loads(row.body)
    except Exception:
        return None
    if unit_ids is not None:
        if quoted_ids(lesson) - unit_ids:
            return None
        size = lesson.get("unit_size")
        if not isinstance(size, int):
            return None  # written before the rule existed: written again once, then it records the size
        if len(unit_ids) >= size + max(5, int(size * GROWTH)):
            return None
    return lesson


_writing: set = set()
_write_lock = threading.Lock()

#: Per què NO s'ha pogut escriure una lliçó, per unitat i nivell. Una escriptura que falla ho ha
#: de dir: la pàgina deia «s'està escrivint ara mateix» per sempre i no hi havia manera de saber,
#: des de fora, que el redactor estava sense crèdit.
_failures: dict = {}


def writing() -> List[str]:
    """The units whose lesson is being written right now."""
    with _write_lock:
        return sorted(_writing)


def _stored(row) -> Optional[dict]:
    """Whatever lesson is kept for a unit, fresh or not."""
    try:
        return json.loads(row.body) if row is not None else None
    except Exception:
        return None


def _store_lesson(db, slug: str, lesson: dict, deep: bool = False) -> None:
    from datetime import datetime
    from models import GrammarLesson
    body = json.dumps(lesson, ensure_ascii=False)
    version = DEEP_VERSION if deep else LESSON_VERSION
    key = _row_id(slug, deep)
    row = db.query(GrammarLesson).filter(GrammarLesson.id == key).first()
    if row is None:
        db.add(GrammarLesson(id=key, body=body, version=version))
    else:
        row.body = body; row.version = version; row.updated_at = datetime.utcnow()
    db.commit()


def _write_in_background(session_factory, slug: str, grammar_md: str, examples: List[dict], unit_ids: Optional[set],
                         tables: Optional[List[dict]] = None, deep: bool = False) -> bool:
    """Write the unit's lesson — or its «a fons» level — on a thread of its own, once at a time per
    unit and level. True when this call started the writing."""
    key = _row_id(slug, deep)
    with _write_lock:
        if key in _writing:
            return False
        _writing.add(key)

    def run():
        db = session_factory()
        try:
            lesson = write_lesson(slug, grammar_md, examples, sheet=sheet_for(db, slug, grammar_md),
                                  tables=tables,
                                  notes=notes_for(db, slug, {e["id"]: (e.get("shi") or "", e.get("ca") or "") for e in examples}),
                                  deep=deep)
            if unit_ids is not None:
                lesson["unit_size"] = len(unit_ids)  # so growth of the unit can be noticed later
            _store_lesson(db, slug, lesson, deep=deep)
            print(f"[GRAMMAR] {'a fons' if deep else 'lesson'} {slug}: written ({len(lesson.get('steps') or [])} steps)")
        except Exception as e:
            # I que es vegi. Una escriptura que falla deixava la pàgina dient «s'està escrivint
            # ara mateix» per sempre: amb Gemini sense crèdit, els 22 nivells «a fons» que
            # falten ho han dit tota la nit sense que res digués per què.
            _failures[key] = {"when": time.time(), "why": str(e)[:200]}
            print(f"[GRAMMAR] {'a fons' if deep else 'lesson'} {slug}: {e}")
        else:
            _failures.pop(key, None)
        finally:
            try:
                db.close()
            except Exception:
                pass
            with _write_lock:
                _writing.discard(key)

    threading.Thread(target=run, daemon=True).start()
    return True


def _placeholder(slug: str, examples: List[dict], deep: bool = False) -> dict:
    unit = next((u for u in UNITS if u["slug"] == slug), None)
    failed = _failures.get(_row_id(slug, deep))
    if failed:
        return {"intro": "", "writing": False, "failed": failed["why"], "steps": [
            {"type": "explain", "title": (unit or {}).get("title") or "Unitat",
             "text": ("Aquesta lliçó no s'ha pogut escriure: " + failed["why"] + "\n\nMentrestant "
                      "pots escoltar i llegir les frases de la unitat, que són les de sempre."),
             "examples": examples[:4]},
            {"type": "end"}]}
    return {"intro": "", "writing": True, "steps": [
        {"type": "explain", "title": (unit or {}).get("title") or "Unitat",
         "text": "S’està escrivint aquesta lliçó ara mateix. Mentrestant pots escoltar i llegir les frases de la "
                 "unitat; la lliçó apareixerà tota sola en un minut.",
         "examples": examples[:4]},
        {"type": "end"}]}


def _with_notes(lesson, notes: Dict[int, str]):
    """Put «why this sentence is here» on every sentence a lesson shows, matched by drill id. Late,
    like the glosses: a note written after the lesson still reaches the learner."""
    if not isinstance(lesson, dict) or not notes:
        return lesson
    for s in lesson.get("steps") or []:
        if not isinstance(s, dict):
            continue
        shown = list(s.get("examples") or [])
        if isinstance(s.get("example"), dict):
            shown.append(s["example"])
        for e in shown:
            why = notes.get(e.get("id"))
            if why:
                e["why"] = why
    return lesson


#: Com escriuen els nostres parlants cada so. La unitat ensenya que la ɛ s'escriu «ɛ», i la
#: biblioteca l'escriu «3» (vegeu #302): per saber si una frase PORTA el so que s'explica, s'han
#: de conèixer les dues maneres.
SOUND_SPELLINGS: Dict[str, tuple] = {
    "ɣ": ("ɣ", "ġ", "gh"),
    "x": ("x", "kh"),
    "ɛ": ("ɛ", "ε", "3"),
    "ḥ": ("ḥ",),
    "š": ("š", "c", "sh", "ch"),
    "ḍ": ("ḍ",),
    "ṭ": ("ṭ",),
    "ṣ": ("ṣ",),
    "ẓ": ("ẓ",),
    "q": ("q", "Q"),
    "ž": ("ž",),
    "kʷ": ("kʷ", "kw"),
    "gʷ": ("gʷ", "gw"),
}


def step_sounds(title: str) -> set:
    """Quins sons ensenya aquest pas.

    Dues maneres de dir-ho, i totes dues surten a les lliçons escrites: citat —«El so 'gh' o
    'ɣ': una 'r' francesa»— i llistat —«Consonants emfàtiques: ṭ, ḍ, ṣ, ẓ». La tifinag que el
    servidor penja al costat del so («'gh ⵖ'») no compta per a la cerca."""
    t = re.sub(r"[ⴰ-⵿]+", " ", title or "")
    found = set()
    for m in _QUOTED.finditer(t):
        bit = (m.group(1) or "").strip()
        for sound, spellings in SOUND_SPELLINGS.items():
            if bit == sound or bit in spellings:
                found.add(sound)
    if not found:
        # una llista de sons sense cometes: cada lletra sola, entre comes o espais
        for sound in SOUND_SPELLINGS:
            if re.search(r"(?<![^\W\d_])" + re.escape(sound) + r"(?![^\W\d_])", t):
                found.add(sound)
    return found


def has_sound(shi: str, sound: str) -> bool:
    """Si aquesta frase porta aquest so, escrit com sigui.

    La biblioteca guarda les lletres DESCOMPOSTES —«sġix» és una g i un punt a sobre a part,
    «3afaš» és una s i un capelló a part— i per això una comparació lletra a lletra amb «ġ» o
    «š» no les trobava mai. Es compara sempre amb el text ajuntat (NFC)."""
    low = unicodedata.normalize("NFC", shi or "").lower()
    return any(unicodedata.normalize("NFC", sp).lower() in low
               for sp in SOUND_SPELLINGS.get(sound, (sound,)))


def with_the_sound_it_teaches(lesson, slug: str):
    """A la unitat dels sons, un exemple ha de PORTAR el so que el pas explica.

    El pas de la š ensenyava «skrtn» «mireu-les», que no en té cap, de š. Es treuen els que no
    el porten —però només si al pas n'hi queda algun que sí—, perquè un pas sense cap exemple
    seria pitjor que un pas amb exemples barrejats, i perquè així una frase escrita d'una manera
    que encara no sabem llegir no desapareix de la lliçó sense que ningú se n'adoni.
    """
    if slug != SOUNDS_UNIT or not isinstance(lesson, dict):
        return lesson
    for s in lesson.get("steps") or []:
        if s.get("type") != "explain" or not s.get("examples"):
            continue
        vocals = vocals_del_pas(s.get("title") or "")
        if vocals:
            # «Les vocals bàsiques: a, i, u» posava `Zr` i `trt` d'exemple, que no en porten cap
            # (#365). «Fixa't com apareixen» damunt d'una paraula on no apareixen no ensenya res.
            porten = [e for e in s["examples"]
                      if any(porta_vocal(e.get("shi") or "", v) for v in vocals)]
            if porten:
                s["examples"] = _una_de_cada_vocal(porten, vocals)
            continue
        sounds = step_sounds(s.get("title") or "")
        if not sounds:
            continue
        keep = [e for e in s["examples"]
                if any(has_sound(e.get("shi") or "", so) for so in sounds)]
        if keep and len(keep) < len(s["examples"]):
            s["examples"] = keep
        # I al davant, les que escriuen el so amb la seva lletra. El pas que ensenya que la ɛ
        # s'escriu «ɛ» obria amb «shba3», «i3rQ», «A3wni»: totes porten el so, però cap no
        # l'escriu com la lliçó diu que s'escriu. No se'n treu cap —el text és de qui el va
        # escriure— però la primera que es llegeix és la que ensenya la lletra.
        s["examples"] = sorted(s["examples"],
                               key=lambda e: not written_with_the_letter(e.get("shi") or "", sounds))
    return lesson


#: Les lletres amazigues que no es poden confondre amb cap lletra del català: una «ṭ» soltada
#: dins d'un títol és sempre la lletra, mentre que una «x» o una «q» podrien ser d'una paraula
#: catalana i només s'anoten si van citades.
_LLETRES_SOLES = ("ṭ", "ḍ", "ṣ", "ẓ", "ṛ", "ḥ", "ɣ", "ɛ", "š", "ž")

#: Les vocals que la unitat dels sons ensenya.
VOCALS = ("a", "i", "u")


def _tifinag_de(lletra: str) -> str:
    """La tifinag d'una lletra sola, o res si el transliterador no en treu cap."""
    try:
        import transliteration
        return (transliteration.to_forms(lletra)["tifinagh"] or "").strip()
    except Exception:
        return ""


def amb_lletres_als_titols(lesson):
    """Un títol que anomena una lletra amaziga en llatí l'ha de dir també en tifinag.

    «Consonants emfàtiques: ṭ, ḍ, ṣ, ẓ» citava quatre lletres i no en pintava cap (#366), i el
    títol és el lloc on més es mira de tota la secció. El text de l'explicació ja passava per
    `with_letters`; els títols no hi passaven, perquè es netegen amb `_clean_text`.

    S'arregla en servir, com les glosses i la tifinag dels exemples: una lliçó ja escrita no ha
    d'esperar que algú la reescrigui per dir les lletres que ensenya. Un títol que ja porta
    tifinag no es toca.
    """
    if not isinstance(lesson, dict):
        return lesson
    for s in lesson.get("steps") or []:
        if not isinstance(s, dict):
            continue
        t = s.get("title") or ""
        if not t or re.search(r"[ⴰ-⵿]", t):
            continue
        nou = with_letters(t)              # el que va citat: «'sh'» → «'sh ⵛ'»
        if nou == t:                       # i el que va en llista: «: ṭ, ḍ, ṣ, ẓ»
            for lletra in _LLETRES_SOLES:
                tif = _tifinag_de(lletra)
                if not tif:
                    continue
                nou = re.sub(r"(?<![^\W\d_])" + re.escape(lletra) + r"(?![^\W\d_])",
                             lletra + " " + tif, nou)
        if nou == t and re.search(r"vocals?", t, re.I):
            # Les vocals van sense cometes i amb lletres que el català també fa servir («i» hi
            # és una conjunció), així que només s'anota una llista neta darrere dels dos punts.
            cap, _, cua = t.rpartition(":")
            if cap and re.fullmatch(r"\s*[aiu](\s*,\s*[aiu])+\s*", cua):
                nou = cap + ":" + re.sub(r"[aiu]", lambda m: m.group(0) + " " + _tifinag_de(m.group(0)), cua)
        if nou != t:
            s["title"] = nou
    return lesson


def vocals_del_pas(title: str) -> tuple:
    """Quines vocals ensenya aquest pas, si en ensenya.

    Només es mira si el títol parla de vocals i les llista darrere dels dos punts: en un títol
    qualsevol, la «a» és una preposició i la «i» una conjunció, i les trobaríem a tot arreu."""
    t = re.sub(r"[ⴰ-⵿]+", " ", title or "")
    if not re.search(r"vocals?", t, re.I):
        return ()
    cua = t.rpartition(":")[2] if ":" in t else t
    return tuple(v for v in VOCALS
                 if re.search(r"(?<![^\W\d_])" + v + r"(?![^\W\d_])", cua, re.I))


def porta_vocal(shi: str, vocal: str) -> bool:
    return vocal in unicodedata.normalize("NFC", shi or "").lower()


def _una_de_cada_vocal(examples: List[dict], vocals) -> List[dict]:
    """Al davant, una paraula per vocal i les curtes primer.

    «Fixa't com apareixen en aquests exemples» demana que s'hi vegin: `imi` (boca) ho ensenya
    millor que una frase de set paraules on la i es perd."""
    tria, vistos = [], set()
    for v in vocals:
        quines = sorted((e for e in examples
                         if id(e) not in vistos and porta_vocal(e.get("shi") or "", v)),
                        key=lambda e: len(e.get("shi") or ""))
        if quines:
            tria.append(quines[0])
            vistos.add(id(quines[0]))
    return tria + [e for e in examples if id(e) not in vistos]


def written_with_the_letter(shi: str, sounds) -> bool:
    """Si la frase escriu aquests sons amb la seva lletra (ɛ, ɣ, š) i no de la manera ràpida
    (3, gh, sh). Vegeu #302: només el 8% de la biblioteca fa servir l'alfabet que el curs ensenya."""
    low = unicodedata.normalize("NFC", shi or "").lower()
    return any(so in low for so in sounds)


def _with_glosses(lesson, examples: List[dict]):
    """Put the library's CURRENT word-by-word readings AND Tifinagh into a kept lesson, matched by
    drill id, so una lectura que millora arriba al curs sense reescriure la lliçó.

    La tifinag va amb les glosses i per la mateixa raó. Quan es va arreglar el transliterador
    (#304) les lliçons ja escrites seguien servint la tifinag del dia que es van escriure: la
    unitat dels sons continuava ensenyant `sġix → ⵙⴳⵉⵅ`, amb una ⴳ, el dia després d'arreglar-ho.
    Una conversió que millora no ha d'esperar que algú reescrigui la lliçó."""
    if not isinstance(lesson, dict):
        return lesson
    have = {e["id"]: e for e in examples if e.get("id")}
    if not have:
        return lesson
    for s in lesson.get("steps") or []:
        if not isinstance(s, dict):
            continue
        shown = list(s.get("examples") or [])
        if isinstance(s.get("example"), dict):
            shown.append(s["example"])
        for e in shown:
            fresh = have.get(e.get("id"))
            if not fresh:
                continue
            if fresh.get("gloss"):
                e["gloss"] = fresh["gloss"]
            if fresh.get("tif"):
                e["tif"] = fresh["tif"]
    return lesson


def deep_first(db, slug: str, examples: List[dict]) -> List[dict]:
    """The pool as the «a fons» level should see it: the sentences the first lesson does NOT quote
    first, so the two levels teach the same point with different sentences."""
    from models import GrammarLesson
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    base = quoted_ids(_stored(row) or {}) if row is not None else set()
    if not base:
        return examples
    return [e for e in examples if e["id"] not in base] + [e for e in examples if e["id"] in base]


def get_lesson(db, slug: str, grammar_md: str, examples: List[dict], force: bool = False, unit_ids: Optional[set] = None,
               session_factory=None, tables: Optional[List[dict]] = None, deep: bool = False) -> dict:
    """The unit's lesson from the `grammar_lessons` table — or, with `deep`, its «a fons» level. A
    page NEVER waits for Gemini: when the lesson is missing or outdated and a session factory is
    given, the writing starts on a thread and the kept lesson (or a short placeholder) comes back at
    once, marked so the page can ask again."""
    from models import GrammarLesson
    try:
        notes = notes_for(db, slug, {e["id"]: (e.get("shi") or "", e.get("ca") or "") for e in examples})
    except Exception:  # a database that has not met the notes table yet must still serve the course
        notes = {}

    def dressed(lesson):
        return amb_lletres_als_titols(
            with_the_sound_it_teaches(_with_notes(_with_glosses(lesson, examples), notes), slug))

    if deep:
        examples = deep_first(db, slug, examples)
    row = db.query(GrammarLesson).filter(GrammarLesson.id == _row_id(slug, deep)).first()
    lesson = None if force else _current(row, unit_ids, deep=deep)
    if lesson is not None:
        return dressed(lesson)
    if session_factory is not None:
        _write_in_background(session_factory, slug, grammar_md, examples, unit_ids, tables, deep=deep)
        kept = _stored(row)
        return dressed({**kept, "stale": True, "writing": True}) if kept else dressed(_placeholder(slug, examples, deep))
    with _explain_lock:  # a script that asked for the lesson itself waits for it
        row = db.query(GrammarLesson).filter(GrammarLesson.id == _row_id(slug, deep)).first()
        lesson = None if force else _current(row, unit_ids, deep=deep)
        if lesson is not None:
            return dressed(lesson)
        lesson = write_lesson(slug, grammar_md, examples, sheet=sheet_for(db, slug, grammar_md),
                              tables=tables, notes=notes, deep=deep)
        if unit_ids is not None:
            lesson["unit_size"] = len(unit_ids)
        _store_lesson(db, slug, lesson, deep=deep)
        return dressed(lesson)
