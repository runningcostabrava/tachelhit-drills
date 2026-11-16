# -*- coding: utf-8 -*-
"""Carrega import.jsonl a producció, fila a fila: puja el so a R2 (magatzem.puja, carpeta
tachelhit/tutlait) i insereix el drill directament al Postgres de Render (DATABASE_URL de
backend/.env.prod), sense engegar traducció ni veu sintètica (l'àrab ja hi és; el català confirmat no
necessita res més). Reprèn: cada fila feta s'apunta a carregat.jsonl amb el seu id de producció.
ÚS: carrega.py            → prova: compta, comprova el so i no escriu res
    carrega.py --escriu [--max N]   → carrega (per defecte totes; --max per anar per tandes)
L'executa el propietari."""
import io, json, os, sys, time
from datetime import datetime
import psycopg2
from dotenv import dotenv_values, load_dotenv

CARPETA = r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
BACKEND = r"C:\Users\josep\app2\tachelhit-drills\backend"
ESCRIU = "--escriu" in sys.argv
MAX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 0
load_dotenv(os.path.join(BACKEND, ".env"), override=True)  # claus d'R2
sys.path.insert(0, BACKEND)
import magatzem

url = dotenv_values(os.path.join(BACKEND, ".env.prod")).get("DATABASE_URL")
if not url:
    sys.exit("falta DATABASE_URL a backend/.env.prod")
if not magatzem.a_r2():
    sys.exit("R2 no configurat a backend/.env: el so no tindria on anar")

files = [json.loads(l) for l in io.open(os.path.join(CARPETA, "import.jsonl"), encoding="utf-8") if l.strip()]
p_fets = os.path.join(CARPETA, "carregat.jsonl")
fets = set()
if os.path.exists(p_fets):
    for l in io.open(p_fets, encoding="utf-8"):
        if l.strip():
            fets.add(json.loads(l)["id_tutlait"])
pend = [f for f in files if f["id_tutlait"] not in fets]
sense_so = [f for f in pend if not os.path.exists(f["audio"])]
print(f"import.jsonl: {len(files)} files; ja carregades {len(fets)}; pendents {len(pend)}; sense fitxer de so {len(sense_so)}")
if not ESCRIU:
    conf = sum(1 for f in pend if f.get("text_catalan"))
    print(f"PROVA (res escrit): entrarien {len(pend) - len(sense_so)} drills ({conf} amb català confirmat, la resta com a proposta)")
    sys.exit(0)

COLS = ["tag", "author", "text_catalan", "text_catalan_suggested", "text_arabic", "audio_url", "voice_wanted", "variety", "region",
        "speaker", "source_url", "source_title", "license", "esborranys", "date_created", "updated_at"]
con = psycopg2.connect(url)
cur = con.cursor()
n = 0
t0 = time.time()
with io.open(p_fets, "a", encoding="utf-8") as out:
    for f in pend:
        if MAX and n >= MAX:
            break
        if not os.path.exists(f["audio"]):
            continue
        nom = f["id_tutlait"] + "_" + str(int(time.time() * 1000))
        adreca = magatzem.puja(f["audio"], "tachelhit/tutlait", nom, mena="so")
        ara = datetime.utcnow()
        vals = [f["tag"], f["author"], f.get("text_catalan"), f.get("text_catalan_suggested"), f["text_arabic"], adreca, False,
                f["variety"], f["region"], f["speaker"], f["source_url"], f["source_title"], f["license"], f.get("esborranys"), ara, ara]
        cur.execute(f"INSERT INTO drills ({', '.join(COLS)}) VALUES ({', '.join(['%s'] * len(COLS))}) RETURNING id", vals)
        nou = cur.fetchone()[0]
        con.commit()
        out.write(json.dumps({"id_tutlait": f["id_tutlait"], "id": nou, "audio_url": adreca}, ensure_ascii=False) + "\n")
        out.flush()
        n += 1
        if n % 100 == 0:
            print(n, "carregats", f"{time.time() - t0:.0f} s", flush=True)
        time.sleep(0.2)  # una cua lenta: el Render no hi intervé, però R2 i el Postgres tampoc no cal apallissar-los
con.close()
print(f"ESCRIT: {n} drills nous en {time.time() - t0:.0f} s")
