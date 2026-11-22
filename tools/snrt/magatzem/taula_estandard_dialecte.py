"""La taula estàndard ↔ dialecte, treta de les 26 hores de Tamazight TV.

La hipòtesi d'en Pablo (17-11-2026): els subtítols s'escriuen en la norma de l'IRCAM i els
actors parlen dialecte; si la diferència és sistemàtica, comparant-les surten els patrons.

Fins avui no es podia comprovar perquè no teníem el que sent el model sobre el mateix so. Ara
sí: per a cada rèplica hi ha el text de la pantalla (l'ull) i el que sona (l'orella), llegits
per dues màquines que no saben res l'una de l'altra.

Com es treu una correspondència, i per què així:

- Només paraules que l'orella sent amb **confiança alta**: si dubta, la diferència pot ser seva.
- Només quan a la mateixa rèplica hi ha una paraula de l'ull que li **fa de parella** per posició
  (la més propera que no s'hagi aparellat ja), i les dues NO coincideixen.
- I es demana que la parella **surti en més d'un capítol**: una vegada és una casualitat o un
  error; repetida en capítols diferents, amb veus diferents, és un patró.

El que NO fa: dir qui té raó. La norma no és «el bo» ni la parla «el dolent»: són dues maneres
d'escriure la mateixa llengua, i la taula serveix per entendre-les totes dues.
"""
import io
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

MAG = Path(r"E:\tamazight\_magatzem")
ORIGEN = MAG / "ocurrencies_26.jsonl"
DESTI = MAG / "estandard_dialecte.jsonl"
CONF_MIN = 0.9
MIN_CAPITOLS = 2

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}


def a_llati(t, de_tifinag):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c) if de_tifinag else LLATI.get(c, c)
        if c and (c.isalpha() or c in "εġḍḥṣṭẓšḫ"):
            fora.append(c)
    return "".join(fora)


files = [json.loads(l) for l in io.open(ORIGEN, encoding="utf-8") if l.strip()]
print(f"ocurrències: {len(files)}")

parelles = defaultdict(lambda: {"capitols": set(), "n": 0, "exemples": []})
for r in files:
    if r["grau"] != "B" or r["conf"] < CONF_MIN or not r.get("norma"):
        continue
    orella = a_llati(r["sentit"], False)
    ull = a_llati(r["norma"], True)
    if not orella or not ull or orella == ull:
        continue
    #: una lletra sola no diu res: «n» contra «d» pot ser qualsevol cosa
    if len(orella) < 2 or len(ull) < 2:
        continue
    k = (ull, orella)
    p = parelles[k]
    p["capitols"].add(r["capitol"])
    p["n"] += 1
    if len(p["exemples"]) < 2 and r.get("catala"):
        p["exemples"].append(r["catala"][:60])

bones = {k: v for k, v in parelles.items() if len(v["capitols"]) >= MIN_CAPITOLS}
print(f"parelles diferents: {len(parelles)}   en {MIN_CAPITOLS}+ capítols: {len(bones)}")

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for (ull, orella), v in sorted(bones.items(), key=lambda t: -t[1]["n"]):
        f.write(json.dumps({"norma": ull, "parla": orella, "vegades": v["n"],
                            "capitols": len(v["capitols"]), "exemples": v["exemples"]},
                           ensure_ascii=False) + "\n")
print(f"desat a {DESTI}\n")

print(f"{'la norma escriu':>18}  {'es diu':<18} vegades  capítols")
for (ull, orella), v in sorted(bones.items(), key=lambda t: -t[1]["n"])[:25]:
    print(f"{ull:>18}  {orella:<18} {v['n']:5d}   {len(v['capitols']):3d}")

#: quantes de les diferències són d'una sola lletra (ortografia) i quantes són una altra paraula
ortografia = sum(v["n"] for (u, o), v in bones.items()
                 if abs(len(u) - len(o)) <= 1 and sum(a != b for a, b in zip(u, o)) <= 1)
total = sum(v["n"] for v in bones.values())
print(f"\nde {total} ocurrències amb parella repetida:")
print(f"   {ortografia} ({100*ortografia/max(1,total):.0f}%) són d'una lletra: ortografia")
print(f"   {total-ortografia} ({100*(total-ortografia)/max(1,total):.0f}%) són una altra paraula")
