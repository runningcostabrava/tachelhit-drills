"""Provar models d'ASR amb el nostre corpus, en bloc i amb GPU (Kaggle o Colab).

Per què cal sortir de casa per a això. El model que tenim corrent al Docker fa 51 MB i va a
CPU: amb l'amazic estàndard llegit se'n surt (CER 0,134) i amb les nostres veus de Beni Mellal
i d'Aït Mraw, no. Els models que la taula de referència posa al davant —l'omniASR de 7B, el
MMS, el wav2vec2-berber— **volen GPU i no caben en aquesta màquina**: té 1 GB de RAM lliure i
cap NVIDIA.

Aquest quadern els passa pel mateix material i amb la mateixa vara, de manera que els números
es puguin comparar entre ells i amb el que ja tenim.

## Com es fa servir

**Kaggle**: puja'l com a quadern, posa Accelerator = GPU, i afegeix el teu token de HuggingFace
a Add-ons → Secrets amb el nom `HF_TOKEN`. Després «Save & Run All»: corre sol fins a 12 hores
encara que tanquis el navegador, i el resultat queda desat.

**Colab**: obre'l, tria un entorn amb GPU, i posa el token a l'esquerra, al pany (Secrets), amb
el mateix nom.

## El que mesura, i per què dues vares

· **la vara de fora** (TOSD): amazic estàndard llegit. Diu si el model sap llegir la llengua.
· **la vara nostra**: Beni Mellal i Aït Mraw. Diu si sap llegir **el que nosaltres gravem**,
  que és l'única cosa que de debò ens importa.

Un model pot ser bo a la primera i inútil a la segona —ens ha passat— i per això es miren les
dues. El número que mana és el segon.

## El que NO fa

No escriu res a la biblioteca. En surt un fitxer de resultats i prou; el que entri a l'app
passa per la porta de sempre: `*_suggested`, i ho confirma una persona.
"""

# %% [markdown]
# # Provar models d'ASR amb el corpus de taixelhit
#
# El corpus és un dataset privat de HuggingFace (`josepabloucr/tamazight-corpus`): 2.836 talls
# amb el text en tifinag, la varietat, la comarca i el repartiment entre entrenar i provar.
#
# **El que es tria i prova no s'entrena**: aquí només es mesura.

# %%
MODELS = [
    # id a HuggingFace                                    com es carrega
    ("ayymen/stt_zgh_fastconformer_ctc_small", "nemo"),   # el que ja tenim: la referència
    ("TutlaytAI/wav2vec2-berber", "wav2vec2"),            # CER 0,35 al banc de proves
    ("facebook/mms-1b-all", "mms"),                       # multilingüe, amb adaptador per a shi
]
#: Quants talls de cada vara. Amb 0 es passen tots.
QUANTS = 300

# %%
# El NeMo no ve de serie ni a Kaggle ni a Colab, i sense ell el model de referencia no es pot ni
# carregar: la passada anterior va morir amb «No module named 'nemo'». S'instal·la aqui, al
# principi, perque trigui mentre encara no fa falta res mes.
import subprocess  # noqa: E402
import sys as _sys  # noqa: E402

try:
    import nemo  # noqa: F401
    print("el nemo ja hi era")
except Exception:
    print("instal·lant el nemo...", flush=True)
    subprocess.run([_sys.executable, "-m", "pip", "install", "-q", "nemo_toolkit[asr]"],
                   check=False)
    try:
        import nemo  # noqa: F401
        print("nemo llest")
    except Exception as e:
        print("el nemo no s'ha pogut instal·lar:", str(e)[:150])

# %%
import json
import os
import re
import sys
import unicodedata

def secret(nom):
    """El token, d'on sigui que l'hagi posat qui corre això."""
    if os.environ.get(nom):
        return os.environ[nom]
    try:                                   # Kaggle
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(nom)
    except Exception:
        pass
    try:                                   # Colab
        from google.colab import userdata
        return userdata.get(nom)
    except Exception:
        pass
    raise SystemExit("falta el secret %s (Kaggle: Add-ons > Secrets; Colab: el pany)" % nom)

# El token NO es demana aqui: a Kaggle el corpus ve d'un dataset i no en cal cap. Demanar-lo
# per endavant feia caure la passada a la segona cel·la encara que no fes falta.
HF_TOKEN = None

# %%
# El corpus.
#
# A Kaggle ve d'un dataset privat enganxat al quadern, i aixo **no demana cap token**: corre amb
# el compte de qui l'ha pujat. Es a posta. Mentre el corpus vivia darrere d'un token de
# HuggingFace, cada vegada que es pujava una versio del quadern per l'API el secret s'hi
# desenganxava i la passada queia amb «falta el secret HF_TOKEN» — van caure'n tres seguides.
# Amb el dataset, pujar i llancar torna a ser una sola ordre i el peo pot correr sol.
#
# A Colab no hi ha datasets, i alla si que es baixa de HuggingFace amb el token.
import os as _os

KAGGLE = "/kaggle/input/corpus-taixelhit"
if _os.path.isdir(KAGGLE):
    carpeta = KAGGLE
    print("el corpus ve del dataset de Kaggle: no cal cap token")
else:
    from huggingface_hub import snapshot_download
    carpeta = snapshot_download(repo_id="josepabloucr/tamazight-corpus", repo_type="dataset",
                                token=secret("HF_TOKEN"))
    print("el corpus ve de HuggingFace")
files = [json.loads(l) for l in open(os.path.join(carpeta, "manifest.jsonl"), encoding="utf-8") if l.strip()]
prova = [f for f in files if f.get("split") == "test"]
print("corpus: %d talls | de prova: %d" % (len(files), len(prova)))

# %%
# La mesura.
#
# Dues coses, i la segona és la que fa que el número vulgui dir alguna cosa:
#
# · el CER es compta sobre LLETRES. La puntuació i els espais no diuen res de si el model hi
#   sent bé, i comptar-los faria pujar el número per coses que no són errors.
#
# · **els dos costats es passen al mateix alfabet abans de restar.** La nostra referència és
#   en tifinag i molts models escriuen en llatí: comparats tal qual, `ⵜⴰⵣⵣⵍⴰ` i `tazzla` —que
#   són LA MATEIXA PARAULA— donen un error del 100%. Va passar de debò: el wav2vec2-berber va
#   sortir amb CER 1,17 i resulta que llegia bé les nostres paraules.
#
# Això és la lliçó del projecte escrita en codi: abans de creure's un número, comprova que les
# dues bandes parlen el mateix idioma.

#: El tifinag passat a llatí, per poder comparar amb els models que escriuen en llatí.
#: Surt de `backend/transliteration.py`; aquí va a mà perquè el quadern ha de ser autònom.
TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
#: I el llatí, plegat a les mateixes lletres: els models escriuen `gh`/`ɣ`, `ch`/`š`, `3`/`ɛ`…
#: Sense plegar-ho, la mateixa paraula escrita per dues mans compta com a error.
PLEGA = {"ɣ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "ṛ": "r",
         "š": "c", "ž": "j", "ǧ": "j", "e": "", "'": "", "’": ""}

def net(t):
    """Totes dues bandes reduïdes a la mateixa forma: lletres llatines plegades, i prou."""
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

def cer(parelles):
    d = sum(distancia(net(r), net(h)) for r, h in parelles)
    n = sum(len(net(r)) for r, h in parelles)
    return d / max(1, n)

# %%
# Els resultats, model per model. Si un no es pot carregar, es diu i es continua: val més
# tenir tres números de quatre models que cap.
resultats = {}
for model_id, mena in MODELS:
    print("\n=== %s (%s)" % (model_id, mena), flush=True)
    try:
        if mena == "nemo":
            from nemo.collections.asr.models import ASRModel
            m = ASRModel.from_pretrained(model_name=model_id)
            def digues(camins):
                return [str(x) for x in m.transcribe(camins, batch_size=8, verbose=False)]
        else:
            import torch
            from transformers import AutoProcessor, AutoModelForCTC
            import soundfile as sf
            import librosa
            proc = AutoProcessor.from_pretrained(model_id)
            mod = AutoModelForCTC.from_pretrained(model_id)
            mod = mod.to("cuda" if torch.cuda.is_available() else "cpu").eval()
            def digues(camins):
                fora = []
                for c in camins:
                    ona, _ = librosa.load(c, sr=16000, mono=True)
                    ent = proc(ona, sampling_rate=16000, return_tensors="pt").to(mod.device)
                    with torch.no_grad():
                        ids = mod(**ent).logits.argmax(-1)
                    fora.append(proc.batch_decode(ids)[0])
                return fora
    except Exception as e:
        print("   no s'ha pogut carregar: %s" % e)
        resultats[model_id] = {"error": str(e)[:200]}
        continue

    tanda = prova[:QUANTS] if QUANTS else prova
    camins = [os.path.join(carpeta, "audio", f["audio"]) for f in tanda]
    camins = [c for c in camins if os.path.exists(c)]
    dits = digues(camins)
    parelles = [(f["text"], h) for f, h in zip(tanda, dits)]
    resultats[model_id] = {
        "talls": len(parelles),
        "cer": round(cer(parelles), 4),
        "mostra": [{"ref": r, "dit": h} for r, h in parelles[:5]],
    }
    print("   CER: %.4f sobre %d talls" % (resultats[model_id]["cer"], len(parelles)))

# %%
print("\n=== RESUM (com més baix, millor) ===")
for k, v in sorted(resultats.items(), key=lambda kv: kv[1].get("cer", 9)):
    print("%-48s %s" % (k, v.get("cer", v.get("error", "—"))))

with open("resultats.json", "w", encoding="utf-8") as fh:
    json.dump(resultats, fh, ensure_ascii=False, indent=1)
print("\ndesat a resultats.json")
