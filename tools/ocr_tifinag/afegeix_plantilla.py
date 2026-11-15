"""afegeix_plantilla.py: afegeix a plantilles.npz un grup de glifs nous etiquetat a ull.
Us: python -X utf8 afegeix_plantilla.py <video_id> <nouNN> <etiqueta>   (despres, torna a passar llegeix.py)"""
import json, os, sys, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
vid, nou, etiqueta = sys.argv[1], sys.argv[2], sys.argv[3]
idx = json.load(open(os.path.join(AQUI, f"nous_{vid}.json"), encoding="utf-8"))[nou]
T = np.load(os.path.join(AQUI, f"teles_{vid}.npy"))
z = np.load(os.path.join(AQUI, "plantilles.npz"), allow_pickle=True)
ets = [str(e) for e in z["etiquetes"]]; ims = list(z["imatges"])
nova = T[idx].mean(axis=0)
if etiqueta in ets:
    j = ets.index(etiqueta); ims[j] = (ims[j] + nova) / 2
else:
    ets.append(etiqueta); ims.append(nova)
np.savez_compressed(os.path.join(AQUI, "plantilles.npz"), etiquetes=np.array(ets, dtype=object), imatges=np.stack(ims))
reg = os.path.join(AQUI, "plantilles_afegides.json")
r = json.load(open(reg, encoding="utf-8")) if os.path.exists(reg) else []
r.append({"video": vid, "grup": nou, "etiqueta": etiqueta, "n": len(idx)})
json.dump(r, open(reg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{etiqueta}: {len(idx)} glifs de {vid}/{nou} -> plantilles.npz ({len(ets)} plantilles)")
