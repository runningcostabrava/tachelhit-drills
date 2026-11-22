"""La fàbrica ja sabia quins capítols havia llegit malament?

Als catorze capítols de sota (acord ≤ 1,7 %) l'ull no diu res i l'orella i l'àrab es confirmen
l'un a l'altre: el problema és la lectura, no la parla. I mirant la franja d'un d'ells es veu
per què —el subtítol va sobre un fons fosc i carregat de branques, i binaritzar-lo falla.

La pregunta pràctica: la fàbrica desa `tifinag_conf_mitjana` a cada capítol. ¿Aquell número ja
avisava? Si avisa, tenim un filtre barat per saber de quins capítols fiar-nos sense haver de
passar-hi el transcriptor.
"""
import io
import json
import os
import statistics
import tarfile
import tempfile
from pathlib import Path

for l in io.open(r"C:\Users\josep\app2\tachelhit-drills\backend\.env", encoding="utf-8",
                 errors="replace"):
    l = l.strip()
    if l.startswith("HF_TOKEN") and "=" in l:
        os.environ["HF_TOKEN"] = l.split("=", 1)[1].strip().strip('"').strip("'")

from huggingface_hub import hf_hub_download  # noqa: E402

acord = {}
for l in io.open(r"E:/tamazight/_magatzem/acord_26.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        c = acord.setdefault(r["capitol"], [0, 0])
        c[1] += 1
        c[0] += r["grau"] == "A"

out = []
for slug, (a, n) in acord.items():
    try:
        t = hf_hub_download("josepabloucr/tamazight-tv-privat", f"capitols/{slug}/dades.tar",
                            repo_type="dataset", token=os.environ["HF_TOKEN"])
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(t) as z:
                try:
                    z.extractall(tmp, filter="data")
                except TypeError:
                    z.extractall(tmp)
            p = next(Path(tmp).rglob("numeros.json"), None)
            d = json.load(io.open(p, encoding="utf-8")) if p else {}
    except Exception:
        continue
    out.append((a / n, slug, d.get("tifinag_conf_mitjana"), d.get("arab_acord_mitja"),
                d.get("tifinag_glifs"), d.get("tifinag_dubtosos_total") or d.get("tifinag_dubtosos")))

out.sort(reverse=True)
print(f"{'capítol':<18}{'acord':>7}{'conf tifinag':>14}{'acord àrab':>12}{'glifs':>8}")
for a, s, tc, aa, gl, du in out:
    print(f"{s[:16]:<18}{100*a:6.1f}%{(tc if tc is not None else -1):14.4f}"
          f"{(aa if aa is not None else -1):12.4f}{(gl or 0):8d}")

xs = [o[2] for o in out if o[2] is not None]
ys = [o[0] for o in out if o[2] is not None]
if len(xs) > 3:
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    print(f"\ncorrelació acord ↔ confiança del tifinag: {num/den if den else 0:+.2f}")
    print("(si és alta, la fàbrica ja sabia quins havia llegit malament i no ho vam mirar)")
