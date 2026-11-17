# Entrenamiento del detector de limones

Cuaderno de Google Colab que entrena un `yolo26n` de una sola clase (`limon`) juntando datasets de Roboflow
Universe y, cuando estén, fotos propias con las cámaras NoIR del robot. Deja en Drive `limon_yolo26n_<versión>.pt` (`VERSION`, sección 9) y
su versión NCNN (a 480, como predice el nodo `yolo_ros` de la Pi).

| Archivo | Qué es |
|---|---|
| `entrenar_limon.py` | **Fuente** del cuaderno (celdas `# %%`): se edita este |
| `hacer_cuaderno.py` | Genera `entrenar_limon.ipynb` desde el `.py` (`python3 hacer_cuaderno.py`) |
| `entrenar_limon.ipynb` | El cuaderno para subir a Colab (*Archivo → Subir cuaderno*) |

## Versiones del detector (`versiones/`)

Copia fija del cuaderno con el que salió cada modelo. Los pesos no van en git: están en Drive y en la Pi
(`~/vision_estereo/modelos/`).

| Versión | Cuaderno | Datos | Pesos |
|---|---|---|---|
| v1 (28/09) | `v1_entrenar_limon_2026-09-28.ipynb` (commit `e03901d`) | Roboflow: `lime-detection` + `tree-fruit-detection` (`lime`) | Drive `arturito/limon_yolo_v1`; Pi `limon_yolo26n_ncnn_model` |
| v2 (28/10) | `v2_entrenar_limon_2026-10-28.ipynb` (commit `ea6cf01`) | Solo limones verdes (ver Estado, 28/10) | Drive `arturito/limon_yolo_v2`; Pi `limon_yolo26n_v2_ncnn_model` |
| v3 (07/11, reentrenada 12/11) | `v3_tarea_va_limones_amarillos_2026-11-07.ipynb` (Tarea VA de R2, con salidas) | `brinjalproject/lemons-segmentation` + 50 fotos propias de limones amarillos | Drive `R2_TPF2026S2_limones/`; Pi `limon_yolo26n_v3_ncnn_model` (en uso) |

`entrenar_limon.ipynb` (arriba) es el cuaderno vivo de la línea v1/v2; el de la v3 se edita en Colab y esta es
una copia (el original sigue en `docs/TPF R2/TAREA VA/`, fuera de git).

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
