# -*- coding: utf-8 -*-
"""Ajunta metadades.jsonl (el tall: so, parlant, varietat), traduccions.jsonl (el català de Qwen) i el
veredicte dels auditors (canvis.json de resum.py: confirmada / descartada; la resta, proposta) en un
sol import.jsonl, una fila per drill tal com entrarà a la biblioteca:
- confirmada per dos auditors → text_catalan = el text acordat, etiqueta traduit-per-auditors;
- sense acord → text_catalan buit i text_catalan_suggested = el de Qwen, etiqueta traduit-per-maquina;
- descartada per dos → es queda fora (no entra res que dos auditors diguin que és fals).
L'àrab va a text_arabic (és una traducció, no una transcripció: així ho diu la nota). Res d'amazic
escrit: el lector hi posarà la seva proposta més endavant.
ÚS: prepara_import.py [<carpeta tutlait>] [<carpeta auditors>]"""
import io, json, os, sys

CARPETA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
AUDIT = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors_tutlait"
FONT = "https://huggingface.co/datasets/Ma-OpenHub/Tutlait-v1"
TITOL = "Tutlait v1: Tamazight Speech with Arabic Translations"
NOTA = "àrab del corpus (traducció, no transcripció); català de màquina auditat"

meta = {}
for l in io.open(os.path.join(CARPETA, "metadades.jsonl"), encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        meta[x["id"]] = x
trad = {}
for l in io.open(os.path.join(CARPETA, "traduccions.jsonl"), encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        trad[x["id"]] = x
canvis = {}
p = os.path.join(AUDIT, "canvis.json")
if os.path.exists(p):
    for c in json.load(io.open(p, encoding="utf-8")):
        canvis[c["id"]] = c

comptes = {"confirmada": 0, "proposta": 0, "descartada": 0, "sense traducció": 0, "ja a producció": 0}
n = 0
with io.open(os.path.join(CARPETA, "import.jsonl"), "w", encoding="utf-8") as out:
    for ident, m in meta.items():
        if m["ja_a_produccio"]:
            comptes["ja a producció"] += 1
            continue
        t = trad.get(ident)
        if not t or not (t.get("text_catalan") or "").strip():
            comptes["sense traducció"] += 1
            continue
        c = canvis.get(ident)
        base = {"id_tutlait": ident, "audio": m["audio"], "text_arabic": m["text_arabic"], "variety": m["variety"], "region": m["region"],
                "speaker": m["speaker"], "source_url": FONT, "source_title": TITOL, "license": "CC BY 4.0", "author": "tamazight.drills",
                "voice_wanted": False, "duration": m["duration"], "verified_corpus": m["verified"], "split": m["split"]}
        if c and c["mena"] == "descartada":
            comptes["descartada"] += 1
            continue
        if c and c["mena"] == "confirmada":
            fila = dict(base, text_catalan=c["text_catalan"], text_catalan_suggested=None,
                        tag="tutlait, font externa, sense text, per-escriure, traduit-per-auditors",
                        esborranys=json.dumps([{"text": t["text_catalan"], "model": t["model"], "llengua": "ca", "de": "l'àrab del corpus",
                                               "auditors": c.get("auditors", [])}], ensure_ascii=False))
            comptes["confirmada"] += 1
        else:
            fila = dict(base, text_catalan=None, text_catalan_suggested=t["text_catalan"],
                        tag="tutlait, font externa, sense text, per-escriure, traduit-per-maquina",
                        esborranys=json.dumps([{"text": t["text_catalan"], "model": t["model"], "llengua": "ca", "de": "l'àrab del corpus"}], ensure_ascii=False))
            comptes["proposta"] += 1
        out.write(json.dumps(fila, ensure_ascii=False) + "\n")
        n += 1
print("files a import.jsonl:", n, comptes)
