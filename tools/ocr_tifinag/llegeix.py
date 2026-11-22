"""llegeix.py — llegeix un vídeo nou del canal amb les plantilles del primer.

Cadena sencera: fotogrames (0,5 s) → text (vermell o negre) → trams/pàgines → files → glifs →
classificació per plantilla més propera (plantilles.npz, correlació) → transcripció amb les
regles de transcriu.py. Els glifs que cap plantilla no accepta surten a nous_<video>.png
(agrupats per semblança, amb la millor plantilla i la seva correlació) per etiquetar-los a ull.

Modes de text (--mode auto|vermell|negre): «vermell» = el text llegit és vermell (vídeo 1:
karaoke acumulatiu, vídeo 2: tot vermell); «negre» = text negre fix (màscara min(r,g,b)<110),
pàgines per canvi de contingut. En tots dos modes es detecta el subratllat vermell (component
baix i ample) per datar les files si n'hi ha.

Ús: python -X utf8 llegeix.py ../MTDbi14_5cU.mp4 [--mode auto] [--llindar 0.85]
Surt a: fot_<id>/, linies_<id>/, linies_<id>.json, glifs_<id>.json, nous_<id>.png,
        transcripcio_<id>.json, conte_<id>.txt
"""
import json
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import fotogrames as F
import glifs as G
import transcriu as T

PAS = 0.5
REPARA = False  # --repara=1 activa la fusió de meitats d'anell (ajunta ⵏⵏ en una ⵍ: no ho facis servir)
LLINDARS_PROVA = (0.80, 0.85, 0.90)


# ---------- màscares ----------
def mascara_negra(a):
    """Text negre: fosc i sense color (el títol verd i el subratllat vermell no hi entren)."""
    mx, mn = a.max(axis=2), a.min(axis=2)
    return (mn < 110) & ((mx - mn) < 60)


def mascara_negra_nucli(a):
    mx, mn = a.max(axis=2), a.min(axis=2)
    return (mx < 90) & ((mx - mn) < 50)


_cache_tall = {}


def tall_subratllat(a, minim=20):
    """Píxels a esborrar: tirades horitzontals de >= minim px del NUCLI vermell (el subratllat és
    vermell ple), amb 1 px per sobre i per sota. Es calcula sobre el nucli i no sobre l'halo perquè
    l'halo ajunta lletres veïnes i formaria tirades llargues que no són cap subratllat."""
    clau = (id(a), a.shape)
    if clau in _cache_tall:
        return _cache_tall[clau]
    m = F.__dict__["_nucli_orig"](a)
    H, W = m.shape
    tall = np.zeros_like(m)
    for y in range(H):
        fila = m[y]
        if fila.sum() < minim:
            continue
        canvis = np.diff(np.concatenate(([0], fila.astype(np.int8), [0])))
        inicis, finals = np.nonzero(canvis == 1)[0], np.nonzero(canvis == -1)[0]
        for p, q in zip(inicis, finals):
            if q - p >= minim:
                tall[max(0, y - 1):y + 2, p:q] = True
    _cache_tall.clear(); _cache_tall[clau] = tall
    return tall


def sense_subratllat(m, a):
    return m & ~tall_subratllat(a)


def nucli_vermell_tolerant(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 150) & (g < 115) & (b < 115)


def posa_mode(mode):
    if mode == "negre":
        F.mascara_vermella = lambda a: sense_subratllat(mascara_negra(a), a)
        F.mascara_nucli = lambda a: sense_subratllat(mascara_negra_nucli(a), a)
    else:
        F.mascara_vermella = lambda a: sense_subratllat(F.__dict__["_vermell_orig"](a), a)
        F.mascara_nucli = lambda a: sense_subratllat(nucli_vermell_tolerant(a), a)
    G.REPARA = REPARA


F._vermell_orig = F.mascara_vermella
F._nucli_orig = F.mascara_nucli


def subratllats(a):
    """Components vermells baixos i amples (el subratllat que marca la paraula llegida)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    verm = (r > 120) & ((r - g) > 40) & ((r - b) > 40)
    lab, n = ndimage.label(verm)
    res = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h <= 5 and w >= 15:
            res.append([int(sl[1].start), int(sl[0].start), int(sl[1].stop), int(sl[0].stop)])
    return res


def tria_mode(fot, noms):
    """Vermell si hi ha files de text vermell en >= 25 % dels fotogrames de mostra (el text llegit
    es pinta de vermell, com al vídeo 1); si no, negre. Un vídeo pot tenir pàgines negres abans
    que el lector hi arribi: per això no val comptar glifs."""
    mostra = noms[:: max(1, len(noms) // 40)]
    amb = {"vermell": 0, "negre": 0}
    for mode in ("vermell", "negre"):
        posa_mode(mode)
        for nom in mostra:
            a = np.asarray(Image.open(os.path.join(fot, nom)).convert("RGB")).astype(int)
            comps, _ = F.components_de_text(a)
            if F.files_de_text(comps):
                amb[mode] += 1
    print(f"fotogrames de mostra amb text: {amb} de {len(mostra)}")
    # vermell si hi és en >= 25 % dels fotogrames I almenys tant com el negre (un vídeo de diàlegs
    # amb text negre i quatre rètols vermells sobre el dibuix és negre)
    return "vermell" if amb["vermell"] >= 0.25 * len(mostra) and amb["vermell"] >= 0.9 * amb["negre"] else "negre"


# ---------- fotogrames → trams ----------
def trams_del_video(video, vid, mode):
    fot = os.path.join(AQUI, f"fot_{vid}")
    os.makedirs(fot, exist_ok=True)
    if len([f for f in os.listdir(fot) if f.endswith(".png")]) < 10:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps={1 / PAS}",
                        os.path.join(fot, "f%04d.png")], check=True)
    noms = sorted(f for f in os.listdir(fot) if f.endswith(".png"))
    if mode == "auto":
        mode = tria_mode(fot, noms)
    posa_mode(mode)
    print(f"{len(noms)} fotogrames, mode {mode}")
    lin_dir = os.path.join(AQUI, f"linies_{vid}")
    os.makedirs(lin_dir, exist_ok=True)
    trams, actual = [], None
    subr = {}  # t -> caixes de subratllat
    for k, nom in enumerate(noms):
        t = round(k * PAS, 1)
        a = np.asarray(Image.open(os.path.join(fot, nom)).convert("RGB")).astype(int)
        sb = subratllats(a)
        if sb:
            subr[t] = sb
        res = F.analitza(os.path.join(fot, nom))
        if res is None:
            if actual is not None:
                trams.append(actual); actual = None
            continue
        if actual is not None and F.mateixa_linia(actual["ref"], res):
            actual["fi"] = t; actual["fotogrames"].append(nom); actual["resultats"].append(res)
        else:
            if actual is not None:
                trams.append(actual)
            actual = {"inici": t, "fi": t, "fotogrames": [nom], "resultats": [res], "ref": res}
    if actual is not None:
        trams.append(actual)
    sortida = []
    for n, tr in enumerate(trams):
        npix = [r["npix"] for r in tr["resultats"]]
        i_rep = int(np.argsort(npix)[len(npix) // 2])
        rep = tr["resultats"][i_rep]
        nom_png = f"{n:03d}.png"
        Image.fromarray(rep["nivells"]).save(os.path.join(lin_dir, nom_png))
        sortida.append({"id": n, "de": tr["inici"], "a": round(tr["fi"] + PAS, 1), "fotograma": tr["fotogrames"][i_rep],
                        "n_fotogrames": len(tr["fotogrames"]), "caixa": rep["caixa"], "files": rep["files"],
                        "npix": rep["npix"], "ncomp": rep["ncomp"], "retall": f"linies_{vid}/{nom_png}"})
    # pàgines (mateixa regla que fotogrames.py)
    pag = 0
    for i, s in enumerate(sortida):
        if i > 0:
            p = sortida[i - 1]
            salt = s["de"] - p["a"] > 2.0
            minva = s["npix"] < 0.9 * p["npix"] or len(s["files"]) < len(p["files"])
            mou = abs(s["files"][0][0] - p["files"][0][0]) > 4 or abs(s["files"][0][1] - p["files"][0][1]) > 4
            if salt or minva or mou:
                pag += 1
        s["pagina"] = pag
    for i, s in enumerate(sortida):
        s["final_de_pagina"] = (i == len(sortida) - 1) or sortida[i + 1]["pagina"] != s["pagina"]
    json.dump({"mode": mode, "trams": sortida, "subratllats": subr},
              open(os.path.join(AQUI, f"linies_{vid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(sortida)} trams, {pag + 1} pàgines (abans de treure transicions)")
    return mode, sortida, subr, fot


# ---------- glifs ----------
MAX_TRAMS_PAGINA = 12


def segmenta(sortida, vid):
    finals = G.trams_finals(sortida)
    pagines_reals = {s["pagina"] for s in finals}
    per_pag = {}
    for s in sortida:
        if s["pagina"] in pagines_reals:
            per_pag.setdefault(s["pagina"], []).append(s)
    triats = []
    for p, ts in per_pag.items():
        if len(ts) > MAX_TRAMS_PAGINA:
            idx = sorted({round(i * (len(ts) - 1) / (MAX_TRAMS_PAGINA - 1)) for i in range(MAX_TRAMS_PAGINA)})
            ts = [ts[i] for i in idx]
        triats += ts
    glifs, teles = [], []
    for s in triats:
        niv = np.asarray(Image.open(os.path.join(AQUI, s["retall"])).convert("L"))
        files = sorted(s["files"], key=lambda f: f[1])
        per_fila = [G.segmenta_fila(niv, f, s["caixa"]) for f in files]
        alcades = [g["caixa"][3] - g["caixa"][1] for gs in per_fila for g in gs]
        if not alcades:
            continue
        H = float(np.percentile(alcades, 85))
        if H < 9:
            continue  # lletra massa petita per llegir-la (marca d'aigua, peu de pàgina)
        buits = [b["caixa"][0] - a["caixa"][2] for gs in per_fila for a, b in zip(gs, gs[1:])]
        buit_tipic = float(np.median([b for b in buits if b >= 0])) if buits else 4.0
        llindar_espai = max(1.5 * buit_tipic, buit_tipic + 3)
        for fi, gs in enumerate(per_fila):
            paraula = 0
            for pi, g in enumerate(gs):
                if pi > 0 and g["caixa"][0] - gs[pi - 1]["caixa"][2] > llindar_espai:
                    paraula += 1
                teles.append(G.normalitza(g["mask"], H))
                cx, cy = s["caixa"][0], s["caixa"][1]
                glifs.append({"n": len(glifs), "pagina": s["pagina"], "linia": s["id"], "fotograma": s["fotograma"],
                              "fila": fi, "posicio": pi, "paraula": paraula, "caixa_retall": g["caixa"],
                              "caixa_fotograma": [g["caixa"][0] + cx, g["caixa"][1] + cy, g["caixa"][2] + cx, g["caixa"][3] + cy],
                              "h_rel": round((g["caixa"][3] - g["caixa"][1]) / H, 3),
                              "w_rel": round((g["caixa"][2] - g["caixa"][0]) / H, 3), "H": H,
                              "n_peces": g["n_peces"], "forma_excl": g["forma_excl"],
                              "fila_caixa": [int(v) for v in files[fi]]})
    print(f"{len(finals)} pàgines reals, {len(triats)} trams segmentats, {len(glifs)} glifs (abans de triar la millor "
          f"versió de cada fila); alçada de caixa alta: {sorted({round(g['H'], 1) for g in glifs})}")
    return glifs, teles, finals


def tria_millor_versio(glifs):
    """Cada fila de cada pàgina surt en molts trams; es queda la versió amb més glifs acceptats
    (i, en empat, més confiança mitjana). Marca els glifs de les versions descartades."""
    versions = {}
    for g in glifs:
        clau = (g["pagina"], round(g["fila_caixa"][1] / 6), round(g["fila_caixa"][0] / 8))
        versions.setdefault(clau, {}).setdefault(g["linia"], []).append(g)
    triats = set()
    for clau, per_tram in versions.items():
        def punt(gs):
            acc = [h for h in gs if h["etiqueta"] != "□"]
            return (len(acc), float(np.mean([h["conf"] for h in gs])))
        millor = max(per_tram.items(), key=lambda kv: punt(kv[1]))
        triats.add((clau, millor[0]))
    n = 0
    for g in glifs:
        clau = (g["pagina"], round(g["fila_caixa"][1] / 6), round(g["fila_caixa"][0] / 8))
        g["triat"] = (clau, g["linia"]) in triats
        n += g["triat"]
    print(f"  {len(versions)} files; {n} glifs a les versions triades")
    return [g for g in glifs if g["triat"]]


# ---------- classificació ----------
def classifica(glifs, teles, llindar, llindar_1a=0.80):
    """Dues passades: (1) plantilles del vídeo 1, llindar baix; (2) plantilles adaptades = mitjana
    dels glifs acceptats a la primera passada (la lletra és la mateixa però canvia de mida i de
    gruix relatiu), amb el llindar definitiu. Les etiquetes sense prou exemplars conserven la
    plantilla original."""
    z = np.load(os.path.join(AQUI, "plantilles.npz"), allow_pickle=True)
    etiquetes = [str(e) for e in z["etiquetes"]]
    imatges = z["imatges"]
    usar = [i for i, e in enumerate(etiquetes) if e != "(meitat)"]
    etiquetes = [etiquetes[i] for i in usar]
    P = np.stack([G.vector(imatges[i]) for i in usar])
    V = np.stack([G.vector(t) for t in teles])
    S1 = V @ P.T
    m1, c1 = S1.argmax(axis=1), S1.max(axis=1)
    print(f"  1a passada (plantilles del vídeo 1): accepta {(c1 >= llindar_1a).sum()} de {len(c1)} a {llindar_1a:.2f}")
    T2 = np.stack([t for t in teles])
    P2 = P.copy()
    adaptades = 0
    for j in range(len(etiquetes)):
        sel = np.nonzero((m1 == j) & (c1 >= llindar_1a))[0]
        if len(sel) >= 3:
            P2[j] = G.vector(T2[sel].mean(axis=0)); adaptades += 1
    S = V @ P2.T
    millor, conf = S.argmax(axis=1), S.max(axis=1)
    print(f"  2a passada ({adaptades} plantilles adaptades al vídeo):")
    for ll in LLINDARS_PROVA:
        print(f"    llindar {ll:.2f}: accepta {(conf >= ll).sum()} de {len(conf)} ({100 * (conf >= ll).mean():.1f} %), nous {(conf < ll).sum()}")
    for g, m, c, mm, cc in zip(glifs, millor, conf, m1, c1):
        g["millor"] = etiquetes[m]; g["conf"] = round(float(c), 3)
        g["millor_1a"] = etiquetes[mm]; g["conf_1a"] = round(float(cc), 3)
        g["etiqueta"] = etiquetes[m] if c >= llindar else "□"
    return etiquetes


def mosaic_nous(glifs, teles, vid):
    per_n = {g["n"]: g for g in glifs}
    nous = [g["n"] for g in glifs if g["etiqueta"] == "□"]
    nom = os.path.join(AQUI, f"nous_{vid}.png")
    if not nous:
        Image.new("RGB", (300, 30), "black").save(nom); return 0
    V = np.stack([G.vector(teles[i]) for i in nous])
    grups = G.enllac_mitja(V, 0.10) if len(nous) > 1 else [[0]]
    grups.sort(key=len, reverse=True)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)
    MIDA, ESC, PER = 32, 2, 12
    im = Image.new("RGB", (150 + PER * (MIDA * ESC + 4), len(grups) * (MIDA * ESC + 6)), "black")
    d = ImageDraw.Draw(im)
    for r, mem in enumerate(grups):
        y = r * (MIDA * ESC + 6)
        gl = [per_n[nous[i]] for i in mem]
        d.text((3, y + 2), f"nou {r:02d} n={len(mem)}", font=font, fill="yellow")
        d.text((3, y + 20), f"~{gl[0]['millor']} {np.mean([g['conf'] for g in gl]):.2f}", font=font, fill="cyan")
        d.text((3, y + 38), f"h{np.mean([g['h_rel'] for g in gl]):.2f} p{gl[0]['pagina']}", font=font, fill="lime")
        for k, i in enumerate(mem[:PER]):
            t = Image.fromarray((teles[nous[i]] * 255).astype(np.uint8)).resize((MIDA * ESC, MIDA * ESC), Image.NEAREST)
            im.paste(t.convert("RGB"), (150 + k * (MIDA * ESC + 4), y + 2))
    im.save(nom)
    json.dump({f"nou{r:02d}": [int(nous[i]) for i in mem] for r, mem in enumerate(grups)},
              open(os.path.join(AQUI, f"nous_{vid}.json"), "w", encoding="utf-8"))
    return len(grups)


# ---------- transcripció ----------
def es_alcat(g):
    """Glif petit (< 0,55 de la caixa alta) que seu a la part de dalt de la fila: el signe ⵯ
    (labialització) que va enganxat a ⴳ/ⴽ; la ⴰ, de la mateixa mida, seu al mig."""
    fy0, fy1 = g["fila_caixa"][1], g["fila_caixa"][3]
    h = max(1, fy1 - fy0)
    top = (g["caixa_fotograma"][1] - fy0) / h
    bot = (g["caixa_fotograma"][3] - fy0) / h
    return g["h_rel"] < 0.55 and top < 0.3 and bot < 0.62 and g["posicio"] > 0


def transcriu(glifs, sortida, subr, etiquetes, vid, mode):
    noms = etiquetes + ["□", ""] + ([] if "ⵯ" in etiquetes else ["ⵯ"])
    n_w = 0
    per_fila = {}
    for g in glifs:
        per_fila.setdefault((g["linia"], g["fila"]), []).append(g)
    for gs in per_fila.values():
        gs.sort(key=lambda g: g["posicio"])
        for k, g in enumerate(gs):
            abans = gs[k - 1] if k > 0 and gs[k - 1]["paraula"] == g["paraula"] else None
            rere_gk = abans is not None and abans["etiqueta"] in ("ⴳ", "ⴽ")
            # signe petit i alçat: ⵯ si segueix ⴳ/ⴽ (sigui quina sigui l'etiqueta: ⴰ, cometa, □),
            # o si té forma de ⴰ/ⵓ/punt i penja de dalt
            if es_alcat(g) and (rere_gk or g["etiqueta"] in ("ⴰ", "□", "ⵓ", ".")):
                g["etiqueta"] = "ⵯ"; n_w += 1
            elif es_alcat(g) and abans is not None and abans["etiqueta"] == "ⵯ":
                g["etiqueta"] = ""  # segona peça del mateix signe (ⵯ dibuixat com ˮ)
    if n_w:
        print(f"  {n_w} glifs petits alçats llegits com a ⵯ (per posició)")
    idx = {e: i for i, e in enumerate(noms)}
    etiq = {f"g{i:02d}": {"glif": e, "segur": True} for i, e in enumerate(noms)}
    for g in glifs:
        g["grup"] = idx[g["etiqueta"]]
    pagines = {}
    for s in sortida:
        pagines.setdefault(s["pagina"], []).append(s)
    files = {}
    for g in glifs:
        files.setdefault((g["linia"], g["fila"]), []).append(g)
    per_tram = {s["id"]: s for s in sortida}
    res = []
    for (tram, fi), gs in sorted(files.items()):
        s = per_tram[tram]
        fila = gs[0]["fila_caixa"]
        ts = pagines[s["pagina"]]
        de, a = None, None
        for t in ts:
            for f in t["files"]:
                if T.mateixa_fila(f, fila):
                    if de is None:
                        de = t["de"]
                    if f[2] >= fila[2] - 3 and a is None:
                        a = t["de"]
        de = s["de"] if de is None else de
        a = s["a"] if a is None or a <= de else a
        if a == de + PAS or a == de:  # sense acumulació: dura tota la pàgina
            a = ts[-1]["a"]
        # subratllat sota la fila: data més fina
        temps = [tt for tt, caixes in subr.items() if ts[0]["de"] <= tt < ts[-1]["a"]
                 and any(fila[3] - 2 <= c[1] <= fila[3] + 10 and c[2] > fila[0] and c[0] < fila[2] for c in caixes)]
        if temps:
            de, a = min(temps), round(max(temps) + PAS, 1)
        tif = T.text_fila(gs, etiq)
        res.append({"pagina": s["pagina"], "fila": fi, "de": de, "a": a, "fotograma": s["fotograma"], "tram_final": tram,
                    "caixa": fila, "n_glifs": len(gs), "n_nous": sum(1 for g in gs if g["etiqueta"] == "□"),
                    "conf_min": min(g["conf"] for g in gs), "tifinag": tif, "llati": T.llati(tif)})
    res.sort(key=lambda r: (r["pagina"], r["caixa"][1]))
    # una fila que és el començament d'una altra de la mateixa pàgina (mateixa alçada): versió
    # incompleta (animació d'entrada) que ha sobreviscut amb una clau diferent
    def nucli_text(t):
        return "".join(ch for ch in t if "ⴰ" <= ch <= "⵿")
    fora = set()
    for i, a in enumerate(res):
        for j, b in enumerate(res):
            if i != j and a["pagina"] == b["pagina"] and abs(a["caixa"][1] - b["caixa"][1]) <= 4 and a["n_glifs"] < b["n_glifs"]:
                ta, tb = nucli_text(a["tifinag"]), nucli_text(b["tifinag"])
                # tros d'una altra fila (per davant o per darrere: el subratllat esborrat o l'animació)
                if len(ta) >= 3 and (ta[:len(ta) - 2] in tb or ta[2:] in tb):
                    fora.add(i)
    # files amb menys de 3 lletres tifinag (sense comptar ⵯ) o amb menys del 60 % de glifs
    # acceptats: brossa d'imatge, rètols d'una altra font, puntuació sola, trossos
    for i, r in enumerate(res):
        if len(nucli_text(r["tifinag"]).replace("ⵯ", "")) < 3 or (r["n_glifs"] - r["n_nous"]) < 0.6 * r["n_glifs"]:
            fora.add(i)
    res = [r for i, r in enumerate(res) if i not in fora]
    print(f"  files incompletes descartades: {len(fora)}")
    # la mateixa fila (mateix text, mateixa caixa) en pàgines consecutives = la pàgina creixia:
    # es queda la darrera i hereta el «de» de la primera
    fusionades, abans = [], {}
    pags = sorted({r["pagina"] for r in res})
    for p in pags:
        ara = {}
        for r in [r for r in res if r["pagina"] == p]:
            k = (r["tifinag"], round(r["caixa"][0] / 6), round(r["caixa"][1] / 6))
            if k in abans:
                r["de"] = min(r["de"], abans[k]["de"]); r["a"] = max(r["a"], abans[k]["a"])
                fusionades.append(abans[k])
            ara[k] = r
        abans = ara
    res = [r for r in res if not any(r is f for f in fusionades)]
    print(f"  files fusionades entre pàgines consecutives: {len(fusionades)}")
    # files que només són glifs rebutjats (brossa d'una imatge o d'una transició): fora
    res = [r for r in res if r["n_nous"] < r["n_glifs"] or r["n_glifs"] > 3]
    # pàgines en ordre de temps (la fusió pot avançar el «de» d'una fila)
    inici_pag = {}
    for r in res:
        inici_pag[r["pagina"]] = min(inici_pag.get(r["pagina"], 1e9), r["de"])
    res.sort(key=lambda r: (inici_pag[r["pagina"]], r["pagina"], r["caixa"][1]))
    json.dump(res, open(os.path.join(AQUI, f"transcripcio_{vid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    linies, pag_ant = [f"# {vid}  mode {mode}"], None
    for r in res:
        if r["pagina"] != pag_ant:
            linies.append(""); linies.append(f"# pàgina {r['pagina']}  ({r['de']:.1f} s, fotograma {r['fotograma']})"); pag_ant = r["pagina"]
        linies.append(f"[{r['de']:6.1f}-{r['a']:6.1f}] {r['tifinag']}")
        linies.append(f"{'':16} {r['llati']}")
    open(os.path.join(AQUI, f"conte_{vid}.txt"), "w", encoding="utf-8").write("\n".join(linies) + "\n")
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=") for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    video = os.path.abspath(args[0])
    vid = os.path.splitext(os.path.basename(video))[0]
    mode = opts.get("mode", "auto")
    llindar = float(opts.get("llindar", 0.85))
    global REPARA
    REPARA = opts.get("repara", "0") == "1"
    mode, sortida, subr, fot = trams_del_video(video, vid, mode)
    glifs, teles, finals = segmenta(sortida, vid)
    if not glifs:
        print("cap glif llegible: no hi ha text de pàgina en aquest vídeo")
        json.dump([], open(os.path.join(AQUI, f"transcripcio_{vid}.json"), "w", encoding="utf-8"))
        open(os.path.join(AQUI, f"conte_{vid}.txt"), "w", encoding="utf-8").write(f"# {vid}  sense text llegible\n")
        json.dump({}, open(os.path.join(AQUI, f"nous_{vid}.json"), "w", encoding="utf-8"))
        print(f"0 files, 0 glifs, 0 nous en 0 grups -> transcripcio_{vid}.json")
        return
    etiquetes = classifica(glifs, teles, llindar)
    glifs = tria_millor_versio(glifs)
    conf = np.array([g["conf"] for g in glifs])
    for ll in LLINDARS_PROVA:
        print(f"  files triades, llindar {ll:.2f}: accepta {(conf >= ll).sum()} de {len(conf)} ({100 * (conf >= ll).mean():.1f} %)")
    n_grups_nous = mosaic_nous(glifs, teles, vid)
    res = transcriu(glifs, sortida, subr, etiquetes, vid, mode)
    json.dump(glifs, open(os.path.join(AQUI, f"glifs_{vid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # només les imatges dels glifs nous (les de tots els trams pesen desenes de MB per vídeo)
    nous_n = [g["n"] for g in glifs if g["etiqueta"] in ("□", "ⵯ")]
    cand_w = [g["n"] for g in glifs if g["etiqueta"] == "ⵯ"]
    if cand_w:
        nj = os.path.join(AQUI, f"nous_{vid}.json")
        d = json.load(open(nj, encoding="utf-8")); d["candidats_w"] = cand_w
        json.dump(d, open(nj, "w", encoding="utf-8"))
    np.savez_compressed(os.path.join(AQUI, f"nous_{vid}.npz"), n=np.array(nous_n, dtype=np.int64),
                        teles=np.stack([teles[i] for i in nous_n]) if nous_n else np.zeros((0, 32, 32), np.float32))
    nous = sum(1 for g in glifs if g["etiqueta"] == "□")
    print(f"{len(res)} files, {len(glifs)} glifs, {nous} nous en {n_grups_nous} grups -> transcripcio_{vid}.json, conte_{vid}.txt, nous_{vid}.png")
    print("subratllats detectats en", len(subr), "fotogrames")


if __name__ == "__main__":
    main()
