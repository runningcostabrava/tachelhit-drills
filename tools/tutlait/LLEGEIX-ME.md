# TutlAit v1 a la biblioteca: veu amaziga + significat en català (#328)

El corpus `Ma-OpenHub/Tutlait-v1` (CC BY 4.0; `docs/CREDITS.md`) són 13.369 talls de veu taixelhit i
tamazight amb una **traducció a l'àrab, no una transcripció**. N'hi havia 239 a la biblioteca. Aquesta
cadena hi porta la resta (Atles 9.956 + Souss 3.378; el Rif i Cabília queden fora) com a material
d'escolta: veu real més significat en català, i cap amazic escrit que no hagi dit una persona o el
lector com a proposta. El català surt de l'àrab per màquina i el jutgen dos auditors independents
(la regla del 31-10: només l'acord entra com a text; la resta queda com a proposta).

| pas | guió | surt |
|---|---|---|
| 0 | `huggingface_hub.snapshot_download` del dataset a `Veus-tachelhit\_paquets\tutlait\hf\` (1,3 GB) | parquets |
| 1 | `treu_dades.py` | `metadades.jsonl` (id, àrab, accent → varietat, parlant, durada, `ja_a_produccio`) i `audio\<id>.flac` |
| 2 | `tradueix_ar_ca.py` | `traduccions.jsonl` (`qwen3.8-max`, àrab → català; reprèn) |
| 3 | `fes_pendents.py` | `pendents.json` a `…\traduccions\auditors_tutlait\` |
| 4 | `tools/lm/auditors_traduccions/audita_arab.py`, `audita_tercer.py`, `resum.py` amb aquella carpeta | `veredictes*.jsonl`, `canvis.json`, `resum.md` |
| 5 | `prepara_import.py` | `import.jsonl`: confirmades amb `text_catalan` i `traduit-per-auditors`; sense acord amb `text_catalan_suggested` i `traduit-per-maquina`; descartades fora |
| 6 | `carrega.py` (prova) / `carrega.py --escriu [--max N]` | so a R2 (`tachelhit/tutlait/`) i files a `drills` pel Postgres de Render; `carregat.jsonl` per reprendre. **Només el propietari.** |

`nit.py` encadena 3-5 quan la traducció acaba. Cada fila entra amb `speaker = TutlAit · spk_NNN`,
`variety` tzm o shi, `region` «Atles Central (corpus TutlAit)» o «Souss (corpus TutlAit)», `license`
CC BY 4.0, `source_url` del dataset, i l'àrab a `text_arabic`. El que el lector digui de la veu anirà
a `text_tachelhit_suggested` més endavant (la màquina de Singapur, quan acabi aslmdtv).
