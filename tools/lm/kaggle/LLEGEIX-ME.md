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
| `h5_afina_shi_propi_mes_zouhir.py` | `h5-afina-shi-propi-mes-zouhir` | H4b + el corpus propi (`corpus_v4`) + Zouhir net; sis tests (test-dins, test-fora, cv-zgh-test, TFA-226, Zouhir fora, Alcorà net). Només mou Beni Mellal; no es desplega |
| `bootstrap_h4.py` | (a casa) | Δ CER abans → després per prova amb IC 95 %, i H4 contra H4b sobre els mateixos talls |

Resultats a `docs/recerca/tamazight-for-all.md` i `zouhir-amazigh.md`. Un adaptador afinat amb
material de tercers no es desplega sense permís dels autors: el d'H4b (`adaptador_shi_zouhir_b.pt`)
es va desplegar el 16-11-2026 amb el permís que consta a `docs/PERMISOS.md`.

Avís (16-11): `cues.json` del dataset `zouhir-veritat` porta rètols amb veritat en lletres àrabs,
en grafia cabilenca i amb temps desplaçats (canal de l'Alcorà). `tools/lm/zouhir_resum.py` els
marca a `veritat_zouhir.json` (`mena`: «àrab», «altra grafia», «rètol»). `h4b_afina_shi_net.py`
(nucli `h4b-afina-shi-net`) és H4 amb aquest filtre fet dins del nucli i l'Alcorà fora amb tres
vídeos nets.

| `prepara_parelles.py` → `nllb_afina_propi.py` → `baixa_sortides.py` → `avalua_a_casa.py` | `nllb-afina-propi` (dataset privat `nllb-parelles-propies`) | H-MT1 (16-11): afinar el NLLB de Tamazight-NLP amb 4.609 parelles pròpies netes (fuita per text treta); català directe 0,454 → 0,571 sobre les 60, +0,147 al test-dins de 200; el pont per l'anglès no es mou |
| `prepara_parelles_v3.py` → `nllb_afina_propi_v3.py` → `avalua_a_casa.py --pont=abans,millor,millor-ct2int8` → `compara_v3_v2.py` | `nllb-afina-propi` v3 (mateix dataset, versió 3) | H-MT1 v3 (16-11, nit): train sense vocabulari sol ni glosses múltiples (−1.482) i amb 302 parelles MTNRA/CV confirmades pels dos auditors (3.399), ritme 5e-5, 5 èpoques, millor checkpoint per pèrdua de dev (la 4a); català directe 0,618 sobre les 60 (v2 0,571; Δ +0,047 [+0,018, +0,080]) i 0,453 al test-dins (v2 0,425); ct2 int8 dins del nucli, idèntic a l'fp16 |
