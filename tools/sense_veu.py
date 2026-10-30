"""Quines línies amazigues de l'app es mostren sense veu (#504).

    python tools/sense_veu.py [API]

Recorre els capítols del Mètode tal com els serveix producció (que ja hi enganxa la veu de la
biblioteca quan una frase gravada diu exactament la línia) i llista, per capítol, les línies que
continuen mudes: són les que encara cal gravar o demanar.
"""
import json
import sys
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "https://tachelhit-drills-api.onrender.com"


def get(path):
    with urllib.request.urlopen(API + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def linies(c):
    for t in ((c.get("dialogue") or {}).get("turns") or []):
        yield t
    for s in c.get("sections") or []:
        yield from (s.get("examples") or [])
        for col in s.get("columns") or []:
            yield from (col.get("rows") or [])
    yield from (c.get("vocabulary") or [])


tot = muts = 0
for cap in get("/method/")["chapters"]:
    slug = cap.get("slug") if isinstance(cap, dict) else cap
    c = (get(f"/method/{slug}") or {}).get("content") or {}
    ls = [l for l in linies(c) if isinstance(l, dict) and (l.get("shi") or "").strip()]
    mudes = [l["shi"] for l in ls if not (l.get("audio_url") or l.get("cd") or l.get("heard"))]
    tot, muts = tot + len(ls), muts + len(mudes)
    print(f"{slug}: {len(ls) - len(mudes)}/{len(ls)} sonen")
    for m in mudes:
        print("   ·", m)
print(f"total: {tot - muts} de {tot} línies sonen")
