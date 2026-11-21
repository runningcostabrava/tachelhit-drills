"""Franges d'arab DE DEBO amb l'etiqueta del Qwen, per adaptar l'OCR a la lletra del video.

## Per que

L'OCR d'arab fa 0,0178 sobre text fabricat i **0,19 de coincidencia mediana** sobre les
franges reals d'en Baba Ali, quan el Qwen coincideix amb ell mateix a 0,73. El numero fabricat
no es trasllada: la lletra del video no s'assembla prou a cap de les 15 tipografies.

El remei estandard es ensenyar-li la lletra de debo. No tenim text d'or de cap franja, pero
tenim **219 franges on el Qwen diu el mateix en color i en blanc i negre** (acord >= 0,8). No
es text d'or i no se'n diu; es una etiqueta d'un altre model, mes fort, sobre la imatge real.
Aixo no es el volant que l'auditoria va prohibir (entrenar amb el que el nostre model ja
encerta): les etiquetes venen d'una maquina independent, no de la nostra.

## Les dues condicions

1. **Nomes franges d'UNA linia.** El Qwen llegeix la franja sencera; si te dues linies,
   l'etiqueta es la concatenacio i no se sap on es parteix. Es queden les que la particio
   per vores troba com una sola linia.
2. **Partida pel TEMPS, no a l'atzar.** El primer 70 % del video entrena, l'ultim 30 % prova.
   Dues franges consecutives son gairebe la mateixa imatge; una particio a l'atzar les posaria
   a les dues bandes i el numero mentiria.
"""
import io
import json
import os

from PIL import Image

import ocr_ar as O

S = os.path.dirname(os.path.abspath(__file__))
ON = os.path.join(S, "ar_reals")
LLINDAR_QWEN = 0.8
os.makedirs(os.path.join(ON, "linies"), exist_ok=True)

d = json.load(io.open(os.path.join(S, "arab_contrast.json"), encoding="utf-8"))
seg = {s["i"]: s for s in json.load(io.open(os.path.join(S, "prova_arab", "segments.json"),
                                             encoding="utf-8"))}
bones = [x for x in d if x.get("qwen_amb_qwen") is not None and x["qwen_amb_qwen"] >= LLINDAR_QWEN]
print("franges on el Qwen coincideix amb si mateix >= %.1f: %d" % (LLINDAR_QWEN, len(bones)))

fora, dues_o_mes, cap = [], 0, 0
for x in bones:
    cami = os.path.join(S, "prova_arab", "bandes1080", seg[x["i"]]["fotograma"])
    im = Image.open(cami).convert("RGB")
    linies = O.talla_linies(im)
    if len(linies) != 1:
        dues_o_mes += len(linies) > 1
        cap += len(linies) == 0
        continue
    r = O.retalla_marges(linies[0])
    if r.width < 40:
        continue
    nom = "r%06d.png" % x["i"]
    w = max(16, min(1600, int(r.width * 48 / r.height)))
    r.convert("L").resize((w, 48), Image.BILINEAR).save(os.path.join(ON, "linies", nom))
    fora.append({"fitxer": nom, "i": x["i"], "de": x["de"], "text": O.net(x["qwen_color"]),
                 "qwen_amb_qwen": x["qwen_amb_qwen"]})

fora.sort(key=lambda z: z["de"])
tall = int(len(fora) * 0.7)
for k, x in enumerate(fora):
    x["split"] = "train" if k < tall else "test"
json.dump(fora, io.open(os.path.join(ON, "reals.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("d'una sola linia: %d · amb dues o mes: %d · sense cap: %d" % (len(fora), dues_o_mes, cap))
print("train (primer 70 %% del video): %d · test (ultim 30 %%): %d" % (tall, len(fora) - tall))
print("a %s" % ON)
