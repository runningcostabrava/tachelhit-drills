"""Quines lletres confon l'OCR, deduït del que l'orella sent amb molta seguretat.

Sense veritat humana no se sabia on falla el lector en una tipografia nova. Però quan el
transcriptor sent una paraula amb confiança ≥0,95 i l'ull n'ha llegit una de PARESCUDA (mateixa
llargada d'esquelet, poca distància), la diferència entre les dues és, molt probablement, un
error de lectura i no una altra paraula. Alineant-les lletra a lletra surt la llista de
confusions d'aquesta tipografia.

Què NO és: una veritat. L'orella també s'equivoca, i una confusió pot ser una diferència real
entre el que s'escriu i el que es diu. Per això només es mira la part alta de la confiança, es
demana que les dues formes s'assemblin molt, i el resultat es diu «candidates», no «errors».

Serveix per a dues coses: saber què arreglar al lector, i saber de què desconfiar mentrestant.
"""
import io
import json
import unicodedata
from collections import Counter
from pathlib import Path

ORIGEN = Path(r"E:\tamazight\_magatzem\ocurrencies.jsonl")
CONF_MIN, DIST_MAX = 0.95, 0.5

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
#: per dir-ho amb el signe que es veu a la pantalla i no amb la seva transcripció
DE_LLATI = {}
for t, l in TIF.items():
    DE_LLATI.setdefault(l, t)
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}


def normal(t, de_tifinag):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c) if de_tifinag else LLATI.get(c, c)
        if c and c.isalpha():
            fora.append(c)
    return "".join(fora)


def alinea(a, b):
    """Camí d'edició entre dues cadenes: (lletra de l'orella, lletra de l'ull)."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    parelles, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            parelles.append((a[i - 1], b[j - 1])); i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            parelles.append((a[i - 1], "—")); i -= 1
        else:
            parelles.append(("—", b[j - 1])); j -= 1
    return parelles[::-1]


files = [json.loads(l) for l in io.open(ORIGEN, encoding="utf-8") if l.strip()]
tria = [r for r in files if r["conf"] >= CONF_MIN and r.get("norma")
        and r["dist"] <= DIST_MAX and r["grau"] in ("A", "B")]
print(f"ocurrències mirades: {len(tria)} (confiança ≥{CONF_MIN}, distància ≤{DIST_MAX})")

conf = Counter()
for r in tria:
    orella = normal(r["sentit"], False)
    ull = normal(r["norma"], True)
    for a, b in alinea(orella, ull):
        if a != b:
            conf[(b, a)] += 1   # (el que ha llegit l'ull, el que ha sentit l'orella)

print(f"\nconfusions candidates (l'ull llegeix → l'orella sent), les 18 més repetides:\n")
print(f"{'ull':>6}  {'orella':>8}   vegades")
for (ull, orella), n in conf.most_common(18):
    su = DE_LLATI.get(ull, ull) if ull != "—" else "(res)"
    so = DE_LLATI.get(orella, orella) if orella != "—" else "(res)"
    print(f"{su:>6}  {so:>8}   {n:5d}    [{ull} → {orella}]")

total = sum(conf.values())
print(f"\ntotal de diferències: {total}")
cau = sum(n for (u, _), n in conf.items() if u == "—")
sobra = sum(n for (_, o), n in conf.items() if o == "—")
print(f"   l'ull veu una lletra que l'orella no sent: {sobra}")
print(f"   l'orella sent una lletra que l'ull no veu: {cau}")
