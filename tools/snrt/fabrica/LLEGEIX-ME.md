# La fàbrica de Tamazight TV (#601): de l'mp4 a les rèpliques llegides, tallades i traduïdes

Segueix `docs/recerca/tamazight-tv-fabrica-especificacio.md` (l'«especificació»); el pla és a
`docs/recerca/tamazight-tv-pla.md`. Permís de la SNRT del 17-11-2026 (`docs/PERMISOS.md`): recerca per al traductor
i el transcriptor, **no republicar**. Cap etapa escriu a producció ni fa cap drill.

## Carpetes (§2)

Arrel de dades `TD_TV` (al PC `C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\`, a l'ECS `~/tamazight_tv/`).
Un capítol és `TD_TV/<slug>/` amb `video.mp4` (720p amb so) i, si pot ser, `video_1080.mp4` (per al tifinag). Les
etapes hi deixen `franges/`, `lectures.jsonl`, `tif/`, `subtitols.jsonl` (§3.3), `talls/<id>.wav`, `numeros.json`,
`INFORME.md`, `mostra/`, `estat.json` (per etapa: `inici`, `fi`, `comptes`, `versio`, `error`) i `fabrica.log`.
L'única cosa fora de la carpeta és una línia a `TD_TV/_informes/AAAA-MM-DD.md`.

## Etapes (§4)

| etapa | què fa | reprèn per |
|---|---|---|
| 01 (dins `nit.py`) | `../baixa_replay.py` (replay; va bé des de l'ECS) o `yt-dlp` del venv (YouTube; només des del PC) → `video.mp4`, i `video_1080.mp4` si n'hi ha | el vídeo que ja hi és |
| `02_llegeix.py` | franges 1 fps · **comprovació de la geometria** (10 fotogrames; s'atura amb error si < 3 tenen les dues línies on toca) · **rellotge pel tifinag** (segmentador de glifs, gratuït) → trams · **un fotograma d'àrab per tram** (el del mig; un segon si la lectura és buida, < 6 caràcters o errònia) amb `qwen3-vl-plus` · franges idèntiques saltades · tifinag al fotograma del mig amb `lector_tifinag.llegeix_bandes` (sobre `video_1080.mp4` si hi és) · `credits` (> 3 línies de text o text idèntic repetit > 20 s) | segon (`lectures.jsonl`) i retall (`tif/`) |
| `03_talla.py` | `talls/<id>.wav` mono 16 kHz, t_ini − 0,25 … t_fi + 0,25, dins el vídeo; els crèdits no | id (el wav que ja hi és) |
| `04_tradueix.py` | àrab → català amb `qwen3.8-max` (a) i `deepseek-chat` (b), `chrf_ab`; 0,3 ≤ chrf_ab < 0,5 → tercer `qwen4-max` (Gemini no té crèdit) i es queda el que hi coincideix ≥ 0,5 («tercer»); ≥ 0,5 → «confirmat»; si no, «descartat». Tifinag → català amb el Space només per a `chrf_tif_ar` | id (una fila amb `catala_estat` i el mateix àrab/tifinag no es repeteix) |
| `05_informe.py` | `numeros.json`, `INFORME.md` (plantilla §7), portes §5, varietat §6.1 (punts 1–3, si `TD_CATALEG`), 20 a ull, línia a `_informes/` | sempre es refà (és barat) |
| `nit.py` | `TD_TV/cataleg/capitols.jsonl` ordenat per `prioritat` i `mena`; per a cada pendent 01 → 05; marca `estat` i `nota` al catàleg; `TD_TV/nit.log` | etapa feta = `fi` sense `error` |

```sh
python -X utf8 tools/snrt/fabrica/nit.py                        # tot el catàleg pendent
python -X utf8 tools/snrt/fabrica/nit.py --nomes <slug> --fils 6  # un capítol
python -X utf8 tools/snrt/fabrica/nit.py <carpeta> [<carpeta>]    # sense catàleg: 02 → 05 d'aquestes carpetes
python -X utf8 tools/snrt/fabrica/02_llegeix.py <carpeta> --un-per-segon   # el mètode car de la prova d'«Illy»
```

El catàleg real del peó `snrt-cataleg` (`slug_forja`, `url_snrt`, `youtube_id`, `cami_per_omissio`,
`qualitats_replay`) es llegeix tal qual: `slug` = `slug_forja`, `url` = `url_snrt`, `font` = `cami_per_omissio`;
`mena` = «entrevista» per a Tadfi n Tskla; `prioritat` 9 si no hi és. Els camps de §3.1 també s'accepten.

## Què cal

Python ≥ 3.10 amb el venv del backend (`numpy`, `scipy`, `pillow`, `requests`, `python-dotenv`, `gradio_client`),
`ffmpeg`/`ffprobe`, el repositori sencer (`tools/ocr_tifinag/` per al lector de plantilles, `backend/transliteration.py`
per a la varietat), i les claus en un `.env` (al PC `backend/.env`; a l'ECS `~/.env` o `tools/snrt/fabrica/.env`;
`TD_ENV` per dir-ne un altre):

```
DASHSCOPE_API_KEY=sk-ws-...       # Model Studio: visió (qwen3-vl-plus), text (qwen3.8-max, qwen4-max)
DASHSCOPE_BASE_URL=https://ws-....ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
DEEPSEEK_API_KEY=sk-...           # model b
TD_TV=/root/tamazight_tv          # opcional (per omissió, el del PC o ~/tamazight_tv)
TD_CATALEG=/root/cataleg_prod.json  # opcional: varietat (§6.1); al PC, Veus-tachelhit\_escoltats\traduccions\auditors\cataleg_prod.json
TD_SPACE_NLLB=josepabloucr/Finetuned-Quantized-NLLB   # opcional
```

### A l'ECS

```sh
ssh -i backend/tach.pem root@<IP>
git clone <repositori> tachelhit-drills && cd tachelhit-drills
/opt/venv/bin/pip install numpy scipy pillow requests python-dotenv gradio_client
cp /on/sigui/.env ~/.env
mkdir -p ~/tamazight_tv/cataleg && scp capitols.jsonl root@<IP>:~/tamazight_tv/cataleg/
tmux new -s nit
/opt/venv/bin/python -X utf8 tools/snrt/fabrica/nit.py --fils 6
```

Els capítols de YouTube no es poden baixar des de l'ECS: el PC els baixa (`nit.py --nomes <slug>` fins a 01, o
`yt-dlp` a mà) i els puja amb `scp` a `~/tamazight_tv/<slug>/video.mp4`; la nit els troba baixats.

## El cost, mesurat (l'únic que tenim per a la visió és la quota gratuïta: 1 M de fitxes per model)

| | Illy cap. 1 (30 min, sèrie) | entrevista Tadfi (55 min) |
|---|---|---|
| rèpliques de diàleg | 306 | 1.173 |
| 1 fotograma per segon (prova) | 1.820 crides, 313 k fitxes | 2.837 crides, 511 k |
| rellotge pel tifinag, 1 fotograma per tram | 1.013 crides (−44 %) | 2.183 crides (−23 %), simulat sobre les lectures d'1 fps: mateix text en 919 + 91 de 1.249, 45 diferents, 25 de diàleg perduts, temps a ±1 s en 1.003 de 1.055 |

El mínim és **una crida per rèplica** (≈ 172 fitxes): per a una entrevista, ≈ 215 k per hora encara que el rellotge
fos perfecte (avui parteix 1,7–2,4 trams per rèplica). Amb Qwen-VL el milió dona per a **5–7 hores d'entrevista**,
no per a 18 capítols. El camí per no pagar és el lector d'àrab propi (§6.3). Els números de la prova amb els dos
mètodes són a `Veus-tachelhit\_escoltats\tamazight_tv\replay\tadfi_goughelt\INFORME.md`. Temps de màquina: ≈ 1 h per
hora de vídeo, la meitat a l'API de visió (6 fils).

## El que NO quadra amb l'especificació (perquè el director ho decideixi)

- **Porta de l'ASR** (§5, CER ≤ 0,4 de l'ASR actual contra el tifinag): no es calcula. Cal dir quin transcriptor i on
  corre (el Space, l'ECS per CPU); 05 compta només la part de durada ≥ 0,8 s i escriu «no mesurat».
- **Tercer model**: `gemini-2.5-flash` no té crèdit (24-10); s'usa `qwen4-max` directament, com diu §4.
- **Varietat §6.1**: només els punts 1–3 (formes i paraules gramaticals contra tres referències, amb el control); el
  punt 4 (escoltar 30 rèpliques amb l'ASR) no es fa. `varietat_capitol` queda «desconeguda» fins que el director la posi
  (es copia del catàleg si hi ha el camp `varietat`).
- **Crèdits**: «més de 3 línies» es compta sobre el fotograma sencer en gris i petit (grups de files molt clares);
  «text idèntic repetit > 20 s» sobre l'àrab exacte. Les targetes del títol d'un programa (que no tenen tifinag) cauen
  soles perquè el rellotge del tifinag no les veu.
- **06 publica** (dataset privat d'HF, setmanal): no és aquí.
- **Ids**: `<slug>_<k:04d>` surten d'un càlcul determinista sobre `lectures.jsonl`; si es tornés a llegir un capítol
  des de zero amb un lector d'àrab diferent, els `k` podrien canviar. Mentre es reprengui amb les mateixes lectures,
  no canvien.
- `tifinag_glifs`, `linies_text`, `arab_traduit`, `tifinag_traduit`, `catala_c`, `error_traduccio` són camps de més a
  `subtitols.jsonl` (serveixen per reprendre i per comptar); els de §3.3 hi són tots.

## El lector de tifinag és una funció

`lector_tifinag.llegeix_bandes(imatges)` rep les bandes de tot el capítol i torna, per a cada una, `{"tifinag", "glifs",
"n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"}`; `lector_tifinag.NOM` (`plantilles-segmentador-v1`) és el que va a
`tifinag_lector`. Avui és el segmentador nou + classificador de plantilles de Tifinaghe-Ircam i xifres (`tifinag_segmenta.py`,
`tifinag_plantilles.py` i `tifinag_plantilles.npz`; res entrenat): CER 0,0051 sobre les 52 línies de «Illy» transcrites a mà
(`prova_lector_tifinag.py <carpeta_tipografia>` ho reprodueix), 0,0073 amb les mateixes línies baixades a 720p (simulat; el 720p real
encara no s'ha mesurat). 01 segueix baixant el 1080p quan n'hi ha. `conf` és `min(1, IoU/0,75)` perquè els llindars de §5 (0,85)
segueixin volent dir «dubtós»; no és una probabilitat. El lector per plantilles d'aslmdtv (`tools/ocr_tifinag/`) ja no s'hi crida.

## D'on ve

Dels guions de la prova de mesura d'«Illy» (`Veus-tachelhit\_escoltats\tamazight_tv\illy_01\guions\`, 17-11), que
adapten `tools/notebooks/llegeix_episodi_arab.py` (Baba Ali), `tools/ocr_tifinag/` (aslmdtv) i
`tools/tutlait/tradueix_ar_ca.py`. Trampes apreses: el fotograma k del `fps=1` és l'instant k−0,5; treure les vocals
curtes de l'àrab abans d'ajuntar segons; el «:» del lector de plantilles és la ⵓ; el senyal petit darrere ⴳ/ⴽ és ⵯ;
el logotip d'un programa dins la franja surt com a lletres de confiança baixa (es descarta per paraula); el client
`android` del yt-dlp només donava 360p (SABR), el per defecte dona 136+140.
