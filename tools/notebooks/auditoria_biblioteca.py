"""Auditar la biblioteca: on el que se sent no s'assembla al que hi ha escrit

La idea és simple: la màquina escolta cada gravació, i es compara el que sent amb el que algú
va escriure. Si no s'assemblen gens, **alguna cosa falla** — o el text no és el que diu la
gravació, o la gravació no és la del text.

Això fins avui no es podia fer. Amb un lector que s'equivoca la meitat de les lletres, un
desacord no vol dir res: podia ser el lector. El model que hem afinat amb les nostres vuit
hores fa **CER 0,20**, i això canvia la pregunta.

## La trampa que cal evitar, i que ja m'ha enganyat una vegada

Amb una paraula **curta** qualsevol error sembla enorme: si la paraula té 6 lletres i se
n'encerta una, surt un 85% de desacord. Amb una frase llarga, una lletra equivocada surt un 3%.
Mesurant-ho tot junt, les paraules soltes omplien la llista de falsos sospitosos: semblava que
fallés el 25% de la biblioteca quan, mirant només frases, en falla el **5%**.

Per això aquí:

- **només entren frases** (20 caràcters o més), que és on el desacord vol dir alguna cosa;
- les **paraules soltes** es miren a part i amb un llindar molt més alt;
- i es compten a banda les gravacions on **la màquina sent un o dos sons i prou**: allà el
  problema no és el text sinó que a la gravació gairebé no hi ha veu.

## El que NO fa

No canvia res. Treu una llista ordenada pel desacord perquè una persona miri primer les
pitjors. El text d'un parlant no el toca mai una màquina.
"""

# %%
#: El nostre model. Ve d'un dataset de Kaggle, per no dependre de cap secret.
MODEL = "josepabloucr/wav2vec2-taixelhit-nostre"
#: A partir d'aquí una cosa és una frase i el desacord vol dir alguna cosa.
FRASE = 20
#: Per sota d'això es mira a part: una paraula curta sempre sembla sospitosa.
CURT = 10
#: Amb 0 es miren totes.
QUANTES = 0

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile", "huggingface_hub"], check=False)
print("instal·lat")

# %%
import json
import os
import tempfile
import unicodedata

import requests

TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "ṛ": "r",
         "š": "c", "ž": "j", "ǧ": "j", "č": "c", "e": "", "'": "", "’": ""}


def net(t):
    """Les dues bandes a la mateixa forma: el text d'or pot ser en tifinag o en llatí."""
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_A_LLATI.get(c, c) for c in t)
    for mult, un in (("gh", "g"), ("kh", "x"), ("ch", "c"), ("sh", "c"), ("ou", "u")):
        t = t.replace(mult, un)
    t = "".join(PLEGA.get(c, c) for c in t)
    return "".join(c for c in t if c.isalnum())


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


FORA = ("/kaggle/working/auditoria.jsonl" if os.path.isdir("/kaggle/working")
        else "auditoria.jsonl")

cami = de_kaggle("drills_tots.json")
if cami is None:
    raise SystemExit("falta drills_tots.json: " + str(os.listdir("/kaggle/input")))
drills = json.load(open(cami, encoding="utf-8"))
feina = [x for x in drills
         if (x.get("audio_url") or "").strip() and len(net(x.get("text_tachelhit"))) >= 4]
if QUANTES:
    feina = feina[:QUANTES]
frases = [x for x in feina if len(net(x.get("text_tachelhit"))) >= FRASE]
print("amb veu i text: %d · de les quals frases (>=%d lletres): %d"
      % (len(feina), FRASE, len(frases)))

fetes = set()
if os.path.exists(FORA):
    for l in open(FORA, encoding="utf-8"):
        try:
            fetes.add(json.loads(l)["id"])
        except Exception:
            pass
print("ja fetes:", len(fetes))

# %%
import librosa
import torch
from transformers import AutoModelForCTC, AutoProcessor

d_on = MODEL
for arrel, _, fitxers in os.walk("/kaggle/input"):
    if "model.safetensors" in fitxers and "config.json" in fitxers:
        d_on = arrel
        break
print("model des de:", d_on)
proc = AutoProcessor.from_pretrained(d_on)
model = AutoModelForCTC.from_pretrained(d_on).eval()
if torch.cuda.is_available():
    model = model.cuda()
print("carregat")


def diu(ona):
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


# %%
fallades = 0
mirades = 0
with open(FORA, "a", encoding="utf-8") as fh:
    for i, x in enumerate(feina, 1):
        if x["id"] in fetes:
            continue
        dit = None
        segons = None
        try:
            so = requests.get(x["audio_url"].strip(), timeout=120)
            so.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as t:
                t.write(so.content)
                cami_so = t.name
            try:
                ona, _ = librosa.load(cami_so, sr=16000, mono=True)
                segons = round(len(ona) / 16000, 2)
                dit = diu(ona)
            finally:
                os.unlink(cami_so)
            fallades = 0
        except Exception as e:
            print("  #%s ha fallat: %s" % (x["id"], str(e)[:80]), flush=True)
            fallades += 1
            if fallades >= 3:
                print("tres fallades seguides: m'aturo al %d" % i, flush=True)
                break
            continue

        escrit, sentit = net(x.get("text_tachelhit")), net(dit)
        if not escrit:
            continue
        desacord = round(distancia(escrit, sentit) / max(1, len(escrit)), 3)
        mirades += 1
        fh.write(json.dumps({
            "id": x["id"], "desacord": desacord, "segons": segons,
            "lletres_escrit": len(escrit), "lletres_sentit": len(sentit),
            "es_frase": len(escrit) >= FRASE,
            "escrit": (x.get("text_tachelhit") or "").strip(), "sentit": dit,
            "catala": (x.get("text_catalan") or "").strip(),
            "font": x.get("source_title") or x.get("source"), "regio": x.get("region"),
        }, ensure_ascii=False) + "\n")
        fh.flush()
        if i % 200 == 0:
            print("%5d/%d  mirades %d" % (i, len(feina), mirades), flush=True)

print("\nmirades:", mirades)

# %%
d = []
for l in open(FORA, encoding="utf-8"):
    try:
        d.append(json.loads(l))
    except Exception:
        pass

frases = [x for x in d if x["es_frase"]]
paraules = [x for x in d if not x["es_frase"]]
#: On la màquina sent un o dos sons i prou: allà el problema no és el text, és que a la
#: gravació gairebé no hi ha veu.
mudes = [x for x in d if x["lletres_sentit"] <= 2]

print("=== FRASES (>=%d lletres): %d ===" % (FRASE, len(frases)))
for llindar in (0.8, 0.6, 0.5):
    n = sum(1 for x in frases if x["desacord"] >= llindar)
    print("  desacord >= %.1f : %4d  (%d%%)" % (llindar, n, 100 * n // max(1, len(frases))))
print("=== paraules soltes (<%d lletres): %d ===" % (FRASE, len(paraules)))
print("  (aquí el desacord enganya: una paraula curta sempre sembla sospitosa)")
print("=== gravacions on la màquina sent 1-2 sons: %d ===" % len(mudes))

print("\n--- les frases que més criden l'atenció ---")
for x in sorted(frases, key=lambda z: -z["desacord"])[:12]:
    print("\n#%-6s desacord %.2f · %ss · %s" % (x["id"], x["desacord"], x["segons"],
                                                (x.get("regio") or x.get("font") or "?")[:28]))
    print("   escrit:  %s" % x["escrit"][:58])
    print("   se sent: %s" % x["sentit"][:58])
    print("   català:  %s" % (x.get("catala") or "")[:58])

print("\n--- gravacions gairebé sense veu ---")
for x in sorted(mudes, key=lambda z: (z["segons"] or 0))[:10]:
    print("  #%-6s %ss  escrit «%s» · se sent «%s»"
          % (x["id"], x["segons"], x["escrit"][:30], x["sentit"][:12]))
