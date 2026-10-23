"""El Mètode: deu capítols que porten algú de zero a dir alguna cosa al mercat.

Això és el catàleg, i és tot el que es pren d'un manual publicat: **el pla**. De cada capítol,
quatre caselles escrites per nosaltres llegint-lo — quines funcions comunicatives ensenya, quina
gramàtica demana, de quins camps de vocabulari va, i qui hi parla. El recorregut d'un curs és un
fet sobre com s'ensenya una llengua; el text d'un llibre és d'algú.

Ni una frase, ni un diàleg, ni una explicació, ni una entrada de lèxic surten del llibre. Tot el
que es veurà en un capítol surt de la nostra biblioteca i del compendi d'amazic.cat, igual que el
curs de gramàtica, i el que un capítol demana i no tenim es converteix en una frase catalana
sense amazic que va a demanar veu (ADR 0003, docs/CREDITS.md §2b).

El pla seguit és:
    Abdallah El Mountassir, «Méthode de Tachelhit. Langue amazighe (berbère) du sud du Maroc»,
    L'Asiathèque, Collection Langues & Mondes, París, 2009.
    Ed. italiana: Università degli Studi di Napoli «L'Orientale», 2017.

Un avís que no s'ha de perdre: aquell manual és **tachelhit del Souss** i el gruix de les nostres
veus és de l'**Atles central**. Per això un capítol pot ensenyar la mateixa cosa en dues columnes,
i per això cada frase ha de dir de quina varietat és. Barrejar-les sense dir-ho va contra
docs/SCOPE.md.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import grammar
import topics as topics_catalog

# La citació, que va al peu de cada capítol i enlloc més amagada.
SOURCE = {
    "author": "Abdallah El Mountassir",
    "title": "Méthode de Tachelhit. Langue amazighe (berbère) du sud du Maroc",
    "publisher": "L'Asiathèque — Maison des langues du monde",
    "place": "París",
    "year": 2009,
    "italian": ("Metodo di tachelhit. Lingua amazigh (berbera) del sud del Marocco, "
                "Università degli Studi di Napoli «L'Orientale», 2017"),
    # El que es llegeix a la pantalla és «Basat en…», i res més: la citació diu d'on ve el
    # material, no quins permisos tenim. Què ens deixa fer l'autor és cosa nostra i del registre
    # (ADR 0004), no de la targeta d'un capítol.
    "based_on": "Basat en",
    "took": "les explicacions, l'estructura, els diàlegs i el lèxic, adaptats a la nostra varietat",
    "did_not_take": "les veus: cada frase la diu una persona de debò que el projecte coneix",
}

# `grammar` són slugs de grammar.UNITS; `topics` són slugs de topics.TOPICS. Els dos es
# comproven a l'arrencada (check()) perquè una errada d'escriptura aquí dins es veuria com un
# capítol misteriosament buit en comptes de com el que és.
CHAPTERS: List[Dict] = [
    {
        "n": 1,
        "slug": "sons",
        "name": None,
        "title": "Els sons i com s'escriuen",
        "about": "Sentir la diferència entre els sons que el català no té, i saber escriure'ls.",
        "functions": [
            "distingir les consonants tenses de les simples",
            "sentir les emfàtiques (ḍ, ṭ, ṣ, ẓ) i dir-les",
            "reconèixer ɣ, x, q, ḥ, ɛ i les labiovelars",
            "llegir i escriure en tifinag i en llatí",
        ],
        "grammar": ["sons-i-escriptura"],
        # Cap frase porta la unitat de fonètica —no és un punt de gramàtica que es vegi a la
        # frase— així que aquest capítol s'omple pel tema: l'alfabet, i les paraules soltes on
        # un so es pot sentir sol.
        "topics": ["alfabet", "vocabulari"],
        "roles": [],
    },
    {
        "n": 2,
        "slug": "salutacions",
        "name": "Timinsiwin",
        "title": "Saludar-se i conèixer-se",
        "about": "Les primeres coses que es diuen: hola, com estàs, com et dius, d'on ets.",
        "functions": [
            "saludar i acomiadar-se segons l'hora",
            "preguntar com està algú i respondre",
            "dir com et dius i preguntar-ho",
            "donar les gràcies i desitjar sort",
        ],
        "grammar": ["formules", "pronoms-personals"],
        "topics": ["salutacions", "familia"],
        "roles": ["qui arriba", "qui rep"],
    },
    {
        "n": 3,
        "slug": "el-cami",
        "name": "Aɣaras n-Tfrawt",
        "title": "El camí: on són les coses",
        "about": "Dir on ets, on va una cosa, i preguntar per un lloc.",
        "functions": [
            "preguntar on és un lloc",
            "dir que una cosa és a un lloc",
            "situar a la dreta i a l'esquerra",
            "dir de quin poble és una cosa o una persona",
            "dir on treballa algú",
        ],
        "grammar": ["estat-annexio", "preposicions", "ser-tenir", "preguntes"],
        "topics": ["viatge", "feina", "casa"],
        "roles": ["qui pregunta", "qui coneix el lloc"],
    },
    {
        "n": 4,
        "slug": "la-botiga",
        "name": "Dar butḥanut",
        "title": "A la botiga",
        "about": "Demanar una cosa, saber què val, dir-ne quanta en vols i pagar.",
        "functions": [
            "preguntar si tenen una cosa",
            "dir què vols",
            "preguntar el preu",
            "dir quanta quantitat en vols",
            "donar una cosa a algú",
        ],
        "grammar": ["noms-genere-nombre", "clitics-objecte", "numerals", "ser-tenir"],
        "topics": ["menjar", "mercat", "numeros"],
        "roles": ["qui compra", "qui ven"],
    },
    {
        "n": 5,
        "slug": "que-fas",
        "name": "Ma tskart?",
        "title": "Què fas",
        "about": "Parlar del que fas cada dia i del que has fet, i de qui és cada cosa.",
        "functions": [
            "preguntar què fa algú",
            "dir el que fas habitualment",
            "dir el que has fet",
            "dir de qui és una cosa",
            "dir que no fas una cosa",
        ],
        "grammar": ["imperfectiu-habitual", "perfectiu", "possessius", "negacio"],
        "topics": ["feina", "casa", "temps-dies"],
        "roles": ["qui pregunta", "qui explica"],
    },
    {
        "n": 6,
        "slug": "el-mercat",
        "name": "Bulxʷḍrt",
        "title": "Al mercat: això i allò",
        "about": "Assenyalar el que vols, dir com és, i dir que no en vols cap.",
        "functions": [
            "assenyalar una cosa aquí i una cosa allà",
            "dir «aquí tens»",
            "preguntar com és una cosa i dir-ho",
            "dir els colors",
            "dir que no n'hi ha cap",
        ],
        "grammar": ["demostratius", "negacio", "relatiu-participi", "adjectius-qualitat"],
        "topics": ["menjar", "mercat", "roba-colors"],
        "roles": ["qui compra", "qui para la parada"],
    },
    {
        "n": 7,
        "slug": "qui-ets",
        "name": "Mani trit?",
        "title": "Qui ets i on vas",
        "about": "Dir qui ets, quants anys tens, i el que faràs.",
        "functions": [
            "preguntar el nom i l'edat",
            "dir on vas",
            "dir el que faràs",
            "dir quan passarà una cosa",
            "dir que no ho faràs",
        ],
        "grammar": ["aorist-ad", "temps-adverbis", "possessius", "numerals"],
        "topics": ["familia", "presentacions", "temps-dies", "numeros"],
        "roles": ["qui pregunta", "qui respon"],
    },
    {
        "n": 8,
        "slug": "el-metge",
        "name": "Dar uḍbib",
        "title": "Al metge",
        "about": "Dir què et passa, on et fa mal, i entendre el que t'han dit que facis.",
        "functions": [
            "preguntar com es troba algú",
            "dir on et fa mal",
            "dir que tens fred, set, gana o son",
            "dir que cal fer una cosa",
            "donar una ordre i dir que no la facin",
        ],
        "grammar": ["imperatiu", "negacio", "ser-tenir", "subordinades"],
        "topics": ["cos-salut", "emocions"],
        "roles": ["qui està malalt", "el metge"],
    },
    {
        "n": 9,
        "slug": "el-viatge",
        "name": "Amuddu",
        "title": "El viatge",
        "about": "Anar d'un lloc a un altre: com s'hi va, amb qui, i què ha passat pel camí.",
        "functions": [
            "dir com vas a un lloc",
            "dir amb qui vas",
            "dir que has passat per un lloc",
            "dir que has perdut una cosa",
            "dir que no hi has anat mai o que ja hi has anat",
        ],
        "grammar": ["preposicions", "temps-adverbis", "perfectiu", "derivacio-verbal"],
        "topics": ["viatge", "natura", "meteorologia"],
        "roles": ["qui viatja", "qui l'acompanya"],
    },
    {
        "n": 10,
        "slug": "els-convidats",
        "name": "Inbgiwn",
        "title": "Els convidats",
        "about": "Rebre algú a taula: el menjar, com està, i explicar el que vas fer.",
        "functions": [
            "convidar algú a entrar i a seure",
            "oferir menjar i beure",
            "dir si una cosa és bona",
            "explicar una cosa que va passar",
            "agrair i acomiadar-se",
        ],
        "grammar": ["perfectiu", "adjectius-qualitat", "manlleus", "imperatiu"],
        "topics": ["menjar", "casa", "salutacions"],
        "roles": ["qui rep", "qui és convidat"],
    },
]

# Com a molt, tantes frases triades NOMÉS pel tema. Coincidir pel tema és una coincidència
# fluixa —«menjar» és cert de mig catàleg— i serveix per completar un capítol curt, no per
# omplir-lo.
TOPIC_TOPUP = 24

BY_SLUG: Dict[str, Dict] = {c["slug"]: c for c in CHAPTERS}
SLUGS = [c["slug"] for c in CHAPTERS]


def check() -> List[str]:
    """Els slugs d'un capítol han d'existir de debò.

    Una errada d'escriptura aquí no peta res: el capítol surt buit, i això s'interpreta com «de
    cuina encara no en tenim res» quan el que passa és que el tema es diu d'una altra manera. Per
    això es comprova a l'arrencada i les queixes es diuen en veu alta.
    """
    units = set(grammar.SLUGS)
    subjects = {t["slug"] for t in topics_catalog.TOPICS}
    bad: List[str] = []
    for c in CHAPTERS:
        for g in c["grammar"]:
            if g not in units:
                bad.append(f"capítol {c['n']}: la unitat «{g}» no existeix")
        for t in c["topics"]:
            if t not in subjects:
                bad.append(f"capítol {c['n']}: el tema «{t}» no existeix")
    return bad


def chapter(slug_or_n) -> Optional[Dict]:
    """Un capítol pel seu nom curt o pel seu número."""
    if slug_or_n in BY_SLUG:
        return BY_SLUG[slug_or_n]
    try:
        n = int(slug_or_n)
    except (TypeError, ValueError):
        return None
    return next((c for c in CHAPTERS if c["n"] == n), None)


def sentences_for(db, slug: str) -> List:
    """Les frases NOSTRES que fan el que aquest capítol demana.

    Es trien pels slugs de gramàtica i de tema del capítol, i passen pels filtres d'exclusió de
    sempre (`grammar.not_excluded`): res gravat en càmera de «Tamazight For All», res etiquetat
    «private», cap drill irlandès. Una frase que coincideix per gramàtica compta més que una que
    només coincideix pel tema, i una amb veu va davant d'una muda: un capítol ha de començar pel
    que es pot escoltar.
    """
    from models import Drill as DrillModel
    c = BY_SLUG.get(slug)
    if not c:
        return []
    # El recull de Beni Mellal («private») hi entra: l'amo en té permís (decisió de 23-10-2026).
    # Aquella etiqueta protegeix la redistribució, no l'ensenyament. El que sí que queda fora és
    # el de sempre: les llengües excloses.
    rows = grammar.not_excluded(
        db.query(DrillModel).filter(DrillModel.text_tachelhit != None,      # noqa: E711
                                    DrillModel.text_tachelhit != "",
                                    DrillModel.text_catalan != None,        # noqa: E711
                                    DrillModel.text_catalan != ""),
        DrillModel).all()

    units, subjects = set(c["grammar"]), set(c["topics"])
    by_unit, by_topic = [], []
    for d in rows:
        hit_unit = bool(units & set(grammar.parse(d.grammar)))
        hit_topic = bool(subjects & set(topics_catalog.parse(d.topics)))
        if hit_unit:
            by_unit.append(d)
        elif hit_topic:
            by_topic.append(d)

    def best_first(rows_):
        # Primer qui ho diu. Les frases de la Halima i d'en Driss són 69 de 3.390 i sense
        # aquesta regla s'ofegarien entre les dues mil del recull: són les que porten una persona
        # que el projecte coneix, amb el seu poble i la seva varietat, i un capítol ha de
        # començar per aquestes (decisió de l'amo, 23-10-2026).
        # Després, el que es pot escoltar: un capítol que obre amb frases mudes ensenya a llegir,
        # i això és un mètode per parlar.
        return sorted(rows_, key=lambda d: (0 if grammar.our_speaker(d) else 1,
                                            0 if d.audio_url else 1,
                                            0 if d.image_url else 1, d.id))

    # A chapter is a path, not a pile. Matching by subject alone is a weak match — «menjar» is
    # true of half the library — so it only tops the chapter up when the grammar did not give
    # enough, and never drowns it.
    out = best_first(by_unit)
    if len(out) < TOPIC_TOPUP:
        out += best_first(by_topic)[:TOPIC_TOPUP - len(out)]
    return out


# Per sota d'això una secció no dona per a una lliçó: tres exemples que es puguin ESCOLTAR és
# el mínim per ensenyar a dir una cosa, i una frase muda ensenya a llegir-la, que no és el mateix.
ENOUGH = 3


def what_is_missing(c: Dict, rows: List) -> Dict:
    """El que a aquest capítol li falta per poder-se fer servir.

    No mesura si una unitat hi és —gairebé sempre hi és— sinó si té prou frases **amb veu**. Una
    secció amb vint frases i cap gravada no ensenya a dir res, i aquesta és la diferència que la
    biblioteca té de debò ara mateix: hi ha molt text i menys veu.

    No és una queixa: és la llista del que s'ha d'anar a gravar, per ordre d'urgència.
    """
    titles = {u["slug"]: u["title"] for u in grammar.UNITS}
    thin = []
    for g in c["grammar"]:
        here = [d for d in rows if g in grammar.parse(d.grammar)]
        voiced = [d for d in here if d.audio_url]
        if len(voiced) < ENOUGH:
            thin.append({"slug": g, "title": titles.get(g, g),
                         "sentences": len(here), "with_voice": len(voiced),
                         # una unitat que cap frase de la biblioteca no porta no és un forat
                         # d'aquest capítol: és un punt que no es veu a la frase (la fonètica)
                         "nowhere": len(here) == 0})
    voiceless = [d for d in rows if not d.audio_url]
    return {
        "thin": thin,
        "voiceless": [{"id": d.id, "text_tachelhit": d.text_tachelhit,
                       "text_catalan": d.text_catalan} for d in voiceless[:20]],
        "voiceless_total": len(voiceless),
    }


def readiness(c: Dict, rows: List) -> Dict:
    """Quant d'aquest capítol es pot fer servir: seccions amb prou veu, de les que té."""
    ok = 0
    for g in c["grammar"]:
        if sum(1 for d in rows if g in grammar.parse(d.grammar) and d.audio_url) >= ENOUGH:
            ok += 1
    return {"sections_ready": ok, "sections_total": len(c["grammar"])}


def index() -> List[Dict]:
    """Els deu capítols, amb el títol de les unitats que demanen."""
    titles = {u["slug"]: u["title"] for u in grammar.UNITS}
    return [{
        "n": c["n"], "slug": c["slug"], "name": c["name"], "title": c["title"],
        "about": c["about"], "functions": c["functions"], "roles": c["roles"],
        "grammar": [{"slug": g, "title": titles.get(g, g)} for g in c["grammar"]],
        "topics": c["topics"],
    } for c in CHAPTERS]
