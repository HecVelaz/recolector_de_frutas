"""Genera entrenar_limon.ipynb desde entrenar_limon.py (celdas "# %%" y "# %% [markdown]")."""
import re
from pathlib import Path

import nbformat

aqui = Path(__file__).parent
texto = (aqui / "entrenar_limon.py").read_text()
celdas = []
for bloque in re.split(r"^# %%", texto, flags=re.M)[1:]:
    cabecera, _, cuerpo = bloque.partition("\n")
    cuerpo = cuerpo.strip("\n")
    if "[markdown]" in cabecera:
        md = "\n".join(re.sub(r"^# ?", "", linea) for linea in cuerpo.splitlines())
        celdas.append(nbformat.v4.new_markdown_cell(md))
    else:
        celdas.append(nbformat.v4.new_code_cell(cuerpo))
nb = nbformat.v4.new_notebook(cells=celdas)
nb.metadata = {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
               "kernelspec": {"name": "python3", "display_name": "Python 3"}}
nbformat.write(nb, aqui / "entrenar_limon.ipynb")
print(f"{len(celdas)} celdas")
