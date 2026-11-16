# -*- coding: utf-8 -*-
"""Aplica canvis.json a producció (Postgres de Render, DATABASE_URL de backend/.env.prod), directament a
la taula drills, sense engegar traducció a l'àrab ni veu (equival a quiet=true).
ÚS: aplica.py            → prova: diu què faria i no escriu res
    aplica.py --escriu   → escriu, en una sola transacció, i desa aplicat.json amb l'estat anterior
Només toca files que encara porten «traduit-per-maquina» i el mateix text_catalan que quan es van auditar."""
import io, json, os, sys
from datetime import datetime
import psycopg2
from dotenv import dotenv_values

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"  # carpeta de dades, fora del repositori
ESCRIU = "--escriu" in sys.argv
url = dotenv_values(r"C:\Users\josep\app2\tachelhit-drills\backend\.env.prod").get("DATABASE_URL")
if not url:
    sys.exit("falta DATABASE_URL a backend/.env.prod")
canvis = json.load(io.open(os.path.join(AQUI, "canvis.json"), encoding="utf-8"))
con = psycopg2.connect(url)
cur = con.cursor()
cur.execute("SELECT id, text_catalan, tag FROM drills WHERE id = ANY(%s)", ([c["id"] for c in canvis],))
ara = {i: (t, g) for i, t, g in cur.fetchall()}
fets, saltats, abans = 0, [], []
for c in canvis:
    t, g = ara.get(c["id"], (None, None))
    if t is None or "traduit-per-maquina" not in (g or "") or (t or "").strip() != (c["abans"] or "").strip():
        saltats.append(c["id"])
        continue
    abans.append({"id": c["id"], "text_catalan": t, "tag": g})
    if c["mena"] == "confirmada":
        if ESCRIU:
            cur.execute("UPDATE drills SET text_catalan = %s, tag = %s, updated_at = %s WHERE id = %s",
                        (c["text_catalan"], c["tag"], datetime.utcnow(), c["id"]))
    else:
        if ESCRIU:
            cur.execute("UPDATE drills SET tag = %s, updated_at = %s WHERE id = %s", (c["tag"], datetime.utcnow(), c["id"]))
    fets += 1
if ESCRIU:
    con.commit()
    json.dump(abans, io.open(os.path.join(AQUI, "aplicat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
con.close()
n_conf = sum(1 for c in canvis if c["mena"] == "confirmada")
print(f"{'ESCRIT' if ESCRIU else 'PROVA (res escrit)'}: {fets} canvis ({n_conf} confirmades, {len(canvis) - n_conf} descartades al fitxer); "
      f"saltats {len(saltats)} (ja canviats a producció): {saltats[:10]}")
