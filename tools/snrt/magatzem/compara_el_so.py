"""El tall d'audio que va escoltar l'orella conte la veu de la seva replica?

Es baixa `talls.tar` d'un episodi dolent i d'un bo, i de cada tall es mesura:
  - quant de so hi ha (RMS) i quant de silenci,
  - i si el tall de la fabrica i el tros del MEU video a les mateixes marques de temps son el
    mateix so (es comparen les dues envolupants d'energia; si son el mateix moment, es
    corresponen; si no, no).

Aixi es separa «el model no entén aquest parlant» de «el tall no porta el moment que toca».
"""
import io, os, subprocess, tarfile, tempfile, wave
from pathlib import Path

import numpy as np

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")
from huggingface_hub import hf_hub_download  # noqa: E402

REPO = "josepabloucr/tamazight-tv-privat"
CASOS = [("hmssyuzoyqzywbajgargfzkflkuppdermxyipydr", "dolent 0,4%"),
         ("bueyrhjvjyaleocffcrxdtmeqfpfgqqwauwesbrw", "bo 41,7%")]
TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"
TMP.mkdir(exist_ok=True)


def llegeix_wav(p):
    with wave.open(str(p)) as w:
        n, sr = w.getnframes(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a, sr


def envolupant(a, sr, passos=40):
    t = np.array_split(a, passos)
    return np.array([float(np.sqrt((x ** 2).mean())) if len(x) else 0. for x in t])


for slug, etiqueta in CASOS:
    tar = hf_hub_download(REPO, f"capitols/{slug}/talls.tar", repo_type="dataset",
                          token=os.environ["HF_TOKEN"])
    dest = TMP / slug
    if not dest.exists():
        dest.mkdir(parents=True)
        with tarfile.open(tar) as z:
            try:
                z.extractall(dest, filter="data")
            except TypeError:
                z.extractall(dest)
    wavs = sorted(Path(dest).rglob("*.wav"))
    print(f"\n=== {slug[:16]}  {etiqueta}:  {len(wavs)} talls")
    if not wavs:
        print("   dins del tar:", [p.name for p in Path(dest).rglob('*')][:8])
        continue
    rms, silenci, corr = [], [], []
    vid = Path(r"E:/tamazight/_videos") / f"{slug}.mp4"
    import json
    temps = {}
    for i, l in enumerate(io.open(f"E:/tamazight/_visor/{slug}/subtitols.jsonl", encoding="utf-8")):
        if l.strip():
            x = json.loads(l)
            temps[str(x.get("k", i))] = (x.get("t_ini"), x.get("t_fi"))
    for w in wavs[::max(1, len(wavs) // 25)][:25]:
        a, sr = llegeix_wav(w)
        if not len(a):
            continue
        r = float(np.sqrt((a ** 2).mean()))
        rms.append(r)
        marcs = envolupant(a, sr)
        silenci.append(float((marcs < .005).mean()))
        k = w.stem.split("_")[-1].lstrip("0") or "0"
        ti, tf = temps.get(k, (None, None))
        if ti is None or not vid.exists():
            continue
        p2 = TMP / "meu.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ti), "-t",
                        str(max(.3, float(tf) - float(ti))), "-i", str(vid), "-ac", "1",
                        "-ar", str(sr), "-y", str(p2)], check=False)
        if p2.exists():
            b, _ = llegeix_wav(p2)
            if len(b) > sr // 10:
                m2 = envolupant(b, sr)
                if m2.std() > 1e-6 and marcs.std() > 1e-6:
                    corr.append(float(np.corrcoef(marcs, m2)[0, 1]))
    print(f"so mitja (RMS) {np.mean(rms):.4f} | tall en silenci {100*np.mean(silenci):.0f}% "
          f"del temps | durada mitjana {np.mean([len(llegeix_wav(w)[0])/llegeix_wav(w)[1] for w in wavs[:10]]):.1f} s")
    if corr:
        print(f"el tall de la fabrica i el meu video al mateix instant: correlacio "
              f"{np.mean(corr):+.2f}  (n={len(corr)})")
