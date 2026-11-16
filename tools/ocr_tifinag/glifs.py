"""glifs.py — dels retalls de línia als glifs i als grups de glifs semblants.

El vermell s'acumula lletra a lletra dins de cada pàgina (karaoke), així que el text sencer
de la pàgina és al darrer tram "net" de la pàgina. Aquí:
1. Tria el tram final de cada pàgina real (descarta pàgines que són un fotograma de transició).
2. A cada fila del retall, segmenta els glifs per components connexos, ajuntant els que se
   solapen horitzontalment (el punt de ⴹ ⵟ ⴶ, el ⵯ alçat, les barres de ⵉ/ⵍ no se solapen i
   queden separades: es tracten al transcriptor).
3. Espais: buit > 1,5 × buit típic entre glifs de la pàgina.
4. Normalitza cada glif a 32×32 (escala comuna per pàgina: l'alçada de caixa alta → 24 px,
   centrat; així ⴰ (petit) i ⵔ (gran) no es confonen) i agrupa per correlació.
5. Desa grups/grupNN.png (mosaic), grups.json (ocurrències), glifs.json (tots els glifs amb
   el seu grup, per a transcriu.py) i grups_full.png (tots els grups en un full).

Ús: python -X utf8 glifs.py [llindar=0.80]
"""
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
def _llindar_arg():
    try:
        return float(sys.argv[1]) if len(sys.argv) > 1 and __name__ == "__main__" else 0.90
    except ValueError:
        return 0.90


LLINDAR = _llindar_arg()
MIDA = 32
ALCADA_NORM = 24


def trams_finals(L):
    """Per a cada pàgina real, el darrer tram amb geometria de files coherent amb l'anterior."""
    pagines = {}
    for s in L:
        pagines.setdefault(s["pagina"], []).append(s)
    finals = []
    for pag, ts in sorted(pagines.items()):
        durada = ts[-1]["a"] - ts[0]["de"]
        if durada < 1.5 and len(ts) <= 2:
            continue  # fotograma de transició entre pàgines
        k = len(ts) - 1
        while k > 0:
            f, p = ts[k], ts[k - 1]
            if len(f["files"]) < len(p["files"]):
                k -= 1; continue
            be = True
            for fa, fb in zip(p["files"], f["files"]):
                # mateixa fila: x0, y0, y1 iguals (±3) i x1 que no minva
                if abs(fa[0] - fb[0]) > 3 or abs(fa[1] - fb[1]) > 3 or abs(fa[3] - fb[3]) > 3 or fb[2] < fa[2] - 3:
                    be = False; break
            if be:
                break
            k -= 1
        finals.append(ts[k])
    return finals


REPARA = False  # llegeix.py ho activa: tanca forats d'1 px del nucli dins l'halo (anells partits en lletra petita)


def segmenta_fila(niv, fila, caixa):
    """Glifs d'una fila: llista de dicts amb caixa (coords del retall) i màscara.
    niv: retall a tres nivells (255 nucli, 110 halo). Components pel nucli; forma = halo
    a 1 px del nucli (l'halo ajunta lletres veïnes, el nucli no)."""
    x0, y0, x1, y1 = fila
    cx0, cy0 = caixa[0], caixa[1]
    ya, yb = max(0, y0 - cy0 - 1), min(niv.shape[0], y1 - cy0 + 1)
    xa, xb = max(0, x0 - cx0 - 1), min(niv.shape[1], x1 - cx0 + 1)
    sub = niv[ya:yb, xa:xb]
    nucli = sub > 200
    forma = sub > 60
    lab, n = ndimage.label(nucli, structure=np.ones((3, 3)))
    if n == 0:
        return []
    objs = ndimage.find_objects(lab)
    comps = []
    for i, sl in enumerate(objs):
        comps.append({"x0": sl[1].start, "x1": sl[1].stop, "y0": sl[0].start, "y1": sl[0].stop, "ids": [i + 1]})
    comps.sort(key=lambda c: c["x0"])
    # ajunta els que se solapen horitzontalment (>= 2 px o >= 30 % del més estret)
    fusionats = []
    for c in comps:
        if fusionats:
            u = fusionats[-1]
            sol = min(u["x1"], c["x1"]) - max(u["x0"], c["x0"])
            estret = min(u["x1"] - u["x0"], c["x1"] - c["x0"])
            if sol >= 2 or (estret > 0 and sol / estret >= 0.3):
                u["x0"], u["x1"] = min(u["x0"], c["x0"]), max(u["x1"], c["x1"])
                u["y0"], u["y1"] = min(u["y0"], c["y0"]), max(u["y1"], c["y1"])
                u["ids"] += c["ids"]
                continue
        fusionats.append(dict(c))
    if REPARA and len(fusionats) > 1:
        # anells partits en dues meitats «( )» (lletra petita): dos trossos veïns (buit <= 1 px)
        # que junts no passen de l'alçada de la fila s'ajunten
        alt_fila = max(1, y1 - y0)
        tornats = [fusionats[0]]
        for c in fusionats[1:]:
            u = tornats[-1]
            buit = c["x0"] - u["x1"]
            estrets = max(u["x1"] - u["x0"], c["x1"] - c["x0"]) <= 0.45 * alt_fila
            alts = min(u["y1"] - u["y0"], c["y1"] - c["y0"]) >= 0.6 * alt_fila
            if buit <= 2 and estrets and alts and (max(u["x1"], c["x1"]) - min(u["x0"], c["x0"])) <= 0.95 * alt_fila:
                u["x0"], u["x1"] = min(u["x0"], c["x0"]), max(u["x1"], c["x1"])
                u["y0"], u["y1"] = min(u["y0"], c["y0"]), max(u["y1"], c["y1"])
                u["ids"] += c["ids"]
            else:
                tornats.append(c)
        fusionats = tornats
    glifs = []
    for c in fusionats:
        # caixa amb 1 px de marge per a l'halo
        X0, Y0 = max(0, c["x0"] - 1), max(0, c["y0"] - 1)
        X1, Y1 = min(sub.shape[1], c["x1"] + 1), min(sub.shape[0], c["y1"] + 1)
        nuc = np.isin(lab[Y0:Y1, X0:X1], c["ids"])
        if nuc.sum() < 3:
            continue  # engruna
        # forma = tot el que hi ha dins la caixa (nucli + halo), menys el que és d'altres glifs
        altres = (lab[Y0:Y1, X0:X1] > 0) & ~nuc
        altres = ndimage.binary_dilation(altres, structure=np.ones((3, 3)))
        m = forma[Y0:Y1, X0:X1] & ~altres
        m &= ndimage.binary_dilation(nuc, structure=np.ones((3, 3)), iterations=2)
        ys, xs = np.nonzero(m)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        # forma de "!": dues peces, la de sota petita (<= 35 % de l'alçada) i separada
        forma_excl = False
        if len(c["ids"]) == 2:
            peces = sorted((objs[i - 1][0].start, objs[i - 1][0].stop) for i in c["ids"])
            alt_total = peces[1][1] - peces[0][0]
            forma_excl = (peces[1][1] - peces[1][0]) <= 0.35 * alt_total and peces[1][0] > peces[0][1]
        glifs.append({
            "caixa": [int(X0 + xs.min() + xa), int(Y0 + ys.min() + ya), int(X0 + xs.max() + 1 + xa), int(Y0 + ys.max() + 1 + ya)],
            "mask": m,
            "n_peces": len(c["ids"]),  # components de nucli que formen el glif (ⵓ=2, ⵉ=1, "!"=2, ⴻ=3)
            "forma_excl": bool(forma_excl),
        })
    return glifs


def normalitza(m, H):
    """Màscara binària -> imatge 32×32 (float 0..1), escala 24/H, centrada."""
    h, w = m.shape
    s = ALCADA_NORM / H
    nh, nw = max(1, round(h * s)), max(1, round(w * s))
    if max(nh, nw) > MIDA:
        s2 = MIDA / max(nh, nw)
        nh, nw = max(1, round(nh * s2)), max(1, round(nw * s2))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((nw, nh), Image.BILINEAR)
    tela = np.zeros((MIDA, MIDA), np.float32)
    oy, ox = (MIDA - nh) // 2, (MIDA - nw) // 2
    tela[oy:oy + nh, ox:ox + nw] = np.asarray(im, np.float32) / 255.0
    return tela


def vector(tela):
    v = ndimage.gaussian_filter(tela, 0.7).ravel()
    v = v - v.mean()
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def enllac_mitja(V, dmax):
    """Agrupament aglomeratiu d'enllaç mitjà (Lance-Williams) fins que la distància mínima
    entre grups supera dmax. V: vectors unitaris (n×d). Torna llista de llistes d'índexs."""
    n = len(V)
    D = np.clip(1.0 - (V @ V.T), 0.0, 2.0).astype(np.float32)
    np.fill_diagonal(D, np.inf)
    actiu = np.ones(n, bool)
    mida = np.ones(n, np.float32)
    membres = {i: [i] for i in range(n)}
    rowmin = D.min(axis=1); rowarg = D.argmin(axis=1)
    while True:
        i = int(np.argmin(rowmin))
        d = rowmin[i]
        if not np.isfinite(d) or d > dmax:
            break
        j = int(rowarg[i])
        # nou grup a la fila i: mitjana ponderada de les distàncies de i i j
        nova = (D[i] * mida[i] + D[j] * mida[j]) / (mida[i] + mida[j])
        D[i, :] = nova; D[:, i] = nova
        D[i, i] = np.inf
        D[j, :] = np.inf; D[:, j] = np.inf
        actiu[j] = False
        mida[i] += mida[j]
        membres[i] += membres.pop(j)
        rowmin[j] = np.inf
        rowmin[i] = D[i].min(); rowarg[i] = D[i].argmin()
        # files que apuntaven a i o j: recalcula
        afectats = np.nonzero(actiu & ((rowarg == i) | (rowarg == j)))[0]
        for k in afectats:
            if k == i:
                continue
            rowmin[k] = D[k].min(); rowarg[k] = D[k].argmin()
        # files on la nova distància a i és menor que el seu mínim
        millora = np.nonzero(actiu & (D[:, i] < rowmin))[0]
        for k in millora:
            rowmin[k] = D[k, i]; rowarg[k] = i
    return list(membres.values())


def main():
    L = json.load(open(os.path.join(AQUI, "linies.json"), encoding="utf-8"))
    finals = trams_finals(L)
    print(f"{len(finals)} pàgines reals (trams finals: {[s['id'] for s in finals]})")
    glifs = []  # registres plans
    teles = []
    for s in finals:
        ret = np.asarray(Image.open(os.path.join(AQUI, s["retall"])).convert("L"))
        files = sorted(s["files"], key=lambda f: f[1])
        per_fila = [segmenta_fila(ret, f, s["caixa"]) for f in files]
        alcades = [g["caixa"][3] - g["caixa"][1] for gs in per_fila for g in gs]
        if not alcades:
            continue
        H = float(np.percentile(alcades, 85))
        # buit típic entre glifs (per pàgina)
        buits = []
        for gs in per_fila:
            for a, b in zip(gs, gs[1:]):
                buits.append(b["caixa"][0] - a["caixa"][2])
        buit_tipic = float(np.median([b for b in buits if b >= 0])) if buits else 4.0
        llindar_espai = max(1.5 * buit_tipic, buit_tipic + 3)
        for fi, gs in enumerate(per_fila):
            paraula = 0
            for pi, g in enumerate(gs):
                if pi > 0 and g["caixa"][0] - gs[pi - 1]["caixa"][2] > llindar_espai:
                    paraula += 1
                tela = normalitza(g["mask"], H)
                teles.append(tela)
                cx, cy = s["caixa"][0], s["caixa"][1]
                glifs.append({
                    "n": len(glifs), "pagina": s["pagina"], "linia": s["id"], "fotograma": s["fotograma"],
                    "fila": fi, "posicio": pi, "paraula": paraula,
                    "caixa_retall": g["caixa"],
                    "caixa_fotograma": [g["caixa"][0] + cx, g["caixa"][1] + cy, g["caixa"][2] + cx, g["caixa"][3] + cy],
                    "h_rel": round((g["caixa"][3] - g["caixa"][1]) / H, 3),
                    "w_rel": round((g["caixa"][2] - g["caixa"][0]) / H, 3),
                    "H": H, "buit_tipic": buit_tipic, "n_peces": g["n_peces"], "forma_excl": g["forma_excl"],
                    "fila_caixa": [int(v) for v in files[fi]],
                })
    print(f"{len(glifs)} glifs")
    V = np.stack([vector(t) for t in teles])
    hrel = np.array([g["h_rel"] for g in glifs]); wrel = np.array([g["w_rel"] for g in glifs])

    # agrupament jeràrquic (enllaç mitjà) sobre la distància cosinus de les imatges normalitzades:
    # més estable que un agrupament per líder; LLINDAR = semblança mitjana mínima entre dos grups
    # perquè s'ajuntin. (Implementat a mà: scipy.cluster no carrega amb aquest numpy.)
    membres = enllac_mitja(V, 1.0 - LLINDAR)
    # ordena grups per mida (els més freqüents primer)
    ordre = sorted(range(len(membres)), key=lambda k: -len(membres[k]))
    membres = [membres[k] for k in ordre]
    print(f"{len(membres)} grups (llindar {LLINDAR}); mides: {[len(m) for m in membres]}")

    os.makedirs(os.path.join(AQUI, "grups"), exist_ok=True)
    for f in os.listdir(os.path.join(AQUI, "grups")):
        os.remove(os.path.join(AQUI, "grups", f))
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    grups_json = {}
    ESC = 2
    files_full = []
    for gi, mem in enumerate(membres):
        for i in mem:
            glifs[i]["grup"] = gi
        mostra = mem[:20]
        W = 70 + len(mostra) * (MIDA * ESC + 4)
        im = Image.new("RGB", (W, MIDA * ESC + 4), (30, 30, 30))
        d = ImageDraw.Draw(im)
        d.text((3, 4), f"g{gi:02d}", font=font, fill="yellow")
        d.text((3, 24), f"n={len(mem)}", font=font, fill="lime")
        d.text((3, 44), f"h{np.mean([glifs[i]['h_rel'] for i in mem]):.2f}", font=font, fill="cyan")
        for k, i in enumerate(mostra):
            t = Image.fromarray((teles[i] * 255).astype(np.uint8)).resize((MIDA * ESC, MIDA * ESC), Image.NEAREST)
            im.paste(t.convert("RGB"), (70 + k * (MIDA * ESC + 4), 2))
        im.save(os.path.join(AQUI, "grups", f"grup{gi:02d}.png"))
        files_full.append(im)
        grups_json[f"g{gi:02d}"] = {
            "n": len(mem),
            "h_rel": round(float(np.mean([glifs[i]["h_rel"] for i in mem])), 3),
            "w_rel": round(float(np.mean([glifs[i]["w_rel"] for i in mem])), 3),
            "ocurrencies": [{"fotograma": glifs[i]["fotograma"], "linia": glifs[i]["linia"], "fila": glifs[i]["fila"],
                             "posicio": glifs[i]["posicio"], "caixa": glifs[i]["caixa_fotograma"]} for i in mem],
        }
    # full únic amb tots els grups (12 exemplars) per etiquetar-los d'una ullada
    PER = 12
    W = 70 + PER * (MIDA * ESC + 4)
    full = Image.new("RGB", (W, len(files_full) * (MIDA * ESC + 6)), "black")
    for gi, im in enumerate(files_full):
        full.paste(im.crop((0, 0, min(W, im.width), im.height)), (0, gi * (MIDA * ESC + 6)))
    full.save(os.path.join(AQUI, "grups_full.png"))
    with open(os.path.join(AQUI, "grups.json"), "w", encoding="utf-8") as f:
        json.dump(grups_json, f, ensure_ascii=False, indent=1)
    for g in glifs:
        g.pop("mask", None)
    with open(os.path.join(AQUI, "glifs.json"), "w", encoding="utf-8") as f:
        json.dump(glifs, f, ensure_ascii=False)
    np.save(os.path.join(AQUI, "teles.npy"), np.stack(teles))
    print("-> grups/, grups.json, glifs.json, grups_full.png, teles.npy")


if __name__ == "__main__":
    main()
