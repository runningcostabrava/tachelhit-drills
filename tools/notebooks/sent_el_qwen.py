"""Sent el Qwen l'amazic? La prova, amb talls que ja sabem què diuen

El Gemini s'ha quedat sense crèdit dues vegades aquest mes, i cada vegada tot el que depenia
d'ell s'atura. El Qwen2-Audio està fet per escoltar —no és un model de text amb una orella
postissa— i corre de franc a una GPU qualsevol. Si sent l'amazic prou bé, la feina que avui
paguem per sentir deixa de costar.

**El que no es fa és creure-s'ho.** Es mesura contra el text d'or dels talls de prova del
corpus, els mateixos amb què hem mesurat els altres:

| model | CER | sobre què |
|---|---|---|
| `ayymen/stt_zgh_fastconformer_ctc_small` | **0,134** | amazic estàndard llegit (TOSD) |
| `TutlaytAI/wav2vec2-berber` | **0,370** | tot el nostre corpus, 2.836 talls |
| `facebook/mms-1b-all` | 0,425 | els nostres 143 talls de prova |

Per sota de 0,30 val la pena; per sobre de 0,60 vol dir que no sent la llengua.

**I la trampa de sempre.** El Qwen escriu en lletra llatina i la nostra referència és en tifinag.
Comparar-les tal qual dona un error de gairebé el 100% encara que ho hagi sentit perfectament:
és l'error que ens ha donat quatre mesures falses aquest mes, inclosa la d'aquest mateix quadern
aquest matí (CER 1,17 per a un model que llegia bé les paraules). Aquí es plega tot a la mateixa
forma abans de comparar.

**Per què a Colab i no a Kaggle:** Kaggle ja té les dues sessions ocupades, una llegint l'àrab
cremat amb el Qwen de visió i l'altra mesurant els tres models d'ASR.
"""

# %%
MODEL = "Qwen/Qwen2-Audio-7B-Instruct"
#: Quants talls de prova. Amb 150 n'hi ha prou per distingir 0,3 de 0,6.
QUANTS = 150

# %%
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.48", "accelerate", "librosa", "soundfile",
                "huggingface_hub"], check=False)
import transformers
print("transformers", transformers.__version__)

# %%
import json
import os
import unicodedata


def secret(nom):
    """El token, d'on sigui que l'hagi posat qui corre això."""
    if os.environ.get(nom):
        return os.environ[nom]
    try:                                   # Colab
        from google.colab import userdata
        return userdata.get(nom)
    except Exception:
        pass
    try:                                   # Kaggle
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(nom)
    except Exception:
        pass
    raise SystemExit("falta el secret %s (Colab: el pany de l'esquerra)" % nom)


HF_TOKEN = secret("HF_TOKEN")

TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "ɛ": "a", "ḥ": "h", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "ṛ": "r",
         "š": "c", "ž": "j", "ǧ": "j", "č": "c", "e": "", "'": "", "’": ""}


def net(t):
    """Les dues bandes a la mateixa forma abans de comparar."""
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


# %%
from huggingface_hub import snapshot_download

carpeta = snapshot_download(repo_id="josepabloucr/tamazight-corpus", repo_type="dataset",
                            token=HF_TOKEN)
files = [json.loads(l) for l in open(os.path.join(carpeta, "manifest.jsonl"), encoding="utf-8")
         if l.strip()]
prova = [f for f in files if f.get("split") == "test"][:QUANTS] or files[:QUANTS]
print("talls de prova: %d" % len(prova))

# %%
import librosa
import torch
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

proc = AutoProcessor.from_pretrained(MODEL, token=HF_TOKEN)
model = Qwen2AudioForConditionalGeneration.from_pretrained(
    MODEL, device_map="auto", torch_dtype=torch.float16, token=HF_TOKEN).eval()
print("carregat")

PREGUNTA = ("This audio is one sentence in Tamazight (Berber, Morocco). Write ONLY what is said, "
            "transcribed in Latin letters, with no translation, no explanation and no quotes. "
            "If you cannot hear it clearly, write NOTHING-HEARD.")


def sent(ona):
    conversa = [{"role": "user", "content": [{"type": "audio", "audio_url": "x"},
                                             {"type": "text", "text": PREGUNTA}]}]
    text = proc.apply_chat_template(conversa, add_generation_prompt=True, tokenize=False)
    try:
        ent = proc(text=text, audio=[ona], sampling_rate=16000, return_tensors="pt", padding=True)
    except TypeError:        # segons la versió el camp es diu `audios`
        ent = proc(text=text, audios=[ona], sampling_rate=16000, return_tensors="pt", padding=True)
    ent = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in ent.items()}
    with torch.no_grad():
        fora = model.generate(**ent, max_new_tokens=96, do_sample=False)
    return proc.batch_decode(fora[:, ent["input_ids"].size(1):], skip_special_tokens=True)[0].strip()


# %%
suma_d = suma_n = 0
fallades = 0
sortida = []
for i, f in enumerate(prova, 1):
    cami = os.path.join(carpeta, "audio", f["audio"])
    if not os.path.exists(cami):
        continue
    try:
        ona, _ = librosa.load(cami, sr=16000, mono=True)
        dit = sent(ona)
        fallades = 0
    except Exception as e:
        print("  #%s ha fallat: %s" % (f["id"], str(e)[:90]))
        fallades += 1
        # Una fila buida no és una resposta. Tres fallades seguides volen dir que el problema no
        # és el tall, i val més una cua a mitges que un fitxer de buits que sembla feina feta.
        if fallades >= 3:
            print("tres fallades seguides: m'aturo al %d" % i)
            break
        continue
    r, h = net(f["text"]), net(dit)
    d = distancia(r, h)
    suma_d += d
    suma_n += len(r)
    sortida.append({"id": f["id"], "ref": f["text"], "dit": dit,
                    "cer": round(d / max(1, len(r)), 3), "region": f.get("region")})
    if i <= 6 or i % 25 == 0:
        print("%4d/%d  CER acumulat %.4f   | %s -> %s"
              % (i, len(prova), suma_d / max(1, suma_n), f["text"][:22], dit[:34]))

print("\n=== CER del Qwen sobre els nostres talls: %.4f ===" % (suma_d / max(1, suma_n)))
print("per comparar: NeMo zgh 0,134 (amazic estàndard llegit) · wav2vec2-berber 0,370 (tot el")
print("nostre corpus) · mms-1b-all 0,425. Per sota de 0,30 val la pena; per sobre de 0,60 no")
print("sent la llengua.")
json.dump(sortida, open("lectura_qwen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("desat a lectura_qwen.json")
