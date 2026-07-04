"""
Build the Amazigh-grammar knowledge file for the AI tutor by downloading the
public PDFs from amazic.cat and extracting their text.

The extracted text is NOT committed to the repo (it is third-party grammar
material); it is generated on demand into knowledge/amazigh_grammar.md and
regenerated whenever missing. Run directly (`python build_knowledge.py`) or
let the backend call build_grammar() lazily on the first AI request.
"""
import os
import re

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")
GRAMMAR_PATH = os.path.join(KNOWLEDGE_DIR, "amazigh_grammar.md")

BASE = "https://www.amazic.cat/wp-content/uploads/2017/02"
SOURCES = [
    (1, "Fonologia i grafemàtica", "1.-Fonologia-i-grafem%C3%A0tica.pdf"),
    (2, "Morfofonologia", "2.-Morfofonologia.pdf"),
    (3, "Morfologia nominal", "3.-Morfologia-nominal.pdf"),
    (4, "Morfosintaxi pronominal", "4.-Morfosintaxi-pronominal.pdf"),
    (5, "Morfosintaxi verbal", "5.-Morfosintaxi-verbal.pdf"),
    (6, "Morfosintaxi de les paraules invariables", "6.-Morfosintaxi-de-les-paraules-invariables.pdf"),
    (7, "Sintaxi oracional elemental", "7.-Sintaxi-oracional-elemental.pdf"),
]


def build_grammar(force: bool = False) -> str:
    """Generate the grammar markdown if missing; return its path."""
    if os.path.exists(GRAMMAR_PATH) and not force:
        return GRAMMAR_PATH

    import requests
    import fitz  # pymupdf

    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    parts = [
        "# Compendi de Gramàtica Amaziga (font: amazic.cat)\n",
        "Gramàtica de referència de la llengua amaziga/tamazight (inclou el taixelhit), en català.\n",
    ]
    for n, title, fname in SOURCES:
        url = f"{BASE}/{fname}"
        print(f"[KB] Downloading {url}")
        pdf_bytes = requests.get(url, timeout=90).content
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        txt = "\n".join(page.get_text() for page in doc)
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
        parts.append(f"\n\n## {n}. {title}\n\n{txt}")

    with open(GRAMMAR_PATH, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"[KB] Wrote {GRAMMAR_PATH} ({os.path.getsize(GRAMMAR_PATH):,} bytes)")
    return GRAMMAR_PATH


if __name__ == "__main__":
    build_grammar(force=True)
