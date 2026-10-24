"""
Berber (Tachelhit / Tamazight) transliteration — "one input, several faces".

Contributors type the way their thumbs already know: the demotic phone/chat
Latin ("Arabizi"-style) — 3=ɛ, 7=ḥ, 9=q, gh=ɣ, kh=x, ch=š, ou=u … We ALSO
accept academic Berber Latin (ḥ ɛ ɣ ḍ ṭ ṣ ṛ ẓ š, and c=š) as-is.

From that single parse we derive, in the background, three faces that are
never forced on the user and never overwrite their gold input:

  - clean_latin : canonical academic Berber-Latin  (searchable, citable)
  - tifinagh    : Neo-Tifinagh / IRCAM  (the identity script — for display/pride)
  - key         : an aggressive phonemic key for search / dedup / pronunciation
                  scoring (de-geminated, schwa-stripped, script-independent)

Deterministic, no external service. Best-effort only: Berber orthography is
genuinely underdetermined (schwa, gemination, labialization, spirantization),
so the generated forms are SUGGESTIONS a human confirms — not gold.
"""

# Demotic/academic spelling -> internal phoneme symbol (clean Berber-Latin).
# Longest keys are matched first, so digraphs beat single letters.
_DEMOTIC = {
    # labialized (explicit)
    "gw": "gʷ", "kw": "kʷ", "qw": "qʷ",
    # digraphs (demotic + some spirantized conventions)
    "gh": "ɣ", "kh": "x", "ch": "š", "sh": "š", "ou": "u",
    "dj": "j", "dh": "ḍ",
    # «th» NO hi és, i té història. Hi era com a dígraf (la t espirantitzada que els cabilencs
    # escriuen «th»), i a la nostra llengua es menjava una seqüència freqüentíssima: el prefix
    # de 3a persona femenina «t-» davant d'arrels que comencen per h-. «thnna» («va bé») sortia
    # «tnna», «thlla» sortia «tlla», i «thanut» («la botiga») sortia «tanut» — a la pantalla, a
    # la tifinagh I a `clean_latin`, que és la forma que el mòdul promet com a citable.
    #
    # Comptat al corpus sencer (3.401 frases): «th» hi surt 75 vegades i NI UNA no és el dígraf
    # —thanut (13), thla (6), thnna (3), thdar, buthanut…—, mentre que gh (936), sh (569), ch
    # (174), kh (141) i ou (21) sí que són com la gent escriu. Per això cau aquest i es queden
    # els altres. Ho va trobar un auditor llegint una frase nostra que el capítol justificava
    # dient «diu tna», que no és cap paraula.
    # Arabic chat-alphabet numerals
    "3": "ɛ", "7": "ḥ", "9": "q", "5": "x", "8": "ɣ",
    # academic Berber-Latin pass-through
    "ḥ": "ḥ", "ɛ": "ɛ", "ɣ": "ɣ", "ḍ": "ḍ", "ṭ": "ṭ", "ṣ": "ṣ",
    "ṛ": "ṛ", "ẓ": "ẓ", "š": "š", "ž": "j", "ʒ": "j", "č": "š",
    # Les lletres GREGUES que tothom escriu en comptes de les llatines, i la ġ de molts
    # reculls. Semblen iguals a la pantalla i no ho són (γ U+03B3 ≠ ɣ U+0263), i el que el mapa
    # no coneixia, el transliterador el llençava en silenci: «riγ» sortia ⵔⵉ («ri») i «aγrum»
    # «pa» sortia ⴰⵔⵓⵎ, que ja és una altra paraula. Ho va trobar un auditor comptant 59 línies
    # del capítol 4 amb una consonant de menys.
    "γ": "ɣ", "ε": "ɛ", "ġ": "ɣ", "ε̣": "ɛ", "Γ": "ɣ", "Ε": "ɛ", "Ġ": "ɣ",
    # single letters (Berber-Latin conventions: c=š, e=schwa, o->u, no p/v)
    "a": "a", "b": "b", "c": "š", "d": "d", "e": "ə", "f": "f",
    "g": "g", "h": "h", "i": "i", "j": "j", "k": "k", "l": "l",
    "m": "m", "n": "n", "o": "u", "p": "b", "q": "q", "r": "r",
    "s": "s", "t": "t", "u": "u", "v": "f", "w": "w", "x": "x",
    "y": "y", "z": "z",
}
# phoneme -> Neo-Tifinagh (IRCAM, Unicode Tifinagh block)
_TIFINAGH = {
    "a": "ⴰ", "b": "ⴱ", "g": "ⴳ", "gʷ": "ⴳⵯ", "d": "ⴷ", "ḍ": "ⴹ",
    "ə": "ⴻ", "f": "ⴼ", "k": "ⴽ", "kʷ": "ⴽⵯ", "h": "ⵀ", "ḥ": "ⵃ",
    "ɛ": "ⵄ", "x": "ⵅ", "q": "ⵇ", "qʷ": "ⵇⵯ", "i": "ⵉ", "j": "ⵊ",
    "l": "ⵍ", "m": "ⵎ", "n": "ⵏ", "u": "ⵓ", "r": "ⵔ", "ṛ": "ⵕ",
    "ɣ": "ⵖ", "s": "ⵙ", "ṣ": "ⵚ", "š": "ⵛ", "t": "ⵜ", "ṭ": "ⵟ",
    "w": "ⵡ", "y": "ⵢ", "z": "ⵣ", "ẓ": "ⵥ",
}

# phoneme -> clean academic Latin. Schwa is 'e'; labialization is written with
# an ASCII 'w' (gw/kw/qw) rather than the superscript ʷ, so clean_latin re-parses
# losslessly back to the same phonemes/key (the input map knows gw/kw/qw).
_CLEAN = {"ə": "e", "gʷ": "gw", "kʷ": "kw", "qʷ": "qw"}

# Accept Tifinagh as input too, so the phonemic key is script-INDEPENDENT
# (ASR may emit either script; the gold field is often Tifinagh). Longest-match
# first, so labialized digraphs (ⴳⵯ) beat their base letter (ⴳ).
_INPUT = dict(_DEMOTIC)
for _ph, _tif in _TIFINAGH.items():
    _INPUT.setdefault(_tif, _ph)
_KEYS_BY_LEN = sorted(_INPUT.keys(), key=len, reverse=True)


def _tokenize(text_lower):
    """Greedy longest-match over the demotic table. Returns [(kind, value)]
    where kind is 'phon' (value is a phoneme symbol) or 'other' (raw char)."""
    out, i, s = [], 0, text_lower
    while i < len(s):
        for k in _KEYS_BY_LEN:
            if s.startswith(k, i):
                out.append(("phon", _INPUT[k]))
                i += len(k)
                break
        else:
            out.append(("other", s[i]))
            i += 1
    return out


def to_forms(raw: str) -> dict:
    """Parse demotic/academic Berber-Latin into its phoneme faces.

    Returns {input, clean_latin, tifinagh, key}. Idempotent-ish: feeding
    clean_latin back in reproduces the same tifinagh/key.
    """
    raw = raw or ""
    toks = _tokenize(raw.lower())
    clean, tif, key = [], [], []
    prev = None
    for kind, val in toks:
        if kind == "other":
            clean.append(val)
            if val.isspace():
                tif.append(" ")
                key.append(" ")
            # non-space punctuation/digits: keep in clean, drop from tif/key
            prev = None
            continue
        ph = val
        clean.append(_CLEAN.get(ph, ph))
        tif.append(_TIFINAGH.get(ph, ""))
        # key: skip schwa, collapse gemination
        if ph != "ə" and ph != prev:
            key.append(ph)
        prev = ph
    # collapse runs of spaces in the key
    key_str = " ".join("".join(key).split())
    return {
        "input": raw,
        "clean_latin": "".join(clean).strip(),
        "tifinagh": "".join(tif).strip(),
        "key": key_str,
    }


def phonemic_key(raw: str) -> str:
    """Just the matching key — for search / dedup / pronunciation scoring."""
    return to_forms(raw)["key"]
