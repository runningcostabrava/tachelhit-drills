# Afinar NLLB per traduir TIFINAG -> ARAB amb les parelles de la pantalla del SNRT.
#
# D'on surt la idea (d'en Pablo, 21-11): «la traduccio al catala es important, pero molt mes
# important la traduccio a l'arab, perque si el model es capac de traduir perfectament del
# tifinag a l'arab, despres la traduccio de l'arab al catala es trivial».
#
# Per que es pot fer avui: cada replica del SNRT porta el tifinag i l'arab **cremats al mateix
# fotograma**, aixi que l'alineacio es exacta i gratuita. Hi ha 9.897 parelles que passen les
# portes de la fabrica, i el cataleg te 215 capitols: si s'acaba Tadfi seran ~107.000.
#
# El punt de partida (mesurat a casa, model afinat per al CATALA al qual se li demana arab):
# chrF 0,266 sobre una mostra. El numero a batre es el del test sencer, que es mesura a casa.
#
# Particio **per CAPITOLS**, no per linies: dues linies del mateix capitol comparteixen tema,
# convidat i vocabulari, i partir per linies posaria el mateix convidat als dos costats.
#   train 7.194 (21 capitols) · dev 861 (2) · test 1.682 (4) · cap text del test al train.
#
# Es desa el checkpoint amb millor chrF de DEV, no l'ultim, i es converteix a CTranslate2 int8
# dins del nucli perque a casa es pugui fer servir igual que l'actual.

MODEL = "Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch"
ORIGEN, DESTI = "zgh_Tfng", "arb_Arab"
RITME = 5e-5
EPOQUES = 5
LOT = 8
ACUMULA = 2
MAX_FITXES = 128
DADES = None   #: el busca _troba(), que el camí de Kaggle canvia
FORA = "/kaggle/working"

import os, subprocess, sys, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44,<5", "sentencepiece", "accelerate", "ctranslate2"], check=False)

import io, json, math, random, shutil
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
from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)


def llegeix(nom):
    return [json.loads(l) for l in io.open(f"{DADES}/{nom}.jsonl", encoding="utf-8") if l.strip()]


train, dev, test = llegeix("train"), llegeix("dev"), llegeix("test")
print(f"train {len(train)} · dev {len(dev)} · test {len(test)}", flush=True)

tok = AutoTokenizer.from_pretrained(MODEL, src_lang=ORIGEN, tgt_lang=DESTI)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL).cuda()


def chrf(hip, ref, n=6, beta=2.0):
    """chrF com el de casa, perque els numeros siguin comparables."""
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        from collections import Counter
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


class Joc(torch.utils.data.Dataset):
    def __init__(self, files):
        self.f = files

    def __len__(self):
        return len(self.f)

    def __getitem__(self, i):
        x = self.f[i]
        d = tok(x["zgh"], text_target=x["ar"], max_length=MAX_FITXES, truncation=True)
        return d


def tradueix(files, lot=16):
    model.eval()
    fora = []
    bos = tok.convert_tokens_to_ids(DESTI)
    with torch.no_grad():
        for i in range(0, len(files), lot):
            b = [x["zgh"] for x in files[i:i + lot]]
            e = tok(b, return_tensors="pt", padding=True, truncation=True,
                    max_length=MAX_FITXES).to("cuda")
            g = model.generate(**e, forced_bos_token_id=bos, num_beams=4,
                               max_new_tokens=MAX_FITXES, repetition_penalty=1.1)
            fora += tok.batch_decode(g, skip_special_tokens=True)
    model.train()
    return fora


def puntua(files, nom):
    h = tradueix(files)
    cs = [chrf(a, x["ar"]) for a, x in zip(h, files)]
    m = sum(cs) / len(cs)
    print(f"   {nom}: chrF {m:.4f} · >=0,5 {sum(1 for c in cs if c >= .5)}/{len(cs)}", flush=True)
    return m, h


print("\n== abans d'entrenar ==", flush=True)
millor, _ = puntua(dev, "dev")
torch.save({"chrf": millor}, f"{FORA}/dev_abans.pt")

args = Seq2SeqTrainingArguments(
    output_dir=f"{FORA}/ck", per_device_train_batch_size=LOT,
    gradient_accumulation_steps=ACUMULA, learning_rate=RITME, num_train_epochs=1,
    logging_steps=50, save_strategy="no", fp16=True, report_to=[])

historia = []
for ep in range(1, EPOQUES + 1):
    tr = Seq2SeqTrainer(model=model, args=args, train_dataset=Joc(train),
                        data_collator=DataCollatorForSeq2Seq(tok, model=model))
    tr.train()
    print(f"\n== època {ep} ==", flush=True)
    m, _ = puntua(dev, "dev")
    historia.append({"epoca": ep, "dev_chrf": m})
    if m > millor:
        millor = m
        model.save_pretrained(f"{FORA}/millor", safe_serialization=True)
        tok.save_pretrained(f"{FORA}/millor")
        print(f"   -> desat (millor dev fins ara: {m:.4f})", flush=True)

print(f"\nmillor dev: {millor:.4f}")
if not os.path.exists(f"{FORA}/millor"):
    model.save_pretrained(f"{FORA}/millor", safe_serialization=True)
    tok.save_pretrained(f"{FORA}/millor")

#: el test, UNA sola vegada i amb el millor
model = AutoModelForSeq2SeqLM.from_pretrained(f"{FORA}/millor").cuda()
tok = AutoTokenizer.from_pretrained(f"{FORA}/millor", src_lang=ORIGEN, tgt_lang=DESTI)
mt, ht = puntua(test, "TEST")
json.dump({"dev": historia, "millor_dev": millor, "test_chrf": mt,
           "test": [{"zgh": x["zgh"], "ar": x["ar"], "model": h, "capitol": x["capitol"]}
                    for x, h in zip(test, ht)]},
          io.open(f"{FORA}/resultat.json", "w", encoding="utf-8"), ensure_ascii=False)

subprocess.run([sys.executable, "-m", "ctranslate2.converters.transformers",
                "--model", f"{FORA}/millor", "--output_dir", f"{FORA}/ct2_int8",
                "--quantization", "int8", "--force"], check=False)
shutil.rmtree(f"{FORA}/ck", ignore_errors=True)
print("fet")
