# -*- coding: utf-8 -*-
"""Baixa el catàleg de producció a raigs de 500 i el desa a cataleg_prod.json."""
import io, json, os, requests, sys
API = "https://tachelhit-drills-api.onrender.com"
os.makedirs(AQUI, exist_ok=True)
tot = []
off = 0
while True:
    r = requests.get(f"{API}/drills", params={"limit": 500, "offset": off}, timeout=120)
    r.raise_for_status()
    p = r.json()
    tot.extend(p)
    total = int(r.headers.get("X-Total-Count", "0"))
    print(off, len(p), total, flush=True)
    off += 500
    if not p or off >= total:
        break
json.dump(tot, io.open(os.path.join(AQUI, "cataleg_prod.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("desats", len(tot))
