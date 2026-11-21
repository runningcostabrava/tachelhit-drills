"""Buida el «Vocabulaire grammatical amazighe» (IRCAM, 2009) a una taula.

Per què aquest i no els diccionaris grossos: és l'únic dels vuit PDF baixats que porta text de
debò en Unicode. L'Ayt Wirra i el de Figuig són escanejos (cal OCR) i el de mitjans i el de
geologia porten el tifinag en una tipografia antiga que surt il·legible en copiar-lo.

Val perquè és **l'autoritat de la norma**: els subtítols de Tamazight TV s'escriuen en aquesta
norma, i la taula estàndard ↔ dialecte necessita saber què diu la norma, no deduir-ho.

Cada entrada del llibre és: `• francès / anglès / àrab` i, a sota, les formes en tifinag i les
mateixes en llatí. L'àrab surt amb la tipografia antiga i es llença: no es desa el que no es pot
llegir, que seria fer veure que es té.

Sortida: `lexic_ircam_gramatical.tsv` (francès, anglès, tifinag, llatí).
"""
import io
import re
from pathlib import Path

import fitz

PDF = Path(r"E:\tamazight\_biblioteca_ircam\vocabulaire-grammatical-2009.pdf")
DESTI = Path(r"E:\tamazight\_magatzem\lexic_ircam_gramatical.tsv")

TIF = re.compile(r"[\u2d30-\u2d7f]")
#: el llatí acadèmic de l'IRCAM: amb les emfàtiques i la ɣ; els guions separen les formes
LLATI = re.compile(r"^[a-zɣɛḥḍṭẓṣṛšžəāīū\u0300-\u036f \-]+$", re.I)

d = fitz.open(PDF)
linies = []
for i in range(d.page_count):
    for l in d[i].get_text("text").split("\n"):
        l = " ".join(l.split())
        if l:
            linies.append(l)

files, actual = [], None
for l in linies:
    if l.startswith("•"):
        #: una entrada nova tanca l'anterior encara que no hagi trobat cap forma: així no
        #: s'arrosseguen les formes d'una entrada cap a la següent
        if actual:
            files.append(actual)
        trossos = [t.strip() for t in l.lstrip("• ").split("/")]
        actual = {"fr": trossos[0] if trossos else "", "en": trossos[1] if len(trossos) > 1 else "",
                  "tif": [], "lat": []}
        continue
    if not actual:
        continue
    if TIF.search(l):
        actual["tif"].extend(x for x in l.split(" - ") if TIF.search(x))
    elif LLATI.match(l) and len(l) > 1:
        actual["lat"].extend(x.strip() for x in l.split(" - ") if x.strip())
if actual:
    files.append(actual)

amb = [f for f in files if f["tif"]]
with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    f.write("frances\tangles\ttifinag\tllati\n")
    for x in amb:
        f.write(f"{x['fr']}\t{x['en']}\t{' - '.join(x['tif'])}\t{' - '.join(x['lat'])}\n")

print(f"entrades al llibre: {len(files)}   amb forma amaziga: {len(amb)}")
print(f"formes tifinag: {sum(len(x['tif']) for x in amb)}   desat a {DESTI}")
for x in amb[:6]:
    print(f"   {x['fr'][:28]:30s} {' - '.join(x['tif'])[:34]:36s} {' - '.join(x['lat'])[:34]}")
