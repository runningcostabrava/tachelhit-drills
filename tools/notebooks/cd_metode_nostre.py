"""El CD del Mètode, llegit amb el nostre model

Els capítols 1 a 6 de la *Méthode de Tachelhit* llegits en veu alta: 39 minuts de vídeo que, un
cop tret el silenci i la part explicada en francès, deixen **14 minuts de taixelhit dit a poc a
poc**, tallats en 666 trossos pels silencis.

## Per què aquest material val més que un altre

Perquè **el llibre el tenim**, en PDF i amb capa de text. Això vol dir que aquí no busquem
propostes sinó **parelles**: si el que el model sent s'assembla prou a una línia del llibre,
aquell tros d'àudio té text d'or —escrit per l'autor del mètode, no per una màquina—. És
l'única font nova que pot donar text d'or sense que ningú s'assegui a escoltar-ho tot.

Aquest quadern fa la primera meitat: **sentir**. L'aparellament amb el llibre es fa després i a
casa, perquè és allà on hi ha el PDF.

## El que NO fa

No entra res a la biblioteca, i el que surt d'aquí no és el text de cap parlant: és el que una
màquina ha sentit, amb una lletra de cada sis equivocada sobre material conegut. Va a `/revisa`
com a esborrany amb la seva procedència, mai al camp d'or.
"""

# %%
#: Amb 0 es fan tots els talls.
QUANTS = 0

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile"], check=False)
print("instal·lat")

# %%
import json
import os


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


TALLS = de_kaggle("talls.json")
if not TALLS:
    raise SystemExit("no trobo talls.json: " + str(os.listdir("/kaggle/input")))
CARPETA = os.path.dirname(TALLS)
talls = json.load(open(TALLS, encoding="utf-8"))
if QUANTS:
    talls = talls[:QUANTS]
print("talls: %d (%.1f minuts)" % (len(talls), sum(t["dura"] for t in talls) / 60))

import collections  # noqa: E402

for cap, n in collections.Counter(t["capitol"] for t in talls).most_common():
    print("  %3d  %s" % (n, cap))

FORA = "/kaggle/working/cd_metode_nostre.jsonl"
fets = set()
if os.path.exists(FORA):
    for l in open(FORA, encoding="utf-8"):
        try:
            fets.add(json.loads(l)["fitxer"])
        except Exception:
            pass
print("ja fets:", len(fets))

# %%
import librosa
import torch
from transformers import AutoModelForCTC, AutoProcessor

d_on = None
for arrel, _, fitxers in os.walk("/kaggle/input"):
    if "model.safetensors" in fitxers and "config.json" in fitxers:
        d_on = arrel
        break
if not d_on:
    raise SystemExit("no trobo el model al dataset")
print("model des de:", d_on)
proc = AutoProcessor.from_pretrained(d_on)
model = AutoModelForCTC.from_pretrained(d_on).eval()
if torch.cuda.is_available():
    model = model.cuda()
print("carregat")


def diu(cami):
    ona, _ = librosa.load(cami, sr=16000, mono=True)
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


# %%
amb, muts, fallades = 0, 0, 0
with open(FORA, "a", encoding="utf-8") as fh:
    for i, t in enumerate(talls, 1):
        if t["fitxer"] in fets:
            continue
        cami = os.path.join(CARPETA, t["fitxer"])
        if not os.path.exists(cami):
            print("  falta %s" % t["fitxer"], flush=True)
            continue
        try:
            dit = diu(cami)
            fallades = 0
        except Exception as e:
            print("  %s ha fallat: %s" % (t["fitxer"], str(e)[:80]), flush=True)
            fallades += 1
            if fallades >= 3:
                print("tres fallades seguides: m'aturo al %d" % i, flush=True)
                break
            continue
        if not dit:
            muts += 1              # una fila buida no és una resposta
            continue
        amb += 1
        fh.write(json.dumps({**t, "sentit": dit}, ensure_ascii=False) + "\n")
        fh.flush()
        if i <= 10 or i % 50 == 0:
            print("%4d/%d  %-10s %4.1fs  %s" % (i, len(talls), t["fitxer"], t["dura"], dit[:52]),
                  flush=True)

print("\nllegits %d, sense veu %d" % (amb, muts))

# %%
d = []
for l in open(FORA, encoding="utf-8"):
    try:
        d.append(json.loads(l))
    except Exception:
        pass

print("=== què se sent, capítol per capítol ===")
for cap in sorted({x["capitol"] for x in d}):
    g = [x for x in d if x["capitol"] == cap]
    lletres = sum(len(x["sentit"]) for x in g)
    print("\n%s  —  %d talls, %d lletres (mitjana %.1f)"
          % (cap, len(g), lletres, lletres / max(1, len(g))))
    for x in g[:6]:
        print("   %6.1fs %4.1fs  %s" % (x["de"], x["dura"], x["sentit"][:58]))

print("\nel que ve després: aparellar-ho amb el text del llibre. Una lectura que s'assembli prou")
print("a una línia del Mètode té text d'or; les altres es queden com a esborrany.")
