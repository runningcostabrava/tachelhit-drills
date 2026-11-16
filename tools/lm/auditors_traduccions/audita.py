# -*- coding: utf-8 -*-
"""Dos auditors independents (qwen3.8-max i deepseek-chat) sobre les traduccions «traduit-per-maquina»
d'MTNRA i Common Voice que van quedar sense confirmar el 31-10 (pendents.json, 1.643 frases).
Cada auditor veu la frase amaziga, la traducció de la màquina i el diccionari, i respon
TRIA: <text> / FORA / NO-HO-SE. Escriu veredictes.jsonl (reprèn si ja n'hi ha). No toca producció."""
import io, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import requests
from dotenv import load_dotenv

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors"  # carpeta de dades, fora del repositori
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "backend"))
load_dotenv(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", override=True)
load_dotenv(r"C:\Users\josep\app2\nomatrails-seo-pipeline\.env", override=False)
QKEY, QBASE = os.environ["DASHSCOPE_API_KEY"].strip(), os.environ["DASHSCOPE_BASE_URL"].rstrip("/")
DKEY, DBASE = os.environ["DEEPSEEK_API_KEY"].strip(), "https://api.deepseek.com/v1"

AUDITORS = {"qwen": ("qwen3.8-max", QBASE, QKEY), "deepseek": ("deepseek-chat", DBASE, DKEY)}
#: El tercer, per desempatar quan els dos primers no es posen d'acord: raona (i per aixo te mes sostre).
TERCER = {"qwen4": ("qwen4-max", QBASE, QKEY)}
PENSEN = {"qwen4-max"}

ERRORS = ("tihirit=cotxe (no samarreta), tasrɣint=àrab, tifrxin=noies (no ocells), taddart=casa (no poble), "
          "udad=mufló (no conill), tamsulaft=càmera, aftas=platja, asimwas=divendres, alaway=tren, "
          "tilfanidin=pastilles, aɣanib=bolígraf, aqmqum=tabaquera (no bossa), taɣlust=cafè, ixšnn=dolent "
          "(la màquina el gira a «bo»), akrbay=pantalons, ansmaddu=autobús, ablhaw=llebrer, hrima=ratpenat, "
          "acnyal=bandera, tazmalt=exèrcit, imalass=setmana, aḥanu=habitació, asaru=pel·lícula, "
          "andudi=terratrèmol, aɣrf=poble, tikrkas=mentides, aẓalim=ceba, tagʷmart=euga, skkus=seure, "
          "taskla=literatura, rms=entendre (no provar), ungal=novel·la, tantala=dialecte, takkalt=aranya, "
          "tilggʷit=pont, amdlu=núvol, tinɛacin=diners, ardlim=cirera, amssayl=pilot, anmhal=director, "
          "tamddit=vespre, tawla=febre, anbraz=campió, abrsira=gabinet, tanbḍayt=magistratura, agadaz=mercat "
          "(no abocador), tasna=pàgina, tasskart=cistell, amaccu=gat, tafullust=gallina, amsgnaf=metge, "
          "sbuxrur=roncar, ɣir=córrer, taẓuṛi=art, timɣrit=classe, aɣzu=presó, tamhla=direcció, "
          "tafrmlit=infermera, tanfult=bitllet, sɣawsa=necessitar, tayyu=camaleó, azlalam=bicicleta, "
          "simraw=vint, abrray=ferida, aɣrab=paret, ayda=fortuna, abariq=bufetada, abufuck=gavina, "
          "ayaẓiḍ=gall, ssaɣ=comprar.")

SISTEMA = (
    "Ets un auditor de traduccions de l'amazic (taixelhit i tamazight de l'Atles central, Marroc) al català. "
    "T'arriba una frase amaziga en tifinag i, si n'hi ha, en lletres llatines; la traducció al català que en va "
    "fer una màquina; i el que diuen el diccionari de l'IRCAM, el Viccionari i les taules de conjugació de les "
    "seves paraules (poden ser coincidències aproximades i enganyar). La teva feina és decidir si la traducció "
    "és fidel al que diu la frase amaziga.\n\n"
    "Respon amb UNA sola línia i res més:\n"
    "- «TRIA: <traducció final en català>» si la traducció és fidel tal com està (torna-la igual), o si només "
    "cal retocar-la i estàs segur del retoc (torna la frase sencera corregida, en català natural i correcte).\n"
    "- «FORA» si la traducció és clarament falsa (parla d'una altra cosa, s'inventa noms o fets, contradiu el "
    "diccionari) i no la pots arreglar amb seguretat.\n"
    "- «NO-HO-SE» si no tens prou elements per decidir.\n\n"
    "Regles: no inventis mai; el diccionari mana sobre la intuïció; no diguis TRIA per cortesia: si dubtes, "
    "NO-HO-SE. Les frases són lectures d'un corpus (notícies, contes, frases soltes). Els noms d'institucions "
    "marroquines la màquina se'ls inventa sempre: si la frase en porta i el diccionari no ho sosté, FORA o "
    "NO-HO-SE. Errors sistemàtics coneguts de la màquina, tots comprovats al diccionari: " + ERRORS)


def prompt(x):
    parts = [f"Frase amaziga (tifinag): {x['text_tachelhit']}"]
    if x.get("llati"):
        parts.append(f"Frase amaziga (lletres llatines): {x['llati']}")
    parts.append(f"Traducció de la màquina: {x['text_catalan']}")
    if x.get("fonts"):
        parts.append("Diccionari i conjugació de les seves paraules:\n" + "\n".join("- " + l for l in x["fonts"][:16]))
    else:
        parts.append("Diccionari: cap paraula de la frase no hi surt.")
    parts.append("La teva resposta (TRIA: … / FORA / NO-HO-SE):")
    return "\n\n".join(parts)


def crida(nom, text):
    model, base, key = {**AUDITORS, **TERCER}[nom]
    body = {"model": model, "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": text}],
            "max_tokens": 8000 if model in PENSEN else 400, "temperature": 0}
    if model.startswith("qwen"):
        body["enable_thinking"] = model in PENSEN
    t0 = time.time()
    for intent in range(4):
        try:
            r = requests.post(base + "/chat/completions", headers={"Authorization": "Bearer " + key}, json=body, timeout=120)
            if r.status_code == 200:
                d = r.json()
                u = d.get("usage", {})
                cont = (d["choices"][0]["message"].get("content") or "").strip()
                return {"dit": cont, "s": round(time.time() - t0, 2), "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
            if r.status_code in (429, 500, 502, 503):
                time.sleep(5 + 10 * intent)
            else:
                return {"dit": "", "s": round(time.time() - t0, 2), "error": f"{r.status_code} {r.text[:120]}"}
        except Exception as e:
            err = str(e)[:120]
            time.sleep(3 + 5 * intent)
    return {"dit": "", "s": round(time.time() - t0, 2), "error": "esgotat: " + err}


def veredicte(dit):
    """TRIA: text / FORA / NO-HO-SE, llegit amb mànega ampla (cometes, guions, majúscules)."""
    linies = [l.strip(" -*`\"«»") for l in dit.splitlines() if l.strip()]
    if not linies:
        return "buit", ""
    l = linies[0]
    u = l.upper().replace("É", "E").replace("È", "E")
    if u.startswith("FORA"):
        return "fora", ""
    if u.startswith("NO-HO-SE") or u.startswith("NO HO SE") or u.startswith("NO-HO-SÉ"):
        return "no-ho-se", ""
    m = re.match(r"TRIA\s*[:：]\s*(.+)$", l, flags=re.I | re.S)
    if m:
        return "tria", m.group(1).strip().strip("«»\"'")
    return "altre", l


def main():
    pend = json.load(io.open(os.path.join(AQUI, "pendents.json"), encoding="utf-8"))
    LIMIT = int(os.environ.get("LIMIT") or 0)
    if LIMIT:
        pend = pend[:LIMIT]
    import lexicon
    from transliteration import to_forms
    lexicon.load()
    for x in pend:
        f = to_forms(x["text_tachelhit"])
        x["llati"] = x.get("text_tachelhit_latin") or f.get("clean_latin") or ""
        x["fonts"] = lexicon.grounding_lines(x["text_tachelhit"]) or lexicon.grounding_lines(x["llati"])
    print("frases", len(pend), "amb diccionari", sum(1 for x in pend if x["fonts"]), flush=True)

    sortida = os.path.join(AQUI, "prova.jsonl" if LIMIT else "veredictes.jsonl")
    fets = set()
    if os.path.exists(sortida):
        for l in io.open(sortida, encoding="utf-8"):
            if l.strip():
                v = json.loads(l)
                fets.add((v["id"], v["auditor"]))
    feines = [(x, a) for x in pend for a in AUDITORS if (x["id"], a) not in fets]
    print("crides pendents", len(feines), flush=True)
    pany = threading.Lock()
    t0 = time.time()
    n = 0
    with io.open(sortida, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=6) as ex:
        def una(f):
            x, a = f
            r = crida(a, prompt(x))
            mena, text = veredicte(r["dit"])
            return {"id": x["id"], "auditor": a, "mena": mena, "text": text, "cru": r["dit"][:600], "s": r["s"],
                    "in": r.get("in", 0), "out": r.get("out", 0), "error": r.get("error")}
        for v in ex.map(una, feines):
            with pany:
                out.write(json.dumps(v, ensure_ascii=False) + "\n")
                out.flush()
                n += 1
                if n % 100 == 0:
                    print(n, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
    print("fet en", f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
