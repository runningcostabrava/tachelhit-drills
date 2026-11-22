"""fotogrames.py — del vídeo d'aslmdtv a les línies vermelles.

1. Extreu un fotograma cada 0,5 s amb ffmpeg (fot/fNNNN.png; es reaprofita si ja hi és).
2. A cada fotograma troba els píxels vermells (r>150, g<90, b<90), els agrupa en
   components connexos, en descarta els de < 8 píxels i també els que no seuen sobre
   paper blanc (els vermells de la il·lustració), i es queda amb els que fan files de text.
3. Agrupa els fotogrames consecutius que mostren el mateix text vermell (mateixes caixes de
   fila i mateixa forma) en trams [de, a]. ATENCIÓ: en aquest vídeo el vermell no és "la línia
   que es llegeix" sinó tot el que s'ha llegit fins ara a la pàgina (karaoke lletra a lletra),
   així que un tram nou = una lletra o paraula nova en vermell, i el text sencer d'una pàgina
   és al darrer tram de la pàgina. El vermell es reinicia quan canvia la pàgina ("pagina").
4. Desa linies.json i, per a cada tram, linies/NNN.png a tres nivells (255 nucli del traç,
   110 halo antialiàsat, 0 fons): glifs.py segmenta pel nucli perquè l'halo ajunta lletres veïnes.

Ús: python -X utf8 fotogrames.py [video.mp4]
"""
import json
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")
import numpy as np
from PIL import Image
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "..", "ZlG8Bp_rwKc.mp4")
FOT = os.path.join(AQUI, "fot")
LINIES = os.path.join(AQUI, "linies")
PAS = 0.5  # segons entre fotogrames
MIN_PIXELS_COMPONENT = 8
MIN_ALCADA, MAX_ALCADA = 6, 60  # alçada plausible d'un glif (px) a 640x360
MIN_COMPONENTS_FILA = 2


def extreu_fotogrames():
    os.makedirs(FOT, exist_ok=True)
    if len([f for f in os.listdir(FOT) if f.endswith(".png")]) > 10:
        return
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", VIDEO, "-vf", f"fps={1 / PAS}",
         os.path.join(FOT, "f%04d.png")],
        check=True,
    )


def mascara_vermella(a):
    """Píxel de text vermell. El nucli del traç és (216,0,0) però les vores antialiàsades
    arriben a (240,168,144); el criteri r>150,g<90,b<90 trencava els glifs a trossos.
    El text negre dona 0 píxels amb aquest criteri (comprovat a sonda2.py)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 120) & ((r - g) > 40) & ((r - b) > 40)


def mascara_nucli(a):
    """Nucli del traç (sense l'halo antialiàsat): amb l'halo, les lletres veïnes es toquen i
    els components connexos ajunten paraules senceres. El retall es desa a tres nivells:
    255 nucli, 110 halo, 0 fons; glifs.py segmenta pel nucli i pren la forma amb l'halo."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 150) & (g < 90) & (b < 90)


def mascara_blanca(a):
    return a.min(axis=2) > 185


def components_de_text(a):
    """Components vermells que semblen glifs sobre paper blanc.
    Torna llista de (y0, y1, x0, x1, npix) i l'etiquetatge."""
    verm = mascara_vermella(a)
    blanc = mascara_blanca(a)
    # l'halo gris/rosat de 1 px al voltant del text no és paper ni és text: no compta a l'anell
    # (una barra ⵏ de 2 px d'ample té més halo que cos i queia sota el 85 % de blanc)
    verm_halo = ndimage.binary_dilation(verm, structure=np.ones((3, 3)))
    lab, n = ndimage.label(verm, structure=np.ones((3, 3)))
    if n == 0:
        return [], lab
    objs = ndimage.find_objects(lab)
    mides = ndimage.sum(verm, lab, index=np.arange(1, n + 1))
    H, W = verm.shape
    res = []
    petits = []  # components petits: només valen si són dins d'un glif acceptat (el punt de ⵙ)
    for i, sl in enumerate(objs):
        npix = int(mides[i])
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        if npix < MIN_PIXELS_COMPONENT or h < MIN_ALCADA:
            petits.append((y0, y1, x0, x1, npix, i + 1))
            continue
        if h > MAX_ALCADA or w > 80:
            continue
        # anell de 4 px al voltant de la caixa: sobre paper ha de ser majoritàriament blanc
        # (o altres píxels de text: vermell/negre), però no colors de dibuix.
        Y0, Y1 = max(0, y0 - 4), min(H, y1 + 4)
        X0, X1 = max(0, x0 - 4), min(W, x1 + 4)
        anell = np.ones((Y1 - Y0, X1 - X0), bool)
        anell[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = False
        sub = a[Y0:Y1, X0:X1]
        # a l'anell hi pot haver altres glifs (vermells o negres): no compten.
        # La resta ha de ser paper blanc; si és color de dibuix, el component és de la il·lustració.
        altres = verm_halo[Y0:Y1, X0:X1][anell] | (sub.max(axis=2) < 120)[anell]
        b = blanc[Y0:Y1, X0:X1][anell][~altres]
        if len(b) < 10 or b.mean() < 0.85:
            continue
        res.append((y0, y1, x0, x1, npix, i + 1))
    # el punt interior de ⵙ ⴹ ⵟ fa 3-7 px: s'accepta si cau dins la caixa (+2 px) d'un glif acceptat;
    # els punts de ":" "." "!" i les cometes: components petits (>= 3 px) a la mateixa banda
    # vertical d'un glif acceptat i a menys de 30 px.
    acceptats = list(res)
    for (y0, y1, x0, x1, npix, idx) in petits:
        for (ay0, ay1, ax0, ax1, _, _) in acceptats:
            dins = y0 >= ay0 - 2 and y1 <= ay1 + 2 and x0 >= ax0 - 2 and x1 <= ax1 + 2
            prop = (npix >= 3 and y1 > ay0 - 2 and y0 < ay1 + 2
                    and (x0 - ax1 < 30) and (ax0 - x1 < 30))
            if dins or prop:
                res.append((y0, y1, x0, x1, npix, idx))
                break
    return res, lab


def files_de_text(comps):
    """Agrupa components per files (centre y proper). Torna llista de files (llistes de comps)."""
    if not comps:
        return []
    comps = sorted(comps, key=lambda c: (c[0] + c[1]) / 2)
    alc = np.median([c[1] - c[0] for c in comps])
    files, actual = [], [comps[0]]
    for c in comps[1:]:
        cy = (c[0] + c[1]) / 2
        cy_fila = np.median([(d[0] + d[1]) / 2 for d in actual])
        if abs(cy - cy_fila) <= 0.7 * alc:
            actual.append(c)
        else:
            files.append(actual)
            actual = [c]
    files.append(actual)
    # dins una fila, un buit horitzontal enorme (> 5 alçades) separa coses que no són la mateixa línia
    partides = []
    for f in files:
        f = sorted(f, key=lambda c: c[2])
        tros = [f[0]]
        for c in f[1:]:
            if c[2] - max(d[3] for d in tros) > 5 * alc:
                partides.append(tros); tros = [c]
            else:
                tros.append(c)
        partides.append(tros)
    files = [f for f in partides if len(f) >= MIN_COMPONENTS_FILA and sum(c[4] for c in f) >= 60
             and max(c[1] - c[0] for c in f) >= 11]  # files de glifs minúsculs = marca d'aigua
    return files


def caixa(comps):
    return [int(min(c[2] for c in comps)), int(min(c[0] for c in comps)),
            int(max(c[3] for c in comps)), int(max(c[1] for c in comps))]


def analitza(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    comps, lab = components_de_text(a)
    files = files_de_text(comps)
    if not files:
        return None
    tots = [c for f in files for c in f]
    x0, y0, x1, y1 = caixa(tots)
    # retall net: vermell fluix només dins les caixes dels components acceptats (1 px de marge)
    net = np.zeros(a.shape[:2], bool)
    verm = lab > 0
    for (cy0, cy1, cx0, cx1, _, idx) in tots:
        net[cy0:cy1, cx0:cx1] |= (lab[cy0:cy1, cx0:cx1] == idx)
    nucli = net & mascara_nucli(a)
    retall = net[y0:y1, x0:x1]
    nivells = np.where(nucli[y0:y1, x0:x1], 255, np.where(retall, 110, 0)).astype(np.uint8)
    return {
        "caixa": [x0, y0, x1, y1],
        "files": [caixa(f) for f in files],
        "npix": int(retall.sum()),
        "ncomp": len(tots),
        "retall": retall,
        "nivells": nivells,
    }


def mateixa_linia(p, q):
    """p, q: resultats d'analitza. Mateixa línia si la caixa gairebé coincideix i la forma també."""
    if p is None or q is None:
        return p is None and q is None
    if len(p["files"]) != len(q["files"]):
        return False
    # el text vermell creix paraula a paraula: cada fila ha de tenir la mateixa caixa (±3 px)
    for fa, fb in zip(p["files"], q["files"]):
        if max(abs(u - v) for u, v in zip(fa, fb)) > 3:
            return False
    # forma: XOR sobre una tela comuna alineada per la cantonada superior esquerra
    h = max(p["retall"].shape[0], q["retall"].shape[0])
    w = max(p["retall"].shape[1], q["retall"].shape[1])
    A = np.zeros((h, w), bool); A[:p["retall"].shape[0], :p["retall"].shape[1]] = p["retall"]
    B = np.zeros((h, w), bool); B[:q["retall"].shape[0], :q["retall"].shape[1]] = q["retall"]
    # tolerància a un desplaçament d'1 px
    millor = 1.0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            Bs = np.roll(np.roll(B, dy, 0), dx, 1)
            xor = (A ^ Bs).sum() / max(1, (A | Bs).sum())
            millor = min(millor, xor)
    return millor < 0.15


def main():
    extreu_fotogrames()
    os.makedirs(LINIES, exist_ok=True)
    noms = sorted(f for f in os.listdir(FOT) if f.endswith(".png"))
    print(f"{len(noms)} fotogrames")
    trams = []  # cada tram: dict amb idx inicial/final i llista de resultats
    actual = None
    for k, nom in enumerate(noms):
        t = k * PAS
        res = analitza(os.path.join(FOT, nom))
        if res is None:
            if actual is not None:
                trams.append(actual); actual = None
            continue
        if actual is not None and mateixa_linia(actual["ref"], res):
            actual["fi"] = t
            actual["fotogrames"].append(nom)
            actual["resultats"].append(res)
        else:
            if actual is not None:
                trams.append(actual)
            actual = {"inici": t, "fi": t, "fotogrames": [nom], "resultats": [res], "ref": res}
        if k % 200 == 0:
            print(f"  {nom} t={t:.1f}s trams={len(trams)}")
    if actual is not None:
        trams.append(actual)

    sortida = []
    n = 0
    for tr in trams:
        # representant: el fotograma amb el nombre de píxels mitjà del tram (evita transicions)
        npix = [r["npix"] for r in tr["resultats"]]
        ordre = np.argsort(npix)
        i_rep = int(ordre[len(ordre) // 2])
        rep = tr["resultats"][i_rep]
        curt = len(tr["fotogrames"]) < 2
        nom_png = f"{n:03d}.png"
        Image.fromarray(rep["nivells"]).save(os.path.join(LINIES, nom_png))
        sortida.append({
            "id": n,
            "de": round(tr["inici"], 1),
            "a": round(tr["fi"] + PAS, 1),
            "fotograma": tr["fotogrames"][i_rep],
            "n_fotogrames": len(tr["fotogrames"]),
            "caixa": rep["caixa"],
            "files": rep["files"],
            "npix": rep["npix"],
            "ncomp": rep["ncomp"],
            "retall": f"linies/{nom_png}",
            "curt": curt,
        })
        n += 1
    # Pàgines: el vermell s'acumula lletra a lletra dins una pàgina (karaoke) i es reinicia
    # quan canvia la pàgina. Tram nou de pàgina = el vermell minva o es mou.
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
    with open(os.path.join(AQUI, "linies.json"), "w", encoding="utf-8") as f:
        json.dump(sortida, f, ensure_ascii=False, indent=1)
    print(f"{pag + 1} pàgines")
    llargs = [s for s in sortida if not s["curt"]]
    print(f"{len(sortida)} trams ({len(llargs)} de >= 2 fotogrames) -> linies.json, linies/")


if __name__ == "__main__":
    main()
