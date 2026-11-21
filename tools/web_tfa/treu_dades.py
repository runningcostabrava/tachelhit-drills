# -*- coding: utf-8 -*-
"""Les dades que el web de Tamazight For All porta dins del seu HTML (és un Blogger amb tot en
línia): els `const X = [...]` de JavaScript (contes, pronoms, preposicions, glossari, jocs) i les
taules de diàlegs i vocabulari (tifinag + llatí + traducció). Només es LLEGEIX: el peu del web
diu «tots els drets reservats, ús personal no comercial»; això és un instrument de validació.

ÚS: treu_dades.py <index.html> <sortida.json>
"""
import io
import json
import re
import sys


def bloc_balancejat(text, inici):
    """Des de `[` a `inici`, el tros fins al `]` que el tanca, saltant cadenes."""
    prof, i, en_cadena, esc = 0, inici, None, False
    while i < len(text):
        ch = text[i]
        if en_cadena:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == en_cadena:
                en_cadena = None
        else:
            if ch in "\"'`":
                en_cadena = ch
            elif ch == "[":
                prof += 1
            elif ch == "]":
                prof -= 1
                if prof == 0:
                    return text[inici:i + 1]
        i += 1
    return None


def js_a_json(s):
    """JS tolerant → JSON: claus sense cometes, cometes simples, comes finals, comentaris."""
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)
    #: cometes simples → dobles (sense tocar apòstrofs dins de cadenes dobles: aproximació)
    s = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: '"' + m.group(1).replace('"', '\\"') + '"', s)
    s = re.sub(r",(\s*[\]}])", r"\1", s)
    #: plantilles `...` amb salts de línia: es passen a cadena normal
    s = re.sub(r"`((?:[^`\\]|\\.)*)`", lambda m: json.dumps(m.group(1)), s, flags=re.S)
    try:
        return json.loads(s, strict=False)
    except json.JSONDecodeError:
        #: sumes de cadenes («a» + «b») i expressions: s'esborra el que no és literal
        s2 = re.sub(r'"\s*\+\s*"', "", s)
        return json.loads(s2, strict=False)


if __name__ == "__main__":
    html = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
    fora, errors = {}, {}
    for m in re.finditer(r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\[", html):
        nom, inici = m.group(1), m.end() - 1
        bloc = bloc_balancejat(html, inici)
        if not bloc:
            continue
        try:
            fora[nom] = js_a_json(bloc)
        except Exception as e:
            errors[nom] = f"{type(e).__name__}: {str(e)[:60]} (mida {len(bloc)})"
            #: com a mínim les cadenes, perquè no es perdi el contingut
            fora[nom + "__cadenes"] = re.findall(r"[\"'`]([^\"'`]{2,200})[\"'`]", bloc)[:2000]
    #: les taules HTML amb tifinag: files de <tr> amb cel·les
    taules = []
    for t in re.findall(r"<table.*?</table>", html, flags=re.S):
        if not re.search(r"[ⴰ-⵿]", t):
            continue
        files = []
        for tr in re.findall(r"<tr.*?</tr>", t, flags=re.S):
            cels = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
            if any(cels):
                files.append(cels)
        if files:
            taules.append(files)
    fora["__taules_amb_tifinag"] = taules
    json.dump(fora, io.open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in fora.items():
        print(f"{k:28} {len(v):6} elements" + (f"  · ex: {json.dumps(v[0], ensure_ascii=False)[:120]}" if v else ""))
    for k, e in errors.items():
        print(f"  (no parsejat del tot) {k}: {e}")
    print(f"taules amb tifinag: {len(taules)} · files: {sum(len(t) for t in taules)}")
