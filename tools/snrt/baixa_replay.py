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
import argparse, io, json, os, re, subprocess, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tachelhit-drills/recerca"
CAPS = {"User-Agent": UA, "Referer": "https://forja.ma/", "Origin": "https://forja.ma", "Accept": "*/*"}
VENV_PY = r"C:\Users\josep\app2\tachelhit-drills\backend\venv\Scripts\python.exe"
CARPETA = r"C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\replay"


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
    ordre = [VENV_PY, "-X", "utf8", "-m", "yt_dlp", "--no-warnings", "--referer", "https://forja.ma/", "--user-agent", UA,
             "-f", f"bestvideo[height<={a.qualitat}]+bestaudio/best[height<={a.qualitat}]/best",
             "--merge-output-format", "mp4", "-o", sortida, final]
    print("yt-dlp →", sortida, flush=True)
    sys.exit(subprocess.call(ordre))


if __name__ == "__main__":
    main()
