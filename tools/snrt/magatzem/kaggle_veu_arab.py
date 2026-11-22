# Via 3: afinar Whisper perque, sentint amazic, escrigui ARAB. Sense text amazic pel mig.
#
# D'on surt: del tifinag escrit es tradueix a chrF 0,319 i del que sent l'orella a 0,131 --
# la cadena multiplica errors. Pero el so i l'arab de la pantalla estan alineats, aixi que es
# pot anar de l'un a l'altre directament i l'error de l'orella no hi entra.
#
# I el que la fa valuosa: **no necessita tifinag**. A mes de les 48 h de Tadfi hi caben les
# 67 h de programes amb subtitol nomes en arab, que per a l'orella no servien de res.
#
# Punt de partida mesurat a casa amb Whisper small tal qual (40 clips): chrF 0,1003 -- el que
# fa es **transcriure el so amazic amb lletres arabs** (escriu `أزول` per «azul»), no traduir.
# El numero del text (tifinag -> arab, NLLB sense afinar) es 0,2614 sobre el mateix test.
#
# Particio pels MATEIXOS capitols que el corpus de text, perque els dos experiments es puguin
# comparar: train 10.684 talls (12,7 h) · dev 892 (1,2 h) · test 1.850 (2,7 h).
#
# El truc per fer traduccio amb Whisper: se li posa el prompt de l'arab (`language="ar"`,
# tasca `transcribe`) i la diana es la **traduccio** arab. El model aprèn a mapar so amazic ->
# text arab, que no es la seva tasca original pero si una que la seva arquitectura admet.

MODEL = "openai/whisper-small"
LLENGUA, TASCA = "ar", "transcribe"
RITME = 1e-5
EPOQUES = 3
LOT = 8
ACUMULA = 2
DADES = None   #: el busca _troba(), que el camí de Kaggle canvia
FORA = "/kaggle/working"

import os, subprocess, sys, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44,<5", "accelerate", "soundfile", "librosa", "evaluate"],
               check=False)

import io, json, random
import numpy as np
import soundfile as sf
import torch


def _troba(nom):
    """On ha muntat Kaggle el conjunt que conte `nom`.

    El cami ha canviat (abans /kaggle/input/<conjunt>, ara
    /kaggle/input/datasets/<usuari>/<conjunt>) i un cami escrit a ma es trenca cada vegada.
    Es busca la carpeta que contingui el fitxer.
    """
    import os
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return arrel
    raise FileNotFoundError(f"no trobo cap carpeta amb {nom} sota /kaggle/input")


DADES = _troba("train.jsonl")
print("dades a", DADES)
from transformers import (WhisperForConditionalGeneration, WhisperProcessor,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)


def llegeix(nom):
    return [json.loads(l) for l in io.open(f"{DADES}/{nom}.jsonl", encoding="utf-8") if l.strip()]


train, dev, test = llegeix("train"), llegeix("dev"), llegeix("test")
print(f"train {len(train)} · dev {len(dev)} · test {len(test)}", flush=True)

proc = WhisperProcessor.from_pretrained(MODEL, language=LLENGUA, task=TASCA)
model = WhisperForConditionalGeneration.from_pretrained(MODEL).cuda()
model.generation_config.language = LLENGUA
model.generation_config.task = TASCA
model.generation_config.forced_decoder_ids = None


def chrf(hip, ref, n=6, beta=2.0):
    from collections import Counter

    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        ch, cr = Counter(h), Counter(r)
        com = sum((ch & cr).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def so(nom):
    d, sr = sf.read(f"{DADES}/so/{nom}", dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    if sr != 16000:
        n = int(len(d) * 16000 / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype("float32")
    return d


class Joc(torch.utils.data.Dataset):
    def __init__(self, files):
        self.f = files

    def __len__(self):
        return len(self.f)

    def __getitem__(self, i):
        x = self.f[i]
        e = proc.feature_extractor(so(x["so"]), sampling_rate=16000).input_features[0]
        lab = proc.tokenizer(x["ar"], max_length=180, truncation=True).input_ids
        return {"input_features": e, "labels": lab}


def plega(lot):
    feats = torch.tensor(np.stack([x["input_features"] for x in lot]))
    etiq = proc.tokenizer.pad([{"input_ids": x["labels"]} for x in lot], return_tensors="pt")
    lab = etiq["input_ids"].masked_fill(etiq.attention_mask.ne(1), -100)
    if (lab[:, 0] == proc.tokenizer.convert_tokens_to_ids("<|startoftranscript|>")).all():
        lab = lab[:, 1:]
    return {"input_features": feats, "labels": lab}


def puntua(files, nom, lot=16):
    model.eval()
    hip = []
    with torch.no_grad():
        for i in range(0, len(files), lot):
            b = files[i:i + lot]
            f = proc.feature_extractor([so(x["so"]) for x in b], sampling_rate=16000,
                                       return_tensors="pt").input_features.cuda().half()
            g = model.half().generate(f, max_new_tokens=180, num_beams=4)
            hip += proc.batch_decode(g, skip_special_tokens=True)
            model.float()
    cs = [chrf(h.strip(), x["ar"]) for h, x in zip(hip, files)]
    m = sum(cs) / len(cs)
    print(f"   {nom}: chrF {m:.4f} · >=0,5 {sum(1 for c in cs if c >= .5)}/{len(cs)}", flush=True)
    model.train()
    return m, hip


print("\n== abans d'entrenar ==", flush=True)
millor, _ = puntua(dev[:200], "dev (200)")

args = Seq2SeqTrainingArguments(
    output_dir=f"{FORA}/ck", per_device_train_batch_size=LOT,
    gradient_accumulation_steps=ACUMULA, learning_rate=RITME, num_train_epochs=1,
    warmup_steps=200, logging_steps=50, save_strategy="no", fp16=True, report_to=[],
    remove_unused_columns=False, dataloader_num_workers=2)

historia = []
for ep in range(1, EPOQUES + 1):
    tr = Seq2SeqTrainer(model=model, args=args, train_dataset=Joc(train), data_collator=plega)
    tr.train()
    print(f"\n== època {ep} ==", flush=True)
    m, _ = puntua(dev[:200], "dev (200)")
    historia.append({"epoca": ep, "dev_chrf": m})
    if m > millor:
        millor = m
        model.save_pretrained(f"{FORA}/millor", safe_serialization=True)
        proc.save_pretrained(f"{FORA}/millor")
        print(f"   -> desat (millor dev: {m:.4f})", flush=True)

if not os.path.exists(f"{FORA}/millor"):
    model.save_pretrained(f"{FORA}/millor", safe_serialization=True)
    proc.save_pretrained(f"{FORA}/millor")
model = WhisperForConditionalGeneration.from_pretrained(f"{FORA}/millor").cuda()
model.generation_config.language = LLENGUA
model.generation_config.task = TASCA
model.generation_config.forced_decoder_ids = None
mt, ht = puntua(test, "TEST")
json.dump({"dev": historia, "millor_dev": millor, "test_chrf": mt,
           "test": [{"so": x["so"], "ar": x["ar"], "model": h, "capitol": x["capitol"],
                     "zgh": x.get("zgh", "")} for x, h in zip(test, ht)]},
          io.open(f"{FORA}/resultat.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nTEST chrF {mt:.4f} (punt de partida 0,1003 · el text fa 0,2614)")
