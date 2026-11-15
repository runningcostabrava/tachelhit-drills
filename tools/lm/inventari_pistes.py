# -*- coding: utf-8 -*-
"""Inventari pista a pista d'un canal o llista de YouTube: per a cada vídeo, quines pistes de
subtítols HUMANES hi ha (i sota quin codi), quina llengua ha endevinat YouTube per als
automàtics, durada i títol. És el pas zero de tota font de vídeo (#623, front B): la pista
amaziga va penjada sota codis falsos («ak», «af», «wo»…) i cap cerca per llengua la troba.

Fa servir `player_client=android` (el client per omissió dona vídeos públics per «no
disponibles») i va d'un en un, a poc a poc.

ÚS: inventari_pistes.py <url del canal/llista> <sortida.tsv>
    columnes: id, durada, subtítols manuals, llengua dels automàtics (-orig), títol
    Imprimeix el recompte final: vídeos, minuts, quants amb pista manual i quins codis.
"""
import collections
import io
import json
import os
import subprocess
import sys

CODIS_SOSPITOSOS = {"ak", "af", "aa", "wo", "am", "ay", "ber", "zgh", "tzm", "shi", "kab", "rif", "tmh"}


def ytdlp(*args):
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--extractor-args", "youtube:player_client=android", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def llista(url):
    out = ytdlp("--flat-playlist", "--print", "%(id)s", url)
    return [l.strip() for l in out.splitlines() if l.strip()]


def fitxa(vid):
    out = ytdlp("-j", "--skip-download", f"https://www.youtube.com/watch?v={vid}")
    try:
        d = json.loads(out)
    except ValueError:
        return None
    auto = d.get("automatic_captions") or {}
    orig = [k for k in auto if k.endswith("-orig")]
    return {"id": d["id"], "durada": d.get("duration") or 0, "manuals": sorted(d.get("subtitles") or {}),
            "auto": orig[0] if orig else "", "titol": (d.get("title") or "").replace("\t", " ")}


if __name__ == "__main__":
    url, fora = sys.argv[1], sys.argv[2]
    fets = {}
    if os.path.exists(fora):
        for l in io.open(fora, encoding="utf-8"):
            p = l.rstrip("\n").split("\t")
            if len(p) >= 5:
                fets[p[0]] = p
    ids = llista(url)
    print(len(ids), "vídeos a la llista ·", len(fets), "ja fets", flush=True)
    with io.open(fora, "a", encoding="utf-8") as g:
        for i, vid in enumerate(ids):
            if vid in fets:
                continue
            f = fitxa(vid)
            if not f:
                g.write(f"{vid}\tERROR\t\t\t\n")
                continue
            g.write(f"{f['id']}\t{f['durada']}\t{','.join(f['manuals'])}\t{f['auto']}\t{f['titol']}\n")
            g.flush()
            if i % 10 == 9:
                print(i + 1, flush=True)
    files = [l.rstrip("\n").split("\t") for l in io.open(fora, encoding="utf-8")]
    files = [p for p in files if len(p) >= 5 and p[1] != "ERROR"]
    amb = [p for p in files if p[2]]
    codis = collections.Counter(c for p in amb for c in p[2].split(","))
    sosp = [p for p in amb if set(p[2].split(",")) & CODIS_SOSPITOSOS]
    print(f"{len(files)} vídeos · {sum(float(p[1] or 0) for p in files) / 60:.0f} min · {len(amb)} amb pista manual "
          f"({sum(float(p[1] or 0) for p in amb) / 60:.0f} min) · codis: {dict(codis.most_common(8))}")
    print(f"{len(sosp)} amb un codi sospitós d'amagar amazic ({sum(float(p[1] or 0) for p in sosp) / 60:.0f} min)")
    print("llengua dels automàtics:", dict(collections.Counter(p[3] or "—" for p in files).most_common(6)))
