# -*- coding: utf-8 -*-
"""Un model de llengua en format ARPA, escrit a mà, per a pyctcdecode/KenLM.

Per què a mà: pyctcdecode NOMÉS fa servir la llista de paraules (`unigrams`) si hi ha un model
KenLM; sense fitxer .arpa, el feix ignora el lèxic i la ruta /transcribe_mms_lm del Space és
una descodificació per feix sense cap lèxic (comprovat al codi font de pyctcdecode, 15-11-2026).
Per tant la hipòtesi H3 no s'ha provat mai. Aquest guió fa l'ARPA que li falta.

Dos models, per separar l'efecte del lèxic del de l'ordre de paraules:
  A) `lexic.arpa`      — només unigrames: totes les formes del lèxic amb la mateixa massa (i les
                        del corpus amb la seva freqüència). És la «restricció al lèxic» pura.
  B) `corpus_bi.arpa`  — bigrames del corpus de la biblioteca (7.461 frases de parlants) amb
                        descompte absolut i recaiguda a unigrames; les formes del lèxic que no
                        són al corpus hi entren com a unigrames amb compte 1.

Res del conjunt de prova (els 8 vídeos amb subtítols humans) no entra aquí.

ÚS:  fes_arpa.py <corpus_shi.txt> <unigrams_shi.txt> <carpeta de sortida>
"""
import collections
import io
import math
import os
import sys

D = 0.75          # descompte absolut (Ney); el valor clàssic


def log10(x):
    return math.log10(x) if x > 0 else -99.0


def llegeix_frases(cami):
    for l in io.open(cami, encoding="utf-8"):
        t = l.strip().split()
        if t:
            yield t


def escriu_arpa(cami, uni, bi=None, backoff=None):
    """uni: {w: logprob}; bi: {(a,b): logprob}; backoff: {w: log backoff}"""
    with io.open(cami, "w", encoding="utf-8", newline="\n") as g:
        g.write("\\data\\\n")
        g.write(f"ngram 1={len(uni)}\n")
        if bi:
            g.write(f"ngram 2={len(bi)}\n")
        g.write("\n\\1-grams:\n")
        for w, lp in sorted(uni.items(), key=lambda x: x[0]):
            if bi and w in backoff and w != "</s>":
                g.write(f"{lp:.6f}\t{w}\t{backoff[w]:.6f}\n")
            else:
                g.write(f"{lp:.6f}\t{w}\n")
        if bi:
            g.write("\n\\2-grams:\n")
            for (a, b), lp in sorted(bi.items()):
                g.write(f"{lp:.6f}\t{a} {b}\n")
        g.write("\n\\end\\\n")


def model_lexic(corpus, unigrams, fora):
    c = collections.Counter()
    for t in corpus:
        c.update(t)
        c["</s>"] += 1
    for w in unigrams:
        c[w] += 1                       # cada forma del lèxic, com a mínim un cop
    c["<unk>"] = 1
    total = sum(c.values())
    uni = {w: log10(n / total) for w, n in c.items()}
    uni["<s>"] = -99.0
    #: KenLM no sempre accepta un model d'ordre 1: s'escriu com a bigrama amb un sol bigrama
    #: fictici i recaiguda zero a tot arreu, que és exactament el model d'unigrames.
    escriu_arpa(fora, uni, {("<s>", "</s>"): -3.0}, {w: 0.0 for w in uni})
    return len(uni)


def model_bigram(corpus, unigrams, fora):
    """Descompte absolut interpolat (Kneser-Ney simplificat: la distribució de recaiguda és la
    de continuació). Prou bo per a un corpus petit; el que importa aquí és el senyal, no l'última
    dècima de perplexitat."""
    c1 = collections.Counter()
    c2 = collections.Counter()
    for t in corpus:
        s = ["<s>"] + t + ["</s>"]
        c1.update(s[1:])
        c1["<s>"] += 1
        for a, b in zip(s, s[1:]):
            c2[(a, b)] += 1
    #: continuació: en quants contextos diferents apareix cada paraula com a segona
    cont = collections.Counter(b for (a, b) in c2)
    seguidors = collections.Counter(a for (a, b) in c2)            # N1+(a •)
    total_cont = sum(cont.values())
    vocab = set(c1) | set(unigrams) | {"<unk>"}
    #: unigrames de recaiguda: continuació per a les del corpus; massa mínima per a les del lèxic
    p_uni = {}
    massa_lexic = 1.0 / (total_cont + len(vocab))
    for w in vocab:
        p_uni[w] = (cont.get(w, 0) + 1) / (total_cont + len(vocab))
    # normalitza
    z = sum(p_uni.values())
    p_uni = {w: p / z for w, p in p_uni.items()}
    uni = {w: log10(p) for w, p in p_uni.items()}
    uni["<s>"] = -99.0
    #: bigrames i pes de recaiguda per context
    bi, backoff = {}, {}
    ctx_total = collections.Counter()
    for (a, b), n in c2.items():
        ctx_total[a] += n
    for (a, b), n in c2.items():
        p = max(n - D, 0) / ctx_total[a] + (D * seguidors[a] / ctx_total[a]) * p_uni[b]
        bi[(a, b)] = log10(p)
    for a in ctx_total:
        #: la massa que el context cedeix a la recaiguda, dividida per la massa d'unigrama que
        #: NO cobreixen els bigrames vistos (forma estàndard del back-off ARPA)
        lam = D * seguidors[a] / ctx_total[a]
        vistos = sum(p_uni[b] for (x, b) in c2 if x == a) if False else None
        backoff[a] = log10(lam)   # aproximació: interpolat ja inclou p_uni; el back-off
        #                           només s'aplica a parelles no vistes, i lam·p_uni(b) és just
        #                           el que la fórmula d'interpolació els dóna.
    for w in vocab:
        backoff.setdefault(w, 0.0)
    escriu_arpa(fora, uni, bi, backoff)
    return len(uni), len(bi)


if __name__ == "__main__":
    corpus_cami, uni_cami, fora = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(fora, exist_ok=True)
    corpus = list(llegeix_frases(corpus_cami))
    unigrams = [l.strip() for l in io.open(uni_cami, encoding="utf-8") if l.strip()]
    print(f"corpus: {len(corpus)} frases, {sum(len(t) for t in corpus)} tokens · lèxic: {len(unigrams)} formes")
    n = model_lexic(corpus, unigrams, os.path.join(fora, "lexic.arpa"))
    print(f"lexic.arpa: {n} unigrames")
    n1, n2 = model_bigram(corpus, unigrams, os.path.join(fora, "corpus_bi.arpa"))
    print(f"corpus_bi.arpa: {n1} unigrames, {n2} bigrames")
