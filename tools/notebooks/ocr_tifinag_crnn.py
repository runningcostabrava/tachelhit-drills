"""Un OCR de tifinag entrenat amb text fabricat

## Per què es pot fer sense imatges etiquetades

El tifinag té 33 signes i el que hem de llegir és **lletra impresa de subtítol**, no manuscrita.
Amb un alfabet tancat i tipografies disponibles, les imatges es poden fabricar: és la manera
estàndard de fer un OCR per a una escriptura que no té milers d'imatges etiquetades, i aquí no
en tenim ni cent.

Cap OCR nostre no ha sabut llegir tifinag fins ara. El Qwen2.5-VL el llegeix però l'escriu amb
lletres que s'assemblen, que per a una biblioteca és pitjor que no llegir-lo: escriu una cosa
que sembla bona i no ho és.

## Les tres decisions que fan que això funcioni o no

**1. El text és de debò.** 2.750 línies de tifinag real —1.801 del MTNRA, 920 lectures del NeMo
i 313 frases de la biblioteca—, no lletres a l'atzar. Les combinacions de signes d'una llengua
no són les d'un generador aleatori, i un model entrenat amb soroll aprèn a llegir signes solts
i no paraules.

**2. Els fons són fotogrames de debò.** 2.500 franges retallades del vídeo d'en Baba Ali i dels
vídeos del Mètode. El que ha de llegir aquest model és lletra damunt de cares, de cel i de
paret, no damunt de blanc.

**3. Les mostres es fabriquen sobre la marxa.** Cada passada en veu de noves: no hi ha un
conjunt fix per memoritzar. Per això aquí no es puja cap imatge, només les fonts, el text i els
fons: 17 MB en comptes de centenars.

## La partició, que és on es fan les trampes sense voler

Es parteix **per línia de text**: les frases que es proven no s'han dibuixat mai durant
l'entrenament, ni amb una altra font ni amb un altre fons. Si es partís per imatge, el model
hauria vist la mateixa frase mil vegades i el número no voldria dir res.

## El que aquest número NO serà

Serà el CER sobre imatges fabricades per mi, amb les meves tres tipografies. **No és el CER
sobre un vídeo de debò.** De text d'or llegit per una persona només en tenim una línia sencera,
i amb això no es mesura un OCR. Quan el model existeixi caldrà que algú llegeixi vint o trenta
franges a mà; fins llavors, aquest número diu que el model ha après la feina que li hem posat,
no que sàpiga llegir el que ens interessa.
"""

# %%
ALT = 48
MAX_AMPLE = 800
LOT = 32
EPOQUES = 12
#: Quantes mostres es fabriquen per època. No hi ha «conjunt»: són totes noves cada vegada.
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

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


FITXA = de_kaggle("tif_text.json")
if not FITXA:
    raise SystemExit("no trobo tif_text.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
TEXT = json.load(open(FITXA, encoding="utf-8"))


def _font_bona(cami):
    """Que existeixi i pesi no vol dir que sigui una font: s'obre."""
    try:
        ImageFont.truetype(cami, 24)
        return True
    except Exception:
        return False


FONTS = [f for f in sorted(glob.glob(os.path.join(ARREL, "fonts", "*.ttf"))) if _font_bona(f)]
FONS = sorted(glob.glob(os.path.join(ARREL, "fons", "*.jpg")))
print("fonts: %d · fons: %d · línies: %d" % (len(FONTS), len(FONS), len(TEXT)))
if not FONTS:
    raise SystemExit("cap font vàlida")

#: La partició per LÍNIA: les frases de la prova no es dibuixen mai a l'entrenament.
rnd = random.Random(11)
linies = sorted(set(t.strip() for t in TEXT if len(t.strip()) >= 3))
rnd.shuffle(linies)
TALL = int(len(linies) * 0.9)
TRAIN_TXT, TEST_TXT = linies[:TALL], linies[TALL:]
print("línies per entrenar: %d · per provar: %d" % (len(TRAIN_TXT), len(TEST_TXT)))

#: L'alfabet surt del text, no d'una llista escrita a mà: si una frase porta un signe que no
#: hi hagués, el model no el podria encertar mai i el CER duria un terra que no és culpa seva.
SIGNES = sorted(set(c for t in linies for c in t))
BUIT = 0                                   # el símbol en blanc del CTC
A_NUM = {c: i + 1 for i, c in enumerate(SIGNES)}
A_SIGNE = {i + 1: c for i, c in enumerate(SIGNES)}
print("alfabet: %d símbols" % len(SIGNES))

# %%
#: --- el fabricant de mostres, el mateix que s'ha mirat amb els ulls en local ---


def un_text(r, caixa):
    t = r.choice(caixa).strip()
    mots = t.split()
    if len(mots) > 8:
        i = r.randrange(0, len(mots) - 4)
        t = " ".join(mots[i:i + r.randint(3, 8)])
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
    font = ImageFont.truetype(r.choice(FONTS), r.randint(28, 64))
    vora = r.randint(0, 4)
    prova = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    c = prova.textbbox((0, 0), text, font=font, stroke_width=vora)
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
    d.text((mx - c[0], my - c[1]), text, font=font, fill=ct, stroke_width=vora, stroke_fill=cv)

    #: Amb tres famílies de lletra, inclinar i estirar canvia la forma del glif de debò. No
    #: substitueix tenir-ne més, i queda dit.
    if r.random() < 0.35:
        inc = r.uniform(-0.22, 0.22)
        im = im.transform((im.width + int(abs(inc) * im.height), im.height), Image.AFFINE,
                          (1, inc, -inc * im.height if inc > 0 else 0, 0, 1, 0),
                          resample=Image.BILINEAR)
    if r.random() < 0.35:
        f = r.uniform(0.78, 1.3)
        im = im.resize((max(8, int(im.width * f)), im.height), Image.BILINEAR)
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
    return im.convert("L").resize((w, ALT), Image.BILINEAR), text


class Fabrica(torch.utils.data.Dataset):
    """Cada element és una mostra NOVA. La llavor depèn de l'índex i de l'època, de manera que
    no es repeteix cap imatge i alhora la prova és sempre la mateixa."""

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
        #: Si no en surt cap de bona, una de buida: el collate la descarta.
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
    #: La xarxa divideix l'amplada per 4: és el nombre de passes que veurà el CTC.
    llargs_x = torch.tensor([max(1, a // 4) for a in amples], dtype=torch.long)
    return x, y, llargs_x, llargs_y, [b[2] for b in lot]


# %%
class CRNN(nn.Module):
    """Convolucions per veure la forma, i una memòria que llegeix d'esquerra a dreta.

    L'alçada es redueix fins a 1 i l'amplada només es divideix per 4: en una escriptura
    alfabètica la informació va en horitzontal, i escurçar massa l'amplada ajunta signes veïns
    en una sola passa i el CTC ja no els pot separar.
    """

    def __init__(self, classes):
        super().__init__()
        def bloc(e, s, pool):
            return nn.Sequential(nn.Conv2d(e, s, 3, 1, 1), nn.BatchNorm2d(s),
                                 nn.ReLU(True), nn.MaxPool2d(pool))
        self.cnn = nn.Sequential(
            bloc(1, 64, (2, 2)),             # 48 -> 24
            bloc(64, 128, (2, 2)),           # 24 -> 12
            bloc(128, 256, (2, 1)),          # 12 -> 6, amplada intacta
            bloc(256, 256, (2, 1)),          # 6 -> 3
            nn.Conv2d(256, 256, (3, 1)), nn.BatchNorm2d(256), nn.ReLU(True),  # 3 -> 1
        )
        self.rnn = nn.LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True,
                           dropout=0.1)
        self.sortida = nn.Linear(512, classes)

    def forward(self, x):
        h = self.cnn(x)                      # (B, C, 1, W/4)
        h = h.squeeze(2).permute(0, 2, 1)    # (B, W/4, C)
        h, _ = self.rnn(h)
        return self.sortida(h)               # (B, T, classes)


aparell = "cuda" if torch.cuda.is_available() else "cpu"
model = CRNN(len(SIGNES) + 1).to(aparell)
print("paràmetres: %.1f M" % (sum(p.numel() for p in model.parameters()) / 1e6))

ctc = nn.CTCLoss(blank=BUIT, zero_infinity=True)
opt = torch.optim.AdamW(model.parameters(), lr=RITME, weight_decay=1e-4)
passes = EPOQUES * (PER_EPOCA // LOT)
pla = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=RITME, total_steps=passes,
                                          pct_start=0.1)


def descodifica(logits, llargs):
    """CTC golut: treure repeticions i buits."""
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
            sortida = model(x.to(aparell))
            dits = descodifica(sortida, lx)
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
    print("  època %2d · pèrdua %.3f · CER sobre text NOU %.4f" % (ep + 1, suma / max(1, quants),
                                                                   cer), flush=True)

print("\n--- sis lectures de la prova ---")
for r, h in exemples:
    print("  or : %s" % r[:60])
    print("  dit: %s" % h[:60])

torch.save({"model": model.state_dict(), "signes": SIGNES, "alt": ALT},
           "/kaggle/working/ocr_tifinag.pt")
print("\ndesat a ocr_tifinag.pt")

# %%
#: --- i el que de debò volem saber: què fa amb una imatge de VERITAT ---
OR = de_kaggle("or_fotogrames.json")
if OR:
    doror = json.load(open(OR, encoding="utf-8"))
    carpeta = os.path.dirname(OR)
    model.eval()
    print("\n=== els fotogrames de debò, llegits per una persona ===")
    for nom, bo in doror.items():
        if nom.startswith("_"):
            continue
        cami = os.path.join(carpeta, nom)
        if not os.path.exists(cami):
            continue
        im = Image.open(cami).convert("L")
        #: La franja de sota, que és on van els subtítols.
        im = im.crop((0, int(im.height * 0.72), im.width, im.height))
        w = max(16, min(MAX_AMPLE, int(im.width * ALT / im.height)))
        x = torch.from_numpy(np.array(im.resize((w, ALT), Image.BILINEAR),
                                      dtype=np.float32) / 255.0)
        with torch.no_grad():
            s = model(x.unsqueeze(0).unsqueeze(0).to(aparell))
        dit = descodifica(s, torch.tensor([w // 4]))[0]
        print("\n  %s" % nom)
        print("     la persona: %s" % str(bo)[:60])
        print("     el model  : %s" % dit[:60])
    print("\nAMB UNA LÍNIA D'OR NO ES MESURA UN OCR. Això és per mirar-ho amb els ulls,")
    print("no per treure'n un número. Cal que algú llegeixi vint o trenta franges a mà.")
