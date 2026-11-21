# Tamazight TV: el pla, i la fàbrica que ha de córrer sola (17-11-2026)

Permís de la SNRT: recerca sí (traductor i transcriptor), republicar no (`docs/PERMISOS.md`).
Encàrrec d'en Pablo: (1) els dos OCR, tifinag i àrab, «al 100 %»; (2) una traducció àrab → català
(o anglès o francès) perfecta; (3) **el pivot en àrab**: qui va fer els subtítols traduïa de l'amazic
a l'àrab, així que la parella humana és amazic ↔ àrab, no amazic ↔ català; (4) la varietat ha de ser
la de Boutharar / Aït Bougmez; (5) **el procés ha de córrer sense Claude**: els models xinesos (Qwen a
Model Studio, DeepSeek) fan la feina de pensar dins de guions; Claude és un director extern que
llegeix informes i decideix.

## Què és aquest material, dit amb precisió

Cada rèplica d'un capítol dona tres coses alineades en el temps: **so** (parla real en context),
**tifinag** (la transcripció del que es diu, feta per l'equip de la cadena) i **àrab** (la traducció
humana). D'aquí surten dues parelles humanes, so ↔ tifinag (veritat per a l'ASR) i tifinag ↔ àrab
(veritat per al traductor), i una de màquina, àrab → català, que amb l'àrab estàndard els models grans
fan molt bé i es pot auditar. És el que no teníem: milers d'hores de parella humana. Les reserves,
perquè no ens enganyem: el subtítol pot resumir la rèplica (no sempre és literal), la varietat canvia
per sèrie, i tot passa per dos OCR que avui no són perfectes.

## Les fases

> **Dues fases de sota es van corregir (vegeu `AUDITORIA-2026-11-21.md`, troballes 2 i 6).** La
> **fase 4** afirma un filtre («només les sèries de l'Alt Atles central entren al train») que no
> existeix: `05_varietat.py` no s'ha construït mai i la funció que fa la feina
> (`tools/snrt/fabrica/05_informe.py:111-150`) no té cap referència del Rif, de manera que no pot
> dir-ne «rif». Va dir «tachelhit» als 27 capítols collits, i 8 són del Rif (quadern §42). La
> **fase 6** posa com a porta «millorar el 0,1537 actual»: 0,1537 és del 29-10 i des del 16-11
> servim H4b, que al mateix test fa 0,140 — un model que passés aquesta porta seria pitjor que el
> que tenim. (El bucle que corre no la fa servir: `tools/lm/cercle_virtuos.py` compara contra el
> model d'ara i no té cap llindar absolut. És el text que està malament, no la màquina.) El que hi
> ha aquí sota és el que es va creure.

1. **OCR tancat** (peó `ocr-tipografia`, en curs). La lletra dels subtítols és fixa: identificar-la,
   generar línies sintètiques amb aquesta lletra, entrenar un lector per a cada escriptura i mesurar
   sobre 200 franges reals transcrites a mà. Porta: CER < 1 % en totes dues línies. Comprovació
   creuada gratuïta: tifinag llegit → àrab (traductor) contra l'àrab llegit; les rèpliques on no
   casen van a revisió, no al train.
2. **Segmentació i triples.** Un fotograma per segon, lectura, agrupació dels segons que diuen el
   mateix (el mètode de Baba Ali), tall de so per rèplica, i una fila per rèplica: vídeo, segon
   d'inici i fi, tifinag, àrab, acord de l'OCR, varietat de la sèrie. Es guarda al disc i al dataset
   privat d'HF; mai a l'app.
3. **Àrab → català de confiança.** Dos models (Qwen i DeepSeek) tradueixen; el tercer només si no hi
   ha acord; chrF ≥ 0,9 entre ells = confirmada (la cadena dels auditors de sempre). Mostra mensual
   de 50 mirada per una persona. Això dona el català de cada rèplica, marcat com a traducció de màquina
   d'una traducció humana.
4. **Varietat.** Per sèrie, no per rèplica: proporció de formes compartides amb els nostres parlants
   d'Aït Mraw i de Beni Mellal contra el Souss, i la resposta de la SNRT sobre on es va rodar cada
   sèrie. Només les sèries de l'Alt Atles central entren al train de la varietat; la resta queda
   etiquetada per a més endavant.
5. **Traductor amb pivot.** Tres candidats sobre les mateixes 60 frases i el test-dins: (a) la v3
   actual, directa; (b) NLLB afinat amazic → àrab amb les parelles humanes, i àrab → català amb el
   model gran; (c) NLLB afinat amazic → català amb el català de la fase 3 (destil·lació). Es queda el
   que guanyi amb interval; la vara de soroll és 0,005.
6. **Transcriptor.** Afinar MMS (o Whisper) amb so ↔ tifinag de les sèries de l'Alt Atles, mesurar
   sobre el test net de CV zgh (256 talls), test-fora i els deu minuts de veritat humana quan hi
   siguin. Porta: millorar el 0,1537 actual sense empitjorar test-fora.

## La fàbrica: com corre sense Claude

- **On:** a l'ECS (forja.ma no bloqueja la IP; YouTube sí, així que els capítols de YouTube els baixa
  el PC amb `engega_fora.ps1` i puja només el vídeo a 720p). Tot sota `tmux`, amb `nohup`, registre
  per etapa.
- **Què:** una carpeta `tools/snrt/fabrica/` amb una etapa per guió, totes **reprenibles per id**
  (si cau a mig camí, torna a engegar i continua): `01_baixa.py` (llista de YouTube o pàgina de
  replay → mp4), `02_llegeix.py` (franges → tifinag i àrab, amb el lector de la fase 1 i el vot entre
  fotogrames), `03_talla.py` (rèpliques i so), `04_tradueix.py` (Qwen + DeepSeek + tercer),
  `05_varietat.py`, `06_publica.py` (dataset privat d'HF i `INFORME.md` amb els comptes del dia),
  `nit.py` que les encadena. Cada etapa escriu el seu `estat.json` amb comptes, i **cap etapa escriu
  a producció**.
- **Qui pensa:** Qwen-VL per llegir on el lector sintètic dubta, Qwen i DeepSeek per traduir i auditar,
  qwen-max com a jutge de varietat i de «el subtítol resumeix o és literal». Les claus al `.env` de
  l'ECS, mai al repositori.
- **Portes numèriques, no opinions:** una rèplica entra al train si l'OCR dels dos costats té acord
  entre fotogrames ≥ 3, la comprovació creuada tifinag → àrab dona chrF ≥ 0,5, i el català té acord
  entre els dos models ≥ 0,9. El que no passa queda al disc amb el motiu.
- **El paper de Claude:** llegir l'`INFORME.md` de cada nit (comptes, mostres a ull, portes
  tancades), decidir quines sèries entren, quan es reentrena, i què es canvia; i revisar les
  pull requests de la fàbrica. Res de feina manual de rèplica en rèplica.

## El que cal abans de construir-la

L'informe d'«Illy» (capítol 1) i el de l'entrevista del replay: nombre de rèpliques per hora, acord
de l'OCR, chrF entre el català de l'àrab i el del tifinag, i la primera mesura de varietat. Amb
aquests números es dimensiona la fàbrica i s'escriu la primera versió.
