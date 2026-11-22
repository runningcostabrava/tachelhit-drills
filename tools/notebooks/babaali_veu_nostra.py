"""La veu d'en Baba Ali, llegida amb el nostre model

El vídeo porta l'àrab cremat a sota —el significat que l'autor va escriure— i 52 minuts de
taixelhit del Souss parlat de veritat. Els trams ja es van llegir una vegada amb el **NeMo**,
però ara sabem que el NeMo fa **CER 0,38** sobre gravacions nostres amb text d'or, mentre que
el model que hem afinat fa **0,157** sobre 2.404 drills i **0,093** sobre les mateixes 216
frases que havia llegit el NeMo. Quatre vegades millor.

O sigui que la primera lectura era massa dolenta per fer-ne res, i val la pena refer-la.

## Què en surt

Per a cada tram amb subtítol: **hora · què diu l'àrab (i si ens en podem fiar) · què s'hi sent**.
Això és el més a prop que hem estat d'una frase d'en Baba Ali que pugui entrar algun dia a la
biblioteca.

Dues coses que cal recordar en mirar-ho:

- **L'acord de l'àrab mesura constància entre lectures, no correcció.** Vol dir que diverses
  lectures del mateix subtítol coincideixen, no que el text sigui bo.
- **El taixelhit és de màquina.** Una lletra de cada sis segueix malament, i el model està
  afinat amb Beni Mellal i Aït Mraw, no amb el Souss — que és una altra varietat. Això s'ha de
  tenir present: pot ser pitjor aquí que a casa.

El que **no** fa: entrar res a la biblioteca.
"""

# %%
#: Un pèl abans i un pèl després del subtítol: surt amb la frase, no abans.
MARGE_ABANS = 0.3
MARGE_DESPRES = 0.6
#: Amb 0 es fan tots els trams.
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
import tempfile


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


SO = de_kaggle("babaali.wav")
TRAMS = de_kaggle("arab_votat.json")
if not SO or not TRAMS:
    raise SystemExit("falta l'àudio o els trams: " + str(os.listdir("/kaggle/input")))

trams = [x for x in json.load(open(TRAMS, encoding="utf-8"))
         if len((x.get("arab") or "").strip()) >= 8]
if QUANTS:
    trams = trams[:QUANTS]
print("trams amb àrab: %d" % len(trams))

FORA = "/kaggle/working/babaali_nostra.jsonl"
fets = set()
if os.path.exists(FORA):
    for l in open(FORA, encoding="utf-8"):
        try:
            fets.add(json.loads(l)["de"])
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

#: L'àudio sencer una sola vegada: tallar-lo 700 vegades amb ffmpeg seria mig matí.
ona_tota, _ = librosa.load(SO, sr=16000, mono=True)
print("àudio: %.1f minuts" % (len(ona_tota) / 16000 / 60))


def diu(ona):
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


# %%
amb = 0
muts = 0
with open(FORA, "a", encoding="utf-8") as fh:
    for i, x in enumerate(trams, 1):
        if x["de"] in fets:
            continue
        de = max(0.0, x["de"] - MARGE_ABANS)
        fins = de + max(1.0, x["dura"] + MARGE_DESPRES)
        tall = ona_tota[int(de * 16000):int(fins * 16000)]
        if len(tall) < 4000:
            muts += 1
            continue
        try:
            dit = diu(tall)
        except Exception as e:
            print("  %ds ha fallat: %s" % (x["de"], str(e)[:80]), flush=True)
            continue
        if not dit:
            muts += 1              # una fila buida no és una resposta
            continue
        amb += 1
        fh.write(json.dumps({"de": x["de"], "a": x["a"], "dura": x["dura"],
                             "arab": x.get("arab"), "acord_arab": x.get("acord"),
                             "taixelhit": dit}, ensure_ascii=False) + "\n")
        fh.flush()
        if i <= 8 or i % 100 == 0:
            print("%4d/%d  %5ds  %s" % (i, len(trams), x["de"], dit[:52]), flush=True)

print("\nllegits %d trams, %d sense veu" % (amb, muts))

# %%
d = []
for l in open(FORA, encoding="utf-8"):
    try:
        d.append(json.loads(l))
    except Exception:
        pass

bons = [x for x in d if (x.get("acord_arab") or 0) >= 0.8 and len(x["taixelhit"]) >= 10]
print("=== %d trams amb àrab estable I veu llegida ===" % len(bons))
print("(l'àrab estable vol dir que diverses lectures coincideixen, no que sigui correcte)")
for x in sorted(bons, key=lambda z: -(z.get("acord_arab") or 0))[:15]:
    print("\n  %5ds (%ss · acord %.2f)" % (x["de"], x["dura"], x["acord_arab"]))
    print("    àrab:       %s" % (x["arab"] or "")[:56])
    print("    taixelhit:  %s" % x["taixelhit"][:56])
