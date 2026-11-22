"""Un fotograma sense subtitols no prova res: nomes surten quan algu parla.

El 22-11 vaig mirar UN fotograma de cada programa i sis em van sortir nets. Per `tifawin` la
conclusio es solida (40 fotogrames mirats i 30 capitols caiguts), pero per als altres sis
descartar 110 capitols amb un cop d'ull seria el mateix error que vaig cometre amb la sonda:
decidir sobre poca mostra i escriure-ho a moltes files.

Aqui es miren **24 fotogrames repartits** de cada programa i es compta en quants hi ha **dues
linies de text** a la franja de baix -- que es el que la fabrica necessita.

Per comparar: `tadfi-n-tskla`, que funciona, i `tifawin`, que no.

No toca res: nomes compta i ho escriu.
"""
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(r"E:/tamazight/fabrica")
sys.path.insert(0, str(AQUI / "tools" / "snrt" / "fabrica"))
from PIL import Image  # noqa: E402

import ordre_linies as ol  # noqa: E402

BAIXA = AQUI / "tools" / "snrt" / "baixa_replay.py"
CAT = AQUI / "cataleg" / "capitols.jsonl"
PY = r"C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe"
QUANTS = 24
PART_BAIXA = 0.55


def filla(mestra, qual="1280x720"):
    base, _, q = mestra.partition("?")
    return f"{base.rsplit('/', 1)[0]}/{qual}/chunks.m3u8?{q}"


def adreca(c):
    r = subprocess.run([PY, "-X", "utf8", str(BAIXA), c["url_snrt"], "--nomes-url"],
                       capture_output=True, text=True, timeout=180)
    l = [x for x in (r.stdout or "").splitlines() if "m3u8" in x]
    return filla(l[-1].strip()) if l else None


caps = [json.loads(l) for l in io.open(CAT, encoding="utf-8") if l.strip()]
vistos, tria = set(), []
for c in caps:
    p = c.get("programa")
    if p in vistos or not c.get("url_snrt"):
        continue
    vistos.add(p)
    tria.append(c)

print(f"{len(tria)} programes · {QUANTS} fotogrames de cadascun\n", flush=True)
print(f"   {'programa':<28}{'amb 2 línies':>14}{'de':>5}   veredicte")

for c in tria:
    p = c["programa"]
    u = adreca(c)
    if not u:
        print(f"   {str(p)[:27]:<28}{'—':>14}{'—':>5}   no s'ha pogut resoldre l'adreça")
        continue
    dues, mirats = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(QUANTS):
            t = 300 + i * 110
            d = Path(tmp) / f"f{i}.png"
            subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", u, "-frames:v", "1", str(d)],
                           capture_output=True, timeout=300)
            if not d.exists() or d.stat().st_size < 2000:
                continue
            mirats += 1
            im = Image.open(d).convert("RGB")
            im = im.crop((0, int(im.height * PART_BAIXA), im.width, im.height))
            try:
                if ol.ordre_del_fotograma(im):
                    dues += 1
            except Exception:
                pass
    if not mirats:
        diu = "cap fotograma llegit"
    elif dues == 0:
        diu = "cap línia: NO sembla tenir subtítols"
    elif dues / mirats < 0.15:
        diu = f"molt pocs ({100*dues/mirats:.0f} %): dubtós"
    else:
        diu = f"SÍ, en té ({100*dues/mirats:.0f} % dels fotogrames)"
    print(f"   {str(p)[:27]:<28}{dues:>14}{mirats:>5}   {diu}", flush=True)
