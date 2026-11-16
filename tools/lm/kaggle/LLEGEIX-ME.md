# Els nuclis de Kaggle d'aquesta recerca (compte `josepabloucr`)

Guions tal com s'han executat; `fes_nb.py` els converteix en quadern (`# %%` parteix cel·les).
Les dades són datasets privats del compte (`tfa-veritat-h3`, `zouhir-veritat`): so de tercers, no
va al repositori.

| guió | nucli | què mesura |
|---|---|---|
| `h3_lexic_al_feix.py` | `tfa-h3-el-lexic-al-feix`, `tfa-h3-cpu-…` | 226 versos de TFA: greedy / feix / feix + bigrames (α, β; amb i sense ⵡⵉⴽⵉⵎⴰⵡⴰⵍ) |
| `zouhir_lector_contra_pista.py` | `zouhir-lector-contra-pista-humana` | 2.164 rètols de Zouhir + Alcorà: greedy / feix / α 0,1 / α 0,15 |
| `h4_afina_shi_amb_zouhir.py` | `h4-afina-shi-amb-zouhir` | afinar l'adaptador `shi` amb Zouhir; mesura abans/després sobre TFA-226, Zouhir fora i Alcorà fora |
| `h4b_afina_shi_net.py` | `h4b-afina-shi-net` | H4 només amb la veritat neta (1.308 rètols); rèplica de la millora |
| `bootstrap_h4.py` | (a casa) | Δ CER abans → després per prova amb IC 95 %, i H4 contra H4b sobre els mateixos talls |

Resultats a `docs/recerca/tamazight-for-all.md` i `zouhir-amazigh.md`. L'adaptador afinat amb
material de tercers NO es desplega sense permís dels autors.

Avís (16-11): `cues.json` del dataset `zouhir-veritat` porta rètols amb veritat en lletres àrabs,
en grafia cabilenca i amb temps desplaçats (canal de l'Alcorà). `tools/lm/zouhir_resum.py` els
marca a `veritat_zouhir.json` (`mena`: «àrab», «altra grafia», «rètol»). `h4b_afina_shi_net.py`
(nucli `h4b-afina-shi-net`) és H4 amb aquest filtre fet dins del nucli i l'Alcorà fora amb tres
vídeos nets.
