# El pla

*Posat al dia el 21-11-2026. Si llegeixes un sol document d'aquest projecte, que sigui aquest.*

Què volem fer és a [`SCOPE.md`](SCOPE.md) i no canvia. Aquí hi ha **on som i què ve ara**, amb
els números mesurats al costat. Un número sense data i sense d'on surt no val: tots els d'aquí
tenen els dos.

---

## 1. On som, via per via

El material del SNRT porta **tres coses alineades al mateix fotograma**: la veu, el tifinag
cremat i l'àrab cremat. D'aquí surten tres vies, i una quarta que no és un model.

| via | mesurat | quan | com es mesura |
|---|---|---|---|
| **jo traduint l'àrab a mà** | **chrF 0,746** | 21-11 | contra una traducció confirmada, prova aparellada neta |
| **tifinag → àrab** (NLLB afinat) | **chrF 0,3470** (de 0,2634) | 21-11 | test per capítols, sense Rif, 4 capítols mai vistos |
| **veu → àrab** (Whisper afinat) | chrF 0,1573 (de 0,1003) — **però no tradueix** | 21-11 | el mateix test |
| **l'orella** (MMS + adaptador H4b) | CER **0,140** a cv-zgh-test-256 | 16-11 | 256 clips nets |

**El 0,1573 de la veu no és un guany, i el document ho ha de dir.** El número puja, però el
que en surt parla **del tema, no de la frase**: com que tot l'episodi va de literatura, el
model produeix àrab plausible sobre llibres i encerta el vocabulari del domini. Un 6 % de les
sortides es queden repetint una paraula. Comparat amb el de text, on les sortides sí parlen de
la mateixa frase, aquest **encara no serveix**. 7,4 h són molt poques — i, sobretot, el 40 %
d'aquelles hores no és la frase (§3, pas 1).

**La notícia incòmoda és la primera fila.** El que de debò tradueix avui no és cap model
nostre: és una lectura a mà de l'àrab. Els models valen per allò que no es pot fer a mà —215
capítols— i encara no hi arriben.

**La idea que ordena tot això** és d'en Pablo (21-11): *la traducció al català és important,
però molt més la traducció a l'àrab, perquè si el model tradueix bé del tifinag a l'àrab,
d'àrab a català ja és trivial.* I hi ha una raó tècnica que la fa encara millor: **l'àrab és
l'única baula de la cadena que és text humà de debò**. El tifinag cremat és una traducció
normalitzada per l'IRCAM i l'oïda s'equivoca; l'àrab el posa el canal. Per això l'àrab pot
**jutjar** les altres dues: quan l'oïda i el lector de tifinag casen amb el mateix àrab, les
dues són bones alhora.

---

## 2. El coll d'ampolla és la fàbrica, no cap model

Cada capítol que la fàbrica acaba dona **so, tifinag i àrab del mateix moment**: una parella
per a cadascuna de les tres vies. Per tant el que limita les tres alhora és quants capítols
s'acaben, no quin model s'entrena.

Estat: **27 capítols collits, ~17,9 h**, dels quals **8 són del Rif** i no entren enlloc
(tarifit és una altra llengua). El catàleg en té **215**.

---

## 3. Què ve ara, en ordre

L'ordre no és per gust: és **per guany mesurat dividit per esforç**.

### 1r. Tornar a tallar amb l'alineació forçada — **el 40 % del so no és la frase**

El diagnòstic del 18-11, sobre talls de capítols **antics**, deia que el 62 % tenien l'inici
desplaçat més de mig segon, i que retallant bé el CER passava de 0,7370 a **0,6581**: −0,0789.

**El 21-11 s'ha mesurat sobre ELS NOSTRES talls** (1.187 de la collita, MMS + adaptador H4b),
i estan pitjor:

| | |
|---|---|
| silenci al davant | mediana **0,74 s** · més de 0,3 s al **84 %** |
| silenci al darrere | mediana **0,85 s** · més de 0,3 s al **94 %** |
| **so que no és la frase** | **40 %** |

*«Silenci» vol dir «fora d'on el model sent el text»: pot ser el veí parlant. Tant se val —
no és la frase.*

**Dues de cada cinc hores que donem als models no són el que els diem que són.** Per comparar:
una ronda del cercle val −0,003 a −0,013 de CER, i el model de llengua al feix −0,009. Això és
d'un altre ordre, **no demana cap dada nova**, i toca el material que alimenta les tres vies
alhora. També explica per què la veu → àrab parla del tema i no de la frase.

Els límits nous ja estan calculats (`alineacio_nostra.json`, a la versió 3 del quadern
`veu-ar-afina` de Kaggle). Falta **tornar a tallar les 17,9 h amb aquests límits** i refer-ho
tot a sobre. El guió és
[`tools/snrt/magatzem/kaggle_alinea.py`](../tools/snrt/magatzem/kaggle_alinea.py) (i
`modelscope_alinea.py` per a aquella plataforma).

### 2n. Desencallar i fer córrer la fàbrica

Hi ha **dos encallaments diferents**, i convé no confondre'ls:

- **`tadfi-n-tskla / OMAR DEROUICH`** va caure amb `OrdreIndecis` perquè el logotip del canal
  és a la mateixa alçada que els subtítols i la seva tinta entrava a la puntuació del tram.
  **#721 ho resol**: de 3 N / 3 I (indecís) a **41 N / 0 I**, i els capítols que ja anaven
  donen retalls idèntics.
- **Els sis de `nkkni-didk`** no és cap error nostre: **la SNRT no en publica el vídeo.** La
  pàgina respon 200 i no porta **cap** font (0 m3u8, 0 mp4, `qualitats_replay: None`), mentre
  que una de bona en porta sis. No es poden collir, i el supervisor els hauria de marcar
  «sense font» en lloc de reintentar-los.

Cada capítol nou que passi són ~500 rèpliques per a les tres vies alhora.

### 3r. Refer els dos afinaments cap a l'àrab, amb els talls bons

Tots dos ja s'han fet un cop amb els talls d'ara: text **0,3470**, veu **0,1573 però sense
traduir**. **Cap dels dos no s'ha de desplegar ni donar per bo fins que el pas 1 estigui fet**:
entrenar amb un 40 % de so que no és la frase és pagar GPU per aprendre soroll. Els dos models
estan desats a Kaggle com a punt de partida per comparar-hi.

### 4t. Més parelles

Quan la fàbrica vagi, el corpus creix sol. Amb 4.562 parelles el text fa 0,3470; val la pena
tornar a mesurar cada cop que es dupliqui.

### El que NO fem ara, i per què

- **Més rondes del cercle virtuós**: val −0,003 a −0,013 per ronda, trenta vegades menys que
  el pas 1, i sobre el mateix material mal tallat.
- **Millorar l'OCR del tifinag**: ja llegeix amb **CER 0,0009**. No hi ha res a guanyar.
- **Tarifit**: és una altra llengua. Ni corpus, ni visor, ni app.

---

## 4. Aturat esperant una decisió

| què | qui |
|---|---|
| **Rotar la clau de BigQuery i la contrasenya del WordPress**, que van estar a git des del juny | en Pablo; jo no puc entrar als comptes |
| **Fusionar els PR amb la CI verda** | en Pablo; el classificador em bloqueja les fusions |
| Si es fa servir la GPU del ModelScope (gratis amb quota) per al pas 1 | en Pablo |
| Demanar els SRT a la SNRT, que estalviaria tota la lectura de pantalla | en Pablo |

---

## 5. On és cada cosa

| vols saber… | mira |
|---|---|
| què és el producte i on s'atura | [`SCOPE.md`](SCOPE.md) |
| **què hem mesurat, amb la prova al costat** | [`recerca/DESXIFRAT.md`](recerca/DESXIFRAT.md) — 44 seccions, amb índex |
| **en quines trampes he caigut** | [`recerca/METODE.md`](recerca/METODE.md) |
| quines afirmacions dels documents han quedat falses | [`recerca/AUDITORIA-2026-11-21.md`](recerca/AUDITORIA-2026-11-21.md) |
| decisions que costen de desfer | [`adr/`](adr/) |
| com es treballa aquí | `.claude/skills/project/SKILL.md` |
| els guions de la recerca | [`../tools/snrt/magatzem/`](../tools/snrt/magatzem/) — arxiu de treball, no codi mantingut |
| la fàbrica que corre cada dia | [`../tools/snrt/fabrica/`](../tools/snrt/fabrica/) |

**Com es llegeix el quadern.** Només s'hi afegeix: una secció no es reescriu mai, perquè el
valor és veure què es va creure i per què era fals. Quan una secció posterior en desmenteix
una d'anterior, la primera porta un avís que hi apunta. **Mira l'índex abans de citar cap
número.**

---

## 6. Per què existeix aquest document

L'alineació forçada es va mesurar el **18-11** i val més que qualsevol altra cosa que tenim a
l'abast. **Ningú no en va llegir el resultat fins al 21.** No era un descuit de ningú: no hi
havia cap lloc on aquella xifra hagués de competir amb les altres per l'ordre de prioritat.

Aquest document és aquell lloc. Si es queda vell, torna a passar.
