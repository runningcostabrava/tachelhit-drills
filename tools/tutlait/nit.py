# -*- coding: utf-8 -*-
"""La cadena de la nit de TutlAit: espera que tradueix_ar_ca.py acabi (traduccions.jsonl amb totes les
files de metadades no a producció), i llavors fes_pendents → audita_arab → audita_tercer → resum →
prepara_import → carrega (prova). No escriu a producció. Tot queda a nit.log.
ÚS: nit.py"""
import io, json, os, subprocess, sys, time

PY = r"C:\Users\josep\app2\tachelhit-drills\backend\venv\Scripts\python.exe"
AQUI = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.normpath(os.path.join(AQUI, "..", "lm", "auditors_traduccions"))
CARPETA = r"C:\Users\josep\Veus-tachelhit\_paquets\tutlait"
AUDIT = r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors_tutlait"
LOG = io.open(os.path.join(CARPETA, "nit.log"), "a", encoding="utf-8")


def diu(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def corre(guio, *args):
    diu("→", os.path.basename(guio), *args)
    r = subprocess.run([PY, "-X", "utf8", guio, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for l in (r.stdout or "").splitlines()[-12:]:
        diu("  ", l)
    if r.returncode != 0:
        diu("  ERROR", (r.stderr or "")[-1500:])
        sys.exit(1)


def esperats():
    return sum(1 for l in io.open(os.path.join(CARPETA, "metadades.jsonl"), encoding="utf-8")
               if l.strip() and not json.loads(l)["ja_a_produccio"] and json.loads(l)["text_arabic"])


def fets():
    p = os.path.join(CARPETA, "traduccions.jsonl")
    return sum(1 for l in io.open(p, encoding="utf-8") if l.strip()) if os.path.exists(p) else 0


n = esperats()
while fets() < n:
    diu("traduccions", fets(), "de", n)
    time.sleep(300)
diu("traducció acabada:", fets(), "de", n)
# repassa les que van quedar buides per error (reprèn només les que falten o són buides)
corre(os.path.join(AQUI, "fes_pendents.py"), CARPETA, AUDIT)
corre(os.path.join(AUD, "audita_arab.py"), AUDIT)
corre(os.path.join(AUD, "audita_tercer.py"), AUDIT)
corre(os.path.join(AUD, "resum.py"), AUDIT)
corre(os.path.join(AQUI, "prepara_import.py"), CARPETA, AUDIT)
corre(os.path.join(AQUI, "carrega.py"))
diu("nit acabada: import.jsonl a punt; carrega.py --escriu és del propietari")
