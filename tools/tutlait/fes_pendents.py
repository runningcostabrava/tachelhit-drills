# -*- coding: utf-8 -*-
"""De traduccions.jsonl (el català de Qwen per a cada tall de TutlAit) en fa el pendents.json que
esperen audita_arab.py, audita_tercer.py i resum.py (tools/lm/auditors_traduccions), a la carpeta
d'auditors de TutlAit. Les files sense traducció queden fora (es tornaran a traduir).
ÚS: fes_pendents.py [<carpeta tutlait>] [<carpeta auditors>]"""
import io, json, os, sys

CARPETA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
AUDIT = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors_tutlait"
os.makedirs(AUDIT, exist_ok=True)
TAG = "tutlait, font externa, sense text, per-escriure, traduit-per-maquina"
pend, buides = [], 0
for l in io.open(os.path.join(CARPETA, "traduccions.jsonl"), encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if not (x.get("text_catalan") or "").strip():
        buides += 1
        continue
    pend.append({"id": x["id"], "tag": TAG, "text_arabic": x["text_arabic"], "text_catalan": x["text_catalan"],
                 "text_tachelhit_suggested": None, "source_title": "Tutlait v1 (Ma-OpenHub)"})
json.dump(pend, io.open(os.path.join(AUDIT, "pendents.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("pendents", len(pend), "sense traducció", buides, "→", AUDIT)
