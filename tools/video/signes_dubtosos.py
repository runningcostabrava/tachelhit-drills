"""Els signes on l'OCR de tifinag dubta, retallats un a un, amb les seves alternatives.

En Pablo no ha de llegir franges senceres: se li ensenya NOMES la lletra on el model no
esta segur, i se li pregunta si la suposicio del model es bona. Si diu que no, se li ensenyen
les altres opcions que el model considerava, en ordre de probabilitat.

Com es troba on es la lletra a la imatge: el CTC llegeix la linia (escalada a 48 px d'alt) en
passes de 4 px d'amplada. La passa on surt el signe diu on es; es retalla un tros al voltant,
a la resolucio original.
"""
import io, json, os
import torch
from PIL import Image
import ocr_tif as O

S = os.path.dirname(os.path.abspath(__file__))
ON = os.path.join(S, "pagina_signes")
DUBTE = 0.85
os.makedirs(os.path.join(ON, "signes"), exist_ok=True)
F = json.load(io.open(os.path.join(S, "pagina", "franges.json"), encoding="utf-8"))
#: Les 7 primeres ja les va llegir en Pablo sencera; no se li tornen a preguntar.
FETES = {"franja%02d.jpg" % i for i in range(1, 8)}

preguntes = []
for f in F:
    if f["fitxer"] in FETES:
        continue
    im = Image.open(os.path.join(S, "pagina", "franges", f["fitxer"])).convert("RGB")
    linies = O.talla_linies(im, minim_alt=14)
    ys = O.linies_y(im, minim_alt=14)
    for nl, l in enumerate(linies):
        r = O.retalla_marges(l)
        y0 = ys[nl]
        #: Una linia que toca la vora de la franja te les lletres tallades (en Pablo, a la 57:
        #: «no m'ensenya la lletra sencera»): el model hi ha llegit mitja lletra i no es pot preguntar.
        #: «Tocar» vol dir que hi ha traç a la fila de la vora, no nomes que la linia hi arribi: a
        #: les franges 11-13 la linia arriba a dalt pero les lletres hi son senceres.
        vv = O.vores_per_fila(O.np.array(im.convert("L")))
        if (y0 <= 1 and vv[0] >= 0.5 * vv.max()) or (y0 + l.height >= im.height - 1 and vv[-1] >= 0.5 * vv.max()):
            continue
        dx = O.marge_esquerre(l)
        if r.width < 60:
            continue
        #: Una «linia» on el model no esta segur de res no es text: a la franja 8 era una tira
        #: de 26 px de les potes del lleo (confianca 0,65), i en sortien preguntes sobre fons buit.
        if O.llegeix(r)[1] < 0.75:
            continue
        x = O._prepara(r)
        w48 = x.shape[-1]
        with torch.no_grad():
            p = O.MODEL(x)[0].softmax(-1)
        ids = p.argmax(-1).tolist()
        ant, inici = -1, 0
        trossos = []                          # (signe, passa inicial, passa final, prob min)
        for k, i in enumerate(ids + [-1]):
            if i != ant:
                if ant not in (-1, 0):
                    pr = p[inici:k, ant].min().item()
                    trossos.append((ant, inici, k, pr))
                ant, inici = i, k
        text_linia = "".join(O.A_SIGNE.get(a, "") for a, *_ in trossos)
        for n, (a, i0, i1, pr) in enumerate(trossos):
            signe = O.A_SIGNE.get(a, "")
            if pr >= DUBTE or not signe.strip():
                continue
            #: Les alternatives: a la passa mes dubtosa, els altres signes per ordre.
            pas = min(range(i0, i1), key=lambda k: p[k, a].item())
            ordre = torch.argsort(p[pas], descending=True).tolist()
            alt = [O.A_SIGNE[j] for j in ordre if j != 0 and j != a and "ⴰ" <= O.A_SIGNE.get(j, " ")[:1] <= "⵿"][:5]
            #: De passes (4 px a 48 d'alt) a pixels de la linia original, amb marge.
            esc = r.width / float(w48)
            #: En coordenades de la franja sencera: la linia retallada talla el cap de les
            #: lletres altes (en Pablo: «no es veu prou»). Es mostra tota l'alcada de la franja i
            #: 260 px a cada banda, amb un requadre sobre el signe.
            from PIL import ImageDraw
            sx0 = dx + int((i0 * 4 - 12) * esc); sx1 = dx + int((i1 * 4 + 12) * esc)
            x0 = max(0, sx0 - 260); x1 = min(im.width, sx1 + 260)
            tros = im.crop((x0, 0, x1, im.height)).convert("RGB")
            ImageDraw.Draw(tros).rectangle((sx0 - x0, max(0, y0), sx1 - x0, min(im.height - 1, y0 + r.height)),
                                           outline=(255, 40, 40), width=3)
            tros = tros.resize((max(1, tros.width * 220 // tros.height), 220), Image.BICUBIC)
            nom = "%s_l%d_s%02d.jpg" % (f["fitxer"][:-4], nl, n)
            tros.save(os.path.join(ON, "signes", nom), quality=88)
            preguntes.append({"id": nom[:-4], "fitxer": nom, "franja": f["fitxer"], "linia": nl,
                              "pos": n, "signe": signe, "alternatives": alt,
                              "confianca": round(pr, 3), "text_linia": text_linia})

json.dump(preguntes, io.open(os.path.join(ON, "signes.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("preguntes: %d, de %d franges" % (len(preguntes), len({q['franja'] for q in preguntes})))
mida = sum(os.path.getsize(os.path.join(ON, "signes", q["fitxer"])) for q in preguntes) / 1e6
print("imatges: %.1f MB" % mida)
for q in preguntes[:4]:
    print("  %s  model: %s  alternatives: %s" % (q["id"], q["signe"], " ".join(q["alternatives"])))
