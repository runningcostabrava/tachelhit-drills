"""Els videos del disc E, mirables des del mobil quan no ets a casa.

En Pablo: «vull fer servir els videos que hi han a E: online, puc possar una petita contrasenya
extra quan entri a la pagina».

**Que fa.** Un servidor petit aqui, en aquest ordinador, que serveix:

    /<contrasenya>/                      la pagina del visor (llista + reproductor)
    /<contrasenya>/video/<slug>          el fitxer d'E:, **amb salts** (Range)
    /<contrasenya>/sub/<slug>            els subtitols

i s'obre a fora amb `ngrok http 8099`, que dona una adreca `https://…` que el mobil pot obrir.

**Per que una pagina propia i no la del web.** Si el video el servis des d'aqui i la pagina fos
la de Vercel, cada peticio seria d'origen creuat: ngrok gratuit posa una pagina d'avis al davant
la primera vegada, i la galeta que la salta seria de tercers -- el Safari i el Chrome del mobil
la bloquegen. Servint **pagina i video del mateix lloc** no hi ha cap d'aquests dos problemes, i
de passada funciona encara que Render estigui caigut.

**Els subtitols** venen de l'API de produccio la primera vegada i es **guarden al disc**: despres
ja no cal que Render hi sigui.

**El video no surt d'aqui.** No es puja enlloc: el serveix aquest ordinador mentre el programa
corre, i quan s'atura no hi ha res. Aixo respecta la condicio del permis de la SNRT (recerca si,
republicar no), pero **l'adreca d'ngrok es publica mentre dura**: qui la tingui i sapiga la
contrasenya pot mirar. Per aixo la contrasenya va al cami i l'adreca canvia a cada engegada.

    serveix_els_videos.py [contrasenya] [port]
"""
import io
import json
import os
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

#: la contrasenya no te valor per defecte i no s'escriu aqui: es passa en engegar-lo, o per
#: la variable CLAU_VISOR. Una clau escrita al codi queda a l'historial per sempre.
CLAU = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAU_VISOR") or ""
if not CLAU:
    raise SystemExit("falta la contrasenya: serveix_els_videos.py <contrasenya> [port]")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8099
API = os.environ.get("API", "https://tachelhit-drills-api.onrender.com")
CARPETES = [Path(r"E:/tamazight/_videos"), Path(r"E:/tamazight/_videos_baba")]
CAU = Path(r"E:/tamazight/_magatzem/cau_subtitols")
CAU.mkdir(parents=True, exist_ok=True)


def catalogue():
    """slug -> fitxer, i el conjunt de claus que nomes son **alies**.

    Els alies (l'id de YouTube que va dins del nom) serveixen per trobar el fitxer, pero no han
    de sortir a la llista. Es tornen marcats i no endevinats per la forma: `baba_ali_01` fa
    **exactament onze caracters**, com un id de YouTube, i una regla per la forma se'ls menjava
    tots trenta.
    """
    d, alies = {}, set()
    #: els episodis collits aqui tenen el video a `TD_TV/<id>/video.mp4`, i son els unics que
    #: porten tifinag: son justament els que val la pena mirar
    fabrica = Path(r"E:/tamazight/TD_TV")
    if fabrica.exists():
        for carpeta in sorted(fabrica.iterdir()):
            v = carpeta / "video.mp4"
            if carpeta.is_dir() and v.exists() and v.stat().st_size > 10 ** 6:
                d.setdefault(carpeta.name, v)
    for carp in CARPETES:
        if not carp.exists():
            continue
        for f in sorted(carp.glob("*.mp4")):
            if f.stat().st_size < 10 ** 6:
                continue
            d.setdefault(f.stem, f)
            m = re.search(r"_([A-Za-z0-9_-]{11})$", f.stem)
            if m and m.group(1) not in d:
                d[m.group(1)] = f
                alies.add(m.group(1))
    return d, alies


VARIETATS = Path(r"E:/tamazight/_magatzem/don_son_els_nous.json")


def _varietats():
    """{capitol: varietat}, llegida dels **toponims a l'arab**.

    En Pablo no vol tarifit barrejat: es una altra llengua. El classificador pel lexic no
    serveix per a aixo (te 117 marques tachelhit contra 39 tarifit, i el tifinag esta
    normalitzat per l'IRCAM, que es on les marques dialectals s'esborren). Els toponims a
    l'arab no passen per cap d'aquests dos filtres.
    """
    if not VARIETATS.exists():
        return {}
    try:
        d = json.loads(VARIETATS.read_text(encoding="utf-8"))
    except Exception:
        return {}
    nom = {"rif": "tarifit", "sus": "tachelhit", "atles": "Atles central",
           "cap senyal": ""}
    return {k: nom.get(v.get("diu"), "") for k, v in d.items()}


VAR = _varietats()

GLOSSARI = Path(r"E:/tamazight/_magatzem/glossari_del_significat.tsv")


def _glossari():
    """{esquelet: que vol dir} del glossari del cami invers.

    L'esquelet es calcula **aqui**, amb la mateixa funcio que la resta de la canonada. Si el
    calcules una segona vegada a la pagina en JavaScript, el dia que una de les dues canvii
    deixaran de dir el mateix i ningu no se n'adonara.
    """
    import sys
    sys.path.insert(0, r"E:/tamazight/_magatzem")
    try:
        from tria_el_millor_text import esquelet
    except Exception:
        return {}, None
    d = {}
    if GLOSSARI.exists():
        for i, l in enumerate(io.open(GLOSSARI, encoding="utf-8")):
            if i == 0:
                continue
            p = l.rstrip("\n").split("\t")
            if len(p) < 6 or not p[0].strip():
                continue
            k = esquelet(p[0])
            #: quatre consonants, no tres. Mesurat contra un glossari fals amb els mateixos
            #: esquelets barrejats: a tres consonants el 28 % dels casaments son casualitat
            #: (i d'aqui sortien «nnun = dit» i «yanun = coneixer», que son falsos); a quatre,
            #: el 7 %. Es el mateix llindar que al diccionari, i el mateix error que ja havia
            #: comes alla.
            if len(k) >= 4:
                #: si dues entrades casen amb el mateix esquelet, es queda la de mes capitols
                vell = d.get(k)
                caps = int(p[3] or 0)
                if vell is None or caps > vell[1]:
                    d[k] = (p[1], caps)
    return d, esquelet


GLOS, _ESQ = _glossari()


def anota(dades):
    """Afegeix a cada linia les paraules del glossari que hi surten, amb el seu significat."""
    if not GLOS or _ESQ is None:
        return dades
    for x in (dades.get("linies") or dades.get("repliques") or []):
        vist, fora = set(), []
        for camp in ("sentit", "tifinag"):
            for w in (x.get(camp) or "").split():
                k = _ESQ(w)
                if len(k) >= 4 and k in GLOS and k not in vist:
                    vist.add(k)
                    fora.append({"paraula": w, "vol_dir": GLOS[k][0]})
        if fora:
            x["glossari"] = fora[:4]
    return dades


def titol_de(slug, fitxer):
    """El nom que es llegeix a la llista: del fitxer del costat, del cau, o del slug."""
    s = fitxer.with_suffix(".json")
    if s.exists():
        try:
            t = json.loads(s.read_text(encoding="utf-8")).get("titol")
            if t:
                return t[:78]
        except Exception:
            pass
    c = CAU / f"{slug}.json"
    if c.exists():
        try:
            t = json.loads(c.read_text(encoding="utf-8")).get("episodi", {}).get("titol")
            if t:
                return t
        except Exception:
            pass
    m = re.fullmatch(r"baba_ali_(\d+)", slug)
    if m:
        return f"Baba Ali · episodi {int(m.group(1))}"
    m = re.fullmatch(r"baba_s(\d+)_e(\d+)_.+", slug)
    if m:
        return f"Baba Ali · temporada {int(m.group(1))} · episodi {int(m.group(2))}"
    return slug


AMB_SUB = Path(r"E:/tamazight/_magatzem/cau_amb_subtitols.json")


def amb_subtitols():
    """{slug: titol} dels episodis que tenen subtitols. De l'API un cop, i despres del disc.

    Sense aixo la llista la dominen els 127 Baba Ali acabats de baixar, que encara no en tenen:
    s'obre el visor i surt un trailer d'un minut amb un 404 a sota.
    """
    if AMB_SUB.exists():
        try:
            d = json.loads(AMB_SUB.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    try:
        with urllib.request.urlopen(f"{API}/snrt-privat/", timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
        noms = {e["slug"]: (e.get("titol") or e["slug"])
                for e in (d.get("episodis") or d) if e.get("slug")}
        AMB_SUB.write_text(json.dumps(noms, ensure_ascii=False), encoding="utf-8")
        return noms
    except Exception:
        #: si l'API no hi es, val el que ja hem llegit episodi a episodi
        return {f.stem: f.stem for f in CAU.glob("*.json")}


def durada_de(fitxer):
    s = fitxer.with_suffix(".json")
    if s.exists():
        try:
            return int(json.loads(s.read_text(encoding="utf-8")).get("durada") or 0)
        except Exception:
            return 0
    return 0


FABRICA = Path(r"E:/tamazight/TD_TV")


def de_la_fabrica(slug):
    """Els subtitols que la fabrica ha escrit aqui, per als episodis que encara no son a
    produccio.

    Els episodis acabats de collir tenen el **tifinag i l'arab** al seu `subtitols.jsonl`, i
    encara els falten la traduccio i l'orella. Al visor sortien com a «sense subtitols», que es
    fals: el que els falta es el catala, no el text.
    """
    p = FABRICA / slug / "subtitols.jsonl"
    if not p.exists() or p.stat().st_size == 0:
        return None
    linies = []
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("credits"):
            continue
        linies.append({"k": x.get("k"), "t_ini": x.get("t_ini"), "t_fi": x.get("t_fi"),
                       "tifinag": x.get("tifinag") or "", "arab": x.get("arab") or "",
                       "catala": x.get("catala") or "",
                       "sentit": x.get("sentit") or "",
                       "catala_estat": x.get("catala_estat") or "sense traduir"})
    if not linies:
        return None
    return {"slug": slug, "titol": slug, "linies": linies,
            "avis": ("Collit aquí fa poc: text llegit de la imatge."
                     + ("" if any(l["catala"] for l in linies) else " Encara sense traduir."))}


def subtitols(slug):
    """Del disc si ja hi son, de l'API si hi es, i de la fabrica d'aqui si no."""
    c = CAU / f"{slug}.json"
    if c.exists():
        return json.loads(c.read_text(encoding="utf-8"))
    try:
        with urllib.request.urlopen(f"{API}/snrt-privat/{slug}", timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
        c.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d
    except Exception as e:
        #: no hi es a produccio: potser l'acabem de collir nosaltres
        propi = de_la_fabrica(slug)
        if propi is not None:
            return propi
        return {"error": str(e), "repliques": []}


PAGINA = r"""<!doctype html><html lang="ca"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Tamazight TV</title><style>
:root{color-scheme:dark;--fons:#0d0f12;--marc:#15181d;--vora:#2a2f38}
*{box-sizing:border-box}
body{margin:0;background:var(--fons);color:#e9edf2;font:15px/1.5 system-ui,-apple-system,sans-serif}
header{padding:10px 14px;border-bottom:1px solid var(--vora);display:flex;gap:10px;align-items:center}
select{flex:1;min-width:0;background:var(--marc);color:inherit;border:1px solid var(--vora);
 border-radius:8px;padding:9px 10px;font:inherit}
.marc{background:#000}
.tela{position:relative;background:#000;container-type:inline-size}
video{width:100%;display:block;max-height:78vh;background:#000}
/* 64px: la barra de controls de Chrome fa uns 56px d'alt (i hi va el temps i el volum).
   Amb 52 el subtitol en catala encara hi queia a sobre -- es va veure MIRANT-HO, no
   mesurant-ho: la mesura deia «40px de marge» i semblava prou. */
.sub{position:absolute;left:0;right:0;bottom:64px;display:flex;flex-direction:column;
 align-items:center;gap:4px;padding:0 10px;pointer-events:none}
.sub div{background:rgba(0,0,0,.72);border-radius:7px;padding:4px 10px;max-width:96%;
 text-align:center;text-shadow:0 1px 3px #000}
.tif{font-size:19px;color:#ffd98a}.se{font-size:17px;color:#b6f0c0;font-style:italic}
.ar{font-size:17px;direction:rtl}.ca{font-size:16px;color:#cfe6ff}\n.glo{font-size:13px;color:#e8c6ff;background:rgba(0,0,0,.6)}.glo b{color:#fff;font-weight:600}
/* Els salts van FORA del video, en flux normal: a 360px un subtitol de tres llengues
   s'enfila i els tocava. A pantalla completa el video es tot l'espai i llavors si que
   han de ser-hi a dins, i hi tornen (regla :fullscreen de mes avall). */
.salts{display:flex;gap:5px;padding:8px 10px;justify-content:center}
.salts button,.ple{background:rgba(0,0,0,.62);color:#fff;border:1px solid rgba(255,255,255,.3);
 border-radius:7px;padding:6px 9px;font:600 13px system-ui;cursor:pointer}
.ple{position:absolute;right:8px;top:8px}
@container (max-width:430px){.tif{font-size:16px}.se{font-size:14px}.glo{font-size:11px}.ar{font-size:15px}.ca{font-size:14px}
 .sub{bottom:52px;gap:3px}.sub div{padding:3px 8px}.ple{padding:4px 7px;font-size:11px}}
#marc:fullscreen{display:flex;flex-direction:column;justify-content:center;height:100%}
#marc:fullscreen .tela{flex:0 1 auto}
#marc:fullscreen .salts{position:absolute;left:8px;top:8px;padding:0;z-index:2}
ol{list-style:none;margin:0;padding:8px 10px 40px;max-height:38vh;overflow:auto}
li{padding:7px 9px;border-radius:7px;cursor:pointer;display:flex;gap:9px}
li:hover{background:var(--marc)}li.ara{background:#1d2633}
li b{color:#8fb6ff;font-weight:600;min-width:52px;font-variant-numeric:tabular-nums}
p.avis{padding:12px 14px;color:#9aa6b4}
</style></head><body>
<header><select id="tria"></select></header>
<div class="marc" id="marc">
 <div class="tela" id="tela">
  <video id="v" controls playsinline controlsList="nofullscreen" disablePictureInPicture></video>
  <button class="ple" id="ple">&#9974;</button>
  <div class="sub" id="sub"></div>
 </div>
 <div class="salts">
  <button data-s="-5">-5s</button><button data-s="-2">-2s</button>
  <button data-s="2">+2s</button><button data-s="5">+5s</button>
 </div>
</div>
<ol id="llista"></ol>
<p class="avis" id="avis"></p>
<script>
const CLAU=location.pathname.split("/")[1];
const v=document.getElementById("v"), sub=document.getElementById("sub");
const llista=document.getElementById("llista"), tria=document.getElementById("tria");
let reps=[], ultim=-1;
fetch(`/${CLAU}/episodis`).then(r=>r.json()).then(d=>{
  // el tarifit no arriba aqui: el servidor ja l'ha tret
  const amb=d.episodis.filter(e=>e.sub), sense=d.episodis.filter(e=>!e.sub);
  const op=e=>`<option value="${e.slug}">${(e.titol||e.slug)}${e.varietat&&e.varietat!=="tarifit"?" · "+e.varietat:""}</option>`;
  tria.innerHTML =
    (amb.length?`<optgroup label="Amb subtítols (${amb.length})">${amb.map(op).join("")}</optgroup>`:"")
    + (sense.length?`<optgroup label="Encara sense subtítols (${sense.length})">${sense.map(op).join("")}</optgroup>`:"");
  const desat=localStorage.getItem("snrt_slug");
  if(desat && d.episodis.some(e=>e.slug===desat)) tria.value=desat;
  else if(amb.length) tria.value=amb[0].slug;
  else if(sense.length) tria.value=sense[0].slug;
  carrega(tria.value);
});
tria.onchange=()=>carrega(tria.value);
function carrega(slug){
  if(!slug) return;
  localStorage.setItem("snrt_slug",slug);
  v.src=`/${CLAU}/video/${encodeURIComponent(slug)}`;
  reps=[]; ultim=-1; sub.innerHTML=""; llista.innerHTML="";
  document.getElementById("avis").textContent="";
  fetch(`/${CLAU}/sub/${encodeURIComponent(slug)}`).then(r=>r.json()).then(d=>{
    // l'API diu «linies»; i els temps venen com a text ("137.0"): sense convertir-los,
    // x.t_fi+3 enganxa cadenes en comptes de sumar i el subtitol no marxa mai
    reps=(d.linies||d.repliques||[]).filter(x=>x.t_ini!=null)
      .map(x=>({...x, t_ini:Number(x.t_ini), t_fi:x.t_fi==null?null:Number(x.t_fi)}))
      .filter(x=>!isNaN(x.t_ini)).sort((a,b)=>a.t_ini-b.t_ini);
    if(!reps.length) document.getElementById("avis").textContent=
      "Aquest episodi encara no té subtítols nostres: només s'hi pot mirar i escoltar.";
    llista.innerHTML=reps.map((x,i)=>
      `<li data-i="${i}"><b>${mmss(x.t_ini)}</b><span>${esc(x.catala||x.sentit||x.tifinag||x.arab||"")}</span></li>`
    ).join("");
    llista.querySelectorAll("li").forEach(li=>li.onclick=()=>{
      v.currentTime=reps[+li.dataset.i].t_ini; v.play();
    });
  });
}
function esc(s){return (s||"").replace(/[<>&]/g,c=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]));}
function mmss(s){s=Math.max(0,Math.round(s));return (s/60|0)+":"+String(s%60).padStart(2,"0");}
v.ontimeupdate=()=>{
  const t=v.currentTime;
  let i=reps.findIndex(x=>t>=x.t_ini-.15 && t<=(x.t_fi??x.t_ini+3)+.15);
  if(i===ultim) return; ultim=i;
  if(i<0){sub.innerHTML="";return;}
  const x=reps[i], p=[];
  if(x.tifinag) p.push(`<div class="tif">${esc(x.tifinag)}</div>`);
  if(x.sentit) p.push(`<div class="se">${esc(x.sentit)}</div>`);
  if(x.arab) p.push(`<div class="ar">${esc(x.arab)}</div>`);
  if(x.catala) p.push(`<div class="ca">${esc(x.catala)}</div>`);
  if(x.glossari && x.glossari.length)
    p.push(`<div class="glo">${x.glossari.map(g=>
      `<b>${esc(g.paraula)}</b> = ${esc(g.vol_dir)}`).join(" · ")}</div>`);
  sub.innerHTML=p.join("");
  const li=llista.querySelector("li.ara"); if(li) li.classList.remove("ara");
  const nou=llista.querySelector(`li[data-i="${i}"]`);
  if(nou){nou.classList.add("ara"); nou.scrollIntoView({block:"nearest"});}
};
function mou(s){ v.currentTime=Math.max(0,v.currentTime+s); v.play(); }
document.querySelectorAll(".salts button").forEach(b=>b.onclick=()=>mou(+b.dataset.s));
document.getElementById("ple").onclick=()=>{
  const m=document.getElementById("marc");
  if(document.fullscreenElement) document.exitFullscreen();
  else (m.requestFullscreen||m.webkitRequestFullscreen).call(m);
};
addEventListener("keydown",e=>{
  if(e.target.tagName==="SELECT") return;
  const k={z:-5,x:-2,c:2,v:5}[e.key.toLowerCase()];
  if(k!==undefined){e.preventDefault();mou(k);}
  else if(e.key===" "){e.preventDefault();v.paused?v.play():v.pause();}
});
</script></body></html>"""


class Ma(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _curt(self, codi, cos=b"", tipus="text/plain; charset=utf-8", extres=None):
        self.send_response(codi)
        self.send_header("Content-Type", tipus)
        self.send_header("Content-Length", str(len(cos)))
        for k, v in (extres or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cos)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parts = [unquote(p) for p in self.path.split("?")[0].strip("/").split("/")]
        if not parts or parts[0] != CLAU:
            return self._curt(404, b"no")
        resta = parts[1:]

        if not resta or resta[0] == "":
            cos = PAGINA.encode("utf-8")
            return self._curt(200, cos, "text/html; charset=utf-8",
                              {"Cache-Control": "no-store"})

        if resta[0] == "episodis":
            cat, alies = catalogue()
            te_sub = dict(amb_subtitols())
            #: els collits aqui tambe en tenen, encara que no siguin a produccio
            if FABRICA.exists():
                for d in os.listdir(FABRICA):
                    p = FABRICA / d / "subtitols.jsonl"
                    if d not in te_sub and p.exists() and p.stat().st_size > 0:
                        te_sub[d] = d
            eps = []
            for s in sorted(cat):
                if s in alies:
                    continue
                #: els noms aleatoris de quaranta lletres semblaven brossa d'una altra
                #: canonada, i n'hi havia **vint-i-sis que son episodis amb subtitols**:
                #: nomes s'amaguen els que no en tenen
                if re.fullmatch(r"[a-z]{30,}", s) and s not in te_sub:
                    continue
                #: els collits aqui es diuen amb l'id de YouTube (onze caracters); nomes
                #: s'amaguen si no en tenim subtitols
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", s) and s not in te_sub:
                    continue
                #: el tarifit no hi entra: es una altra llengua i en Pablo no la vol aqui
                if VAR.get(s) == "tarifit":
                    continue
                eps.append({"slug": s, "titol": te_sub.get(s) or titol_de(s, cat[s]),
                            "sub": s in te_sub, "durada": durada_de(cat[s]),
                            "varietat": VAR.get(s, "")})
            #: primer els que tenen subtitols; despres els llargs; els trailers al final
            eps.sort(key=lambda e: (not e["sub"], e["durada"] < 300, -e["durada"], e["titol"]))
            cos = json.dumps({"episodis": eps}, ensure_ascii=False).encode("utf-8")
            return self._curt(200, cos, "application/json; charset=utf-8")

        if len(resta) > 1 and VAR.get(resta[1]) == "tarifit":
            return self._curt(404, "tarifit: fora del visor".encode("utf-8"))

        if resta[0] == "sub" and len(resta) > 1:
            #: s'anota al servir, no al desar: aixi el cau no es queda amb un glossari vell
            cos = json.dumps(anota(subtitols(resta[1])),
                             ensure_ascii=False).encode("utf-8")
            return self._curt(200, cos, "application/json; charset=utf-8")

        if resta[0] == "video" and len(resta) > 1:
            f = catalogue()[0].get(resta[1])
            if not f or not f.exists():
                return self._curt(404, b"no hi es")
            return self.video(f)

        return self._curt(404, b"no")

    def video(self, f):
        """Amb Range: sense aixo el mòbil no deixa saltar ni avançar."""
        mida = f.stat().st_size
        rang = self.headers.get("Range")
        ini, fi = 0, mida - 1
        codi = 200
        if rang:
            m = re.match(r"bytes=(\d*)-(\d*)", rang.strip())
            if m:
                a, b = m.group(1), m.group(2)
                if a:
                    ini = int(a)
                    fi = int(b) if b else mida - 1
                elif b:                       #: els ultims N bytes
                    ini = max(0, mida - int(b))
                if ini >= mida:
                    return self._curt(416, b"", "text/plain",
                                      {"Content-Range": f"bytes */{mida}"})
                fi = min(fi, mida - 1)
                codi = 206
        llarg = fi - ini + 1
        self.send_response(codi)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(llarg))
        if codi == 206:
            self.send_header("Content-Range", f"bytes {ini}-{fi}/{mida}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with io.open(f, "rb") as fh:
            fh.seek(ini)
            queda = llarg
            while queda > 0:
                tros = fh.read(min(262144, queda))
                if not tros:
                    break
                try:
                    self.wfile.write(tros)
                except (BrokenPipeError, ConnectionResetError):
                    return            #: el mòbil ha saltat: talla i prou
                queda -= len(tros)


if __name__ == "__main__":
    cat, _ = catalogue()
    print(f"{len(cat)} vídeos · port {PORT} · camí /{CLAU}/")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Ma)
    srv.daemon_threads = True
    srv.serve_forever()
