# Casar un episodi del Baba Ali amb la seva pujada, quan la pujada ve muda

Deu dels nostres episodis es van casar amb el vídeo del canal **pel so**: el tall que tenim
desat és un tros exacte de la banda sonora de la pujada, i trobar-lo és un càlcul. Dues pujades
(les dels episodis 7 i 9) no ho permeten: YouTube les serveix **mudes**, −91 dB de cap a cap,
que és el silenci digital — segurament una reclamació de la música. Aquests guions són el camí
per a aquests casos, i per als que vinguin (els episodis 16 a 30 encara no s'han capturat).

La idea: el subtítol àrab va cremat a la franja de baix de la imatge, i el moment en què un
subtítol deixa lloc al següent és **exactament** el que són les nostres marques de temps. No cal
llegir l'àrab — el Tesseract no se'n surt, amb aquests subtítols —; n'hi ha prou de mirar quant
canvia la franja de fotograma a fotograma.

## Com es fa

Cal `ffmpeg` i `yt-dlp` **del venv del backend** (el `yt-dlp` global del PC és de febrer i es
menja un 403: `backend/venv/Scripts/python.exe -m yt_dlp`).

```sh
# 1. la imatge de la pujada (720p; la franja dels subtítols es mesura en 1280x720)
python -m yt_dlp -f 136 -o "video/<ID>.%(ext)s" "https://www.youtube.com/watch?v=<ID>"

# 2. quin dels nostres episodis hi és, i a quin desplaçament
python canvis.py <ID>

# 3. la prova: quantes marques hi casen, i què en casa el millor de tots els altres
python prova_canvis.py <ID> <episodi> <desplaçament>
```

Com que l'episodi gairebé omple la pujada, els desplaçaments possibles són pocs (uns 40 s), i
el que importa no és el número sol sinó quant destaca de tots els altres.

## I després, la pantalla

El càlcul sol no tanca res. Agafa fotogrames del segon que el desplaçament prediu i mira si la
pantalla hi diu la nostra línia:

```sh
ffmpeg -ss <t + desplaçament + 1> -i video/<ID>.mp4 -frames:v 1 \
       -vf "crop=1280:130:0:566" franja.png
```

Tria línies que durin uns quants segons i que siguin llargues, i reparteix-les per tot
l'episodi. Si tres o quatre hi diuen el mateix paraula per paraula, és aquell vídeo. Això és el
que es desa a `backend/data/baba_ali_pujades.json` com a `frases_comprovades_a_la_pantalla`.

## Variables

- `TD_BIBLIOTECA` — el cau local de la biblioteca (per omissió, el de la màquina d'en Pablo).
- `TD_VIDEOS` — on són els `.mp4` baixats.
- `TD_CAU_CANVIS` — on es desa la mesura, que costa un minut per vídeo.
