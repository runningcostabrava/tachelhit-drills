"""Dir-li al model de quina zona és la veu, i veure si llegeix millor

## La pregunta

El mateix model fa 0,1883 a Beni Mellal i 0,3281 fora. La varietat importa. ¿Milloraria si li
diguéssim de quina zona és cada gravació?

## Per què la manera òbvia no serveix

A un model tipus Whisper se li posa una etiqueta de llengua al davant del text i prou. El nostre
és **CTC**, i el CTC exigeix que cada símbol que surt estigui alineat amb un tros d'àudio. Una
etiqueta de zona no sona enlloc: posar-la al text trencaria l'alineació i el model sortiria
pitjor. Si ho féssim així i anés malament, conclouríem que la zona no serveix quan el que no
serveix és la manera d'injectar-la.

## Com es fa aquí

Un **vector après per zona** que se suma a l'estat intern just abans de la capa que tria les
lletres. Quatre vectors (beni-mellal, taixelhit, ait-mraw, estàndard) de la mida de l'estat
intern. No toca l'alineació perquè és el mateix vector a cada passa de temps: només desplaça el
que el model espera sentir.

És el canvi més petit que pot respondre la pregunta. Si no serveix amb això, tampoc servirà amb
res més gran, i ens haurem estalviat la passada.

## El que es mesura

El mateix test, les mateixes particions i la mateixa distància que les altres passades, perquè
els números es puguin posar al costat:

    el nostre v3 (sense zona)   test-dins 0,1883   test-fora 0,3281
    mms-1b-all sense afinar     test-dins 0,2894   test-fora 0,3452

I **dues** mesures de la passada nova, que diuen coses diferents:

  · **amb la zona de debò** — el sostre: què es guanya si algú sap d'on és la veu;
  · **amb la zona que endevina un classificador** — el que de debò tindrem amb un vídeo nou.

Si el primer millora i el segon no, el que falta és el classificador, no la idea.

## I una trampa que s'ha de dir

**Les nostres etiquetes de varietat diuen d'on vam treure el fitxer, no qui parla.**
`beni-mellal` vol dir «això venia del recull de Beni Mellal». Un classificador entrenat amb
això pot aprendre a reconèixer micròfons i veus en comptes de dialectes i semblar que encerta.
Per això el classificador es mesura **sobre les particions de prova**, on les fonts no han
entrenat, i no sobre una mostra apartada a l'atzar.
"""

# %%
BASE = "TutlaytAI/wav2vec2-berber"
EPOQUES = 8
LOT = 8
RITME = 1e-4
SEGONS_MAXIM = 14
QUANTS = 0

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

import librosa
import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModelForCTC, AutoProcessor


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
files = [f for f in files if f["lletra"] and os.path.exists(f["cami"])]
if QUANTS:
    files = files[:QUANTS]

ZONES = sorted(set(f["varietat"] for f in files))
Z_NUM = {z: i for i, z in enumerate(ZONES)}
print("zones: %s" % ", ".join("%s(%d)" % (z, sum(1 for f in files if f["varietat"] == z))
                              for z in ZONES))

train = [f for f in files if f["split"] == "train"]
dev = [f for f in files if f["split"].startswith("dev")]
proves = {s: [f for f in files if f["split"] == s]
          for s in ("test-dins", "test-fora", "test-mtnra")}

proc = AutoProcessor.from_pretrained(BASE)
base = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean",
                                       pad_token_id=proc.tokenizer.pad_token_id)
base.freeze_feature_encoder()
base.gradient_checkpointing_enable()


# %%
class AmbZona(nn.Module):
    """El model de sempre, més un vector per zona que se suma abans de triar les lletres.

    El vector és el MATEIX a totes les passes de temps, de manera que no mou l'alineació del
    CTC: només desplaça el que el model espera sentir. Comença a zero, així que a l'inici
    aquest model és exactament el de sempre i tot el que guanyi serà de la zona.
    """

    def __init__(self, dins, zones):
        super().__init__()
        self.dins = dins
        amagat = dins.config.hidden_size
        self.zona = nn.Embedding(zones, amagat)
        nn.init.zeros_(self.zona.weight)

    def forward(self, input_values, attention_mask=None, labels=None, zona=None):
        sortida = self.dins.wav2vec2(input_values, attention_mask=attention_mask)
        h = self.dins.dropout(sortida[0])
        if zona is not None:
            h = h + self.zona(zona).unsqueeze(1)
        logits = self.dins.lm_head(h)
        perdua = None
        if labels is not None:
            llargs = torch.full((logits.shape[0],), logits.shape[1], dtype=torch.long,
                                device=logits.device)
            marca = labels >= 0
            perdua = nn.functional.ctc_loss(
                logits.log_softmax(-1).transpose(0, 1), labels.masked_select(marca),
                llargs, marca.sum(-1), blank=self.dins.config.pad_token_id,
                reduction="mean", zero_infinity=True)
        return perdua, logits


model = AmbZona(base, len(ZONES))
aparell = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(aparell)
print("vectors de zona: %d x %d" % (len(ZONES), base.config.hidden_size))


def carrega(f):
    ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
    return ona[:int(SEGONS_MAXIM * 16000)]


class Talls(torch.utils.data.Dataset):
    def __init__(self, g):
        self.g = g

    def __len__(self):
        return len(self.g)

    def __getitem__(self, i):
        f = self.g[i]
        x = proc(carrega(f), sampling_rate=16000).input_values[0]
        y = proc.tokenizer(f["lletra"]).input_ids
        return {"x": x, "y": y, "z": Z_NUM[f["varietat"]]}


def ajunta(lot):
    x = proc.pad([{"input_values": b["x"]} for b in lot], padding=True, return_tensors="pt")
    y = proc.tokenizer.pad([{"input_ids": b["y"]} for b in lot], padding=True,
                           return_tensors="pt")
    return (x["input_values"], x.get("attention_mask"),
            y["input_ids"].masked_fill(y.attention_mask.ne(1), -100),
            torch.tensor([b["z"] for b in lot], dtype=torch.long))


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
opt = torch.optim.AdamW(model.parameters(), lr=RITME, weight_decay=1e-4)
carrega_train = torch.utils.data.DataLoader(Talls(train), batch_size=LOT, shuffle=True,
                                            collate_fn=ajunta, num_workers=2, drop_last=True)
passes = EPOQUES * len(carrega_train)
pla = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=RITME, total_steps=passes, pct_start=0.1)
escala = torch.amp.GradScaler("cuda", enabled=torch.cuda.is_available())

print("\nentrenant amb %d frases" % len(train))
model.train()
for ep in range(EPOQUES):
    suma, n = 0.0, 0
    for x, m, y, z in carrega_train:
        x, y, z = x.to(aparell), y.to(aparell), z.to(aparell)
        m = m.to(aparell) if m is not None else None
        with torch.amp.autocast("cuda", enabled=torch.cuda.is_available()):
            perdua, _ = model(x, attention_mask=m, labels=y, zona=z)
        opt.zero_grad()
        escala.scale(perdua).backward()
        escala.unscale_(opt)
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        escala.step(opt)
        escala.update()
        pla.step()
        suma += float(perdua)
        n += 1
    print("  època %d · pèrdua %.3f" % (ep + 1, suma / max(1, n)), flush=True)

torch.save({"zona": model.zona.state_dict(), "zones": ZONES},
           "/kaggle/working/vectors_de_zona.pt")
model.dins.save_pretrained("/kaggle/working/amb_zona")
proc.save_pretrained("/kaggle/working/amb_zona")
print("desat")


# %%
def llegeix(f, z):
    ent = proc(carrega(f), sampling_rate=16000, return_tensors="pt")
    x = ent.input_values.to(aparell)
    zz = torch.tensor([z], dtype=torch.long, device=aparell) if z is not None else None
    with torch.no_grad():
        _, logits = model(x, zona=zz)
    return proc.batch_decode(logits.argmax(-1))[0].strip()


model.eval()
print("\n=== CER ===")
print("%-12s %-14s %-14s %-14s" % ("", "zona de debò", "sense zona", "zona equivocada"))
taula = {}
for nom, g in proves.items():
    if not g:
        continue
    fila = {}
    for com in ("certa", "cap", "falsa"):
        d = n = 0
        for f in g:
            z = Z_NUM[f["varietat"]]
            if com == "cap":
                z = None
            elif com == "falsa":
                z = (z + 1) % len(ZONES)
            try:
                dit = llegeix(f, z)
            except Exception:
                continue
            d += distancia(f["lletra"], dit)
            n += len(f["lletra"])
        fila[com] = d / max(1, n)
    taula[nom] = fila
    print("%-12s %-14.4f %-14.4f %-14.4f" % (nom, fila["certa"], fila["cap"], fila["falsa"]))

print("\n=== per comparar, les passades d'abans sobre LES MATEIXES frases ===")
print("  el nostre v3 (sense zona)    test-dins 0.1883  test-fora 0.3281  test-mtnra 0.0841")
print("  mms-1b-all sense afinar      test-dins 0.2894  test-fora 0.3452  test-mtnra 0.2170")
print("  mms-1b-all afinat            test-dins 0.3295  test-fora 0.4027  test-mtnra 0.1423")

print("\ncom s'ha de llegir:")
print("  «zona de debò» és el SOSTRE: què es guanya si algú sap d'on és la veu.")
print("  «zona equivocada» diu si el vector fa res: si dona igual que la certa, no fa res.")
print("  i cap dels dos no és el que tindrem amb un vídeo nou, on la zona l'haurà")
print("  d'endevinar un classificador. Això és la passada següent.")

json.dump({"zones": ZONES, "taula": taula},
          open("/kaggle/working/zona.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
