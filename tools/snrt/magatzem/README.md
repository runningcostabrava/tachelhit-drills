# El magatzem: arxiu de treball, no codi mantingut

Aquests 141 guions són el que s'ha anat escrivint mentre es desxifrava el material del SNRT i
es muntaven els corpus. Vivien només a `E:\tamazight\_magatzem`, en un sol disc i sense cap
historial. Són aquí perquè no es perdin.

**Què NO són.** No són codi mantingut. No tenen proves, molts són d'un sol ús, i uns quants
contradiuen els altres perquè van ser intents successius de la mateixa cosa. Per això no van a
`tools/snrt/fabrica/`, que sí que és codi que corre cada dia a l'ECS.

**Com es llegeix.** Cada guió porta al capdamunt què fa i **per què es va escriure**, que és
el que no es pot tornar a deduir del codi. El raonament sencer és al quadern:
[`docs/recerca/DESXIFRAT.md`](../../../docs/recerca/DESXIFRAT.md) (què hem desxifrat, amb la
prova al costat) i [`docs/recerca/METODE.md`](../../../docs/recerca/METODE.md) (les trampes en
què he caigut, perquè no s'hi torni).

**Camins.** Molts apunten a `E:/tamazight/...`, que és on viuen els vídeos, els talls i els
models — massa grossos per al repositori. Un guió copiat d'aquí no correrà en una altra màquina
sense canviar-los.

**Si un d'aquests guions es torna feina de cada dia**, no es queda aquí: es neteja, se li fan
proves i passa a `tools/snrt/`.

## Els que importen més

| guió | què fa |
|---|---|
| `corpus_tifinag_arab.py` | munta el corpus tifinag→àrab, partit **per capítols** i sense el Rif |
| `corpus_veu_arab.py` | el mateix per a veu→àrab, heretant la mateixa partició |
| `base_zgh_ar.py` | el punt de partida a batre: chrF 0,2634 |
| `don_son_els_convidats_nous.py` | de quina varietat és cada capítol, pels **topònims a l'àrab** |
| `kaggle_zgh_arab.py`, `kaggle_veu_arab.py`, `kaggle_alinea.py` | els tres treballs de GPU |
| `serveix_els_videos.py` | el visor del telèfon |
| `posa_la_traduccio.py` | posa al capítol una traducció feta a mà, sense tocar res més |
