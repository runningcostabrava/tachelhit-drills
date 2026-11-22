# -*- coding: utf-8 -*-
"""Etapa 04: el català de cada rèplica (§4 i §3.3).

  python -X utf8 04_tradueix.py <carpeta_del_capitol> [--fils 4] [--nomes N]

- Àrab → català amb dos models (un Qwen de la quota gratuïta de Model Studio, en cascada `qwen3.8-max` → `qwen4-max` → `qwen3.7-max` → `qwen3.8-flash`
  (rota a l'800.000 de cadascun), i `deepseek-chat`; sense cap Qwen, «acord DeepSeek + Gemini» només amb `arab_conf` ≥ 0,8; temperatura 0; el prompt de
  tools/tutlait/tradueix_ar_ca.py): `catala_a`, `catala_b`, `model_a`, `model_b`, `chrf_ab`.
- Si 0,3 ≤ chrf_ab < 0,5, un tercer auditor (`gemini-2.5-flash` sense raonar, només en aquest cas; o el que digui `TD_MODEL_AR_C`) i
  es queda el dels dos que coincideixi ≥ 0,5 amb el tercer (`catala_estat` = «tercer»). Si chrf_ab ≥ 0,5,
  `catala` = `catala_a` («confirmat»). Si no hi ha acord, «descartat» i `catala` buit.
- Tifinag → català amb **el nostre NLLB a casa** (`traductor_local.py`, CTranslate2 en CPU): `catala_de_tifinag` i
  `chrf_tif_ar` (contra `catala`). Si les dues escriptures coincideixen (`chrf_tif_ar ≥ 0,5`), l'estat puja a
  **«creuat»**: dos OCR independents diuen el mateix, i això és l'única cosa de la cadena que pot enxampar una
  paraula àrab mal llegida — dos traductors del mateix text àrab no poden, perquè en comparteixen l'error (ADR 0014).
- El que no arriba a l'acord **es catalogua, no es llença**: `catala_estat` = «sense_acord», amb `catala_proposat`
  marcada com a proposta i les dues lectures desades. `catala` només s'omple quan hi ha acord.
Reprèn per id: una fila amb `catala_estat` i sense error no es repeteix; si l'àrab o el tifinag han canviat, sí.
Els crèdits no es tradueixen. Les rèpliques amb `arab_dubtos` (lector d'àrab propi) tampoc: no passen la porta del traductor (§5) i no han de gastar fitxes.

Límit de cost (ordre del director, 18-11-2026): cada crida suma les fitxes del model a `TD_TV/_costos.json` (acumulat de tots els capítols). Quan un model passa el
límit — DeepSeek `TD_LIMIT_DEEPSEEK_USD` (3,6 $ de seguretat per als 4 €), Gemini `TD_LIMIT_GEMINI_USD` (1,8 $ per als 2 €), la resta (Qwen, quota gratuïta d'1 M)
`TD_LIMIT_QWEN_FITXES` (850.000) — l'etapa deixa de traduir: les files que queden no es toquen (catàleg amb el català buit), l'etapa acaba bé amb
`comptes.pressupost_esgotat`, i quan es pugi el límit la mateixa etapa reprèn el que falta. El preu es compta per excés: totes les fitxes (dins i fora) al preu de
sortida (DeepSeek 0,28 $/M, Gemini 2,5 $/M).
"""
import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comu  # noqa: E402

ETAPA = "04_tradueix"
# Primer auditor: models Qwen de la quota gratuïta, en cascada. Quan el que toca passa de `TD_ROTA_QWEN_FITXES` (800.000, per sota del límit d'850.000) la
# fila següent va al model següent, cadascun amb el seu comptador. Provats àrab -> català (chrF contra qwen3.8-max, 8 frases): qwen4-max 0,88, qwen3.7-max 0,83,
# qwen3.8-flash 0,81. (`qwen3.8-max-0902` dona exactament el mateix i no es pot assegurar que tingui quota pròpia; per això no hi és.)
MODELS_A = [m.strip() for m in os.environ.get("TD_MODELS_AR_A", os.environ.get("TD_MODEL_AR_A", "qwen3.8-max,qwen4-max,qwen3.7-max,qwen3.8-flash")).split(",") if m.strip()]
MODEL_A = MODELS_A[0]
ROTA_QWEN = float(os.environ.get("TD_ROTA_QWEN_FITXES", "800000"))
CONF_ALTA = float(os.environ.get("TD_ARAB_CONF_ALTA", "0.8"))   # sense cap Qwen: només es tradueixen (DeepSeek + Gemini) les rèpliques amb arab_conf >= això
MODEL_B = os.environ.get("TD_MODEL_AR_B", "deepseek-chat")
MODEL_C = os.environ.get("TD_MODEL_AR_C", "gemini-2.5-flash")   # tercer auditor (ordre del 18-11-2026; abans qwen4-max)
#: el tifinag ja no passa per cap Space: es tradueix a casa (ADR 0014, `traductor_local.py`)
CONFIRMAT, DUBTE = 0.5, 0.3


def sense_acord(f):
    """Dues lectures que no coincideixen: es **catalogen**, no es llencen (ADR 0014).

    Abans quedaven amb `catala` buit i estat «descartat», i el significat es perdia: 142 rèpliques
    (17 %) de l'episodi del 20-11. Mirant-les, el llindar castiga les maneres de dir diferents —
    dues traduccions amb chrF 0,30 deien exactament el mateix i es van perdre totes dues.

    `catala` segueix buit, que és el que impedeix que res presenti com a fet un significat que no
    ho és; el que hi ha és una **proposta** marcada, i les dues lectures al costat.
    """
    f["catala"], f["catala_estat"] = "", "sense_acord"
    f["catala_proposat"] = f.get("catala_a") or f.get("catala_b") or f.get("catala_c") or ""
    return f
SISTEMA = ("Ets un traductor de l'àrab al català. T'arriba la traducció àrab (àrab estàndard, de vegades amb "
           "trets marroquins) d'una frase dita en amazic per algú del Marroc: una frase de conversa, un conte, "
           "una dita o una frase solta. Torna NOMÉS la traducció al català, en una sola línia, natural i correcta, "
           "sense cometes ni comentaris. Deixa els noms propis tal com són; «إن شاء الله» és «si Déu vol». "
           "Si l'àrab és incomplet o no té sentit, tradueix el que hi ha sense inventar res.")


PREU_M_USD = {"deepseek": 0.28, "gemini": 2.5}   # $ per milió de fitxes, preu de sortida (per excés)


class PressupostEsgotat(BaseException):
    """Es llança ABANS de cada crida si el model ja ha arribat al límit. És una BaseException a posta: els `except Exception` de la feina no
    l'han d'empassar (la fila quedaria com a «descartat»); `feina()` la captura i deixa la fila sense tocar."""


class Pressupost:
    """Fitxes de text acumulades per model a `<TD_TV>/_costos.json` i el seu límit (vegeu el docstring del mòdul)."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.fitxes = {}
        try:
            import json
            with open(path, encoding="utf-8") as fh:
                self.fitxes = {k: int(v) for k, v in json.load(fh).get("fitxes", {}).items()}
        except Exception:
            self.fitxes = {}
        self.reconcilia(os.path.dirname(path))

    def reconcilia(self, td):
        """El comptador no es pot quedar per sota del que els capítols diuen que s'ha gastat (`estat.json` -> 04 -> comptes.fitxes_text): una etapa 04
        d'una versió del codi sense comptador (el capítol en curs en un desplegament) gastava sense deixar rastre a `_costos.json`, i el límit es va
        passar de 55 k el 18-11-2026. Es pren el màxim dels dos, sumant els capítols."""
        import glob
        import json
        suma = {}
        for q in glob.glob(os.path.join(td, "*", "estat.json")):
            try:
                with open(q, encoding="utf-8") as fh:
                    ft = ((json.load(fh).get("04_tradueix") or {}).get("comptes") or {}).get("fitxes_text") or {}
            except Exception:
                continue
            for m, n in ft.items():
                suma[m] = suma.get(m, 0) + int(n or 0)
        for m, n in suma.items():
            if n > self.fitxes.get(m, 0):
                self.fitxes[m] = n

    @staticmethod
    def tipus(model):
        return "deepseek" if model.startswith("deepseek") else "gemini" if model.startswith("gemini") else "qwen"

    @staticmethod
    def limit(model):
        t = Pressupost.tipus(model)
        if t == "deepseek":
            return float(os.environ.get("TD_LIMIT_DEEPSEEK_USD", "3.6"))
        if t == "gemini":
            return float(os.environ.get("TD_LIMIT_GEMINI_USD", "1.8"))
        return float(os.environ.get("TD_LIMIT_QWEN_FITXES", "850000"))

    def cost(self, model):
        """Dòlars (per excés) per a DeepSeek i Gemini; fitxes per a la resta."""
        t = Pressupost.tipus(model)
        n = self.fitxes.get(model, 0)
        return n * PREU_M_USD[t] / 1e6 if t in PREU_M_USD else n

    def esgotat(self, models):
        return [m for m in models if m and self.cost(m) >= Pressupost.limit(m)]

    def suma(self, model, n):
        import json
        with self.lock:
            self.fitxes[model] = self.fitxes.get(model, 0) + int(n or 0)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"fitxes": self.fitxes}, fh, indent=1)
            os.replace(tmp, self.path)


PRESSUPOST = None   # es crea a main() (necessita TD_TV)


def tria_a():
    """El primer model Qwen de la cascada que encara no ha arribat a la rotació; None si cap."""
    for m in MODELS_A:
        if PRESSUPOST.cost(m) < min(ROTA_QWEN, Pressupost.limit(m)):
            return m
    return None


def primera_linia(t):
    ls = [l.strip().strip('«»"') for l in (t or "").splitlines() if l.strip()]
    return ls[0] if ls else ""


def tradueix(model, text):
    msgs = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": f"Àrab: {text}\n\nCatalà:"}]
    if PRESSUPOST is not None and PRESSUPOST.esgotat([model]):   # el límit es comprova ABANS de cada crida, no al final del capítol
        raise PressupostEsgotat(model)
    if model.startswith("deepseek"):
        out, u = comu.xat(model, msgs, max_tokens=300, base=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                          key=os.environ.get("DEEPSEEK_API_KEY", ""))
    elif model.startswith("gemini"):
        out, u = gemini(model, msgs)
    else:
        out, u = comu.xat(model, msgs, max_tokens=300)
    n = u.get("total_tokens", 0)
    if PRESSUPOST is not None:
        PRESSUPOST.suma(model, n)
    return primera_linia(out), n


def gemini(model, msgs, intents=4):
    """Tercer auditor: Gemini pel punt OpenAI-compatible, SENSE raonar (reasoning_effort none: només fitxes de text, el preu més baix).
    La clau és GEMINI_API_KEY. Torna (text, usage)."""
    import requests
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("falta GEMINI_API_KEY")
    body = {"model": model, "messages": msgs, "max_tokens": 300, "temperature": 0.0, "reasoning_effort": "none"}
    err = ""
    for intent in range(intents):
        try:
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                              headers={"Authorization": "Bearer " + key}, json=body, timeout=120)
            if r.status_code == 200:
                d = r.json()
                return (d["choices"][0]["message"].get("content") or "").strip(), d.get("usage") or {}
            err = f"{r.status_code} {r.text[:120]}"
            if r.status_code not in (429, 500, 502, 503):
                break
        except Exception as e:
            err = str(e)[:120]
        time.sleep(4 + 8 * intent)
    raise RuntimeError(err)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--nomes", type=int, default=0)
    a = ap.parse_args()
    comu.carrega_env()
    carpeta = os.path.abspath(a.carpeta)
    log = comu.obre_log(carpeta)
    comu.etapa_inici(carpeta, ETAPA)
    t0 = time.time()
    try:
        files = comu.subtitols(carpeta)
        if not files:
            raise RuntimeError("sense subtitols.jsonl")
        te_b = bool(os.environ.get("DEEPSEEK_API_KEY"))
        comu.diu(log, f"== {ETAPA} {comu.ara()} {MODEL_A} + {MODEL_B if te_b else 'cap segon model (sense DEEPSEEK_API_KEY)'} + tercer {MODEL_C} + tifinag a casa")
        import collections
        fitxes = collections.defaultdict(int)
        pany = threading.Lock()
        global PRESSUPOST
        PRESSUPOST = Pressupost(os.path.join(comu.td_tv(), "_costos.json"))
        saltades = [0, 0]   # [pel pressupost, per confiança baixa sense Qwen]

        def aturat():
            """Models (DeepSeek, Gemini) que han esgotat el límit: l'etapa para. Els Qwen no paren res: roten, i sense cap Qwen es passa a DeepSeek + Gemini."""
            ex = PRESSUPOST.esgotat([MODEL_B if te_b else None, MODEL_C])
            if not ex and tria_a() is None and not te_b:
                ex = ["qwen (tots) i sense DeepSeek"]
            return ex

        def cal(f):
            if f.get("credits") or not f.get("arab") or f.get("arab_dubtos"):
                return False   # les dubtoses del lector propi no passen la porta del traductor: no gasten fitxes
            if f.get("catala_estat") and not f.get("error_traduccio") and f.get("arab_traduit") == f["arab"]:
                return not f.get("tifinag") or f.get("tifinag_traduit") == f.get("tifinag")
            return True

        #: Els capítols llegits abans de l'ADR 0014 porten «descartat», amb el significat llençat.
        #: Com que la seva feina d'àrab ja està feta i no es tornarà a tocar, aquí es canvia el nom
        #: i es recupera la proposta: si no, el catàleg tindria dos vocabularis per sempre i qui el
        #: llegís hauria de conèixer-los tots dos.
        vells = [f for f in files if f.get("catala_estat") == "descartat"]
        for f in vells:
            sense_acord(f)
        if vells:
            comu.diu(log, f"{len(vells)} rèpliques «descartat» passades a «sense_acord» (ADR 0014)")

        feines = [f for f in files if cal(f)]
        if a.nomes:
            feines = feines[:a.nomes]
        comu.diu(log, f"{len(files)} rèpliques, {len(feines)} a traduir")
        #: El tifinag es tradueix a casa (ADR 0014). Abans es demanava a un Space gratuït, i el
        #: Space es dorm: el 20-11-2026 van sortir ZERO rèpliques amb la comparació entre les dues
        #: vies perquè la crida va caducar. Un testimoni que no es presenta mai no val res, i
        #: aquesta via és l'única que pot enxampar un error de lectura de l'àrab.
        import traductor_local
        local = traductor_local.disponible()
        comu.diu(log, f"tifinag → català: {'el nostre NLLB a casa' if local else 'NO DISPONIBLE'}")
        sem = threading.Semaphore(2)

        def tif_ca(text):
            if not text or not local:
                return ""
            try:
                with sem:
                    return traductor_local.tradueix(text)
            except Exception as e:
                comu.diu(log, f"traductor local: {type(e).__name__} {str(e)[:70]}")
                return ""

        def feina(f):
            try:
                return feina_int(f)
            except PressupostEsgotat:   # un model ha arribat al límit a mitja fila: la fila es queda sense tocar i es farà quan es pugi el límit
                with pany:
                    saltades[0] += 1
                f.pop("arab_traduit", None)
                return f

        def feina_int(f):
            if aturat():   # límit de cost: no es toca la fila (es traduirà quan es pugi el límit)
                with pany:
                    saltades[0] += 1
                return f
            err = None
            mod_a = tria_a()
            canvi_arab = f.get("arab_traduit") != f["arab"] or not f.get("catala_a")
            if mod_a is None and canvi_arab:
                # Cap Qwen gratuït: «acord DeepSeek + Gemini», només en rèpliques de confiança alta (la porta de línia de §5 no baixa)
                conf = f.get("arab_conf")
                if conf is not None and conf < CONF_ALTA:
                    with pany:
                        saltades[1] += 1
                    return f
                f["model_a"], f["catala_a"], f["catala_b"], f["catala_c"], f["chrf_ab"] = None, "", "", None, None
                try:
                    f["catala_b"], n = tradueix(MODEL_B, f["arab"]); f["model_b"] = MODEL_B
                    with pany:
                        fitxes[MODEL_B] += n
                    f["catala_c"], n = tradueix(MODEL_C, f["arab"])
                    with pany:
                        fitxes[MODEL_C] += n
                    acord = comu.chrf(f["catala_c"], f["catala_b"])
                    f["chrf_bc"] = acord
                    if acord >= CONFIRMAT:
                        f["catala"], f["catala_estat"] = f["catala_b"], "confirmat"
                    else:
                        sense_acord(f)
                    f["via"] = "deepseek+gemini"
                except Exception as e:
                    err = f"b/c: {str(e)[:80]}"; sense_acord(f)
                f["arab_traduit"] = f["arab"]
                canvi_arab = False
            if canvi_arab:
                f.pop("via", None)
                try:
                    f["catala_a"], n = tradueix(mod_a, f["arab"]); f["model_a"] = mod_a
                    with pany:
                        fitxes[mod_a] += n
                except Exception as e:
                    f["catala_a"] = ""; err = f"a: {str(e)[:80]}"
                f["catala_b"] = ""; f["model_b"] = None
                if te_b:
                    try:
                        f["catala_b"], n = tradueix(MODEL_B, f["arab"]); f["model_b"] = MODEL_B
                        with pany:
                            fitxes[MODEL_B] += n
                    except Exception as e:
                        err = (err or "") + f" b: {str(e)[:80]}"
                f["chrf_ab"] = comu.chrf(f["catala_b"], f["catala_a"]) if f["catala_a"] and f["catala_b"] else None
                f["catala_c"] = None
                if f["chrf_ab"] is None:
                    # un sol model: no hi ha acord possible; es guarda com a «tercer» només si el tercer hi coincideix
                    ok = False
                    if f["catala_a"]:
                        try:
                            f["catala_c"], n = tradueix(MODEL_C, f["arab"])
                            with pany:
                                fitxes[MODEL_C] += n
                            ok = comu.chrf(f["catala_c"], f["catala_a"]) >= CONFIRMAT
                        except Exception as e:
                            err = (err or "") + f" c: {str(e)[:80]}"
                    if ok:
                        f["catala"], f["catala_estat"] = f["catala_a"], "tercer"
                    else:
                        sense_acord(f)
                elif f["chrf_ab"] >= CONFIRMAT:
                    f["catala"], f["catala_estat"] = f["catala_a"], "confirmat"
                elif f["chrf_ab"] >= DUBTE:
                    try:
                        f["catala_c"], n = tradueix(MODEL_C, f["arab"])
                        with pany:
                            fitxes[MODEL_C] += n
                    except Exception as e:
                        f["catala_c"] = ""; err = (err or "") + f" c: {str(e)[:80]}"
                    ca, cb = comu.chrf(f["catala_c"], f["catala_a"]), comu.chrf(f["catala_c"], f["catala_b"])
                    if max(ca, cb) >= CONFIRMAT:
                        f["catala"], f["catala_estat"] = (f["catala_a"] if ca >= cb else f["catala_b"]), "tercer"
                    else:
                        sense_acord(f)
                else:
                    sense_acord(f)
                f["arab_traduit"] = f["arab"]
            if f.get("tifinag") and (f.get("tifinag_traduit") != f["tifinag"] or not f.get("catala_de_tifinag")):
                f["catala_de_tifinag"] = tif_ca(f["tifinag"]); f["tifinag_traduit"] = f["tifinag"]
            elif not f.get("tifinag"):
                f["catala_de_tifinag"] = ""
            ref = f.get("catala") or ""
            f["chrf_tif_ar"] = comu.chrf(f.get("catala_de_tifinag", ""), ref) if ref and f.get("catala_de_tifinag") else None
            #: Les dues escriptures diuen el mateix (ADR 0014). Això val més que «confirmat»: allà
            #: hi ha dos traductors del MATEIX text àrab, que comparteixen l'error de lectura; aquí
            #: hi ha dos OCR d'escriptures diferents, que no se'l poden compartir. És l'única cosa
            #: de tota la cadena que pot enxampar una paraula àrab mal llegida.
            #:
            #: El desacord, de moment, NO treu res: abans de tancar aquesta porta cal saber quina
            #: part és error d'OCR i quina és que el nostre traductor és fluix.
            if f["chrf_tif_ar"] is not None and f["chrf_tif_ar"] >= CONFIRMAT \
                    and f.get("catala_estat") in ("confirmat", "tercer"):
                f["catala_estat"] = "creuat"
            f["error_traduccio"] = err
            return f

        n = 0
        with ThreadPoolExecutor(max_workers=a.fils) as ex:
            for _ in ex.map(feina, feines):
                n += 1
                if n % 100 == 0:
                    with pany:
                        comu.desa_subtitols(carpeta, files)
                    comu.diu(log, f"  {n}/{len(feines)} {time.time() - t0:.0f} s")
        comu.desa_subtitols(carpeta, files)
        dial = [f for f in files if not f.get("credits") and f.get("arab")]
        estats = {e: sum(1 for f in dial if f.get("catala_estat") == e)
                  for e in ("creuat", "confirmat", "tercer", "sense_acord")}
        ab = [f["chrf_ab"] for f in dial if f.get("chrf_ab") is not None]
        #: quantes rèpliques han arribat a tenir la segona via: si surt zero, el traductor local no
        #: s'ha carregat i el creuament no s'ha fet — val més veure-ho al registre que descobrir-ho
        #: tres episodis més tard, que és el que va passar amb el Space
        estats["amb_via_tifinag"] = sum(1 for f in dial if f.get("chrf_tif_ar") is not None)
        vell = comu.estat_llegeix(carpeta).get(ETAPA, {}).get("comptes", {})
        comptes = {"traduides": len(dial), "estats": estats, "chrf_ab_mitja": round(sum(ab) / len(ab), 4) if ab else None,
                   "fitxes_text": {m: fitxes.get(m, 0) + (vell.get("fitxes_text") or {}).get(m, 0) for m in set(fitxes) | set(vell.get("fitxes_text") or {})},
                   "model_a": MODELS_A, "model_b": MODEL_B if te_b else None, "model_c": MODEL_C,
                   "tifinag": "traductor_local",
                   "errors": sum(1 for f in dial if f.get("error_traduccio")), "segons": round(time.time() - t0),
                   "saltades_pressupost": saltades[0], "saltades_sense_qwen_confianca_baixa": saltades[1], "pressupost_esgotat": aturat() or None,
                   "qwen_actual": tria_a(),
                   "cost_acumulat": {m: round(PRESSUPOST.cost(m), 4) for m in PRESSUPOST.fitxes}}
        comu.etapa_fi(carpeta, ETAPA, comptes)
        comu.diu(log, f"{ETAPA}: {estats}, chrf_ab {comptes['chrf_ab_mitja']}, {comptes['segons']} s")
    except Exception as e:
        comu.etapa_fi(carpeta, ETAPA, {"segons": round(time.time() - t0)}, error=f"{type(e).__name__}: {e}")
        comu.diu(log, f"{ETAPA}: ERROR {e}")
        raise


if __name__ == "__main__":
    main()
