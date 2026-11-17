# -*- coding: utf-8 -*-
"""La nit (§4): llegeix `TD_TV/cataleg/capitols.jsonl`, ordena per `prioritat` i després per `mena` (entrevistes
abans que sèries), i per a cada capítol pendent fa 01 (baixar) → 02 → 03 → 04 → 05. Reprenible: una etapa que
`estat.json` ja dona per feta (fi sense error) es salta, i cada etapa reprèn per dins. L'`estat` del capítol al
catàleg passa a «fet» o «error» (amb la `nota`). Registre a `TD_TV/nit.log`. A l'ECS: `tmux new -s nit` i deixar-ho.

  python -X utf8 nit.py [--cataleg RUTA] [--nomes SLUG ...] [--refes] [--fils 6] [--sense-baixar] [--un-per-segon] [--lector-arab visio|propi]
  python -X utf8 nit.py <carpeta> [<carpeta> ...]      # sense catàleg: aquestes carpetes, 02 → 05

01 baixa: `font` = «replay» → `tools/snrt/baixa_replay.py <url> --carpeta TD_TV/<slug> --nom video` (va bé des de
l'ECS); «youtube» → `python -m yt_dlp` del venv (només des del PC: l'ECS té la IP bloquejada; llavors es puja el
720p amb scp i la nit el troba ja baixat). L'etapa 06 (publicar al dataset privat) no és aquí encara.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPES = ["02_llegeix", "03_talla", "04_tradueix", "05_informe"]
ORDRE_MENA = {"entrevista": 0, "debat": 1, "cultural": 2, "informatiu": 3, "infantil": 4, "musical": 5, "serie": 6}
BAIXA_REPLAY = os.path.join(os.path.dirname(comu.AQUI), "baixa_replay.py")


def te_video(c):
    return os.path.isdir(c) and comu.video_de(c) is not None


def fitxa(cap):
    """Els camps de §3.1 a partir del catàleg real (el del peó snrt-cataleg porta slug_forja, url_snrt, youtube_id…)."""
    slug = cap.get("slug") or cap.get("slug_forja") or cap.get("youtube_id")
    url = cap.get("url") or cap.get("url_snrt") or (f"https://www.youtube.com/watch?v={cap['youtube_id']}" if cap.get("youtube_id") else "")
    font = cap.get("font") or ("replay" if cap.get("url_snrt") or cap.get("slug_forja") else "youtube")
    if cap.get("cami_per_omissio") in ("youtube", "replay"):
        font = cap["cami_per_omissio"]
    te_1080 = any("1080" in q for q in (cap.get("qualitats_replay") or []))
    return {"slug": slug, "url": url, "font": font, "mena": cap.get("mena") or ("entrevista" if "tadfi" in (cap.get("programa") or "") else "desconeguda"),
            "prioritat": cap.get("prioritat") or 9, "titol": cap.get("titol", ""), "te_1080": te_1080,
            "youtube": f"https://www.youtube.com/watch?v={cap['youtube_id']}" if cap.get("youtube_id") else None,
            "forja": f"https://forja.ma/player/{cap['slug_forja']}?lang=ar" if cap.get("slug_forja") else None, "programa": cap.get("programa")}


def baixa(f, carpeta, log, amb_1080=True):
    """01: video.mp4 (720p amb so) i, si el replay en té, video_1080.mp4 per al tifinag. Replay des d'on sigui; YouTube només
    des del PC (l'ECS té la IP bloquejada): si el replay falla i hi ha YouTube, es prova."""
    os.makedirs(carpeta, exist_ok=True)
    if f.get("forja") and os.environ.get("TD_REPLAY_FORJA", "1") == "1":   # el replay directe de forja.ma (va bé des de l'ECS) i mai YouTube (IP bloquejada)
        f = dict(f, font="replay", url=f["forja"], youtube=None)

    def replay(qualitat, nom):
        cmd = [comu.PY, "-X", "utf8", BAIXA_REPLAY, f["url"], "--carpeta", carpeta, "--qualitat", str(qualitat)]
        comu.diu(log, f"   01_baixa: replay {qualitat}p {f['url']}")
        r = subprocess.run(cmd)
        if r.returncode != 0:
            return False
        for g in os.listdir(carpeta):   # baixa_replay deixa <slug_forja>.mp4 (+ .json): es reanomena
            if g.lower().endswith(".mp4") and g not in ("video.mp4", "video_1080.mp4"):
                os.replace(os.path.join(carpeta, g), os.path.join(carpeta, nom))
                j = os.path.join(carpeta, g[:-4] + ".json")
                if os.path.exists(j):
                    os.replace(j, os.path.join(carpeta, nom[:-4] + ".json"))
                return True
        return False

    def youtube(url):
        cmd = [comu.PY, "-m", "yt_dlp", "--js-runtimes", "node", "-f", "136+140/bestvideo[height<=720]+bestaudio/best[height<=720]",
               "--merge-output-format", "mp4", "-o", os.path.join(carpeta, "video.%(ext)s"), url]
        comu.diu(log, f"   01_baixa: youtube {url}")
        return subprocess.run(cmd).returncode == 0

    if not te_video(carpeta):
        be = False
        if f["font"] == "replay" and f["url"]:
            be = replay(720, "video.mp4")
        if not be and f.get("youtube"):
            be = youtube(f["youtube"])
        if not be or not te_video(carpeta):
            comu.diu(log, "   01_baixa: ERROR, sense vídeo")
            return False
    if amb_1080 and not os.path.exists(os.path.join(carpeta, "video_1080.mp4")):
        be = False
        if f["font"] == "replay" and f.get("te_1080"):
            be = replay(1080, "video_1080.mp4")
        elif f.get("youtube"):
            cmd = [comu.PY, "-m", "yt_dlp", "--js-runtimes", "node", "-f", "137/bestvideo[height<=1080]", "-o",
                   os.path.join(carpeta, "video_1080.%(ext)s"), f["youtube"]]
            comu.diu(log, "   01_baixa: youtube 1080p (sense so) per al tifinag")
            be = subprocess.run(cmd).returncode == 0
        if not be:
            comu.diu(log, "   01_baixa: el 1080p no ha baixat; el tifinag es llegirà a 720p (avís a l'informe)")
    return True


def corre(carpeta, a, log):
    refer = False   # si una etapa s'ha refet, les següents també es repassen (són reprenibles per id: només fan el que falta)
    for etapa in ETAPES:
        feta = comu.etapa_feta(carpeta, etapa)
        if feta and etapa == "02_llegeix" and comu.estat_llegeix(carpeta).get(etapa, {}).get("comptes", {}).get("sense_arab"):
            feta = False   # feta sense àrab (tanda --sense-arab del 17-11-2026): ara cal llegir-lo
        if feta and etapa == "03_talla" and not os.path.exists(os.path.join(carpeta, "talls", "intervals.json")):
            feta = False   # talls sense registre d'intervals: no validats (poden ser d'una lectura vella de 02), es refan
                if not a.refes and feta and not refer:
            comu.diu(log, f"   {etapa}: ja feta"); continue
        cmd = [comu.PY, "-X", "utf8", os.path.join(comu.AQUI, etapa + ".py"), carpeta]
        if etapa == "02_llegeix":
            cmd += ["--fils", str(a.fils)] + (["--un-per-segon"] if a.un_per_segon else []) + (["--lector-arab", a.lector_arab] if a.lector_arab != "visio" else [])
        t0 = time.time()
        r = subprocess.run(cmd)
        comu.diu(log, f"   {etapa}: {'bé' if r.returncode == 0 else 'ERROR ' + str(r.returncode)} en {time.time() - t0:.0f} s")
        if r.returncode != 0:
            err = comu.estat_llegeix(carpeta).get(etapa, {}).get("error") or f"codi {r.returncode}"
            return False, f"{etapa}: {err}"
        refer = True
    return True, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpetes", nargs="*")
    ap.add_argument("--cataleg", default=None)
    ap.add_argument("--nomes", nargs="*", default=None, help="només aquests slugs")
    ap.add_argument("--refes", action="store_true")
    ap.add_argument("--fils", type=int, default=6)
    ap.add_argument("--sense-baixar", action="store_true")
    ap.add_argument("--sense-1080", action="store_true", help="no baixar també el 1080p del replay per al tifinag")
    ap.add_argument("--un-per-segon", action="store_true")
    ap.add_argument("--lector-arab", choices=["visio", "propi"], default="visio", help="propi: CRNN propi sense visió (candidat; marca arab_dubtos)")
    a = ap.parse_args()
    arrel = comu.td_tv()
    os.makedirs(arrel, exist_ok=True)
    log = open(os.path.join(arrel, "nit.log"), "a", encoding="utf-8")
    if a.carpetes:
        comu.diu(log, f"==== nit {comu.ara()} {len(a.carpetes)} carpetes")
        for c in a.carpetes:
            c = os.path.abspath(c)
            comu.diu(log, f"-- {os.path.basename(c)}")
            if not te_video(c):
                comu.diu(log, "   sense vídeo, salto"); continue
            be, motiu = corre(c, a, log)
            comu.diu(log, f"   {'fet' if be else 'ERROR ' + motiu}")
        comu.diu(log, f"==== nit acabada {comu.ara()}")
        return
    cat_p = a.cataleg or os.path.join(arrel, "cataleg", "capitols.jsonl")
    caps = comu.jsonl_llegeix(cat_p)
    if not caps:
        sys.exit(f"cap capítol a {cat_p}")
    # El catàleg es rellegeix abans de triar cada capítol i s'hi desa només la fila d'aquest capítol: qui reencua un capítol (estat
    # «pendent», fila al final) mentre la nit corre no es perd, i ningú no el trepitja (#601: capítols amb talls no validats).
    intentats = set()

    def cua(caps):
        fitxes = [fitxa(c) for c in caps]
        ordre = sorted(range(len(caps)), key=lambda i: (fitxes[i]["prioritat"], ORDRE_MENA.get(fitxes[i]["mena"], 9), i))
        pend = [i for i in ordre if ((caps[i].get("estat") or "pendent") != "fet" or a.refes) and fitxes[i]["slug"] not in intentats]
        if a.nomes:
            pend = [i for i in pend if fitxes[i]["slug"] in a.nomes]
        return fitxes, pend

    def desa_fila(slug, **camps):
        fresc = comu.jsonl_llegeix(cat_p)
        for c in fresc:
            if fitxa(c)["slug"] == slug:
                c.update(camps)
        comu.jsonl_escriu(cat_p, fresc)

    fitxes, pendents = cua(caps)
    comu.diu(log, f"==== nit {comu.ara()} {len(pendents)} capítols pendents de {len(caps)} ({cat_p})")
    while True:
        caps = comu.jsonl_llegeix(cat_p)
        fitxes, pendents = cua(caps)
        if not pendents:
            break
        i = pendents[0]
        f = fitxes[i]
        slug = f["slug"]
        intentats.add(slug)
        if not slug:
            continue
        carpeta = os.path.join(arrel, slug)
        comu.diu(log, f"-- {slug} [{f['mena']}, prioritat {f['prioritat']}] {f['titol'][:60]}")
        t0 = time.time()
        if a.sense_baixar and not te_video(carpeta):
            desa_fila(slug, estat="error", nota="01_baixa: sense vídeo (--sense-baixar)"); continue
        if not a.sense_baixar and not baixa(f, carpeta, log, amb_1080=not a.sense_1080):
            desa_fila(slug, estat="error", nota="01_baixa: sense vídeo"); continue
        comu.estat_desa(carpeta, slug=slug, titol=f["titol"], font=f["font"], mena=f["mena"])
        be, motiu = corre(carpeta, a, log)
        desa_fila(slug, estat="fet" if be else "error", nota="" if be else motiu, fet_el=comu.ara())
        comu.diu(log, f"   {slug}: {'fet' if be else 'error'} {motiu} en {(time.time() - t0) / 60:.0f} min")
    comu.diu(log, f"==== nit acabada {comu.ara()}")


if __name__ == "__main__":
    main()
