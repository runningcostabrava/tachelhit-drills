# La fàbrica de la SNRT: de l'mp4 a les rèpliques llegides, tallades i traduïdes (#601)

Permís de la SNRT del 17-11-2026 (`docs/PERMISOS.md`): recerca per al traductor i el transcriptor, **no
republicar**. Tot el que surt d'aquí és train/test; cap etapa escriu a producció ni fa cap drill.

Una carpeta per vídeo, amb el `.mp4` a dins. Les etapes hi deixen tot el que produeixen (rutes relatives)
i `estat.json` porta els comptes de cada una. Totes **reprenen**: si cau a mig camí, es torna a engegar i
continua on era (l'àrab per segon, els talls per fitxer, les traduccions per subtítol).

| etapa | què fa | surt |
|---|---|---|
| 01 (ja existeix) | baixar: `python -m yt_dlp` per a YouTube (des del PC: l'ECS té la IP bloquejada), `../baixa_replay.py` per al replay de snrt.ma (va bé des de l'ECS) | `<carpeta>/<nom>.mp4` |
| `02_llegeix.py` | franges d'un fotograma per segon; l'àrab amb el model de visió de Model Studio i vot entre fotogrames; el tifinag amb `lector_tifinag.py` al fotograma del mig de cada subtítol | `franges/`, `lectures.jsonl`, `linies_arab.json`, `tif/`, `tifinag.json` |
| `03_talla.py` | la taula de subtítols (amb `credits`) i els talls de so a 16 kHz | `audio16k.wav`, `subtitols.jsonl`, `talls/` |
| `04_tradueix.py` | àrab → català amb dos models (Qwen de Model Studio + DeepSeek) i l'acord entre ells; tifinag → català amb el Space NLLB; chrF | `traduccions.jsonl` |
| `05_informe.py` | els comptes sobre el diàleg, les parelles útils per a entrenar, la varietat (si hi ha catàleg) i la mostra a ull | `numeros.json`, `INFORME.md`, `mostra/` |
| `nit.py` | encadena 02 → 05 per a una llista de carpetes, salta el que ja és fet | `nit.log` |

```sh
python -X utf8 tools/snrt/fabrica/nit.py /dades/tamazight_tv/illy_01 /dades/tamazight_tv/illy_02 --credits 150,1700
python -X utf8 tools/snrt/fabrica/nit.py --arrel /dades/tamazight_tv/entrevistes
```

Cada etapa també va sola: `python -X utf8 tools/snrt/fabrica/02_llegeix.py <carpeta> --fils 6`. Opcions que
importen: `02 --video-tifinag <1080p.mp4>` (el tifinag llegit a 1080p és clarament millor que a 720p: a 20 px
ⵎ↔ⴹ es confonen; l'àrab va bé a 720p), `02 --rellotge tifinag` (vegeu «Cost»), `03 --credits A,B` (títols
del principi i del final, que no són diàleg; a «Illy» 150,1700), `04 --model2 cap` (sense DeepSeek),
`05 --mostra 20 --llavor 1114`.

## Què cal

- Python 3.10 o més, amb el que ja té el venv del backend: `numpy`, `scipy`, `pillow`, `requests`,
  `python-dotenv`, `gradio_client`. Res més. I `ffmpeg`/`ffprobe` al PATH.
- El repositori sencer (el lector de tifinag fa servir `tools/ocr_tifinag/glifs.py` i `plantilles.npz`; la
  varietat, `backend/transliteration.py`).
- Les claus en un `.env`: al PC es llegeix `backend/.env`; a l'ECS, `tools/snrt/fabrica/.env` (o el que digui
  `TD_ENV`). Mai al repositori.

```
DASHSCOPE_API_KEY=sk-ws-...          # Model Studio: visió (qwen3-vl-plus) i traducció (qwen3.8-max)
DASHSCOPE_BASE_URL=https://ws-....ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1   # el de l'espai de treball
DEEPSEEK_API_KEY=sk-...              # el segon traductor de l'àrab (sense, 04 en fa servir un de sol)
TD_SPACE_NLLB=josepabloucr/Finetuned-Quantized-NLLB   # opcional
TD_CATALEG=/dades/cataleg_prod.json  # opcional: l'estimació de varietat de 05
```

## A l'ECS

```sh
ssh -i backend/tach.pem root@<IP>
git clone <repositori> tachelhit-drills && cd tachelhit-drills
/opt/venv/bin/pip install numpy scipy pillow requests python-dotenv gradio_client
cp /on/sigui/.env tools/snrt/fabrica/.env
mkdir -p /dades/tamazight_tv/illy_01     # un mp4 per carpeta (scp des del PC per als de YouTube)
tmux new -s nit
/opt/venv/bin/python -X utf8 tools/snrt/fabrica/nit.py --arrel /dades/tamazight_tv --fils 6
```

`nit.log` a l'arrel i `fabrica.log` a cada carpeta diuen on és. Si una etapa falla, la nit apunta l'error i passa
a la carpeta següent; en tornar-la a engegar, reprèn.

## Cost i temps (mesurats a «Illy» cap. 1, 30 min, 1080p per al tifinag)

| | |
|---|---|
| franges | 1.820, 1 min |
| àrab, 1 fotograma per segon | 1.820 crides, **313 k fitxes** de visió (≈172 per franja), 12 min amb 6 fils |
| tifinag (plantilles, local) | 3 min, gratuït |
| talls | 1 min |
| traduccions | ≈ 100 k fitxes de text (dos models), 9 min; el Space és gratuït |
| total per capítol | ≈ 30 min de màquina |

La quota gratuïta de Model Studio és d'1 M de fitxes per model: a 1 fotograma per segon, **tres capítols**.
Les franges idèntiques a l'anterior no s'envien (a «Illy», un 5 %; en un plató quiet, més). `--rellotge tifinag`
fa servir el segmentador de glifs del tifinag (gratuït) com a rellotge: només envia l'àrab d'un fotograma per
tram de glifs iguals (i un segon per confirmar quan el tram dura 3 s o més). Mesurat sobre «Illy» contra les
1.820 lectures: 1.013 crides en lloc de 1.820 (−44 %), 2 canvis de text de diàleg perduts de 650 (els altres
17 són als crèdits). És la manera de fer-ho a escala quan la quota s'acabi.

## Els números que diu l'informe, i què volen dir

- **Acord de l'OCR àrab**: de quants fotogrames surt cada subtítol i quants diuen el mateix. A «Illy», el 80 %
  dels vistos en ≥ 2 fotogrames són unànimes; a ull, 18 de 20 exactes.
- **Confiança del tifinag**: correlació mitjana amb les plantilles; ≥ 0,85 és «segur». A «Illy», 88 % dels
  glifs; a ull, 18 de 20 subtítols exactes.
- **Acord àrab → català** (chrF entre Qwen i DeepSeek): 0,62 a «Illy»; on és baix hi ha un error d'OCR o un
  nom propi. És la porta per al català de referència.
- **chrF tifinag → català contra àrab → català**: 0,29 a «Illy». Mesura el traductor amazic (i que les dues
  línies no són traducció literal), no l'OCR: amb les dues lectures bones surten 0,15 sovint.
- **Parelles per a entrenar**: la taula de l'informe per llindar. Proposta: train = tifinag ≥ 0,85 amb el
  català de l'àrab; test = acord ≥ 0,5 entre els dos catalans.

## El lector de tifinag és una funció

`lector_tifinag.llegeix_bandes(imatges)` rep les bandes de tot el vídeo i torna, per a cada una,
`{"tifinag", "glifs", "n_glifs", "n_dubtosos", "conf_mitjana", "conf_min"}`. Avui és el lector per plantilles
d'aslmdtv (la lletra de la SNRT és la mateixa família IRCAM); quan hi hagi el lector entrenat amb el sintètic
del peó de tipografia, es canvia aquest mòdul i l'etapa 02 no se n'assabenta.

## D'on ve

Dels guions de la prova de mesura d'«Illy» (`Veus-tachelhit\_escoltats\tamazight_tv\illy_01\guions\`, 17-11),
que al seu torn adapten `tools/notebooks/llegeix_episodi_arab.py` (Baba Ali), `tools/ocr_tifinag/` (aslmdtv) i
`tools/tutlait/tradueix_ar_ca.py`. Trampes apreses: el fotograma k del `fps=1` és l'instant k−0,5; cal treure
les vocals curtes de l'àrab abans d'ajuntar segons; el «:» del lector de plantilles és la ⵓ; el senyal petit
darrere ⴳ/ⴽ és la ⵯ; el client `android` del yt-dlp només donava 360p (SABR), el per defecte dona 136+140.
