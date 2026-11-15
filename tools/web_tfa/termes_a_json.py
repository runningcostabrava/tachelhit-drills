# -*- coding: utf-8 -*-
"""Els 59 termes lingüístics del glossari de l'autor (tamazightforall.com) → lèxic validat en
català, amb la forma llatina IRCAM que el nostre transliterador treu del tifinag. El català el poso
jo a partir de l'anglès i el castellà de l'autor: és terminologia lingüística estàndard, no hi ha
res a endevinar. Font i llicència al fitxer de sortida.

ÚS: termes_a_json.py <dades.json> <sortida.json>
"""
import io
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ARREL, "backend"))
os.environ["LEXICON_WARMUP"] = "0"
import transliteration as T   # noqa: E402

EN_CA = {
    "Borrowing": "manlleu", "Code-Switching": "alternança de codi", "Dialect Boundary": "frontera dialectal",
    "Dialect Continuum": "contínuum dialectal", "High (H) Variety": "varietat alta (H)", "Isogloss": "isoglossa",
    "Low (L) Variety": "varietat baixa (L)", "Mutual Intelligibility": "intel·ligibilitat mútua",
    "Covert Prestige": "prestigi encobert", "Overt Prestige": "prestigi manifest", "Standardization": "estandardització",
    "Phonetics": "fonètica", "Spirantization": "espirantització", "Morphological Root": "arrel morfològica",
    "Suffix": "sufix", "Neologism": "neologisme", "Prestige": "prestigi", "Morpheme": "morfema",
    "Semantic Extension": "extensió semàntica", "Alphabet": "alfabet", "Language Family": "família lingüística",
    "Dialectology": "dialectologia", "Diglossia": "diglòssia", "Phoneme": "fonema", "Allophone": "al·lòfon",
    "Lexicology": "lexicologia", "Prefix": "prefix", "Pragmatics": "pragmàtica", "Etymology": "etimologia",
    "Applied Linguistics": "lingüística aplicada", "Pedagogy": "pedagogia", "Linguistics": "lingüística",
    "Phonology": "fonologia", "Morphology": "morfologia", "Syntax": "sintaxi", "Semantics": "semàntica",
    "Sociolinguistics": "sociolingüística", "Dialect": "dialecte", "Language": "llengua", "Grammar": "gramàtica",
    "Lexicon": "lèxic", "Vocabulary": "vocabulari", "Word": "paraula", "Sentence": "frase", "Noun": "nom",
    "Verb": "verb", "Adjective": "adjectiu", "Pronoun": "pronom", "Preposition": "preposició", "Particle": "partícula",
    "Root": "arrel", "Stem": "radical", "Affix": "afix", "Infix": "infix", "Gender": "gènere", "Number": "nombre",
    "Plural": "plural", "Singular": "singular", "Masculine": "masculí", "Feminine": "femení",
    "Construct State": "estat d'annexió", "Free State": "estat lliure", "Annexed State": "estat d'annexió",
    "Aorist": "aorist", "Perfective": "perfectiu", "Imperfective": "imperfectiu", "Negative": "negatiu",
    "Translation": "traducció", "Standard Language": "llengua estàndard", "Mother Tongue": "llengua materna",
    "Script": "escriptura", "Letter": "lletra", "Sound": "so", "Consonant": "consonant", "Vowel": "vocal",
    "Emphatic": "emfàtic", "Labialization": "labialització", "Gemination": "geminació", "Assimilation": "assimilació",
    "Metathesis": "metàtesi", "Loanword": "manlleu", "Calque": "calc", "Corpus": "corpus", "Terminology": "terminologia",
    "Orthography": "ortografia", "Transcription": "transcripció", "Transliteration": "transliteració",
    "Variety": "varietat", "Register": "registre", "Bilingualism": "bilingüisme", "Multilingualism": "multilingüisme",
    "Language Planning": "planificació lingüística", "Language Policy": "política lingüística",
    "Language Death": "mort d'una llengua", "Language Shift": "substitució lingüística", "Revitalization": "revitalització",
    "Speech Community": "comunitat de parla", "Idiolect": "idiolecte", "Sociolect": "sociolecte", "Koine": "koiné",
    "Pidgin": "pidgin", "Creole": "crioll", "Lingua Franca": "llengua franca", "Grammaticalization": "gramaticalització",
    "Deep Structure": "estructura profunda", "Substratum Influence": "influència del substrat", "Syllable": "síl·laba",
    "Synonymy": "sinonímia", "Writing System": "sistema d'escriptura", "Grapheme / Letter": "grafema, lletra",
    "Orthographic Codification": "codificació ortogràfica", "Proto-language": "protollengua",
    "Language Acquisition": "adquisició del llenguatge",
}


def llati(tif):
    try:
        return (T.to_forms(tif) or {}).get("clean_latin") or ""
    except Exception:
        return ""


if __name__ == "__main__":
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    fora, sense = {}, []
    for t in d.get("linguisticTerms", []):
        tif = re.sub(r"\s*\([A-Z]\)\s*$", "", t.get("amazigh") or "")
        lat = re.sub(r"[^a-zɣɛḍṭẓṣṛḥʷ ]", "", llati(tif).lower()).strip()
        en = (t.get("english") or "").strip()
        ca = EN_CA.get(en) or EN_CA.get(re.sub(r"\s*\([A-Z]\)", "", en).strip())
        if not lat or not ca:
            sense.append((lat, en, t.get("spanish")))
            continue
        fora[lat] = {"ca": ca, "en": en, "es": t.get("spanish") or "", "ar": t.get("arabic") or "",
                     "tifinag": tif, "arrel": t.get("root") or "", "mena": t.get("type") or ""}
    out = {"_font": "Glossari de termes lingüístics de tamazightforall.com (Naceur Jabouja Ulmer), llegit el 15-11-2026; "
                    "terminologia de l'IRCAM. Ús: validació de glosses; el web diu «tots els drets reservats, ús personal "
                    "no comercial». Català posat per nosaltres a partir de l'anglès i el castellà de l'autor.",
           "termes": fora}
    json.dump(out, io.open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(fora), "termes amb català ·", len(sense), "sense:", sense[:12])
    print("d'un sol token:", sum(1 for k in fora if " " not in k), "· de més d'un:", sum(1 for k in fora if " " in k))
