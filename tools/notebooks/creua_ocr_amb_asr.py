"""L'OCR i l'ASR sobre el mateix segon: on coincideixen, el parell és bo

## Què es prova aquí

Del conte del lleó n'hem tret 31 moments amb **el so i el text del subtítol alhora**. El text el
va llegir l'OCR de tifinag, que té un CER de 0,250 sobre l'única línia d'or que tenim. Amb un
error de lletra de cada quatre, aquell text no pot entrar sol a la biblioteca ni entrenar res.

Però hi ha una segona màquina que diu què s'hi diu: **el nostre ASR**, que escolta la veu. I les
dues no comparteixen res —ni model, ni dades d'entrenament, ni alfabet de sortida—. Quan totes
dues treuen la mateixa frase al mateix segon, no pot ser error de cap de les dues.

És la mateixa manera de treballar que ja ens ha funcionat tres vegades avui: els tres lectors de
les mudes, l'ordre del llibre al CD del Mètode, i el préstec àrab d'en Baba Ali.

## Què decideix si val

**El control**: el mateix càlcul amb els parells barrejats, l'OCR d'un moment contra la veu d'un
altre. Tres voltes. Si barrejant surt el mateix, l'acord no vol dir res i el que hem muntat no
serveix per collir parells sols.

## El que NO prova

Que el text sigui correcte. Dues màquines poden coincidir en un error si totes dues senten
malament la mateixa cosa —passa amb els noms propis i amb els sons que el taixelhit té i que cap
dels dos models no distingeix bé. L'acord fa la frase **candidata**, no verdadera: va a
`*_suggested` igual, però amb una procedència que val molt més que una lectura sola.
"""

# %%
#: El nostre model afinat v3, que és el millor que tenim: 0,1883 a casa i 0,3281 a fora.
NOSTRE = "model-taixelhit-nostre"
#: Per sota d'això, l'OCR no estava segur del que llegia i no val la pena comparar-ho.
CONFIA = 0.80

# %%
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile"], check=False)
print("instal·lat")

# %%
import json
import random
import re
import unicodedata

import librosa
import torch
from transformers import AutoModelForCTC, AutoProcessor


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


FITXA = de_kaggle("extret.json")
if not FITXA:
    raise SystemExit("no trobo extret.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
d = json.load(open(FITXA, encoding="utf-8"))
parells = [p for p in d["parells"] if p.get("text") and p.get("so")]
print("parells del vídeo: %d" % len(parells))

#: El model nostre: es busca la carpeta dins dels datasets enganxats.
cami = None
for arrel, dirs, _ in os.walk("/kaggle/input"):
    for x in dirs:
        if NOSTRE in x:
            cami = os.path.join(arrel, x)
if not cami:
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if "preprocessor_config.json" in fitxers:
            cami = arrel
if not cami:
    raise SystemExit("no trobo el model: " + str(os.listdir("/kaggle/input")))
print("model: %s" % cami)

proc = AutoProcessor.from_pretrained(cami)
model = AutoModelForCTC.from_pretrained(cami)
if torch.cuda.is_available():
    model = model.cuda()
model.eval()

# %%
#: Les dues bandes escriuen diferent: l'OCR treu TIFINAG i l'ASR treu LLATÍ. Comparar-los tal
#: qual dona un 100% d'error encara que diguin exactament el mateix. Es plega tot a la mateixa
#: forma abans de comparar — és l'error que ja ens ha costat quatre mesures falses aquest mes.
TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "γ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s",
         "ṛ": "r", "š": "c", "ž": "j", "ǧ": "j", "č": "c", "ʷ": "w", "'": "", "’": ""}


def plega(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_A_LLATI.get(c, c) for c in t)
    for a, b in (("gh", "g"), ("kh", "x"), ("ch", "c"), ("sh", "c"), ("ou", "u")):
        t = t.replace(a, b)
    t = "".join(PLEGA.get(c, c) for c in t)
    return re.sub(r"[^a-z]+", "", t)


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


def acord(a, b):
    a, b = plega(a), plega(b)
    if not a or not b:
        return 0.0
    return round(1 - distancia(a, b) / max(len(a), len(b)), 3)


def escolta(cami_so):
    ona, _ = librosa.load(cami_so, sr=16000, mono=True)
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


# %%
fora = []
for p in parells:
    so = os.path.join(ARREL, "so", p["so"])
    if not os.path.exists(so):
        continue
    try:
        sentit = escolta(so)
    except Exception as e:
        print("  %s ha fallat: %s" % (p["so"], str(e)[:60]), flush=True)
        continue
    fora.append({"n": p["n"], "de": p["de"], "a": p["a"], "dura": p["dura"],
                 "ocr": p["text"], "confianca": p.get("confianca"),
                 "asr": sentit, "acord": acord(p["text"], sentit)})

print("\nmoments comparats: %d" % len(fora))
segurs = [x for x in fora if (x["confianca"] or 0) >= CONFIA]
print("amb l'OCR segur (>= %.2f): %d" % (CONFIA, len(segurs)))

for llindar in (0.8, 0.7, 0.6, 0.5, 0.4):
    n = sum(1 for x in segurs if x["acord"] >= llindar)
    print("  acord >= %.1f : %3d" % (llindar, n))

#: El control: l'OCR d'un moment contra la veu d'un altre. Tres voltes.
random.seed(5)
caixa = [x["ocr"] for x in segurs]
atzar = 0.0
for _ in range(3):
    random.shuffle(caixa)
    atzar += sum(1 for t, x in zip(caixa, segurs) if acord(t, x["asr"]) >= 0.6)
atzar /= 3.0
bons = sum(1 for x in segurs if x["acord"] >= 0.6)
print("\ncontrol amb els parells barrejats (acord >= 0,6): %.1f" % atzar)
print("de debò: %d" % bons)
print("-> %s" % ("l'acord MESURA alguna cosa" if bons > 2.5 * max(atzar, 1)
                 else "NO distingeix prou: això no serveix per collir parells sols"))

print("\n--- deu moments, pel seu acord ---")
for x in sorted(segurs, key=lambda z: -z["acord"])[:10]:
    print("\n  %5.1f-%5.1fs  acord %.2f  (OCR segur al %.2f)"
          % (x["de"], x["a"], x["acord"], x["confianca"] or 0))
    print("     el subtítol: %s" % x["ocr"][:62])
    print("     la veu     : %s" % x["asr"][:62])

json.dump(fora, open("/kaggle/working/creuat.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ndesat a creuat.json")
print("\nel que això NO prova: que el text sigui correcte. Dues màquines poden coincidir en un")
print("error si totes dues senten malament el mateix. L'acord fa la frase CANDIDATA.")
