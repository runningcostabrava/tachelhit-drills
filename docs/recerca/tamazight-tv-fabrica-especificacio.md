# La fàbrica de Tamazight TV: especificació (17-11-2026)

Document de referència perquè els peons (models més senzills) facin la feina sense haver de decidir
res de fons. El pla general és a `tamazight-tv-pla.md`; el permís, a `docs/PERMISOS.md` (recerca sí,
republicar no, cap SRT: els OCR són nostres). Quan una cosa d'aquí no quadri amb la realitat, el peó
ho apunta a l'informe i **no** canvia la regla pel seu compte: la canvia el director.

## 1. Vocabulari

- **Capítol:** un vídeo (entrevista, capítol de sèrie, programa), identificat per `slug` (el de
  forja.ma si ve del replay; l'id de YouTube si ve del canal).
- **Rèplica:** un subtítol: un tram de temps amb una línia de tifinag a dalt i una d'àrab a sota.
  Id `<slug>_<k:04d>`, amb `k` l'ordre dins del capítol. L'id no canvia mai un cop assignat.
- **Triple:** so + tifinag + àrab d'una rèplica. **Parella humana:** tifinag ↔ àrab (la va fer un
  traductor humà de la cadena) i so ↔ tifinag. **Parella de màquina:** àrab → català.
- **Porta:** una condició numèrica que una rèplica passa o no. Les portes són les de §5 i només les
  canvia el director.

## 2. Carpetes i fitxers

Arrel de dades: `TD_TV` (al PC `C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\`; a l'ECS
`/root/tamazight_tv/`). Res d'això entra al repositori ni a producció.

```
TD_TV/
  cataleg/capitols.jsonl       una fila per capítol a processar (vegeu §3.1)
  cataleg/persones.jsonl       qui parla i d'on és (vegeu §3.2)
  <slug>/                      un capítol
    video.mp4                  720p amb so (i video_1080.mp4 sense so si cal per al tifinag)
    estat.json                 què ha fet cada etapa i amb quins comptes
    franges/                   fotogrames retallats (es poden esborrar quan 02 ha acabat)
    subtitols.jsonl            una fila per rèplica (vegeu §3.3)
    talls/<id>.wav             so de cada rèplica, mono 16 kHz
    numeros.json, INFORME.md   el resum de l'etapa 05
  _informes/AAAA-MM-DD.md      l'informe de cada nit per al director
```

## 3. Esquemes (camps obligatoris; els opcionals, només si es tenen)

### 3.1 `capitols.jsonl`
`slug`, `font` («replay» | «youtube»), `url` (pàgina de snrt.ma o `https://www.youtube.com/watch?v=…`),
`programa`, `titol`, `mena` («entrevista» | «debat» | «serie» | «informatiu» | «infantil» | «cultural» |
«musical»), `convidat` (nom o buit), `presentador`, `durada_s`, `prioritat` (1 = zona Dadès–Kalaat
M'Gouna o Azilal–Aït Bougmez; 2 = Alt Atles / Beni Mellal; 3 = altres), `estat` («pendent» | «fet» |
«error») i `nota`.

### 3.2 `persones.jsonl`
`nom`, `rol` («convidat» | «presentador»), `origen_lloc`, `origen_regio`, `varietat_probable`
(«taixelhit» | «tamazight de l'Atles central» | «tamazight de l'Atles mitjà» | «tarifit» | «sud-est» |
«desconeguda»), `font_origen` (url o cita; «no trobat» si no hi és), `capitols` (llista de slugs).
**Mai** inventar un origen: «no trobat» és una resposta vàlida.

### 3.3 `subtitols.jsonl` (una fila per rèplica)
`id`, `slug`, `k`, `t_ini`, `t_fi` (segons dins del vídeo, amb el marge de 0,25 s ja aplicat als
talls però NO aquí), `durada`, `arab` (text llegit, sense tashkil), `arab_lectures` (quants fotogrames
s'han llegit), `arab_acord` (fracció d'acord entre lectures; 1,0 si només n'hi ha una),
`arab_lector` («qwen3-vl-plus» | «crnn-v4» | …), `arab_conf` i `arab_dubtos` (només amb el lector propi: probabilitat mínima de la lectura i marca de revisió), `tifinag`, `tifinag_conf` (confiança mitjana per
glif), `tifinag_dubtosos` (glifs sota 0,85), `tifinag_lector` («plantilles-aslmdtv» | «sintetic-v1» |
…), `credits` (true si és capçalera o crèdits: fora de tot), `catala_a` i `catala_b` (àrab → català
pels dos models, amb `model_a`, `model_b`), `chrf_ab`, `catala` (el definitiu: `catala_a` si
`chrf_ab ≥ 0,5`; el del tercer model si ha calgut; buit si no passa), `catala_estat`
(«confirmat» | «tercer» | «descartat»), `catala_de_tifinag` (pel nostre traductor, només per
mesurar), `chrf_tif_ar` (entre `catala_de_tifinag` i `catala`), `tall` (ruta relativa del wav),
`varietat_capitol` (copiada del catàleg quan es conegui).

## 4. Etapes: contractes

Totes: s'executen com `python -X utf8 tools/snrt/fabrica/NN_nom.py <carpeta_del_capitol>`;
**reprenibles per id** (si ja hi ha resultat per a un id, no es repeteix; si el procés cau, tornar a
engegar continua); escriuen a `estat.json` la clau de l'etapa amb `inici`, `fi`, `comptes`, `versio`
i `error`; no escriuen mai fora de la carpeta del capítol (llevat de `_informes/`); cap ruta de
Windows fixa; les claus d'API, per variables d'entorn carregades del `.env` del backend (PC) o de
`~/.env` (ECS), mai al codi. Dependències: el venv del backend + `ffmpeg`.

- **01 baixa** (`tools/snrt/baixa_replay.py` per al replay, `yt-dlp` del venv per a YouTube):
  deixa `video.mp4` a 720p amb so. Si el lector de tifinag ho demana, també `video_1080.mp4`
  (sense so). Al replay, el PC i l'ECS hi arriben; a YouTube, només el PC (l'ECS té la IP
  bloquejada): el PC baixa i puja el 720p amb `scp`.
- **02 llegeix:** fotogrames de la franja de tifinag a 1 fps (geometria 720p: tifinag y 588–608
  `crop=1280:34:0:580`; àrab y 615–650 `crop=1280:44:0:612`; el fotograma `k` és l'instant
  `k − 0,5`; **comprovar la geometria a cada capítol nou** amb 10 fotogrames i aturar-se amb error
  si no quadra). **El rellotge el posa el tifinag:** segmentació per canvis de la franja de dalt
  (gratis) → trams; a cada tram, un fotograma d'àrab (el del mig) llegit pel lector d'àrab (visió de
  Qwen mentre no hi hagi el propi), i un segon fotograma només si la lectura és buida, curta
  (< 6 caràcters) o dona error; franges idèntiques a l'anterior se salten. Tifinag llegit al fotograma
  del mig amb el lector de tifinag (per plantilles d'aslmdtv mentre no hi hagi el sintètic; a 1080p
  si la confiança a 720p cau sota 0,9). Marca `credits` als trams on el text és capçalera o rodolí
  final (regla: més de 3 línies o text idèntic repetit > 20 s).
- **03 talla:** `talls/<id>.wav` mono 16 kHz, de `t_ini − 0,25` a `t_fi + 0,25`, retallat als
  límits del vídeo; no talla crèdits.
- **04 tradueix:** àrab → català amb dos models (per defecte `qwen3.8-max` i `deepseek-chat`,
  temperatura 0, el prompt de `tools/tutlait/tradueix_ar_ca.py`), `chrf_ab`; si `0,3 ≤ chrf_ab < 0,5`,
  un tercer (`gemini-2.5-flash` només si hi ha crèdit; si no, `qwen4-max`) i es queda el que
  coincideixi ≥ 0,5 amb el tercer; si `chrf_ab < 0,3` i cap acord, `descartat` (quasi sempre és un
  error d'OCR de l'àrab). Tifinag → català amb el nostre Space només per a `chrf_tif_ar` (mesura).
- **05 informe:** `numeros.json` i `INFORME.md` del capítol amb la plantilla de §7, i afegeix una
  línia a `_informes/AAAA-MM-DD.md`.
- **06 publica** (setmanal, no per capítol): les files que passen les portes de §5, al dataset
  **privat** d'HF `josepabloucr/tamazight-tv` (parquet: una taula de rèpliques + els wav), amb la
  fitxa que diu «Tamazight TV (SNRT), permís de recerca del 17-11-2026, no redistribuir».
- **nit.py:** llegeix `capitols.jsonl`, ordena per `prioritat` i després per `mena` (entrevistes
  abans que sèries), i per a cada capítol pendent fa 01→05; en acabar la llista, 06 si és dia de
  setmana marcat. Registre a `TD_TV/nit.log`. A l'ECS corre sota `tmux` i es pot matar i reprendre.

## 5. Portes (els números que decideixen)

Una rèplica és **apta per al train del traductor** si: `credits = false`, `tifinag_conf ≥ 0,85` i
`tifinag_dubtosos ≤ 2`, `arab_acord ≥ 0,5` (o 1 lectura sense error), `catala_estat ∈ {confirmat,
tercer}`, i 2 ≤ paraules del tifinag ≤ 30. **No** es filtra per `chrf_tif_ar`: aquest número mesura el
traductor, i filtrar-hi triaria el que el traductor ja sap (vist a Illy: 45 de 304).

Una rèplica és **apta per a l'ASR** si a més `durada ≥ 0,8 s` i la transcripció del nostre ASR actual
(MMS amb l'adaptador shi o el que mani `docs/recerca/`) té CER ≤ 0,4 contra el tifinag transliterat i
normalitzat (§6.2): és la manera de treure els subtítols que resumeixen en lloc de transcriure.

Un **capítol** és apte si ≥ 60 % de les seves rèpliques passen la porta del traductor; si no, va a
`estat = error` amb el motiu (geometria, so mut, lector) i el director decideix.

Un **lector nou** (tifinag o àrab) substitueix l'actual si, sobre les 200 franges reals amb veritat
(el full de dubtes resolt per en Pablo + les transcrites a mà), té CER ≤ 0,02 i no empitjora cap
parella de confusió coneguda; es canvia només la funció `llegeix_*` de l'etapa 02 i s'apunta
`*_lector` a cada fila.

## 6. Protocols

### 6.1 Varietat d'un capítol o d'una sèrie

> **Això es va corregir a `DESXIFRAT.md` §42 (vegeu `AUDITORIA-2026-11-21.md`, troballa 6):** del
> protocol de sota només corre el punt 2, el que el text mateix qualifica d'orientatiu, i les seves
> tres referències **no inclouen el Rif**, de manera que no pot retornar «rif» per construcció
> (`tools/snrt/fabrica/05_informe.py:118-122`). El punt 4, «la mesura que val», no es fa
> (`tools/snrt/fabrica/LLEGEIX-ME.md:87-89`). El resultat: va dir «tachelhit» als 27 capítols
> collits, i 8 són del Rif. El senyal bo no passa per cap dels dos filtres: són **els topònims a
> l'àrab**. El que hi ha aquí sota és el que es va creure.

1. Transliterar el tifinag de les rèpliques aptes al llatí amb `backend/transliteration.py`.
2. Normalitzar (§6.2) i comptar formes. Comparar amb tres referències construïdes de la biblioteca
   (`cataleg_prod.json`, camps `region`/`variety`/`speaker`): **Aït Mraw / Beni Mellal** (Halima,
   Driss i els reculls de Beni Mellal i Azilal), **Souss** (MTNRA, Common Voice shi), **Atles Mitjà**
   (zgh de CV i el que hi hagi). Mesura: proporció de les 200 formes més freqüents del capítol que
   són a cada referència, i la mateixa proporció **només sobre paraules gramaticals** (les 60 més
   freqüents de cada referència), que és la que discrimina.
3. Control obligatori: la mateixa mesura entre les tres referències entre elles (Illy: Beni Mellal i
   Souss només comparteixen un 14 %, perquè la distància és en bona part ortogràfica).
4. **Escoltar:** 30 rèpliques del capítol per l'ASR actual; la transcripció (dialectal) contra el
   tifinag (estàndard) dona els parells de correspondència (futur `rad` ↔ `ad`/`da`, condicional
   `iɣ` ↔ `mš`, etc.). Es guarden a `TD_TV/_varietat/<slug>.jsonl` i alimenten la taula estàndard ↔
   dialecte. Aquesta és la mesura que val; la del punt 2 és orientativa.
5. Resultat per capítol: `varietat_capitol` ∈ {«taixelhit», «atles-central», «atles-mitja», «rif»,
   «mixt», «desconeguda»} i tres números (proporcions). La decisió la pren el director amb les
   proporcions, les persones (§3.2) i la resposta de la SNRT; el peó no etiqueta per intuïció.

### 6.2 Normalització per comparar ortografies
Minúscules; `ḍ ṭ ẓ ṣ ṛ ḥ` → `d t z s r h`; `gh γ ġ` → `ɣ`; `c ch sh` → `š`; `kh` → `x`; `3 ε` → `ɛ`;
treure `ʷ` i `e`; una sola consonant on n'hi ha dues; treure guions i apòstrofs. És només per
comparar: mai es guarda text normalitzat com a text.

### 6.3 Lector sintètic (tifinag i àrab)
Tipografia identificada visualment i numèricament (IoU sobre glifs discriminants); 20.000 línies
sintètiques (text: el corpus propi; per a l'àrab, els subtítols llegits i `text_arabic` de TutlAit),
alçada de lletra de la SNRT ± 10 %, fons de vídeo real darrere, desenfocament 0–1 px, JPEG 60–90,
desplaçament vertical ± 2 px; CRNN + CTC (`tools/notebooks/ocr_tifinag_crnn.py` com a base) a Kaggle;
**veritat:** 200 franges reals etiquetades a mà (full de dubtes resolt per en Pablo + transcripció a
mà del peó), mai lectures d'un altre model com a única veritat (serveixen de pseudoveritat per a
l'entrenament, no per a l'acceptació). Acceptació: §5.

### 6.4 Traductor amb pivot (fase 5 del pla)
- **Dades:** rèpliques aptes (§5) de capítols aptes. **Partició per capítol, mai per línia** (les
  rèpliques d'un capítol es repeteixen i es responen): test = 10 % dels capítols (sencers), dev =
  5 %, train = la resta. Fuita: treure del train tota rèplica el tifinag o el català normalitzat de la
  qual sigui a `mostra60.json` o al test-dins de 200 (regla de `excloure-per-id-no-tanca-la-fuita`).
- **Tres candidats** amb el mateix nucli de Kaggle (`nllb_afina_propi_v3.py`, lr 5e-5, 5 èpoques,
  millor dev, llavor 1114): (a) v3 actual (sense tocar); (b) NLLB afinat **amazic → àrab**
  (`tzm_Tfng` → `arb_Arab`) amb la parella humana, i àrab → català amb `deepseek-chat`; (c) NLLB
  afinat **amazic → català** amb el català confirmat (destil·lació). I (d) = (c) + les 3.399 parelles
  de la v3.
- **Mesura:** chrF sobre les 60 de sempre (shi i Beni Mellal per separat), test-dins 200, i el test
  de capítols nous; bootstrap aparellat 2.000 × llavor 1114 (`compara_v3_v2.py`). **Decisió:** es
  desplega el candidat que guanya la v3 sobre les 60 amb IC que exclou 0 i Δ ≥ 0,01, sense empitjorar
  test-dins més enllà de 0,005 (la vara del soroll). Desplegament com sempre: pujar al repositori
  privat del model, reiniciar el Space, mesurar en viu, `torna_a_v2.py` preparat.
- **Mai** al train: rèpliques `descartat`, crèdits, ni res de la biblioteca marcada com a text de
  màquina no confirmat.

### 6.5 Transcriptor (fase 6)

> **Això es va corregir a `AUDITORIA-2026-11-21.md`, troballa 2:** la «referència 0,1537» és la
> xifra del 29-10 d'un adaptador que des del 16-11 ja no serveix. Al mateix test de 256 clips,
> l'adaptador que servim ara (H4b) fa **0,140** (`zouhir-amazigh.md:173`), i el quadern §38 en dona
> el greedy a 0,1463. Un model nou que «millorés 0,1537» pot ser pitjor que el que ja tenim. A més,
> el text no diu amb quina escala de puntuació és el 0,1537, i el projecte sap que les escales
> difereixen (`tamazight-for-all.md:893`). El que hi ha aquí sota és el que es va creure.

Dades: rèpliques aptes per a l'ASR (§5) de capítols amb `varietat_capitol` = «atles-central» primer;
objectiu text = tifinag transliterat sense plegar (regla `tachelhit-asr-plegat-esborrava-lletres`).
Entrenament: adaptador MMS a Kaggle com H4 (`h4_afina_shi_amb_zouhir.py`). Mesura: test net CV zgh
(256 talls; referència 0,1537), test-fora, i 10 % de capítols retinguts. Decisió: adoptar si CV zgh
millora amb IC i test-fora no empitjora més de 0,005.

## 7. Plantilla d'`INFORME.md` d'un capítol

Títol, slug, font, programa, convidat, durada; taula: rèpliques totals / crèdits / diàleg, segons amb
text, mediana de durada; OCR àrab: lectures, acord mitjà, % unànimes; OCR tifinag: conf mitjana, %
glifs ≥ 0,85, dubtosos; traducció: `chrf_ab` mitjà, % confirmat / tercer / descartat; `chrf_tif_ar`
mitjà i % ≥ 0,5 (mesura del traductor); portes: quantes rèpliques aptes per al traductor i per a
l'ASR; varietat (§6.1, els tres números i la decisió pendent); cost (fitxes de visió i de text per
model, minuts de màquina); **20 rèpliques a ull** (llavor 1114) amb franja, àrab, tifinag, català i
un judici d'una paraula («bé» / «OCR» / «traducció» / «resum»); problemes i el que el director ha de
decidir. L'informe de la nit (`_informes/`) és la suma: capítols fets, rèpliques aptes acumulades,
cost del dia, portes tancades amb motiu, i les decisions pendents en una llista.

## 8. Què decideix el director (i només ell)

Quins capítols entren (amb les persones i la varietat davant), quan es llança un entrenament, si un
lector nou substitueix l'actual, qualsevol canvi de llindar de §5, qualsevol cosa que toqui
producció o publiqui dades, i què es diu a la SNRT.
