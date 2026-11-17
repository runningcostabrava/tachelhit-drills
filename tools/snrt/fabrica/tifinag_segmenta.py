# -*- coding: utf-8 -*-
"""Segmentador de glifs de la franja de tifinag dels subtítols de Tamazight TV (SNRT): Tifinaghe-Ircam Unicode, blanc amb vora fosca.

Idea: un píxel és de lletra si és BLANC i està ENTRE DUES VORES FOSQUES (a ≤ R px a banda i banda en alguna de les
quatre direccions). El fons clar (parets, reflexos, plecs) és blanc però només té vora fosca per un costat o cap, i no passa.
Després: components connexos → fusió de peces apilades (ⵓ ⴻ ? : i l'anell+punt de ⵙ) → límit d'amplada (≈1,2× el cos) amb tall per
projecció vertical → filtres (àrea mínima, vora de la franja, alçada/posició del cos, extensió centrada).

Geometria (1080p, y absoluta del fotograma): cos 884–910 (27-28 px), centre x≈964, comes fins a ≈917 (6 px sota la base).
A 720p tot ×2/3 (cos 588–608, franja crop=1280:34:0:580): es puja la franja ×1,5 i va com la de 1080p.

ÚS com a mòdul (el crida lector_tifinag.py):
    from tifinag_segmenta import segmenta
    r = segmenta(rgb, y_origen=870)      # rgb: np.uint8 (H,W,3) · y_origen = y de la fila 0 de la franja al fotograma 1080p
    r["glifs"]   -> [{"caixa": (x0,y0,x1,y1), "tipus": ..., "mask": bool}]  (coordenades de la franja)
    r["extensio"] -> (xa, xb) o None
    r["descartats"] -> [{"caixa", "motiu"}]
"""
import numpy as np
from scipy import ndimage

COS_TOP, COS_BOT = 884, 911      # files absolutes (1080p) del cos: [884, 911)
CENTRE_X = 964
COS_H = 28
AMPLE_MAX = int(round(1.2 * COS_H))       # 34
VORA_MIN = 12                             # px de la vora de la franja
AREA_MIN = 6 * 6
MARGE_INF = 13                            # px sota la base que es conserven (les comes baixen 6)
R_VORA = 5                                # distància màx. a la vora fosca a cada banda
LLINDAR_BLANC = 175
LLINDAR_FOSC = 135
MODE_TALL_BUITS = True
TALL_TOLERANT = True
_GRUPS = [0]
FOSC_RELATIU = True
FOSC_DELTA = 55


def _dist_fosc_1d(fosc, eix):
    """Per cada píxel, distància al píxel fosc més proper a l'esquerra i a la dreta (al llarg de l'eix). inf si no n'hi ha."""
    a = fosc if eix == 1 else fosc.T
    h, w = a.shape
    idx = np.arange(w)[None, :].repeat(h, 0)
    esq = np.maximum.accumulate(np.where(a, idx, -10**6), axis=1)
    dre = np.minimum.accumulate(np.where(a, idx, 10**6)[:, ::-1], axis=1)[:, ::-1]
    dl = idx - esq
    dr = dre - idx
    return (dl, dr) if eix == 1 else (dl.T, dr.T)


def _dist_diagonal(fosc):
    """Igual, al llarg de les dues diagonals (per cisallament)."""
    h, w = fosc.shape
    out = []
    for signe in (1, -1):
        W2 = w + h + 1
        B = np.zeros((h, W2), bool)
        ys, xs = np.mgrid[0:h, 0:w]
        cols = xs - ys + h if signe == 1 else xs + ys
        B[ys, cols] = fosc
        dl, dr = _dist_fosc_1d(B, 0)       # al llarg de la columna del cisallament = la diagonal
        out.append((dl[ys, cols], dr[ys, cols]))
    return out


def mascara_lletra(rgb):
    """Blanc i entre dues vores fosques. Retorna (mascara, blanc, fosc)."""
    a = rgb.astype(np.int16)
    mn, mx = a.min(axis=2), a.max(axis=2)
    blanc = (mn > LLINDAR_BLANC) & ((mx - mn) < 55)
    fosc = mx < LLINDAR_FOSC
    if FOSC_RELATIU:   # vora poc contrastada sobre fons clar: fosca respecte del blanc veí (≥ 55 sota el màxim local 9x9)
        fosc |= (mx < ndimage.maximum_filter(mn, size=9) - FOSC_DELTA) & (mx < 215)
    ok = np.zeros(blanc.shape, bool)
    for eix in (1, 0):
        dl, dr = _dist_fosc_1d(fosc, eix)
        ok |= (dl <= R_VORA) & (dr <= R_VORA)
    for dl, dr in _dist_diagonal(fosc):
        ok |= (dl <= R_VORA) & (dr <= R_VORA)
    return blanc & ok, blanc, fosc


def _caixa_comp(sl):
    return (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)


def _talla_ample(mask, x0, x1, y0, y1):
    """Parteix un component massa ample per les columnes amb menys píxels (≤ 3) fins que cap no passi de AMPLE_MAX."""
    pendents = [(x0, x1)]
    fets = []
    while pendents:
        a, b = pendents.pop()
        if b - a <= AMPLE_MAX:
            fets.append((a, b)); continue
        proj = mask[y0:y1, a:b].sum(axis=0)
        lo, hi = 6, (b - a) - 6
        cand = [(proj[i], abs(i - (b - a) / 2), i) for i in range(lo, hi) if proj[i] <= 3]
        if not cand:
            fets.append((a, b)); continue    # no es pot partir: es marcarà com a «massa ample»
        _, _, i = min(cand)
        pendents.append((a, a + i)); pendents.append((a + i, b))
    return sorted(fets)


def segmenta(rgb, y_origen=870, alt_video=1080, extensio_forcada=None):
    """Retorna dict amb glifs, extensio, descartats, mask (màscara de lletra) i y_origen en 1080p."""
    if alt_video == 720:
        from PIL import Image
        im = Image.fromarray(rgb)
        rgb = np.asarray(im.resize((int(round(im.width * 1.5)), int(round(im.height * 1.5))), Image.LANCZOS))
        y_origen = int(round(y_origen * 1.5))
    H, W = rgb.shape[:2]
    mask, blanc, fosc = mascara_lletra(rgb)
    pont = ndimage.binary_dilation(mask, structure=np.ones((3, 3)), iterations=1)   # tanca forats d'1-2 px (unions de traços)
    lab, n = ndimage.label(pont, structure=np.ones((3, 3)))
    lab = np.where(mask, lab, 0)
    sls = ndimage.find_objects(lab)
    comps = []
    for i, sl in enumerate(sls, 1):
        x0, y0, x1, y1 = _caixa_comp(sl)
        m = lab[sl] == i
        comps.append({"caixa": [x0, y0, x1, y1], "area": int(m.sum()), "id": i})
    cos_top, cos_bot = COS_TOP - y_origen, COS_BOT - y_origen   # en coordenades de la franja

    # 1) fusió de peces apilades: solapament en x i buit vertical ≤ 6 px, resultat ≤ 30 d'ample i ≤ 36 d'alt (ⵓ ⴻ ? : ⵙ-anell+punt)
    #    + la inclusió (punt dins un anell). També ⵯ (dues marques altes enganxades en x) i la coma a un punt.
    def fusiona(comps):
        canvi = True
        while canvi:
            canvi = False
            comps.sort(key=lambda c: c["caixa"][0])
            for i in range(len(comps)):
                for j in range(i + 1, len(comps)):
                    a, b = comps[i]["caixa"], comps[j]["caixa"]
                    if b[0] > a[2] + 2:
                        break
                    ox = min(a[2], b[2]) - max(a[0], b[0])
                    if ox < 0.5 * min(a[2] - a[0], b[2] - b[0]) - 0.01:
                        continue
                    if min(a[1], b[1]) < cos_top - 6 or max(a[3], b[3]) > cos_bot + 9:
                        continue          # només dins la banda del cos: no s'enganxen peces de la línia d'àrab de sota ni fons de dalt
                    buit = max(a[1], b[1]) - min(a[3], b[3])
                    nx0, ny0 = min(a[0], b[0]), min(a[1], b[1]); nx1, ny1 = max(a[2], b[2]), max(a[3], b[3])
                    peces_peti = (a[3] - a[1]) <= 14 and (b[3] - b[1]) <= 14 and (a[2] - a[0]) <= 16 and (b[2] - b[0]) <= 16
                    if (buit <= 6 and (nx1 - nx0) <= 30 and (ny1 - ny0) <= 36) or                        (peces_peti and buit <= 14 and (nx1 - nx0) <= 18 and (ny1 - ny0) <= 34):
                        comps[i] = {"caixa": [nx0, ny0, nx1, ny1], "area": comps[i]["area"] + comps[j]["area"],
                                    "id": comps[i]["id"], "ids": comps[i].get("ids", [comps[i]["id"]]) + comps[j].get("ids", [comps[j]["id"]])}
                        del comps[j]; canvi = True; break
                if canvi:
                    break
        return comps
    comps = fusiona(comps)
    for c in comps:
        c.setdefault("ids", [c["id"]])

    # 1b) tall per buit de columnes: un component amb ≥ 1 columna sense cap píxel de lletra a dins són dues lletres enganxades pel pont d'1 px
    #     (p. ex. un cercle petit ⴰ i una barra ⵍ sobre fons clar). Només es parteix si les dues bandes són glifs plausibles: ≥ 3 px d'ample,
    #     ≥ 9 px d'alt i ≥ 20 px de nucli (els braços d'una ⵜ trencada fan ≤ 5 px d'alt i no compten).
    sense_buits = []
    for c in comps:
        x0, y0, x1, y1 = c["caixa"]
        if MODE_TALL_BUITS and (y1 - y0) >= 20 and (x1 - x0) >= 14:
            msk = np.isin(lab, c.get("ids", [c["id"]]))[y0:y1, x0:x1]
            proj = msk.sum(axis=0)
            talls, ini = [], 0
            i = 0
            while i < len(proj):
                if proj[i] == 0 and i > 0:
                    j = i
                    while j < len(proj) and proj[j] == 0:
                        j += 1
                    if j < len(proj) and (j - i) >= 3:      # el buit entre lletres és de ~4 px; 1-2 columnes buides són soroll de JPEG dins d'un glif
                        talls.append((ini, i)); ini = j
                    i = j
                else:
                    i += 1
            talls.append((ini, len(proj)))
            parts = []
            for a, b in talls:
                sub = msk[:, a:b]; ys, xs = np.nonzero(sub)
                if len(ys):
                    parts.append((a, b, ys.min(), ys.max() + 1, xs.min(), xs.max() + 1, int(sub.sum())))
            bons = [p for p in parts if (p[5] - p[4]) >= 3 and (p[3] - p[2]) >= 9 and p[6] >= 20]
            if len(parts) > 1 and len(bons) == len(parts):
                _GRUPS[0] += 1
                tot = {"grup_buit": _GRUPS[0], "caixa_total": [x0, y0, x1, y1]}
                for a, b, ya, yb, xa_, xb_, ar in parts:
                    sense_buits.append({"caixa": [x0 + a + xa_, y0 + ya, x0 + a + xb_, y0 + yb], "area": ar, "ids": c.get("ids", [c["id"]]), "id": c["id"],
                                        "x_talla": (x0 + a, x0 + b), "partit_buit": True, **tot})
                continue
        sense_buits.append(c)
    comps = sense_buits

    # 2) límit d'amplada
    noves = []
    for c in comps:
        x0, y0, x1, y1 = c["caixa"]
        if x1 - x0 > AMPLE_MAX:
            msk = np.isin(lab, c["ids"])
            talls = _talla_ample(msk, x0, x1, y0, y1)
            if len(talls) > 1:
                for a, b in talls:
                    sub = msk[y0:y1, a:b]
                    ys, xs = np.nonzero(sub)
                    if len(ys) == 0:
                        continue
                    noves.append({"caixa": [a + xs.min(), y0 + ys.min(), a + xs.max() + 1, y0 + ys.max() + 1], "area": int(sub.sum()),
                                  "ids": c["ids"], "partit": True, "x_talla": (a, b), "id": c["id"]})
                continue
            c["massa_ample"] = True
            if TALL_TOLERANT and x1 - x0 <= 2 * AMPLE_MAX:
                # dues lletres rodones tangents (ⴰ+ⵔ sobre fons clar) no tenen cap columna buida. Es guarden els valls de projecció com a CANDIDATS de tall
                # (la columna del mínim de cada vall, ≤ 10 px de nucli, a ≥ 8 px de les vores); l'escollirà la plantilla (resol_amples): la projecció sola
                # no distingeix el punt de contacte de dues rodones del mig d'una sola rodona.
                proj = msk[y0:y1, x0:x1].sum(axis=0)
                vall, cols = [], []
                for i in range(8, (x1 - x0) - 8):
                    if proj[i] <= 10:
                        vall.append(i)
                    elif vall:
                        cols.append(min(vall, key=lambda j: proj[j])); vall = []
                if vall:
                    cols.append(min(vall, key=lambda j: proj[j]))
                c["cand_cols"] = [x0 + i for i in cols][:8]
        noves.append(c)
    comps = noves

    # 3) classificació per mida/posició (coordenades de franja) i filtres
    glifs, descartats, marques = [], [], []
    for c in comps:
        x0, y0, x1, y1 = c["caixa"]; w, h = x1 - x0, y1 - y0
        motiu = None
        if w <= 8 and 4 <= h <= 13 and abs(y0 - cos_top) <= 5 and c["area"] >= 8 and VORA_MIN <= x0 and x1 <= W - VORA_MIN:
            marques.append(c); continue          # candidat a ⵯ: al vídeo són dues marques verticals fines dalt (el traç és massa prim per la màscara normal)
        if w * h < AREA_MIN and not (w >= 3 and h >= 4 and c["area"] >= 10 and y0 >= cos_bot - 14):
            motiu = "area"
        elif x0 < VORA_MIN or x1 > W - VORA_MIN:
            motiu = "vora_franja"
        elif c.get("massa_ample") and not c.get("cand_cols"):
            motiu = "massa_ample"
        elif y1 < cos_top + 6 or y0 > cos_bot + 8:
            motiu = "fora_de_fila"
        elif h > 36:
            motiu = "massa_alt"
        c["tipus"] = ("cos" if h >= 20 else "petit")
        if motiu:
            descartats.append({"caixa": c["caixa"], "motiu": motiu}); continue
        # una peça petita ha d'estar a una posició coneguda: ⴰ (13x13 al peu), ⵯ (10x8 dalt), coma/punt (baix)
        if h < 20:
            ok = False
            if 9 <= w <= 16 and 9 <= h <= 16 and abs(y1 - cos_bot) <= 4:
                c["tipus"] = "ⴰ"; ok = True
            elif 6 <= w <= 13 and 5 <= h <= 11 and abs(y0 - cos_top) <= 4:
                c["tipus"] = "ⵯ"; ok = True
            elif 3 <= w <= 9 and 4 <= h <= 15 and cos_bot - 8 <= y0 <= cos_bot + 2:
                c["tipus"] = "coma"; ok = True
            elif 11 <= h < 20 and 9 <= w <= 30 and abs(y1 - cos_bot) <= 5:
                ok = True            # un cos més baix (p. ex. ⵓ/⁝ parcial, lletra dins la franja)
            if not ok:
                descartats.append({"caixa": c["caixa"], "motiu": "peca_petita_fora_de_lloc"}); continue
        else:
            if not (abs(y0 - cos_top) <= 6 and abs(y1 - cos_bot) <= 8):
                if h < 22 or y0 > cos_top + 8:
                    descartats.append({"caixa": c["caixa"], "motiu": "alcada_cos"}); continue
        c["mask"] = np.isin(lab, c["ids"])[c["caixa"][1]:c["caixa"][3], c["caixa"][0]:c["caixa"][2]]
        if c.get("partit_buit") or c.get("partit"):
            xa_t, xb_t = c["x_talla"]; cm = np.zeros_like(c["mask"]); cm[:, max(0, xa_t - c["caixa"][0]):max(0, xb_t - c["caixa"][0])] = True
            c["mask"] = c["mask"] & cm
        glifs.append(c)

    # 3b) ⵯ: una o dues marques fines i altes; només si van just a la dreta d'un glif de cos (ⴳ ⴽ ...) a ≤ 16 px
    marques.sort(key=lambda c: c["caixa"][0])
    grups_m, act = [], []
    for c in marques:
        if act and c["caixa"][0] - act[-1]["caixa"][2] <= 12 and len(act) < 2:
            act.append(c)
        else:
            if act:
                grups_m.append(act)
            act = [c]
    if act:
        grups_m.append(act)
    cos_gs = [g for g in glifs if g["tipus"] == "cos"]
    for gm in grups_m:
        x0 = min(c["caixa"][0] for c in gm); x1 = max(c["caixa"][2] for c in gm)
        y0 = min(c["caixa"][1] for c in gm); y1 = max(c["caixa"][3] for c in gm)
        esq = [g for g in cos_gs if -3 <= x0 - g["caixa"][2] <= 16]
        if not esq:
            for c in gm:
                descartats.append({"caixa": c["caixa"], "motiu": "marca_sense_glif_a_l_esquerra"})
            continue
        ids = [i for c in gm for i in c.get("ids", [c["id"]])]
        glifs.append({"caixa": [x0, y0, x1, y1], "area": sum(c["area"] for c in gm), "ids": ids, "tipus": "ⵯ",
                      "mask": np.isin(lab, ids)[y0:y1, x0:x1]})

    # 4) extensió: grups per buits ≤ 40 px; es tria la tirada de grups més centrada al centre del text conegut
    glifs.sort(key=lambda g: g["caixa"][0])
    ext = extensio_forcada
    if glifs and ext is None:
        grups, act = [], [glifs[0]]
        for g in glifs[1:]:
            if g["caixa"][0] - act[-1]["caixa"][2] <= 40:
                act.append(g)
            else:
                grups.append(act); act = [g]
        grups.append(act)
        millor = None
        for i in range(len(grups)):
            for j in range(i, len(grups)):
                gs = [g for k in range(i, j + 1) for g in grups[k]]
                xa, xb = gs[0]["caixa"][0], gs[-1]["caixa"][2]
                alts = sum(1 for g in gs if g["tipus"] in ("cos",))
                err = abs((xa + xb) / 2 - CENTRE_X)
                # puntuació: molts glifs de cos, ben centrat; penalitza el desquadrament
                punts = alts - 0.5 * max(0, err - 15) - (0 if alts >= 2 else 10)
                if millor is None or punts > millor[0]:
                    millor = (punts, (xa, xb), gs)
        ext = millor[1]
        for g in glifs:
            if g not in millor[2]:
                descartats.append({"caixa": g["caixa"], "motiu": "fora_extensio"})
        glifs = millor[2]
    elif glifs and ext is not None:
        glifs = [g for g in glifs if g["caixa"][0] >= ext[0] - 2 and g["caixa"][2] <= ext[1] + 2]
    return {"glifs": glifs, "extensio": ext, "descartats": descartats, "mask": mask, "lab": lab, "y_origen": y_origen, "rgb": rgb,
            "cos": (cos_top, cos_bot)}



def unifica_grups(r, classifica):
    """Un component partit pel buit de columnes torna a ser UN glif si la plantilla l'encaixa millor sencer que les seves parts
    (p. ex. la barra i els braços de ⵥ, que a vegades queden separats): IoU del conjunt >= mitjana dels IoU de les parts - 0,02.
    Si no, es queden separats (ⴰ i ⵍ enganxats sobre fons clar). `classifica(mask, y_rel_top)` torna [(IoU, signe), ...]."""
    cos_top = r["cos"][0]
    grups = {}
    for g in r["glifs"]:
        if g.get("grup_buit"):
            grups.setdefault(g["grup_buit"], []).append(g)
    for gid, parts in grups.items():
        x0, y0, x1, y1 = parts[0]["caixa_total"]
        ids = parts[0]["ids"]
        msk = np.isin(r["lab"], ids)[y0:y1, x0:x1]
        ys, xs = np.nonzero(msk)
        if not len(ys):
            continue
        cx0, cy0, cx1, cy1 = x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1
        msk = msk[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        iou_tot = classifica(msk, cy0 - cos_top)[0][0]
        iou_parts = np.mean([classifica(p["mask"], p["caixa"][1] - cos_top)[0][0] for p in parts])
        if iou_tot >= iou_parts - 0.02:
            nou = {"caixa": [cx0, cy0, cx1, cy1], "area": int(msk.sum()), "ids": ids, "tipus": "cos", "mask": msk, "unit_per_plantilla": True}
            pos = r["glifs"].index(parts[0])
            r["glifs"] = [g for g in r["glifs"] if g not in parts]
            r["glifs"].insert(pos, nou)
    return r


def resol_amples(r, classifica, iou_min=0.5):
    """Els components massa amples sense columna buida (ⴰ+ⵔ tangents sobre fons clar) porten `cand_cols`. Es parteix per la columna
    que dona les dues parts amb millor IoU de plantilla (mitjana ≥ iou_min); si cap no hi arriba, el component es descarta com abans."""
    cos_top = r["cos"][0]
    nous = []
    for g in r["glifs"]:
        cols = g.get("cand_cols")
        if not cols:
            nous.append(g); continue
        x0, y0, x1, y1 = g["caixa"]
        full = np.isin(r["lab"], g["ids"])
        best = None
        for cx in cols:
            parts = []
            for a, b in ((x0, cx), (cx, x1)):
                sub = full[y0:y1, a:b]
                ys, xs = np.nonzero(sub)
                if len(ys) < 20 or (xs.max() - xs.min() + 1) < 6:
                    parts = None; break
                m = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                parts.append({"caixa": [a + xs.min(), y0 + ys.min(), a + xs.max() + 1, y0 + ys.max() + 1], "area": int(sub.sum()), "ids": g["ids"],
                              "tipus": "cos" if (ys.max() - ys.min() + 1) >= 20 else "petit", "mask": m})
            if not parts:
                continue
            ious = [classifica(p["mask"], p["caixa"][1] - cos_top)[0][0] for p in parts]
            if best is None or np.mean(ious) > best[0]:
                best = (np.mean(ious), parts)
        if best and best[0] >= iou_min:
            nous.extend(best[1])
    r["glifs"] = nous
    return r
