"""Renombra un export YOLO de Roboflow a limon_001.jpg ... limon_050.jpg, con sus etiquetas.

Uso: python3 renombrar_dataset.py <export.zip> <carpeta_salida>
Ordena por el nombre original (fecha y hora de la foto) y numera de corrido en train, valid y test.
"""
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

zip_path, salida = Path(sys.argv[1]), Path(sys.argv[2])
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(zip_path).extractall(tmp)
    imagenes = sorted(Path(tmp).glob("*/images/*"), key=lambda p: p.name)
    assert imagenes, "el zip no tiene carpetas */images/: exportar en formato YOLOv8"
    shutil.rmtree(salida, ignore_errors=True)
    for i, img in enumerate(imagenes, 1):
        split = img.parent.parent.name                    # train, valid o test
        nuevo = f"limon_{i:03d}"
        etiqueta = img.parent.parent / "labels" / (img.stem + ".txt")
        for sub in ("images", "labels"):
            (salida / split / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy(img, salida / split / "images" / (nuevo + img.suffix))
        shutil.copy(etiqueta, salida / split / "labels" / (nuevo + ".txt"))
        print(f"{split:5s} {nuevo}  <-  {img.name.split('_jpg')[0]}")
    shutil.copy(next(Path(tmp).glob("data.yaml")), salida / "data.yaml")
print(f"{len(imagenes)} imágenes en {salida}")
