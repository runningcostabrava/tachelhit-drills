# -*- coding: utf-8 -*-
"""Etapa 03: els talls de so (§4): `talls/<id>.wav` mono 16 kHz, de t_ini − 0,25 a t_fi + 0,25, retallats als
límits del vídeo; els crèdits no es tallen. Reprèn per id: el tall que ja hi és no es refà.

  python -X utf8 03_talla.py <carpeta_del_capitol>
"""
import argparse
import json
import os
import subprocess
import wave
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "03_talla"


def durada_wav(p):
    try:
        with wave.open(p) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return None


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
        refets = 0
        p_reg = os.path.join(talls, "intervals.json")
        try:
            reg = json.load(open(p_reg, encoding="utf-8"))
        except Exception:
            reg = {}
        so = 0.0
        for f in files:
            if f.get("credits"):
                f["tall"] = None
                continue
            ini = max(0.0, f["t_ini"] - comu.MARGE_TALL)
            fin = min(durada, f["t_fi"] + comu.MARGE_TALL)
            desti = os.path.join(talls, f["id"] + ".wav")
            # un tall només es reutilitza si el registre diu que es va tallar d'aquest interval i la durada del wav hi quadra
            # (si 02 s'ha refet, els ids es reaprofiten amb altres t_ini/t_fi i el wav vell no hi correspon); si no, es refà
            d = durada_wav(desti) if os.path.exists(desti) else None
            interval = [round(ini, 2), round(fin, 2)]
            if d is None or reg.get(f["id"]) != interval or abs(d - (fin - ini)) > 0.06:
                refets += d is not None
                reg[f["id"]] = interval
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.2f}", "-to", f"{fin:.2f}", "-i", audio, "-ac", "1", "-ar", "16000", desti], check=True)
                nous += 1
            f["tall"] = "talls/" + f["id"] + ".wav"
            so += fin - ini
        json.dump(reg, open(p_reg, "w", encoding="utf-8"))
        marca = os.path.join(carpeta, "talls_no_validats.txt")   # posat a mà quan es van trobar talls vells; ja no val
        if os.path.exists(marca):
            os.remove(marca)
        comu.desa_subtitols(carpeta, files)
        try:    # porta d'alineació so<->text (només escriu talls/alineacio.json; si falla, la fàbrica segueix i el transcriptor no hi confia)
            import porta_alineacio
            porta_alineacio.main_carpeta(carpeta, files)
        except Exception as e:
            comu.diu(log, f"{ETAPA}: porta d'alineació no feta ({type(e).__name__}: {e})")
        comptes = {"talls": sum(1 for f in files if f.get("tall")), "talls_nous": nous, "talls_refets_per_durada": refets, "segons_so": round(so, 1), "segons": round(time.time() - t0)}
        comu.etapa_fi(carpeta, ETAPA, comptes)
        comu.diu(log, f"{ETAPA}: {comptes['talls']} talls ({nous} nous), {comptes['segons_so']} s de so, {comptes['segons']} s")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {e}")
        raise


if __name__ == "__main__":
    main()
