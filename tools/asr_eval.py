"""What is our transcriber actually worth? (issue #204)

The Space at Tamazight-NLP/ASR is used to decide whether a voice says what a text says. Until now
nobody had measured it, so a bad score meant nothing: the fault could be the audio, the text, or
the transcriber itself.

This measures it against the best material there is for the purpose — OUR OWN recordings. Every
drill with a human voice carries the sentence as its speaker writes it, from a named person in a
named place. Public corpora are mostly Standard Moroccan read aloud; what we need to know is
whether the Space hears Aït Mraw and Beni Mellal.

The two sides are compared in Tifinagh: the Space writes Tifinagh, and the app's own
transliterator turns our Latin into it, so no comparison depends on how a speaker chose to spell.

    python tools/asr_eval.py --sample 60            # measure, write the report
    python tools/asr_eval.py --sample 20 --dry      # pick the clips, call nothing

Writes docs/ASR_EVAL_<date>.md and a JSON beside it.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("LEXICON_WARMUP", "0")

API = os.environ.get("TACHELHIT_API", "https://tachelhit-drills-api.onrender.com")
# The Space the APP actually calls (backend/main.py ASR_SPACE_DEFAULT): our own Docker Space,
# NeMo FastConformer, with /transcribe and /align. Measuring anything else measures a
# transcriber nobody uses -- which is exactly what happened on 2026-10-22.
SPACE = os.environ.get("ASR_SPACE", "https://josepabloucr-huggingface-asr-space.hf.space")
HF_TOKEN = os.environ.get("HUGGINGFACE_API_KEY", "")
if not HF_TOKEN:
    try:
        for _line in open(os.path.join(ROOT, "backend", ".env"), encoding="utf-8"):
            if _line.startswith("HUGGINGFACE_API_KEY="):
                HF_TOKEN = _line.split("=", 1)[1].strip()
                break
    except OSError:
        pass
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tachelhit-ops"}


# Each source gets its own file name. This used to be "CV if Common Voice else NOSTRA", which
# meant the third corpus quietly overwrote the library's own report.
SLUG = {
    "la nostra biblioteca": "NOSTRA",
    "Common Voice (Mozilla Data Collective)": "CV",
    "Tamazight Open Speech Dataset": "TOSD",
}

# A measurement names whose recordings it used. Keyed by the `source` passed to measure().
CREDIT = {
    "Common Voice (Mozilla Data Collective)": [
        "## D'on surten les gravacions",
        "",
        "Mozilla Common Voice, *Scripted Speech* 27.0 — Tamazight (`zgh`), "
        "`cv-corpus-27.0-2026-09-11`, baixat del Mozilla Data Collective. Llicència **CC0**: no "
        "exigeix atribució, però els clips els van gravar i validar persones de la comunitat "
        "amaziga i és just dir-ho. En baixar-los es va acceptar no intentar esbrinar qui parla.",
    ],
    "Tamazight Open Speech Dataset": [
        "## D'on surten les gravacions",
        "",
        "**Tamazight Open Speech Dataset**, publicat per **Tamazight NLP** al Mozilla Data "
        "Collective, llicència **Apache-2.0**. 1.801 gravacions, 1,44 h, amb la frase en tifinag. "
        "No entren a la biblioteca: no diuen qui parla ni d'on és, i no porten cap significat en "
        "català. Aquí només fan de jutge.",
    ],
    "la nostra biblioteca": [
        "## D'on surten les gravacions",
        "",
        "De la nostra biblioteca: Halima i Driss (Aït Mraw) i els reculls de Beni Mellal, que han "
        "dit aquestes frases per al projecte. El text de referència és el seu, passat a tifinag "
        "amb el transliterador de l'app.",
    ],
}


def levenshtein(a: list, b: list) -> int:
    """Edits to turn one sequence into the other. Characters or words, same arithmetic."""
    if not a:
        return len(b)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def rates(reference: str, heard: str) -> dict:
    """How wrong the machine was, per character and per word. 0 is perfect, 1 is everything."""
    ref_c, got_c = list(reference.replace(" ", "")), list(heard.replace(" ", ""))
    ref_w, got_w = reference.split(), heard.split()
    return {
        "cer": round(levenshtein(ref_c, got_c) / max(1, len(ref_c)), 3),
        "wer": round(levenshtein(ref_w, got_w) / max(1, len(ref_w)), 3),
    }


def common_voice(folder: str, sample: int, seed: int) -> list:
    """A Common Voice corpus as this tool wants it: the clip, and the sentence as written.

    Nothing has to be transliterated here — Common Voice writes Tifinagh and so does the Space —
    which removes the one weak point of measuring against our own library, where the reference
    has to be converted from the speaker's own spelling first.
    """
    import csv
    valid = os.path.join(folder, "validated.tsv")
    rows = list(csv.DictReader(open(valid, encoding="utf-8"), delimiter="	"))
    buckets: dict = collections.defaultdict(list)
    for r in rows:
        if not (r.get("sentence") or "").strip():
            continue
        name = (r.get("variant") or "").strip()
        label = ("Tachelhit" if "Tachelhit" in name else
                 "Atles central" if "Central" in name else "sense varietat")
        buckets[label].append(r)
    rnd = random.Random(seed)
    share = max(1, sample // max(1, len(buckets)))
    picked = []
    for label, items in buckets.items():
        rnd.shuffle(items)
        for r in items[:share]:
            picked.append({"id": r.get("path"), "origin": label,
                           "said": r["sentence"], "reference": r["sentence"].strip(),
                           "file": os.path.join(folder, "clips", r["path"])})
    print(f"{len(rows)} validades · "
          + " · ".join(f"{k}: {min(len(v), share)} de {len(v)}" for k, v in buckets.items()))
    rnd.shuffle(picked)
    return picked


def tamazight_open_speech(folder: str, sample: int, seed: int) -> list:
    """The Tamazight Open Speech Dataset as this tool wants it.

    1.801 clips, 1,44 h, each with its sentence in Tifinagh -- so, like Common Voice, nothing has
    to be transliterated. Unlike Common Voice it says nothing about who speaks or from where, so
    there is no variety to break the sample down by: the only split it offers is its own two
    subsets, and those are what the report shows.
    """
    rows = [json.loads(line) for line in open(os.path.join(folder, "metadata.jsonl"), encoding="utf-8")
            if line.strip()]
    buckets: dict = collections.defaultdict(list)
    for r in rows:
        if (r.get("text") or "").strip():
            buckets[r.get("subset") or "sense grup"].append(r)
    rnd = random.Random(seed)
    share = max(1, sample // max(1, len(buckets)))
    picked = []
    for label, items in buckets.items():
        rnd.shuffle(items)
        for r in items[:share]:
            picked.append({"id": os.path.basename(r["audio_filepath"]), "origin": label,
                           "said": r["text"], "reference": r["text"].strip(),
                           "file": os.path.join(folder, r["audio_filepath"])})
    print(f"{len(rows)} gravacions · "
          + " · ".join(f"{k}: {min(len(v), share)} de {len(v)}" for k, v in buckets.items()))
    rnd.shuffle(picked)
    return picked


def measure(picked: list, source: str = "la nostra biblioteca") -> None:
    """Ask the Space to transcribe each clip, and say how wrong it was.

    `picked` holds dicts with: id, origin, said, reference (already Tifinagh), and either `file`
    (a clip on disk) or `audio` (a URL to fetch). Only /predict is called: /predict and
    /predict_1 returned identical error rates on every source measured on 2026-10-22, so the
    second one buys nothing but time.
    """
    import requests
    # A URL means our own Docker Space (FastAPI: POST /transcribe). An "owner/name" means a
    # Gradio Space, which is how the public ones are reached.
    rest = SPACE.startswith("http")
    client = None
    if not rest:
        from gradio_client import Client, handle_file
        client = Client(SPACE)
    auth = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    out = []
    for i, p in enumerate(picked, 1):
        local = p.get("file")
        if not local:
            local = os.path.join(os.environ.get("TEMP", "/tmp"), f"asr_{p['id']}.mp3")
            try:
                with open(local, "wb") as f:
                    f.write(requests.get(p["audio"], headers=HEADERS, timeout=120).content)
            except Exception as e:
                print(f"  {p['id']}: no audio ({str(e)[:50]})")
                continue
        if not os.path.exists(local):
            print(f"  {p['id']}: the clip is not where the index says")
            continue
        row = {"id": p["id"], "origin": p["origin"], "said": p["said"],
               "reference": p["reference"], "models": {}}
        try:
            if rest:
                with open(local, "rb") as fh:
                    r = requests.post(f"{SPACE}/transcribe", headers=auth,
                                      files={"audio_file": (os.path.basename(local), fh, "audio/wav")},
                                      timeout=600)
                r.raise_for_status()
                heard = (r.json() or {}).get("text") or ""
            else:
                heard = client.predict(audio_path=handle_file(local), api_name="/predict")
                heard = heard if isinstance(heard, str) else json.dumps(heard, ensure_ascii=False)
            heard = heard.strip()
            row["models"]["/predict"] = {"heard": heard, **rates(p["reference"], heard)}
        except Exception as e:
            row["models"]["/predict"] = {"heard": "", "error": str(e)[:80], "cer": 1.0, "wer": 1.0}
        out.append(row)
        print(f"  {i:3d}/{len(picked)} [{p['origin']:14s}] CER {row['models']['/predict']['cer']:.2f}", flush=True)
        if not p.get("file"):
            try:
                os.remove(local)
            except OSError:
                pass
        time.sleep(0.4)

    stamp = date.today().isoformat()
    per = collections.defaultdict(list)
    wer = collections.defaultdict(list)
    for r in out:
        m = r["models"]["/predict"]
        per[r["origin"]].append(m.get("cer", 1.0))
        wer[r["origin"]].append(m.get("wer", 1.0))
        per["tot"].append(m.get("cer", 1.0))
        wer["tot"].append(m.get("wer", 1.0))
    lines = [f"# Què val el nostre transcriptor ({stamp})", "",
             f"Space `{SPACE}` · font: **{source}** · {len(out)} gravacions.", "",
             "| origen | gravacions | CER mitjà | WER mitjà |", "|---|---|---|---|"]
    for origin in sorted(per):
        lines.append(f"| {origin} | {len(per[origin])} | {sum(per[origin])/max(1,len(per[origin])):.2f} "
                     f"| {sum(wer[origin])/max(1,len(wer[origin])):.2f} |")
    lines += ["", "CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per decidir si una "
                  "veu diu el que diu un text caldria estar clarament per sota de 0,5.", ""]
    lines += CREDIT.get(source, []) + ["", "Totes les fonts del projecte: [docs/CREDITS.md](CREDITS.md).", ""]
    slug = SLUG.get(source, "ALTRES")
    md = os.path.join(ROOT, "docs", f"ASR_EVAL_{slug}_{stamp}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(md.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n".join(lines[3:]))
    print(f"\nescrit a {md}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", help="a Common Voice corpus folder (the one holding validated.tsv)")
    ap.add_argument("--tosd", help="a Tamazight Open Speech folder (the one holding metadata.jsonl)")
    ap.add_argument("--sample", type=int, default=60, help="how many recordings to listen to")
    ap.add_argument("--dry", action="store_true", help="pick them, call nothing")
    ap.add_argument("--seed", type=int, default=22)
    args = ap.parse_args()

    import requests

    if args.cv:
        picked = common_voice(args.cv, args.sample, args.seed)
        if args.dry:
            for p in picked[:10]:
                print(f"  {p['origin']:14s} {p['said'][:46]}")
            return
        measure(picked, source="Common Voice (Mozilla Data Collective)")
        return

    if args.tosd:
        picked = tamazight_open_speech(args.tosd, args.sample, args.seed)
        if args.dry:
            for p in picked[:10]:
                print(f"  {p['origin']:14s} {p['said'][:46]}")
            return
        measure(picked, source="Tamazight Open Speech Dataset")
        return

    import grammar
    import transliteration

    rows = requests.get(f"{API}/drills/", headers=HEADERS, timeout=300).json()
    # A fair test: a human voice, a sentence worth transcribing, and nothing synthetic.
    pool = [d for d in rows
            if (d.get("audio_url") or "").strip()
            and (d.get("text_tachelhit") or "").strip()
            and grammar.kind(d["text_tachelhit"]) == "sentence"]
    by_origin = collections.defaultdict(list)
    for d in pool:
        by_origin[grammar.origin(type("R", (), d)) if False else (d.get("tag") or "")].append(d)

    def origin_of(d) -> str:
        tag = (d.get("tag") or "").lower()
        if "benimellal" in tag:
            return "Beni Mellal"
        if "mraw" in tag or (d.get("author") or "") in ("Halima", "Driss"):
            return "Aït Mraw"
        return "altres"

    # Fair shares, not a raffle: two thirds of the library is one deck, so a random draw would
    # measure that deck and say little about our own speakers.
    rnd = random.Random(args.seed)
    buckets: dict = collections.defaultdict(list)
    for d in pool:
        buckets[origin_of(d)].append(d)
    share = max(1, args.sample // max(1, len(buckets)))
    picked = []
    for origin, items in buckets.items():
        rnd.shuffle(items)
        picked.extend(items[:share])
    rnd.shuffle(picked)
    print(f"{len(pool)} recordings to choose from · listening to {len(picked)}"
          f" ({', '.join(f'{k}: {min(len(v), share)}' for k, v in buckets.items())})")

    if args.dry:
        for d in picked[:10]:
            print(f"  {d['id']:6d} [{origin_of(d):11s}] {d['text_tachelhit'][:48]}")
        return

    measure([{"id": d["id"], "origin": origin_of(d), "said": d["text_tachelhit"],
               "reference": (transliteration.to_forms(d["text_tachelhit"])["tifinagh"] or "").strip(),
               "audio": d["audio_url"]}
              for d in picked
              if (transliteration.to_forms(d["text_tachelhit"])["tifinagh"] or "").strip()])


if __name__ == "__main__":
    main()
