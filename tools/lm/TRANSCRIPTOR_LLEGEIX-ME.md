# Bucle del transcriptor (#601, §6.5)

Afina l'adaptador MMS `shi` (H4b, el que serveix al Space) amb parelles **so ↔ tifinag** de Tamazight TV (SNRT)
que la fàbrica de l'ECS ja ha llegit, i **només l'accepta si guanya la regla**. Material de **recerca**: el model
entrenat amb so de la SNRT no es publica ni es desplega al Space ni a Render (`docs/PERMISOS.md`, 17-11-2026); es
queda a Kaggle privat.

Fitxers: `tools/lm/transcriptor_bucle.py` (el bucle, només biblioteca estàndard, corre a l'ECS),
`tools/lm/kaggle/transcriptor_snrt.py` (el nucli de Kaggle), proves a `backend/tests/test_transcriptor_bucle.py`.

## Ús (a l'ECS, des d'una còpia del repositori; el CLI de Kaggle és a `/root/venv-kaggle`, token a `~/.kaggle/access_token`)
```
python3 tools/lm/transcriptor_bucle.py construeix            # dataset + partició congelada a /root/transcriptor
python3 tools/lm/transcriptor_bucle.py puja                  # dataset PRIVAT josepabloucr/snrt-transcriptor
python3 tools/lm/transcriptor_bucle.py llanca --recepta A    # A = només SNRT · B = SNRT + dades d'H4b
python3 tools/lm/transcriptor_bucle.py espera --recepta A    # avisa si no comença en 90 min; baixa la sortida
python3 tools/lm/transcriptor_bucle.py avalua --sortides /root/transcriptor/sortida_A/snrt_A_sortides.json
python3 tools/lm/transcriptor_bucle.py cicle --recepta A     # tot, i apunta a registre.jsonl
```
Reprenible: cada subordre deixa un fitxer (`ds/rows.json`, `particio.json`, `sortida_X/`, `veredicte_X.json`).

## Què fa cada pas
1. **Dades** (`construeix`). Per cada capítol amb 02 i 03 fets sense error: rèpliques **aptes per a l'ASR** (§5):
   no crèdit, tifinag amb confiança ≥ 0,85 i ≤ 2 glifs dubtosos, durada ≥ 0,8 s, 2–30 paraules, i el wav **hi és, dura
   durada + 0,5 s i no és anterior al final de la 02**. Aquest darrer control importa: la 03 és reprenible per id i no refà
   els talls que ja hi són, així que quan la 02 es refà queden **talls vells sota els mateixos ids** (vist el 17/18-11: 486 de
   700 files d'un capítol). Un capítol amb menys de 100 aptes queda fora.
2. **Partició per capítol, mai per línia** (llavor 1114): ~10 % dels capítols sencers a test, ~5 % a dev (almenys 1 i 1),
   la resta a train. La llista d'ids es congela a `particio.json` amb el seu hash. Es treuen del train (i del dev) les
   rèpliques amb el mateix text ric que el test o el dev.
3. **Objectiu**: tifinag → llatí **ric sense plegar** (ġ ε ḥ ḍ ṭ ṣ ẓ es conserven; regla `tachelhit-asr-plegat-esborrava-lletres`),
   la mateixa `rica()` que H4/H4b/H5.
4. **Nucli** (`transcriptor_snrt.py`, T4): mesura l'adaptador actual («abans»); filtra el train i el dev amb **CER ≤ 0,4**
   de l'adaptador actual contra el tifinag (§5: treu els subtítols que resumeixen en lloc de transcriure); treu del train
   tot el que coincideix per text amb qualsevol prova; entrena (només adaptadors, 4 èpoques, 1e-4, millor època per dev) i
   torna a mesurar sobre els mateixos talls («després»). Proves: **cv-zgh-test** (256 clips), **test-fora**, **tfa-226**,
   **zouhir-tests**, **snrt-retingut** (capítols sencers fora d'entrenament, **sense** el filtre CER perquè el filtre és de
   l'ASR actual i afavoriria el test).
5. **Regla** (`avalua`, bootstrap aparellat 2.000 × llavor 1114): s'adopta **només si** CV zgh baixa amb IC (límit alt de
   Δ < 0), **i** test-fora no empitjora més de 0,005, **i** els capítols retinguts no empitjoren (salvaguarda del pla). Si
   falta cap de les tres proves, no s'adopta.
6. **Límits** (PLA_BUCLE_TRANSCRIPTOR): `cicle` es nega a córrer si els dos darrers cicles no han millorat (`--forca` ho
   salta); el supervisor fixa la cadència i activa l'etapa (`config.json → transcriptor.actiu`).

## Recepta A i B
A = només SNRT. B = SNRT + els rètols nets de Zouhir i l'Alcorà d'H4b. Dos nuclis (`snrt-transcriptor-a`,
`snrt-transcriptor-b`); el compte té màxim 2 sessions de GPU alhora.

## Mai
- Publicar o desplegar res: ni Space d'ASR, ni Render, ni dataset públic (el dataset és privat per omissió i el guió no
  fa servir mai `--public`).
- Posar claus al repositori: el token de Kaggle és a l'ECS i el nucli no en porta cap.
- Entrenar amb talls que no hagin passat el control de wav vell.
