"""lot.py — llegeix el canal aslmdtv d'un vídeo en un: baixa, llegeix.py, comprova (3 files),
apunta els números a lot_estat.json i esborra el .mp4 i els fotogrames.
Ús: python -X utf8 lot.py [quants] [--des=k]   (segueix per on anava: lot_estat.json)"""
import json, os, re, subprocess, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
ARREL = os.path.dirname(AQUI)
PY = sys.executable
quants = int([a for a in sys.argv[1:] if not a.startswith("--")][0]) if [a for a in sys.argv[1:] if not a.startswith("--")] else 5
llista = json.load(open(os.path.join(AQUI, "lot_llista.json"), encoding="utf-8"))
estat_p = os.path.join(AQUI, "lot_estat.json")
estat = json.load(open(estat_p, encoding="utf-8")) if os.path.exists(estat_p) else {}
log = open(os.path.join(AQUI, "lot.log"), "a", encoding="utf-8")


def diu(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True); log.write(s + "\n"); log.flush()


def corre(cmd, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=AQUI)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


refes = [a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--refes=")]
refes = refes[0] if refes else []
fets = 0
for v in llista:
    vid = v["id"]
    if refes and vid not in refes:
        continue
    if not refes and vid in estat and estat[vid].get("estat") in ("fet", "baixada_fallida", "lectura_fallida"):
        continue
    if fets >= quants:
        break
    fets += 1
    t0 = time.time()
    mp4 = os.path.join(ARREL, f"{vid}.mp4")
    reg = {"id": vid, "titol": v["titol"], "mena": v["mena"], "durada": v["durada"]}
    diu(f"\n===== {vid}  {v['mena']}  {v['titol'][:60]}")
    if not os.path.exists(mp4):
        rc, out = corre([PY, "-m", "yt_dlp", "--js-runtimes", "node", "--extractor-args", "youtube:player_client=android",
                         "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]", "--merge-output-format", "mp4",
                         "-o", mp4, f"https://www.youtube.com/watch?v={vid}"], timeout=1200)
        if rc != 0 or not os.path.exists(mp4):
            reg["estat"] = "baixada_fallida"; reg["error"] = out[-600:]
            diu("  baixada fallida:", out[-300:].replace("\n", " | "))
            estat[vid] = reg; json.dump(estat, open(estat_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            subprocess.run(["ping", "-n", "11", "127.0.0.1"], capture_output=True)
            continue
        reg["mb"] = round(os.path.getsize(mp4) / 1e6, 1)
        diu(f"  baixat: {reg['mb']} MB")
    rc, out = corre([PY, "-X", "utf8", os.path.join(AQUI, "llegeix.py"), mp4], timeout=2400)
    out = "\n".join(l for l in out.splitlines() if "Warning" not in l)
    reg["sortida_llegeix"] = out[-3000:]
    if rc != 0:
        reg["estat"] = "lectura_fallida"
        diu("  llegeix.py ha fallat:", out[-500:].replace("\n", " | "))
    else:
        m = re.search(r"mode (\w+)", out); reg["mode"] = m.group(1) if m else "?"
        m = re.search(r"(\d+) pàgines reals", out); reg["pagines"] = int(m.group(1)) if m else None
        m = re.search(r"alçada de caixa alta: \[([^\]]*)\]", out); reg["alcades"] = m.group(1) if m else ""
        m = re.search(r"files triades, llindar 0\.85: accepta (\d+) de (\d+) \(([\d.]+) %\)", out)
        if m:
            reg["glifs_triats"], reg["acceptats"], reg["pct"] = int(m.group(2)), int(m.group(1)), float(m.group(3))
        m = re.search(r"(\d+) files, (\d+) glifs, (\d+) nous en (\d+) grups", out)
        if m:
            reg["files"], reg["nous"], reg["grups_nous"] = int(m.group(1)), int(m.group(3)), int(m.group(4))
        # files finals (després de fusions) i glifs únics
        try:
            T = json.load(open(os.path.join(AQUI, f"transcripcio_{vid}.json"), encoding="utf-8"))
            reg["files_finals"] = len(T); reg["glifs_finals"] = sum(r["n_glifs"] for r in T)
            reg["nous_finals"] = sum(r["n_nous"] for r in T)
            txt = " ".join(r["tifinag"] for r in T)
            reg["lletres"] = "".join(sorted({c for c in txt if "ⴰ" <= c <= "⵿"}))
            reg["rars"] = {k: txt.count(k) for k in "ⵯⵄⵅⵚ" if txt.count(k)}
        except Exception as e:
            reg["error_transcripcio"] = str(e)
        # resum dels grups de glifs nous (per saber si cal mirar el mosaic)
        try:
            G = {g["n"]: g for g in json.load(open(os.path.join(AQUI, f"glifs_{vid}.json"), encoding="utf-8"))}
            N = json.load(open(os.path.join(AQUI, f"nous_{vid}.json"), encoding="utf-8"))
            resum = []
            for k, idx in N.items():
                gs = [G[i] for i in idx if i in G]
                if not gs:
                    continue
                resum.append({"grup": k, "n": len(gs), "millor": gs[0]["millor"], "conf": round(sum(g["conf"] for g in gs) / len(gs), 2),
                              "h": round(sum(g["h_rel"] for g in gs) / len(gs), 2), "w": round(sum(g["w_rel"] for g in gs) / len(gs), 2)})
            reg["grups_nous_resum"] = resum
            cand = [r for r in resum if r["n"] >= 3 and 0.75 <= r["h"] <= 1.3]
            reg["candidats_lletra"] = cand
            diu("  grups nous candidats a lletra:", cand)
        except Exception as e:
            reg["error_nous"] = str(e)
        rc2, out2 = corre([PY, "-X", "utf8", os.path.join(AQUI, "comprova.py"), "1114", "3", vid], timeout=300)
        reg["comprova"] = "\n".join(l for l in out2.splitlines() if "Warning" not in l and not l.startswith("["))
        reg["estat"] = "fet"
        diu(f"  mode {reg.get('mode')} pàgines {reg.get('pagines')} glifs {reg.get('glifs_triats')} acceptats {reg.get('pct')} % "
            f"nous {reg.get('nous')} files {reg.get('files_finals')} rars {reg.get('rars')}")
        if reg.get("pct") is not None and reg["pct"] < 90:
            diu("  ATENCIÓ: < 90 % acceptats")
    reg["segons"] = round(time.time() - t0)
    estat[vid] = reg
    json.dump(estat, open(estat_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # neteja
    for p in [mp4]:
        if os.path.exists(p):
            os.remove(p)
    fot = os.path.join(AQUI, f"fot_{vid}")
    if os.path.isdir(fot):
        for f in os.listdir(fot):
            os.remove(os.path.join(fot, f))
        os.rmdir(fot)
    diu(f"  {reg['segons']} s")
    subprocess.run(["ping", "-n", "11", "127.0.0.1"], capture_output=True)
diu(f"lot acabat: {fets} vídeos en aquesta passada")
