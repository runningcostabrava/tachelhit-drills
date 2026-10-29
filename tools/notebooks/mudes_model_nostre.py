"""Les 921 mudes, rellegides amb el model que hem afinat nosaltres

Les 270 frases on dos models coincidien van sortir de lectors que s'equivoquen molt: el
`wav2vec2-berber` tal com ve fa **CER 0,40** i el `mms-1b-all` 0,43. El model que acabem
d'afinar amb les nostres vuit hores fa **0,20** sobre el mateix conjunt de prova.

Amb un lector que s'equivoca la meitat, les coincidències haurien de pujar — i aquestes són
justament les frases que poden entrar a la biblioteca.

El quadern fa dues coses:

1. **Llegeix les 921** amb `josepabloucr/wav2vec2-taixelhit-nostre`.
2. **Les creua amb les dues lectures que ja teníem** (NeMo en tifinag, wav2vec2 de base en
   llatí) plegant els alfabets abans de comparar, i diu quantes tenen **dos** acords i quantes
   **tres**.

Tres acords independents sobre la mateixa gravació és el més fort que podem oferir sense que
una persona l'hagi escoltada.

**El que NO fa:** escriure res a la biblioteca. En surt un fitxer, i el que hi hagi entrarà
com a `text_tachelhit_suggested` perquè algú digui sí o no.
"""

# %%
MODEL = "josepabloucr/wav2vec2-taixelhit-nostre"
#: Amb 0 es llegeixen totes.
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


def secret(nom):
    if os.environ.get(nom):
        return os.environ[nom]
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(nom)
    except Exception:
        pass
    try:
        from google.colab import userdata
        return userdata.get(nom)
    except Exception:
        pass
    return None


# El token és opcional: el model i la llista vénen de datasets de Kaggle, que no en demanen.
# Només fa falta per pujar el resultat; sense ell, el resultat queda a la sortida del quadern.
HF_TOKEN = secret("HF_TOKEN")
print("token de HuggingFace:", "sí" if HF_TOKEN else "no (el resultat quedarà a la sortida)")

TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "ṛ": "r",
         "š": "c", "ž": "j", "ǧ": "j", "č": "c", "e": "", "'": "", "’": ""}


def net(t):
    """Les bandes a la mateixa forma: un escriu tifinag i els altres llatí."""
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


def acord(a, b):
    a, b = net(a), net(b)
    if not a or not b:
        return 0.0
    return round(1 - distancia(a, b) / max(len(a), len(b)), 3)


# %%
import requests
from huggingface_hub import HfApi, hf_hub_download

REPO = "josepabloucr/tamazight-corpus"
FORA = "/kaggle/working/mudes_nostre.jsonl" if os.path.isdir("/kaggle/working") else "mudes_nostre.jsonl"
api = HfApi()

def de_kaggle(nom):
    """El fitxer dins de /kaggle/input, on sigui que Kaggle l'hagi muntat."""
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


cami_mudes = de_kaggle("mudes.json")
if cami_mudes is None:
    cami_mudes = hf_hub_download(repo_id=REPO, filename="mudes.json", repo_type="dataset",
                                 token=HF_TOKEN)
mudes = json.load(open(cami_mudes, encoding="utf-8"))
if QUANTES:
    mudes = mudes[:QUANTES]
print("mudes:", len(mudes))

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

# El model, del dataset de Kaggle si hi és (cap token) i si no, de HuggingFace.
d_on = MODEL
for arrel, _, fitxers in os.walk("/kaggle/input"):
    if "model.safetensors" in fitxers and "config.json" in fitxers:
        d_on = arrel
        break
print("model des de:", d_on)
proc = AutoProcessor.from_pretrained(d_on, token=HF_TOKEN)
model = AutoModelForCTC.from_pretrained(d_on, token=HF_TOKEN).eval()
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


def puja(cami):
    if not HF_TOKEN:
        return                      # sense token, el resultat viu a la sortida del quadern
    try:
        api.upload_file(path_or_fileobj=cami, path_in_repo=os.path.basename(cami),
                        repo_id=REPO, repo_type="dataset", token=HF_TOKEN)
    except Exception as e:
        print("   (no s'ha pogut pujar: %s)" % str(e)[:80], flush=True)


# %%
fallades = 0
amb = 0
muts = 0
with open(FORA, "a", encoding="utf-8") as fh:
    for i, m in enumerate(mudes, 1):
        if m["id"] in fetes:
            continue
        url = (m.get("audio_url") or "").strip()
        if not url:
            continue
        dit = None
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as t:
                t.write(r.content)
                cami = t.name
            try:
                ona, _ = librosa.load(cami, sr=16000, mono=True)
                dit = diu(ona)
            finally:
                os.unlink(cami)
            fallades = 0
        except Exception as e:
            print("  #%s ha fallat: %s" % (m["id"], str(e)[:80]), flush=True)
            fallades += 1
            # Una fila buida no és una resposta.
            if fallades >= 3:
                print("tres fallades seguides: m'aturo al %d" % i, flush=True)
                break
            continue
        if not dit:
            muts += 1
            continue
        amb += 1
        fh.write(json.dumps({"id": m["id"], "catala": m.get("text_catalan"), "dit": dit},
                            ensure_ascii=False) + "\n")
        fh.flush()
        if i <= 8 or i % 100 == 0:
            print("%4d/%d  | %-34s | %s" % (i, len(mudes), (m.get("text_catalan") or "")[:34],
                                            dit[:40]), flush=True)
        if i % 200 == 0:
            puja(FORA)
puja(FORA)
print("\nllegides %d, mudes %d" % (amb, muts))

# %%
# Creuar amb les dues lectures que ja teníem.
nostre = {}
for l in open(FORA, encoding="utf-8"):
    try:
        d = json.loads(l)
        nostre[d["id"]] = d
    except Exception:
        pass

velles = {}
for fitxer, camp in (("mudes_nemo.jsonl", "nemo"), ("lectura_mudes.jsonl", "wav2vec2")):
    cami = de_kaggle(fitxer)
    if cami is None:
        try:
            cami = hf_hub_download(repo_id=REPO, filename=fitxer, repo_type="dataset",
                                   token=HF_TOKEN)
        except Exception:
            print("no hi ha", fitxer, "(les lectures velles no es podran creuar)")
            continue
    for l in open(cami, encoding="utf-8"):
        try:
            d = json.loads(l)
            velles.setdefault(d["id"], {})[camp] = (d.get("dit") or "").strip()
        except Exception:
            pass
print("lectures velles per a %d gravacions" % len(velles))

creuades = []
for i, d in nostre.items():
    v = velles.get(i) or {}
    e = {"id": i, "catala": d.get("catala"), "nostre": d["dit"],
         "nemo": v.get("nemo", ""), "wav2vec2": v.get("wav2vec2", "")}
    e["amb_nemo"] = acord(e["nostre"], e["nemo"])
    e["amb_wav2vec2"] = acord(e["nostre"], e["wav2vec2"])
    e["nemo_wav2vec2"] = acord(e["nemo"], e["wav2vec2"])
    # Quants parells dels tres possibles coincideixen prou.
    e["acords"] = sum(1 for k in ("amb_nemo", "amb_wav2vec2", "nemo_wav2vec2") if e[k] >= 0.7)
    creuades.append(e)

json.dump(creuades, open(os.path.join(os.path.dirname(FORA) or ".", "mudes_tres_lectors.json"),
                         "w", encoding="utf-8"), ensure_ascii=False, indent=1)
puja(os.path.join(os.path.dirname(FORA) or ".", "mudes_tres_lectors.json"))

print("\n=== quants acords de tres possibles ===")
for n in (3, 2, 1, 0):
    print("  %d parells d'acord: %4d" % (n, sum(1 for e in creuades if e["acords"] == n)))
print("\nabans, amb dos lectors, n'hi havia 270 amb acord >= 0,7.")
print("\nles més segures:")
for e in sorted(creuades, key=lambda z: (-z["acords"], -z["amb_nemo"]))[:10]:
    print("\n  #%s  (%d parells d'acord)  «%s»" % (e["id"], e["acords"], (e["catala"] or "")[:40]))
    print("    el nostre: %s" % e["nostre"][:48])
    print("    nemo:      %s" % e["nemo"][:48])
    print("    wav2vec2:  %s" % e["wav2vec2"][:48])
