"""Arma el .ipynb de una entrega desde su .md: una celda por cada `<!-- celda -->`.

Una celda que es solo un bloque ```python queda como celda de código; el resto, como markdown.
Uso: python3 armar_cuaderno.py "Entrega 8/Entrega8.md" "Entrega 8/Entrega8.ipynb"
"""
import hashlib
import json
import re
import sys

md, salida = sys.argv[1:3]
celdas = []
for i, texto in enumerate(open(md, encoding="utf-8").read().split("<!-- celda -->")):
    texto = texto.strip("\n")
    codigo = re.fullmatch(r"```python\n(.*)\n```", texto.strip(), re.S)
    fuente = codigo.group(1) if codigo else texto
    celda = {"cell_type": "code" if codigo else "markdown",
             "metadata": {"id": hashlib.md5(f"{i}{fuente}".encode()).hexdigest()[:12]},
             "source": fuente.splitlines(keepends=True)}
    if codigo:
        celda.update(execution_count=None, outputs=[])
    celdas.append(celda)

nb = {"nbformat": 4, "nbformat_minor": 0, "cells": celdas,
      "metadata": {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}}}
json.dump(nb, open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{salida}: {len(celdas)} celdas ({sum(c['cell_type'] == 'code' for c in celdas)} de código)")
