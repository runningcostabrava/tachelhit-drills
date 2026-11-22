# -*- coding: utf-8 -*-
"""CERCLE VIRTUÓS del transcriptor de veu (#601, Tamazight TV · SNRT). RECERCA privada.

Rondes autònomes. Amb el model M_r (la ronda 0 parteix de l'adaptador «alta+ancoratge B»):
  a) Kaggle: concordança + alineació forçada CTC sobre TOTS els talls diana dels capítols llegits (nucli cercle_observa_snrt.py;
     l'adaptador M_r puja a un dataset PRIVAT «snrt-cercle-model» com adaptador_inici.pt)
  b) parelles: «alta» (rang+marge) I esquelet <= 0,5 amb M_r, retallades per l'alineació sobre la línia de temps refeta amb els
     talls veïns ([al_ini-0,3, al_fi+0,3]); capítols fora dels conjunts congelats (llavor 1114); res dels conjunts congelats a train
  c) entrenament recepta B (talls seleccionats + ancoratge H4b), ritme 5e-5, 3 èpoques, partint de M_r
  d) avaluació amb la regla de transcriptor_bucle.avalua CONTRA M_r. REGLA INTERNA (director): M_{r+1} = el nou adaptador només si
     cap conjunt empitjora amb IC i almenys dos milloren amb IC; si no, la ronda es descarta. La regla de producció (§6.5) NO es toca.
  e) /root/cercle/rondes.jsonl (una línia per ronda) i /root/cercle/ESTAT.md
Atura: 3 rondes seguides sense millora · fitxer /root/cercle/ATURA · disc < 15 GB · un error de Kaggle repetit 2 cops.
Res d'això va a producció, ni a cap Space, ni a cap dataset públic: tot és privat (docs/PERMISOS.md, SNRT).

Ús (a l'ECS, dins tmux «cercle»):  /opt/venv/bin/python tools/lm/cercle_virtuos.py [--rondes N]
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
USUARI = "josepabloucr"
SEED_BASE = 42
ESQ_MAX = 0.5                          # esquelet consonàntic màxim (director)
MARGE_RETALL = 0.3                     # s a cada banda del lloc alineat
DURADA_MIN, DURADA_MAX = 0.8, 14.0     # = DURADA_MIN de §5 i SEGONS_MAXIM del nucli
RITME, EPOQUES = 5e-5, 3
ANCORATGE_H4B = 1422                   # talls d'ancoratge que el nucli B construeix (només avís si canvia)
PROVES = ["cv-zgh-test", "test-fora", "tfa-226", "zouhir-tests", "snrt-retingut"]
MIN_RONDES_SENSE_MILLORA = 3
MIN_DISC_GB = 15
ALINEACIO_MIN_OK = 0.7                 # part dels talls diana que l'alineació ha de poder alinear perquè la sortida sigui creïble
DS_CONGELAT = "/root/alta/ds"          # rows.json + audio dels conjunts congelats (test/dev de la partició d'«alta», llavor 1114)
ESPERA_MAX_S = 7 * 3600
ESPERA_COMENCA_MAX_S = 3 * 3600


class Atura(Exception):
    """Condició d'aturada del cercle."""


def _carrega(nom, cami):
    esp = importlib.util.spec_from_file_location(nom, cami)
    m = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(m)
    return m


tb = _carrega("transcriptor_bucle_cercle", os.path.join(AQUI, "transcriptor_bucle.py"))
cc = _carrega("concordanca_cercle", os.path.join(AQUI, "..", "snrt", "concordanca.py"))


# ------------------------------------------------------------------ lògica pura (provada a backend/tests/test_cercle_virtuos.py)
def capitols_retinguts(particions):
    """Capítols de test i dev de TOTES les particions que han existit (alta, conc, estricte, transcriptor): mai no entren a train."""
    fora = set()
    for p in particions:
        for s in ("test", "dev"):
            fora.update((p.get("capitols") or {}).get(s, []))
    return fora


def finestra_retall(al_ini, al_fi, marge=MARGE_RETALL, origen=0.0, fi=None, durada_min=DURADA_MIN, durada_max=DURADA_MAX):
    """[al_ini-marge, al_fi+marge] dins la finestra [origen, fi] de la línia de temps; None si el tall resultant és massa curt o llarg."""
    t0 = max(origen, al_ini - marge)
    t1 = al_fi + marge if fi is None else min(fi, al_fi + marge)
    if t1 - t0 < durada_min or t1 - t0 > durada_max:
        return None
    return round(t0, 2), round(t1, 2)


def selecciona_parelles(conc, ali, retinguts, esq_max=ESQ_MAX):
    """Talls amb concordança «alta» I CER d'esquelet <= esq_max amb M_r I alineació sense error, fora dels capítols retinguts.
    conc: {id: {alta, hip, text}} · ali: [{id, slug, al_ini, al_fi | error}]. -> (parelles, comptes de motius)."""
    motius = collections.Counter()
    sortida = []
    for e in ali:
        c = conc.get(e["id"])
        if e["slug"] in retinguts:
            motius["capítol retingut"] += 1
        elif c is None:
            motius["sense concordança"] += 1
        elif c.get("alta") is not True:
            motius["no alta"] += 1
        elif cc.cer_esq(c.get("hip", ""), c.get("text", "")) > esq_max:
            motius["esquelet"] += 1
        elif "error" in e or "al_ini" not in e:
            motius["alineació fallida"] += 1
        else:
            sortida.append(e)
            motius["seleccionat"] += 1
    return sortida, dict(motius)


def monta_buffer(membres, carrega, sr=16000):
    """Línia de temps refeta amb els talls veïns, com al nucli d'alineació: cada tall al seu temps absolut (camp «a»).
    membres: [{id, a, b}] · carrega(id) -> mostres. -> (origen, buffer)."""
    import numpy as np   # noqa: PLC0415
    origen = min(m["a"] for m in membres)
    fi = max(m["b"] for m in membres)
    buf = np.zeros(int((fi - origen) * sr) + sr, dtype=np.float32)
    for m in membres:
        w = carrega(m["id"])
        i0 = int((m["a"] - origen) * sr)
        buf[i0:i0 + len(w)] = w[:len(buf) - i0]
    return origen, buf


def talla_clip(buf, origen, t0, t1, sr=16000):
    return buf[max(0, int(round((t0 - origen) * sr))):int(round((t1 - origen) * sr))]


def regla_interna(stats, proves=PROVES):
    """Regla del bucle (decidida pel director): s'adopta si CAP conjunt empitjora amb IC (límit baix de l'IC de Δ CER > 0) i
    almenys DOS milloren amb IC (límit alt < 0). Si falta una prova no es pot jutjar: no s'adopta."""
    millora, empitjora, absents = [], [], []
    for p in proves:
        s = stats.get(p)
        if s is None:
            absents.append(p)
        elif s.get("unitats", 10 ** 9) < 3:
            #: amb menys de tres unitats independents l'interval no vol dir res (una sola
            #: unitat en dona un d'amplada zero, que diria «millora» per construcció)
            absents.append(p)
        elif s["ic_lo"] > 0:
            empitjora.append(p)
        elif s["ic_hi"] < 0:
            millora.append(p)
    adopta = not absents and not empitjora and len(millora) >= 2
    motiu = (f"milloren {millora}; empitjoren {empitjora}; absents {absents}")
    return {"adopta": adopta, "milloren": millora, "empitjoren": empitjora, "absents": absents, "motiu": motiu}


def rondes_sense_millora(rondes):
    """Rondes seguides (comptant des de l'última) que no han adoptat res."""
    n = 0
    for r in reversed(rondes):
        if r.get("adopta"):
            break
        n += 1
    return n


def motiu_aturada(rondes, atura_existeix, disc_lliure_gb, errors_kaggle):
    """-> text del motiu d'aturada o None."""
    if atura_existeix:
        return "fitxer ATURA"
    if disc_lliure_gb < MIN_DISC_GB:
        return f"disc ECS {disc_lliure_gb:.1f} GB < {MIN_DISC_GB} GB"
    if rondes_sense_millora(rondes) >= MIN_RONDES_SENSE_MILLORA:
        return f"{MIN_RONDES_SENSE_MILLORA} rondes seguides sense millora"
    rep = [k for k, v in errors_kaggle.items() if v >= 2]
    if rep:
        return f"error de Kaggle repetit 2 cops: {rep[0]}"
    return None


def comprova_observacio(obs, run_id, n_diana):
    """Problemes (llista; buida = ok) d'una sortida del nucli d'observació."""
    p = []
    if obs.get("run_id") != run_id:
        p.append(f"run_id {obs.get('run_id')!r} != {run_id!r}: sortida vella")
    if obs.get("adaptador") != "adaptador_inici.pt":
        p.append(f"adaptador {obs.get('adaptador')!r}")
    if obs.get("talls", 0) < 0.9 * n_diana:
        p.append(f"concordança de {obs.get('talls')} talls de {n_diana}")
    if obs.get("alineats", 0) < ALINEACIO_MIN_OK * max(1, obs.get("talls", 0)):
        p.append(f"només {obs.get('alineats')} alineats de {obs.get('talls')}")
    return p


def comprova_entrenament(res, run_id, seed, n_train_snrt, sha_nou, sha_inici):
    """Problemes d'una sortida d'entrenament (lliçó 17-11/18-11: una vegada es va avaluar una sortida vella com si fos nova)."""
    cfg = (res or {}).get("config", {})
    p = []
    if cfg.get("run_id") != run_id:
        p.append(f"run_id {cfg.get('run_id')!r} != {run_id!r}: sortida vella")
    if cfg.get("seed") != seed:
        p.append(f"llavor {cfg.get('seed')} != {seed}")
    if cfg.get("adaptador_inici") != "adaptador_inici.pt":
        p.append(f"el nucli ha partit de {cfg.get('adaptador_inici')!r}, no de M_r")
    ts = cfg.get("train_snrt", -1)
    if not (0.9 * n_train_snrt <= ts <= n_train_snrt):
        p.append(f"train SNRT del resultat {ts} no quadra amb el dataset construït ({n_train_snrt})")
    if cfg.get("ritme") != RITME or cfg.get("epoques") != EPOQUES or cfg.get("recepta") != "B":
        p.append(f"recepta/ritme/èpoques inesperats: {cfg.get('recepta')} {cfg.get('ritme')} {cfg.get('epoques')}")
    if sha_nou == sha_inici:
        p.append("l'adaptador nou és idèntic a M_r (no s'ha entrenat)")
    return p


def resum_stats(stats):
    return {p: {"n": s["n"], "abans": round(s["abans"], 4), "despres": round(s["despres"], 4), "delta": round(s["delta"], 4),
                "ic": [round(s["ic_lo"], 4), round(s["ic_hi"], 4)]} for p, s in stats.items()}


# ------------------------------------------------------------------ entorn (ECS)
class Cercle:
    def __init__(self, base="/root/cercle", arrel="/root/tamazight_tv", kaggle_cli=None, dorm=time.sleep):
        self.base, self.arrel, self.dorm = base, arrel, dorm
        self.cli = kaggle_cli or os.environ.get("KAGGLE_CLI", "/root/venv-kaggle/bin/kaggle")
        self.errors = collections.Counter()
        for d in ("models", "obs", "rondes"):
            os.makedirs(os.path.join(base, d), exist_ok=True)

    # -- registre
    def log(self, *a):
        t = time.strftime("%Y-%m-%d %H:%M:%S") + " " + " ".join(str(x) for x in a)
        print(t, flush=True)
        with open(os.path.join(self.base, "cercle.log"), "a", encoding="utf-8") as f:
            f.write(t + "\n")

    def rondes(self):
        p = os.path.join(self.base, "rondes.jsonl")
        return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []

    def apunta(self, entrada):
        with open(os.path.join(self.base, "rondes.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        self.estat_md()

    def estat_md(self, estat="en marxa", motiu=""):
        rs = self.rondes()
        L = [f"# Cercle virtuós · {time.strftime('%Y-%m-%d %H:%M')} · {estat} {motiu}".rstrip(), "",
             f"Rondes fetes: {len(rs)} · adoptades: {sum(1 for r in rs if r.get('adopta'))} · "
             f"seguides sense millora: {rondes_sense_millora(rs)} (atura a {MIN_RONDES_SENSE_MILLORA})",
             f"Model actual: {self.model_actual()[0]}", "", "| ronda | model | seed | train SNRT | adopta | milloren | empitjoren |", "|---|---|---|---|---|---|---|"]
        for r in rs:
            L.append(f"| {r['ronda']} | {r['model_idx']} | {r.get('seed')} | {r.get('train_snrt')} | {r.get('adopta')} | "
                     f"{','.join(r.get('milloren', []))} | {','.join(r.get('empitjoren', []))} |")
        if rs:
            L += ["", "Última ronda (CER abans -> després):"]
            for p, s in rs[-1].get("stats", {}).items():
                L.append(f"- {p}: {s['abans']} -> {s['despres']} (Δ {s['delta']:+}, IC {s['ic']})")
        L += ["", "Atura: crea /root/cercle/ATURA · registre complet: cercle.log · dades: rondes.jsonl"]
        open(os.path.join(self.base, "ESTAT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    def model_actual(self):
        """(camí, índex) del model M_r: el de l'última ronda adoptada, o M_0."""
        idx = sum(1 for r in self.rondes() if r.get("adopta"))
        return os.path.join(self.base, "models", f"M{idx}.pt"), idx

    def disc_lliure_gb(self):
        return shutil.disk_usage(self.base).free / 1e9

    # -- Kaggle
    def kaggle(self, *args, cwd=None, check=True):
        p = subprocess.run([self.cli, *args], capture_output=True, text=True, cwd=cwd)
        if check and p.returncode:
            raise RuntimeError(f"kaggle {' '.join(args)}: {p.stdout[-300:]} {p.stderr[-300:]}")
        return p.stdout + p.stderr

    def amb_reintent(self, clau, f):
        """Un error de Kaggle es reintenta una vegada (5 min); el segon, del mateix pas, atura el cercle."""
        try:
            return f()
        except Exception as e:   # noqa: BLE001
            self.errors[clau] += 1
            self.log(f"ERROR Kaggle ({clau}) #{self.errors[clau]}: {str(e)[:300]}")
            if self.errors[clau] >= 2:
                raise Atura(f"error de Kaggle repetit 2 cops: {clau}")
            self.dorm(300)
            return self.amb_reintent(clau, f)

    def dataset_llest(self, slug):
        return "ready" in self.kaggle("datasets", "status", f"{USUARI}/{slug}", check=False).lower()

    def puja_dataset(self, carpeta, slug, titol, missatge):
        json.dump({"title": titol, "id": f"{USUARI}/{slug}", "licenses": [{"name": "other"}], "isPrivate": True},
                  open(os.path.join(carpeta, "dataset-metadata.json"), "w"))
        existeix = self.dataset_llest(slug)
        if existeix:
            self.kaggle("datasets", "version", "-p", carpeta, "-m", missatge, "-r", "tar")
        else:
            self.kaggle("datasets", "create", "-p", carpeta, "-r", "tar")   # privat per omissió; mai --public
        t0 = time.time()
        self.dorm(30)
        while not self.dataset_llest(slug):   # el nucli només s'empeny quan el dataset és «ready»
            if time.time() - t0 > 3600:
                raise RuntimeError(f"el dataset {slug} no arriba a ready")
            self.dorm(20)

    def estat_nucli(self, slug):
        s = self.kaggle("kernels", "status", f"{USUARI}/{slug}", check=False)
        m = re.search(r'has status "?(?:KernelWorkerStatus\.)?([A-Za-z_]+)', s)   # no es llegeix «error» solt: pot ser al text
        return m.group(1).lower() if m else "desconegut"

    def llanca_nucli(self, carpeta, slug):
        out = self.kaggle("kernels", "push", "-p", carpeta, "--accelerator", "NvidiaTeslaT4")
        self.log("push", slug, out.strip()[:200])

    def espera_nucli(self, slug):
        t0, ha_comencat, ha_vist_actiu = time.time(), False, False
        self.dorm(60)
        while True:
            e = self.estat_nucli(slug)
            if e in ("queued", "running"):
                ha_vist_actiu = True
            # just després del push l'estat pot ser encara el de la versió ANTERIOR (complete): s'ignora fins que el nucli nou apareix
            if (e in ("complete", "error") or e.startswith("cancel")) and (ha_vist_actiu or time.time() - t0 > 900):
                return e
            if e == "running":
                ha_comencat = True
            if time.time() - t0 > ESPERA_MAX_S or (not ha_comencat and time.time() - t0 > ESPERA_COMENCA_MAX_S):
                raise RuntimeError(f"el nucli {slug} no acaba/comença a temps (estat {e})")
            if os.path.exists(os.path.join(self.base, "ATURA")):
                raise Atura("fitxer ATURA mentre esperava el nucli")
            self.dorm(120)

    def baixa_sortida(self, slug, carpeta):
        shutil.rmtree(carpeta, ignore_errors=True)   # lliçó: mai no es mira una sortida que no és d'aquesta execució
        os.makedirs(carpeta)
        self.kaggle("kernels", "output", f"{USUARI}/{slug}", "-p", carpeta)

    def mira_el_log(self, carpeta, slug):
        """Lliçó (iii): no s'interpreta res d'una sortida sense mirar el log."""
        logs = [f for f in os.listdir(carpeta) if f.endswith(".log")]
        if not logs:
            self.log(f"AVÍS: la sortida de {slug} no porta log")
            return ""
        txt = open(os.path.join(carpeta, logs[0]), encoding="utf-8", errors="replace").read()
        self.log(f"log {slug}: {len(txt)} car.; Traceback={'Traceback' in txt}; final: {txt[-300:].strip()!r}")
        return txt

    # -- dades d'observació (es construeixen una vegada)
    def particions(self):
        return [json.load(open(p, encoding="utf-8")) for p in
                ("/root/alta/particio.json", "/root/conc/particio.json", "/root/estricte/particio.json", "/root/transcriptor/particio.json")
                if os.path.exists(p)]

    def construeix_dades_obs(self):
        """Dataset d'observació: tots els talls APTES (§5 + porta d'alineació de la fàbrica) dels capítols llegits no retinguts, més
        els veïns (només per a la línia de temps de l'alineació). Es fa una vegada: el pare de les rondes."""
        import soundfile as sf   # noqa: PLC0415
        d = os.path.join(self.base, "dades_obs")
        if os.path.exists(os.path.join(d, "dades.ok")):
            return d
        os.environ.pop("SNRT_ALTA", None)
        os.environ.pop("SNRT_ESQ_MAX", None)   # la selecció per concordança és cosa del cercle, no de la porta de la fàbrica
        retinguts = capitols_retinguts(self.particions())
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(os.path.join(d, "audio"))
        rows, n_diana = [], 0
        caps = tb.llegeix_capitols(self.arrel)
        for slug, c in sorted(caps.items()):
            if slug in retinguts:
                continue
            carpeta = c["carpeta"]
            try:
                iv = json.load(open(os.path.join(carpeta, "talls", "intervals.json"), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ordre = sorted(iv)
            pos = {k: n for n, k in enumerate(ordre)}
            sub = {r["id"]: r for r in c["files"]}
            t02 = tb.fi_02(c["estat"])
            diana = set()
            for r in c["files"]:
                if r["id"] not in pos or r.get("credits") or not r.get("tifinag"):
                    continue
                ok, _ = tb.apta(r, tb.wav_quadra(r, carpeta, t02))
                if ok and tb.alineacio_ok(r, carpeta):
                    diana.add(r["id"])
            need = set()
            for i in diana:
                for m in (pos[i] - 1, pos[i], pos[i] + 1):
                    if 0 <= m < len(ordre):
                        need.add(ordre[m])
            os.makedirs(os.path.join(d, "audio", slug), exist_ok=True)
            for k in sorted(need):
                w = os.path.join(carpeta, "talls", k + ".wav")
                if not os.path.exists(w):
                    continue
                dades, sr = sf.read(w)
                sf.write(os.path.join(d, "audio", slug, k + ".flac"), dades, sr)
                rows.append({"id": k, "slug": slug, "a": iv[k][0], "b": iv[k][1], "tifinag": (sub.get(k) or {}).get("tifinag") or "",
                             "alvo": k in diana, "n": pos[k]})
            n_diana += len(diana)
            self.log("dades_obs", slug[:10], "diana", len(diana))
        json.dump(rows, open(os.path.join(d, "rows.json"), "w", encoding="utf-8"), ensure_ascii=False)
        shutil.copy(os.path.join(AQUI, "..", "snrt", "concordanca.py"), d)
        json.dump({"diana": n_diana, "capitols": len({r['slug'] for r in rows}), "retinguts": sorted(retinguts),
                   "data": time.strftime("%Y-%m-%d %H:%M")}, open(os.path.join(d, "dades.ok"), "w"))
        return d

    # -- passos d'una ronda
    def observa(self, model_path, dades):
        """a) concordança + alineació amb M_r. Reutilitza la sortida si ja existeix per a aquest model (sha del .pt)."""
        sha = sha12(model_path)
        obs = os.path.join(self.base, "obs", sha)
        n_diana = json.load(open(os.path.join(dades, "dades.ok")))["diana"]
        if os.path.exists(os.path.join(obs, "obs.ok")):
            self.log("observació de M", sha, "reutilitzada")
            return obs
        run_id = uuid.uuid4().hex[:12]
        md = os.path.join(self.base, "model_ds")
        shutil.rmtree(md, ignore_errors=True)
        os.makedirs(md)
        shutil.copy(model_path, os.path.join(md, "adaptador_inici.pt"))
        self.amb_reintent("dataset-model", lambda: self.puja_dataset(md, "snrt-cercle-model", "SNRT cercle model", f"M {sha} {run_id}"))
        if not self.dataset_llest("snrt-cercle-dades"):
            self.amb_reintent("dataset-dades", lambda: self.puja_dataset(dades, "snrt-cercle-dades", "SNRT cercle dades", f"dades {time.strftime('%Y-%m-%d')}"))
        nuc = self.prepara_nucli("obs", run_id)
        for intent in (1, 2):
            sortida = os.path.join(self.base, "rondes", "sortida_obs")
            shutil.rmtree(sortida, ignore_errors=True)   # lliçó (i): esborra la sortida antiga abans de llançar
            self.amb_reintent("push-obs", lambda: self.llanca_nucli(nuc, "snrt-cercle-obs"))   # si falla, NO s'espera (propaga)
            e = self.espera_nucli("snrt-cercle-obs")
            self.amb_reintent("sortida-obs", lambda: self.baixa_sortida("snrt-cercle-obs", sortida))
            self.mira_el_log(sortida, "snrt-cercle-obs")
            try:
                if e != "complete":
                    raise RuntimeError(f"nucli d'observació acabat amb estat {e}")
                info = json.load(open(os.path.join(sortida, "cercle_obs.json")))
                p = comprova_observacio(info, run_id, n_diana)
                if p:
                    raise RuntimeError("sortida d'observació no vàlida: " + "; ".join(p))
                break
            except Exception as ex:   # noqa: BLE001
                self.errors["nucli-obs"] += 1
                self.log(f"ERROR observació (intent {intent}): {ex}")
                if self.errors["nucli-obs"] >= 2:
                    raise Atura("error de Kaggle repetit 2 cops: nucli-obs")
        os.makedirs(obs, exist_ok=True)
        for f in ("concordanca.json", "alineacio.json", "concordanca_resum.json", "cercle_obs.json"):
            shutil.copy(os.path.join(sortida, f), obs)
        open(os.path.join(obs, "obs.ok"), "w").write(run_id)
        shutil.rmtree(sortida, ignore_errors=True)
        self.errors["nucli-obs"] = 0
        return obs

    def construeix_train(self, ronda_dir, model_path, obs, dades):
        """b) selecció + retall. Escriu <ronda>/ds (rows.json, audio, adaptador_inici.pt). -> (n_train, resum)."""
        import numpy as np   # noqa: F401, PLC0415
        import soundfile as sf   # noqa: PLC0415
        conc = json.load(open(os.path.join(obs, "concordanca.json"), encoding="utf-8"))
        ali = json.load(open(os.path.join(obs, "alineacio.json"), encoding="utf-8"))
        rows = json.load(open(os.path.join(dades, "rows.json"), encoding="utf-8"))
        per = collections.defaultdict(dict)
        for r in rows:
            per[r["slug"]][r["n"]] = r
        pos = {r["id"]: r for r in rows}
        retinguts = capitols_retinguts(self.particions())
        sel, motius = selecciona_parelles(conc, ali, retinguts)
        ds = os.path.join(ronda_dir, "ds")
        shutil.rmtree(ds, ignore_errors=True)
        os.makedirs(os.path.join(ds, "audio"))
        congelat = json.load(open(os.path.join(DS_CONGELAT, "rows.json"), encoding="utf-8"))
        fixos = [r for r in congelat if r["split"] in ("test", "dev")]
        fixos_text = {tb.rica(r["tifinag"]) for r in fixos}
        for r in fixos:   # el mateix test i dev de sempre (mateixos ids i so original)
            dest = os.path.join(ds, r["fitxer"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest):
                shutil.copy(os.path.join(DS_CONGELAT, r["fitxer"]), dest)
        nous, motius_clip = [], collections.Counter()
        carregues = {}

        def carrega(k):
            if k not in carregues:
                w, sr = sf.read(os.path.join(dades, "audio", pos[k]["slug"], k + ".flac"), dtype="float32")
                if w.ndim > 1:
                    w = w.mean(axis=1)
                if sr != 16000:
                    import librosa   # noqa: PLC0415
                    w = librosa.resample(w, orig_sr=sr, target_sr=16000)
                carregues[k] = w
            return carregues[k]

        for e in sel:
            r = pos[e["id"]]
            text = r["tifinag"]
            if tb.rica(text) in fixos_text:
                motius_clip["text als conjunts congelats"] += 1
                continue
            membres = [per[r["slug"]][m] for m in (r["n"] - 1, r["n"], r["n"] + 1) if m in per[r["slug"]]]
            origen, buf = monta_buffer(membres, carrega)
            fi_buf = origen + len(buf) / 16000
            fin = finestra_retall(e["al_ini"], e["al_fi"], origen=origen, fi=fi_buf)
            if fin is None:
                motius_clip["durada del retall"] += 1
                continue
            clip = talla_clip(buf, origen, *fin)
            dest = os.path.join(ds, "audio", r["slug"], r["id"] + ".flac")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            sf.write(dest, clip, 16000)
            nous.append({"id": r["id"], "slug": r["slug"], "split": "train", "tifinag": text, "durada": round(len(clip) / 16000, 2),
                         "conf": None, "dubtosos": None, "fitxer": f"audio/{r['slug']}/{r['id']}.flac"})
            if len(carregues) > 60:
                carregues.clear()
        assert not {n["slug"] for n in nous} & retinguts, "capítol retingut a train"
        assert not {tb.rica(n["tifinag"]) for n in nous} & fixos_text, "text dels conjunts congelats a train"
        json.dump(fixos + nous, open(os.path.join(ds, "rows.json"), "w", encoding="utf-8"), ensure_ascii=False)
        shutil.copy(model_path, os.path.join(ds, "adaptador_inici.pt"))
        resum = {"seleccio": motius, "retall": dict(motius_clip), "train": len(nous),
                 "hores": round(sum(n["durada"] for n in nous) / 3600, 3), "capitols": len({n["slug"] for n in nous}),
                 "fixos": collections.Counter(r["split"] for r in fixos)}
        resum["fixos"] = dict(resum["fixos"])
        return len(nous), resum

    def prepara_nucli(self, quin, run_id, seed=SEED_BASE):
        """Directori del nucli («obs» o «train») amb RUN_ID (i recepta/ritme/èpoques/llavor) escrits al guió."""
        d = os.path.join(self.base, "rondes", f"nucli_{quin}")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)

        def posa(codi, nom, valor):
            nou, n = re.subn(rf"^{nom} = .*$", lambda m: f"{nom} = {valor}", codi, flags=re.M)
            assert n == 1, f"no trobo {nom} al nucli"
            return nou
        if quin == "obs":
            codi = open(os.path.join(AQUI, "kaggle", "cercle_observa_snrt.py"), encoding="utf-8").read()
            codi = posa(codi, "RUN_ID", json.dumps(run_id))
            slug, fitxer = "snrt-cercle-obs", "snrt-cercle-obs.py"
            fonts = [f"{USUARI}/snrt-cercle-dades", f"{USUARI}/snrt-cercle-model"]
        else:
            codi = open(os.path.join(AQUI, "kaggle", "transcriptor_snrt.py"), encoding="utf-8").read()
            for nom, valor in (("RECEPTA", '"B"'), ("RITME", repr(RITME)), ("EPOQUES", str(EPOQUES)), ("SEED", str(seed)),
                               ("RUN_ID", json.dumps(run_id))):
                codi = posa(codi, nom, valor)
            slug, fitxer = "snrt-cercle-train", "snrt-cercle-train.py"
            fonts = [f"{USUARI}/snrt-cercle"] + tb.DATASETS_NUCLI
        open(os.path.join(d, fitxer), "w", encoding="utf-8").write(codi)
        json.dump({"id": f"{USUARI}/{slug}", "title": slug.replace("-", " "), "code_file": fitxer, "language": "python", "kernel_type": "script",
                   "is_private": True, "enable_gpu": True, "enable_internet": True, "dataset_sources": fonts, "kernel_sources": [],
                   "competition_sources": []}, open(os.path.join(d, "kernel-metadata.json"), "w"))
        return d

    def entrena(self, ronda_dir, model_path, n_train, seed):
        """c) puja el dataset de train, llança el nucli recepta B i en recull la sortida verificada."""
        ds = os.path.join(ronda_dir, "ds")
        self.amb_reintent("dataset-train", lambda: self.puja_dataset(ds, "snrt-cercle", "SNRT cercle train", f"ronda {os.path.basename(ronda_dir)} seed {seed}"))
        run_id = uuid.uuid4().hex[:12]
        nuc = self.prepara_nucli("train", run_id, seed)
        sortida = os.path.join(ronda_dir, "sortida_B")
        for intent in (1, 2):
            shutil.rmtree(sortida, ignore_errors=True)   # lliçó (i)
            self.amb_reintent("push-train", lambda: self.llanca_nucli(nuc, "snrt-cercle-train"))
            e = self.espera_nucli("snrt-cercle-train")
            self.amb_reintent("sortida-train", lambda: self.baixa_sortida("snrt-cercle-train", sortida))
            self.mira_el_log(sortida, "snrt-cercle-train")
            try:
                if e != "complete":
                    raise RuntimeError(f"nucli d'entrenament acabat amb estat {e}")
                res = json.load(open(os.path.join(sortida, "snrt_B_resultat.json"), encoding="utf-8"))
                nou = os.path.join(sortida, "adaptador_shi_snrt_B.pt")
                p = comprova_entrenament(res, run_id, seed, n_train, sha12(nou), sha12(model_path))
                if p:
                    raise RuntimeError("sortida d'entrenament no vàlida: " + "; ".join(p))
                if res["config"].get("train_zouhir") != ANCORATGE_H4B:
                    self.log(f"AVÍS: ancoratge H4b {res['config'].get('train_zouhir')} (esperats {ANCORATGE_H4B})")
                self.errors["nucli-train"] = 0
                return res, sortida
            except Exception as ex:   # noqa: BLE001
                self.errors["nucli-train"] += 1
                self.log(f"ERROR entrenament (intent {intent}): {ex}")
                if self.errors["nucli-train"] >= 2:
                    raise Atura("error de Kaggle repetit 2 cops: nucli-train")

    def ronda(self, r, intent):
        model, idx = self.model_actual()
        seed = SEED_BASE + 1000 * intent
        t0 = time.time()
        self.log(f"=== RONDA {r} · model M{idx} ({sha12(model)}) · intent {intent} · seed {seed}")
        dades = self.construeix_dades_obs()
        obs = self.observa(model, dades)
        rdir = os.path.join(self.base, "rondes", f"r{r:03d}")
        os.makedirs(rdir, exist_ok=True)
        n_train, resum = self.construeix_train(rdir, model, obs, dades)
        self.log("train construït", json.dumps(resum, ensure_ascii=False))
        if n_train < 200:
            raise Atura(f"només {n_train} talls seleccionats a la ronda {r}: dades insuficients")
        res, sortida = self.entrena(rdir, model, n_train, seed)
        av = tb.avalua(os.path.join(sortida, "snrt_B_sortides.json"))
        stats = av["stats"]
        regla = regla_interna(stats)
        nou = os.path.join(sortida, "adaptador_shi_snrt_B.pt")
        entrada = {"ronda": r, "data": time.strftime("%Y-%m-%d %H:%M"), "model_idx": idx, "model_sha": sha12(model), "seed": seed, "intent": intent,
                   "train_snrt": res["config"]["train_snrt"], "train_total": res["config"]["train"], "hores_train": round(res["config"]["hores_train"], 3),
                   "seleccio": resum, "stats": resum_stats(stats), "adopta": regla["adopta"], "milloren": regla["milloren"],
                   "empitjoren": regla["empitjoren"], "motiu": regla["motiu"], "adaptador_nou_sha": sha12(nou),
                   "sortida": rdir, "segons": round(time.time() - t0)}
        if regla["adopta"]:
            shutil.copy(nou, os.path.join(self.base, "models", f"M{idx + 1}.pt"))
            entrada["model_nou"] = f"M{idx + 1}.pt"
        else:
            shutil.copy(nou, os.path.join(rdir, "adaptador_descartat.pt"))
        shutil.rmtree(os.path.join(sortida, "afinat"), ignore_errors=True)
        shutil.rmtree(os.path.join(rdir, "ds"), ignore_errors=True)
        self.apunta(entrada)
        self.log(f"ronda {r}: {'ADOPTA M%d' % (idx + 1) if regla['adopta'] else 'DESCARTADA'} · {regla['motiu']}")
        return entrada

    def corre(self, max_rondes=None):
        os.makedirs(self.base, exist_ok=True)
        m0 = os.path.join(self.base, "models", "M0.pt")
        if not os.path.exists(m0):
            shutil.copy("/root/alta/sortida_B/adaptador_shi_snrt_B.pt", m0)   # alta+ancoratge B: model de partida i línia base
        feta = 0
        try:
            while True:
                rs = self.rondes()
                motiu = motiu_aturada(rs, os.path.exists(os.path.join(self.base, "ATURA")), self.disc_lliure_gb(), self.errors)
                if motiu:
                    raise Atura(motiu)
                if max_rondes is not None and feta >= max_rondes:
                    raise Atura(f"{max_rondes} rondes fetes (--rondes)")
                idx = self.model_actual()[1]
                intent = sum(1 for x in rs if x["model_idx"] == idx) + 1
                self.ronda(len(rs), intent)
                feta += 1
        except Atura as a:
            self.log("ATURAT:", a)
            self.estat_md("ATURAT", f"— {a}")
        except Exception as e:   # noqa: BLE001
            self.log("ERROR INESPERAT:", repr(e))
            self.estat_md("ERROR", f"— {e!r}"[:200])
            raise


def sha12(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="/root/cercle")
    ap.add_argument("--arrel", default="/root/tamazight_tv")
    ap.add_argument("--rondes", type=int, default=None, help="màxim de rondes d'aquesta execució")
    a = ap.parse_args(argv)
    if os.environ.get("KAGGLE_USERNAME") is None and os.path.exists("/root/.env"):
        for l in open("/root/.env", encoding="utf-8"):   # secrets: es carreguen a l'entorn, mai no s'imprimeixen
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.strip().split("=", 1)
                os.environ.setdefault(k.replace("export ", "").strip(), v.strip().strip('"').strip("'"))
    Cercle(a.base, a.arrel).corre(a.rondes)


if __name__ == "__main__":
    main()
