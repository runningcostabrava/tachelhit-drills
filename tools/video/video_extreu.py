"""Treure parells de so i text d'un video amb subtitols cremats.

## El canvi d'enfocament, i per que

El primer intent buscava **on** era la franja del subtitol mirant els pixels. Vaig provar tres
senyals i cap no separa el subtitol del dibuix en una pel·licula animada:

  · vora per fila x variacio en el temps  -> deia «del 9% al 90% de l'alcada»;
  · blanc amb vora negra                  -> en aquest video la lletra es NEGRA, raó 3,4x;
  · quietud x salts bruscos               -> el fotograma SENCER s'esta quiet i canvia de cop
                                             a cada canvi d'escena; raó 1,4x.

L'enfocament que si que funciona: **no endevinar on hi ha lletra, provar de llegir-la**. El CTC
dona la probabilitat de cada simbol que tria, i la mitjana diu com de segur esta el model. Sobre
un fotograma de debo:

    el dibuix     conf 0,77   ⵃⴰⴼⵢⴹⵔ ⴱⵏⴽⵔⵀⵢ          (escombraria)
    el subtitol   conf 0,86   ⵉⴷⵓⵢ ⴷ , ⵢⴰⴼ ⴷ ⴰⵖⵔⴷⴰ...  (de debo)

## Les quatre passes

**1. On son els subtitols**: es llegeixen tots els blocs de text d'una mostra de fotogrames i
es miren les ALCADES on el model llegeix amb seguretat. La franja surt de les lectures, no
d'una suposicio.

**2. Els esdeveniments**: ja sabent la franja, es compara fotograma amb fotograma NOMES alla.
Un tros llarg sense canvis es un subtitol; el principi i el final son el so que li correspon.

**3. Les linies**: la franja sovint porta DUES linies i l'OCR esta entrenat amb UNA. Esclafar
les dues a 48 pixels fa illegible tot -va ser l'error que va fer fracassar la primera prova,
de 0,61 de confianca a 0,85 nomes partint-les.

**4. El so**: un tall per esdeveniment, amb els seus segons exactes.

## El que en surt i el que NO es

Surt: (tall de so, linies de text llegides, confianca, segons). **La lectura es d'una maquina**,
i va a `*_suggested` com tot el que llegeix una maquina. El CER d'aquest OCR sobre l'unica linia
d'or que tenim es 0,250: una lletra de cada quatre. Serveix per proposar, no per decidir.
"""
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

import ocr_tif as O

#: Cada quants segons es mira un fotograma per seguir els canvis.
PAS = 0.25
#: Quants fotogrames es llegeixen per saber on son els subtitols.
MOSTRES = 40
#: Per sota d'aixo el model no esta segur del que llegeix.
CONFIA = 0.80
#: Menys signes que aixo no es una frase.
MINIM_SIGNES = 4
#: Per sota d'aixo, dos fotogrames son el mateix subtitol.
IGUAL = 4.0
MINIM_DURA = 0.6
TIF = re.compile(r"[ⴰ-⵿]")


def nomes_tifinag(t):
    return "".join(c for c in (t or "") if TIF.match(c))


def treu_fotogrames(video, on, pas, escala):
    os.makedirs(on, exist_ok=True)
    for f in os.listdir(on):
        os.remove(os.path.join(on, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf",
                    "fps=%s,scale=%d:-1" % (1.0 / pas, escala),
                    os.path.join(on, "f%06d.png")], check=True)
    return sorted(os.path.join(on, n) for n in os.listdir(on))


def on_son_els_subtitols(camins):
    """Llegeix una mostra de fotogrames i torna la franja d'alcades on el model llegeix segur.

    Aixo no es deduir, es comprovar: la franja surt de les linies que s'han llegit de debo.
    """
    pas = max(1, len(camins) // MOSTRES)
    daltbaix, lectures = [], 0
    for c in camins[::pas]:
        im = Image.open(c).convert("RGB")
        alt = im.height
        a = np.array(im.convert("L"))
        v = O.vores_per_fila(a)
        if v.max() <= 0:
            continue
        llindar = max(3.0, v.max() * 0.22)
        marca = v >= llindar
        dins, inici = False, 0
        for k, m in enumerate(list(marca) + [False]):
            if m and not dins:
                dins, inici = True, k
            elif not m and dins:
                dins = False
                if k - inici < 10:
                    continue
                tros = im.crop((0, max(0, inici - 4), im.width, min(alt, k + 4)))
                tros = O.retalla_marges(tros)
                if tros.width < 50:
                    continue
                t, conf = O.llegeix(tros)
                lectures += 1
                if conf >= CONFIA and len(nomes_tifinag(t)) >= MINIM_SIGNES:
                    daltbaix.append((inici / alt, k / alt, nomes_tifinag(t)))
    print("  blocs provats: %d · llegits amb seguretat: %d" % (lectures, len(daltbaix)))
    if not daltbaix:
        return None

    #: La confianca sola no distingeix el subtitol d'una MARCA D'AIGUA: en aquest video
    #: `ⵃⴰⴼⵢⴹⴰ ⴱⵏⴽⴰⵀⵢⴰ` es llegeix amb 0,91 de confianca i surt a 8 dels 32 moments, perque hi
    #: es sempre. La regla bona no es com de segur es llegeix, sino **si canvia**:
    #:
    #:     el subtitol   llegeix coses DIFERENTS al llarg del video
    #:     la marca      llegeix sempre el MATEIX
    #:
    #: Es reparteixen les lectures en vint bandes d'alcada i es tria la banda amb mes textos
    #: diferents. Les bandes d'un sol text son marques i cauen.
    BANDES = 20
    per_banda = {}
    for d, a, t in daltbaix:
        b = int(((d + a) / 2) * BANDES)
        per_banda.setdefault(b, {"textos": set(), "de": [], "a": []})
        per_banda[b]["textos"].add(t)
        per_banda[b]["de"].append(d)
        per_banda[b]["a"].append(a)
    print("  bandes amb lletra: %s"
          % ", ".join("%.0f%%:%d textos" % (100.0 * b / BANDES, len(v["textos"]))
                      for b, v in sorted(per_banda.items())))
    bones = [b for b, v in per_banda.items() if len(v["textos"]) >= 3]
    if not bones:
        #: Cap banda canvia: o el video no te subtitols, o la mostra es massa curta.
        return None
    de = max(0.0, min(min(per_banda[b]["de"]) for b in bones) - 0.02)
    a = min(1.0, max(max(per_banda[b]["a"]) for b in bones) + 0.03)
    return de, a


def esdeveniments(camins, de, a, pas):
    franges = []
    for c in camins:
        im = np.array(Image.open(c).convert("L"))
        franges.append(im[int(de * im.shape[0]):int(a * im.shape[0]), :])
    fora, i = [], 0
    while i < len(franges):
        j = i + 1
        while j < len(franges) and np.abs(franges[j].astype(np.int16)
                                          - franges[i].astype(np.int16)).mean() < IGUAL:
            j += 1
        if float(O.vores_per_fila(franges[i]).max()) > 6.0 and (j - i) * pas >= MINIM_DURA:
            fora.append({"de": round(i * pas, 2), "a": round(j * pas, 2),
                         "dura": round((j - i) * pas, 2)})
        i = j
    return fora


def main():
    video = sys.argv[1]
    on = sys.argv[2] if len(sys.argv) > 2 else "extret"
    os.makedirs(on, exist_ok=True)
    tmp = os.path.join(on, "_quadres")

    camins = treu_fotogrames(video, tmp, PAS, 640)
    print("fotogrames: %d (un cada %.2f s)" % (len(camins), PAS))

    print("buscant on son els subtitols, llegint-los:")
    franja = on_son_els_subtitols(camins)
    if not franja:
        print("  cap bloc llegit amb seguretat: aquest video no porta tifinag cremat,")
        print("  o el porta en una lletra que aquest model no sap llegir.")
        return
    de, a = franja
    print("  la franja va del %.0f%% al %.0f%% de l'alcada" % (de * 100, a * 100))

    ev = esdeveniments(camins, de, a, PAS)
    print("subtitols: %d · temps cobert %.0f s de %d"
          % (len(ev), sum(e["dura"] for e in ev), int(len(camins) * PAS)))

    os.makedirs(os.path.join(on, "linies"), exist_ok=True)
    os.makedirs(os.path.join(on, "so"), exist_ok=True)
    fora = []
    for n, e in enumerate(ev, 1):
        mig = (e["de"] + e["a"]) / 2
        gran = os.path.join(on, "_f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % mig, "-i", video,
                        "-frames:v", "1", "-vf",
                        "crop=iw:ih*%.4f:0:ih*%.4f" % (a - de, de), gran], check=True)
        if not os.path.exists(gran):
            continue
        im = Image.open(gran).convert("RGB")
        llegides = []
        for k, l in enumerate(O.talla_linies(im, minim_alt=14), 1):
            r = O.retalla_marges(l)
            if r.width < 60:
                continue
            t, conf = O.llegeix(r)
            if len(nomes_tifinag(t)) < MINIM_SIGNES:
                continue
            nom = "s%03d_l%d.png" % (n, k)
            r.save(os.path.join(on, "linies", nom))
            llegides.append({"fitxer": nom, "dit": t, "confianca": round(conf, 3)})
        if not llegides:
            continue
        so = "s%03d.wav" % n
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % e["de"],
                        "-t", "%.2f" % e["dura"], "-i", video, "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", os.path.join(on, "so", so)], check=True)
        fora.append({"n": n, "de": e["de"], "a": e["a"], "dura": e["dura"],
                     "so": so, "linies": llegides,
                     "text": " ".join(x["dit"] for x in llegides).strip(),
                     "confianca": round(min(x["confianca"] for x in llegides), 3)})

    #: --- fora la marca d'aigua ---
    #: En aquest video els subtitols NO son a una franja fixa: es mouen per la pantalla (hi ha
    #: lletra que canvia al 10% i tambe del 65% al 85% de l'alcada). Per tant no es pot tallar
    #: la marca per posicio. El que si la delata es que **diu sempre el mateix**: aqui
    #: `ⵃⴰⴼⵢⴹⴰ ⴱⵏⴽⴰⵀⵢⴰ` surt a 8 dels 32 moments. Un subtitol que es repetis tant seria,
    #: igualment, una careta o un titol, i tampoc no es una frase nova per a la biblioteca.
    #: La marca no es repeteix IGUAL: l'OCR la llegeix cada cop una mica diferent
    #: (`ⵃⴰⴼⵢⴹⴰⴱⵏⴽⴰⵀⵢⴰ`, `ⵃⴰⴼⵢⴹⴰⴱⵏⴽⴰⵀⵢ`, `ⴰⴼⵢⴹⴰⴱⵏⴽⴰⵀⵢⴰ`...) i comparar el text exacte en
    #: deixava passar variants que quedaven enganxades al davant de frases bones i els
    #: enfonsaven l'acord amb l'ASR. Es compara per semblanca: dues lectures que coincideixen en
    #: tres quartes parts de les lletres son la mateixa marca.
    import difflib
    claus = []
    for p in fora:
        for l in p["linies"]:
            k = nomes_tifinag(l["dit"])
            if k:
                claus.append(k)
    grups = []                                   # [representant, membres]
    for k in claus:
        for g in grups:
            if difflib.SequenceMatcher(None, k, g[0]).ratio() >= 0.75:
                g[1].append(k)
                break
        else:
            grups.append([k, [k]])
    repetida = max(3, int(0.2 * max(1, len(fora))))
    marques = [g for g in grups if len(g[1]) >= repetida]
    if marques:
        print("\nfora per repetir-se a %d moments o mes (marca d'aigua o careta):" % repetida)
        for g in sorted(marques, key=lambda z: -len(z[1])):
            print("  %2d cops  %s  (%d variants)" % (len(g[1]), g[0][:44], len(set(g[1]))))

    def es_marca(k):
        return any(difflib.SequenceMatcher(None, k, g[0]).ratio() >= 0.75 for g in marques)

    net = []
    for p in fora:
        ll = [l for l in p["linies"] if not es_marca(nomes_tifinag(l["dit"]))]
        if not ll:
            continue
        p["linies"] = ll
        p["text"] = " ".join(x["dit"] for x in ll).strip()
        p["confianca"] = round(min(x["confianca"] for x in ll), 3)
        net.append(p)
    fora = net

    if os.path.exists(os.path.join(on, "_f.png")):
        os.remove(os.path.join(on, "_f.png"))
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)

    json.dump({"video": os.path.basename(video), "franja": [round(de, 4), round(a, 4)],
               "parells": fora},
              io.open(os.path.join(on, "extret.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n=== parells de so i text: %d ===" % len(fora))
    if fora:
        segurs = [x for x in fora if x["confianca"] >= 0.85]
        print("  amb confianca >= 0,85: %d" % len(segurs))
        print("  so en total: %.0f segons" % sum(x["dura"] for x in fora))
        print("\n--- sis ---")
        for x in sorted(fora, key=lambda z: -z["confianca"])[:6]:
            print("  %5.1f-%5.1fs  conf %.2f  %s" % (x["de"], x["a"], x["confianca"],
                                                     x["text"][:56]))
    print("\na %s" % on)


if __name__ == "__main__":
    main()
