# -*- coding: utf-8 -*-
r"""Baixa un vídeo del replay de la SNRT (snrt.ma → reproductor de forja.ma) per a recerca.

Permís: la SNRT va autoritzar el 17-11-2026 l'ús dels seus canals de YouTube i del replay com a font
d'investigació (traductor i transcriptor de veu), sense republicar (docs/PERMISOS.md).

Com funciona el replay: la pàgina de snrt.ma incrusta un reproductor de forja.ma; el reproductor
porta a l'estat de la pàgina un `stream_url` de l'API (api.forja.ma/pages/proxy/content/<id>/stream_url)
que diu on és la llista HLS (vod.forja.ma/vod/SNRT/<num>/playlist.m3u8); i aquesta llista es demana
amb una fitxa d'accés temporal que dona token.forja.ma/prod?url=<llista>. Amb la llista amb fitxa,
yt-dlp (amb ffmpeg) baixa el vídeo.

ÚS (des de Claude, en Pablo amb «!», o des de PowerShell):
  python -X utf8 tools/snrt/baixa_replay.py <URL de snrt.ma o de forja.ma/player/...> [--nomes-url] [--carpeta DIR] [--qualitat 720]
Per omissió desa a C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay\<slug>.mp4 i un .json al costat
amb el títol i les adreces. --nomes-url només imprimeix la llista amb fitxa (per provar sense baixar).
"""
import argparse, concurrent.futures, html, io, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tachelhit-drills/recerca"
CAPS = {"User-Agent": UA, "Referer": "https://forja.ma/", "Origin": "https://forja.ma", "Accept": "*/*"}
# Només cal python 3 i ffmpeg al PATH: corre igual al PC i a l'ECS (forja.ma no bloqueja per país com YouTube).
CARPETA = os.environ.get("TD_REPLAY") or (r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay" if os.name == "nt" else os.path.expanduser("~/tamazight_tv/replay"))


def llegeix(url, caps=CAPS):
    req = urllib.request.Request(url, headers=caps)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def slug_del_reproductor(url):
    m = re.search(r"forja\.ma/player/([a-z0-9]+)", url)
    if m:
        return m.group(1), url
    html = llegeix(url)
    m = re.search(r"https://forja\.ma/player/([a-z0-9]+)[^\"']*", html)
    if not m:
        sys.exit("a la pàgina no hi ha cap reproductor de forja.ma")
    titol = re.search(r"<title>([^<]*)</title>", html)
    return m.group(1), (titol.group(1).strip() if titol else url)


def estat_del_reproductor(slug):
    html = llegeix(f"https://forja.ma/player/{slug}?lang=ar").replace("\\u002F", "/")
    m = re.search(r'stream_url:"(https://api\.forja\.ma/[^"]+)"', html)
    if not m:
        sys.exit("el reproductor no porta cap stream_url (ha canviat la pàgina?)")
    titol = re.search(r"<title>([^<]*)</title>", html)
    tokenitzat = bool(re.search(r"is_tokenized:(true|!0)", html))
    return m.group(1), (titol.group(1).strip() if titol else slug), tokenitzat


def llista_hls(stream_api):
    cos = llegeix(stream_api)
    try:
        d = json.loads(cos)
    except ValueError:
        d = {}
    cadenes = []
    def recull(x):
        if isinstance(x, dict):
            for v in x.values(): recull(v)
        elif isinstance(x, list):
            for v in x: recull(v)
        elif isinstance(x, str):
            cadenes.append(x)
    recull(d)
    if not cadenes:
        cadenes = re.findall(r"https?://[^\s\"']+", cos)
    for c in cadenes:
        if "m3u8" in c:
            return c
    sys.exit(f"l'API no ha donat cap llista m3u8: {cos[:300]}")


def amb_fitxa(llista):
    if "token=" in llista:
        return llista
    cos = llegeix("https://token.forja.ma/prod?url=" + urllib.parse.quote(llista, safe=""))
    try:
        d = json.loads(cos)
        for v in (d.values() if isinstance(d, dict) else []):
            if isinstance(v, str) and "m3u8" in v:
                return v
            if isinstance(v, dict):
                for w in v.values():
                    if isinstance(w, str) and "m3u8" in w:
                        return w
    except ValueError:
        pass
    m = re.search(r"https?://[^\s\"']+m3u8[^\s\"']*", cos)
    if m:
        return m.group(0)
    # El 17-11-2026 el servidor contesta només la cua de consulta, amb els «&» escapats en HTML:
    # «token=…&amp;token_path=…&amp;expires=…». S'enganxa a la llista.
    cua = html.unescape(cos.strip().strip('"'))
    if "token=" in cua:
        return llista + ("&" if "?" in llista else "?") + cua.lstrip("?&")
    sys.exit(f"el servidor de fitxes no ha donat cap llista: {cos[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--nomes-url", action="store_true")
    ap.add_argument("--carpeta", default=CARPETA)
    ap.add_argument("--qualitat", type=int, default=720, help="alçada màxima (720 per a l'OCR dels subtítols; 1080 si cal)")
    a = ap.parse_args()

    slug, titol_pagina = slug_del_reproductor(a.url)
    stream_api, titol, tokenitzat = estat_del_reproductor(slug)
    if titol.lower().startswith("forja"):
        titol = titol_pagina.split("|")[0].strip()  # el reproductor porta un títol genèric; el bo és a snrt.ma
    print("títol:", titol, "| slug:", slug, flush=True)
    llista = llista_hls(stream_api)
    print("llista:", llista, flush=True)
    final = amb_fitxa(llista)
    print("llista amb fitxa:", re.sub(r"(token|token_path)=[^&]+", r"\1=…", final), flush=True)
    if a.nomes_url:
        print(final)
        return
    os.makedirs(a.carpeta, exist_ok=True)
    sortida = os.path.join(a.carpeta, slug + ".mp4")
    json.dump({"url_pagina": a.url, "titol": titol, "titol_pagina": titol_pagina, "slug": slug, "stream_api": stream_api,
               "llista": llista, "fitxer": sortida, "permis": "SNRT 17-11-2026, recerca, no republicar"},
              io.open(sortida[:-4] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # yt-dlp no passa la fitxa (la cua de consulta) als trossos: 403. Ho baixem nosaltres.
    baixa_hls(llista, sortida, a.qualitat)


def _baixa_tros(url, cua, desti, fitxa_nova):
    """Un tros .ts amb la fitxa; si la fitxa ha caducat (403), en demana una de nova i torna a provar."""
    for intent in range(4):
        try:
            req = urllib.request.Request(url + "?" + cua[0], headers=CAPS)
            with urllib.request.urlopen(req, timeout=120) as r, io.open(desti, "wb") as f:
                while True:
                    b = r.read(1 << 16)
                    if not b:
                        break
                    f.write(b)
            return
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and intent < 3:
                cua[0] = fitxa_nova()
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if intent == 3:
                raise
            time.sleep(3)


def baixa_hls(llista, sortida, qualitat=720, fils=6):
    """Llista mestra → variant de vídeo (≤ qualitat) i pista d'àudio → trossos amb fitxa → ffmpeg."""
    def fitxa_nova():
        return amb_fitxa(llista).split("?", 1)[1]
    cua = [fitxa_nova()]
    mestra = llegeix(llista + "?" + cua[0])
    variants, audio = [], None
    linies = mestra.splitlines()
    for i, l in enumerate(linies):
        if l.startswith("#EXT-X-MEDIA:") and "TYPE=AUDIO" in l:
            m = re.search(r'URI="([^"]+)"', l)
            if m:
                audio = m.group(1)
        if l.startswith("#EXT-X-STREAM-INF:"):
            m = re.search(r"RESOLUTION=(\d+)x(\d+)", l)
            alt = int(m.group(2)) if m else 0
            variants.append((alt, linies[i + 1].strip()))
    if not variants:
        sys.exit("la llista mestra no té variants")
    aptes = [v for v in variants if v[0] <= qualitat] or [min(variants)]
    alt, uri_video = max(aptes)
    print(f"variant {alt}p: {uri_video}" + (f" | àudio: {audio}" if audio else ""), flush=True)
    tmp = sortida[:-4] + "_trossos"
    os.makedirs(tmp, exist_ok=True)
    parts = []
    for nom, uri in (("video", uri_video), ("audio", audio)):
        if not uri:
            continue
        base = urllib.parse.urljoin(llista, uri)
        mitja = llegeix(base + "?" + cua[0])
        trossos = [urllib.parse.urljoin(base, l.strip()) for l in mitja.splitlines() if l.strip() and not l.startswith("#")]
        print(f"{nom}: {len(trossos)} trossos", flush=True)
        fitxers = []
        with concurrent.futures.ThreadPoolExecutor(fils) as ex:
            futurs = []
            for k, url in enumerate(trossos):
                desti = os.path.join(tmp, f"{nom}_{k:05d}.ts")
                fitxers.append(desti)
                if os.path.exists(desti) and os.path.getsize(desti) > 0:
                    continue
                futurs.append(ex.submit(_baixa_tros, url, cua, desti, fitxa_nova))
            for n, f in enumerate(concurrent.futures.as_completed(futurs), 1):
                f.result()
                if n % 50 == 0:
                    print(f"  {nom} {n}/{len(futurs)}", flush=True)
        junt = os.path.join(tmp, nom + ".ts")
        with io.open(junt, "wb") as out:
            for p in fitxers:
                out.write(io.open(p, "rb").read())
        parts.append(junt)
    ordre = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in parts:
        ordre += ["-i", p]
    ordre += ["-c", "copy", "-movflags", "+faststart", sortida]
    print("ffmpeg →", sortida, flush=True)
    if subprocess.call(ordre) != 0:
        sys.exit("ffmpeg ha fallat; els trossos queden a " + tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    print("fet:", sortida, round(os.path.getsize(sortida) / 1e6, 1), "MB", flush=True)


if __name__ == "__main__":
    main()
