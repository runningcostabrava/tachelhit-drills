# SNRT: baixar del replay per a recerca

Permís de la SNRT del 17-11-2026 (`docs/PERMISOS.md`): els canals de YouTube i el replay del web
com a font d'investigació per al traductor i el transcriptor; **no republicar**. Res d'això va a la
biblioteca pública: tot a `Veus-tachelhit\_escoltats\tamazight_tv\`.

- **YouTube (camí per omissió):** `python -m yt_dlp` del venv del backend sobre el canal
  `UCZ97maPQK1vncXInrHeTEAg` (llista plana a `Veus-tachelhit\_escoltats\tamazight_tv_videos.txt`).
- **Replay del web (`snrt.ma/fr/...`):** `baixa_replay.py <URL>`. El replay el serveix el reproductor
  de forja.ma amb una llista HLS i una fitxa d'accés temporal; el guió segueix els passos
  (pàgina → reproductor → API → llista → fitxa → yt-dlp). La crida al servidor de fitxes la
  bloqueja el classificador de la sessió de Claude: **l'executa en Pablo amb «!»**.

```
! C:/Users/josep/app2/tachelhit-drills/backend/venv/Scripts/python.exe -X utf8 C:/Users/josep/app2/tachelhit-drills.worktrees/mirar/tools/snrt/baixa_replay.py https://www.snrt.ma/fr/tadfi-n-tskla-hicham-fouad-goughelt
```

`--nomes-url` per provar sense baixar; `--qualitat 1080` si l'OCR ho demana; `--carpeta` per
canviar la destinació. Al costat del `.mp4` queda un `.json` amb el títol, les adreces i el permís.
