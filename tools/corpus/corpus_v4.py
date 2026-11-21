"""El corpus v4: el v3 més el Common Voice zgh, sense tornar a filtrar veus.

## Què hi entra i per què així

El Common Voice zgh (88 % taixelhit autodeclarat) és del nostre domini: el v3 hi fa 0,23, millor
que al test de fora de casa. Entra. Però amb dues condicions que l'auditoria del 29/10 va
posar i que aquí es compleixen a la lletra:

1. **Els 256 clips de `test.tsv` no entren MAI**, ni cap altre clip dels seus 26 parlants:
   són l'únic test net del projecte i la referència de tot el que vingui. El CV reparteix els
   parlants entre `train`, `dev` i `test` sense solapar-se, així que només `train.tsv` i
   `dev.tsv` poden entrar. Són DOS parlants (908 i 310 clips).

2. **Topall de 150 clips per parlant.** Sense topall, una sola veu seria el 20 % de
   l'entrenament del v4: la trampa de la baralla d'Anki de Beni Mellal amb un altre nom.

Resultat: unes 300 frases de dues veus, no les 1.474. Menys del que semblava, però netes.

## El que es conserva del v3 tal qual

Tot: particions, plegat (`a_llati` amb `ġ ḫ`), i els tres tests vells, que es mantenen però
ja no decideixen res (comparteixen font amb l'entrenament). El que decideix és `cv-zgh-test`,
que NO és dins d'aquest corpus: es prova a part.

## I una cosa nova que el v3 no tenia

`speaker` ple de debò per al CV (el `client_id`). Al v3 és buit o «MTNRA» a totes les files;
aquí hi ha per primera vegada files on la separació per veu es pot comprovar.
"""
import collections
import csv
import glob
import io
import json
import os
import random
import re
import shutil
import subprocess
import unicodedata
import wave

S = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.join(S, "corpus_v3")
ON = os.path.join(S, "corpus_v4")
AUDIO = os.path.join(ON, "audio")
CV = glob.glob(os.path.join(S, "corpus_nous", "zgh", "*", "zgh"))[0]
TOPALL = 150

TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "γ": "g", "ġ": "g", "ɛ": "a", "ḥ": "h", "ḫ": "x", "ḍ": "d", "ṭ": "t",
         "ẓ": "z", "ṣ": "s", "ṛ": "r", "š": "c", "ž": "j", "ǧ": "j", "č": "c", "ʷ": "w",
         "'": "", "’": ""}


def a_llati(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_A_LLATI.get(c, c) for c in t)
    t = "".join(PLEGA.get(c, c) for c in t)
    return re.sub(r"[^a-z ]+", "", t).strip()


if os.path.exists(ON):
    shutil.rmtree(ON)
os.makedirs(AUDIO)

#: --- el v3, copiat tal qual ---
v3 = json.load(io.open(os.path.join(V3, "corpus_v3.json"), encoding="utf-8"))
for x in v3:
    shutil.copy(os.path.join(V3, "audio", x["fitxer"]), os.path.join(AUDIO, x["fitxer"]))
files = list(v3)
print("del v3: %d files" % len(v3))

#: --- els parlants del test, que no poden entrar per cap porta ---
test_parlants = set(r["client_id"] for r in csv.DictReader(
    io.open(os.path.join(CV, "test.tsv"), encoding="utf-8"), delimiter="\t"))
print("parlants del test net (prohibits): %d" % len(test_parlants))

rnd = random.Random(4)
afegits, fora_test, fora_topall, mal = 0, 0, 0, 0
for nom_tsv in ("train.tsv", "dev.tsv"):
    rows = list(csv.DictReader(io.open(os.path.join(CV, nom_tsv), encoding="utf-8"),
                               delimiter="\t"))
    per_parlant = collections.defaultdict(list)
    for r in rows:
        if r["client_id"] in test_parlants:
            fora_test += 1
            continue
        per_parlant[r["client_id"]].append(r)
    for pid, rs in per_parlant.items():
        rnd.shuffle(rs)
        fora_topall += max(0, len(rs) - TOPALL)
        for r in rs[:TOPALL]:
            lletra = a_llati(r["sentence"])
            if not lletra:
                continue
            nom = "cv_" + r["path"].replace(".mp3", ".wav")
            p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i",
                                os.path.join(CV, "clips", r["path"]), "-ac", "1", "-ar",
                                "16000", "-c:a", "pcm_s16le", os.path.join(AUDIO, nom)],
                               capture_output=True)
            if p.returncode:
                mal += 1
                continue
            files.append({"fitxer": nom, "lletra": lletra, "text_original": r["sentence"],
                          "font": "CV-zgh:" + nom_tsv[:-4], "font_corpus": "CV-zgh",
                          "regio": "Common Voice zgh (%s)" % (r.get("variant") or "sense variant"),
                          "speaker": r["client_id"],
                          "varietat": ("taixelhit" if "ⵛⵍⵃ" in (r.get("variant") or "")
                                       else "central-atlas" if "ⵟⵍⴰⵚ" in (r.get("variant") or "")
                                       else "cv-sense-variant"),
                          "split": "train"})
            afegits += 1
print("del Common Voice: %d afegits · %d fora per ser del test · %d fora per topall · %d no s'han convertit"
      % (afegits, fora_test, fora_topall, mal))

#: --- la comprovació que ja ens va costar una passada: que tot s'obri ---
bons, dolents = [], []
for x in files:
    try:
        with wave.open(os.path.join(AUDIO, x["fitxer"])) as w:
            if w.getframerate() == 16000 and w.getnchannels() == 1:
                bons.append(x)
            else:
                dolents.append(x["fitxer"])
    except Exception:
        dolents.append(x["fitxer"])
print("s'obren a 16 kHz mono: %d · malament: %d" % (len(bons), len(dolents)))
json.dump(bons, io.open(os.path.join(ON, "corpus_v4.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("\n=== com queda ===")
for k, n in collections.Counter(x["split"] for x in bons).most_common():
    g = [x for x in bons if x["split"] == k]
    vs = collections.Counter(x["varietat"] for x in g)
    print("  %-11s %5d  %s" % (k, n, ", ".join("%s(%d)" % (a, b) for a, b in vs.most_common())))
amb_veu = sum(1 for x in bons if x.get("speaker") and x["speaker"] != "MTNRA")
print("\nfiles amb parlant de debò: %d de %d" % (amb_veu, len(bons)))
pes = sum(os.path.getsize(os.path.join(AUDIO, f)) for f in os.listdir(AUDIO)) / 1e6
print("audio: %d fitxers, %.0f MB" % (len(os.listdir(AUDIO)), pes))
