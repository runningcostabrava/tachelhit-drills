# -*- coding: utf-8 -*-
"""Etapa 03: els talls de so (§4): `talls/<id>.wav` mono 16 kHz, de t_ini − 0,25 a t_fi + 0,25, retallats als
límits del vídeo; els crèdits no es tallen. Reprèn per id: el tall que ja hi és no es refà.

  python -X utf8 03_talla.py <carpeta_del_capitol>
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "03_talla"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    a = ap.parse_args()
    carpeta = os.path.abspath(a.carpeta)
    log = comu.obre_log(carpeta)
    comu.etapa_inici(carpeta, ETAPA)
    t0 = time.time()
    try:
        video = comu.video_de(carpeta)
        _, _, durada = comu.mida_video(video)
        files = comu.subtitols(carpeta)
        if not files:
            raise RuntimeError("sense subtitols.jsonl: cal l'etapa 02")
        comu.diu(log, f"== {ETAPA} {comu.ara()} {len(files)} rèpliques")
        audio = os.path.join(carpeta, "audio16k.wav")
        if not os.path.exists(audio):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", audio], check=True)
        talls = os.path.join(carpeta, "talls")
        os.makedirs(talls, exist_ok=True)
        nous = 0
        so = 0.0
        for f in files:
            if f.get("credits"):
                f["tall"] = None
                continue
            ini = max(0.0, f["t_ini"] - comu.MARGE_TALL)
            fin = min(durada, f["t_fi"] + comu.MARGE_TALL)
            desti = os.path.join(talls, f["id"] + ".wav")
            if not os.path.exists(desti):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.2f}", "-to", f"{fin:.2f}", "-i", audio, "-ac", "1", "-ar", "16000", desti], check=True)
                nous += 1
            f["tall"] = "talls/" + f["id"] + ".wav"
            so += fin - ini
        comu.desa_subtitols(carpeta, files)
        comptes = {"talls": sum(1 for f in files if f.get("tall")), "talls_nous": nous, "segons_so": round(so, 1), "segons": round(time.time() - t0)}
        comu.etapa_fi(carpeta, ETAPA, comptes)
        comu.diu(log, f"{ETAPA}: {comptes['talls']} talls ({nous} nous), {comptes['segons_so']} s de so, {comptes['segons']} s")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {e}")
        raise


if __name__ == "__main__":
    main()
