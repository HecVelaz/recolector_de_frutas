# Entrenamiento del detector de limones

Cuaderno de Google Colab que entrena un `yolo26n` de una sola clase (`limon`) juntando datasets de Roboflow
Universe y, cuando estén, fotos propias con las cámaras NoIR del robot. Deja en Drive `limon_yolo26n.pt` y
su versión NCNN (a 480, como predice el nodo `yolo_ros` de la Pi).

| Archivo | Qué es |
|---|---|
| `entrenar_limon.py` | **Fuente** del cuaderno (celdas `# %%`): se edita este |
| `hacer_cuaderno.py` | Genera `entrenar_limon.ipynb` desde el `.py` (`python3 hacer_cuaderno.py`) |
| `entrenar_limon.ipynb` | El cuaderno para subir a Colab (*Archivo → Subir cuaderno*) |

Formato (desde el 27/10): el del cuaderno de la clase del profesor (`vision/CLASE_27_10_26/`, frutillas):
secciones numeradas y comentadas, estadísticas por dataset, chequeo de B4, matriz de confusión, etiqueta contra
predicción y prueba con una foto propia. La localización (sección 11) se explica, pero la hace el estéreo en la Pi.

Uso: ver las instrucciones de la primera celda (GPU T4, API key de Roboflow como secreto `ROBOFLOW_API_KEY`,
revisar los datasets de la celda 3).

## Estado

- Cuaderno sin correr todavía en Colab. Probada en la PC la celda que unifica clases (dataset simulado).
- Datasets candidatos encontrados por búsqueda, **sin revisar las fotos** (Roboflow no deja leerlas sin
  navegador): `dip-dqsgr/lime-detection` (~680 imágenes), `smart-harvesting-system/tree-fruit-detection`
  (~4 500, frutas en el árbol, con clase `lime`), `yolo-1zyxa/food-lemons`. Otro posible, en formato COCO y
  con licencia CC BY-NC-SA: CitDet (cítricos en el árbol).
- 27/10: sumados tres datasets con limones **amarillos y anaranjados** (maduros), también como `limon`:
  `lemon-classification-ai/lemon-detection-ifcwr` (clases `Ripe`/`Unripe`/`Rotten`,
  todas a `limon`), `fruitclassi/new-lemon` y `brinjalproject/lemons-segmentation` (segmentación, se
  pasa a cajas). Descartado `limoneros/lemon-tree`: árboles desde arriba. Sin revisar las fotos ni correr en Colab: el modelo de la Pi (28/09) todavía no los tiene.
- 28/10: clases elegidas por dataset (pedido del usuario): `lime-detection` todo (verdes); `tree-fruit-detection`
  solo `lime`; `lemon-detection-ifcwr` solo `Ripe`; `new-lemon` solo `good lemon`; `lemons-segmentation` solo
  `lemon yellow`, `lemons - segmentation` y `good lemon`. Las imágenes con limones de clases descartadas
  (`Unripe`, `Rotten`, `Raw_lemon`…) se sacan enteras (`DUDOSAS`), para no enseñarle que un limón es fondo.
- 28/10 (2): **solo limones verdes** (el robot cosecha verdes; la madurez se decide por tamaño con el estéreo,
  no con YOLO). Quedan `lime-detection` (todo), `tree-fruit-detection` (solo `lime`) y `lemons-segmentation`
  (`good lemon` verdes y `lemon yellow`; las imágenes con `disease lemon` se sacan). Quitados `lemon-detection-ifcwr`
  y `new-lemon` (amarillos sueltos).
- Falta: fotos propias con las NoIR (limones verdes reales; las NoIR corren el color del verde).
