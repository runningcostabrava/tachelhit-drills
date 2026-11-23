# El pla dels models: què tenim, què falta i en quin ordre

Escrit el 23-11-2026 perquè qualsevol sessió —també una amb un model més barat— pugui continuar
sense haver de reconstruir res. El detall de cada mesura és a `DESXIFRAT.md`; això és el mapa.

**L'objectiu:** traduir amazic, **de veu i de text**, fins al català. L'àrab és el pont: tot el
material aparellat que existeix és en àrab, i d'àrab a català ja se'n sap.

## 1. Els quatre models i què els alimenta

| model | fa | material | on és (23-11) |
|---|---|---|---|
| **A. text → català** | NLLB afinat | parelles pròpies del catàleg, auditades | chrF 0,62; desplegat; passa el Gemini (0,60) |
| **B. text tifinag → àrab** | NLLB afinat | 4.562 parelles de la pantalla de la SNRT | 0,2634 → 0,3470 (§43) |
| **C. veu → text amazic** (ASR) | MMS-1b + adaptador `shi` | Common Voice, MTNRA, TFA, catàleg | CER 0,15-0,17 en veu neta; **1,05 sobre la tele** |
| **D. veu → àrab** (via 3) | Whisper small | SNRT 7,4 h + TutlAit 14 h = 21,4 h (§51) | **no ha corregut mai**; partida 0,1003 |

Dues coses que expliquen la taula:

* **Els subtítols de la SNRT no transcriuen el que es diu.** Són amazic estàndard escrit per ser
  llegit, sobre gent que parla dialecte. Per això la SNRT és mal material per a C (l'ASR contra
  ells dona CER > 1) i bon material per a B i D, que només demanen **significat**.
* **El TutlAit no té text amazic**, només so i àrab. Serveix per a D i no per a B ni C.
* **El TutlAit és traducció humana sencera**: a cada voluntari se li mostrava una frase àrab i
  la deia en el seu amazic (fitxa del conjunt). Per això `test_tutlait` ja és un jutge humà per
  a D. El seu camp `verified` (1.567 files) és una altra cosa: una tanda revisada d'**un sol
  parlant**, tota tzm i tota d'entrenament; no serveix de test.

## 2. Les regles de mesura (cadascuna ens ha costat un dia)

1. **Cap comparació que canviï la durada del so** quan el CER de partida passa d'1 (§49).
2. **La partició és per grup**: capítol a la SNRT, parlant al TutlAit. Mai per fila (§42).
3. **La fuita es tanca per text normalitzat**, no per identificador (§51: 1.395 files).
4. **El test és el mateix i sencer** a totes les variants que es comparen.
5. **Es mesura abans d'entrenar**, amb el mateix codi, i el número de partida es desa.
6. **Abans de creure un número, mirar què rep el model** (§48: alineava espais 22 h).
7. Cada resultat va a `DESXIFRAT.md` com a secció nova. Una secció no es reescriu: si una de
   posterior la contradiu, se li posa un avís que apunta endavant.

## 3. Els passos, en ordre

### Pas 1 — Llançar D (veu → àrab) amb el corpus combinat  ← ÉS EL SEGÜENT

* **Què hi ha fet:** manifests a `E:/tamazight/_magatzem/veu_ar_combinat/` (els refà
  `tools/snrt/magatzem/corpus_veu_arab_combinat.py`); quadern a
  `tools/snrt/magatzem/kaggle/veu-ar-afina.py`.
* **Conjunts de Kaggle** (tots privats, compte `josepabloucr`): `veu-ar-combinat` (manifests),
  `snrt-veu-ar` (so de la SNRT), `tutlait-veu-ar` (so del TutlAit).
* **Com es llança:** obrir `kaggle.com/code/josepabloucr/veu-ar-afina`, comprovar que els tres
  conjunts hi són adjunts, GPU T4, i prémer **Run All**. No fer servir la cua per lots
  (`kaggle kernels push` queda en QUEUED hores; memòria `kaggle-cua-per-lots-encallada`).
* **Ha anat bé si:** el registre diu `sense so 0` a les quatre parts, i al final surt el resum
  amb `test_snrt` i `test_tutlait`, abans i després.
* **Què se'n fa:** baixar `resultat.json`, escriure la **§52** amb la taula (abans/després per
  test, chrF per època), i llegir 20 sortides a ull: tradueix, o segueix transliterant?
* **Números a batre:** Whisper sense afinar 0,1003 · la via del text sense afinar 0,2614 (tots
  dos sobre la SNRT). Si `test_snrt` passa de 0,26, la via directa guanya la cadena.

### Pas 2 — Afegir el corpus d'EMINES a D

* `huggingface.co/datasets/EMINES/Tamazight-Speech-to-Arabic-Text` (~15,5 h, taixelhit).
* **Abans d'ajuntar-lo, passar-li `quin_arab_es_el_del_tutlait.py`** (canviant-hi el fitxer):
  la seva fitxa diu «transcripcions en àrab» i pot ser transliteració. Si la proporció de
  frases amb paraula funcional àrab queda a prop del 79 % del control, és traducció i entra a
  D. Si queda molt per sota, és amazic en lletres àrabs: **no entra a D** (ensenyaria a
  transliterar) i s'apunta com a material possible per a C.
* Mirar-ne la llicència i apuntar-la a `docs/CREDITS.md` abans de fer-lo servir.
* Afegir-lo com a tercera font a `corpus_veu_arab_combinat.py` amb les mateixes tres
  vigilàncies (grup, fuita per text, test separat) i tornar a fer el pas 1.

### Pas 2b — Les sèries de la SNRT, com a traducció humana per a D

**La idea (d'en Pablo, 23-11):** el subtítol àrab d'una sèrie el fa un subtitulador professional
a partir del diàleg. És traducció humana, igual que l'àrab del TutlAit. Per a D (que només
demana significat) es pot tractar com a material confirmat. **Per a C no** (no és transcripció),
**ni com a `verified` a l'app** (allà vol dir que un parlant nostre ho ha confirmat), **ni al
catàleg públic** (el permís de la SNRT és per a recerca i models).

**Primer, el que ja tenim: Baba Ali.** 3.621 parelles so ↔ àrab, Souss (shi, la varietat que
més ens falta a D), ja al catàleg amb la forma del TutlAit (`text_tachelhit` buit, `text_arabic`
del subtítol, regió «Souss (sèrie Baba Ali, SNRT)»). Afegir-lo com a tercera font a
`corpus_veu_arab_combinat.py` i fer una segona tirada de D canviant **només** això: la diferència
amb la primera diu quant aporta el material de sèrie. Així es jutja la idea amb un número abans
de collir-ne 70 hores.

**Després, el gros: 954 capítols de sèrie, 284 h** (catàleg a `tamazight-tv.md`, mai collits).

* Per a D no cal el tifinag, que és el que obliga a 1080p i el que fa caure capítols a la porta
  de qualitat. Cal: baixar a 720p, llegir **només la línia àrab** amb el lector propi
  (`tools/snrt/fabrica/lector_arab.py`, CER 0,007, local i gratis) i tallar el so per l'hora.
* La fàbrica no ho sap fer: l'etapa 02 exigeix tifinag i cau amb `OrdreIndecis` quan no n'hi
  ha. Cal un mode «àrab sol» a 02 (i a 05, que les portes no demanin tifinag).
* **Pilot abans d'encuar res:** Illy capítol 1 (`q8rMnmWpMkI`). Comptar rèpliques, mirar 20
  lectures de l'àrab a ull, i mesurar el desfasament entre l'hora del subtítol i la veu (a les
  entrevistes era > 0,5 s al 62 % dels talls, §41; en una sèrie pot ser diferent).
* **La partició és per sèrie, no per capítol:** els mateixos actors surten a tots els capítols
  d'una sèrie, i partir per capítol posaria la mateixa veu a l'entrenament i al test.
* **La varietat va per sèrie** (Illy és de l'Atles; Baba Ali, del Souss): etiquetar-la, com al
  TutlAit, perquè la barreja es pugui triar.
* Avisos: el subtítol condensa (és més curt que el que es diu), hi ha música i diàlegs que
  es trepitgen. Per a D és acceptable; per això el test de sèries ha d'anar separat dels altres.

### Pas 3 — El retall, com a variant de D i no com a projecte

* L'alineació (`alinea_mms_fa_tot.py`) deixa les fronteres a
  `E:/tamazight/_magatzem/alineacio_mms_fa_tot_*de*.jsonl`; `ajunta_mms_fa.py` les ajunta.
* Retallar **només el so d'entrenament** de la SNRT amb `retalla.py --alineacio ...`, pujar-lo
  com a conjunt nou i tornar a llançar el pas 1 canviant només això. **Els tests i el dev van
  sencers.**
* Es compara `test_snrt` entre la tirada sencera i la retallada. Aquest número no té el biaix
  de la §49 perquè el test no canvia de durada. Si la diferència és menor que la que hi ha
  entre dues èpoques seguides, el retall no val la pena i es tanca.

### Pas 4 — Un jutge humà on encara no n'hi ha (és d'en Pablo, no de la màquina)

* Per a D sobre veu llegida **ja n'hi ha un**: `test_tutlait` es mesura contra traduccions
  humanes (vegeu el punt 1).
* El que falta: **la parla de la tele** (`test_snrt` es mesura contra subtítols, que no són el
  que es diu) i **la sortida en català** del pas 5 (el català del TutlAit al catàleg el van fer
  auditors de màquina). Per a això: 200 frases escoltades per un parlant (Halima, Driss), i la
  traducció del model, és bona, mig bona o dolenta?
* Sense això no se sap si un chrF de 0,35 vol dir «s'entén» o «no s'entén».
* Al catàleg, `verified` vol dir que **un parlant nostre** ho ha confirmat d'oïda a l'app: n'hi
  ha 1 de 12.402, i 5.404 esperant. No mesura la qualitat del catàleg (el material del TutlAit
  hi és humà encara que no porti la marca; la importació ho desa a `verified_corpus`), sinó si
  el bucle de confirmació funciona. Els 245 marcats «la màquina hi està d'acord» són mitja hora
  de feina d'un parlant.

### Pas 5 — La cadena sencera: veu → català

* Agafar la sortida àrab de D i passar-la pel traductor àrab → català que ja fa servir el
  backend. Mesurar-ho contra els exercicis del TutlAit que ja tenen `text_catalan` auditat al
  catàleg (etiqueta `traduit-per-auditors`), **només els del test**.
* Aquest és el número de l'objectiu. Fins que no existeixi, tot el de dalt són peces.

### Pas 6 — B (text tifinag → àrab): més parelles, no més èpoques

* El millor punt de control és el tercer de cinc; a partir del quart es desaprèn (§43). El que
  falta és material.
* En queden ~61 capítols collibles, no 215 (dos programes porten tifinag; cal 1080p). La
  fàbrica (`tools/snrt/fabrica/`) els cull sola. Quan el corpus de parelles creixi un 50 %,
  tornar a entrenar amb `kaggle_zgh_arab.py` i el mateix test net.

### Pas 7 — C (ASR): no tocar-lo amb la SNRT

* No s'entrena C amb els subtítols de la SNRT com si fossin transcripcions: no ho són.
* El que el pot millorar és text confirmat per parlants (pas 4) i, si el pas 2 diu que
  EMINES és transliteració, aquell corpus.
* C deixa de ser al camí crític de la traducció de veu si D funciona.

### Pas 8 — La millora contínua amb tota la SNRT (quan els passos 1-2b hagin donat número)

**El bucle:** vídeos nous de la SNRT (YouTube, replay de forja) → baixar → llegir l'àrab (i el
tifinag si hi ha 1080p) → tallar ajustant el subtítol a la veu → portes → corpus partit per
sèrie → reentrenar D i B cada setmana a Kaggle → mesurar sobre els **tests fixos** → si guanya,
substituir el model. La SNRT penja capítols cada setmana: el material creix sol.

**Abans de collir, el que s'ha de mesurar** (al pilot d'Illy 1):

* **L'àrab a 720p amb el lector propi no s'ha mesurat mai** (CER 0,0074 és a 1080p; el codi ho
  avisa). El 720p real no és el simulat: amb el tifinag, el simulat donava 0,0073 i el real
  5/18. Mesurar les mateixes línies a 720p i a 1080p contra la veritat a mà.
* **Baixar 1080p sempre que n'hi hagi**: el tifinag dona parelles per a B (ara 4.562) i permet
  tallar amb l'alineació forçada.
* **Com es talla:** amb tifinag, MMS_FA sobre el tifinag (§50: 0,040 s de desacord amb el model
  gran); només amb àrab, un detector de veu (Silero VAD) que ajusti la finestra del subtítol.
  Comparar subtítol, MMS_FA i VAD contra 50 talls marcats a mà.
* **Quines sèries porten subtítol de principi a fi**: 24 fotogrames per sèrie, com es va fer amb
  els programes (`docs/EL_PLA.md`). Dels programes només 2 de 11 en portaven prou.

**Les quatre condicions perquè el bucle no es faci malbé sol:**

1. **Els tests no es toquen mai.** Les sèries noves només entren a l'entrenament.
2. **Un model nou només substitueix l'anterior si guanya als tests fixos** per més que la
   diferència entre dues èpoques seguides.
3. **Mai s'entrena amb la sortida dels nostres models**: només amb els subtítols de la SNRT. El
   29-10 el volant OCR ↔ ASR es va enverinar així (memòria `auditoria-asr-2026-10-29`).
4. **Una porta per sèrie nova** (confiança del lector + lectura de control del Qwen sobre una
   mostra, dins la quota gratuïta) i el jutge humà del pas 4 de tant en tant. El lector només
   s'ha mesurat en dos programes.

**Límits pràctics:** a `E:` hi queden 247 GB (95 % ple): esborrar el vídeo un cop extret el so
i llegides les franges. YouTube només baixa des del PC; el replay, també des de l'ECS. Kaggle
dona 30 h de GPU per setmana: una tirada setmanal hi cap.

**El que no és automàtic:** els permisos, el jutge humà i mirar a ull quan la porta d'una sèrie
nova s'encén.

## 4. El que NO s'ha de fer

* No comparar CER de so retallat contra so sencer.
* No publicar res de la SNRT a la biblioteca de l'app: el permís és per a recerca i models.
  (El TutlAit sí que es pot fer servir lliurement: permís confirmat per en Pablo el 23-11.)
* No reescriure `text_tachelhit`, `text_catalan` ni `text_arabic` a producció: la sortida de
  màquina va als camps `*_suggested`.
* No apilar feines de model al PC: 17,9 GB de RAM, i el sistema mata processos sense avisar.
  Una feina pesada cada vegada, i **enganxada al sistema de tasques**, mai amb `nohup`.
* No copiar un fitxer d'una branca local sense haver fet `git fetch` i `git pull` abans.

## 5. On és cada cosa

| | |
|---|---|
| quadern de la recerca | `docs/recerca/DESXIFRAT.md` |
| guions de mesura i muntatge | `tools/snrt/magatzem/` (còpia de treball: `E:/tamazight/_magatzem/`) |
| talls de la SNRT | `E:/tamazight/talls_ecs/` (19.547 talls, 33 capítols) |
| TutlAit | `E:/tamazight/_paquets/tutlait/` (13.334 talls, 20,8 h, 109 parlants) |
| Python amb torch i soundfile | `E:/tamazight/venv_asr/Scripts/python.exe` |
| eina de Kaggle | `E:/tamazight/venv_kaggle/Scripts/kaggle.exe` — a Windows, cridar-la **des de dins** de la carpeta amb `-p .` (amb un camí absolut falla) |
| com es treballa al repositori | `.claude/skills/project/` — una branca per issue, CI verda, i `main` exigeix branca al dia |
