"""L'OCR d'arab contra les 904 lectures del Qwen, sobre les franges de debo d'en Baba Ali.

## Que es mesura i com se'n diu

El Qwen2.5-VL va llegir 2.647 franges del video en dues versions de la imatge (color i blanc i
negre) i en va treure text a 904. **No es text d'or**: es una altra maquina. Per aixo el numero
es «coincidencia amb el Qwen», no CER.

I el Qwen no coincideix ni amb ell mateix: a la mateixa franja, la lectura en color i la de
blanc i negre sovint difereixen. Aquesta coincidencia Qwen↔Qwen es el sostre del que pot voler
dir «coincidir amb el Qwen»: si el nostre OCR hi coincideix tant com el Qwen coincideix amb si
mateix, no se li pot demanar mes amb aquesta referencia.

## Les franges

`segments.json[i].fotograma` es la franja `bandes1080/NNNNNN.jpg` del segon `de`, i
`arab_tast[i]` porta les dues lectures del Qwen per a la mateixa `i`. Es parteix per linies
abans de llegir, com amb el tifinag.
"""
import io
import json
import os

from PIL import Image

import ocr_ar as O

S = os.path.dirname(os.path.abspath(__file__))
seg = json.load(io.open(os.path.join(S, "prova_arab", "segments.json"), encoding="utf-8"))
qwen = json.load(io.open(os.path.join(S, "pont_baixat", "modelscope", "arab_tast.json"),
                         encoding="utf-8"))
per_i = {s["i"]: s for s in seg}


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


def coincidencia(a, b):
    a, b = O.net(a).replace(" ", ""), O.net(b).replace(" ", "")
    if not a or not b:
        return 0.0
    return round(1 - distancia(a, b) / max(len(a), len(b)), 3)


fora = []
for q in qwen:
    ref = (q.get("color") or "").strip()
    alt = (q.get("tallats") or "").strip()
    if not ref:
        continue
    s = per_i.get(q["i"])
    if not s:
        continue
    cami = os.path.join(S, "prova_arab", "bandes1080", s["fotograma"])
    if not os.path.exists(cami):
        continue
    im = Image.open(cami).convert("RGB")
    linies = []
    for l in O.talla_linies(im):
        r = O.retalla_marges(l)
        if r.width < 40:
            continue
        t, c = O.llegeix(r)
        if O.net(t):
            linies.append((t, c))
    nostre = " ".join(t for t, _ in linies)
    fora.append({"i": q["i"], "de": q["de"], "qwen_color": ref, "qwen_bn": alt,
                 "nostre": nostre,
                 "confianca": round(min([c for _, c in linies], default=0.0), 3),
                 "amb_qwen": coincidencia(ref, nostre),
                 "qwen_amb_qwen": coincidencia(ref, alt) if alt else None})

json.dump(fora, io.open(os.path.join(S, "arab_contrast.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

n = len(fora)
print("franges amb lectura del Qwen: %d" % n)
amb_text = [x for x in fora if x["nostre"]]
print("on el nostre OCR hi ha trobat text: %d" % len(amb_text))
print("\n=== coincidencia del NOSTRE amb el Qwen (color) ===")
for ll in (0.9, 0.8, 0.7, 0.6, 0.5):
    print("  >= %.1f : %4d (%3.0f%%)" % (ll, sum(1 for x in fora if x["amb_qwen"] >= ll),
                                        100.0 * sum(1 for x in fora if x["amb_qwen"] >= ll) / n))
vals = sorted(x["amb_qwen"] for x in fora)
print("  mediana %.3f" % vals[n // 2])

qq = [x for x in fora if x["qwen_amb_qwen"] is not None]
print("\n=== el sostre: el Qwen en color contra el Qwen en blanc i negre, mateixa franja ===")
for ll in (0.9, 0.8, 0.7, 0.6, 0.5):
    print("  >= %.1f : %4d de %d (%3.0f%%)"
          % (ll, sum(1 for x in qq if x["qwen_amb_qwen"] >= ll), len(qq),
             100.0 * sum(1 for x in qq if x["qwen_amb_qwen"] >= ll) / max(1, len(qq))))
v2 = sorted(x["qwen_amb_qwen"] for x in qq)
print("  mediana %.3f" % v2[len(v2) // 2])

print("\n--- vuit franges, de mes a menys coincidencia ---")
for x in sorted(fora, key=lambda z: -z["amb_qwen"])[:8]:
    print("\n  %6.1fs  coincidencia %.2f  (conf %.2f)" % (x["de"], x["amb_qwen"], x["confianca"]))
    print("     Qwen  : %s" % x["qwen_color"][:60])
    print("     nostre: %s" % x["nostre"][:60])
print("\n--- i quatre de baixes, per veure que falla ---")
for x in sorted([z for z in amb_text], key=lambda z: z["amb_qwen"])[:4]:
    print("\n  %6.1fs  coincidencia %.2f  (conf %.2f)" % (x["de"], x["amb_qwen"], x["confianca"]))
    print("     Qwen  : %s" % x["qwen_color"][:60])
    print("     nostre: %s" % x["nostre"][:60])
print("\ndesat a arab_contrast.json")
