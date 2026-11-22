# -*- coding: utf-8 -*-
"""Un lector d'ARPA amb la interfície de KenLM, perquè pyctcdecode pugui fer servir el lèxic.

**Per què existeix.** pyctcdecode només mira la llista de paraules (`unigrams`) si hi ha un
model KenLM carregat; sense un fitxer `.arpa` el feix ignora el lèxic del tot. I KenLM no
compila ni al Python 3.13 de Kaggle ni al 3.14 d'aquesta màquina: demana un compilador de C++.
Aquest mòdul fa la feina en Python pur, amb l'ARPA que escriu `fes_arpa.py`.

S'endolla apedaçant el mòdul abans de construir el descodificador:

    import pyctcdecode.language_model as plm, pyctcdecode.decoder as pdec
    import arpa_lm
    plm.kenlm = arpa_lm
    pdec.kenlm = arpa_lm
    from pyctcdecode import build_ctcdecoder

**El que pyctcdecode demana** (comprovat al seu codi): `Model(camí)` amb `.order`, `.path`,
`BaseScore(estat_entrada, paraula, estat_sortida)`, `BeginSentenceWrite(estat)` i
`NullContextWrite(estat)`; i `State()`, que per a ell és una capsa opaca.

**El càlcul** és el d'un model amb descompte i backoff, en log10, com el que escriu `fes_arpa`:

    P(w | ctx) = p(ctx, w)                    si el bigrama hi és
               = backoff(ctx) + p(w)          si no hi és
               = backoff(ctx) + p(<unk>)      si la paraula tampoc no hi és

Aquest fitxer vivia **només al dataset de Kaggle**, i per això l'únic experiment que ha mesurat
el guany del model de llengua (H3: WER 0,712 → 0,640) no es podia repetir des del repositori.
"""
import io
import os

__all__ = ["Model", "State", "LanguageModel"]

NEG_INF = -99.0          #: el que l'ARPA escriu per «això no passa mai»


class State:
    """El context. Per a pyctcdecode és opac; aquí hi guarda les últimes paraules."""

    __slots__ = ("words",)

    def __init__(self):
        self.words = ()

    def __repr__(self):                           # pragma: no cover - només per mirar
        return f"State({' '.join(self.words) or '-'})"


class Model:
    """Un ARPA llegit a memòria, amb la interfície mínima de `kenlm.Model`."""

    def __init__(self, path):
        self.path = path
        self.order = 1
        #: {paraula: (log10 p, log10 backoff)} i {(ctx, paraula): log10 p}
        self._uni = {}
        self._bi = {}
        self._llegeix(path)

    def _llegeix(self, path):
        if not os.path.exists(path):
            raise OSError(f"no hi ha cap ARPA a {path}")
        n = 0
        with io.open(path, encoding="utf-8") as f:
            for linia in f:
                linia = linia.strip()
                if not linia:
                    continue
                if linia.startswith("\\") and linia.endswith("-grams:"):
                    n = int(linia[1:].split("-")[0])
                    self.order = max(self.order, n)
                    continue
                if linia.startswith("\\") or linia.startswith("ngram "):
                    continue
                if n == 0:
                    continue
                trossos = linia.split("\t")
                if len(trossos) < 2:
                    continue
                p = float(trossos[0])
                #: l'ARPA estandard posa les paraules de l'n-grama en UN camp separades per
                #: espais (`-2.41<tab>de la`), pero n'hi ha que les separen amb tabuladors.
                #: Es llegeixen les dues formes: el backoff nomes hi es si, tretes les n
                #: paraules, queda un camp mes i es un numero.
                resta = " ".join(trossos[1:]).split()
                bo, paraules = 0.0, resta
                if len(resta) == n + 1:
                    try:
                        bo, paraules = float(resta[-1]), resta[:-1]
                    except ValueError:
                        pass
                if n == 1 and len(paraules) == 1:
                    self._uni[paraules[0]] = (p, bo)
                elif n == 2 and len(paraules) == 2:
                    self._bi[(paraules[0], paraules[1])] = p
        if not self._uni:
            raise ValueError(f"{path}: cap unigrama; això no és un ARPA que sapiguem llegir")

    #: --- la interfície que pyctcdecode crida ---

    def BeginSentenceWrite(self, state):          # noqa: N802 - el nom és de KenLM
        state.words = ("<s>",)
        return state

    def NullContextWrite(self, state):            # noqa: N802
        state.words = ()
        return state

    def BaseScore(self, in_state, word, out_state):   # noqa: N802
        """log10 P(word | context), i escriu el context nou a `out_state`."""
        ctx = in_state.words[-1] if in_state is not None and in_state.words else None
        punt = self._puntua(ctx, word)
        if out_state is not None:
            #: el context que es guarda és la paraula tal com s'ha vist, retallat a l'ordre
            out_state.words = ((word,) if self.order > 1 else ())
        return punt

    def _puntua(self, ctx, word):
        if self.order > 1 and ctx is not None:
            p = self._bi.get((ctx, word))
            if p is not None:
                return p
            #: no hi és el bigrama: es paga el backoff del context i es tira d'unigrama
            backoff = self._uni.get(ctx, (NEG_INF, 0.0))[1]
            return backoff + self._unigrama(word)
        return self._unigrama(word)

    def _unigrama(self, word):
        p = self._uni.get(word)
        if p is not None:
            return p[0]
        desconeguda = self._uni.get("<unk>")
        return desconeguda[0] if desconeguda else NEG_INF

    #: --- comoditats per a les proves i per mirar-ho ---

    def score(self, frase, bos=True, eos=False):
        """log10 P d'una frase sencera, com `kenlm.Model.score`."""
        estat, seguent = State(), State()
        if bos:
            self.BeginSentenceWrite(estat)
        else:
            self.NullContextWrite(estat)
        total = 0.0
        for w in frase.split():
            total += self.BaseScore(estat, w, seguent)
            estat, seguent = seguent, State()
        if eos:
            total += self.BaseScore(estat, "</s>", seguent)
        return total

    def __contains__(self, word):
        return word in self._uni

    def __len__(self):
        return len(self._uni)

    def __repr__(self):                           # pragma: no cover
        return (f"arpa_lm.Model({os.path.basename(self.path)}: ordre {self.order}, "
                f"{len(self._uni)} unigrames, {len(self._bi)} bigrames)")


#: pyctcdecode mira `kenlm.LanguageModel` a algunes versions
LanguageModel = Model
