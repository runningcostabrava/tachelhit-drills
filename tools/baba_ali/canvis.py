"""Casa un episodi amb una pujada MUDA mirant QUAN CANVIA el subtitol de la imatge.

PER QUE AIXI. Les pujades dels episodis 7 i 9 venen sense so de YouTube (-91 dB, silenci
absolut), segurament per una reclamacio de la musica, i la correlacio de la banda sonora --amb
que vam casar els altres deu-- no hi serveix. Llegir l'arab tampoc: el Tesseract no se'n surt
amb aquests subtitols. Pero no cal llegir-los. A la franja de baix hi ha gairebe sempre text, i
el que marca el ritme de l'episodi es el moment en que un subtitol deixa lloc al seguent. Les
nostres marques de temps son exactament aixo: l'instant de cada linia.

  · del VIDEO: la franja, binaritzada (nomes el blanc del text) i reduida a una graella. Entre
    fotograma i fotograma es mira quant ha canviat: quan entra un subtitol nou, el canvi es
    gran; mentre s'aguanta, es gairebe zero.
  · de NOSALTRES: un pols a cada marca, eixamplat mig segon perque les marques son en segons
    sencers i el pols ha de poder caure a banda i banda.

Es correlacionen els dos trens de polsos per a tot desplacament. El resultat es diu en z: quantes
desviacions tipiques treu el millor desplacament a tots els altres. Un episodi que hi es de debo
en fa desenes; si no hi es, el millor desplacament es un numero qualsevol i el z es baix.

LA PROVA DEL NOU. De l'episodi 7 ja en sabem el desplacament per un altre cami: el fotograma del
segon 600 diu «أما أنت فتوقدين النار من دون حطب», que es la nostra linia del segon 730 i no surt
enlloc mes de la serie; per tant -130. Si aquest guio retroba -130 tot sol, es pot creure quan
digui el de l'episodi 9.

US: canvis.py <id_del_video> [episodi ...]
"""
import io
import json
import os
import subprocess
import sys

import numpy as np

import marques

AQUI = os.path.dirname(os.path.abspath(__file__))
#: on son els .mp4 baixats i on es desa la mesura; cap de les dues coses va al repositori
VIDEO = os.environ.get("TD_VIDEOS", os.path.join(AQUI, "video"))
CAU = os.environ.get("TD_CAU_CANVIS", os.path.join(AQUI, "_canvis"))

FPS = 4.0
GRAELLA = (8, 64)   #: files x columnes a que es redueix la franja binaritzada
LLINDAR = 200       #: el text es gairebe blanc; l'escena, rarament
FRANJA = "crop=1280:120:0:572"
AMPLE_POLS = 0.5    #: segons a banda i banda de cada marca nostra


def canvis_del_video(vid):
    """Quant canvia la franja de text entre fotograma i fotograma."""
    os.makedirs(CAU, exist_ok=True)
    cau = os.path.join(CAU, f"{vid}.npy")
    if os.path.exists(cau):
        return np.load(cau)
    files, cols = GRAELLA
    filtre = (f"{FRANJA},format=gray,lut=y='if(gt(val,{LLINDAR}),255,0)',"
              f"fps={FPS},scale={cols}:{files}:flags=area")
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i",
                        os.path.join(VIDEO, f"{vid}.mp4"), "-vf", filtre,
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    crua = np.frombuffer(p.stdout, dtype=np.uint8)
    n = len(crua) // (files * cols)
    graelles = crua[:n * files * cols].reshape(n, files * cols).astype(np.float32)
    dif = np.abs(np.diff(graelles, axis=0)).sum(axis=1)
    dif = np.concatenate([[0.0], dif]).astype(np.float32)
    np.save(cau, dif)
    return dif


def polsos_nostres(marques_s, n, t0):
    s = np.zeros(n, dtype=np.float32)
    w = int(AMPLE_POLS * FPS)
    for t in marques_s:
        i = int(round((t - t0) * FPS))
        if 0 <= i < n:
            s[max(0, i - w):min(n, i + w + 1)] = 1.0
    return s


def correlacio(a, b):
    a = a - a.mean()
    b = b - b.mean()
    n = 1
    while n < len(a) + len(b):
        n *= 2
    return np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)[:len(b)]


def mira(vid, episodis, calla=False):
    dif = canvis_del_video(vid)
    #: nomes interessa ON hi ha canvi, no com de gran; aixi un tall d'escena no mana
    senyal = np.minimum(dif, np.percentile(dif, 97)).astype(np.float32)
    minuts = len(senyal) / FPS / 60
    if not calla:
        print(f"vídeo {vid}: {minuts:.1f} min\n")
        print(f"{'episodi':8s} {'desplaçament':>13s} {'z':>7s} {'2n z':>7s}  {'línies':>7s}  diu")
    per_ep = marques.carrega()
    fora = {}
    for ep in episodis:
        files = per_ep.get(ep)
        if not files:
            continue
        temps = [f[0] for f in files]
        t0 = temps[0]
        llarg = int((temps[-1] - t0) * FPS) + 1
        if llarg >= len(senyal):
            if not calla:
                print(f"{ep:<8d} {'—':>13s}  l'episodi no hi cap")
            continue
        nostre = polsos_nostres(temps, llarg, t0)
        c = correlacio(nostre, senyal)[:len(senyal) - llarg]
        z = (c - c.mean()) / (c.std() or 1.0)
        i = int(np.argmax(z))
        fosc = z.copy()
        fosc[max(0, i - int(10 * FPS)):i + int(10 * FPS)] = -1e9
        segon = float(fosc.max())
        despl = i / FPS - t0
        bo = z[i] > 8 and z[i] > 2.0 * max(segon, 1.0)
        if not calla:
            print(f"{ep:<8d} {despl:>13.2f} {z[i]:>7.1f} {segon:>7.1f}  {len(files):>7d}  "
                  f"{'SÍ' if bo else 'no'}")
        fora[ep] = {"desplacament": round(despl, 2), "z": round(float(z[i]), 1),
                    "segon_z": round(segon, 1), "accepta": bool(bo), "linies": len(files)}
    json.dump(fora, io.open(os.path.join(AQUI, f"canvis_{vid}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return fora


if __name__ == "__main__":
    vid = sys.argv[1]
    eps = [int(a) for a in sys.argv[2:]] or sorted(marques.carrega())
    mira(vid, eps)
