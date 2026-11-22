"""L'adreça que Render ensenya ha de servir tal com es copia.

El tauler de Render dona l'adreça de la base com a `postgres://`, que és el nom antic.
SQLAlchemy 2 ja no el coneix i contesta «Can't load plugin: sqlalchemy.dialects:postgres».
Qui la copia d'allà —que és el camí normal— es troba un mur que no diu què fer.

En Pablo s'hi va trobar el 13-11-2026 executant la reescriptura de les adreces a R2.
"""
import main


def test_el_nom_antic_de_render_es_corregeix():
    assert main.adreca_de_la_base("postgres://qui:clau@on:5432/base") == \
        "postgresql://qui:clau@on:5432/base"


def test_el_nom_bo_no_es_toca():
    bona = "postgresql://qui:clau@on:5432/base"
    assert main.adreca_de_la_base(bona) == bona


def test_el_sqlite_no_es_toca():
    assert main.adreca_de_la_base("sqlite:///drills.db") == "sqlite:///drills.db"
    assert main.adreca_de_la_base("sqlite:///C:/on/sigui/drills.db") == \
        "sqlite:///C:/on/sigui/drills.db"


def test_nomes_al_principi():
    """Una contrasenya que contingui «postgres://» no s'ha de tocar: si es canviés pel mig,
    l'adreça deixaria de valer i l'error seria molt més difícil de veure que el d'ara."""
    rara = "postgresql://qui:postgres://rara@on:5432/base"
    assert main.adreca_de_la_base(rara) == rara


def test_el_modul_la_fa_servir():
    """La funció no serveix de res si DATABASE_URL no hi passa.

    Es mira en un procés a part, amb l'adreça antiga a l'entorn, perquè és l'única manera de
    provar-ho de debò: comparant `main.DATABASE_URL` amb la funció dins d'aquesta mateixa
    sessió la prova passaria igual sense la crida, perquè el sqlite de les proves no es toca
    tant si s'aplica com si no. (Comprovat: amb aquella versió, treure la crida no feia caure
    res.)
    """
    import os
    import subprocess
    import sys

    entorn = dict(os.environ)
    entorn["DATABASE_URL"] = "postgres://qui:clau@on:5432/base"
    entorn["LEXICON_WARMUP"] = "0"
    arrel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, "-c", "import main; print(main.DATABASE_URL)"],
                       cwd=arrel, env=entorn, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    assert "postgresql://qui:clau@on:5432/base" in r.stdout, r.stdout[-400:]
