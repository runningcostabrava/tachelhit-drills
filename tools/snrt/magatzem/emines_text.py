"""Llegeix NOMES text i metadades d'EMINES (sense audio) i mira si s'encavalca amb el nostre corpus."""
import io, json, sys
from collections import Counter
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalitza_arab import norma

fs = HfFileSystem()
REPO = "datasets/EMINES/Tamazight-Speech-to-Arabic-Text/data"
files = []
for p in sorted(fs.ls(REPO, detail=False)):
    if not p.endswith(".parquet"):
        continue
    with fs.open(p, "rb", block_size=1 << 20) as f:
        t = pq.ParquetFile(f).read(columns=["text", "metadata"])
    part = p.rsplit("/", 1)[1].split("-")[0]
    for i, (txt, md) in enumerate(zip(t.column("text").to_pylist(), t.column("metadata").to_pylist())):
        files.append({"fitxer": p.rsplit("/", 1)[1], "idx": i, "particio": part, "ar": txt, **md})
    print(p.rsplit("/", 1)[1], len(files), flush=True)
io.open(r"E:/tamazight/_magatzem/emines/text.jsonl", "w", encoding="utf-8").write(
    "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in files))

nostres = {}
for nom in ["train", "dev", "test_snrt", "test_tutlait"]:
    for l in io.open(rf"E:/tamazight/_magatzem/veu_ar_combinat_baba/{nom}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        nostres.setdefault(norma(x["ar"]), set()).add(f"{nom}:{x['font']}")
fonts = Counter(x["source"] for x in files)
print("videos:", len(fonts), "· hores:", round(sum(x["duration"] for x in files) / 3600, 2))
print("particio x video:", {k: len({x['source'] for x in files if x['particio'] == k}) for k in ("train", "test")})
comu = Counter()
llargs = Counter()
for x in files:
    n = norma(x["ar"])
    for t in nostres.get(n, ()):
        comu[t] += 1
        if len(n.split()) >= 4:
            llargs[t] += 1
print("frases EMINES identiques a les nostres:", dict(comu))
print("  de 4 paraules o mes:", dict(llargs))
