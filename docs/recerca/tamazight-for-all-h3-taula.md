# H3: el lèxic al feix, taules crues (15-11-2026)

Les dues taules de sota són la sortida crua de l'experiment H3 sobre els 226 versos narrats de
Tamazight For All amb veritat humana (nucli `tfa-h3-el-lexic-al-feix`). La lectura és a
`tamazight-for-all.md`, secció «H3 · Descodificar amb el lèxic a dins».

> **Això es va corregir a `DESXIFRAT.md` §38 (vegeu `AUDITORIA-2026-11-21.md`, troballa 1):** tot
> plegat està mesurat amb `adaptador_shi_ric`, que el 16-11 al migdia va deixar de servir.
> Redescodificades les proves amb l'adaptador d'ara (H4b), el guany del model de llengua a
> TFA-226 és −0,0014 i **no es pot dir**. El que hi ha aquí sota és el que es va creure.

| descodificació | n | CER | CER plegat | WER | WER plegat | de la qual, frontera |
|---|---|---|---|---|---|---|
| **parlat** | | | | | | |
| shi | 226 | 0.206 | 0.182 | 0.714 | 0.670 | 0.030 |
| greedy | 226 | 0.207 | 0.183 | 0.712 | 0.665 | 0.036 |
| beam | 226 | 0.201 | 0.177 | 0.682 | 0.636 | 0.032 |
| lexic_a0.15_b0.0 | 226 | 0.205 | 0.182 | 0.673 | 0.624 | 0.035 |
| lexic_a0.15_b1.0 | 226 | 0.200 | 0.176 | 0.646 | 0.593 | 0.036 |
| lexic_a0.3_b0.0 | 226 | 0.216 | 0.193 | 0.703 | 0.662 | 0.040 |
| lexic_a0.3_b1.0 | 226 | 0.215 | 0.192 | 0.678 | 0.631 | 0.033 |
| lexic_a0.6_b0.0 | 226 | 0.241 | 0.218 | 0.785 | 0.752 | 0.060 |
| lexic_a0.6_b1.0 | 226 | 0.233 | 0.210 | 0.748 | 0.714 | 0.038 |
| lexic_a0.3_b0.5_unk5 | 226 | 0.234 | 0.209 | 0.808 | 0.778 | 0.072 |
| corpus_bi_a0.15_b0.0 | 226 | 0.204 | 0.180 | 0.666 | 0.616 | 0.036 |
| corpus_bi_a0.15_b1.0 | 226 | 0.198 | 0.174 | 0.640 | 0.584 | 0.033 |
| corpus_bi_a0.3_b0.0 | 226 | 0.216 | 0.193 | 0.696 | 0.656 | 0.038 |
| corpus_bi_a0.3_b1.0 | 226 | 0.213 | 0.190 | 0.671 | 0.625 | 0.032 |
| corpus_bi_a0.6_b0.0 | 226 | 0.239 | 0.215 | 0.777 | 0.743 | 0.057 |
| corpus_bi_a0.6_b1.0 | 226 | 0.236 | 0.212 | 0.744 | 0.709 | 0.041 |
| corpus_bi_a0.3_b0.5_unk5 | 226 | 0.230 | 0.206 | 0.792 | 0.761 | 0.067 |
| **cantat** | | | | | | |
| shi | 15 | 0.230 | 0.211 | 0.702 | 0.663 | 0.000 |
| greedy | 15 | 0.234 | 0.214 | 0.728 | 0.682 | 0.000 |
| beam | 15 | 0.226 | 0.206 | 0.700 | 0.654 | 0.000 |
| lexic_a0.15_b0.0 | 15 | 0.199 | 0.179 | 0.619 | 0.580 | 0.000 |
| lexic_a0.15_b1.0 | 15 | 0.202 | 0.181 | 0.613 | 0.566 | 0.000 |
| lexic_a0.3_b0.0 | 15 | 0.193 | 0.177 | 0.602 | 0.580 | 0.000 |
| lexic_a0.3_b1.0 | 15 | 0.200 | 0.184 | 0.597 | 0.575 | 0.000 |
| lexic_a0.6_b0.0 | 15 | 0.238 | 0.220 | 0.670 | 0.655 | 0.000 |
| lexic_a0.6_b1.0 | 15 | 0.224 | 0.205 | 0.622 | 0.607 | 0.000 |
| lexic_a0.3_b0.5_unk5 | 15 | 0.243 | 0.223 | 0.707 | 0.684 | 0.000 |
| corpus_bi_a0.15_b0.0 | 15 | 0.198 | 0.177 | 0.614 | 0.575 | 0.000 |
| corpus_bi_a0.15_b1.0 | 15 | 0.198 | 0.178 | 0.602 | 0.556 | 0.000 |
| corpus_bi_a0.3_b0.0 | 15 | 0.195 | 0.179 | 0.601 | 0.579 | 0.000 |
| corpus_bi_a0.3_b1.0 | 15 | 0.197 | 0.181 | 0.601 | 0.579 | 0.000 |
| corpus_bi_a0.6_b0.0 | 15 | 0.254 | 0.235 | 0.649 | 0.617 | 0.000 |
| corpus_bi_a0.6_b1.0 | 15 | 0.260 | 0.241 | 0.637 | 0.622 | 0.000 |
| corpus_bi_a0.3_b0.5_unk5 | 15 | 0.239 | 0.219 | 0.699 | 0.677 | 0.000 |
