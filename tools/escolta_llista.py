"""Escoltar una llista de vídeos sencera: transcriure-la, glossar-la i dir què vol dir.

Fet per a les llistes de veu amaziga **parlada de debò**: una persona davant la càmera, sense
música ni doblatge. La de Tamazight For All que en Pablo va passar el 13-11-2026 —vint-i-cinc
vídeos, dues hores, lingüística amaziga explicada EN amazic— és la primera.

## Les quatre passes, i per què cadascuna és com és

**1. Es talla pels SILENCIS, no cada tants segons.** El nostre model llegeix molt millor un
tros curt que un de llarg, i està mesurat dues vegades sobre el mateix clip:

    els 27 segons sencers        «aa aa arga yab yab iba iba…»     certesa 0,767
    el tall de la frase (5 s)    «argaz anna iga ibba»             certesa 0,979

I sobre un vlog de dos minuts, passar de trossos fixos de 15 s a tallar pels silencis va
pujar la certesa de ~0,84 a **0,914 de mediana**, amb el text visiblement més net. El tall
arbitrari parteix frases pel mig i el model s'hi perd.

**2. Ho llegeix el NOSTRE model** (MMS + adaptador shi ric, ADR 0009), el mateix que el
servidor. Cada emissió porta la seva certesa.

**3. El diccionari glossa paraula per paraula.** Un model general NO entén una lectura d'ASR
en amazic —el 30-10 el DeepSeek va contestar null a 150 de 150, i el 13-11 «no s'entén» a 8
de 10—, però el diccionari sí. Les paraules que el model enganxa (`datnttinin`,
`stmaziġtnnḫ`) es proven de partir, i només es donen per bones si TOTS els trossos són al
diccionari.

**4. I només llavors es demana el català**, amb les glosses a la vista. No es demana una
traducció: es demana que munti la frase amb les paraules que el diccionari sosté. Cada
resposta diu si és «segur», «probable» o «no s'entén», perquè una traducció fluida d'una
lectura dolenta sona bé i no vol dir res.

El salt que fa tot això, mesurat sobre dos vídeos: de 2 i 3 trossos útils de cada deu, a 5 de
28 i 10 de 29.

## El que NO fa

No posa res a la biblioteca. Deixa un JSON per vídeo i prou: això és material de tercers, i
qui decideix què hi entra no és un guió.

## Ús

    python tools/escolta_llista.py <url de la llista o del vídeo> --a <carpeta>

Es pot aturar i tornar a engegar: el que ja té JSON no es torna a fer.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

MIN, MAX = 1.2, 9.0      #: cap emissió més curta ni més llarga que això, en segons
PAUSA, SOROLL = 0.35, "-32dB"
MINIM_MOT = 3            #: un tros d'una o dues lletres casa amb qualsevol cosa
SPACE_DEFECTE = "https://josepabloucr-huggingface-asr-space.hf.space"


def codi_que_corre():
    """El commit del repositori que ha produït el fitxer, desat DINS del JSON.

    L'auditoria del 14-11-2026 no va poder reconstruir la línia de base: els JSON eren de
    les 10.10, tres commits eren posteriors, i la reconstrucció més propera donava glosses
    diferents en 14 de 40 trossos. Un resultat sense el codi que l'ha fet no es pot tornar a
    mesurar. També s'ha abaixat la temperatura del traductor a 0 pel mateix motiu: a 0,2 el
    mateix tros donava una resposta bona en una passada i una de falsa a la següent, i la
    casella «bo» d'una mostra de 40 es movia ±4 punts tota sola.
    """
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=os.path.dirname(os.path.abspath(__file__))
                              ).stdout.strip() or "?"
    except Exception:
        return "?"

SYS = (
    "Et donen un tros del que un model de reconeixement de veu ha sentit en un video en "
    "amazic (taixelhit o tamazight de l'Atles). El text ve mal escrit: mots enganxats, "
    "lletres errades, trossos que falten. NO saps amazic i no has de fer veure que si.\n\n"
    "El que SI que tens es el diccionari: et donem el significat de cada paraula que un "
    "diccionari amazic reconeix dins d'aquell tros. La teva feina es MUNTAR, en catala, la "
    "frase que aquelles paraules i aquell context fan mes probable.\n\n"
    "Les glosses venen de dues menes, i la diferencia es important:\n"
    "  mot = significat   la paraula es al diccionari tal com sona, o es una particula "
    "coneguda. Te'n pots refiar.\n"
    "  mot ≈ significat   NO hi era: s'hi ha arribat desfent-li la gramatica (annexio, "
    "plural, afixos de verb) o partint un mot enganxat. Aixo falla una vegada de cada tres "
    "—mesurat—, i la paraula pot voler dir una altra cosa.\n\n"
    "Contesta EXACTAMENT en dues linies:\n"
    "CATALA: <la frase, o «-» si no es pot dir res>\n"
    "CERTESA: segur | probable | no s'enten\n\n"
    "Les tres paraules volen dir aixo, i han de LLIGAR amb la linia de dalt:\n"
    "  segur       les paraules amb `=` sostenen la frase sencera.\n"
    "  probable    la frase es te dreta, pero s'aguanta amb paraules de `≈` o amb el "
    "context. Aquesta es la resposta normal quan has escrit una frase.\n"
    "  no s'enten  NO has escrit cap frase: a CATALA hi va «-».\n\n"
    "Es a dir: si has escrit una frase, la certesa es «segur» o «probable», mai «no "
    "s'enten»; i si has posat «no s'enten», a CATALA hi ha d'anar «-». No inventis una "
    "frase bonica per omplir —val mes dir que no s'enten— pero tampoc no neguis una frase "
    "que has pogut muntar.")

MOTS = re.compile(r"[^\W\d_]+", re.UNICODE)

#: La segona pregunta, la dels FETS. Neix de la mesura del 14-11-2026: amb el verb «ser»
#: servit, els falsos van caure de 15 a 8 i els bons es van quedar a 9. Dels falsos que
#: quedaven, el model n'era la causa en dos: va OMETRE un token glossat bé (#9) i va ESCRIURE
#: UNA RELACIÓ oposada a la glossa (#19). Una frase permet totes dues coses. Aquesta sortida
#: no: una paraula per token, un marc que descriu sense relacionar, la cita copiada, i la
#: frase a part lligada token a token. `backend/fets.py` ho comprova en codi i poda el que no
#: s'aguanta.
SYS_FETS = (
    "Et donen un tros del que un model de reconeixement de veu ha sentit en un video en "
    "amazic, i el significat de les paraules que un diccionari hi reconeix (`=` fiable, "
    "`≈` pot ser fals). NO saps amazic. No has de fer veure que si.\n\n"
    "Contesta NOMES amb un objecte JSON, sense cap text al voltant, amb aquestes claus:\n"
    "  \"interlineal\": una llista amb EXACTAMENT un element per cada token del tros, en el "
    "mateix ordre: la paraula catalana d'aquell token, o \"?\" si no la saps. Mai en saltis "
    "cap, mai n'afegeixis cap. Si un token es una paraula que el parlant ANOMENA (vegeu "
    "\"cita\"), a la seva casella hi va el token mateix entre cometes: \"«imikk»\".\n"
    "  \"tema\": un GRUP NOMINAL en catala que digui de que va el tros (mai una oracio, mai una "
    "relacio), fet amb paraules que surtin de la interlineal; o \"?\".\n"
    "  \"cita\": nomes si el missatge et dona CANDIDATS A CITA (els tokens que segueixen un "
    "verb de dir): el candidat que el parlant anomena com a paraula —«en diuen X», «es diu X»—, "
    "copiat tal com es. NO es cita un candidat que sigui qui parla o de qui es parla (una "
    "gent, un pronom): en «da ttinin imaziġn», «imaziġn» son els que diuen, no la paraula "
    "dita. Si no hi ha candidats o cap no es una paraula anomenada, null.\n"
    "  \"frase\": el catala de corregut, fet amb les paraules de la interlineal. ESCRIU-LA "
    "sempre que les caselles plenes donin per a una frase: un filtre la comprovara paraula "
    "per paraula contra la interlineal i la treura si una no s'aguanta, o sigui que no cal "
    "que t'abstinguis per prudencia. Null nomes si no pots dir res.\n"
    "  \"soste\" (opcional): si a la frase o al tema fas servir una paraula que no casa "
    "literalment amb la casella d'on surt («amazigues» per la casella «amazic»), lliga-la: "
    "{\"amazigues\": [3]}.\n\n"
    "No et demanem si es pregunta o afirmacio, ni si es negatiu, ni qui hi surt: aixo es "
    "calcula a partir de les particules i dels afixos, no cal que ho diguis.\n"
    "Regla unica: tot el que entregues ha de sortir d'una casella de la interlineal. Una "
    "paraula sense casella es una invencio, i es rebutjara."
)


# ------------------------------------------------------------------ el so
def _ffprobe_durada(cami):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", cami], capture_output=True, text=True)
    return float(r.stdout.strip())


def baixa_so(url, cami):
    """Només el so: un vídeo de dos minuts són 2 MB en comptes de 200."""
    if os.path.exists(cami):
        return cami
    #: `player_client=android` perquè el client per omissió es menja un 403 al format de so
    #: sol («unable to download video data: HTTP Error 403: Forbidden»). Amb el d'Android, el
    #: mateix vídeo baixa a la primera.
    subprocess.run([sys.executable, "-m", "yt_dlp", "--js-runtimes", "node",
                    "--extractor-args", "youtube:player_client=android",
                    "-f", "bestaudio/best", "-x", "--audio-format", "wav",
                    "--postprocessor-args", "-ac 1 -ar 16000",
                    "-o", cami.replace(".wav", ".%(ext)s"), url],
                   check=True, capture_output=True)
    return cami


def emissions(wav):
    """Els trossos de VEU, separats pels silencis."""
    p = subprocess.run(["ffmpeg", "-nostdin", "-i", wav, "-af",
                        f"silencedetect=noise={SOROLL}:d={PAUSA}", "-f", "null", "-"],
                       capture_output=True, text=True)
    inicis = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    finals = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    total = _ffprobe_durada(wav)
    brut, de = [], 0.0
    for i, s_de in enumerate(inicis):
        if s_de > de:
            brut.append((de, s_de))
        de = finals[i] if i < len(finals) else total
    if de < total:
        brut.append((de, total))

    nets = []
    for de, a in brut:
        if nets and (a - de) < MIN and (a - nets[-1][0]) <= MAX:
            nets[-1] = (nets[-1][0], a)
            continue
        while a - de > MAX:
            nets.append((de, de + MAX))
            de += MAX
        if a - de >= 0.4:
            nets.append((de, a))
    return nets


# ------------------------------------------------------------------ el model
def sent(cami, space, caps):
    import requests
    with io.open(cami, "rb") as f:
        r = requests.post(space + "/transcribe_mms",
                          files={"audio_file": ("c.wav", f.read(), "audio/wav")},
                          headers=caps, timeout=300)
    if r.status_code != 200:
        return "", None
    d = r.json()
    return (d.get("text") or "").strip(), d.get("confidence")


# ------------------------------------------------------------------ el diccionari
_EINES = {}


def eines_del_lexic(lexicon):
    """(significats, és_verb, és_nom), llegint les QUATRE butaques del lèxic.

    Es fan una sola vegada: porten la seva memòria de consultes, i refer-les cada paraula
    la llençaria.
    """
    if "fetes" not in _EINES:
        try:
            _EINES["fetes"] = morfologia.amb_lexicon(lexicon)
        except Exception:
            _EINES["fetes"] = ((lambda m: []), (lambda m: False), (lambda m: False))
    return _EINES["fetes"]


def significats(lexicon, mot):
    """Els significats de la forma exacta. Buit si el diccionari no la coneix."""
    try:
        return eines_del_lexic(lexicon)[0](mot)
    except Exception:
        return []


def parteix(lexicon, mot, cau=None, fons=0):
    """Les parts d'un mot enganxat, o None si no es pot partir del tot.

    Té la seva pròpia memòria: la de `glossa` guarda parelles (significat, com s'hi ha
    arribat), i barrejar-les aquí llegiria una tupla com si fos una llista de significats.
    """
    parts_cau = _EINES.setdefault("parts", {})
    if not mot or fons > 4:
        return None

    def te(forma):
        if forma not in parts_cau:
            parts_cau[forma] = significats(lexicon, forma)
        return parts_cau[forma]

    for tall in range(len(mot) - MINIM_MOT, MINIM_MOT - 1, -1):
        cap, resta = mot[:tall], mot[tall:]
        if not te(cap) or len(resta) < MINIM_MOT:
            continue
        if te(resta):
            return [cap, resta]
        mes = parteix(lexicon, resta, cau, fons + 1)
        if mes:
            return [cap] + mes
    return None


def glossa(lexicon, text, cau):
    """Què vol dir cada paraula, dient sempre si és una lectura SEGURA o una POSSIBILITAT.

    Les que surten del diccionari tal com sonen, i les partícules escrites a mà, van amb
    `=`. Les que han calgut una regla de morfologia van amb `≈`: d'aquelles, jutjant-ne
    quaranta a mà el 13-11-2026, una de cada tres era falsa, i qui llegeixi la llista ho ha
    de saber per no muntar-hi una frase de debò.
    """
    sig, es_verb, es_nom = eines_del_lexic(lexicon)
    fora = []
    for mot in MOTS.findall(text or ""):
        if len(mot) < 2:
            continue
        if mot not in cau:
            try:
                cau[mot] = morfologia.glossa(mot, sig, es_verb, es_nom)
            except Exception:
                cau[mot] = None
        trobat = cau[mot]
        if trobat:
            diu, com = trobat
            if com in morfologia.SEGURES:
                fora.append(f"{mot} = {diu}")
            else:
                fora.append(f"{mot} ≈ {diu}  [per {com}; pot ser fals]")
            continue
        parts = parteix(lexicon, mot, cau)
        if parts:
            fora.append(f"{mot} ≈ " + " + ".join(
                f"{p} ({', '.join(significats(lexicon, p)[:2])})" for p in parts)
                + "  [mot enganxat; pot ser fals]")
    return fora


# ------------------------------------------------------------------ el català
def que_vol_dir(deepseek, tema, tros, abans, despres, paraules):
    q = [f"DE QUE VA EL VIDEO: {tema}", ""]
    if abans:
        q.append(f"el tros d'abans deia: {abans}")
    if despres:
        q.append(f"el tros de despres deia: {despres}")
    q += ["", f"EL TROS A TRADUIR: {tros}", "",
          "EL QUE EL DICCIONARI RECONEIX EN AQUEST TROS:"]
    q += [f"  {p}" for p in paraules] or ["  (cap paraula reconeguda)"]
    try:
        r = deepseek.deepseek_generate(SYS, [{"role": "user", "text": "\n".join(q)}],
                                       max_output_tokens=400, temperature=0.0)
    except Exception as e:
        return f"(error: {type(e).__name__})", ""
    ca = cert = ""
    for linia in (r or "").splitlines():
        l = linia.strip()
        if l.upper().startswith(("CATALA:", "CATALÀ:")):
            ca = l.split(":", 1)[1].strip()
        elif l.upper().startswith("CERTESA:"):
            cert = l.split(":", 1)[1].strip().lower()
    return ca, cert


def fets(deepseek, tema, tros, abans, despres, paraules):
    """Els fets d'un tros, comprovats per `backend/fets.py`. Mai una frase sola.

    Torna {"fets": {...} | None, "rebutjat": [motius]}. Si el model no entrega JSON o la
    interlineal no fa la llargada dels tokens, `fets` és None i el motiu ho diu; si entrega
    coses sense token, es poden i els motius diuen quines.
    """
    import fets as F
    toks = F.tokens(tros)
    q = [f"DE QUE VA EL VIDEO: {tema}", ""]
    if abans:
        q.append(f"el tros d'abans deia: {abans}")
    if despres:
        q.append(f"el tros de despres deia: {despres}")
    q += ["", f"EL TROS ({len(toks)} tokens): {tros}",
          "ELS TOKENS, NUMERATS: " + "  ".join(f"[{i}] {t}" for i, t in enumerate(toks))]
    cands = F.candidats_a_cita(toks)
    if cands:
        q.append("CANDIDATS A CITA (segueixen un verb de dir): "
                 + ", ".join(f"[{i}] {toks[i]}" for i in cands))
    q += ["", "EL QUE EL DICCIONARI RECONEIX EN AQUEST TROS:"]
    q += [f"  {p}" for p in paraules] or ["  (cap paraula reconeguda)"]
    try:
        r = deepseek.deepseek_generate(SYS_FETS, [{"role": "user", "text": "\n".join(q)}],
                                       max_output_tokens=600, temperature=0.0)
    except Exception as e:
        return {"fets": None, "rebutjat": [f"error: {type(e).__name__}"]}
    nets, motius = F.comprova(r, tros, es_verb=_es_verb(), es_gent=_es_gent(),
                              es_particula=lambda w: morfologia.clau_de_particula(w) is not None,
                              es_coneguda=_es_coneguda())
    return {"fets": nets, "rebutjat": motius}


def _es_verb():
    """`es_verb` del lèxic, si és carregat; si no, cap (i la persona es llegeix amb cautela)."""
    try:
        import lexicon
        return eines_del_lexic(lexicon)[1]
    except Exception:
        return None


#: Gentilicis i pronoms que mai no són una paraula anomenada: són qui parla o de qui es parla.
_GENT = {"imaziġn", "imazighn", "amaziġ", "tamaziġt", "irgazn", "tmġarin", "mddn", "medden",
         "iεrabn", "aεrab", "irumiyn", "nutni", "nutnti", "nkkni", "kunni", "ntta", "nttat"}


def _es_gent():
    return lambda w: w.lower() in _GENT


def _es_coneguda():
    """La paraula, sencera, la coneix el lèxic o la taula a mà? Un token enganxat, no."""
    try:
        import lexicon
        sig, ev, en = eines_del_lexic(lexicon)
        return lambda w: morfologia.glossa(w, sig, ev, en, partir=False) is not None
    except Exception:
        return None


# ------------------------------------------------------------------
def un_video(vid, titol, a, lexicon, deepseek, space, caps, cau):
    fora = os.path.join(a, f"{vid}.json")
    if os.path.exists(fora):
        print(f"  {vid}: ja fet")
        return
    wav = os.path.join(a, f"{vid}.wav")
    try:
        baixa_so(f"https://www.youtube.com/watch?v={vid}", wav)
    except subprocess.CalledProcessError as e:
        print(f"  {vid}: no s'ha pogut baixar ({e.returncode})")
        return
    trossos = emissions(wav)
    print(f"  {vid}: {_ffprobe_durada(wav):.0f} s → {len(trossos)} emissions", flush=True)

    dits = []
    for i, (de, fi) in enumerate(trossos):
        tall = os.path.join(a, f"_t{i:04d}.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(de), "-to", str(fi),
                        "-i", wav, "-y", tall], check=True)
        text, cert = sent(tall, space, caps)
        os.remove(tall)
        dits.append({"de": round(de, 2), "a": round(fi, 2), "hi_sent": text, "certesa": cert,
                     "paraules": glossa(lexicon, text, cau)})

    for i, t in enumerate(dits):
        if not t["hi_sent"]:
            t["vol_dir"], t["certesa_traduccio"] = "", "no s'enten"
            continue
        abans = dits[i - 1]["hi_sent"] if i else ""
        despres = dits[i + 1]["hi_sent"] if i + 1 < len(dits) else ""
        t["vol_dir"], t["certesa_traduccio"] = que_vol_dir(
            deepseek, titol, t["hi_sent"], abans, despres, t["paraules"])
        #: i els fets, a part: la frase de dalt es la que es llegeix; aixo es el que es creu
        t.update(fets(deepseek, titol, t["hi_sent"], abans, despres, t["paraules"]))

    json.dump({"video": vid, "titol": titol, "codi": codi_que_corre(), "emissions": dits},
              io.open(fora, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bones = sum(1 for t in dits if t.get("certesa_traduccio") in ("segur", "probable"))
    certs = [t["certesa"] for t in dits if t["certesa"] is not None]
    print(f"  {vid}: {len(dits)} emissions · certesa mediana "
          f"{sorted(certs)[len(certs)//2]:.3f} · {bones} amb català" if certs else
          f"  {vid}: {len(dits)} emissions", flush=True)
    os.remove(wav)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url", help="la llista o un vídeo sol")
    p.add_argument("--a", default="escoltats", help="on es desen els JSON")
    p.add_argument("--env", help="d'on surten les claus, si no s'executa des de backend/")
    p.add_argument("--space", default=os.getenv("ASR_SPACE", SPACE_DEFECTE))
    o = p.parse_args()

    sys.path.insert(0, os.path.abspath("."))
    from dotenv import load_dotenv
    load_dotenv(o.env) if o.env else load_dotenv()
    os.environ.setdefault("LEXICON_WARMUP", "0")
    global morfologia          #: el mòdul viu a backend/, que només és al camí ara
    import deepseek_client
    import lexicon
    import morfologia
    os.makedirs(o.a, exist_ok=True)

    print("carregant el lèxic…", flush=True)
    lexicon.load()
    caps = ({"Authorization": "Bearer " + os.environ["HUGGINGFACE_API_KEY"]}
            if os.getenv("HUGGINGFACE_API_KEY") else {})

    llista = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node", "--flat-playlist",
         "--print", "%(id)s\t%(title)s", o.url], capture_output=True, text=True)
    videos = [l.split("\t", 1) for l in llista.stdout.splitlines() if "\t" in l]
    print(f"{len(videos)} vídeos\n", flush=True)

    cau = {}
    for vid, titol in videos:
        un_video(vid, titol, o.a, lexicon, deepseek_client, o.space, caps, cau)
    print(f"\nfet. Els JSON són a {o.a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
