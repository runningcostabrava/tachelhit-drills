# OCR d'àrab (i tifinag) de text cremat: resum de recerca (17-11-2026)

Versió breu. L'informe complet, amb fonts i marques de «llegit / cerca / em sembla», és a
`Veus-tachelhit/_escoltats/tamazight_tv/recerca_ocr_arab/INFORME.md`. No s'ha baixat cap model ni dataset.

## Conclusions

- **Cap xifra publicada de CER d'àrab de subtítols cremats amb lectors moderns.** El més proper és AcTiV-R (10.415
  línies de notícies en vídeo, 2018) i EvArEST (escena); no n'he pogut llegir el CER.
- **Lectors generals, mals en àrab per línies** (KITAB-Bench, ACL Findings 2025): Tesseract CER 0,66, Surya 0,87,
  EasyOCR 0,20; PaddleOCR 0,76–0,89 (probable problema d'ordre RTL, sense comprovar). VLM i lectors entrenats amb
  àrab sintètic van molt millor: Gemini 2.0 Flash 0,18 a EvArEST, GPT-4o 0,20, Qari (Qwen2-VL-2B) 0,30; Qari 0,061 al seu
  banc de llibre amb diacrítics.
- **Recepta comunitària més propera a la nostra**: PP-OCRv6 small àrab de medyas, ~800.000 línies sintètiques
  (26 fonts + 12 de display, fons texturats, polaritat invertida), CER 10–14 % en imprès real, **punt de control triat
  sobre real**. L'ordre de les etiquetes és visual (`bidi.get_display`); un ordre equivocat dispara el CER.
- **Fine-tuning de VLM petits**: un LoRA sobre Qwen3-VL-2B va millorar en distribució (0,65→0,37) però va empitjorar
  fora (KHATT 1,5→2,8). No val la pena per a una sola tipografia.

## Recepta per a nosaltres (cost/benefici)

1. Mesurar: ≥ 200 línies reals d'Illy transcrites a mà (~5.000 caràcters) per distingir 2 % de 3 %.
2. Continuar el CRNN+CTC propi, afinant-lo amb les franges reals ja etiquetades i triant el punt de control sobre real.
3. **Vot entre fotogrames** del mateix subtítol (alinear per distància d'edició, majoria de caràcter).
4. Consens amb el lector Qwen i desempat amb un lèxic àrab propi; normalitzar ordre RTL abans de comptar.
5. No val la pena: Surya, TrOCR, VLM de 2–4 B afinats sobre una tipografia.

## Tifinag

- Datasets sintètics a Hugging Face (`Tamazight/Tifinagh-OCR-39K`, 200k, Perspective-5K…, Apache-2.0) i un
  `TrOCR-Tifinagh-Small` **sense cap xifra a la fitxa**; un docTR de joguina (1.000 mostres, 1 època).
- Cap `traineddata` de Tesseract per a Tifinagh. Articles: manuscrit AMHCD 98–99 % de caràcter; rètols de carrer (DaToBS)
  >92 % amb 1.862 imatges.
- La nostra línia (font IRCAM + sintètic + CRNN, CER 0,050 en reals) ja supera tot el que hi ha publicat.

## Pendent de llegir

Zayene et al. IET CV 2018 (CER a AcTiV-R), l'article d'EvArEST i les imatges del Tifinagh-OCR-39K.
