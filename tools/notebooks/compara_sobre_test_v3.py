"""Els altres models sobre EXACTAMENT les nostres frases de prova

El nostre model afinat v3 llegeix amb aquests errors per lletra:

    test-dins   (Beni Mellal, font apartada)   CER 0,1883
    test-fora   (canals i Ait Mraw)            CER 0,3281
    test-mtnra  (taixelhit del Souss)          CER 0,0841

**El 0,33 de fora de casa no vol dir res tot sol.** Els números que teníem d'altres models
—NeMo zgh 0,38, mms-1b-all 0,43— són sobre altres gravacions i amb altres regles de comparació,
i comparar-los amb aquest seria comparar dues coses que no s'han mesurat igual. Aquest quadern
passa els altres models per les **mateixes** frases, amb la **mateixa** funció de distància i el
**mateix** plegat del text.

## La trampa que fa semblar dolent un model bo, i com s'evita

El `mms-1b-all` escriu `uɣrab` amb la seva lletra; el nostre text d'or diu `ugrab`, perquè tota
la biblioteca es plega a 26 lletres. Si es compara tal qual, el model perd per escriure BÉ. Per
això aquí la sortida de cada model passa pel mateix plegat que el text d'or abans de comptar.

I el `mms-1b-all` té un adaptador per llengua: per a taixelhit és `shi`. Sense carregar-lo
llegeix com si fos una altra llengua i el número no diria res del model.

## Què s'ha de llegir del resultat

Si el nostre guanya a `test-dins` però perd a `test-fora`, el que hem fet és un model de Beni
Mellal, no de la llengua. Si guanya a totes dues, l'afinament serveix. I si el `mms` guanya a
`test-mtnra`, el nostre 0,0841 era de la fuita de veu i no de saber llegir.
"""

# %%
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile", "accelerate"], check=False)
print("instal·lat")

# %%
import collections
import json
import re
import unicodedata

import librosa
import torch

#: Les mateixes taules que fem servir per muntar el corpus i per afinar. No se'n fa cap versió
#: nova: si el plegat no és idèntic, els números no es poden comparar.
TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "γ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s",
         "ṛ": "r", "š": "c", "ž": "j", "ǧ": "j", "č": "c", "ʷ": "w", "'": "", "’": ""}


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


FITXA = de_kaggle("corpus_v3.json")
if not FITXA:
    raise SystemExit("no trobo corpus_v3.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
files = json.load(open(FITXA, encoding="utf-8"))
for f in files:
    f["cami"] = os.path.join(ARREL, "audio", f["fitxer"])
proves = {s: [f for f in files if f["split"] == s and f["lletra"]
              and os.path.exists(f["cami"])]
          for s in ("test-dins", "test-fora", "test-mtnra")}
for s, g in proves.items():
    print("%-11s %d frases" % (s, len(g)))

# %%
#: El que ja sabem del nostre, de la passada d'aquest matí, per tenir-ho al costat.
NOSTRE = {"test-dins": 0.1883, "test-fora": 0.3281, "test-mtnra": 0.0841}

MODELS = [
    #: La base de la qual venim, SENSE afinar: diu què hi ha guanyat l'afinament.
    ("TutlaytAI/wav2vec2-berber", None),
    #: El gran de Meta, amb l'adaptador de taixelhit. `shi` és el codi de la llengua.
    ("facebook/mms-1b-all", "shi"),
]

from transformers import AutoModelForCTC, AutoProcessor  # noqa: E402

sortida = []
taula = collections.defaultdict(dict)

for nom, adaptador in MODELS:
    print("\n=== %s%s ===" % (nom, " (adaptador %s)" % adaptador if adaptador else ""),
          flush=True)
    try:
        proc = AutoProcessor.from_pretrained(nom)
        model = AutoModelForCTC.from_pretrained(nom)
        if adaptador:
            #: Sense això llegeix amb l'alfabet d'una altra llengua i el número no diu res.
            proc.tokenizer.set_target_lang(adaptador)
            model.load_adapter(adaptador)
        if torch.cuda.is_available():
            model = model.cuda()
        model.eval()
    except Exception as e:
        print("  no s'ha pogut carregar: %s" % str(e)[:120])
        continue

    for s, g in proves.items():
        d, n, fets = 0, 0, 0
        for f in g:
            try:
                ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
                ent = proc(ona, sampling_rate=16000, return_tensors="pt")
                if torch.cuda.is_available():
                    ent = {k: v.cuda() for k, v in ent.items()}
                with torch.no_grad():
                    ids = model(**ent).logits.argmax(-1)
                #: El plegat, que és el que fa justa la comparació.
                dit = a_llati(proc.batch_decode(ids)[0])
            except Exception as e:
                print("    %s ha fallat: %s" % (f["fitxer"], str(e)[:60]), flush=True)
                continue
            d += distancia(f["lletra"], dit)
            n += len(f["lletra"])
            fets += 1
            sortida.append({"model": nom, "split": s, "fitxer": f["fitxer"],
                            "or": f["lletra"], "dit": dit})
        if fets:
            taula[s][nom] = d / max(1, n)
            print("  %-11s CER %.4f  (%d frases)" % (s, d / max(1, n), fets), flush=True)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# %%
print("\n=== la comparació, sobre les MATEIXES frases i amb el MATEIX plegat ===")
caps = ["el nostre v3"] + [m for m, _ in MODELS]
print("  %-11s %s" % ("", "  ".join("%-26s" % c[:26] for c in caps)))
for s in ("test-dins", "test-fora", "test-mtnra"):
    cel = ["%-26.4f" % NOSTRE[s]]
    for m, _ in MODELS:
        v = taula[s].get(m)
        cel.append("%-26s" % ("%.4f" % v if v is not None else "—"))
    print("  %-11s %s" % (s, "  ".join(cel)))

print("\ncom s'ha de llegir:")
print("  test-dins  = Beni Mellal, amb la font apartada de l'entrenament")
print("  test-fora  = canals i Ait Mraw: cap d'aquestes fonts no ha entrenat")
print("  test-mtnra = taixelhit del Souss. ATENCIÓ: el MTNRA no diu qui parla, i per tant")
print("               les veus de la prova poden ser les mateixes de l'entrenament.")
print("               Treure les frases amb text repetit només el mou de 0,0841 a 0,0883,")
print("               o sigui que la fuita, si n'hi ha, és de VEU i no de text.")

json.dump(sortida, open("/kaggle/working/compara_v3.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ndesat a compara_v3.json")
