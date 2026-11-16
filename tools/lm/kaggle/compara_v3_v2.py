# -*- coding: utf-8 -*-
"""H-MT1 v3 contra v2 (16-11-2026, nit). Agafa resultats_casa.json de la v3 (sortida d'avalua_a_casa.py, amb el
chrF del català directe i del pont per frase) i el de la v2, i dóna, sobre les MATEIXES frases (60 i 200):
  abans → v3 (millor checkpoint), v2 → v3, i v3 fp16 → v3 ct2 int8, amb IC 95 % per bootstrap aparellat (1114, 2.000).
ÚS: compara_v3_v2.py <carpeta_v3> <carpeta_v2>"""
import io, json, os, random, sys

V3, V2 = sys.argv[1], sys.argv[2]
r3 = json.load(io.open(os.path.join(V3, "resultats_casa.json"), encoding="utf-8"))
r2 = json.load(io.open(os.path.join(V2, "resultats_casa.json"), encoding="utf-8"))
f3 = {(s["prova"], s["id"], s["model"]): s for s in r3["frases"]}
f2 = {(s["prova"], s["id"], s["model"]): s for s in r2["frases"]}
grup = {(s["prova"], s["id"]): s["grup"] for s in r3["frases"]}
ids = {p: sorted({k[1] for k in f3 if k[0] == p}) for p in ("mostra60", "test200")}
assert ids["test200"] == sorted({k[1] for k in f2 if k[0] == "test200"}), "el test-dins no és el mateix"


def ic(a, b, n=2000):
    rnd = random.Random(1114)
    N = len(a)
    d = [y - x for x, y in zip(a, b)]
    boots = sorted(sum(d[i] for i in [rnd.randrange(N) for _ in range(N)]) / N for _ in range(n))
    return sum(a) / N, sum(b) / N, sum(d) / N, boots[int(0.025 * n)], boots[int(0.975 * n)], sum(1 for x in d if x > 5e-4), sum(1 for x in d if x < -5e-4)


GRUPS = [("60 frases", "mostra60", None), ("shi (30)", "mostra60", "shi"), ("Beni Mellal (30)", "mostra60", "beni-mellal"), ("test-dins (200)", "test200", None)]
COMP = [("abans → v3 (millor)", f3, "abans", f3, "millor"), ("v2 (3e-5, ep3) → v3 (millor)", f2, "lr3e-05-ep3", f3, "millor"),
        ("v3 fp16 → v3 ct2 int8", f3, "millor", f3, "millor-ct2int8")]
linies = ["| camí | comparació | grup | A | B | Δ | IC 95 % | milloren / empitjoren |", "|---|---|---|---|---|---|---|---|"]
for cami, clau in [("català directe", "chrf_ca"), ("pont anglès + deepseek-chat", "chrf_pont")]:
    for nom, fa, ma, fb, mb in COMP:
        for gnom, prova, g in GRUPS:
            ks = [i for i in ids[prova] if (g is None or grup[(prova, i)] == g) and (prova, i, ma) in fa and (prova, i, mb) in fb
                  and clau in fa[(prova, i, ma)] and clau in fb[(prova, i, mb)]]
            if not ks:
                continue
            a = [fa[(prova, i, ma)][clau] for i in ks]
            b = [fb[(prova, i, mb)][clau] for i in ks]
            A, B, d, lo, hi, mill, pitj = ic(a, b)
            linies.append(f"| {cami} | {nom} | {gnom} | {A:.3f} | {B:.3f} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {mill} / {pitj} |")
print("\n".join(linies))
io.open(os.path.join(V3, "taula_v3_contra_v2.md"), "w", encoding="utf-8").write("\n".join(linies) + "\n")
