"""Fabrica imatges de tifinag per entrenar un OCR, que s'assemblin al que de debo haura de llegir.

## Per que es pot fer aixi

El tifinag te 33 signes i el que hem de llegir es lletra IMPRESA de subtitol, no manuscrita. Amb
un alfabet tancat i tipografies disponibles, el text generat funciona: es la manera estandard de
fer un OCR per a una escriptura que no te milers d'imatges etiquetades, i aqui no en tenim ni
cent.

El que NO es pot fer es generar text a l'atzar. Les combinacions de lletres d'una llengua no son
les d'un generador aleatori, i un model entrenat amb lletres soltes aprendra a llegir lletres i
no paraules. Per aixo el text surt de **tifinag de debo**: 1.801 linies del MTNRA, 920 lectures
del NeMo i 313 frases de la biblioteca.

## I per que els fons son fotogrames i no un degradat

El que ha de llegir aquest model es lletra blanca amb vora negra damunt d'un video: damunt de
cares, de cel, de paret, de coses que es mouen. Un fons blanc net li ensenyaria una feina que no
es la seva. S'hi posen **franges de subtitol de debo** del video d'en Baba Ali (6.237) i
fotogrames dels videos del Metode (5.878).

## Les degradacions, i per que cadascuna

  · **escalar avall i amunt**  — el subtitol d'un video de 480p ampliat;
  · **desenfoc**               — compressio i moviment;
  · **JPEG agressiu**          — tot el que ve de YouTube;
  · **gir petit**              — el video no sempre esta recte;
  · **contrast i brillantor**  — el subtitol damunt d'una escena fosca o cremada.

Cap d'elles es decorativa: totes son coses que surten als fotogrames que ja tenim.
"""
import glob
import io
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

S = os.path.dirname(os.path.abspath(__file__))
#: L'alcada a la qual es normalitza tota linia abans d'entrar al model.
ALT = 48
MAX_AMPLE = 800

def _font_bona(cami):
    """Que existeixi i pesi NO vol dir que sigui una font.

    Vaig baixar dotze variants de la Noto i onze eren pagines d'error 404 del GitHub, de 231 kB
    cadascuna; el filtre que mirava la mida les va donar totes per bones. Aqui s'obren de debo.
    """
    try:
        ImageFont.truetype(cami, 24)
        return True
    except Exception:
        return False


FONTS = [f for f in (sorted(glob.glob(os.path.join(S, "fonts_tif", "*.ttf")))
                     + [r"C:\Windows\Fonts\ebrima.ttf", r"C:\Windows\Fonts\ebrimabd.ttf"])
         if os.path.exists(f) and _font_bona(f)]
if not FONTS:
    raise SystemExit("cap font de tifinag valida")

FONS = (sorted(glob.glob(os.path.join(S, "prova_arab", "bandes1080", "*.png")))[:3000]
        + sorted(glob.glob(os.path.join(S, "prova_arab", "bandes1080", "*.jpg")))[:3000]
        + sorted(glob.glob(os.path.join(S, "cd_metode", "_frames", "*.png")))[:2000]
        + sorted(glob.glob(os.path.join(S, "cd_metode", "_frames", "*.jpg")))[:2000])

TEXT = json.load(io.open(os.path.join(S, "tif_text.json"), encoding="utf-8"))
print("fonts: %d · fons: %d · linies de text: %d" % (len(FONTS), len(FONS), len(TEXT)))


def un_text(rnd):
    """Una linia, o un tros d'una linia llarga: els subtitols son curts."""
    t = rnd.choice(TEXT).strip()
    mots = t.split()
    if len(mots) > 8:
        i = rnd.randrange(0, len(mots) - 4)
        t = " ".join(mots[i:i + rnd.randint(3, 8)])
    return t


def un_fons(rnd, ample, alt):
    """Un tros de fotograma de debo, o un color pla si no n'hi ha."""
    for _ in range(4):
        if not FONS:
            break
        try:
            im = Image.open(rnd.choice(FONS)).convert("RGB")
        except Exception:
            continue
        if im.width < 40 or im.height < 20:
            continue
        #: Un retall a l'atzar, estirat a la mida que cal. Aixi el mateix fotograma dona fons
        #: diferents i no se'n memoritza cap.
        w = rnd.randint(max(20, im.width // 3), im.width)
        h = rnd.randint(max(10, im.height // 3), im.height)
        x = rnd.randint(0, im.width - w)
        y = rnd.randint(0, im.height - h)
        return im.crop((x, y, x + w, y + h)).resize((ample, alt), Image.BILINEAR)
    g = rnd.randint(0, 255)
    return Image.new("RGB", (ample, alt), (g, g, g))


def una_mostra(rnd):
    text = un_text(rnd)
    font = ImageFont.truetype(rnd.choice(FONTS), rnd.randint(28, 64))
    vora = rnd.randint(0, 4)

    #: Primer es mesura amb un llenc provisional, perque la mida depen de la font i del text.
    prova = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    caixa = prova.textbbox((0, 0), text, font=font, stroke_width=vora)
    tw, th = caixa[2] - caixa[0], caixa[3] - caixa[1]
    if tw < 8 or th < 8:
        return None
    marge_x = rnd.randint(4, 26)
    marge_y = rnd.randint(3, 16)
    ample, alt = tw + 2 * marge_x, th + 2 * marge_y

    im = un_fons(rnd, ample, alt)
    d = ImageDraw.Draw(im)
    #: Els subtitols son blancs o grocs amb vora negra. De tant en tant, el contrari.
    if rnd.random() < 0.85:
        c_text = rnd.choice([(255, 255, 255), (255, 255, 255), (250, 240, 120), (240, 240, 240)])
        c_vora = (rnd.randint(0, 40),) * 3
    else:
        c_text = (rnd.randint(0, 50),) * 3
        c_vora = (rnd.randint(210, 255),) * 3
    d.text((marge_x - caixa[0], marge_y - caixa[1]), text, font=font, fill=c_text,
           stroke_width=vora, stroke_fill=c_vora)

    #: --- la forma de la lletra ---
    #: Nomes tenim TRES families de tifinag, i amb tres el model aprendria aquestes tres i prou.
    #: Inclinar i estirar canvia la forma del glif de debo —no es soroll— i es el que fan servir
    #: els OCR quan no tenen tipografies. No substitueix tenir-ne mes, i queda dit.
    if rnd.random() < 0.35:
        inc = rnd.uniform(-0.22, 0.22)
        im = im.transform((im.width + int(abs(inc) * im.height), im.height), Image.AFFINE,
                          (1, inc, -inc * im.height if inc > 0 else 0, 0, 1, 0),
                          resample=Image.BILINEAR)
    if rnd.random() < 0.35:
        f = rnd.uniform(0.78, 1.3)
        im = im.resize((max(8, int(im.width * f)), im.height), Image.BILINEAR)

    #: --- les degradacions ---
    if rnd.random() < 0.3:
        im = im.rotate(rnd.uniform(-1.6, 1.6), resample=Image.BILINEAR, expand=False,
                       fillcolor=(0, 0, 0))
    if rnd.random() < 0.7:
        f = rnd.uniform(0.35, 0.9)
        im = im.resize((max(8, int(im.width * f)), max(8, int(im.height * f))),
                       Image.BILINEAR).resize((im.width, im.height), Image.BICUBIC)
    if rnd.random() < 0.5:
        im = im.filter(ImageFilter.GaussianBlur(rnd.uniform(0.3, 1.4)))
    if rnd.random() < 0.5:
        im = ImageEnhance.Brightness(im).enhance(rnd.uniform(0.6, 1.4))
    if rnd.random() < 0.5:
        im = ImageEnhance.Contrast(im).enhance(rnd.uniform(0.5, 1.5))
    if rnd.random() < 0.7:
        b = io.BytesIO()
        im.save(b, "JPEG", quality=rnd.randint(18, 75))
        b.seek(0)
        im = Image.open(b).convert("RGB")

    #: A l'alcada del model, mantenint la proporcio.
    nou_ample = max(16, min(MAX_AMPLE, int(im.width * ALT / im.height)))
    im = im.convert("L").resize((nou_ample, ALT), Image.BILINEAR)
    return im, text


if __name__ == "__main__":
    quants = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    on = sys.argv[2] if len(sys.argv) > 2 else os.path.join(S, "tif_mostres")
    llavor = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(on, exist_ok=True)
    rnd = random.Random(llavor)
    fitxa = []
    fets = 0
    while fets < quants:
        m = una_mostra(rnd)
        if not m:
            continue
        im, text = m
        nom = "t%06d.png" % fets
        im.save(os.path.join(on, nom))
        fitxa.append({"fitxer": nom, "text": text})
        fets += 1
        if fets % 2000 == 0:
            print("  %d/%d" % (fets, quants), flush=True)
    json.dump(fitxa, io.open(os.path.join(on, "fitxa.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("%d mostres a %s" % (fets, on))
