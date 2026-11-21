# -*- coding: utf-8 -*-
"""Ablació de la v3 (#494, 17-11-2026): la v3 sense les parelles dels auditors, contra la v3 i contra la v2, sobre les
MATEIXES frases (60 i 200), amb IC 95 % per bootstrap aparellat (llavor 1114, 2.000 mostres). Llegeix resultats_casa.json
(sortida d'avalua_a_casa.py) de cada carpeta.
ÚS: compara_ablacio.py <carpeta_ablacio> <carpeta_v3> <carpeta_v2>  → escriu taula_ablacio.md a la carpeta d'ablació"""
import io, json, os, random, sys

AB, V3, V2 = sys.argv[1:4]


def carrega(c):
    r = json.load(io.open(os.path.join(c, "resultats_casa.json"), encoding="utf-8"))
    return {(s["prova"], s["id"], s["model"]): s for s in r["frases"]}


fa, f3, f2 = carrega(AB), carrega(V3), carrega(V2)
grup = {(k[0], k[1]): s["grup"] for k, s in fa.items()}
ids = {p: sorted({k[1] for k in fa if k[0] == p}) for p in ("mostra60", "test200")}
assert ids["test200"] == sorted({k[1] for k in f3 if k[0] == "test200"}) == sorted({k[1] for k in f2 if k[0] == "test200"})


def ic(a, b, n=2000):
    rnd = random.Random(1114)
    N = len(a)
    d = [y - x for x, y in zip(a, b)]
    boots = sorted(sum(d[i] for i in [rnd.randrange(N) for _ in range(N)]) / N for _ in range(n))
    return sum(a) / N, sum(b) / N, sum(d) / N, boots[int(0.025 * n)], boots[int(0.975 * n)], sum(1 for x in d if x > 5e-4), sum(1 for x in d if x < -5e-4)


GRUPS = [("60 frases", "mostra60", None), ("shi (30)", "mostra60", "shi"), ("Beni Mellal (30)", "mostra60", "beni-mellal"), ("test-dins (200)", "test200", None)]
COMP = [("abans → ablació", fa, "abans", fa, "millor"), ("v2 (3e-5, ep3) → ablació", f2, "lr3e-05-ep3", fa, "millor"),
        ("ablació → v3 (amb les 302)", fa, "millor", f3, "millor")]
linies = ["| camí | comparació | grup | A | B | Δ | IC 95 % | milloren / empitjoren |", "|---|---|---|---|---|---|---|---|"]
for cami, clau in [("català directe", "chrf_ca"), ("pont anglès + deepseek-chat", "chrf_pont")]:
    for nom, A_, ma, B_, mb in COMP:
        for gnom, prova, g in GRUPS:
            ks = [i for i in ids[prova] if (g is None or grup[(prova, i)] == g) and (prova, i, ma) in A_ and (prova, i, mb) in B_
                  and clau in A_[(prova, i, ma)] and clau in B_[(prova, i, mb)]]
            if not ks:
                continue
            a = [A_[(prova, i, ma)][clau] for i in ks]
            b = [B_[(prova, i, mb)][clau] for i in ks]
            A, B, d, lo, hi, mill, pitj = ic(a, b)
            linies.append(f"| {cami} | {nom} | {gnom} | {A:.3f} | {B:.3f} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {mill} / {pitj} |")
print("\n".join(linies))
io.open(os.path.join(AB, "taula_ablacio.md"), "w", encoding="utf-8").write("\n".join(linies) + "\n")
