# TRIANGULACIO (#763), pas 4: compara la via 3 entrenada amb el train FILTRAT contra el seu CONTROL
# d'atzar (els dos quaderns triangulacio-afina.py). Un sol numero per test no basta: les tirades 1a
# i 2a van diferir 0,005 sense que res important canviés, aixi que la diferencia es jutja amb un
# bootstrap aparellat que remostreja BLOCS de 20 talls seguits d'un mateix capitol (`grup`), no talls
# solts: els talls veins comparteixen parlant i tema. Capitols sencers no serveixen: test_snrt en te 4.
#
# A test_snrt tambe es separa per l'acord ASR <-> pantalla del tall de test (triangulacio_test.json,
# §58): si el filtre nomes ajuda on la referencia ja es bona, aqui es veu.
#
#   python triangulacio_compara.py resultat_filtrat.json resultat_atzar.json
import io, json, random, sys
from collections import Counter, defaultdict

TRI = "E:/tamazight/_magatzem/tirades/triangulacio/triangulacio_test.json"
LLAVOR, VOLTES, BLOC = 1114, 2000, 20


def chrf(hip, ref, n=6, beta=2.0):
    """El mateix chrF que el quadern (veu-ar-afina.py), perque els numeros casin amb els seus."""
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        ch, cr = Counter(h), Counter(r)
        com = sum((ch & cr).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def per_tall(resultat, test):
    """so -> (bloc, chrF). El bloc es el capitol i la posicio dins del capitol en l'ordre del test."""
    vistos, out = Counter(), {}
    for x in resultat["tests"][test]["files"]:
        bloc = (x["grup"], vistos[x["grup"]] // BLOC)
        vistos[x["grup"]] += 1
        out[x["so"]] = (bloc, chrf(x["model"].strip(), x["ar"]))
    return out


def bootstrap(a, b, sons):
    """Diferencia mitjana a-b i interval del 95 %, remostrejant blocs."""
    per_grup = defaultdict(list)
    for s in sons:
        per_grup[a[s][0]].append(a[s][1] - b[s][1])
    grups = list(per_grup)
    rng = random.Random(LLAVOR)
    mostres = []
    for _ in range(VOLTES):
        d = [v for g in rng.choices(grups, k=len(grups)) for v in per_grup[g]]
        mostres.append(sum(d) / len(d))
    mostres.sort()
    tot = [v for g in grups for v in per_grup[g]]
    return sum(tot) / len(tot), mostres[int(VOLTES * .025)], mostres[int(VOLTES * .975)], len(grups)


def main(fa, fb):
    ra = json.load(io.open(fa, encoding="utf-8"))
    rb = json.load(io.open(fb, encoding="utf-8"))
    na, nb = ra.get("variant", fa), rb.get("variant", fb)
    print(f"{na} ({ra.get('files_train')} files) contra {nb} ({rb.get('files_train')} files)")
    print(f"   millor dev: {ra['millor_dev']:.4f} contra {rb['millor_dev']:.4f}")
    cer = {x["so"]: x["cer"] for x in json.load(io.open(TRI, encoding="utf-8"))}
    for test in ("test_snrt", "test_tutlait"):
        a, b = per_tall(ra, test), per_tall(rb, test)
        assert set(a) == set(b), f"{test}: els dos resultats no tenen els mateixos talls"
        franges = {"tot": list(a)}
        if test == "test_snrt":
            amb = {s: cer.get(s) for s in a}
            franges["CER < 0,75"] = [s for s, c in amb.items() if c is not None and c < .75]
            franges["CER >= 0,75"] = [s for s, c in amb.items() if c is not None and c >= .75]
            franges["sense CER"] = [s for s, c in amb.items() if c is None]
        print(f"\n== {test} ==")
        for nom, sons in franges.items():
            if not sons:
                continue
            ma = sum(a[s][1] for s in sons) / len(sons)
            mb = sum(b[s][1] for s in sons) / len(sons)
            d, lo, hi, ng = bootstrap(a, b, sons)
            senyal = "" if lo <= 0 <= hi else ("  <- " + (na if d > 0 else nb) + " guanya")
            print(f"   {nom:12} {len(sons):5} talls · {ng:3} blocs · {na} {ma:.4f} · {nb} {mb:.4f}"
                  f" · dif {d:+.4f} [{lo:+.4f}, {hi:+.4f}]{senyal}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
