"""Un OCR d'àrab per a subtítols cremats, entrenat amb text fabricat

## Per què i per a què

Els vídeos d'en Baba Ali (i molts altres) porten el significat en àrab cremat a la imatge. El
Qwen2.5-VL el va llegir —2.647 franges en set hores de GPU prestada— i ho fa bé, però a
segons per franja. Per passar «moltíssims vídeos» cal un lector que llegeixi una línia en
mil·lisegons a la CPU. És el mateix camí que l'OCR de tifinag: una CRNN petita amb text
fabricat.

## El que canvia respecte del tifinag

**L'àrab es lliga i va de dreta a esquerra.** Dues coses que el generador ha de respectar:

1. **La forma de les lletres depèn de la posició** (inicial, mitjana, final, aïllada). El
   motor de text de PIL (`raqm`) ho fa sol si se li diu `direction="rtl"`; sense ell, la línia
   sortiria amb lletres soltes que cap subtítol no té.

2. **El CTC llegeix la imatge d'esquerra a dreta**, i en àrab la primera lletra és a la dreta.
   En comptes d'invertir l'etiqueta —que es trenca amb les marques combinades—, **s'inverteix la
   imatge** en mirall, de manera que l'ordre visual coincideixi amb l'ordre del text. El model
   veu àrab emmirallat sempre igual, a l'entrenament i a la lectura; a la lectura s'emmiralla
   la línia abans d'entrar-hi i prou.

## El text és de debò, i el contrast també

2.700 línies d'àrab **escrit per persones**: les traduccions del MTNRA i les de la nostra
biblioteca. **No** s'entrena amb les 904 lectures del Qwen: són de màquina, i serveixen només
de contrast, dient-ne «coincidència amb el Qwen» i mai CER (l'auditoria del 29/10). Les
vocals curtes es treuen a les dues bandes: els subtítols no en porten.

## El que aquest número NO serà

El CER sobre text fabricat és circular: mateixes fonts, fons i augmentació a les dues bandes.
Diu que el model ha après la feina que li hem posat. El número que valdrà és sobre franges de
vídeo de debò, i la primera mesura serà contra el Qwen, com a coincidència.
"""

# %%
ALT = 48
MAX_AMPLE = 800
LOT = 32
EPOQUES = 12
PER_EPOCA = 12000
RITME = 3e-4

# %%
import os
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "pillow"], check=False)
print("instal·lat")

# %%
import glob
import io
import json
import random
import re

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, features

print("raqm (forma de les lletres àrabs): %s" % features.check("raqm"))
if not features.check("raqm"):
    raise SystemExit("sense raqm les lletres surten soltes: no val la pena entrenar")


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


FITXA = de_kaggle("ar_text.json")
if not FITXA:
    raise SystemExit("no trobo ar_text.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
AR = re.compile(r"[؀-ۿ]")
TASHKIL = re.compile(r"[ً-ْـٰ]")
#: Només àrab, espai i puntuació: res de llatí ni de dígits dins de la línia.
NOMES_AR = re.compile(r"^[؀-ۿ\s,.!?:;«»()\-؟،]+$")
TEXT = [TASHKIL.sub("", t).strip() for t in json.load(open(FITXA, encoding="utf-8"))]
TEXT = [t for t in TEXT if t and NOMES_AR.match(t)]


def _font_bona(cami):
    try:
        ImageFont.truetype(cami, 24, layout_engine=ImageFont.Layout.RAQM)
        return True
    except Exception:
        return False


FONTS = [f for f in sorted(glob.glob(os.path.join(ARREL, "fonts", "*"))) if _font_bona(f)]
FONS = sorted(glob.glob(os.path.join(ARREL, "fons", "*.jpg")))
print("fonts: %d · fons: %d · línies: %d" % (len(FONTS), len(FONS), len(TEXT)))

rnd = random.Random(11)
linies = sorted(set(TEXT))
rnd.shuffle(linies)
TALL = int(len(linies) * 0.9)
TRAIN_TXT, TEST_TXT = linies[:TALL], linies[TALL:]
_tr, _te = " | ".join(TRAIN_TXT), " | ".join(TEST_TXT)
TEST_TXT = [t for t in TEST_TXT if t not in _tr]
TRAIN_TXT = [t for t in TRAIN_TXT if t not in _te]
print("línies per entrenar: %d · per provar: %d" % (len(TRAIN_TXT), len(TEST_TXT)))

SIGNES = sorted(set(c for t in linies for c in t))
BUIT = 0
A_NUM = {c: i + 1 for i, c in enumerate(SIGNES)}
A_SIGNE = {i + 1: c for i, c in enumerate(SIGNES)}
print("alfabet: %d símbols" % len(SIGNES))


# %%
def un_text(r, caixa):
    t = r.choice(caixa).strip()
    mots = t.split()
    if len(mots) > 9:
        i = r.randrange(0, len(mots) - 4)
        t = " ".join(mots[i:i + r.randint(3, 9)])
    return t


def un_fons(r, ample, alt):
    for _ in range(4):
        if not FONS:
            break
        try:
            im = Image.open(r.choice(FONS)).convert("RGB")
        except Exception:
            continue
        if im.width < 40 or im.height < 20:
            continue
        w = r.randint(max(20, im.width // 3), im.width)
        h = r.randint(max(10, im.height // 3), im.height)
        x = r.randint(0, im.width - w)
        y = r.randint(0, im.height - h)
        return im.crop((x, y, x + w, y + h)).resize((ample, alt), Image.BILINEAR)
    g = r.randint(0, 255)
    return Image.new("RGB", (ample, alt), (g, g, g))


def una_mostra(r, caixa):
    text = un_text(r, caixa)
    font = ImageFont.truetype(r.choice(FONTS), r.randint(26, 60),
                              layout_engine=ImageFont.Layout.RAQM)
    vora = r.randint(0, 4)
    prova = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    try:
        c = prova.textbbox((0, 0), text, font=font, stroke_width=vora, direction="rtl")
    except Exception:
        return None
    tw, th = c[2] - c[0], c[3] - c[1]
    if tw < 8 or th < 8:
        return None
    mx, my = r.randint(4, 26), r.randint(3, 16)
    im = un_fons(r, tw + 2 * mx, th + 2 * my)
    d = ImageDraw.Draw(im)
    if r.random() < 0.85:
        ct = r.choice([(255, 255, 255), (255, 255, 255), (250, 240, 120), (240, 240, 240)])
        cv = (r.randint(0, 40),) * 3
    else:
        ct, cv = (r.randint(0, 50),) * 3, (r.randint(210, 255),) * 3
    d.text((mx - c[0], my - c[1]), text, font=font, fill=ct, stroke_width=vora,
           stroke_fill=cv, direction="rtl")
    if r.random() < 0.3:
        im = im.rotate(r.uniform(-1.6, 1.6), resample=Image.BILINEAR, fillcolor=(0, 0, 0))
    if r.random() < 0.7:
        f = r.uniform(0.35, 0.9)
        im = im.resize((max(8, int(im.width * f)), max(8, int(im.height * f))),
                       Image.BILINEAR).resize((im.width, im.height), Image.BICUBIC)
    if r.random() < 0.5:
        im = im.filter(ImageFilter.GaussianBlur(r.uniform(0.3, 1.4)))
    if r.random() < 0.5:
        im = ImageEnhance.Brightness(im).enhance(r.uniform(0.6, 1.4))
    if r.random() < 0.5:
        im = ImageEnhance.Contrast(im).enhance(r.uniform(0.5, 1.5))
    if r.random() < 0.7:
        b = io.BytesIO()
        im.save(b, "JPEG", quality=r.randint(18, 75))
        b.seek(0)
        im = Image.open(b).convert("RGB")
    w = max(16, min(MAX_AMPLE, int(im.width * ALT / im.height)))
    im = im.convert("L").resize((w, ALT), Image.BILINEAR)
    #: El mirall: la primera lletra de l'àrab queda a l'esquerra, com l'etiqueta.
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im, text


class Fabrica(torch.utils.data.Dataset):
    def __init__(self, caixa, quants, llavor):
        self.caixa, self.quants, self.llavor = caixa, quants, llavor

    def __len__(self):
        return self.quants

    def __getitem__(self, i):
        r = random.Random(self.llavor * 1000003 + i)
        for _ in range(6):
            m = una_mostra(r, self.caixa)
            if m:
                im, text = m
                x = torch.from_numpy(np.array(im, dtype=np.float32) / 255.0).unsqueeze(0)
                y = torch.tensor([A_NUM[c] for c in text if c in A_NUM], dtype=torch.long)
                if len(y) > 0:
                    return x, y, text
        return torch.zeros(1, ALT, 16), torch.zeros(0, dtype=torch.long), ""


def ajunta(lot):
    lot = [b for b in lot if len(b[1]) > 0]
    if not lot:
        return None
    amples = [b[0].shape[2] for b in lot]
    w = max(amples)
    x = torch.zeros(len(lot), 1, ALT, w)
    for i, b in enumerate(lot):
        x[i, :, :, :b[0].shape[2]] = b[0]
    y = torch.cat([b[1] for b in lot])
    llargs_y = torch.tensor([len(b[1]) for b in lot], dtype=torch.long)
    llargs_x = torch.tensor([max(1, a // 4) for a in amples], dtype=torch.long)
    return x, y, llargs_x, llargs_y, [b[2] for b in lot]


# %%
class CRNN(nn.Module):
    def __init__(self, classes):
        super().__init__()

        def bloc(e, s, pool):
            return nn.Sequential(nn.Conv2d(e, s, 3, 1, 1), nn.BatchNorm2d(s),
                                 nn.ReLU(True), nn.MaxPool2d(pool))

        self.cnn = nn.Sequential(
            bloc(1, 64, (2, 2)), bloc(64, 128, (2, 2)),
            bloc(128, 256, (2, 1)), bloc(256, 256, (2, 1)),
            nn.Conv2d(256, 256, (3, 1)), nn.BatchNorm2d(256), nn.ReLU(True),
        )
        self.rnn = nn.LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True,
                           dropout=0.1)
        self.sortida = nn.Linear(512, classes)

    def forward(self, x):
        h = self.cnn(x).squeeze(2).permute(0, 2, 1)
        h, _ = self.rnn(h)
        return self.sortida(h)


aparell = "cuda" if torch.cuda.is_available() else "cpu"
model = CRNN(len(SIGNES) + 1).to(aparell)
print("paràmetres: %.1f M" % (sum(p.numel() for p in model.parameters()) / 1e6))
ctc = nn.CTCLoss(blank=BUIT, zero_infinity=True)
opt = torch.optim.AdamW(model.parameters(), lr=RITME, weight_decay=1e-4)
passes = EPOQUES * (PER_EPOCA // LOT)
pla = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=RITME, total_steps=passes, pct_start=0.1)


def descodifica(logits, llargs):
    fora = []
    ids = logits.argmax(-1).cpu().numpy()
    for fila, n in zip(ids, llargs.cpu().numpy()):
        ant, lletres = -1, []
        for k in fila[:n]:
            if k != ant and k != BUIT:
                lletres.append(A_SIGNE.get(int(k), ""))
            ant = k
        fora.append("".join(lletres))
    return fora


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
prova = torch.utils.data.DataLoader(Fabrica(TEST_TXT, 1200, 999), batch_size=LOT,
                                    collate_fn=ajunta, num_workers=2)


def mesura():
    model.eval()
    d = n = 0
    exemples = []
    with torch.no_grad():
        for lot in prova:
            if lot is None:
                continue
            x, y, lx, ly, textos = lot
            dits = descodifica(model(x.to(aparell)), lx)
            for r, h in zip(textos, dits):
                d += distancia(r, h)
                n += len(r)
                if len(exemples) < 6:
                    exemples.append((r, h))
    model.train()
    return d / max(1, n), exemples


print("\nentrenant...")
for ep in range(EPOQUES):
    carrega = torch.utils.data.DataLoader(Fabrica(TRAIN_TXT, PER_EPOCA, ep + 1),
                                          batch_size=LOT, shuffle=False, collate_fn=ajunta,
                                          num_workers=2, drop_last=True)
    suma, quants = 0.0, 0
    for lot in carrega:
        if lot is None:
            continue
        x, y, lx, ly, _ = lot
        sortida = model(x.to(aparell)).log_softmax(-1).permute(1, 0, 2)
        perdua = ctc(sortida, y.to(aparell), lx.to(aparell), ly.to(aparell))
        opt.zero_grad()
        perdua.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        pla.step()
        suma += float(perdua)
        quants += 1
    cer, exemples = mesura()
    print("  època %2d · pèrdua %.3f · CER sobre text NOU (circular) %.4f"
          % (ep + 1, suma / max(1, quants), cer), flush=True)

print("\n--- sis lectures de la prova ---")
for r, h in exemples:
    print("  or : %s" % r[:60])
    print("  dit: %s" % h[:60])

torch.save({"model": model.state_dict(), "signes": SIGNES, "alt": ALT, "mirall": True},
           "/kaggle/working/ocr_arab.pt")
print("\ndesat a ocr_arab.pt (el model espera la línia EMMIRALLADA)")
print("el contrast amb les 904 lectures del Qwen es fa a part, sobre franges de vídeo de debò,")
print("i se'n diu «coincidència amb el Qwen», no CER: el Qwen no és text d'or.")
