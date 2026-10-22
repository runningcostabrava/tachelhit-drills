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
SPACE = os.environ.get("ASR_SPACE", "Tamazight-NLP/ASR")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tachelhit-ops"}


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=60, help="how many recordings to listen to")
    ap.add_argument("--dry", action="store_true", help="pick them, call nothing")
    ap.add_argument("--seed", type=int, default=22)
    args = ap.parse_args()

    import requests
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

    from gradio_client import Client, handle_file
    client = Client(SPACE)
    out = []
    for i, d in enumerate(picked, 1):
        reference = (transliteration.to_forms(d["text_tachelhit"])["tifinagh"] or "").strip()
        if not reference:
            continue
        audio = d["audio_url"]
        local = os.path.join(os.environ.get("TEMP", "/tmp"), f"asr_{d['id']}.mp3")
        try:
            with open(local, "wb") as f:
                f.write(requests.get(audio, headers=HEADERS, timeout=120).content)
        except Exception as e:
            print(f"  {d['id']}: no audio ({str(e)[:50]})")
            continue
        row = {"id": d["id"], "origin": origin_of(d), "said": d["text_tachelhit"],
               "reference": reference, "models": {}}
        for endpoint in ("/predict", "/predict_1"):
            try:
                heard = client.predict(audio_path=handle_file(local), api_name=endpoint)
                heard = heard if isinstance(heard, str) else json.dumps(heard, ensure_ascii=False)
                row["models"][endpoint] = {"heard": heard.strip(), **rates(reference, heard.strip())}
            except Exception as e:
                row["models"][endpoint] = {"heard": "", "error": str(e)[:80], "cer": 1.0, "wer": 1.0}
        out.append(row)
        best = min((m.get("cer", 1.0) for m in row["models"].values()), default=1.0)
        print(f"  {i:3d}/{len(picked)} {d['id']:6d} [{row['origin']:11s}] CER {best:.2f}", flush=True)
        try:
            os.remove(local)
        except OSError:
            pass
        time.sleep(0.4)

    # the report
    stamp = date.today().isoformat()
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in out:
        for endpoint, m in r["models"].items():
            per[endpoint][r["origin"]].append(m.get("cer", 1.0))
            per[endpoint]["tot"].append(m.get("cer", 1.0))
    lines = [f"# Què val el nostre transcriptor ({stamp})", "",
             f"Space `{SPACE}` · {len(out)} gravacions nostres · comparat en tifinag "
             "(el text del parlant hi passa amb el transliterador de l'app).", "",
             "| model | origen | gravacions | CER mitjà |", "|---|---|---|---|"]
    for endpoint, origins in per.items():
        for origin, vals in sorted(origins.items()):
            lines.append(f"| `{endpoint}` | {origin} | {len(vals)} | {sum(vals)/max(1,len(vals)):.2f} |")
    lines += ["", "CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per fer servir el "
                  "transcriptor per decidir si una veu diu el que diu un text, caldria estar "
                  "clarament per sota de 0,5.", ""]
    md = os.path.join(ROOT, "docs", f"ASR_EVAL_{stamp}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(md.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n".join(lines[3:]))
    print(f"\nescrit a {md}")


if __name__ == "__main__":
    main()
