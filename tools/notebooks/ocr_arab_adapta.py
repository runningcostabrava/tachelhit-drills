"""Adaptar l'OCR d'àrab a la lletra del vídeo amb franges reals etiquetades pel Qwen

## El problema, mesurat

L'OCR entrenat amb text fabricat fa 0,0178 de CER sobre text fabricat i **0,19 de coincidència
mediana** amb el Qwen sobre les 904 franges reals d'en Baba Ali. El sostre —el Qwen en color
contra el Qwen en blanc i negre, mateixa franja— és 0,73. El número fabricat no es trasllada:
cap de les 15 tipografies s'assembla prou a la lletra del subtítol.

## El remei, i per què no és el volant prohibit

S'ensenya al model la lletra de debò amb **177 franges reals d'una sola línia** on el Qwen diu
el mateix en color i en blanc i negre (acord ≥ 0,8). L'etiqueta és la del Qwen: no és text
d'or, i se'n diu «coincidència», no CER. Però l'etiqueta ve d'un model **independent i més
fort**, no del nostre: això és destil·lació, no el volant que s'alimenta del que el model ja
encerta.

## Les tres condicions que fan que el número valgui

1. **Partició pel temps, no a l'atzar**: el primer 70 % del vídeo entrena (123 línies),
   l'últim 30 % prova (54). Dues franges consecutives són gairebé la mateixa imatge.
2. **El mateix test abans i després**: la millora es mesura sobre les mateixes 54 línies que el
   model inicial no ha vist mai. Sense l'«abans», un número sol no diu res.
3. **Es barreja amb text fabricat** (la meitat de cada lot): 123 línies soles farien que el
   model oblidés les lletres que no hi surten.

## El que aquest número NO és

Coincidència amb el Qwen sobre un sol vídeo. Diu si el model ha après aquesta lletra, no si
llegeix qualsevol subtítol àrab. El següent vídeo tindrà la seva lletra i la seva prova.
"""

# %%
ALT = 48
MAX_AMPLE = 800
LOT = 32
EPOQUES = 8
PER_EPOCA = 4000
RITME = 8e-5

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

if not features.check("raqm"):
    raise SystemExit("sense raqm les lletres surten soltes")


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


PES = de_kaggle("ocr_arab.pt")
REALS = de_kaggle("reals.json")
FITXA = de_kaggle("ar_text.json")
if not (PES and REALS and FITXA):
    raise SystemExit("falten entrades: pes=%s reals=%s text=%s" % (PES, REALS, FITXA))
ARREL_TXT = os.path.dirname(FITXA)
ARREL_REALS = os.path.dirname(REALS)

estat = torch.load(PES, map_location="cpu")
SIGNES = estat["signes"]
BUIT = 0
A_NUM = {c: i + 1 for i, c in enumerate(SIGNES)}
A_SIGNE = {i + 1: c for i, c in enumerate(SIGNES)}
print("alfabet del model inicial: %d símbols" % len(SIGNES))

TASHKIL = re.compile(r"[ً-ْـٰ]")


def net(t):
    return re.sub(r"\s+", " ", TASHKIL.sub("", t or "")).strip()


reals = json.load(open(REALS, encoding="utf-8"))
for r in reals:
    r["cami"] = os.path.join(ARREL_REALS, "linies", r["fitxer"])
    r["text"] = "".join(c for c in net(r["text"]) if c in A_NUM)
reals = [r for r in reals if r["text"] and os.path.exists(r["cami"])]
R_TRAIN = [r for r in reals if r["split"] == "train"]
R_TEST = [r for r in reals if r["split"] == "test"]
print("franges reals: %d entrenen (primer 70 %% del vídeo) · %d proven (últim 30 %%)"
      % (len(R_TRAIN), len(R_TEST)))

NOMES_AR = re.compile(r"^[؀-ۿ\s,.!?:;«»()\-؟،]+$")
TEXT = [net(t) for t in json.load(open(FITXA, encoding="utf-8"))]
TEXT = [t for t in TEXT if t and NOMES_AR.match(t)]
FONTS = []
for f in sorted(glob.glob(os.path.join(ARREL_TXT, "fonts", "*"))):
    try:
        ImageFont.truetype(f, 24, layout_engine=ImageFont.Layout.RAQM)
        FONTS.append(f)
    except Exception:
        pass
FONS = sorted(glob.glob(os.path.join(ARREL_TXT, "fons", "*.jpg")))
print("fabricat: %d línies · %d fonts · %d fons" % (len(TEXT), len(FONTS), len(FONS)))


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


def fabricada(r):
    text = un_text(r, TEXT)
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
    if r.random() < 0.7:
        f = r.uniform(0.35, 0.9)
        im = im.resize((max(8, int(im.width * f)), max(8, int(im.height * f))),
                       Image.BILINEAR).resize((im.width, im.height), Image.BICUBIC)
    if r.random() < 0.5:
        im = im.filter(ImageFilter.GaussianBlur(r.uniform(0.3, 1.4)))
    if r.random() < 0.5:
        im = ImageEnhance.Contrast(im).enhance(r.uniform(0.5, 1.5))
    if r.random() < 0.7:
        b = io.BytesIO()
        im.save(b, "JPEG", quality=r.randint(18, 75))
        b.seek(0)
        im = Image.open(b).convert("RGB")
    w = max(16, min(MAX_AMPLE, int(im.width * ALT / im.height)))
    return im.convert("L").resize((w, ALT), Image.BILINEAR).transpose(Image.FLIP_LEFT_RIGHT), text


def real(r, fila):
    """Una franja real, amb una mica de soroll perquè 123 no siguin sempre les mateixes 123."""
    im = Image.open(fila["cami"]).convert("L")
    if r.random() < 0.5:
        im = ImageEnhance.Contrast(im).enhance(r.uniform(0.7, 1.3))
    if r.random() < 0.4:
        im = im.filter(ImageFilter.GaussianBlur(r.uniform(0.2, 0.9)))
    if r.random() < 0.4:
        f = r.uniform(0.85, 1.15)
        im = im.resize((max(16, int(im.width * f)), ALT), Image.BILINEAR)
    w = max(16, min(MAX_AMPLE, im.width))
    im = im.resize((w, ALT), Image.BILINEAR).transpose(Image.FLIP_LEFT_RIGHT)
    return im, fila["text"]


class Barreja(torch.utils.data.Dataset):
    """Meitat franges reals (amb soroll), meitat fabricades."""

    def __init__(self, quants, llavor):
        self.quants, self.llavor = quants, llavor

    def __len__(self):
        return self.quants

    def __getitem__(self, i):
        r = random.Random(self.llavor * 1000003 + i)
        for _ in range(6):
            m = real(r, r.choice(R_TRAIN)) if r.random() < 0.5 else fabricada(r)
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
    return (x, y, torch.tensor([max(1, a // 4) for a in amples], dtype=torch.long),
            torch.tensor([len(b[1]) for b in lot], dtype=torch.long), [b[2] for b in lot])


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
model.load_state_dict(estat["model"])


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


def coincidencia_real(grup):
    """Mediana i mitjana de la coincidència amb l'etiqueta del Qwen sobre franges reals."""
    model.eval()
    vals = []
    exemples = []
    with torch.no_grad():
        for fila in grup:
            im = Image.open(fila["cami"]).convert("L")
            w = max(16, min(MAX_AMPLE, im.width))
            im = im.resize((w, ALT), Image.BILINEAR).transpose(Image.FLIP_LEFT_RIGHT)
            x = torch.from_numpy(np.array(im, dtype=np.float32) / 255.0)
            dit = descodifica(model(x.unsqueeze(0).unsqueeze(0).to(aparell)),
                              torch.tensor([w // 4]))[0]
            a, b = fila["text"].replace(" ", ""), dit.replace(" ", "")
            c = 1 - distancia(a, b) / max(1, len(a), len(b))
            vals.append(c)
            if len(exemples) < 4:
                exemples.append((fila["text"], dit, c))
    model.train()
    vals.sort()
    return vals[len(vals) // 2], sum(vals) / max(1, len(vals)), \
        sum(1 for v in vals if v >= 0.7) / max(1, len(vals)), exemples


med0, mit0, bons0, ex0 = coincidencia_real(R_TEST)
print("\n=== ABANS d'adaptar, sobre les %d franges reals de prova ===" % len(R_TEST))
print("  coincidència amb el Qwen: mediana %.3f · mitjana %.3f · >= 0,7: %.0f%%"
      % (med0, mit0, 100 * bons0))

# %%
ctc = nn.CTCLoss(blank=BUIT, zero_infinity=True)
opt = torch.optim.AdamW(model.parameters(), lr=RITME, weight_decay=1e-4)
passes = EPOQUES * (PER_EPOCA // LOT)
pla = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=RITME, total_steps=passes, pct_start=0.15)
model.train()
for ep in range(EPOQUES):
    carrega = torch.utils.data.DataLoader(Barreja(PER_EPOCA, ep + 1), batch_size=LOT,
                                          collate_fn=ajunta, num_workers=2, drop_last=True)
    suma, n = 0.0, 0
    for lot in carrega:
        if lot is None:
            continue
        x, y, lx, ly, _ = lot
        s = model(x.to(aparell)).log_softmax(-1).permute(1, 0, 2)
        p = ctc(s, y.to(aparell), lx.to(aparell), ly.to(aparell))
        opt.zero_grad()
        p.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        pla.step()
        suma += float(p)
        n += 1
    med, mit, bons, _ = coincidencia_real(R_TEST)
    print("  època %d · pèrdua %.3f · prova real: mediana %.3f · mitjana %.3f · >= 0,7: %.0f%%"
          % (ep + 1, suma / max(1, n), med, mit, 100 * bons), flush=True)

med1, mit1, bons1, ex1 = coincidencia_real(R_TEST)
print("\n=== DESPRÉS, sobre les MATEIXES %d franges ===" % len(R_TEST))
print("  abans : mediana %.3f · mitjana %.3f · >= 0,7: %.0f%%" % (med0, mit0, 100 * bons0))
print("  després: mediana %.3f · mitjana %.3f · >= 0,7: %.0f%%" % (med1, mit1, 100 * bons1))
print("  el sostre (Qwen contra Qwen a la mateixa franja) és mediana 0,727")
print("\n--- quatre franges de prova, abans → després ---")
for (t, d0, c0), (_, d1, c1) in zip(ex0, ex1):
    print("  Qwen   : %s" % t[:56])
    print("  abans  : %s  (%.2f)" % (d0[:56], c0))
    print("  després: %s  (%.2f)" % (d1[:56], c1))

torch.save({"model": model.state_dict(), "signes": SIGNES, "alt": ALT, "mirall": True},
           "/kaggle/working/ocr_arab_adaptat.pt")
print("\ndesat a ocr_arab_adaptat.pt")
print("això és coincidència amb el Qwen sobre UN vídeo: diu si ha après aquesta lletra, no si")
print("llegeix qualsevol subtítol àrab.")
