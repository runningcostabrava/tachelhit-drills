"""Posa a la biblioteca unes quantes frases amb el seu tall de so.

És el camí per entrar material nou que ja ve escrit: un vídeo on l'autor posa el text a la
pantalla, un recull, un full de paper. No és per a la sortida d'una màquina nostra —per a això
hi ha `*_suggested`— sinó per a text que algú ha escrit de debò.

## Què hi entra i on va

Del fitxer d'entrada, cada frase pot portar:

- `text_tachelhit`, `text_tachelhit_latin`, `text_catalan` — **camps de persona**. Només s'hi
  posa el que ha escrit algú: l'autor del vídeo, el llibre, el parlant. Mai una lectura de
  màquina (ADR 0003).
- `text_tachelhit_suggested` i `esborranys` — el que una màquina hi sent, amb el seu nom.
- `source_*` — d'on surt. Sense això, d'aquí a sis mesos ningú no sabrà què és.
- `_tall_local` — el fitxer de so al disc. Es puja al dipòsit (R2 si hi ha claus, Cloudinary
  si no) i l'adreça va a `audio_url`.

## El que NO fa

No decideix res. Si una frase ja hi és —mateix text amazic i mateixa font— no la torna a
posar, i ho diu. I **no esborra mai res**.

## Ús

    cd backend
    python ../tools/importa_frases.py ../fitxer.json              # mira i no toca res
    python ../tools/importa_frases.py ../fitxer.json --escriu     # ho fa

La base surt de `DATABASE_URL`, com el servidor. Per a producció cal la de Render, i qui
l'executa és qui en té la clau.
"""
import argparse
import io
import json
import os
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fitxer", help="el JSON amb les frases")
    p.add_argument("--escriu", action="store_true", help="desar de debò (per omissió, mira)")
    p.add_argument("--env", help="d'on surten les claus, si no s'executa des de backend/")
    a = p.parse_args()

    sys.path.insert(0, os.path.abspath("."))
    from dotenv import load_dotenv
    load_dotenv(a.env) if a.env else load_dotenv()
    os.environ.setdefault("LEXICON_WARMUP", "0")
    import magatzem
    from main import SessionLocal
    from models import Drill as DrillModel

    frases = json.load(io.open(a.fitxer, encoding="utf-8"))
    print(f"{len(frases)} frases a {a.fitxer}")
    #: Quina base es toca, dit abans de fer res i sense la contrasenya. Aquí no es barra el pas
    #: —importar a una base local és una cosa que es fa per provar—, però cal saber on s'escriu:
    #: el 13-11-2026, una passada contra el sqlite del disc va contestar «res a fer» i semblava
    #: que la feina ja estigués feta.
    adreca = os.getenv("DATABASE_URL", "sqlite:///drills.db")
    on = adreca.split("@")[-1].split("/")[0] if "@" in adreca else adreca
    print(f"base: {on}")
    print(f"dipòsit: {'R2' if magatzem.a_r2() else 'Cloudinary'}\n")

    db = SessionLocal()
    try:
        fetes = saltades = 0
        for f in frases:
            text = (f.get("text_tachelhit") or "").strip()
            font = (f.get("source_title") or "").strip()
            ja = db.query(DrillModel).filter(
                DrillModel.text_tachelhit == text,
                DrillModel.source_title == font).first() if text else None
            if ja:
                print(f"  ja hi és (drill {ja.id}): {text[:40]}")
                saltades += 1
                continue

            tall = f.get("_tall_local")
            adreca = None
            if tall and os.path.exists(tall):
                if a.escriu:
                    #: el nom dins del dipòsit surt del text, no d'un comptador: així dos
                    #: imports de la mateixa frase no fan dos fitxers
                    adreca = magatzem.puja(tall, carpeta="tachelhit/audio",
                                           nom=os.path.splitext(os.path.basename(tall))[0],
                                           mena="so")
                    print(f"  so pujat: {adreca}")
                else:
                    print(f"  so a pujar: {os.path.basename(tall)}")
            elif tall:
                print(f"  ATENCIÓ: no trobo el tall {tall}")

            camps = {k: v for k, v in f.items() if not k.startswith("_")}
            if adreca:
                camps["audio_url"] = adreca
            print(f"  {'DESO' if a.escriu else 'desaria'}: {text[:38]:<40} {camps.get('text_catalan','')[:30]}")
            if a.escriu:
                db.add(DrillModel(**camps))
                db.commit()
            fetes += 1

        print(f"\n{fetes} {'desades' if a.escriu else 'per desar'} · {saltades} ja hi eren")
        if not a.escriu:
            print("(no s'ha tocat res. Amb --escriu es fa.)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
