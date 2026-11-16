# -*- coding: utf-8 -*-
"""El mateix parell d'auditors (qwen3.8-max i deepseek-chat), ara sobre les frases que tenen el
subtítol àrab de l'original i el català de la màquina, sense text amazic: Baba Ali (#493). L'auditor
jutja si el català és fidel a l'àrab. Fa servir crida() i veredicte() d'audita.py; la carpeta de dades
és la del primer argument (per defecte …\traduccions\auditors_baba_ali), on hi ha d'haver
cataleg_prod.json (de baixa_cataleg.py) o pendents.json; resum.py i aplica.py hi valen igual."""
import io, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audita
from audita import AUDITORS, crida, veredicte

AQUI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else r"C:\Users\josep\Veus-tachelhit\_escoltats\traduccions\auditors_baba_ali"

SISTEMA = (
    "Ets un auditor de traduccions de l'àrab al català. T'arriba el subtítol àrab d'una sèrie de dibuixos "
    "animats marroquina (Baba Ali, parlada en amazic i subtitulada en àrab estàndard amb trets marroquins) i la "
    "traducció al català que en va fer una màquina. La teva feina és decidir si el català diu el mateix que l'àrab.\n\n"
    "Respon amb UNA sola línia i res més:\n"
    "- «TRIA: <traducció final en català>» si la traducció és fidel tal com està (torna-la igual), o si només "
    "cal retocar-la i estàs segur del retoc (torna la frase sencera corregida, en català natural i correcte, "
    "amb el to de la rèplica: col·loquial si l'àrab ho és).\n"
    "- «FORA» si la traducció és clarament falsa (canvia el sentit, el subjecte, la negació, o s'inventa coses) "
    "i no la pots arreglar amb seguretat.\n"
    "- «NO-HO-SE» si l'àrab és ambigu o incomplet i no pots decidir.\n\n"
    "Regles: no inventis; mantén els noms propis tal com són; «إن شاء الله» es tradueix «si Déu vol»; "
    "no diguis TRIA per cortesia: si dubtes, NO-HO-SE.")


def prompt(x):
    return (f"Subtítol àrab: {x['text_arabic']}\n\nTraducció de la màquina: {x['text_catalan']}\n\n"
            "La teva resposta (TRIA: … / FORA / NO-HO-SE):")


def main():
    audita.SISTEMA = SISTEMA
    p_pend = os.path.join(AQUI, "pendents.json")
    if not os.path.exists(p_pend):
        d = json.load(io.open(os.path.join(AQUI, "cataleg_prod.json"), encoding="utf-8"))
        pend = [x for x in d if "baba-ali" in (x.get("tag") or "") and "traduit-per-maquina" in x["tag"]
                and "traduccio-descartada" not in x["tag"] and (x.get("text_arabic") or "").strip() and (x.get("text_catalan") or "").strip()]
        camps = ["id", "tag", "text_arabic", "text_catalan", "text_tachelhit_suggested", "source_title"]
        pend = [{k: x.get(k) for k in camps} for x in pend]
        json.dump(pend, io.open(p_pend, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    pend = json.load(io.open(p_pend, encoding="utf-8"))
    LIMIT = int(os.environ.get("LIMIT") or 0)
    if LIMIT:
        pend = pend[:LIMIT]
    sortida = os.path.join(AQUI, "prova.jsonl" if LIMIT else "veredictes.jsonl")
    fets = set()
    if os.path.exists(sortida):
        for l in io.open(sortida, encoding="utf-8"):
            if l.strip():
                v = json.loads(l)
                fets.add((v["id"], v["auditor"]))
    feines = [(x, a) for x in pend for a in AUDITORS if (x["id"], a) not in fets]
    print("frases", len(pend), "crides pendents", len(feines), flush=True)
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
                if n % 200 == 0:
                    print(n, "de", len(feines), f"{time.time() - t0:.0f} s", flush=True)
    print("fet en", f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
