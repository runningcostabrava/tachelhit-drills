# H-MT1 v3 (#494, 16-11-2026, nit): el NLLB-200-600M de Tamazight-NLP (`…-All-Data-3-epoch`) afinat amb les parelles
# pròpies amazic → català, segona tanda. Respecte de la v2 (3e-5, 3 èpoques, 4.609 parelles, chrF 0,571 / 0,425):
#   - train SENSE vocabulari sol (una paraula, IRCAM, glosses «/» «;») i AMB les 302 parelles MTNRA/CV confirmades
#     pels dos auditors del 16-11 (català dels auditors): 3.399 parelles; test-dins IDÈNTIC al de la v2 (200);
#   - ritme 5e-5, 5 èpoques, i es queda el checkpoint amb millor pèrdua de dev (150 parelles de train), no l'últim;
#   - el model final es desa en fp16 i es converteix a CTranslate2 int8 dins del nucli (`ct2_int8/`), i es mesura
#     també l'int8 sobre les 60 i les 200 perquè la conversió no amagui res.
# Mesura com sempre: tzm_Tfng → cat_Latn (directe) i → eng_Latn (pont; el tram en→ca es fa a casa amb deepseek-chat),
# feix 4, repetition_penalty 1,1, 96 fitxes, sobre les 60 i les 200, abans i després de cada època i amb el millor.
# El chrF d'aquí dins és orientatiu; el que mana és el de casa (compara.py: neteja + chrf).

MODEL = "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch"
ORIGEN, CATALA, ANGLES = "tzm_Tfng", "cat_Latn", "eng_Latn"
RITME = 5e-5
EPOQUES = 5
LOT = 8
ACUMULA = 2
DEV = 150            # un tros de train per triar l'època; no és cap test
MAX_FITXES = 128
MILLOR = "/kaggle/working/millor"

import os, subprocess, sys, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44,<5", "sentencepiece", "accelerate", "sacremoses", "ctranslate2"], check=False)

import collections, json, random, re, shutil
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq, Seq2SeqTrainer, Seq2SeqTrainingArguments, TrainerCallback

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
APARELL = "cuda" if torch.cuda.is_available() else "cpu"


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


# ---------------------------------------------------------------- chrF (copiat de compara.py; orientatiu aquí dins)
def neteja(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def ngrams(s, n):
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def chrf(hip, ref, N=6, beta=2.0):
    hip, ref = neteja(hip), neteja(ref)
    if not hip or not ref:
        return 0.0
    P = R = 0.0
    k = 0
    for n in range(1, N + 1):
        h, r = ngrams(hip, n), ngrams(ref, n)
        if not h or not r:
            continue
        comu = sum((h & r).values())
        P += comu / max(1, sum(h.values()))
        R += comu / max(1, sum(r.values()))
        k += 1
    if not k:
        return 0.0
    P, R = P / k, R / k
    if P + R == 0:
        return 0.0
    return (1 + beta ** 2) * P * R / (beta ** 2 * P + R)


# ---------------------------------------------------------------- dades
train_tot = json.load(open(de_kaggle("train.json"), encoding="utf-8"))
test200 = json.load(open(de_kaggle("test200.json"), encoding="utf-8"))
m60 = json.load(open(de_kaggle("mostra60.json"), encoding="utf-8"))
resum = json.load(open(de_kaggle("resum.json"), encoding="utf-8"))
assert resum.get("versio") == "v3" and test200[0]["id"] == 8187, "no és el dataset v3 amb el test de la v2"
random.Random(1114).shuffle(train_tot)
dev, train = train_tot[:DEV], train_tot[DEV:]
print(f"train {len(train)} · dev {len(dev)} · test200 {len(test200)} · mostra60 {len(m60)}")
PROVES = {"mostra60": m60, "test200": test200}

tok = AutoTokenizer.from_pretrained(MODEL)
tok.src_lang, tok.tgt_lang = ORIGEN, CATALA


def carrega(d=MODEL):
    return AutoModelForSeq2SeqLM.from_pretrained(d, torch_dtype=torch.float32).to(APARELL)


@torch.no_grad()
def tradueix(model, textos, dest, lot=16):
    model.eval()
    tok.src_lang = ORIGEN
    bos = tok.convert_tokens_to_ids(dest)
    out = []
    for i in range(0, len(textos), lot):
        enc = tok(textos[i:i + lot], return_tensors="pt", padding=True, truncation=True, max_length=MAX_FITXES).to(APARELL)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=APARELL == "cuda"):
            gen = model.generate(**enc, forced_bos_token_id=bos, max_new_tokens=96, num_beams=4, repetition_penalty=1.1)
        out += [t.strip() for t in tok.batch_decode(gen, skip_special_tokens=True)]
    return out


SORTIDES = []   # una entrada per frase, prova, model (etiqueta) i destí


def desa_sortides(prova, xs, ca, en, etiqueta):
    for x, c, e in zip(xs, ca, en):
        SORTIDES.append({"prova": prova, "id": x["id"], "grup": x.get("grup") or x.get("font"), "amazic": x["tifinag"],
                         "veritat": x["catala"], "model": etiqueta, "ca": c, "en": e})
    sc = [chrf(c, x["catala"]) for x, c in zip(xs, ca)]
    r = {"n": len(xs), "chrf_ca_directe": round(sum(sc) / len(sc), 4)}
    if prova == "mostra60":
        r["chrf_shi"] = round(sum(sc[:30]) / 30, 4)
        r["chrf_beni_mellal"] = round(sum(sc[30:]) / 30, 4)
    return r


def avalua(model, etiqueta):
    res = {}
    t0 = time.time()
    for prova, xs in PROVES.items():
        ca = tradueix(model, [x["tifinag"] for x in xs], CATALA)
        en = tradueix(model, [x["tifinag"] for x in xs], ANGLES)
        res[prova] = desa_sortides(prova, xs, ca, en, etiqueta)
    print(etiqueta, json.dumps(res), f"({time.time() - t0:.0f} s)", flush=True)
    return res


class Parelles(torch.utils.data.Dataset):
    def __init__(self, xs):
        self.xs = xs

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, i):
        x = self.xs[i]
        tok.src_lang, tok.tgt_lang = ORIGEN, CATALA
        enc = tok(x["tifinag"], text_target=x["catala"], truncation=True, max_length=MAX_FITXES)
        return {"input_ids": enc["input_ids"], "attention_mask": enc["attention_mask"], "labels": enc["labels"]}


class PerEpoca(TrainerCallback):
    """Al final de cada època: mesura sobre les 60 i les 200; i quan la pèrdua de dev millora, desa el model a MILLOR."""

    def __init__(self, resultats):
        self.resultats = resultats
        self.millor_perdua, self.millor_epoca = float("inf"), None

    def on_epoch_end(self, args, state, control, model=None, **kw):
        ep = int(round(state.epoch))
        self.resultats[f"ep{ep}"] = avalua(model, f"ep{ep}")
        model.train()

    def on_evaluate(self, args, state, control, model=None, metrics=None, **kw):
        ep = int(round(state.epoch))
        perdua = metrics.get("eval_loss")
        print(f"dev ep{ep}: pèrdua {perdua:.4f}", flush=True)
        if perdua is not None and perdua < self.millor_perdua:
            self.millor_perdua, self.millor_epoca = perdua, ep
            shutil.rmtree(MILLOR, ignore_errors=True)
            model.save_pretrained(MILLOR, safe_serialization=True)
            print(f"  → millor fins ara, desat (ep{ep})", flush=True)


resultats = {}
model = carrega()
print("paràmetres: %.0f M" % (sum(p.numel() for p in model.parameters()) / 1e6))
for f in (ORIGEN, CATALA, ANGLES):
    assert tok.convert_tokens_to_ids(f) != tok.unk_token_id, f
resultats["abans"] = avalua(model, "abans")

args = Seq2SeqTrainingArguments(output_dir="/kaggle/working/entrena", per_device_train_batch_size=LOT, per_device_eval_batch_size=16,
                                gradient_accumulation_steps=ACUMULA, num_train_epochs=EPOQUES, learning_rate=RITME,
                                warmup_ratio=0.05, weight_decay=0.01, lr_scheduler_type="linear",
                                fp16=APARELL == "cuda", logging_steps=50, eval_strategy="epoch", save_strategy="no",
                                report_to=[], seed=1114, dataloader_num_workers=2, predict_with_generate=False)
cb = PerEpoca(resultats)
ent = Seq2SeqTrainer(model=model, args=args, train_dataset=Parelles(train), eval_dataset=Parelles(dev),
                     data_collator=DataCollatorForSeq2Seq(tok, model=model, label_pad_token_id=-100), callbacks=[cb])
t0 = time.time()
ent.train()
perdues = [round(l["eval_loss"], 4) for l in ent.state.log_history if "eval_loss" in l]
print("entrenat en %.0f s" % (time.time() - t0), "pèrdua dev per època:", perdues, "· millor època:", cb.millor_epoca, flush=True)
del model, ent
torch.cuda.empty_cache()

# ---------------------------------------------------------------- el millor checkpoint: mesura, fp16, ct2 int8
model = carrega(MILLOR)
resultats["millor"] = avalua(model, "millor")
model.half().save_pretrained("/kaggle/working/model_afinat", safe_serialization=True)
tok.save_pretrained("/kaggle/working/model_afinat")
shutil.rmtree(MILLOR, ignore_errors=True)
del model
torch.cuda.empty_cache()

conv = subprocess.run(["ct2-transformers-converter", "--model", "/kaggle/working/model_afinat", "--output_dir", "/kaggle/working/ct2_int8",
                       "--quantization", "int8", "--force"], capture_output=True, text=True)
print("ct2:", conv.returncode, (conv.stdout + conv.stderr)[-800:], flush=True)
try:
    import ctranslate2
    tr = ctranslate2.Translator("/kaggle/working/ct2_int8", device=APARELL, compute_type="int8" if APARELL == "cpu" else "int8_float16")

    def tradueix_ct2(textos, dest):
        tok.src_lang = ORIGEN
        fonts = [tok.convert_ids_to_tokens(tok.encode(t)) for t in textos]
        res = tr.translate_batch(fonts, target_prefix=[[dest]] * len(fonts), max_decoding_length=120, beam_size=4, repetition_penalty=1.1, max_batch_size=16)
        return [tok.decode(tok.convert_tokens_to_ids(r.hypotheses[0][1:]), skip_special_tokens=True).strip() for r in res]

    res = {}
    for prova, xs in PROVES.items():
        ca = tradueix_ct2([x["tifinag"] for x in xs], CATALA)
        en = tradueix_ct2([x["tifinag"] for x in xs], ANGLES)
        res[prova] = desa_sortides(prova, xs, ca, en, "millor-ct2int8")
    resultats["millor-ct2int8"] = res
    print("millor-ct2int8", json.dumps(res), flush=True)
    shutil.copy(de_kaggle("sentencepiece.bpe.model") or "/kaggle/working/model_afinat/sentencepiece.bpe.model", "/kaggle/working/ct2_int8/")
except Exception as e:
    print("ct2 no ha pogut mesurar:", repr(e), flush=True)

json.dump({"config": {"model": MODEL, "origen": ORIGEN, "versio": "v3", "ritme": RITME, "epoques": EPOQUES, "lot": LOT * ACUMULA,
                      "train": len(train), "dev": DEV, "perdua_dev": perdues, "millor_epoca": cb.millor_epoca}, "resultats": resultats},
          open("/kaggle/working/nllb_resultat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(SORTIDES, open("/kaggle/working/nllb_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("fet; millor època:", cb.millor_epoca)
