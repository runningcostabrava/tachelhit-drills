"""El Mètode: deu capítols que porten algú de zero a dir alguna cosa al mercat.

Això és el catàleg, i és tot el que es pren d'un manual publicat: **el pla**. De cada capítol,
quatre caselles escrites per nosaltres llegint-lo — quines funcions comunicatives ensenya, quina
gramàtica demana, de quins camps de vocabulari va, i qui hi parla. El recorregut d'un curs és un
fet sobre com s'ensenya una llengua; el text d'un llibre és d'algú.

Això ha canviat: l'**ADR 0004** (23-10-2026) substitueix l'ADR 0003. Ara el Mètode **segueix el
llibre tan a prop com calgui** —explicacions, estructura, diàlegs i lèxic— amb el permís de
l'autor, i el que es canvia és el que la nostra varietat diu d'una altra manera. El que segueix
sent nostre i no ve d'enlloc més són **les veus**: cap frase d'un capítol no sona si no l'ha dita
una persona de la biblioteca, i el que un capítol demana i no tenim gravat va a demanar veu
(docs/CREDITS.md §2b).

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

import re
import unicodedata as ud

import grammar
import transliteration
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
        "about": "Les primeres coses que es diuen: hola, com estàs, i que Déu et porti amb bé.",
        "functions": [
            "començar una conversa i saludar segons l'hora",
            "preguntar com està algú i respondre",
            "desitjar sort, salut i bona festa",
            "rebre algú a casa i donar les gràcies",
            "acomiadar-se",
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
        # El capítol escrit ensenya també els parentius, les fórmules de cortesia, la marca de
        # persona dins del verb i els llocs de treball manllevats. Si no es declaren aquí,
        # `sentences_for()` no hi arriba i aquelles seccions es queden sense cap frase nostra.
        "grammar": ["estat-annexio", "preposicions", "ser-tenir", "preguntes",
                    "possessius", "formules", "perfectiu", "manlleus"],
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
            "dir el que fas habitualment, i el que t'agrada",
            "oferir alguna cosa a algú",
            "dir de qui és una cosa",
            "dir que no fas una cosa, o que no en fa cap ningú",
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
            "dir on vas i a casa de qui",
            "preguntar i dir l'hora",
            "situar una cosa al dia, la setmana, el mes o l'any",
            "demanar perdó",
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
            "dir el que faràs o el que passarà",
            "dir que cal fer una cosa, i donar una ordre",
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


def content_of(db, slug: str) -> Optional[Dict]:
    """El text d'aquest capítol, si ja s'hi ha posat.

    Un capítol sense text no és un error: és un capítol que encara no s'ha escrit, i la pantalla
    ensenya igualment les frases de la biblioteca que li toquen.
    """
    import json
    from models import MethodChapter
    row = db.query(MethodChapter).filter(MethodChapter.slug == slug).first()
    if not row:
        return None
    try:
        body = json.loads(row.body)
    except (ValueError, TypeError):
        return None
    body["updated_at"] = row.updated_at.isoformat() + "Z" if row.updated_at else None
    body["updated_by"] = row.updated_by
    return body


#: El que el servidor POSA en servir un capítol, i que per tant no s'ha de desar quan torna.
#:
#: Qui administra corregeix una línia i el navegador torna el capítol sencer tal com el tenia a
#: la pantalla: amb la tifinagh de cada línia i amb les frases nostres repartides per dins. Això
#: no és el capítol, és el que n'hem calculat; desar-ho el congelaria amb les frases d'aquell dia.
COMPUTED = {"ours_drills", "ours_total", "audio_url", "image_url", "speaker", "region",
            "from_drill_id", "heard"}


def strip_computed(body: Dict) -> Dict:
    """El capítol tal com s'escriu, sense res del que el servidor hi afegeix en servir-lo."""
    drop = COMPUTED | {dst for _, dst in TIF_FIELDS}

    def clean(x):
        if isinstance(x, list):
            return [clean(i) for i in x]
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items() if k not in drop}
        return x
    return clean(body)


def keep_voices(old: Optional[Dict], new: Dict) -> Dict:
    """Les línies que ja són frases de la biblioteca segueixen sent-ho després d'una correcció.

    Una línia del capítol es torna una frase nostra quan algú la grava, i el capítol se'n recorda
    amb un `drill_id`. Qui corregeix el text no ha de saber res d'això: puja el capítol tal com
    l'escriu, sense números, i si no els recuperéssim, **cada correcció desvincularia totes les
    veus**. La gravació seguiria existint i la línia tornaria a dir «grava-la», com si ningú no
    l'hagués dita mai — i això no es veu fins que algú busca el botó de reproduir.

    Ho va trobar un auditor comparant dues lectures del capítol 4 amb cinc hores de diferència:
    l'única línia d'exemple amb veu de tot el capítol l'havia perduda.
    """
    if not old:
        return new
    for kind in LINE_KINDS:
        was, now = _lines_of(old, kind), _lines_of(new, kind)
        for before, after in zip(was, now):
            if before.get("drill_id") and not after.get("drill_id"):
                after["drill_id"] = before["drill_id"]
    return new


def store_content(db, slug: str, body: Dict, who: Optional[str] = None) -> Dict:
    """Desa o reemplaça el text d'un capítol. Només per a qui administra."""
    import json
    from datetime import datetime
    from models import MethodChapter
    if slug not in BY_SLUG:
        raise ValueError(f"«{slug}» no és cap capítol del Mètode")
    # El que hi havia es llegeix ABANS de tocar la fila: si no, la consulta fa sortir la fila
    # nova a mig fer i la base es queixa que el cos és buit.
    body = keep_voices(content_of(db, slug), strip_computed(body))
    row = db.query(MethodChapter).filter(MethodChapter.slug == slug).first()
    if not row:
        row = MethodChapter(slug=slug)
        db.add(row)
    row.body = json.dumps(body, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    row.updated_by = who
    db.commit()
    return body


#: Quantes frases nostres s'ensenyen dins d'una secció. Una secció és una idea, no un magatzem:
#: més enllà d'això deixa d'explicar i es torna una llista.
OURS_PER_SECTION = 4

#: I quantes a les seccions de la segona zona, les que van plegades.
ASIDE_PER_SECTION = 2

#: El que el manual diu i el que es diu a Aït Mraw.
#:
#: El llibre és tachelhit del Souss i la nostra biblioteca és Atles central, i no fan servir les
#: mateixes paraules per a les mateixes coses. Buscar les frases nostres amb les paraules del
#: llibre no troba res: `dar-` surt a 5 frases i cap no té veu, `mnckk` a cap. Les que de debò
#: tenim són `ɣur` (76 frases, 59 amb veu) i `mšta` (13, 11 amb veu).
#:
#: Això no ho pot endevinar una màquina: ho sap qui parla la llengua. Creix quan l'amo n'hi
#: afegeix (aquestes dues les va dir ell, 2026-10-23).
ALSO_SAID = {
    "dar": ["ɣur", "ghor", "ghur", "xor"],          # tenir: nkki ɣur-i, is illa ɣur-š?
    "mnckk": ["mšta", "mshta", "mcta", "mchta"],    # quant / quants
}

#: Paraules catalanes que no diuen res de què va una frase: no es busquen.
STOP_CA = {
    "el", "la", "els", "les", "un", "una", "uns", "unes", "de", "del", "dels", "a", "al", "als",
    "en", "amb", "per", "que", "què", "qui", "és", "son", "són", "hi", "ha", "no", "sí", "si",
    "i", "o", "em", "et", "es", "ens", "us", "se", "li", "jo", "tu", "ell", "ella", "aquest",
    "aquesta", "això", "allò", "molt", "més", "cap", "res", "com", "ho", "d", "l", "s", "n",
}


def _ca_words(text: Optional[str]) -> set:
    """Les paraules catalanes que diuen alguna cosa de què va una frase."""
    import re
    out = set()
    for w in re.findall(r"[\wàèéíòóúïüç·]+", (text or "").lower()):
        w = w.strip("·")
        if len(w) > 2 and w not in STOP_CA:
            out.add(w)
    return out


#: Una paraula que surt a més d'aquesta part de la biblioteca no diu res de què va una frase.
#:
#: Filtrar per LONGITUD seria el remei fàcil i seria dolent: els imperatius que el capítol
#: ensenya —`ẓr` mira, `sɣ` compra, `ml` ensenya— fan dues lletres, i són justament les paraules
#: que s'han de buscar. El que no diu res no és el que és curt, és el que és a tot arreu: `n`,
#: `d`, `a`, `g`. Això es mesura, no s'endevina.
TOO_COMMON = 0.06

#: Per sota d'aquestes frases no es mesura què és comú: no hi ha prou biblioteca per dir-ho.
FEW = 50


def section_keys(s: Dict) -> Dict[str, set]:
    """De què va una secció, dit amb paraules que es puguin buscar a la biblioteca.

    Hi ha dues maneres, i la bona és la primera:

    **El que la secció DIU que ensenya** (`keys` i `keys_ca`). Una secció no va de les coses que
    surten als seus exemples, va d'una cosa: la dels datius va dels datius, encara que els seus
    exemples parlin d'aigua, d'ous i d'una clau. Buscar «aigua» a la biblioteca treu frases que
    parlen d'aigua i no tenen cap datiu, i això és el que l'amo ha vist dues vegades. Quan la
    secció declara les seves paraules, són EXACTAMENT aquelles: el que diuen els exemples és
    il·lustració, no matèria.

    **El que es pot deduir de les seves línies**, quan no en declara cap. Val per a les seccions
    de vocabulari, on els exemples SÓN la matèria.

    Una clau que comença amb guió —`-as`, `-awn`— no és una paraula: és el tros que s'enganxa al
    final («fkiγ-as», «imla-yyi»). Es busca només allà, perquè `aγaras` «camí» acaba en `as` i no
    té cap datiu.

    L'amazic s'eixampla sempre amb el que es diu a Aït Mraw: el manual escriu `dar-k` i aquí es
    diu `ɣur-k`, i sense aquesta passa no es trobaria ni una frase nostra.
    """
    import practice
    shi, tail, ca = set(), set(), set()
    declared = bool(s.get("keys") or s.get("keys_ca"))
    if declared:
        for w in (s.get("keys") or []):
            w = str(w).lower().strip()
            if w.startswith("-"):
                tail.add(w.lstrip("-"))
            else:
                shi.add(w)
                shi.update(ALSO_SAID.get(w, []))
        ca |= set(x.lower() for x in (s.get("keys_ca") or []))
    else:
        lines = list(s.get("examples") or [])
        for col in (s.get("columns") or []):
            lines += list(col.get("rows") or [])
        for line in lines:
            for w in practice.words_of(line.get("shi") or ""):
                w = w.strip("-?!.,¿¡").lower()
                if len(w) < 2:
                    continue
                shi.add(w)
                for alt in ALSO_SAID.get(w.split("-")[0], []):
                    shi.add(alt)
            ca |= _ca_words(line.get("ca"))
    # Una clau d'una lletra no identifica res: `sγ` «compra» sona «s», i «s» és la preposició
    # «a», que és a mig catàleg. El que no es pot buscar, no es busca.
    return {"shi": {k for k in (practice.sound_key(w) for w in shi if w) if len(k) > 1},
            "tail": {k for k in (practice.sound_key(w) for w in tail if w) if len(k) > 1},
            "ca": ca}


def _said(d) -> Dict[str, set]:
    """Què diu una frase, de tres maneres: per so, pel final enganxat, i pel significat.

    Dues coses alhora. Per SO, perquè `ghor`, `ɣur` i `xor` són la mateixa paraula escrita de
    tres maneres. I pels COMENÇAMENTS, perquè l'amazic enganxa la persona al mot: al llibre hi
    ha `dar-k`, i el que la gent diu és `ɣur-i`, `ɣur-š`, `ɣur-nɣ`. Comparant paraules senceres,
    `ɣur` encaixava amb 2 frases de 1.607; amb els començaments, amb les 22 que de debò ho diuen.

    El mateix passa amb els imperatius que el capítol ensenya —`ml`, `ẓr`, `sɣ`— que a les
    frases de debò gairebé no surten mai nus.

    Una clau de dues lletres, però, només casa amb la paraula SENCERA: `ml` «ensenya» per
    començament s'enduia `mlaqayx` «vaig quedar», que no hi té res a veure. De tres lletres en
    amunt el començament ja diu prou.

    I a part, els FINALS enganxats: `fkiγ-as` «li he donat» és el verb més el datiu, i el datiu
    només és datiu quan va darrere del guió. Buscar-lo com a final de paraula qualsevol s'enduria
    `aγaras` «camí»; buscar-lo com el tros de darrere el guió no s'endú res que no sigui això.
    """
    import practice
    out, tails = set(), set()
    for w in practice.words_of((d.text_tachelhit or "") + " " + (d.text_tachelhit_latin or "")):
        k = practice.sound_key(w)
        if k:
            out.add(k)                              # la paraula sencera
            # i els seus començaments, però només els que deixen DOS lletres o menys al darrere:
            # això és un afix (`ɣur-i`, `ɣur-š`) i no una altra paraula. Sense aquest fre, `ttam`
            # «vuit» —que sona «tam»— s'enduia `tamttut` «dona», i la secció dels números
            # ensenyava una frase que no en diu cap.
            for i in range(max(3, len(k) - 2), len(k)):
                out.add(k[:i])
        pieces = str(w).split("-")
        if len(pieces) > 1:
            stem = practice.sound_key(pieces[0])    # el guió ja diu on acaba la paraula
            if stem:
                out.add(stem)
            for piece in pieces[1:]:
                t = practice.sound_key(piece)
                if t:
                    tails.add(t)
    return {"shi": out, "tail": tails, "ca": _ca_words(d.text_catalan)}


def _uninformative(index: List[set]) -> set:
    """Les paraules que surten a tot arreu, i que per tant no diuen de què va res.

    Es mesura contra la biblioteca mateixa en comptes de tenir-ne una llista escrita a mà: el que
    no diu res no és el que és curt —`ml` «ensenya» fa dues lletres i és el que es busca— sinó el
    que és a mig catàleg.
    """
    from collections import Counter
    # Amb quatre frases no es pot mesurar què és comú: una paraula que surt a la meitat d'una
    # biblioteca de dues frases no és una paraula corrent, és la biblioteca. Per sota d'aquí, res
    # no es descarta (i una prova amb dues frases segueix trobant-les).
    if len(index) < FEW:
        return set()
    n = max(1, len(index))
    c = Counter()
    for words in index:
        c.update(words)
    return {w for w, k in c.items() if k / n > TOO_COMMON}


def why_here(said: Dict[str, set], keys: Dict[str, set], unit: Optional[str], d) -> Optional[str]:
    """Per què aquesta frase és en aquesta secció, dit amb paraules.

    El curs de gramàtica ja ho fa —«per què és aquí» a cada exemple— i aquí ha de passar el
    mateix: una frase que apareix sense dir què hi fa és soroll, per bona que sigui.

    No és una explicació inventada: és la raó de debò per la qual la tria l'ha agafada, la
    paraula que diu o el significat que comparteix. Si l'única raó és la unitat de gramàtica,
    també es diu, perquè és una raó més fluixa i qui llegeix ho ha de saber.
    """
    words = sorted(said["shi"] & keys["shi"], key=len, reverse=True)[:2]
    tails = sorted(said["tail"] & keys["tail"])[:2]
    senses = sorted(said["ca"] & keys["ca"])[:2]
    if tails:
        return f"hi porta «-{tails[0]}» enganxat al darrere"
    if words and senses:
        return f"diu «{words[0]}», i parla de {', '.join(senses)}"
    if words:
        return f"diu «{words[0]}»" + (f" i «{words[1]}»" if len(words) > 1 else "")
    if senses:
        return f"parla de {', '.join(senses)}"
    if unit:
        titles = {u["slug"]: u["title"] for u in grammar.UNITS}
        return f"és d'aquesta part de la gramàtica: {titles.get(unit, unit).lower()}"
    return None


def _score(said: Dict[str, set], keys: Dict[str, set], unit: Optional[str], d) -> int:
    """Com de bé va aquesta frase en aquesta secció. Zero vol dir que no hi va.

    Es compta QUANTES coses de la secció diu, no si en diu alguna: una frase que ensenya tres
    números val més que una que esmenta «1987», i això és el que fa que la rellevància guanyi la
    preferència per la veu o pel poble. La unitat de gramàtica només desempata.
    """
    hit_shi = len(said["shi"] & keys["shi"])
    hit_tail = len(said["tail"] & keys["tail"])
    hit_ca = len(said["ca"] & keys["ca"])
    # La PARAULA fa entrar; el significat només ordena. Deixar entrar pel català sol és el que
    # feia que la secció de la preposició `dar` ensenyés «El forn va escalfar la casa»: parla de
    # forns i de cases, i no hi surt la preposició enlloc. Una frase que no diu el que la secció
    # ensenya no ensenya la secció, per bé que hi vagi de tema.
    if not (hit_shi or hit_tail):
        return 0
    score = hit_tail * 4 + hit_shi * 3 + hit_ca * 2
    if unit and unit in grammar.parse(d.grammar):
        score += 1
    return score


def content_with_ours(db, slug: str, rows: List, card) -> Optional[Dict]:
    """El text del capítol amb les NOSTRES frases repartides per dins.

    Això és el que fa que el Mètode no sigui el llibre traduït. Cada secció explica una cosa i,
    tot seguit, ensenya com la diu la gent que coneixem: amb la seva veu, la seva imatge, el seu
    poble i la seva varietat.

    Com es tria, i per què no n'hi ha prou amb la unitat de gramàtica: `noms-genere-nombre` és
    cert de 683 frases, així que una secció sobre pesos i mesures acabava ensenyant «Oriol està
    molt enfadat» i «A les tres de la tarda». Ara una frase hi entra si **diu** una de les
    paraules de la secció (comparades per so, de manera que `ghor`, `ɣur` i `xor` són la
    mateixa) o si **vol dir** una de les seves coses (el català). La unitat només desempata.

    I una frase que no encaixa amb res **no hi surt**: val més una secció sense frases nostres,
    que es veu i es pot omplir, que una secció amb quatre que no hi fan res.
    """
    body = content_of(db, slug)
    if not body:
        return None
    sections = body.get("sections") or []
    if not sections:
        return with_tifinagh(body)

    said = {d.id: _said(d) for d in rows}
    noise = _uninformative([x["shi"] for x in said.values()])

    keys_of = {}
    for s in sections:
        k = section_keys(s)
        keys_of[s["id"]] = {"shi": k["shi"] - noise, "tail": k["tail"], "ca": k["ca"]}

    # Cada frase a la secció on encaixa MILLOR, no a la primera que la trobi. Anar-les repartint
    # per ordre feia que «Pesos i mesures» s'endugués `sin` «dos» i `kraḍ` «tres» abans que la
    # secció dels números hi arribés.
    best: Dict[int, tuple] = {}
    for d in rows:
        for s in sections:
            n = _score(said[d.id], keys_of[s["id"]], s.get("unit"), d)
            if n and n > best.get(d.id, (0, None))[0]:
                best[d.id] = (n, s["id"])

    by_section: Dict[str, List[tuple]] = {s["id"]: [] for s in sections}
    for d in rows:
        if d.id in best:
            by_section[best[d.id][1]].append((best[d.id][0], d))

    for s in sections:
        scored = by_section[s["id"]]
        # el que encaixa millor; després el que es pot escoltar i mirar; després les nostres veus
        scored.sort(key=lambda t: (-t[0],
                                   0 if (t[1].audio_url and t[1].image_url) else 1 if t[1].audio_url else 2,
                                   0 if grammar.our_speaker(t[1]) else 1, t[1].id))
        # i que no siguin quatre vegades la mateixa paraula: una secció ensenya, no repeteix
        picked, seen_keys = [], set()
        for _, d in scored:
            hits = said[d.id]["shi"] & keys_of[s["id"]]["shi"]
            if hits and hits <= seen_keys and len(picked) >= 2:
                continue
            picked.append(d)
            seen_keys |= hits
            # La segona zona (el que l'escena deixa veure, plegat) en porta dues, no quatre: s'hi
            # arriba tafanejant i no s'hi estudia. El total segueix sent el de debò, i la línia
            # «i N més a la biblioteca» hi porta: no desapareix cap frase.
            if len(picked) >= (ASIDE_PER_SECTION if s.get("zone") == "aside" else OURS_PER_SECTION):
                break
        # Una secció curta es queda curta. Omplir-la amb la unitat de gramàtica era el que hi
        # posava frases que no hi feien res —`noms-genere-nombre` és cert de 683 frases, i per
        # això «Pesos i mesures» acabava ensenyant «Oriol està molt enfadat»—, i l'amo ho ha
        # vist dues vegades. Val més una secció buida, que es veu i es pot omplir gravant.
        unit = s.get("unit")
        s["ours_drills"] = [
            {**card(d),
             "why": why_here(said[d.id], keys_of[s["id"]], unit, d)}
            for d in picked]
        s["ours_total"] = len(scored)
    return with_letters_everywhere(with_tifinagh(attach_heard(db, attach_library(db, body, rows), rows)))


#: El que hi ha escrit on hauria d'haver-hi la frase, a 170 drills (115 amb veu, #320). No són
#: paraules amazigues: són el text que s'hi va desar quan la transcripció es va perdre.
PLACEHOLDERS = {"text", "tex", "n", "-", "?", "..."}


def _readable(text: Optional[str]) -> bool:
    """Una frase que es pot ensenyar: sense restes de transcripció i prou curta per llegir-la.

    I que sigui una frase. Buscant la frase més curta que porti una `t`, la guanyadora era la
    paraula `text` —un drill que va perdre el text amazic i es va desar amb la paraula anglesa
    a dins—, i per a la `n`, la lletra `n`. Ensenyar-les com a exemple de res seria fer passar
    una errada nostra per llengua.
    """
    t = (text or "").strip()
    if not t or t.lower() in PLACEHOLDERS:
        return False
    return "[" not in t and len(t) <= 70


def heard_in(sound: str, voiced: List, used: set):
    """La frase nostra que millor deixa sentir aquest so.

    Es busca la LLETRA tal com s'escriu, no la clau de so de `practice`: aquí la gràcia és que
    qui llegeix vegi la lletra que acaba d'aprendre dins d'una frase de debò i la senti. Una
    clau de so faria el contrari —`ɣur`, `ghor` i `xor` són la mateixa clau— i la frase podria
    sortir sense la lletra escrita enlloc.

    Es normalitza a NFC perquè 283 drills guarden les lletres descompostes (š = s + U+030C):
    sense normalitzar, la š de la llista no és la š del drill i la lletra sembla que no hi sigui.
    """
    s = ud.normalize("NFC", sound or "")
    if not s:
        return None
    best = None
    for d in voiced:
        t = ud.normalize("NFC", d.text_tachelhit or "")
        # i que es pugui entendre: una frase sense traducció no ensenya el so de res
        if s not in t or not _readable(t) or not (d.text_catalan or "").strip():
            continue
        # la més curta mana (un so se sent millor en quatre paraules que en catorze), i una que
        # ja s'ha fet servir en una altra lletra passa al darrere: un capítol que ensenya trenta
        # sons no els ha de fer sentir tots amb la mateixa frase
        rank = (1 if d.id in used else 0, len(t.split()), d.id)
        if best is None or rank < best[0]:
            best = (rank, d)
    return best[1] if best else None


def attach_heard(db, body: Optional[Dict], rows: List) -> Optional[Dict]:
    """Cada línia que ensenya un SO, amb una frase nostra on es pot escoltar.

    El capítol dels sons ensenyava trenta-una lletres i no en deixava sentir cap, i ho deia:
    «aquestes paraules, de moment, no les pots escoltar». Era veritat mirant PARAULES SOLES
    gravades —no n'hi ha cap amb ḍ ḥ ɛ ṛ ɣ ṣ ṭ ẓ (#302)—, però un so no s'ha de sentir tot sol
    per sentir-se: dins d'una frase també hi és. Comptades les 3.430 frases, quinze dels setze
    sons difícils tenen com a mínim una frase nostra que els porta i que sona; només la kʷ no en
    té cap, i això el capítol ho ha de dir.

    La frase no SUBSTITUEIX la paraula de la fila: hi va al costat, amb qui la diu i d'on és. La
    paraula del manual segueix sent la paraula del manual, i el botó de sentir diu clarament que
    el que sonarà és una altra cosa —una frase nostra— i no pas ella.
    """
    if not body:
        return body
    lines = []
    for s in body.get("sections") or []:
        for e in s.get("examples") or []:
            # una línia que ja es pot escoltar no necessita cap frase de recanvi
            if e.get("sound") and not e.get("audio_url"):
                lines.append(e)
        for r in ((s.get("table") or {}).get("rows") or []):
            if r.get("sound"):
                lines.append(r)
    if not lines:
        return body

    from models import Drill as DrillModel
    voiced = db.query(DrillModel).filter(DrillModel.audio_url.isnot(None)).all()
    used: set = set()
    for line in lines:
        d = heard_in(line["sound"], voiced, used)
        if d is None:
            continue
        used.add(d.id)
        line["heard"] = {
            "drill_id": d.id, "shi": d.text_tachelhit, "ca": d.text_catalan,
            "audio_url": d.audio_url, "speaker": d.speaker or d.author,
            # NOMÉS el poble. La varietat és un codi —«tzm»— i no és un lloc: a la fila de la ɛ
            # hi sortia «ho diu tzm», que no diu d'on és ningú. Sense poble, el crèdit es queda
            # amb la persona i prou.
            "region": d.region,
            "tif": (transliteration.to_forms(d.text_tachelhit or "")["tifinagh"] or "").strip() or None,
        }
    return body


def attach_library(db, body: Optional[Dict], rows: List) -> Optional[Dict]:
    """Enganxa a cada línia del capítol el que la biblioteca ja en té: la veu i la imatge.

    Dues coses, i totes dues fan el capítol una altra cosa:

    · una línia que algú ha gravat es pot ESCOLTAR allà mateix, i per tant el capítol sencer es
      pot escoltar de dalt a baix. Fins ara el micròfon deia «grava-la» i prou, i la veu que algú
      hi havia posat no es podia sentir des del capítol;
    · una PARAULA del vocabulari que la biblioteca ja té surt amb la seva imatge i la seva veu.
      No és una imatge decorativa: és la que fem per a aquella frase, i una paraula amb la seva
      imatge s'aprèn d'una altra manera que una paraula dins d'una llista.

    No inventa res: si la biblioteca no en té, la línia es queda com era.
    """
    import practice
    from models import Drill as DrillModel
    if not body:
        return body

    # Les línies del capítol es busquen PEL SEU NÚMERO, no entre les frases del capítol: una
    # línia del llibre gravada ja no porta cap unitat de gramàtica (i no n'ha de portar cap),
    # de manera que no surt a `rows` i, buscant-la allà, el capítol no podia sentir-se a si
    # mateix.
    wanted = {line.get("drill_id") for kind in LINE_KINDS for line in _lines_of(body, kind)}
    wanted = {i for i in wanted if isinstance(i, int)}
    by_id = {d.id: d for d in rows}
    missing = wanted - set(by_id)
    if missing:
        for d in db.query(DrillModel).filter(DrillModel.id.in_(missing)).all():
            by_id[d.id] = d

    def from_drill(line, d):
        if d.audio_url:
            line["audio_url"] = d.audio_url
            line["speaker"] = d.speaker or d.author
            # i d'on és qui ho diu. El nom d'un parlant no és un indicador d'estat: és un
            # crèdit a una persona, i un crèdit sense poble deixa la varietat amagada, que
            # és justament el que aquest projecte no fa (docs/SCOPE.md).
            line["region"] = d.region or d.variety
        # Només les il·lustracions que DIBUIXEM per a una frase. Les de la carpeta vella de
        # fotos buscades no il·lustren la paraula: a «aɣrum» «pa» li havia tocat la façana d'un
        # hostal americà i a «tasarut» «clau», una mà amb polseres. Val més una targeta sense
        # imatge que una imatge que ensenya una altra cosa.
        if d.image_url and "/illustrations/" in (d.image_url or ""):
            line["image_url"] = d.image_url

    for kind in LINE_KINDS:
        for line in _lines_of(body, kind):
            d = by_id.get(line.get("drill_id"))
            if d is not None:
                from_drill(line, d)

    # Cada línia del capítol: la frase de la biblioteca que diu exactament això.
    #
    # Abans només s'hi buscaven les paraules del vocabulari, i només entre les frases del
    # capítol. El capítol 1 —el DELS SONS— no té cap frase assignada, de manera que no hi havia
    # on buscar i les sis seccions sortien mudes: un capítol que diu «no passis d'aquí fins que
    # distingeixis `imi` de `immi`» i no deixa sentir cap de les dues no es pot fer servir.
    # Ara s'hi busca per a TOTES les línies i, quan el capítol no en té prou, a tota la
    # biblioteca. Segueix sense inventar res: o la frase diu exactament això, o la línia es
    # queda com era.
    lines = [l for l in _voiceable_lines(body) if not l.get("audio_url")]
    said = _by_what_it_says(rows)
    missing_keys = {k for k in (_said_key(l.get("shi")) for l in lines) if k and k not in said}
    if missing_keys:
        said = {**_by_what_it_says(_short_drills(db, missing_keys)), **said}
    for line in lines:
        k = _said_key(line.get("shi"))
        d = said.get(k) if k else None
        if d is not None:
            from_drill(line, d)
            line["from_drill_id"] = d.id
    return body


def _voiceable_lines(body: Dict) -> List[Dict]:
    """Tot el que, dins d'un capítol, és una frase o una paraula amaziga que es podria escoltar:
    els exemples, els torns del diàleg, el vocabulari i les files de les columnes —que són
    justament les parelles mínimes del capítol dels sons (`imi`/`immi`, `mdi`/`mḍi`)."""
    out = [l for kind in LINE_KINDS for l in _lines_of(body, kind)]
    for s in (body.get("sections") or []):
        for col in (s.get("columns") or []):
            out.extend(r for r in (col.get("rows") or []) if isinstance(r, dict))
    return [l for l in out if isinstance(l, dict) and (l.get("shi") or "").strip()]


def _said_key(text: Optional[str]) -> str:
    """El que diu una frase, sense dependre de com s'escriu: «3afaš» i «ɛafaš» són la mateixa."""
    import practice
    return " ".join(practice.sound_key(w) for w in practice.words_of(text or ""))


def _by_what_it_says(rows: List) -> Dict[str, object]:
    said: Dict[str, object] = {}
    # la que es pugui mirar i escoltar primer; si no, la que tingui veu
    rank = lambda x: (0 if (x.image_url and x.audio_url) else 1 if x.audio_url else 2 if x.image_url else 3)
    for d in rows:
        k = _said_key(getattr(d, "text_tachelhit", None))
        if not k:
            continue
        have = said.get(k)
        if have is None or rank(d) < rank(have):
            said[k] = d
    return said


#: Una línia d'un capítol és una paraula o una frase curta. Buscar-la entre les frases llargues
#: de la biblioteca no serviria de res i costaria la consulta sencera.
SHORT_LINE = 60


class _Said:
    """El poc que una línia del capítol necessita d'una frase: qui la diu i on sona."""
    __slots__ = ("id", "text_tachelhit", "audio_url", "image_url", "speaker", "author",
                 "region", "variety")

    def __init__(self, row):
        (self.id, self.text_tachelhit, self.audio_url, self.image_url,
         self.speaker, self.author, self.region, self.variety) = row


#: L'índex de «què diu cada frase curta gravada» es guarda entre peticions, perquè refer-lo vol
#: dir llegir unes quantes milers de files i passar-les pel normalitzador a cada capítol que
#: algú obre. El que decideix si encara val és un segell barat —quantes n'hi ha i quan es va
#: tocar la darrera— de manera que una frase acabada de gravar hi entra de seguida.
_short_index: Dict[str, object] = {"stamp": None, "by_key": {}}


def _short_stamp(db) -> tuple:
    from sqlalchemy import func
    from models import Drill as DrillModel
    return tuple(db.query(func.count(DrillModel.id), func.max(DrillModel.updated_at))
                 .filter(DrillModel.audio_url.isnot(None)).one())


def _short_drills(db, keys: set) -> List:
    """Les frases curtes i gravades de la biblioteca que poden dir el que diu una línia del
    capítol. Vuit columnes i prou, i només les que es poden escoltar."""
    from sqlalchemy import func
    from models import Drill as DrillModel
    try:
        stamp = _short_stamp(db)
        if _short_index["stamp"] != stamp:
            rows = (db.query(DrillModel.id, DrillModel.text_tachelhit, DrillModel.audio_url,
                             DrillModel.image_url, DrillModel.speaker, DrillModel.author,
                             DrillModel.region, DrillModel.variety)
                    .filter(DrillModel.text_tachelhit.isnot(None))
                    .filter(DrillModel.audio_url.isnot(None))
                    .filter(func.length(DrillModel.text_tachelhit) <= SHORT_LINE)
                    .all())
            by_key: Dict[str, object] = {}
            for r in rows:
                k = _said_key(r[1])
                if k and k not in by_key:
                    by_key[k] = _Said(r)
            _short_index["by_key"], _short_index["stamp"] = by_key, stamp
    except Exception as e:   # una base de dades que no respon no deixa el capítol sense servir
        print(f"[METHOD] no s'ha pogut buscar veus a la biblioteca: {str(e)[:120]}")
        return []
    by_key = _short_index["by_key"]
    return [d for k, d in by_key.items() if k in keys]


def _lines_of(body: Dict, kind: str) -> List[Dict]:
    """Totes les línies d'una mena, en l'ordre en què surten al capítol."""
    if kind == "example":
        return [e for s in (body.get("sections") or []) for e in (s.get("examples") or [])]
    if kind == "turn":
        return list((body.get("dialogue") or {}).get("turns") or [])
    return list(body.get("vocabulary") or [])


#: On hi ha amazic dins del cos d'un capítol, i on va la seva tifinagh.
#:
#: El capítol s'escriu en llatí perquè així és el manual i així escriu la gent que grava, però
#: l'escriptura de la llengua va amb la llengua: a sota, petita, a totes les línies. Es calcula
#: en servir i no es desa, perquè és una transliteració del nostre transliterador i no una cosa
#: que ningú hagi escrit: si el transliterador millora, el capítol millora sol.
TIF_FIELDS = (("shi", "tif"), ("v", "v_tif"), ("m", "m_tif"), ("f", "f_tif"),
              ("qty_shi", "qty_tif"))


#: On hi ha PROSA del capítol, que pot portar sons citats («ɛ», «kʷ») dins d'una frase catalana.
#:
#: El curs de gramàtica ja els posa la tifinagh al costat des de fa temps (`grammar.with_letters`)
#: i el Mètode no hi passava. Es notava justament al capítol 1, que és el DELS SONS: deia «cinc
#: consonants: kʷ, gʷ, ɣʷ, xʷ, qʷ» i no n'ensenyava ni una en tifinagh. Una lliçó que ensenya un
#: so citant-lo en llatí ensenya el so i no ensenya la lletra, i aquesta app ensenya les dues.
#: «q» i «a» són la pregunta i la resposta del «Comprova-ho» que tanca una secció: també són
#: prosa del capítol, i una paraula amaziga que hi surti ha de portar la seva tifinag com a
#: tot arreu.
PROSE_FIELDS = ("intro", "text", "deep", "ours", "summary", "scene", "note", "v", "ca", "q", "a")


#: Les lletres que el català no té. Una paraula que en porta una NO és catalana.
#:
#: És el criteri per saber quines paraules d'una frase catalana són amazigues sense haver-ho
#: d'endevinar: «com la r francesa de Paris — aɣyul «ase», awraɣ «groc»» porta dues paraules
#: amazigues (aɣyul, awraɣ) i la resta és català. Transliterar-ho tot escriuria el català en
#: tifinagh, que és el que feia abans i no vol dir res.
#:
#: És un criteri CURT a posta: deixa fora paraules amazigues que només porten lletres llatines
#: («afrux», «qqn»). Val més una lletra de menys que una frase catalana disfressada.
AMAZIGH_ONLY = "ɣɛḥḍṭẓṣṛšžčǧʷ"
_WORD_IN_PROSE = re.compile(r"[A-Za-zÀ-ÿ" + AMAZIGH_ONLY + r"\-]{2,}")


#: Un tros citat dins la prosa: «mani-ɣ illa uɣaras?». Si a dins hi ha MÉS D'UNA paraula
#: amaziga, la tifinag va al final de la citació sencera i no paraula per paraula.
_QUOTED_RUN = re.compile(r"«([^»]{2,80})»")


def amazigh_words_in(t: str) -> str:
    """La tifinagh de les paraules amazigues que hi ha dins d'una frase catalana.

    L'amo, veient el capítol 1: «a “com la r francesa de «Paris» — aɣyul «ase»”, el que ha
    d'estar també en tifinagh és aɣyul, no la frase».

    Una paraula solta porta la seva tifinag al costat. Una FRASE citada sencera, no: el capítol
    3 servia «ɣur-i ⵖⵓⵔⵉ yan gʷma ⴳⵯⵎⴰ», amb la tifinag escampada entre les paraules i la frase
    il·legible. Quan la citació porta més d'una paraula amaziga, la seva tifinag va tota junta
    al final.

    Es fa en una sola passada: el text es parteix en trossos citats i trossos de fora, i cada
    tros es tracta una vegada. Passar-hi dos cops hi deixava les dues coses alhora.
    """
    if not t or "ⵣ" in t:
        return t

    def word_by_word(chunk: str) -> str:
        def one(m):
            raw = m.group(0)
            if not any(c in raw for c in AMAZIGH_ONLY):
                return raw
            tif = (transliteration.to_forms(raw)["tifinagh"] or "").strip()
            if not tif or tif == raw:
                return raw
            # Si la tifinag ja hi és al darrere, no se n'hi posa una altra: això es calcula en
            # SERVIR el capítol i qui administra el desa tal com el veu, de manera que sense
            # aquesta comprovació cada correcció hi afegia una còpia més.
            if m.string[m.end():].lstrip().startswith(tif):
                return raw
            return f"{raw} {tif}"
        return _WORD_IN_PROSE.sub(one, chunk)

    out, last = [], 0
    for m in _QUOTED_RUN.finditer(t):
        out.append(word_by_word(t[last:m.start()]))
        inside = m.group(1)
        amazigh = [w for w in _WORD_IN_PROSE.findall(inside)
                   if any(c in w for c in AMAZIGH_ONLY)]
        if len(amazigh) >= 2:
            tif = (transliteration.to_forms(inside)["tifinagh"] or "").strip()
            after = t[m.end():].lstrip()
            out.append(m.group(0) if (not tif or tif == inside or after.startswith(tif))
                       else f"«{inside}» {tif}")
        else:
            out.append(f"«{word_by_word(inside)}»")
        last = m.end()
    out.append(word_by_word(t[last:]))
    return "".join(out)


def with_letters_everywhere(body: Optional[Dict]) -> Optional[Dict]:
    """La tifinagh dels sons citats dins de la prosa del capítol.

    Només toca el que `grammar.with_letters` considera citat i curt —un so, no una paraula—, i
    només si el transliterador en treu una tifinagh de debò: val més una lliçó sense una lletra
    que una lliçó amb una lletra inventada.
    """
    if not body:
        return body

    def walk(x):
        if isinstance(x, list):
            for i in x:
                walk(i)
            return
        if not isinstance(x, dict):
            return
        for k in PROSE_FIELDS:
            v = x.get(k)
            if isinstance(v, str) and v.strip():
                x[k] = amazigh_words_in(grammar.with_letters(v))
        # La taula de l'alfabet del capítol 1 és el cas que la funció de dalt no veu: allà la
        # lletra NO va citada dins d'una frase, és la fila sencera («ɣ» | «com la r francesa»).
        p = x.get("p")
        if isinstance(p, str) and 0 < len(p.strip()) <= 2 and "ⵣ" not in p:
            tif = grammar.tifinagh(p.strip())
            if tif and tif != p.strip():
                x["p"] = f"{p.strip()} {tif}"
        for v in x.values():
            walk(v)

    walk(body)
    return body


#: Paraules que, si surten senceres, fan que la línia sigui catalana i no amazic. Una frase
#: catalana pot portar una paraula amaziga a dins («com la r francesa — aɣyul «ase»») i llavors
#: mirar si hi ha lletres amazigues no serveix de res: el que la delata és el català.
_CATALAN_MARKERS = re.compile(
    r"\b(com|una|amb|per|que|del|dels|les|aquesta|aquest|molt|sense|també|però|això|"
    r"quan|cada|fins|dins|cap|els|són|està|fer|dir)\b", re.I)


def _looks_amazigh(v: str) -> bool:
    """Una línia amazic, o una frase catalana que algú ha posat on no tocava?

    El capítol 1 va posar prosa catalana a la columna  —que és la de l'amazic— i la pàgina va
    ensenyar «com la r francesa de Paris» escrit en tifinagh. Allò no vol dir res, i el que s'hi
    havia de veure era la tifinagh de les paraules AMAZIGUES de dins (això ho fa
    ).

    El pany és curt: si no porta cap lletra que el català no tingui I té més de tres paraules,
    és una frase catalana i no es transliterarà.
    """
    if _CATALAN_MARKERS.search(v):
        return False
    return True


def with_tifinagh(body: Optional[Dict]) -> Optional[Dict]:
    """El mateix cos, amb la tifinagh de cada línia amazic al costat."""
    def walk(x):
        if isinstance(x, list):
            for i in x:
                walk(i)
            return
        if not isinstance(x, dict):
            return
        for src, dst in TIF_FIELDS:
            v = x.get(src)
            if isinstance(v, str) and v.strip() and not x.get(dst) and _looks_amazigh(v):
                t = grammar.tifinagh(v)
                if t and t != v.strip():
                    x[dst] = t
        for v in x.values():
            walk(v)
    if body:
        walk(body)
    return body


#: Les tres menes de línia d'un capítol que es poden dir en veu alta, i on viuen dins del cos.
LINE_KINDS = ("example", "turn", "vocabulary")


def line_at(body: Dict, kind: str, section: Optional[str], index: int) -> Optional[Dict]:
    """La línia d'un capítol, pel seu lloc. Retorna el diccionari mateix, per poder-hi escriure."""
    if kind == "example":
        for s in (body.get("sections") or []):
            if s.get("id") == section:
                items = s.get("examples") or []
                return items[index] if 0 <= index < len(items) else None
        return None
    if kind == "turn":
        items = ((body.get("dialogue") or {}).get("turns")) or []
        return items[index] if 0 <= index < len(items) else None
    if kind == "vocabulary":
        items = body.get("vocabulary") or []
        return items[index] if 0 <= index < len(items) else None
    return None


def drill_for_line(db, slug: str, kind: str, section: Optional[str], index: int, user) -> Dict:
    """La frase nostra que hi ha darrere una línia del capítol, creant-la el primer cop.

    El Mètode no estarà acabat fins que les seves línies es puguin **escoltar**, i una línia del
    manual no és encara una frase de la biblioteca: és text dins del capítol. Per poder-la gravar
    ha de ser un drill.

    Això tanca el cercle: **gravar una línia del llibre la converteix en una frase nostra.** El
    llibre hi posa l'amazic i el català; qui grava hi posa la veu, la seva manera d'escriure-ho,
    la seva varietat i el seu poble. El capítol es queda amb el número de la frase, de manera que
    la segona vegada s'hi afegeix una veu en comptes de crear-ne una altra.
    """
    import json
    from models import Drill as DrillModel, MethodChapter
    row = db.query(MethodChapter).filter(MethodChapter.slug == slug).first()
    if not row:
        raise ValueError("aquest capítol encara no té text")
    body = json.loads(row.body)
    line = line_at(body, kind, section, index)
    if line is None:
        raise ValueError("aquí no hi ha cap línia")

    existing = line.get("drill_id")
    if existing:
        d = db.query(DrillModel).filter(DrillModel.id == existing).first()
        if d:
            return {"drill_id": d.id, "created": False}

    shi = (line.get("shi") or "").strip()
    ca = (line.get("ca") or "").strip()
    if not shi:
        raise ValueError("aquesta línia no té text amazic per dir")

    c = BY_SLUG.get(slug) or {}
    d = DrillModel(
        text_tachelhit=shi, text_catalan=ca or None,
        # D'on surt, dit a la cara: ve del manual, que és del Souss, i encara no l'ha dit ningú.
        tag=f"metode-{slug}, del llibre",
        author=None, variety=None,
        # Ni gramàtica ni tema. Això ho va trobar un auditor dialectòleg: una línia del llibre
        # es desava amb LES QUATRE unitats del capítol i `grammar_source="owner"`, el segell de
        # màxima confiança. «is trit aman?» quedava desada com a exemple de `clitics-objecte` i
        # de `numerals`, que és fals; entrava a les lliçons d'aquelles unitats; i, com que
        # «seccions a punt» es compta per unitat declarada, cada línia gravada comptava a les
        # quatre alhora — el capítol es certificava a si mateix.
        #
        # D'on surt ja ho diu l'etiqueta. Què ensenya ho dirà qui ho sàpiga, o el classificador.
        grammar=None, topics=None,
        voice_wanted=True,
        voice_wanted_by=(getattr(user, "display_name", None) or getattr(user, "username", None)),
        created_by_user_id=getattr(user, "id", None),
    )
    db.add(d)
    db.commit()
    db.refresh(d)

    line["drill_id"] = d.id
    row.body = json.dumps(body, ensure_ascii=False)
    db.commit()
    return {"drill_id": d.id, "created": True}


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
