"""El tifinag cap a lletres llatines, per a l'alineador i per a qui l'ha de comptar.

**Per que es un modul i no una funcio copiada.** L'alineador salta els talls amb menys de 3
caracters de text (`len(roman(tifinag)) >= 3`), i el muntador de l'experiment ha de saber
**quants** talls d'un capitol son alineables per decidir si el capitol esta acabat. Si cada un
porta la seva copia de la regla, les dues se separen i el muntador descarta capitols acabats:
amb la regla simple «3 caracters de text» en comptes d'aquesta, 51 talls de 19.547 (el 0,26 %)
canvien de banda, i el llindar del muntador es del 2 %.

Importar-ho de `alinea_mms_fa_tot.py` no serveix: aquell modul carrega torch i torchaudio en
importar-se, i el muntador no pot pagar 1 GB per una taula de 35 lletres.

**Que no es.** No es el transliterador del projecte (`backend/translit.py`) ni el `rica()` de
`tools/lm/kaggle/alineacio_forcada_snrt.py`, que casa amb el vocabulari concret de l'adaptador
`shi` de MMS-1b-all. Aquest nomes ha de donar lletres llatines que el tokenitzador del
`torchaudio MMS_FA` reconegui, i per aixo pot ser mes brut: el que importa es que **sigui el
mateix** per a qui alinea i per a qui compta.
"""
import unicodedata

#: U+2D30-U+2D7F. Atencio: U+2B30 son fletxes, no tifinag.
TIFI = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e",
        "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x",
        "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
        "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
        "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z",
        "ⵥ": "z", "ⵯ": "w", "ⵒ": "p", "ⴶ": "g", "ⵌ": "j"}


def roman(t):
    """El text cap a lletres llatines minuscules separades per un sol espai.

    Les lletres tifinag passen per `TIFI`; les llatines amb accent o cedella es descomponen i
    es queden amb la base; la resta (puntuacio, xifres, signes) cau.
    """
    fora = []
    for c in t or "":
        if c in TIFI:
            fora.append(TIFI[c])
        elif c.isspace():
            fora.append(" ")
        elif c.isascii() and c.isalpha():
            fora.append(c.lower())
        else:
            d = unicodedata.normalize("NFD", c)
            b = "".join(x for x in d if not unicodedata.combining(x))
            if b.isascii() and b.isalpha():
                fora.append(b.lower())
    return " ".join("".join(fora).split())


#: la regla de l'alineador, en un sol lloc: per sota d'aixo no hi ha text per alinear
MINIM = 3


def prou_text(t):
    """Si l'alineador alinearia aquest text o el saltaria."""
    return len(roman(t)) >= MINIM


#: el tifinag ha d'arribar a lletres: «azul tamaziġt» en tifinag son 13 lletres i un espai
assert roman("ⴰⵣⵓⵍ ⵜⴰⵎⴰⵣⵉⵖⵜ") == \
    "azul tamazigt", "el tifinag no arriba a lletres llatines"
