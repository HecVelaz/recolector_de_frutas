# %% [markdown]
# # Detector de limones para Arturito R2D2 (YOLO, Google Colab)
#
# Entrena un `yolo26n` con **una sola clase, `limon`**, juntando datasets de Roboflow Universe y, cuando las
# haya, las fotos propias sacadas con las cámaras NoIR del robot. Al final deja en Google Drive:
#
# - `limon_yolo26n.pt`: para usar tal cual en la Pi (el nodo `yolo_ros` carga un `.pt`).
# - `limon_yolo26n_ncnn_model/`: el mismo modelo en NCNN, más rápido en la CPU de la Pi.
#
# **Antes de empezar**
# 1. *Entorno de ejecución → Cambiar tipo de entorno → GPU (T4)*.
# 2. Crear una cuenta gratis en [roboflow.com](https://roboflow.com) y copiar la API key
#    (*Settings → API Keys*). Guardarla en Colab como secreto: ícono de la llave a la izquierda,
#    nombre `ROBOFLOW_API_KEY`, y habilitar el acceso para este cuaderno.
# 3. Revisar en el navegador cada dataset de la lista `DATASETS` (celda 3) y dejar solo los que sirvan:
#    limones **en la planta**, parecidos a los que va a ver el robot.
#
# Fuente: `vision/entrenamiento_limon/entrenar_limon.py` del repo `recolector_de_frutas`. El `.ipynb` se
# genera desde ese archivo: editar el `.py`, no el cuaderno.

# %% [markdown]
# ## 1. GPU y paquetes
# La versión de ultralytics es la misma que tiene la Pi (`~/yolo_env`), para que el `.pt` cargue sin
# problemas allá.

# %%
!nvidia-smi --query-gpu=name,memory.total --format=csv
!pip -q install "ultralytics==8.4.153" roboflow

# %% [markdown]
# ## 2. Google Drive
# Los resultados del entrenamiento se guardan en Drive: si Colab se desconecta, no se pierden.

# %%
from google.colab import drive
drive.mount("/content/drive")

from pathlib import Path
SALIDA = Path("/content/drive/MyDrive/arturito/limon_yolo")
SALIDA.mkdir(parents=True, exist_ok=True)
print("Resultados en", SALIDA)

# %% [markdown]
# ## 3. Datasets
# Cada entrada es `(workspace, proyecto, versión)`, tal como aparece en la URL de Roboflow Universe:
# `universe.roboflow.com/<workspace>/<proyecto>`. Con versión `None` se usa la última.
#
# Candidatos encontrados (**sin revisar las fotos**: mirarlas antes de entrenar):
# - `dip-dqsgr/lime-detection`: ~680 imágenes de lima (limón verde).
# - `smart-harvesting-system/tree-fruit-detection`: ~4 500 imágenes de frutas en el árbol; una de las
#   8 clases es `lime`.
# - `yolo-1zyxa/food-lemons`: limones, probablemente sueltos (no en la planta).
#
# Cuando estén las fotos propias con las cámaras NoIR, subirlas a un proyecto propio de Roboflow,
# etiquetarlas ahí (una caja por limón, clase `limon`) y agregar ese proyecto a la lista.

# %%
DATASETS = [
    ("dip-dqsgr", "lime-detection", None),
    ("smart-harvesting-system", "tree-fruit-detection", None),
    # ("tu-workspace", "limones-noir", None),   # fotos propias con las cámaras del robot
]

# Clases que pasan a ser "limon" (expresión regular, sin distinguir mayúsculas). Las demás etiquetas se
# borran, y sus imágenes quedan como ejemplos de "esto no es un limón" (naranjas, manzanas, hojas...).
CLASES_LIMON = r"lemon|lime|lim[oó]n"
EXCLUIR = r"infect|diseas|leaf|hoja|tree|arbol|árbol|flower|flor"

# %%
import re
from google.colab import userdata
from roboflow import Roboflow

rf = Roboflow(api_key=userdata.get("ROBOFLOW_API_KEY"))
BAJADOS = Path("/content/bajados")
descargas = []
for ws, proyecto, version in DATASETS:
    p = rf.workspace(ws).project(proyecto)
    v = version or max(int(x.version.split("/")[-1]) for x in p.versions())
    d = p.version(v).download("yolov8", location=str(BAJADOS / f"{ws}__{proyecto}__v{v}"), overwrite=True)
    descargas.append(Path(d.location))
    print(f"OK {ws}/{proyecto} v{v}")

# %% [markdown]
# ## 4. Unificar en una sola clase
# Revisar la tabla que imprime esta celda: **cada fila marcada `-> limon` tiene que ser realmente un
# limón o una lima**. Si algo está mal, corregir `CLASES_LIMON` / `EXCLUIR` y volver a correr la celda.

# %%
import shutil, yaml, random

DATOS = Path("/content/datos")
shutil.rmtree(DATOS, ignore_errors=True)
PARTES = {"train": "train", "valid": "val", "val": "val", "test": "test"}

def es_limon(nombre):
    return re.search(CLASES_LIMON, nombre, re.I) and not re.search(EXCLUIR, nombre, re.I)

for d in descargas:
    nombres = yaml.safe_load((d / "data.yaml").read_text())["names"]
    if isinstance(nombres, dict):
        nombres = [nombres[k] for k in sorted(nombres)]
    mapa = {i: 0 for i, n in enumerate(nombres) if es_limon(n)}
    print(f"\n{d.name}")
    for i, n in enumerate(nombres):
        print(f"  {i:2d} {n:30s} {'-> limon' if i in mapa else '(se borra)'}")
    for parte_origen, parte in PARTES.items():
        carpeta = d / parte_origen / "images"
        if not carpeta.exists():
            continue
        (DATOS / parte / "images").mkdir(parents=True, exist_ok=True)
        (DATOS / parte / "labels").mkdir(parents=True, exist_ok=True)
        for img in carpeta.iterdir():
            etiqueta = d / parte_origen / "labels" / (img.stem + ".txt")
            lineas = []
            if etiqueta.exists():
                for linea in etiqueta.read_text().splitlines():
                    campos = linea.split()
                    if campos and int(campos[0]) in mapa:
                        lineas.append(" ".join(["0"] + campos[1:]))
            nombre = f"{d.name}__{img.name}"
            shutil.copy(img, DATOS / parte / "images" / nombre)
            (DATOS / parte / "labels" / (Path(nombre).stem + ".txt")).write_text("\n".join(lineas))

# Si ningún dataset trajo validación, separar el 10 % de train
if not (DATOS / "val").exists():
    imgs = sorted((DATOS / "train" / "images").iterdir())
    random.Random(0).shuffle(imgs)
    for sub in ("images", "labels"):
        (DATOS / "val" / sub).mkdir(parents=True)
    for img in imgs[: max(1, len(imgs) // 10)]:
        et = DATOS / "train" / "labels" / (img.stem + ".txt")
        shutil.move(img, DATOS / "val" / "images" / img.name)
        shutil.move(et, DATOS / "val" / "labels" / et.name)

print()
for parte in ("train", "val", "test"):
    etiquetas = list((DATOS / parte / "labels").glob("*.txt")) if (DATOS / parte).exists() else []
    limones = [len(e.read_text().split("\n")) if e.read_text() else 0 for e in etiquetas]
    print(f"{parte:5s}: {len(etiquetas):5d} imágenes, {sum(limones):6d} limones, "
          f"{limones.count(0):5d} sin limón")

partes = {p: str(DATOS / p / "images") for p in ("train", "val", "test") if (DATOS / p).exists()}
(DATOS / "data.yaml").write_text(yaml.safe_dump({**partes, "nc": 1, "names": ["limon"]}, allow_unicode=True))
print((DATOS / "data.yaml").read_text())

# %% [markdown]
# ## 5. Mirar algunas etiquetas
# Antes de gastar una hora de GPU: comprobar que las cajas verdes caen sobre limones.

# %%
import cv2, matplotlib.pyplot as plt

muestras = random.Random(1).sample(sorted((DATOS / "train" / "images").iterdir()), 8)
fig, ejes = plt.subplots(2, 4, figsize=(20, 10))
for ax, img in zip(ejes.flat, muestras):
    im = cv2.cvtColor(cv2.imread(str(img)), cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    for linea in (DATOS / "train" / "labels" / (img.stem + ".txt")).read_text().splitlines():
        _, cx, cy, bw, bh = map(float, linea.split())
        x0, y0 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
        cv2.rectangle(im, (x0, y0), (x0 + int(bw * w), y0 + int(bh * h)), (0, 255, 0), max(2, w // 200))
    ax.imshow(im); ax.set_title(img.name[-40:], fontsize=8); ax.axis("off")
plt.show()

# %% [markdown]
# ## 6. Entrenar
# `hsv_h` más alto que el de fábrica (0.015): las cámaras NoIR corren el color, sobre todo el verde, y así
# el modelo depende menos del tono exacto. Con `patience` corta sola si deja de mejorar.
# Si Colab se desconecta, correr la celda de *Continuar* que está abajo.

# %%
from ultralytics import YOLO

modelo = YOLO("yolo26n.pt")
modelo.train(
    data=str(DATOS / "data.yaml"),
    epochs=100,
    patience=20,
    imgsz=640,
    batch=16,
    hsv_h=0.05,
    project=str(SALIDA),
    name="entreno",
    exist_ok=True,
)

# %%
# Continuar un entrenamiento cortado (solo si hace falta)
# YOLO(str(SALIDA / "entreno/weights/last.pt")).train(resume=True)

# %% [markdown]
# ## 7. Resultados
# Lo que importa para agarrar limones: **recall** alto (que no se le escapen) con precisión razonable.
# `mAP50` por encima de ~0.8 en validación es un buen primer modelo.

# %%
mejor = YOLO(str(SALIDA / "entreno/weights/best.pt"))
parte_eval = "test" if "test" in partes else "val"
m = mejor.val(data=str(DATOS / "data.yaml"), split=parte_eval, imgsz=640)
print(f"{parte_eval}: precisión {m.box.mp:.3f}  recall {m.box.mr:.3f}  mAP50 {m.box.map50:.3f}  "
      f"mAP50-95 {m.box.map:.3f}")

# Predicciones sobre imágenes que el modelo no vio, al mismo tamaño que usa la Pi (480)
fotos = random.Random(2).sample(sorted((DATOS / parte_eval / "images").iterdir()), 8)
fig, ejes = plt.subplots(2, 4, figsize=(20, 10))
for ax, r in zip(ejes.flat, mejor.predict([str(f) for f in fotos], imgsz=480, conf=0.40, verbose=False)):
    ax.imshow(cv2.cvtColor(r.plot(), cv2.COLOR_BGR2RGB)); ax.axis("off")
plt.show()

# %% [markdown]
# ## 8. Exportar para la Pi
# El nodo de la Pi predice con `imgsz=480`; el NCNN se exporta a ese tamaño.

# %%
shutil.copy(SALIDA / "entreno/weights/best.pt", SALIDA / "limon_yolo26n.pt")
ruta_ncnn = Path(mejor.export(format="ncnn", imgsz=480))
destino = SALIDA / "limon_yolo26n_ncnn_model"
shutil.rmtree(destino, ignore_errors=True)
shutil.copytree(ruta_ncnn, destino)
print("Listo en Drive:")
for f in sorted(SALIDA.iterdir()):
    print("  ", f.name)

# %% [markdown]
# ## 9. Usarlo en la Pi
# Bajar `limon_yolo26n.pt` (o la carpeta NCNN) de Drive a la notebook y copiarlo a la Pi:
#
# ```bash
# scp limon_yolo26n.pt r2d2@100.116.96.71:~/vision_estereo/modelos/
# ```
#
# El nodo `yolo_ros` hoy carga `/home/r2d2/yolo26n.pt` (COCO). Para probar el modelo nuevo hay que
# apuntarlo a `~/vision_estereo/modelos/limon_yolo26n.pt` (o a la carpeta `limon_yolo26n_ncnn_model`).
# Ese cambio va en el repo `vision_estereo`.
