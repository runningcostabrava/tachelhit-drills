# Via 3: afinar Whisper perque, sentint amazic, escrigui ARAB. Sense text amazic pel mig.
#
# D'on surt: del tifinag escrit es tradueix a chrF 0,319 i del que sent l'orella a 0,131 --
# la cadena multiplica errors. Pero hi ha so amazic aparellat amb l'arab que en diu el
# significat, aixi que es pot anar de l'un a l'altre directament.
#
# EL MATERIAL (DESXIFRAT §51) -- ja no es nomes la SNRT:
#   train        15.427 files · 21,4 h   (SNRT 6.069 + TutlAit 9.358)
#   dev           1.972 files ·  2,2 h
#   test_snrt     2.091 files ·  2,8 h   comparable amb la via del text (0,2614 sense afinar)
#   test_tutlait    547 files ·  0,8 h   comparable amb l'article del TutlAit
# El munta `corpus_veu_arab_combinat.py`: particio per capitol (SNRT) i per parlant (TutlAit),
# i 1.395 files tretes de l'entrenament perque el seu arab sortia en algun dev o test.
#
# Punt de partida mesurat a casa amb Whisper small tal qual (40 clips de la SNRT): chrF 0,1003
# -- transcriu el so amazic amb lletres arabs (escriu `أزول` per «azul»), no tradueix. Aqui es
# torna a mesurar abans d'entrenar, als dos tests, perque el del TutlAit no s'ha mesurat mai.
#
# Tres conjunts de dades de Kaggle, i el quadern els troba sols (el cami de Kaggle canvia):
#   josepabloucr/veu-ar-combinat   els quatre manifests
#   josepabloucr/snrt-veu-ar       el so de la SNRT (carpeta so/, .wav)
#   josepabloucr/tutlait-veu-ar    el so del TutlAit (.flac)
#
# El truc per fer traduccio amb Whisper: prompt de l'arab (`language="ar"`, tasca
# `transcribe`) i la diana es la **traduccio** arab. El model apren a mapar so amazic -> text
# arab, que no es la seva tasca original pero si una que la seva arquitectura admet.

MODEL = "openai/whisper-small"
LLENGUA, TASCA = "ar", "transcribe"
RITME = 1e-5
EPOQUES = 3
LOT = 8
ACUMULA = 2
FORA = "/kaggle/working"

import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44,<5", "accelerate", "soundfile", "librosa", "evaluate"],
               check=False)

import io, json
import numpy as np
import soundfile as sf
import torch

#: on es cada cosa. Es busca pel NOM del fitxer, no pel cami: Kaggle ha canviat on munta els
#: conjunts (/kaggle/input/<conjunt> -> /kaggle/input/datasets/<usuari>/<conjunt>) i un cami
#: escrit a ma es trenca cada vegada. `test_tutlait.jsonl` nomes es al conjunt combinat, que
#: el conjunt vell de la SNRT tambe porta un train.jsonl i s'hi confondria.
DADES, ON = None, {}
for arrel, _, fitxers in os.walk("/kaggle/input"):
    if "test_tutlait.jsonl" in fitxers:
        DADES = arrel
    for f in fitxers:
        if f.endswith((".wav", ".flac")):
            ON[f] = os.path.join(arrel, f)
assert DADES, "no trobo test_tutlait.jsonl: falta el conjunt josepabloucr/veu-ar-combinat"
print(f"manifests a {DADES} · {len(ON)} fitxers de so trobats", flush=True)

from transformers import (WhisperForConditionalGeneration, WhisperProcessor,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)


def llegeix(nom):
    files = [json.loads(l) for l in io.open(f"{DADES}/{nom}.jsonl", encoding="utf-8")
             if l.strip()]
    hi_son = [x for x in files if x["so"] in ON]
    #: si falta so, es diu i es para: entrenar amb mig corpus sense saber-ho es pitjor que
    #: no entrenar (un conjunt de dades que no s'ha adjuntat faria exactament aixo)
    falten = len(files) - len(hi_son)
    print(f"   {nom}: {len(files)} files · sense so {falten}", flush=True)
    assert falten <= len(files) * 0.01, (
        f"{nom}: falten {falten} fitxers de so -- comprova que els tres conjunts son adjunts")
    return hi_son


train, dev = llegeix("train"), llegeix("dev")
tests = {"test_snrt": llegeix("test_snrt"), "test_tutlait": llegeix("test_tutlait")}

proc = WhisperProcessor.from_pretrained(MODEL, language=LLENGUA, task=TASCA)
model = WhisperForConditionalGeneration.from_pretrained(MODEL).cuda()


def prepara(m):
    m.generation_config.language = LLENGUA
    m.generation_config.task = TASCA
    m.generation_config.forced_decoder_ids = None


prepara(model)


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
    d, sr = sf.read(ON[nom], dtype="float32")
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


#: el dev que tria el punt de control: 200 files de cada font, perque cap de les dues mani
dev_tria = ([x for x in dev if x["font"] == "snrt"][:200]
            + [x for x in dev if x["font"] == "tutlait"][:200])

print("\n== abans d'entrenar ==", flush=True)
abans = {k: puntua(v[:200], f"{k} (200)")[0] for k, v in tests.items()}
millor, _ = puntua(dev_tria, "dev (200+200)")

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
    m, _ = puntua(dev_tria, "dev (200+200)")
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
prepara(model)

print("\n== els tests, sencers, amb el millor punt de control ==", flush=True)
resultat = {"dev": historia, "millor_dev": millor, "abans_200": abans, "tests": {}}
for k, v in tests.items():
    m, h = puntua(v, k.upper())
    resultat["tests"][k] = {
        "chrf": m,
        "files": [{"so": x["so"], "ar": x["ar"], "model": y, "grup": x["grup"],
                   "varietat": x.get("varietat")} for x, y in zip(v, h)]}
json.dump(resultat, io.open(f"{FORA}/resultat.json", "w", encoding="utf-8"),
          ensure_ascii=False)

print("\n== resum ==")
for k in tests:
    print(f"   {k}: abans {abans[k]:.4f} (200 files) -> ara {resultat['tests'][k]['chrf']:.4f}")
print("   referencies: Whisper sense afinar 0,1003 · la via del text sense afinar 0,2614")
