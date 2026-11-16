# Dos auditors de màquina sobre les traduccions «traduit-per-maquina» (#494)

La regla del 31-10 («dos auditors i només l'acord», `docs/recerca/models-de-text.md`), ara amb dos
auditors de cases diferents: `qwen3.8-max` (Model Studio, sense raonament) i `deepseek-chat` (API
directa). Cada un veu la frase amaziga (tifinag i llatí), la traducció de la màquina i el que diuen el
diccionari de l'IRCAM, el Viccionari i les taules de conjugació de cada paraula (`lexicon.grounding_lines`),
i respon una sola línia: `TRIA: <text final>`, `FORA` o `NO-HO-SE`. Entra només l'acord: tots dos TRIA
amb el mateix text (o diferent només en puntuació i majúscules, chrF ≥ 0,9) → confirmada i etiqueta
`traduit-per-auditors`; tots dos FORA → etiqueta `traduccio-descartada`; la resta queda com a proposta.

Cap guió no escriu a producció llevat d'`aplica.py --escriu`, que executa el propietari.

| pas | guió | surt |
|---|---|---|
| 1 | `baixa_cataleg.py` | `cataleg_prod.json` (tot el catàleg, a raigs de 500) |
| 2 | `tria_pendents.py` | `pendents.json` (MTNRA + Common Voice amb `traduit-per-maquina`) |
| 3 | `audita.py` | `veredictes.jsonl` (un per frase i auditor; reprèn si es talla; `LIMIT=5` per provar) |
| 4 | `resum.py` | `canvis.json` i `resum.md` (acord, caixes, mostres) |
| 5 | `aplica.py` | prova en sec; `--escriu` aplica els canvis al Postgres de Render (`backend/.env.prod`) i desa `aplicat.json` amb l'estat anterior. Només toca files que encara porten l'etiqueta i el mateix text que es va auditar |

Carpeta de dades (primer argument; per defecte `Veus-tachelhit\_escoltats\traduccions\auditors`), fora
del repositori. Claus: `DASHSCOPE_API_KEY` + `DASHSCOPE_BASE_URL` a `backend/.env`, `DEEPSEEK_API_KEY`
al `.env` del projecte veí. Resultat de la passada del 16-11-2026 a `resum.md` de la carpeta de dades i
a `docs/recerca/models-de-text.md`.
