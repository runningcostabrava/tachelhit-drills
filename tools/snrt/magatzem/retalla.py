"""Aplica l'alineacio forcada als talls: fora el silenci del davant i del darrere.

**Per que.** L'alineacio de l'ECS sobre 4.788 talls diu que **el 51 % del so no es la frase**:
0,79 s de silenci al davant (al 84 % dels talls) i 0,97 s al darrere (al 95 %). Mesurat sobre
250 talls amb MMS-1b-all + shi, el mateix model i la mateixa referencia, nomes canviant si el
wav es sencer o retallat, el CER baixa (vegeu `prova_retall/`).

⚠️ **Cap dels dos numeros del paragraf de dalt mesura el que diu** (quadern, §48 i §49), i es
deixen escrits per no fer com si no s'haguessin cregut. El 51 % el va donar una alineacio que
no va rebre mai la frase: el vocabulari de l'adaptador `shi` es llati i el text anava en
tifinag, aixi que alineava nomes els separadors de paraula. I el CER que baixa no prova que la
frontera sigui bona: amb el CER de partida per sobre d'1 la distancia esta dominada per
insercions i escurcar el so en treu, encerti o no -- menjar-se 0,3 s de veu real de cada banda
guanya tres vegades mes (-0,1913) que retallar be (-0,0741).

El que fa aquest guio -- treure el que l'alineador diu que no es la frase, amb marge -- segueix
sent el que cal fer, i ara amb fronteres que si que han vist la frase. El que no se sap es
**quant val**, i no ho pot dir cap CER d'inferencia: ho ha de dir l'experiment d'entrenament
amb un test de durada fixa (`kaggle/retall-sencer-contra-retallat.py`).

**El marge.** La frontera que torna l'alineador no es exacta -- es el primer i l'ultim
fotograma de 20 ms amb veu -- i tallar-hi arran es menja el principi d'una oclusiva. Per aixo
s'hi deixen 0,15 s a banda i banda.

**Que NO fa.** No esborra l'original. Escriu els retallats en una carpeta nova, perque si la
mesura surt malament es pugui tornar enrere sense haver perdut res.

    python retalla.py <carpeta_talls> <carpeta_desti> [--marge 0.15]
"""
import argparse
import io
import json
import sys
from pathlib import Path

#: v2 = amb el text transliterat. El fitxer sense sufix es deia igual i portava fronteres
#: fetes alineant NOMES els separadors de paraula (vegeu la §48 del quadern): es diu ara
#: *_NOMES_SEPARADORS.jsonl i no es pot agafar sense voler.
ALI = Path(r"E:/tamazight/_magatzem/alineacio_ecs_v2.jsonl")


def llegeix_alineacio(p=ALI):
    d, mal = {}, 0
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            x = json.loads(l)
        except Exception:
            mal += 1          # l'ECS pot estar escrivint-hi: l'ultima linia queda a mitges
            continue
        if x.get("veu_ini") is not None and x.get("veu_fi") is not None:
            d[x["so"]] = x
    return d, mal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("origen")
    ap.add_argument("desti")
    ap.add_argument("--marge", type=float, default=0.15)
    ap.add_argument("--alineacio", default=str(ALI))
    ap.add_argument("--min-veu", type=float, default=0.3,
                    help="per sota d'aixo el tall es descarta: no hi ha frase")
    a = ap.parse_args()

    import soundfile as sf

    ali, mal = llegeix_alineacio(Path(a.alineacio))
    print(f"{len(ali)} talls amb alineació ({mal} línies a mitges, saltades)")

    org, des = Path(a.origen), Path(a.desti)
    des.mkdir(parents=True, exist_ok=True)
    wavs = sorted(org.glob("*.wav"))
    fet = sense = curt = 0
    guanyat = 0.0
    for w in wavs:
        x = ali.get(w.name)
        if not x:
            sense += 1
            continue
        s, sr = sf.read(str(w))
        if s.ndim > 1:
            s = s.mean(axis=1)
        i0 = max(0, int((x["veu_ini"] - a.marge) * sr))
        i1 = min(len(s), int((x["veu_fi"] + a.marge) * sr))
        if (i1 - i0) < sr * a.min_veu:
            curt += 1
            continue
        guanyat += (len(s) - (i1 - i0)) / sr
        sf.write(str(des / w.name), s[i0:i1], sr)
        fet += 1
        if fet % 500 == 0:
            print(f"   {fet} retallats…", flush=True)

    print(f"\n   {fet} retallats · {sense} sense alineació · {curt} massa curts")
    print(f"   silenci tret: {guanyat/60:.0f} min")
    if fet:
        print(f"   de mitjana {guanyat/fet:.2f} s per tall")


if __name__ == "__main__":
    sys.exit(main())
