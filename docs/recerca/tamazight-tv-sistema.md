# El sistema autònom de Tamazight TV: com funciona, on és tot i com controlar-lo (17-11-2026)

Document de referència (llegeix-lo primer). Descriu el sistema que converteix els vídeos de la SNRT en parelles per
millorar els lectors (OCR de tifinag i d'àrab), el transcriptor de veu i el traductor. Escrit per al propietari (en Pablo)
i per a qualsevol peó o sessió nova. Detalls tècnics: `tamazight-tv-fabrica-especificacio.md`; pla general:
`tamazight-tv-pla.md`; permís: `docs/PERMISOS.md` (**SNRT: recerca sí, republicar no**).

## 1. L'objectiu, en una frase

Fer servir els subtítols cremats de Tamazight TV (tifinag a dalt, àrab a sota) com a **font gegant de parelles
so ↔ tifinag ↔ àrab ↔ català**, per aconseguir que els nostres models entenguin i tradueixin l'amazic, amb el màxim d'autonomia.

## 2. El flux, de punta a punta

```
 SNRT (YouTube / replay forja.ma)
        │ 1. BAIXA        (replay des de l'ECS; YouTube des del PC)
        ▼
   vídeo 1080p
        │ 2. LLEGEIX      rellotge pel tifinag → lector de TIFINAG (plantilles IRCAM, CER ≈0,1–0,2 %)
        │                 + lector d'ÀRAB propi (CRNN, CER ≈0,6–0,7 %, sense models de pagament)
        ▼
   rèpliques: [inici, fi, tifinag, àrab]
        │ 3. TALLA        un wav de 16 kHz per rèplica
        │ 4. TRADUEIX     àrab → català amb 2 models (Qwen + DeepSeek) i un tercer (Gemini) si discrepen
        ▼
   subtitols.jsonl   (una fila per rèplica, esquema §3.3 de l'especificació)
        │ 5. PORTES       numèriques (§5): apta per al traductor? apta per a l'ASR?
        ▼
   conjunts d'entrenament  ──►  transcriptor (so↔tifinag)  ·  traductor (tifinag/àrab→català)
        │                       ·  taula d'estandardització (norma ↔ dialecte)  ·  lectors (ajust fi)
        ▼
   informe diari  +  còpia diària al dataset PRIVAT d'HF
```

## 3. Les peces i on són

| peça | què fa | on viu |
|---|---|---|
| **Fàbrica** (`tools/snrt/fabrica/`: `nit.py`, `02_llegeix`, `03_talla`, `04_tradueix`, `05_informe`) | processa un capítol de cap a cap, reprenible per id | codi al repositori (main); corre a l'**ECS** (`/root/snrt`, `tmux nit`) |
| **Lector de tifinag** | segmentador (components connexos, vora fosca) + classificació per plantilles de la font IRCAM | `tools/snrt/fabrica/`; públic: `huggingface.co/josepabloucr/tifinagh-ocr-plantilles` (sense res de la SNRT) |
| **Lector d'àrab** | CRNN de 4,2 M (CPU), retall x110–1560 per excloure el logo | `tipografia\arab\` (PC); pesos `…\tamazight_tv\models\lector_arab_crnn_v4.pt` i `/root/tamazight_tv/models/` |
| **Supervisor** (`/root/supervisor/`) | guió (sense IA): cron cada 15 min, reengega la fàbrica, vigila el disc i els límits de cost, informe diari, còpia diària | ECS; còpia a `…\tamazight_tv\_supervisor\` |
| **Bucle de millora de l'àrab** (`bucle_arab.py`) | reentrena el lector a Kaggle amb línies reals i l'accepta només per regla numèrica | ECS; **EN PAUSA** (vegeu §6) |
| **Director** (Claude) | cada ~2 h llegeix informes, reengega, aplica portes, fusiona PR, avisa si hi ha alarma | sessió de Claude (cron de sessió, vegeu §8) |
| **Dades** | vídeos (temporals), `subtitols.jsonl`, talls, informes | ECS `/root/tamazight_tv/`; PC `C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\`; còpia privada HF `josepabloucr/tamazight-tv-privat` |

## 4. Com mirar com va (sense preguntar a ningú)

1. **L'informe de direcció (la manera fàcil):** `C:\Users\josep\Veus-tachelhit\_escoltats\tamazight_tv\_informes\direccio.md` (una entrada cada ~2 h) i `ALERTA.md` (només si hi ha problema).
2. **Estat de la fàbrica:** `/root/tamazight_tv/ESTAT.md` a l'ECS (es refà cada 5 min), còpia a `…\tamazight_tv\ecs\ESTAT.md`. El supervisor escriu `_informes/AAAA-MM-DD_supervisor.md`.
3. **A l'ECS:** `ssh -i backend/tach.pem root@47.236.101.200`, `tmux ls`, `tail /root/supervisor/log/cron.log`, `df -h /`.
4. **Kaggle:** `python -m kaggle kernels status josepabloucr/<nucli>` (carregant `backend/.env`).
5. **Capítols fets:** `/root/tamazight_tv/cataleg/capitols.jsonl` (camp `estat`: `pendent`, `fet-sense-arab`, `fet`).

## 5. Les portes: què decideix si una cosa entra o no (números, no opinions)

- **Una rèplica és apta per al traductor** si: no és crèdit, tifinag amb confiança ≥ 0,85 i ≤ 2 glifs dubtosos, àrab llegit sense `arab_dubtos`, català amb acord entre els dos models (chrF ≥ 0,5) o decidit pel tercer, i 2–30 paraules. **No** es filtra pel chrF tifinag→català (mesura el traductor, no la dada).
- **Apta per a l'ASR** si a més dura ≥ 0,8 s i el transcriptor actual hi té CER ≤ 0,4 contra el tifinag.
- **Un lector nou substitueix l'actual** només si CER ≤ 0,02 sobre línies reals de veritat, no empitjora cap parella de confusió, i es va mesurar en un capítol que no ha vist.
- **Un model del traductor o del transcriptor** només es desplega si guanya amb interval de confiança sobre les mateixes 60 frases i no empitjora el test (vara del soroll: 0,005).
- Cap model es **desplega a producció** sense decisió d'en Pablo.

## 6. Què està en marxa, què està en pausa i per què

| | estat |
|---|---|
| Fàbrica sense àrab, 31 capítols de «Tadfi n Tskla» | **en marxa a l'ECS** (≈ 27 min per capítol) |
| Canvi a fàbrica **amb àrab propi + traducció** | **ordenat**: s'instal·la quan acabi el capítol en curs; reprocessa els 5 ja fets |
| Bucle de millora de l'àrab | **EN PAUSA** a propòsit: tota la veritat d'àrab és de dos programes on el lector ja s'ha ajustat, i entrenar-hi més només memoritzaria; es reactiva quan hi hagi àrab llegit d'un altre programa |
| Bucle del transcriptor | especificat (`_supervisor\PLA_BUCLE_TRANSCRIPTOR.md`), no construït; no necessita àrab |
| Bucle del traductor | especificat (`_supervisor\PLA_BUCLE_TRADUCTOR.md`); necessita parelles amb català confirmat |
| Estandardització norma ↔ dialecte | pla escrit (`tifinag-estandard-pla-d-analisi.md`); s'activa amb un transcriptor millor |
| Altres programes de la cadena / ordre invertit de línies | detecció d'ordre feta (#671), no provada amb un vídeo invertit real |

## 7. Costos i límits (decidits per en Pablo, 17-11-2026)

DeepSeek **4 €** · Gemini **2 €** (només com a tercer auditor) · Qwen només quota gratuïta (la visió, esgotada: no s'usa) ·
GPU Kaggle ~30 h/setmana (bucle: màx. 3 cicles/dia i 12 h/setmana) · ECS: prova gratuïta **fins al 16-02-2027** (copiar-ne dades i models abans).
El supervisor atura la traducció amb marge (3,6 $ / 1,8 $) i la fàbrica continua sense català.

## 8. Què pot fallar i com s'ha protegit

| risc | protecció |
|---|---|
| Es cau la fàbrica | supervisor reengega (cron 15 min + `@reboot`), màx. reinicis/dia |
| Es plena el disc | neteja automàtica del que ja s'ha processat; alarma <10 GB |
| Es perd l'ECS | còpia diària dels resultats al dataset privat d'HF |
| Un model nou empitjora | només s'accepta per regla numèrica sobre línies congelades |
| Canvi de lletra, de fons o d'ordre de línies | portes de confiança + `arab_dubtos`/glifs dubtosos; la veritat humana de cada disseny nou és l'única cosa no automatitzable |
| Es gasta massa | límits de cost amb comptador a l'informe diari |
| La sessió de Claude s'acaba | l'ECS i Kaggle continuen; el director (cron de sessió) cau als **7 dies** o en tancar la sessió: l'alternativa duradora és una **rutina de Claude Code al núvol** (cal que la creï en Pablo) |

## 9. Com aturar-ho tot

`ssh … root@47.236.101.200` → `python3 /root/supervisor/supervisor.py atura` (atura el supervisor i la fàbrica), o `tmux kill-session -t nit`.
Per aturar el bucle d'àrab: `arab.actiu=false` a `/root/supervisor/config.json`.

## 10. Què només pot fer una persona

- Donar **veritat humana** de cada disseny de subtítols nou (fulls curts amb teclat: `full_net*_*.html`, `revisio_*.html`).
- Decidir si un lector/model nou **substitueix** l'actual o es **desplega**.
- Decidir **publicacions** (res de la SNRT es publica) i **permisos** (`docs/PERMISOS.md`).
- Renovar l'ECS i controlar els costos de pagament.

## 11. Números vigents (17-11-2026)

| | valor |
|---|---|
| OCR tifinag (100 línies no vistes) | CER 0,0009; 50 línies netes ≈ 0,0019 |
| OCR àrab (100 + 100 línies, 2 capítols) | CER 0,0074 i 0,0059 (veritat del peó; mateixa tipografia) |
| Fàbrica, primer capítol (Hasnae Fatni, 52 min) | 877 rèpliques, 580 aptes so↔tifinag (76 %), 26 min a l'ECS |
| Traductor (v3 al Space) | chrF 0,62 sobre les 60 frases |
| Transcriptor | CER ≈ 0,15 (test net CV zgh) |

Relacionats: `ocr-tifinag-snrt.md`, `ocr-arab-text-cremat.md`, `tifinag-estandard-i-dialecte.md`, `tamazight-tv.md`.
