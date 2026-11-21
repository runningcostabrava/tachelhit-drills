"""El magatzem per PARAULA d'un capítol: una fila per cada vegada que s'ha sentit una paraula.

La línia és massa gruixuda. Una frase barreja trossos segurs i impossibles, i jutjada sencera
els iguala pel pitjor: de les 1.249 rèpliques només 134 passen senceres, i mentrestant dins de
les altres hi ha paraules perfectament sentides que es llencen amb la frase.

Cada ocurrència porta d'on surt (fitxer de so i segon) i QUIN MODEL la va sentir, perquè es
pugui tornar a mirar amb un model millor d'aquí a sis mesos. Només creix: una passada nova
afegeix files, no en reescriu cap.

Els quatre graus (E:\\tamazight\\_magatzem\\METODE.md):

  A  l'orella n'està segura i l'ull la confirma   -> es pot fer servir
  B  l'orella n'està segura i l'ull diu una altra cosa -> candidata a estàndard <-> dialecte,
     que és el material que volem, NO un error
  C  l'orella dubta, però la mateixa forma es repeteix al capítol -> la repetició la rescata
  D  ni l'una ni l'altra -> es cataloga i s'espera

No escriu res a producció ni al visor.
"""
import io
import json
import unicodedata
from collections import Counter
from pathlib import Path

SENTIT = Path(r"E:\tamazight\_sentit\sortida\sentit.jsonl")
CAP = Path(r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay\tadfi_goughelt")
DESTI = Path(r"E:\tamazight\_magatzem\ocurrencies.jsonl")
CAPITOL = "tadfi_goughelt"
MODEL = "mms-1b-all+shi+adaptador_inici (19-11-2026)"
SEGUR = 0.85

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiou")


def esquelet(t):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c, LLATI.get(c, c))
        if c.isalpha() and c not in VOCALS:
            fora.append(c)
    return "".join(fora)


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def prop(a, b):
    """Com de lluny són dos esquelets, de 0 (iguals) a 1. Amb un de buit, lluny del tot."""
    if not a or not b:
        return 1.0
    return lev(a, b) / max(len(a), len(b))


subs = {x["id"]: x for x in (json.loads(l) for l in io.open(CAP / "subtitols.jsonl", encoding="utf-8") if l.strip())}
lectures = [json.loads(l) for l in io.open(SENTIT, encoding="utf-8") if l.strip()]

#: primer tot el capítol, per saber quines formes es repeteixen: el grau C depèn del conjunt i
#: no es pot decidir mirant una ocurrència sola
repeticions = Counter()
for x in lectures:
    for p in x.get("paraules", []):
        e = esquelet(p["p"])
        if len(e) >= 2:
            repeticions[e] += 1

files = []
for x in lectures:
    sub = subs.get(x["id"], {})
    ull = [w for w in (sub.get("tifinag") or "").split() if w.strip()]
    ull_esq = [esquelet(w) for w in ull]
    for p in x.get("paraules", []):
        e = esquelet(p["p"])
        #: la paraula de l'ull que més s'assembla a la sentida, dins de la MATEIXA rèplica
        millor, dist = None, 1.0
        for w, we in zip(ull, ull_esq):
            d = prop(e, we)
            if d < dist:
                millor, dist = w, d
        confirmada = millor is not None and dist <= .35
        if p["c"] >= SEGUR:
            grau = "A" if confirmada else "B"
        elif len(e) >= 2 and repeticions[e] >= 3:
            grau = "C"
        else:
            grau = "D"
        files.append({"capitol": CAPITOL, "id": x["id"], "sentit": p["p"], "esquelet": e,
                      "conf": p["c"], "grau": grau, "norma": millor, "dist": round(dist, 3),
                      "repeticions": repeticions[e], "so": sub.get("tall"),
                      "de": sub.get("tall_de"), "a": sub.get("tall_a"),
                      "catala_de_arab": (sub.get("catala_de_arab") or "").strip() or None,
                      "model": MODEL})

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for r in files:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

g = Counter(r["grau"] for r in files)
print(f"ocurrències de paraula: {len(files)}")
for k in "ABCD":
    print(f"   grau {k}: {g[k]:5d}  {100*g[k]/max(1,len(files)):5.1f}%")
print(f"\nformes diferents: {len(repeticions)}")
print(f"desat a {DESTI}")

print("\ngrau A (sentida segura i confirmada per l'ull):")
for r in [r for r in files if r["grau"] == "A"][:6]:
    print(f"   {r['sentit']:16s} conf {r['conf']}  ull: {r['norma']}")
print("\ngrau B (segura, però l'ull diu una altra cosa) — candidates estàndard ↔ dialecte:")
for r in sorted([r for r in files if r["grau"] == "B"], key=lambda r: -r["conf"])[:6]:
    print(f"   {r['sentit']:16s} conf {r['conf']}  ull: {r['norma']}  (dist {r['dist']})")
