"""Que diuen, de veritat, les replicas d'un capitol que te 0,4% d'acord.

Descartat el desajust d'index (d=0 guanya pertot), queden poques explicacions i no es poden
triar per raonament: s'han de mirar. Per a un capitol dolent i un bo, es posen de costat les
tres lectures de la mateixa replica -- el que es veu en tifinag, el que se sent, i l'arab --
i es compta quantes replicas tenen so i quina confianca te l'orella.

Si la llengua parlada no es l'amaziga (serie doblada, programa en arab), l'ull llegeix un
subtitol que es una TRADUCCIO i no una transcripcio, i llavors l'acord baix es correcte: no
hi ha res a arreglar, nomes s'ha de saber de quins capitols no es pot aprendre so.
"""
import io, json, sys
from pathlib import Path
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
RELLEGIT = Path(r"E:/tamazight/_magatzem/rellegit_bo")
VISOR = Path(r"E:/tamazight/_visor")
CASOS = [("hmssyuzoyqzywbaj", "0,4 %"), ("oeeljuwkqlqtebzr", "0,5 %"),
         ("bueyrhjvjyaleocf", "41,7 % (per comparar)")]

sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

for pref, etiqueta in CASOS:
    slug = next((p.stem for p in RELLEGIT.glob("*.json") if p.stem.startswith(pref)), None)
    if not slug:
        continue
    llegit = json.load(io.open(RELLEGIT / f"{slug}.json", encoding="utf-8"))["llegit"]
    arab = {}
    for i, l in enumerate(io.open(VISOR / slug / "subtitols.jsonl", encoding="utf-8")):
        if l.strip():
            x = json.loads(l)
            arab[str(x.get("k", i))] = (x.get("arab") or "").strip()
    claus = [k for k in llegit if sentit.get(f"{slug}:{k}", {}).get("sentit")]
    confs = [sentit[f"{slug}:{k}"].get("conf") for k in claus
             if sentit[f"{slug}:{k}"].get("conf") is not None]
    amb_so = sum(1 for k in llegit if (sentit.get(f"{slug}:{k}", {}).get("sentit") or "").strip())
    print(f"\n=== {slug[:16]}  acord {etiqueta} ===")
    print(f"replicas {len(llegit)} | amb so {amb_so} ({100*amb_so/max(1,len(llegit)):.0f}%) | "
          f"confianca mitjana {sum(confs)/len(confs) if confs else 0:.3f}")
    for k in claus[20:28]:
        s = sentit[f"{slug}:{k}"]
        print(f"  ull  {esquelet(llegit[k]):<28} {llegit[k][:34]}")
        print(f"  oida {esquelet(s['sentit']):<28} {s['sentit'][:34]}   conf {s.get('conf')}")
        print(f"  arab {arab.get(k, '')[:60]}")
