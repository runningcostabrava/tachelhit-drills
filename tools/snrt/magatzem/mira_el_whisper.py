"""El Whisper rifeny contra el subtitol i contra les altres dues orelles.

Es el testimoni independent: arquitectura, base, entrenament i ortografia diferents de les dues
orelles d'MMS. Si tambe sent el mateix que elles i tampoc no casa amb el subtitol, l'objeccio del
parentiu entre models queda tancada.

Escriu en **arab de xat** (9=q, 7=ḥ, 3=ε, ch=š, gh=ġ, kh=ḫ), que l'esquelet no sap llegir tal
com ve: primer es normalitza. La normalitzacio es nomes ortografica i no toca cap consonant --
converteix una manera d'escriure el mateix so en l'altra.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SORTIDA = MAG / "prova_adaptadors" / "sortida_completa"

#: arab de xat -> les nostres lletres. Els digrafs primer, que si no `ch` es llegiria c+h.
DIGRAFS = [("ch", "š"), ("sh", "š"), ("kh", "ḫ"), ("gh", "ġ"), ("dh", "d"), ("th", "t")]
XIFRES = {"9": "q", "7": "ḥ", "3": "ε", "5": "ḫ", "2": "", "8": "ġ", "6": "ṭ", "4": ""}


def de_xat(t):
    t = (t or "").lower()
    for a, b in DIGRAFS:
        t = t.replace(a, b)
    t = "".join(XIFRES.get(c, c) for c in t)
    return re.sub(r"\s+", " ", t).strip()


var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
titols = {r["capitol"]: r["titol"]
          for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

ull = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        ull[x["id"]] = x.get("tifinag") or ""


def llegeix(nom, xat=False):
    d = {}
    p = SORTIDA / f"sentit_{nom}.jsonl"
    if not p.exists():
        return d
    for l in io.open(p, encoding="utf-8"):
        if l.strip():
            x = json.loads(l)
            t = (x.get("sentit") or "").strip()
            d[x["id"]] = de_xat(t) if xat else t
    return d


def casa(a, b):
    ea, eb = esquelet(a), esquelet(b)
    if not ea or not eb:
        return None
    return (lev(ea, eb) / max(len(ea), len(eb))) <= .35


wh = llegeix("whisper", xat=True)
if not wh:
    raise SystemExit("encara no hi ha sentit_whisper.jsonl")
shi, rif = llegeix("shi"), llegeix("rif")

print(f"talls del Whisper: {len(wh)}")
grups = {}
for i in wh:
    if not ull.get(i) or i not in shi or i not in rif:
        continue
    v = var.get(i.split(":")[0], "?")
    g = grups.setdefault(v, {"n": 0, "wh_ull": 0, "sh_ull": 0, "wh_sh": 0, "wh_rf": 0})
    a, b, c, d = (casa(wh[i], ull[i]), casa(shi[i], ull[i]),
                  casa(wh[i], shi[i]), casa(wh[i], rif[i]))
    if None in (a, b, c, d):
        continue
    g["n"] += 1
    g["wh_ull"] += a
    g["sh_ull"] += b
    g["wh_sh"] += c
    g["wh_rf"] += d

print(f"\n{'varietat':<24}{'wh~ull':>8}{'shi~ull':>9}{'wh~shi':>8}{'wh~rif':>8}{'talls':>7}")
for v, g in sorted(grups.items()):
    n = max(1, g["n"])
    print(f"{v[:22]:<24}{100*g['wh_ull']/n:7.1f}%{100*g['sh_ull']/n:8.1f}%"
          f"{100*g['wh_sh']/n:7.1f}%{100*g['wh_rf']/n:7.1f}%{g['n']:7d}")

print("\nsi al tarifit `wh~ull` es tan baix com `shi~ull` pero `wh~shi` i `wh~rif` son alts,")
print("tres orelles de bases diferents senten el mateix i el subtitol es el que queda fora.")
