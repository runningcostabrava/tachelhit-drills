"""Capítol a capítol, quedar-se amb el text que més s'acordi amb l'orella.

No hi ha un guanyador universal i val més dir-ho que triar per fe:

  - La fàbrica llegeix **diversos fotogrames per rèplica** i en treu consens, però ho va fer
    sobre vídeo de **720p**. Guanya quan la imatge és bona: al «bueyrhjvjyaleo» dona 37,3 % i la
    meva relectura 34,1 %.
  - La relectura d'ara treu **un sol fotograma** per rèplica però del vídeo de **1080p**, i amb
    el desempat topològic. Guanya quan la imatge és dolenta: al «caxyzjdttlgi» la fàbrica dona
    **0,0 %** i la relectura **14,8 %**.

O sigui que la tria s'ha de fer per capítol i amb el número al davant. L'àrbitre és el mateix de
sempre: quin dels dos textos s'assembla més al que sent el transcriptor, que no sap res de cap
dels dos.

Surt `text_triat.jsonl` (una línia per rèplica amb el text guanyador i d'on surt) i el recompte.
No toca el visor ni producció.
"""
import io
import json
import unicodedata
from collections import Counter
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
VISOR = Path(r"E:/tamazight/_visor")
SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
RELLEGIT = MAG / "rellegit_bo"
DESTI = MAG / "text_triat.jsonl"

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u",
         "ŋ": "n", "ç": "s"}
#: la ə i la ā son VOCALS de l'ortografia llatina del tarifit: si no hi son,
#: l'esquelet les compta com a consonants i corromp la comparacio amb aquell model.
VOCALS = set("aeiouəā")


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


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()


def acord(slug, textos):
    a = n = 0
    for k, ull in textos.items():
        eu, eo = esquelet(ull), esquelet(sentit.get(f"{slug}:{k}", ""))
        if not eu or not eo:
            continue
        n += 1
        a += (lev(eu, eo) / max(len(eu), len(eo))) <= .35
    return a, n


def main():
    files, compte = [], Counter()
    print(f"{'capítol':<18}{'fàbrica':>10}{'relectura':>12}  guanya")
    for carpeta in sorted(VISOR.iterdir()):
        slug = carpeta.name
        if len(slug) != 40 or not (carpeta / "subtitols.jsonl").exists():
            continue
        vell = {}
        linies = {}
        for i, l in enumerate(io.open(carpeta / "subtitols.jsonl", encoding="utf-8")):
            if l.strip():
                x = json.loads(l)
                vell[str(x.get("k", i))] = (x.get("tifinag") or "").strip()
                linies[str(x.get("k", i))] = x
        p = RELLEGIT / f"{slug}.json"
        nou = json.load(io.open(p, encoding="utf-8"))["llegit"] if p.exists() else None
        av, nv = acord(slug, vell)
        if nou is None:
            guanya, textos, an = "fàbrica (sense relectura)", vell, av
        else:
            an, nn = acord(slug, nou)
            guanya, textos = ("relectura", nou) if an > av else ("fàbrica", vell)
        compte[guanya.split(" ")[0]] += 1
        print(f"{slug[:16]:<18}{100*av/max(1,nv):9.1f}%"
              f"{(100*an/max(1,nn) if nou is not None else float('nan')):11.1f}%  {guanya}")
        for k, t in textos.items():
            x = linies.get(k, {})
            files.append({"id": f"{slug}:{k}", "capitol": slug, "tifinag": t,
                          "d_on": guanya.split(" ")[0], "t_ini": x.get("t_ini"),
                          "t_fi": x.get("t_fi"), "arab": x.get("arab"), "catala": x.get("catala"),
                          "sentit": sentit.get(f"{slug}:{k}") or None})

    with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
        for r in files:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nguanyadors: {dict(compte)}")
    print(f"{len(files)} rèpliques a {DESTI}")


if __name__ == "__main__":
    main()
