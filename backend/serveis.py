"""Quina màquina fa cada feina, i si ara mateix contesta (#295).

L'estratègia està escrita a `docs/SERVEIS_IA.md`; això és la mateixa taula feta codi, perquè es
pugui **llegir des de l'app** en comptes de descobrir-ho cada vegada que un servei cau. El
24-10-2026, en una sola jornada, se'n van quedar tres sense servei alhora: Gemini amb «402
prepayment credits are depleted», la quota de FLUX esgotada i el traductor gratuït de Google
tallant per excés de peticions.

Dues regles de la casa manen aquí, i per això cada feina les porta escrites al costat:

  - **el que surt d'una màquina va a `*_suggested`** i ho confirma una persona;
  - **cap servei no és l'únic**: cada feina ha de tenir un segon i, si no en té, ho ha de **dir**
    en comptes de callar.

El que aquest mòdul NO fa és decidir res: no tria el proveïdor ni l'encamina. Diu qui hauria de
fer cada feina, en quin ordre, i què contesta cadascú ara mateix.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

#: Les menes de proveïdor, i com se sap si contesten.
#:   space     un Space de Hugging Face (gratuït, s'adorm): es mira amb `/health/spaces`
#:   gemini    el Gemini de Google: hi ha clau? queda pressupost?
#:   deepseek  DeepSeek: hi ha clau?
#:   persona   ningú automàticament: ho fa qui parla la llengua
FEINES: List[Dict] = [
    {
        "id": "transcriure",
        "titol": "Sentir una gravació i escriure el que diu",
        "explica": "Només ho pot fer un model de VEU. DeepSeek, Gemini i Claude són models de "
                   "text: no senten res. No és una qüestió de qualitat sinó de què entra per "
                   "l'entrada.",
        "regla": "El que en surt va a «suggerit» amb la seva certesa, i ho confirma una persona.",
        "qui": [
            {"nom": "El nostre Space (NeMo CTC)", "mena": "space", "clau": "asr", "paper": "primer"},
            {"nom": "TutlaytAI/wav2vec2-berber", "mena": "space", "clau": None,
             "paper": "per contrastar, no per substituir: que dos models independents coincideixin "
                      "val més que la certesa d'un de sol"},
        ],
    },
    {
        "id": "traduir-amazic",
        "titol": "Dir què vol dir una frase amaziga",
        "explica": "Sempre amb les fonts al davant: les entrades del diccionari de les seves "
                   "paraules i les frases de la nostra biblioteca que les porten. Sense fonts, el "
                   "model tradueix «mnckk a tskar zzit?» per «com fas oli?» quan vol dir «quant "
                   "val l'oli?»; amb fonts, encerta i a més avisa del que no sap.",
        "regla": "Una traducció de màquina no és mai el text d'un parlant: va a «suggerit».",
        "qui": [
            {"nom": "DeepSeek", "mena": "deepseek", "paper": "primer"},
            {"nom": "Gemini", "mena": "gemini", "paper": "segon"},
        ],
    },
    {
        "id": "traduir-arab",
        "titol": "Traduir de l'àrab al català, a milers",
        "explica": "Una crida per lot. El traductor gratuït de Google talla a la tercera petició.",
        "regla": "El mateix: va a «suggerit».",
        "qui": [
            {"nom": "DeepSeek", "mena": "deepseek", "paper": "primer"},
            {"nom": "El nostre Space de traducció (NLLB)", "mena": "space", "clau": "translation",
             "paper": "segon"},
        ],
    },
    {
        "id": "escriure",
        "titol": "Escriure les lliçons i les explicacions",
        "explica": "El text del curs: les unitats de gramàtica, el paraula per paraula, les notes. "
                   "El que una màquina no fa mai sola és **escriure amazic**.",
        "regla": "Una lliçó escrita per una màquina la pot corregir qualsevol, i la correcció mana.",
        "qui": [
            {"nom": "DeepSeek", "mena": "deepseek", "paper": "primer"},
            {"nom": "Gemini", "mena": "gemini", "paper": "segon"},
        ],
    },
    {
        "id": "dibuixar",
        "titol": "Dibuixar la imatge d'una frase",
        "explica": "Una paraula només s'il·lustra amb un dibuix nostre: una foto trobada a la "
                   "xarxa il·lustra una paraula per casualitat o no la il·lustra gens.",
        "regla": "El dibuix és nostre i es pot canviar; mai una imatge de qui no ens l'ha donada.",
        "qui": [
            {"nom": "Gemini (imatge)", "mena": "gemini", "paper": "primer"},
            {"nom": "Spaces de FLUX", "mena": "space", "clau": "image", "paper": "segon"},
        ],
    },
    {
        "id": "escriure-amazic",
        "titol": "Escriure amazic nou",
        "explica": "Posar paraules a la llengua. Això no ho fa cap màquina d'aquesta app, i no és "
                   "per prudència: una biblioteca de llengua que es deixi omplir per una màquina "
                   "no documenta res.",
        "regla": "Ho fa qui parla la llengua, amb el seu nom i el seu poble.",
        "qui": [{"nom": "Una persona", "mena": "persona", "paper": "sempre"}],
    },
]

#: Com es diu cada estat a la pantalla. El que no se sap no s'inventa.
ESTATS = {
    "viu": "contesta",
    "despertant": "s'està despertant",
    "aturat": "no contesta",
    "sense_clau": "sense clau configurada",
    "sense_pressupost": "ha arribat al pressupost del mes",
    "privat": "és privat: des de fora no es pot mirar",
    "no_configurat": "no està configurat",
    "persona": "ho fa una persona",
    # Dues coses que no són «contesta» i que abans es deien com si ho fossin:
    "no_ho_sabem": "no s'ha mirat",
    "amb_clau": "hi ha clau i pressupost (si contesta, no se sap fins que se li truca)",
}

#: Del que diu `/health/spaces` al que diem nosaltres.
_DE_SPACE = {"up": "viu", "waking": "despertant", "down": "aturat",
             "unset": "no_configurat", "private_or_missing": "privat"}


def _estat_proveidor(p: Dict, spaces: Dict, gemini_ok: bool, gemini_clau: bool,
                     deepseek_clau: bool) -> Dict:
    mena = p.get("mena")
    if mena == "persona":
        return {"estat": "persona"}
    if mena == "space":
        clau = p.get("clau")
        if not clau:
            return {"estat": "no_configurat"}
        diu = (spaces or {}).get(clau)
        # No s'ha mirat no és el mateix que no contestar. Amb `prova=0` no es truca a cap Space, i
        # dir-ne «no contesta» seria inventar-se una mesura que no s'ha fet.
        if not diu:
            return {"estat": "no_ho_sabem"}
        return {"estat": _DE_SPACE.get(diu.get("state"), "aturat")}
    # D'un servei de pagament només sabem si tenim clau i si ens queda pressupost NOSTRE. Si a ell
    # li queda crèdit, no se sap fins que se li truca: el 24-10-2026 Gemini tenia clau, tenia
    # pressupost i contestava «402 prepayment credits are depleted». Per això aquí no hi diu
    # «contesta».
    if mena == "gemini":
        if not gemini_clau:
            return {"estat": "sense_clau"}
        return {"estat": "amb_clau" if gemini_ok else "sense_pressupost"}
    if mena == "deepseek":
        return {"estat": "amb_clau" if deepseek_clau else "sense_clau"}
    return {"estat": "no_configurat"}


def quina_feina_fa_qui(spaces: Optional[Dict] = None, gemini_ok: bool = False,
                       gemini_clau: bool = False, deepseek_clau: Optional[bool] = None) -> Dict:
    """La taula sencera amb l'estat d'ara.

    `spaces` és el que torna `/health/spaces`; si no es dona, els Spaces surten com a
    desconeguts en comptes de fer veure que estan bé.
    """
    if deepseek_clau is None:
        deepseek_clau = bool(os.getenv("DEEPSEEK_API_KEY"))
    feines = []
    for f in FEINES:
        qui = []
        for p in f["qui"]:
            estat = _estat_proveidor(p, spaces or {}, gemini_ok, gemini_clau, bool(deepseek_clau))
            qui.append({**{k: v for k, v in p.items() if k != "clau"}, **estat,
                        "diu": ESTATS.get(estat["estat"], estat["estat"])})
        # Una feina està aturada quan cap dels seus no contesta. Dir-ho és la regla 5: cap
        # servei no és l'únic, i si no en queda cap s'ha de veure, no callar.
        # Una feina funciona si algú la pot fer: una veu viva, una persona, o un servei de
        # pagament amb clau i pressupost. El que no s'ha mirat no compta ni a favor ni en contra.
        viu = any(p["estat"] in ("viu", "persona", "amb_clau") for p in qui)
        feines.append({**{k: v for k, v in f.items() if k != "qui"}, "qui": qui, "funciona": viu})
    return {"feines": feines, "aturades": [f["id"] for f in feines if not f["funciona"]],
            # El que no es pot saber, es diu. D'un proveïdor de pagament sabem si tenim clau i si
            # ens queda pressupost nostre; si a ELL li queda crèdit no se sap fins que se li
            # truca —el 24-10-2026 Gemini contestava «402 prepayment credits are depleted».
            "avis": "D'un servei de pagament només sabem si tenim clau i si ens queda pressupost. "
                    "Si al proveïdor li queda crèdit, no se sap fins que se li truca.",
            "regles": [
                "El que surt d'una màquina va a «suggerit». Ho confirma una persona.",
                "Les fonts guanyen la memòria del model.",
                "Que digui què no sap.",
                "Dos models que coincideixen valen més que un de segur.",
                "Cap servei no és l'únic: si una feina es queda sense ningú, ho diu.",
                "Una certesa alta no vol dir correcte.",
            ]}
