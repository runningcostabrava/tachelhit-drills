"""Provar NOMES la part de carregar dades del quadern de Kaggle, aqui i sense GPU.

Per que: el quadern `retall-sencer-contra-retallat.py` no s'ha executat mai. La primera
vegada que corri sera a Kaggle, amb GPU, i un error de camins hi gastaria una sessio sencera
per una errada de dues lletres. Aqui es proven les parts que no demanen GPU:

  * `carpeta_de()` troba les dues cares dins de /kaggle/input
  * `llegeix()` llegeix els jsonl i els wav
  * **l'assercio que les dues cares tenen les MATEIXES files** -- que es el que fa que
    l'experiment signifiqui alguna cosa

Es simula /kaggle/input amb una carpeta local.
"""
import io
import json
import os
import sys
from pathlib import Path

ARREL = Path(r"E:/tamazight/_magatzem/prova_kaggle/kaggle/input")
QUADERN = Path(r"E:/tamazight/_magatzem/kaggle_retall/retall-sencer-contra-retallat.py")
SR = 16000
SEGONS_MAXIM = 14

#: el codi del quadern fins a la linia del model: s'executa tal qual, canviant nomes l'arrel
codi = io.open(QUADERN, encoding="utf-8").read()
tall = codi.index("# ---------------------------------------------------------------------------------- el model")
cap = codi[:tall].replace('"/kaggle/input"', f'r"{ARREL}"')
#: fora la instal·lacio de paquets i el CUDA_VISIBLE_DEVICES: aqui no toquen
cap = cap.replace('subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",\n'
                  '                "transformers>=4.44", "librosa", "soundfile"], check=False)', "pass")

ns = {"__name__": "__prova__"}
try:
    exec(compile(cap, str(QUADERN), "exec"), ns)
except AssertionError as e:
    print(f"\n   L'ASSERCIO HA SALTAT (i aixo esta be si les cares no casen): {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n   ERROR carregant: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n   la part de carregar del quadern funciona:")
for cara in ("sencer", "retallat"):
    d = {p: len(v) for p, v in ns["material"][cara].items()}
    print(f"      {cara}: {d}")
print(f"      test (sencer per a totes dues): {len(ns['TEST'])}")
print("      l'asserció de files iguals ha passat")
