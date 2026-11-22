"""El so dels episodis dolents es de banda estreta?

L'orella treu POC text (0,60 paraules per escrita contra 0,80) i no casa amb res: la firma d'un
model davant d'un so que li es estrany. I hi ha una manera que un so de veu neta li sigui estrany
sense que ho vegi ni el nivell ni el silenci -- que ja s'han mirat i son bons: que estigui
retallat d'agut. Un enregistrament de banda estreta (telefon, connexio remota) o molt comprimit
perd tot el que hi ha per damunt dels 4 o 5 kHz, i l'MMS esta entrenat a 16 kHz de banda ampla.

Aixo es veu a l'espectre i no es pot discutir: es mesura quanta energia hi ha per damunt de
4 kHz i de 6 kHz, i quina es la frequencia per sota de la qual hi ha el 95% de l'energia.
"""
import io, json, os, wave, statistics
from pathlib import Path

import numpy as np

TMP = Path(os.environ.get("TEMP", ".")) / "so_snrt"
titols = {}
import glob
for p in glob.glob(r"E:/tamazight/_visor/*/estat.json"):
    s = os.path.basename(os.path.dirname(p))
    titols[s] = json.load(io.open(p, encoding="utf-8"))["titol"].replace("TADFI N TSKLA - ", "")

#: l'acord de cada episodi, per ordenar la taula
acord = {}
for l in io.open(r"E:/tamazight/_magatzem/acord_triat.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        c = acord.setdefault(r["capitol"], [0, 0])
        c[1] += 1
        c[0] += r["grau"] == "A"


def llegeix(p):
    with wave.open(str(p)) as w:
        n, sr = w.getnframes(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a, sr


files = []
for d in sorted(TMP.iterdir()):
    talls = sorted((d / "talls").glob("*.wav")) if (d / "talls").exists() else []
    if len(talls) < 20:
        continue
    alt4, alt6, p95, srs = [], [], [], set()
    for w in talls[::max(1, len(talls) // 20)][:20]:
        a, sr = llegeix(w)
        if a.size < sr // 4:
            continue
        srs.add(sr)
        #: espectre mitja de trossos de 1024 mostres
        n = 1024
        trossos = a[:(a.size // n) * n].reshape(-1, n)
        if not trossos.size:
            continue
        esp = (np.abs(np.fft.rfft(trossos * np.hanning(n), axis=1)) ** 2).mean(0)
        fr = np.fft.rfftfreq(n, 1 / sr)
        tot = esp.sum()
        if tot <= 0:
            continue
        alt4.append(float(esp[fr >= 4000].sum() / tot))
        alt6.append(float(esp[fr >= 6000].sum() / tot))
        acum = np.cumsum(esp) / tot
        p95.append(float(fr[np.searchsorted(acum, .95)]))
    if not alt4:
        continue
    a_, n_ = acord.get(d.name, [0, 1])
    files.append((a_ / max(1, n_), titols.get(d.name, d.name)[:24], statistics.mean(alt4),
                  statistics.mean(alt6), statistics.mean(p95), sorted(srs)))

files.sort(reverse=True)
print(f"{'convidat':<26}{'acord':>7}{'>4 kHz':>9}{'>6 kHz':>9}{'95% sota':>11}{'mostreig':>10}")
for a, t, h4, h6, p, srs in files:
    print(f"{t:<26}{100*a:6.1f}%{100*h4:8.2f}%{100*h6:8.2f}%{p:10.0f} Hz{srs[0]:10d}")

bons = [f for f in files if f[0] > .05]
dolents = [f for f in files if f[0] <= .05]
if bons and dolents:
    print(f"\nenergia per damunt de 4 kHz: bons {100*statistics.mean([f[2] for f in bons]):.2f}%, "
          f"dolents {100*statistics.mean([f[2] for f in dolents]):.2f}%")
    print(f"el 95% de l'energia, per sota de: bons {statistics.mean([f[4] for f in bons]):.0f} Hz, "
          f"dolents {statistics.mean([f[4] for f in dolents]):.0f} Hz")
