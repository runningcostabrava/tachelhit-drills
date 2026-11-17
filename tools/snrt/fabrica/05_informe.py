# -*- coding: utf-8 -*-
"""Etapa 05: `numeros.json` i `INFORME.md` del capítol amb la plantilla de §7, i una línia a
`TD_TV/_informes/AAAA-MM-DD.md`.

  python -X utf8 05_informe.py <carpeta_del_capitol> [--mostra 20] [--llavor 1114]

Portes de §5 (sense tocar cap llindar): apta per al traductor = no crèdits, tifinag_conf ≥ 0,85, tifinag_dubtosos ≤ 2,
arab_acord ≥ 0,5 (o una sola lectura sense error), catala_estat ∈ {confirmat, tercer}, 2 ≤ paraules ≤ 30. La porta de
l'ASR (durada ≥ 0,8 s i CER ≤ 0,4 de l'ASR actual contra el tifinag) necessita passar el so pel transcriptor: aquí es
compta només la part de durada i es deixa el CER com a «no mesurat» (pendent del director: quin ASR i on corre).
Varietat §6.1 (punts 1–3): les 200 formes més freqüents del capítol (tifinag de les rèpliques aptes, transliterat i
normalitzat per §6.2) contra Aït Mraw / Beni Mellal, Souss i Atles Mitjà del catàleg (`TD_CATALEG`), i la mateixa
mesura només sobre paraules gramaticals (les 60 més freqüents de cada referència), amb el control entre referències.
El punt 4 (escoltar 30 rèpliques amb l'ASR) no es fa aquí. `varietat_capitol` queda «desconeguda» fins que el director
decideixi (§6.1.5).
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
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "05_informe"


def mitj(xs, f=statistics.mean):
    xs = [x for x in xs if x is not None]
    return round(f(xs), 4) if xs else None


def pc(a, b):
    return f"{100 * a / b:.0f} %" if b else "—"


def paraules(t):
    return len((t or "").split())


def apta_traductor(f, dubtos_ok=False):
    """`arab_dubtos` (lector d'àrab propi: lectures que discrepen o poca confiança) NO és apta per al traductor; per a l'ASR sí
    (dubtos_ok=True): decisió del director del 18-11-2026, només afegeix una condició, no toca cap llindar."""
    if f.get("arab_dubtos") and not dubtos_ok:
        return False
    return (not f.get("credits") and (f.get("tifinag_conf") or 0) >= 0.85 and (f.get("tifinag_dubtosos") or 0) <= 2
            and ((f.get("arab_acord") or 0) >= 0.5 or (f.get("arab_lectures") == 1 and f.get("arab")))
            and f.get("catala_estat") in ("confirmat", "tercer") and 2 <= paraules(f.get("tifinag")) <= 30)


def talls_durades(carpeta, files):
    """Comprovació dels talls (#601): la durada de cada wav ha de ser la de la rèplica ± 0,5 s (03 hi afegeix 0,25 s a cada banda) i la carpeta
    ha de dur `talls/intervals.json` (el registre que 03 desa quan talla: sense ell, els wav poden ser d'una lectura vella). Menys del 99 %
    o sense registre = el capítol NO és apte per a l'ASR."""
    import wave
    amb = [f for f in files if f.get("tall")]
    ok = 0
    for f in amb:
        try:
            with wave.open(os.path.join(carpeta, f["tall"])) as w:
                d = w.getnframes() / w.getframerate()
        except Exception:
            continue
        ok += abs(d - (f["t_fi"] - f["t_ini"])) <= 0.52
    validats = os.path.exists(os.path.join(carpeta, "talls", "intervals.json"))
    pct = round(100 * ok / len(amb), 1) if amb else None
    return {"talls_total": len(amb), "talls_durada_ok": ok, "talls_durada_pct": pct, "talls_validats": validats,
            "capitol_apte_asr": bool(validats and pct is not None and pct >= 99)}


def numeros(files, est):
    D = [f for f in files if not f.get("credits")]
    dur = [f["durada"] for f in D]
    ab = [f["chrf_ab"] for f in D if f.get("chrf_ab") is not None]
    ta = [f["chrf_tif_ar"] for f in D if f.get("chrf_tif_ar") is not None]
    multi = [f for f in D if (f.get("arab_lectures") or 0) > 1]
    conf = [f["tifinag_conf"] for f in D if f.get("tifinag_conf")]
    aptes = [f for f in D if apta_traductor(f)]
    c02 = est.get("02_llegeix", {}).get("comptes", {})
    c04 = est.get("04_tradueix", {}).get("comptes", {})
    n = {
        "slug": est.get("slug"), "video": est.get("video"), "alt": est.get("alt"), "durada_video": est.get("durada"),
        "repliques_total": len(files), "credits": len(files) - len(D), "dialeg": len(D),
        "segons_amb_text": sum(dur), "durada_mediana": mitj(dur, statistics.median), "durada_mitjana": mitj(dur),
        "arab_lectures_total": sum(f.get("arab_lectures") or 0 for f in D), "arab_acord_mitja": mitj([f.get("arab_acord") for f in D]),
        "arab_multi": len(multi), "arab_unanimes": sum(1 for f in multi if f.get("arab_acord") == 1.0),
        "tifinag_conf_mitjana": mitj(conf), "tifinag_glifs": sum(f.get("tifinag_glifs") or 0 for f in D),
        "tifinag_dubtosos": sum(f.get("tifinag_dubtosos") or 0 for f in D), "tifinag_amb_text": sum(1 for f in D if f.get("tifinag")),
        "chrf_ab_mitja": mitj(ab), "catala_estats": {e: sum(1 for f in D if f.get("catala_estat") == e) for e in ("confirmat", "tercer", "descartat")},
        "chrf_tif_ar_mitja": mitj(ta), "chrf_tif_ar_sobre_0_5": sum(1 for c in ta if c >= 0.5), "chrf_tif_ar_n": len(ta),
        "aptes_traductor": len(aptes), "aptes_asr_durada": sum(1 for f in D if apta_traductor(f, True) and f["durada"] >= 0.8), "aptes_asr": None,
        "arab_dubtoses": sum(1 for f in D if f.get("arab_dubtos")),
        "aptes_so_tifinag": sum(1 for f in D if (f.get("tifinag_conf") or 0) >= 0.85 and (f.get("tifinag_dubtosos") or 0) <= 2 and 2 <= paraules(f.get("tifinag")) <= 30),
        "capitol_apte": (len(aptes) / max(1, len(D))) >= 0.6,
        "fitxes_visio": c02.get("fitxes_visio"), "crides_visio": c02.get("crides_visio"), "metode_arab": c02.get("metode"),
        "fotogrames_arab_usats": c02.get("fotogrames_llegits"), "fitxes_visio_equivalents": (c02.get("fotogrames_llegits") or 0) * 172,
        "fitxes_text": c04.get("fitxes_text"),
        "minuts_maquina": round(sum(est.get(e, {}).get("comptes", {}).get("segons") or 0 for e in ("02_llegeix", "03_talla", "04_tradueix")) / 60, 1),
    }
    n["tifinag_glifs_sobre_0_85"] = (n["tifinag_glifs"] - n["tifinag_dubtosos"]) if n["tifinag_glifs"] else 0
    return n, aptes


def varietat(files, est):
    cat_p = os.environ.get("TD_CATALEG")
    if not cat_p or not os.path.exists(cat_p):
        return None
    tr = comu.translitera()
    if tr is None:
        return None
    refs = {
        "Aït Mraw / Beni Mellal": lambda r, v: (r or "").startswith(("Beni Mellal", "Aït Mraw", "Ait Mraw")),
        "Souss": lambda r, v: (r or "").startswith("Souss") or (v == "shi" and not r),
        "Atles Mitjà": lambda r, v: v == "zgh" or (r or "").startswith("Atles"),
    }

    def mots(text, ja_llati=False):
        if not text:
            return []
        cl = text if ja_llati and not any("ⴰ" <= c <= "⵿" for c in text) else tr(text)
        return [m for m in re.split(r"[^\w]+", comu.normalitza(cl)) if len(m) > 1 and not m.isdigit()]

    aptes = [f for f in files if apta_traductor(f)] or [f for f in files if not f.get("credits") and (f.get("tifinag_conf") or 0) >= 0.85]
    cap = Counter()
    for f in aptes:
        cap.update(mots(f["tifinag"]))
    with io.open(cat_p, encoding="utf-8") as fh:
        cat = json.load(fh)
    if isinstance(cat, dict):
        cat = cat.get("drills") or list(cat.values())[0]
    vocab = {g: Counter() for g in refs}
    frases = {g: 0 for g in refs}
    for x in cat:
        t = x.get("text_tachelhit") or ""
        if not t.strip():
            continue
        for g, tria in refs.items():
            if tria(x.get("region"), x.get("variety")):
                vocab[g].update(mots(t, ja_llati=True)); frases[g] += 1
    top200 = [m for m, _ in cap.most_common(200)]
    res = {"formes": len(cap), "aparicions": sum(cap.values()), "repliques": len(aptes), "refs": {}, "control": {}}
    for g, V in vocab.items():
        gram = set(m for m, _ in V.most_common(60))
        gram_cap = [m for m in cap if m in gram]
        res["refs"][g] = {"frases": frases[g], "formes": len(V),
                          "top200": round(sum(1 for m in top200 if m in V) / max(1, len(top200)), 3),
                          "gramaticals": round(sum(cap[m] for m in gram_cap) / max(1, sum(cap.values())), 3),
                          "gramaticals_formes": len(gram_cap)}
    noms = list(refs)
    for i, g in enumerate(noms):
        for h in noms[i + 1:]:
            A, B = vocab[g], vocab[h]
            ta = [m for m, _ in A.most_common(200)]
            res["control"][f"{g} ↔ {h}"] = round(sum(1 for m in ta if m in B) / max(1, len(ta)), 3)
    totes = Counter()
    for V in vocab.values():
        totes.update(V)
    res["noves"] = [(m, c) for m, c in cap.most_common() if m not in totes][:25]
    return res


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
    cand = [f for f in files if not f.get("credits") and f.get("tifinag") and f.get("arab")]
    random.seed(llavor)
    mostra = sorted(random.sample(cand, min(n, len(cand))), key=lambda f: f["k"])
    os.makedirs(os.path.join(carpeta, "mostra"), exist_ok=True)
    fnt = font(18)
    for i, f in enumerate(mostra):
        t = (f["t_ini"] + f["t_fi"]) / 2
        png = os.path.join(carpeta, "mostra", f"ull_{i:02d}_k{f['k']}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                        f"crop={ample}:{round((y1 - y0) * s)}:0:{round(y0 * s)},scale=1920:-1", png], check=False)
        if not os.path.exists(png):
            continue
        im = Image.open(png).convert("RGB")
        full = Image.new("RGB", (im.width, im.height + 150), "black")
        full.paste(im, (0, 0))
        d = ImageDraw.Draw(full)
        d.text((8, im.height + 4), f"[{i}] {f['id']} {f['t_ini']}-{f['t_fi']}s   tifinag: {f['tifinag']}", font=fnt, fill="yellow")
        d.text((8, im.height + 32), f"catala_a: {f.get('catala_a', '')}", font=fnt, fill="white")
        d.text((8, im.height + 60), f"catala_b: {f.get('catala_b', '')}", font=fnt, fill=(220, 220, 220))
        d.text((8, im.height + 88), f"catala_de_tifinag: {f.get('catala_de_tifinag', '')}", font=fnt, fill=(160, 220, 255))
        d.text((8, im.height + 116), f"chrf_ab {f.get('chrf_ab')}  estat {f.get('catala_estat')}  chrf_tif_ar {f.get('chrf_tif_ar')}  acord arab {f.get('arab_acord')}  conf tif {f.get('tifinag_conf')}", font=fnt, fill=(200, 200, 200))
        full.save(png)
        f["full"] = "mostra/" + os.path.basename(png)
    return mostra


def informe(carpeta, files, num, mostra, est, var, cap):
    L = []
    w = L.append
    w(f"# {cap.get('titol') or num['slug']}: informe de la fàbrica ({time.strftime('%Y-%m-%d')})")
    w("")
    w(f"slug `{num['slug']}` · font {cap.get('font', '?')} · programa {cap.get('programa', '?')} · convidat {cap.get('convidat') or '—'} · "
      f"durada {num['durada_video']} s · vídeo {est.get('ample')}x{est.get('alt')}")
    w("")
    w("Material de la SNRT (permís del 17-11-2026: recerca, no republicar). Res va a la biblioteca pública.")
    w("")
    w("## Rèpliques")
    w("")
    w("| | |"); w("|---|---|")
    w(f"| rèpliques totals / crèdits / diàleg | {num['repliques_total']} / {num['credits']} / **{num['dialeg']}** |")
    w(f"| segons amb text / mediana de durada | {num['segons_amb_text']} s / {num['durada_mediana']} s |")
    w(f"| OCR àrab: lectures, acord mitjà, unànimes entre les de ≥ 2 lectures | {num['arab_lectures_total']}, {num['arab_acord_mitja']}, {num['arab_unanimes']} de {num['arab_multi']} ({pc(num['arab_unanimes'], num['arab_multi'])}); mètode: {num['metode_arab']} |")
    w(f"| OCR tifinag: conf mitjana, glifs ≥ 0,85, dubtosos | {num['tifinag_conf_mitjana']}, {pc(num['tifinag_glifs_sobre_0_85'], num['tifinag_glifs'])}, {num['tifinag_dubtosos']} (vídeo de {est.get('02_llegeix', {}).get('comptes', {}).get('tifinag_alt')}p; {num['tifinag_amb_text']} rèpliques amb text) |")
    e = num["catala_estats"]
    w(f"| traducció: chrf_ab mitjà, confirmat / tercer / descartat | {num['chrf_ab_mitja']}, {e['confirmat']} / {e['tercer']} / {e['descartat']} ({pc(e['confirmat'], num['dialeg'])} / {pc(e['tercer'], num['dialeg'])} / {pc(e['descartat'], num['dialeg'])}) |")
    w(f"| chrf_tif_ar mitjà i ≥ 0,5 (mesura del traductor, no porta) | {num['chrf_tif_ar_mitja']}, {num['chrf_tif_ar_sobre_0_5']} de {num['chrf_tif_ar_n']} ({pc(num['chrf_tif_ar_sobre_0_5'], num['chrf_tif_ar_n'])}) |")
    w(f"| talls: durada = t_fi − t_ini ± 0,5 s (cal ≥ 99 %) i `talls/intervals.json` | {num['talls_durada_ok']} de {num['talls_total']} ({num['talls_durada_pct']} %); registre {'sí' if num['talls_validats'] else 'NO'}; capítol {'apte' if num['capitol_apte_asr'] else "**NO apte per a l ASR**"} |")
    w(f"| **portes (§5)**: aptes per al traductor / per a l'ASR | **{num['aptes_traductor']}** ({pc(num['aptes_traductor'], num['dialeg'])}; capítol {'apte' if num['capitol_apte'] else 'NO apte (< 60 %)'}) / {num['aptes_asr_durada']} per durada, CER de l'ASR no mesurat |")
    w(f"| cost: fitxes de visió / de text per model | {num['fitxes_visio']} pagades ara ({num['crides_visio']} crides); {num['fotogrames_arab_usats']} fotogrames d'àrab usats ≈ {num['fitxes_visio_equivalents']} fitxes si es paguessin tots / {num['fitxes_text']} |")
    w(f"| minuts de màquina (02–04) | {num['minuts_maquina']} |")
    w("")
    if var:
        w("## Varietat (§6.1, punts 1–3; la decisió és del director)")
        w("")
        w(f"{var['repliques']} rèpliques, {var['formes']} formes normalitzades ({var['aparicions']} aparicions).")
        w("")
        w("| referència | frases | de les 200 formes més freqüents del capítol | paraules gramaticals (60 més freqüents de la referència): pes al capítol |"); w("|---|---|---|---|")
        for g, r in var["refs"].items():
            w(f"| {g} | {r['frases']} | {100 * r['top200']:.0f} % | {100 * r['gramaticals']:.0f} % ({r['gramaticals_formes']} formes) |")
        w("")
        w("Control entre referències (top 200 de l'una dins l'altra): " + "; ".join(f"{k}: {100 * v:.0f} %" for k, v in var["control"].items()) + ".")
        w("")
        w("Formes freqüents que no té cap referència: " + " ".join(f"{m}({c})" for m, c in var["noves"]) + ".")
        w("")
        w("`varietat_capitol`: **desconeguda** (pendent del director, amb les persones de §3.2 i el punt 4 de §6.1, que no es fa aquí).")
        w("")
    w(f"## {len(mostra)} rèpliques a ull (llavor 1114, `mostra/ull_NN_kK.png`)")
    w("")
    w("| # | id | t | àrab | tifinag | català | estat | chrf_tif_ar | judici |")
    w("|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(mostra):
        w(f"| {i} | {f['id']} | {f['t_ini']} | {f['arab']} | {f['tifinag']} | {f.get('catala') or f.get('catala_a', '')} | {f.get('catala_estat')} | {f.get('chrf_tif_ar')} | pendent |")
    w("")
    w("El judici d'una paraula («bé» / «OCR» / «traducció» / «resum») l'ha de posar algú mirant les imatges: la màquina no es jutja sola.")
    w("")
    w("## Problemes i decisions pendents")
    w("")
    avis = est.get("02_llegeix", {}).get("comptes", {}).get("avis")
    if avis:
        w(f"- {avis}")
    if not num["capitol_apte_asr"]:
        w(f"- Els talls no estan validats ({num['talls_durada_pct']} % amb la durada que toca; registre d'intervals {'sí' if num['talls_validats'] else 'NO'}): el capítol NO és apte per a l'ASR fins que 03 els refaci.")
    if not num["capitol_apte"]:
        w(f"- El capítol no passa la porta del 60 % ({pc(num['aptes_traductor'], num['dialeg'])} d'aptes): el director decideix (geometria, so, lector).")
    w("- La porta de l'ASR (CER ≤ 0,4 contra el tifinag) no està mesurada: cal decidir quin transcriptor i on corre.")
    w("- `varietat_capitol` i les persones (§3.2): pendents del director.")
    w("")
    w("Fitxers: `subtitols.jsonl` (§3.3), `talls/`, `lectures.jsonl`, `tif/`, `numeros.json`, `estat.json`, `fabrica.log`.")
    with io.open(os.path.join(carpeta, "INFORME.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def linia_informe_nit(num, cap):
    arrel = comu.td_tv()
    d = os.path.join(arrel, "_informes")
    try:
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, time.strftime("%Y-%m-%d") + ".md")
        nou = not os.path.exists(p)
        with io.open(p, "a", encoding="utf-8") as f:
            if nou:
                f.write(f"# Fàbrica de Tamazight TV: {time.strftime('%Y-%m-%d')}\n\n| hora | slug | mena | diàleg | aptes traductor | confirmat | chrf_ab | tifinag conf | fitxes visió | capítol |\n|---|---|---|---|---|---|---|---|---|---|\n")
            f.write(f"| {time.strftime('%H:%M')} | {num['slug']} | {cap.get('mena', '?')} | {num['dialeg']} | {num['aptes_traductor']} | "
                    f"{num['catala_estats']['confirmat']} | {num['chrf_ab_mitja']} | {num['tifinag_conf_mitjana']} | {num['fitxes_visio']} | "
                    f"{'apte' if num['capitol_apte'] else 'NO apte'} |\n")
    except OSError:
        pass


def fitxa_del_cataleg(slug):
    p = os.path.join(comu.td_tv(), "cataleg", "capitols.jsonl")
    for x in comu.jsonl_llegeix(p):
        if slug and slug in (x.get("slug"), x.get("slug_forja"), x.get("youtube_id")):
            x = dict(x)
            x.setdefault("font", x.get("cami_per_omissio") or ("replay" if x.get("url_snrt") else "youtube"))
            x.setdefault("mena", "entrevista" if "tadfi" in (x.get("programa") or "") else "desconeguda")
            return x
    return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--mostra", type=int, default=20)
    ap.add_argument("--llavor", type=int, default=1114)
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    comu.carrega_geometria(carpeta)      # #601: una sèrie amb l'ordre de les línies invertit té la seva geometria al capítol
    log = comu.obre_log(carpeta)
    comu.etapa_inici(carpeta, ETAPA)
    t0 = time.time()
    try:
        files = comu.subtitols(carpeta)
        if not files:
            raise RuntimeError("sense subtitols.jsonl")
        est = comu.estat_llegeix(carpeta)
        cap = fitxa_del_cataleg(est.get("slug"))
        if cap.get("varietat"):
            for f in files:
                f["varietat_capitol"] = cap["varietat"]
            comu.desa_subtitols(carpeta, files)
        comu.diu(log, f"== {ETAPA} {comu.ara()}")
        num, aptes = numeros(files, est)
        num.update(talls_durades(carpeta, files))
        var = varietat(files, est)
        if var:
            num["varietat"] = var
        with io.open(os.path.join(carpeta, "numeros.json"), "w", encoding="utf-8") as f:
            json.dump(num, f, ensure_ascii=False, indent=1)
        mostra = mostra_a_ull(carpeta, files, est, a.mostra, a.llavor)
        with io.open(os.path.join(carpeta, "mostra_ull.json"), "w", encoding="utf-8") as f:
            json.dump(mostra, f, ensure_ascii=False, indent=1)
        informe(carpeta, files, num, mostra, est, var, cap)
        linia_informe_nit(num, cap)
        comu.etapa_fi(carpeta, ETAPA, {"dialeg": num["dialeg"], "aptes_traductor": num["aptes_traductor"], "capitol_apte": num["capitol_apte"], "capitol_apte_asr": num["capitol_apte_asr"], "talls_durada_pct": num["talls_durada_pct"],
                                       "segons": round(time.time() - t0)})
        comu.diu(log, f"{ETAPA}: {num['dialeg']} de diàleg, {num['aptes_traductor']} aptes, chrf_ab {num['chrf_ab_mitja']} -> INFORME.md")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {e}")
        raise


if __name__ == "__main__":
    main()
