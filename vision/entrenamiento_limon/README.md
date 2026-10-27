# Entrenamiento del detector de limones

Cuaderno de Google Colab que entrena un `yolo26n` de una sola clase (`limon`) juntando datasets de Roboflow
Universe y, cuando estén, fotos propias con las cámaras NoIR del robot. Deja en Drive `limon_yolo26n.pt` y
su versión NCNN (a 480, como predice el nodo `yolo_ros` de la Pi).

| Archivo | Qué es |
|---|---|
| `entrenar_limon.py` | **Fuente** del cuaderno (celdas `# %%`): se edita este |
| `hacer_cuaderno.py` | Genera `entrenar_limon.ipynb` desde el `.py` (`python3 hacer_cuaderno.py`) |
| `entrenar_limon.ipynb` | El cuaderno para subir a Colab (*Archivo → Subir cuaderno*) |

Uso: ver las instrucciones de la primera celda (GPU T4, API key de Roboflow como secreto `ROBOFLOW_API_KEY`,
revisar los datasets de la celda 3).

## Estado

- Cuaderno sin correr todavía en Colab. Probada en la PC la celda que unifica clases (dataset simulado).
- Datasets candidatos encontrados por búsqueda, **sin revisar las fotos** (Roboflow no deja leerlas sin
  navegador): `dip-dqsgr/lime-detection` (~680 imágenes), `smart-harvesting-system/tree-fruit-detection`
  (~4 500, frutas en el árbol, con clase `lime`), `yolo-1zyxa/food-lemons`. Otro posible, en formato COCO y
  con licencia CC BY-NC-SA: CitDet (cítricos en el árbol).
- 27/10: sumados cuatro datasets con limones **amarillos y anaranjados** (maduros), también como `limon`:
  `limoneros/lemon-tree`, `lemon-classification-ai/lemon-detection-ifcwr` (clases `Ripe`/`Unripe`/`Rotten`,
  todas a `limon`), `fruitclassi/new-lemon` y `brinjalproject/lemons-segmentation`. Los de segmentación se
  pasan a cajas. Sin revisar las fotos ni correr en Colab: el modelo de la Pi (28/09) todavía no los tiene.
- Falta: fotos propias con las NoIR (limones verdes reales; las NoIR corren el color del verde).
