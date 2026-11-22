# H-MT1 (#494, 16-11-2026): afinar el NLLB-200-600M de Tamazight-NLP (`…-All-Data-3-epoch`) amb LES NOSTRES
# parelles amazic → català (parlants propis + traduccions confirmades per dos auditors; 4.710 de train, 200 de
# test-dins reservades amb llavor 1114, i les 60 frases de sempre a part). Mesura ABANS i DESPRÉS, amb la mateixa
# funció i els mateixos paràmetres de generació que el peó del 16-11 (feix 4, repetition_penalty 1,1, 96 fitxes):
#   tzm_Tfng → cat_Latn (català directe)   i   tzm_Tfng → eng_Latn (el pont; el tram en→ca es fa a casa amb deepseek-chat)
# sobre les 60 i les 200, abans i després de cada època. v2 (nit del 16-11): el train és NET de fuites (cap parella amb
# el mateix amazic o català que la mostra o el test; 4.609 parelles); la v1 (4.710, 12/60 i 8/200 frases repetides a
# train) va provar dos ritmes i 3e-5 guanyava clar. Desa les sortides
# (JSON per frase) i els pesos afinats del millor ritme (fp16, safetensors) com a sortida del nucli.
# El chrF d'aquí dins és orientatiu (català directe); el que mana és el de casa (compara.py: neteja + chrf).

MODEL = "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch"
ORIGEN, CATALA, ANGLES = "tzm_Tfng", "cat_Latn", "eng_Latn"
RITMES = [3e-5]        # v1 (amb fuita) va provar 3e-5 i 1e-5: 3e-5 guanya clar; v2 només repeteix el bo amb el train net
EPOQUES = 3
LOT = 8
ACUMULA = 2
DEV = 150            # un tros de train per mirar la pèrdua; no és cap test
MAX_FITXES = 128

import os, subprocess, sys, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44,<5", "sentencepiece", "accelerate", "sacremoses"], check=False)

import collections, json, random, re
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
random.Random(1114).shuffle(train_tot)
dev, train = train_tot[:DEV], train_tot[DEV:]
print(f"train {len(train)} · dev {len(dev)} · test200 {len(test200)} · mostra60 {len(m60)}")
PROVES = {"mostra60": m60, "test200": test200}

tok = AutoTokenizer.from_pretrained(MODEL)
tok.src_lang, tok.tgt_lang = ORIGEN, CATALA


def carrega():
    return AutoModelForSeq2SeqLM.from_pretrained(MODEL, torch_dtype=torch.float32).to(APARELL)


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


def avalua(model, etiqueta):
    res = {}
    t0 = time.time()
    for prova, xs in PROVES.items():
        ca = tradueix(model, [x["tifinag"] for x in xs], CATALA)
        en = tradueix(model, [x["tifinag"] for x in xs], ANGLES)
        for x, c, e in zip(xs, ca, en):
            SORTIDES.append({"prova": prova, "id": x["id"], "grup": x.get("grup") or x.get("font"), "amazic": x["tifinag"],
                             "veritat": x["catala"], "model": etiqueta, "ca": c, "en": e})
        sc = [chrf(c, x["catala"]) for x, c in zip(xs, ca)]
        res[prova] = {"n": len(xs), "chrf_ca_directe": round(sum(sc) / len(sc), 4)}
        if prova == "mostra60":
            res[prova]["chrf_shi"] = round(sum(sc[:30]) / 30, 4)
            res[prova]["chrf_beni_mellal"] = round(sum(sc[30:]) / 30, 4)
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


class AvaluaPerEpoca(TrainerCallback):
    def __init__(self, etiqueta, resultats):
        self.etiqueta, self.resultats = etiqueta, resultats

    def on_epoch_end(self, args, state, control, model=None, **kw):
        ep = int(round(state.epoch))
        self.resultats[f"{self.etiqueta}-ep{ep}"] = avalua(model, f"{self.etiqueta}-ep{ep}")
        model.train()


resultats = {}
model = carrega()
print("paràmetres: %.0f M" % (sum(p.numel() for p in model.parameters()) / 1e6))
# comprovació: la fitxa d'origen i les de destí existeixen al vocabulari
for f in (ORIGEN, CATALA, ANGLES):
    assert tok.convert_tokens_to_ids(f) != tok.unk_token_id, f
resultats["abans"] = avalua(model, "abans")
del model
torch.cuda.empty_cache()

millor = None
for ritme in RITMES:
    et = f"lr{ritme:g}"
    model = carrega()
    args = Seq2SeqTrainingArguments(output_dir=f"/kaggle/working/{et}", per_device_train_batch_size=LOT, per_device_eval_batch_size=16,
                                    gradient_accumulation_steps=ACUMULA, num_train_epochs=EPOQUES, learning_rate=ritme,
                                    warmup_ratio=0.05, weight_decay=0.01, lr_scheduler_type="linear",
                                    fp16=APARELL == "cuda", logging_steps=50, eval_strategy="epoch", save_strategy="no",
                                    report_to=[], seed=1114, dataloader_num_workers=2, predict_with_generate=False)
    ent = Seq2SeqTrainer(model=model, args=args, train_dataset=Parelles(train), eval_dataset=Parelles(dev),
                         data_collator=DataCollatorForSeq2Seq(tok, model=model, label_pad_token_id=-100),
                         callbacks=[AvaluaPerEpoca(et, resultats)])
    t0 = time.time()
    ent.train()
    print(et, "entrenat en %.0f s" % (time.time() - t0), "pèrdua dev per època:",
          [round(l["eval_loss"], 4) for l in ent.state.log_history if "eval_loss" in l], flush=True)
    resultats[et + "-perdua_dev"] = [l["eval_loss"] for l in ent.state.log_history if "eval_loss" in l]
    final = resultats[f"{et}-ep{EPOQUES}"]["test200"]["chrf_ca_directe"]   # el millor ritme es tria pel test-DINS, no per les 60
    if millor is None or final > millor[1]:
        millor = (et, final)
        model.half().save_pretrained("/kaggle/working/model_afinat", safe_serialization=True)
        tok.save_pretrained("/kaggle/working/model_afinat")
        print("desat", et, "a /kaggle/working/model_afinat", flush=True)
    del model, ent
    torch.cuda.empty_cache()

json.dump({"config": {"model": MODEL, "origen": ORIGEN, "ritmes": RITMES, "epoques": EPOQUES, "lot": LOT * ACUMULA, "train": len(train),
                      "dev": DEV, "millor_ritme_per_test200": millor[0]}, "resultats": resultats},
          open("/kaggle/working/nllb_resultat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(SORTIDES, open("/kaggle/working/nllb_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("fet; millor ritme pel test-dins:", millor)
