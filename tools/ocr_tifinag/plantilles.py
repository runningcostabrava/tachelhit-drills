"""plantilles.py: desa les plantilles (mitjana 32x32 de cada etiqueta) per llegir altres videos
del canal amb el mateix tipus de lletra: plantilles.npz (imatges) + plantilles.json (etiqueta, n)."""
import json, os, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(AQUI, "glifs.json"), encoding="utf-8"))
E = json.load(open(os.path.join(AQUI, "etiquetes.json"), encoding="utf-8"))
T = np.load(os.path.join(AQUI, "teles.npy"))
per = {}
for g in G:
    k = f"g{g['grup']:02d}"
    lab = E[k]["glif"]
    if lab in ("", "MARCA") or not E[k].get("segur", True):
        lab = lab or "(meitat)"
    per.setdefault(lab, []).append(g["n"])
noms = sorted(per)
mitjanes = np.stack([T[per[n]].mean(axis=0) for n in noms])
np.savez_compressed(os.path.join(AQUI, "plantilles.npz"), etiquetes=np.array(noms, dtype=object), imatges=mitjanes)
json.dump({n: {"n": len(per[n])} for n in noms}, open(os.path.join(AQUI, "plantilles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(noms), "plantilles:", " ".join(noms))
