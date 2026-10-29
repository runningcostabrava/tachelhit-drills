"""Els tres models sobre el test del Common Voice zgh: el primer test net del projecte

## Per què aquest test i no els que teníem

L'auditoria del 29/10 va demostrar que dos dels tres tests del corpus comparteixen font amb
l'entrenament (Beni Mellal: train 1.680 / test 150; MTNRA: train 1.501 / test 300), i que el
tercer, `test-fora`, només té 101 frases: l'interval d'un bootstrap aparellat hi és de ±0,027 i
cap diferència més petita no es veu. Cap decisió del pla no era decidible amb això.

El `test.tsv` del Common Voice zgh són **256 clips de 26 parlants, 17 minuts**, disjunts per
FONT i per PARLANT de tot el que hem entrenat. És el primer test del projecte on la separació
de veu es pot comprovar: al nostre corpus `speaker` és buit o val «MTNRA» a totes les files.

I no és amazic estàndard: la columna `variant` diu que el 88 % dels parlants es declaren
**taixelhit**, amb 47 clips de Central Atlas. És la diana del projecte, no una llengua veïna.

## Les tres coses que fan que el número valgui

1. **La mateixa regla a les dues bandes**: text d'or i sortida passen per la mateixa `a_llati`,
   amb la taula que cobreix el que les bases escriuen de debò (`ġ`, `ḫ`). Abans s'esborraven i
   cada esborrat era una supressió comptada contra el model.
2. **La sortida crua es desa** al costat de la plegada. Sense això no es pot repartir la pèrdua
   entre model i taula.
3. **Bootstrap aparellat per frase**, mil remostres: una diferència de 0,017 sense interval es
   llegeix com una victòria i no ho és.

## Què decideix

Si el v3 hi fa com a `test-fora` (~0,33) o millor, el zgh és del nostre domini i el v4 el pot
portar (amb topall de clips per parlant: dues veus fan el 83 % del corpus). Si el v3 i el
`mms-1b-all` sense afinar hi són indistingibles, tres passades d'afinament no han guanyat res i
la base petita no és el camí. Avui això no es pot dir amb cap test que tinguem.
"""

# %%
NOSTRE = "model-taixelhit-nostre"
MODELS = [
    ("TutlaytAI/wav2vec2-berber", None),
    ("facebook/mms-1b-all", "shi"),
]
REMOSTRES = 1000

# %%
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile"], check=False)
print("instal·lat")

# %%
import collections
import json
import random
import re
import unicodedata

import librosa
import torch
from transformers import AutoModelForCTC, AutoProcessor

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


def distancia(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


FITXA = de_kaggle("cv_test.json")
if not FITXA:
    raise SystemExit("no trobo cv_test.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
clips = json.load(open(FITXA, encoding="utf-8"))
for c in clips:
    c["cami"] = os.path.join(ARREL, "audio", c["fitxer"])
    c["lletra"] = a_llati(c["sentence"])
clips = [c for c in clips if c["lletra"] and os.path.exists(c["cami"])]
print("clips: %d · parlants: %d" % (len(clips), len(set(c["client_id"] for c in clips))))
print("per variant: %s" % dict(collections.Counter((c["variant"] or "(buit)")[:30] for c in clips)))

#: El nostre, de la carpeta del dataset enganxat. La primera passada buscava
#: `preprocessor_config.json` i no el va trobar: es busca com ho fa `creua_ocr_amb_asr.py`,
#: que sí que el carrega — pel NOM de la carpeta, i si no, per on hi hagi `config.json`.
cami_nostre = None
for arrel, dirs, fitxers in os.walk("/kaggle/input"):
    for x in dirs:
        if NOSTRE in x:
            cami_nostre = os.path.join(arrel, x)
if not cami_nostre:
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if "config.json" in fitxers and "cv_test.json" not in fitxers:
            cami_nostre = arrel
if not cami_nostre:
    raise SystemExit("no trobo el model nostre: " + str(
        [os.path.join(a, x) for a, d, _ in os.walk("/kaggle/input") for x in d][:30]))
print("model nostre: %s → %s" % (cami_nostre, sorted(os.listdir(cami_nostre))[:8]))
TOTS = [("el nostre v3", cami_nostre, None)] + [(n, n, a) for n, a in MODELS]

# %%
lectures = {}
for nom, cami, adaptador in TOTS:
    print("\n=== %s ===" % nom, flush=True)
    proc = AutoProcessor.from_pretrained(cami)
    model = AutoModelForCTC.from_pretrained(cami)
    if adaptador:
        proc.tokenizer.set_target_lang(adaptador)
        model.load_adapter(adaptador)
    if torch.cuda.is_available():
        model = model.cuda()
    model.eval()
    per = {}
    for c in clips:
        try:
            ona, _ = librosa.load(c["cami"], sr=16000, mono=True)
            ent = proc(ona, sampling_rate=16000, return_tensors="pt")
            if torch.cuda.is_available():
                ent = {k: v.cuda() for k, v in ent.items()}
            with torch.no_grad():
                ids = model(**ent).logits.argmax(-1)
            cru = proc.batch_decode(ids)[0]
        except Exception as e:
            print("  %s ha fallat: %s" % (c["fitxer"], str(e)[:60]), flush=True)
            continue
        dit = a_llati(cru)
        per[c["fitxer"]] = {"cru": cru, "dit": dit, "d": distancia(c["lletra"], dit),
                            "n": len(c["lletra"])}
    lectures[nom] = per
    d = sum(x["d"] for x in per.values())
    n = sum(x["n"] for x in per.values())
    print("  CER %.4f  (%d clips) · raó de llargada hipòtesi/or %.3f"
          % (d / max(1, n), len(per),
             sum(len(x["dit"]) for x in per.values()) / max(1, n)), flush=True)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# %%
#: --- la taula, per variant i amb intervals ---
comuns = [c for c in clips if all(c["fitxer"] in lectures[n] for n, _, _ in TOTS)]
print("\nclips llegits pels tres: %d" % len(comuns))


def cer(nom, grup):
    d = sum(lectures[nom][c["fitxer"]]["d"] for c in grup)
    n = sum(lectures[nom][c["fitxer"]]["n"] for c in grup)
    return d / max(1, n)


def bootstrap(a, b, grup):
    """Diferència CER(a) - CER(b), amb les MATEIXES frases remostrejades per als dos."""
    rnd = random.Random(29)
    difs = []
    for _ in range(REMOSTRES):
        m = [grup[rnd.randrange(len(grup))] for _ in grup]
        difs.append(cer(a, m) - cer(b, m))
    difs.sort()
    return difs[int(0.025 * REMOSTRES)], difs[int(0.975 * REMOSTRES)]


def guanya_perd(a, b, grup):
    g = p = e = 0
    for c in grup:
        x, y = lectures[a][c["fitxer"]]["d"], lectures[b][c["fitxer"]]["d"]
        if x < y:
            g += 1
        elif x > y:
            p += 1
        else:
            e += 1
    return g, p, e


grups = {"tots": comuns}
for v in sorted(set(c["variant"] for c in comuns)):
    g = [c for c in comuns if c["variant"] == v]
    if len(g) >= 20:
        grups[(v or "(sense variant)")[:34]] = g

print("\n=== CER sobre el test del Common Voice zgh ===")
print("%-36s %5s  " % ("", "n") + "  ".join("%-16s" % n[:16] for n, _, _ in TOTS))
for nom_g, g in grups.items():
    print("%-36s %5d  " % (nom_g, len(g)) + "  ".join("%-16.4f" % cer(n, g) for n, _, _ in TOTS))

print("\n=== el nostre v3 contra cadascun, bootstrap aparellat per frase (IC 95 %%) ===")
for nom, _, _ in TOTS[1:]:
    for nom_g, g in grups.items():
        lo, hi = bootstrap("el nostre v3", nom, g)
        gu, pe, em = guanya_perd("el nostre v3", nom, g)
        veredicte = ("el v3 GUANYA" if hi < 0 else "el v3 PERD" if lo > 0 else "INDISTINGIBLES")
        print("  v3 − %-26s %-24s dif %+.4f  IC [%+.4f, %+.4f]  frases %d/%d/%d  → %s"
              % (nom[:26], nom_g[:24], cer("el nostre v3", g) - cer(nom, g), lo, hi,
                 gu, pe, em, veredicte))

print("\nper comparar amb l'únic test net d'abans: test-fora (101 frases)")
print("  v3 0,3281 · mms-1b-all 0,3452 · wav2vec2-berber 0,4481 — dif v3−mms −0,017,")
print("  IC [−0,045, +0,011], frases 44/41/16: indistingibles.")

json.dump({"clips": [{k: c[k] for k in ("fitxer", "sentence", "lletra", "client_id", "variant")}
                     for c in comuns],
           "lectures": lectures},
          open("/kaggle/working/cv_zgh_tres_models.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ndesat a cv_zgh_tres_models.json (amb la sortida crua de cada model)")
