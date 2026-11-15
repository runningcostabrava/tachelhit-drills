# -*- coding: utf-8 -*-
"""Fa el notebook de Kaggle a partir del guió, partint-lo per `# %%`. ÚS: fes_nb.py <guió.py> <sortida.ipynb>"""
import io
import json
import sys

text = io.open(sys.argv[1], encoding="utf-8").read()
trossos = [t.strip("\n") for t in text.split("\n# %%\n")]
cells = [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
          "source": t.splitlines(keepends=True)} for t in trossos if t.strip()]
nb = {"cells": cells,
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
io.open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(nb, ensure_ascii=False, indent=1))
print(len(cells), "cel·les →", sys.argv[2])
