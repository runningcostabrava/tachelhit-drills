# -*- coding: utf-8 -*-
"""Etapa 05: els comptes i l'informe.

  python 05_informe.py <carpeta> [--mostra 20] [--llavor 1114]

Ajunta les traduccions a `subtitols.jsonl`, calcula `numeros.json` sobre el diàleg (fora els crèdits) i escriu
`INFORME.md`: subtítols, durades, acord de l'OCR àrab, lectura del tifinag, acord entre els dos traductors de
l'àrab, chrF entre els dos catalans, parelles útils per a entrenar a cada llindar, cost en fitxes i temps de cada
etapa, i una mostra a ull de N subtítols a l'atzar (llavor fixa) amb la franja de les dues línies retallada a
`mostra/ull_NN_kK.png` perquè algú els miri. Si TD_CATALEG apunta al catàleg de producció i el transliterador
del backend és a mà, hi afegeix l'estimació de varietat (vocabulari compartit amb cada grup de parlants).
"""
import argparse
import io
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "05_informe"


def fusiona(carpeta):
    files = comu.jsonl_llegeix(os.path.join(carpeta, "subtitols.jsonl"))
    trad = {x["k"]: x for x in comu.jsonl_llegeix(os.path.join(carpeta, "traduccions.jsonl"))}
    for f in files:
        t = trad.get(f["k"], {})
        f["catala_de_arab"] = t.get("ca_ar1", "")
        f["catala_de_arab_2"] = t.get("ca_ar2", "")
        f["acord_arab"] = t.get("acord_ar")
        f["catala_de_tifinag"] = t.get("ca_tif", "")
        f["chrf"] = t.get("chrf")
    comu.jsonl_escriu(os.path.join(carpeta, "subtitols.jsonl"), files)
    return files


def mitj(xs, f=statistics.mean):
    xs = [x for x in xs if x is not None]
    return round(f(xs), 4) if xs else None


def numeros(files, est):
    D = [f for f in files if not f["credits"]]
    dur = [f["durada"] for f in D]
    ch = [f["chrf"] for f in D if f["chrf"] is not None and f["tifinag"]]
    ac = [f["acord_arab"] for f in D if f["acord_arab"] is not None]
    multi = [f for f in D if f["arab_lectures"] > 1]
    conf = [f["tifinag_conf"] for f in D if f["tifinag_conf"]]
    so = lambda xs: round(sum(f["tall_a"] - f["tall_de"] for f in xs), 1)
    n = {
        "video": est.get("video"), "alt": est.get("alt"), "durada_video": est.get("durada"),
        "subtitols_total": len(files), "subtitols_credits": len(files) - len(D), "subtitols": len(D),
        "segons_amb_text": sum(dur), "segons_so_dialeg": so(D),
        "durada_mitjana": mitj(dur), "durada_mediana": mitj(dur, statistics.median),
        "durades": {str(d): dur.count(d) for d in sorted(set(dur))},
        "arab_un_sol_fotograma": sum(1 for f in D if f["arab_lectures"] <= 1),
        "arab_multi": len(multi), "arab_unanimes": sum(1 for f in multi if f["arab_dacord"] == f["arab_lectures"]),
        "arab_acord_mitja_multi": mitj([f["arab_acord"] for f in multi]),
        "tifinag_amb_text": sum(1 for f in D if f["tifinag"]), "tifinag_glifs": sum(f["tifinag_glifs"] for f in D),
        "tifinag_dubtosos": sum(f["tifinag_dubtosos"] for f in D), "tifinag_conf_mitjana": mitj(conf),
        "tifinag_conf_sota_085": sum(1 for f in D if f["tifinag"] and (f["tifinag_conf"] or 0) < 0.85),
        "acord_arab_n": len(ac), "acord_arab_mitja": mitj(ac), "acord_arab_mediana": mitj(ac, statistics.median),
        "acord_arab_sobre_0_5": sum(1 for c in ac if c >= 0.5), "acord_arab_sota_0_3": sum(1 for c in ac if c < 0.3),
        "chrf_n": len(ch), "chrf_mitja": mitj(ch), "chrf_mediana": mitj(ch, statistics.median),
        "chrf_sobre_0_5": sum(1 for c in ch if c >= 0.5), "chrf_sobre_0_3": sum(1 for c in ch if c >= 0.3),
        "chrf_sota_0_1": sum(1 for c in ch if c < 0.1),
        "parelles": {},
        "fitxes_visio": est.get("02_llegeix", {}).get("fitxes_visio"),
        "fitxes_text": (est.get("04_tradueix", {}).get("fitxes_ar1") or 0) + (est.get("04_tradueix", {}).get("fitxes_ar2") or 0),
        "segons_maquina": sum(est.get(e, {}).get("segons") or 0 for e in ("02_llegeix", "03_talla", "04_tradueix")),
    }
    amb = [f for f in D if f["tifinag"] and f["catala_de_arab"]]
    n["parelles"]["totes"] = {"n": len(amb), "paraules": sum(len(f["tifinag"].split()) for f in amb), "so": so(amb)}
    seg = [f for f in amb if (f["tifinag_conf"] or 0) >= 0.85]
    n["parelles"]["tifinag_0_85"] = {"n": len(seg), "paraules": sum(len(f["tifinag"].split()) for f in seg), "so": so(seg)}
    for ll in (0.3, 0.5):
        s = [f for f in amb if (f["chrf"] or 0) >= ll]
        n["parelles"][f"acord_{ll}"] = {"n": len(s), "paraules": sum(len(f["tifinag"].split()) for f in s), "so": so(s)}
    segur = [f for f in amb if (f["tifinag_conf"] or 0) >= 0.85 and (f["acord_arab"] or 0) >= 0.5]
    n["parelles"]["tifinag_0_85_i_arab_acord_0_5"] = {"n": len(segur), "paraules": sum(len(f["tifinag"].split()) for f in segur), "so": so(segur)}
    return n


def font(mida):
    from PIL import ImageFont
    for p in (r"C:\Windows\Fonts\ebrima.ttf", "/usr/share/fonts/truetype/noto/NotoSansTifinagh-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, mida)
    return ImageFont.load_default()


def mostra_a_ull(carpeta, files, est, n, llavor):
    from PIL import Image, ImageDraw
    video = comu.video_de(carpeta)
    ample, alt = est.get("ample", 1280), est.get("alt", 720)
    y0, y1 = comu.BANDA_720
    s = comu.escala(alt)
    cand = [f for f in files if not f["credits"] and f["tifinag"] and f["arab"] and f["catala_de_arab"]]
    random.seed(llavor)
    mostra = sorted(random.sample(cand, min(n, len(cand))), key=lambda f: f["k"])
    os.makedirs(os.path.join(carpeta, "mostra"), exist_ok=True)
    fnt = font(18)
    for i, f in enumerate(mostra):
        t = (f["t"] + f["fi"]) / 2
        png = os.path.join(carpeta, "mostra", f"ull_{i:02d}_k{f['k']}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                        f"crop={ample}:{round((y1 - y0) * s)}:0:{round(y0 * s)},scale=1920:-1", png], check=False)
        if not os.path.exists(png):
            continue
        im = Image.open(png).convert("RGB")
        full = Image.new("RGB", (im.width, im.height + 150), "black")
        full.paste(im, (0, 0))
        d = ImageDraw.Draw(full)
        d.text((8, im.height + 4), f"[{i}] k={f['k']} {f['t']}-{f['fi']}s   tifinag llegit: {f['tifinag']}", font=fnt, fill="yellow")
        d.text((8, im.height + 32), f"ca(arab, 1): {f['catala_de_arab']}", font=fnt, fill="white")
        d.text((8, im.height + 60), f"ca(arab, 2): {f['catala_de_arab_2']}", font=fnt, fill=(220, 220, 220))
        d.text((8, im.height + 88), f"ca(tifinag): {f['catala_de_tifinag']}", font=fnt, fill=(160, 220, 255))
        d.text((8, im.height + 116), f"chrF tif {f['chrf']}   acord arab {f['acord_arab']}   OCR arab {f['arab_dacord']}/{f['arab_lectures']}   conf tifinag {f['tifinag_conf']}", font=fnt, fill=(200, 200, 200))
        full.save(png)
        f["full"] = os.path.relpath(png, carpeta).replace("\\", "/")
    return mostra


def varietat(files):
    """Vocabulari del tifinag llegit (conf ≥ 0,85) contra els grups de parlants del catàleg de producció."""
    cat_p = os.environ.get("TD_CATALEG")
    if not cat_p or not os.path.exists(cat_p):
        return None
    sys.path.insert(0, os.path.join(comu.REPO, "backend"))
    os.environ.setdefault("LEXICON_WARMUP", "0")
    try:
        from transliteration import to_forms
    except Exception:
        return None
    grups = {
        "Aït Mraw / Beni Mellal (tdl)": lambda r, v: (r or "").startswith(("Beni Mellal", "Aït Mraw", "Ait Mraw")),
        "Souss (shi, MTNRA + Common Voice)": lambda r, v: (r or "").startswith("Souss") or (v == "shi" and not r),
        "Atles Central (tzm)": lambda r, v: (r or "").startswith("Atles Central") or v == "tzm",
        "amazic estàndard (zgh)": lambda r, v: v == "zgh",
    }

    def mots(text):
        if not text:
            return []
        cl = unicodedata.normalize("NFC", to_forms(text)["clean_latin"].lower())
        return [m for m in re.split(r"[^\w]+", cl) if len(m) > 1 and not m.isdigit()]

    video = Counter()
    for f in files:
        if not f["credits"] and f["tifinag"] and (f.get("tifinag_conf") or 0) >= 0.85:
            video.update(mots(f["tifinag"]))
    with io.open(cat_p, encoding="utf-8") as fh:
        cat = json.load(fh)
    if isinstance(cat, dict):
        cat = cat.get("drills") or list(cat.values())[0]
    vocab = {g: Counter() for g in grups}
    frases = {g: 0 for g in grups}
    for x in cat:
        t = x.get("text_tachelhit") or ""
        if not t.strip():
            continue
        for g, tria in grups.items():
            if tria(x.get("region"), x.get("variety")):
                vocab[g].update(mots(t)); frases[g] += 1
    res = {"formes": len(video), "aparicions": sum(video.values()), "grups": {}}
    top = [m for m, _ in video.most_common(100)]
    for g, V in vocab.items():
        tipus = sum(1 for m in video if m in V)
        apar = sum(n for m, n in video.items() if m in V)
        res["grups"][g] = {"frases": frases[g], "formes": len(V), "compartides": tipus,
                           "prop_formes": round(tipus / max(1, len(video)), 3), "prop_aparicions": round(apar / max(1, sum(video.values())), 3),
                           "top100": sum(1 for m in top if m in V)}
    totes = Counter()
    for V in vocab.values():
        totes.update(V)
    res["noves"] = [(m, c) for m, c in video.most_common() if m not in totes][:30]
    return res


def pc(a, b):
    return f"{100 * a / b:.0f} %" if b else "—"


def informe(carpeta, files, num, mostra, est, var):
    D = [f for f in files if not f["credits"]]
    L = []
    w = L.append
    w(f"# {est.get('video', os.path.basename(carpeta))}: informe de la fàbrica ({time.strftime('%Y-%m-%d')})")
    w("")
    w("Material de la SNRT (permís del 17-11-2026: recerca, no republicar). Tot el que hi ha aquí és esborrany de "
      "màquina per a train/test del traductor i de l'ASR; res va a la biblioteca pública.")
    w("")
    w("## Els números (sobre el diàleg, fora els crèdits)")
    w("")
    w("| | |"); w("|---|---|")
    w(f"| vídeo | {est.get('ample')}x{est.get('alt')}, {num['durada_video']} s |")
    w(f"| subtítols | **{num['subtitols']}** de diàleg (+ {num['subtitols_credits']} de crèdits; límits {est.get('credits')}) |")
    w(f"| text a pantalla / so dels talls | {num['segons_amb_text']} s / {num['segons_so_dialeg']} s |")
    w(f"| durada mitjana / mediana | {num['durada_mitjana']} s / {num['durada_mediana']} s |")
    w(f"| distribució de durades (s) | " + " · ".join(f"{k}: {v}" for k, v in num["durades"].items()) + " |")
    w(f"| OCR àrab: vistos en ≥ 2 fotogrames / unànimes | {num['arab_multi']} / {num['arab_unanimes']} ({pc(num['arab_unanimes'], num['arab_multi'])}), acord mitjà {num['arab_acord_mitja_multi']} |")
    w(f"| OCR àrab: d'un sol fotograma (sense confirmació) | {num['arab_un_sol_fotograma']} |")
    w(f"| tifinag: amb text / glifs / dubtosos | {num['tifinag_amb_text']} / {num['tifinag_glifs']} / {num['tifinag_dubtosos']} ({pc(num['tifinag_dubtosos'], num['tifinag_glifs'])}), confiança mitjana {num['tifinag_conf_mitjana']}, vídeo de {est.get('02_llegeix', {}).get('tifinag_alt')}p |")
    w(f"| àrab → català, acord entre els dos models (chrF) | mitjà {num['acord_arab_mitja']}, mediana {num['acord_arab_mediana']}, ≥ 0,5: {num['acord_arab_sobre_0_5']} de {num['acord_arab_n']}, < 0,3: {num['acord_arab_sota_0_3']} |")
    w(f"| tifinag → català contra àrab → català (chrF) | mitjà **{num['chrf_mitja']}**, mediana {num['chrf_mediana']}, ≥ 0,5: {num['chrf_sobre_0_5']} ({pc(num['chrf_sobre_0_5'], num['chrf_n'])}), ≥ 0,3: {num['chrf_sobre_0_3']}, < 0,1: {num['chrf_sota_0_1']} |")
    w(f"| fitxes de visió / de text | {num['fitxes_visio']} / {num['fitxes_text']} |")
    w(f"| temps de màquina (etapes 02–04) | {num['segons_maquina']} s |")
    w("")
    w("El chrF entre els dos catalans mesura el traductor amazic (i que les dues línies no són traducció literal l'una "
      "de l'altra), no l'OCR: amb les dues lectures bones surten valors de 0,15. L'acord entre els dos traductors de "
      "l'àrab és la mesura de l'àrab → català; on és baix sol haver-hi un error d'OCR o un nom propi.")
    w("")
    w("## Què en traiem per entrenar")
    w("")
    w("| filtre | parelles | paraules amazigues | so |"); w("|---|---|---|---|")
    noms = {"totes": "totes les rèpliques amb tifinag i àrab", "tifinag_0_85": "tifinag amb confiança ≥ 0,85",
            "acord_0.3": "acord ≥ 0,3 entre els dos catalans", "acord_0.5": "acord ≥ 0,5 entre els dos catalans",
            "tifinag_0_85_i_arab_acord_0_5": "tifinag ≥ 0,85 i els dos traductors de l'àrab d'acord (≥ 0,5)"}
    for k, p in num["parelles"].items():
        w(f"| {noms.get(k, k)} | {p['n']} | {p['paraules']} | {p['so']} s |")
    w("")
    w("Proposta: train = tifinag ≥ 0,85 amb el català de l'àrab (el dels dos models d'acord) com a objectiu; test = acord "
      "≥ 0,5 entre els dos catalans (segures sense parlant). El so és subtítol, no transcripció literal: per a l'ASR, "
      "filtrar els talls amb el reconeixedor actual.")
    w("")
    if var:
        w("## Estimació de varietat")
        w("")
        w(f"Vocabulari del tifinag llegit (confiança ≥ 0,85): {var['formes']} formes, {var['aparicions']} aparicions, transliterat "
          "al llatí del projecte, contra el catàleg de producció:")
        w("")
        w("| grup | frases | formes | formes del vídeo que ja té | de les aparicions | de les 100 més freqüents |"); w("|---|---|---|---|---|---|")
        for g, r in var["grups"].items():
            w(f"| {g} | {r['frases']} | {r['formes']} | {r['compartides']} ({100 * r['prop_formes']:.0f} %) | {100 * r['prop_aparicions']:.0f} % | {r['top100']} |")
        w("")
        w("Formes freqüents que no té cap grup: " + " ".join(f"{m}({c})" for m, c in var["noves"][:25]))
        w("")
        w("Reserva: part de la distància és ortogràfica (la SNRT i les lectures d'MTNRA/Common Voice segueixen la norma de "
          "l'IRCAM; les frases de Beni Mellal estan escrites a la manera del parlant).")
        w("")
    w(f"## Mostra a ull ({len(mostra)} a l'atzar, `mostra/ull_NN_kK.png`)")
    w("")
    w("| # | k | t | àrab llegit | tifinag llegit | català (àrab, 1) | català (àrab, 2) | català (tifinag) | acord àrab | chrF |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(mostra):
        w(f"| {i} | {f['k']} | {f['t']} | {f['arab']} | {f['tifinag']} | {f['catala_de_arab']} | {f['catala_de_arab_2']} | {f['catala_de_tifinag']} | {f['acord_arab']} | {f['chrf']} |")
    w("")
    w("Les columnes «bé/malament» de l'OCR les ha de posar algú mirant les imatges: la màquina no pot jutjar-se sola.")
    w("")
    w("## Fitxers")
    w("")
    w("`subtitols.jsonl` (tot junt, una fila per subtítol), `talls/` (wav 16 kHz), `lectures.jsonl` (una lectura de l'àrab per "
      "segon), `linies_arab.json`, `tifinag.json` (glif a glif), `traduccions.jsonl`, `numeros.json`, `estat.json` (els comptes "
      "de cada etapa), `fabrica.log`.")
    with io.open(os.path.join(carpeta, "INFORME.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--mostra", type=int, default=20)
    ap.add_argument("--llavor", type=int, default=1114)
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    log = io.open(os.path.join(carpeta, "fabrica.log"), "a", encoding="utf-8")
    comu.diu(log, f"== {ETAPA} {time.strftime('%Y-%m-%d %H:%M')}")
    t0 = time.time()
    files = fusiona(carpeta)
    est = comu.estat_llegeix(carpeta)
    num = numeros(files, est)
    var = varietat(files)
    if var:
        num["varietat"] = var
    with io.open(os.path.join(carpeta, "numeros.json"), "w", encoding="utf-8") as f:
        json.dump(num, f, ensure_ascii=False, indent=1)
    mostra = mostra_a_ull(carpeta, files, est, a.mostra, a.llavor)
    with io.open(os.path.join(carpeta, "mostra_ull.json"), "w", encoding="utf-8") as f:
        json.dump(mostra, f, ensure_ascii=False, indent=1)
    informe(carpeta, files, num, mostra, est, var)
    comu.estat_desa(carpeta, ETAPA, subtitols=num["subtitols"], chrf_mitja=num["chrf_mitja"], acord_arab_mitja=num["acord_arab_mitja"],
                    segons=round(time.time() - t0), fet=True)
    comu.diu(log, f"{ETAPA}: {num['subtitols']} de diàleg, chrF {num['chrf_mitja']}, acord àrab {num['acord_arab_mitja']} -> INFORME.md")


if __name__ == "__main__":
    main()
