# Versiones del detector de limones (YOLO26n, una clase `limon`)

Una carpeta por versión: el cuaderno con el que se entrenó y sus resultados. Los pesos (`.pt` y NCNN) no van a git;
están en Drive y en la Pi (`~/vision_estereo/modelos/`).

## v1: 28/09/2026 (limones verdes, solo Roboflow)

- **Cuaderno:** `v1/cuaderno_v1_2026-09-28.ipynb`. Es la fuente del commit `e03901d`, **sin salidas**: la corrida
  ejecutada quedó en Colab.
- **Datos:** `dip-dqsgr/lime-detection` y `smart-harvesting-system/tree-fruit-detection` (solo `lime`).
- **Entrenamiento:** `yolo26n.pt`, 100 épocas (paciencia 20), imgsz 640, batch 16.
- **Test** (285 imágenes, 200 sin limón, 173 limones; mismas fuentes que el entrenamiento, así que es optimista):

  | P | R | mAP50 | mAP50-95 |
  |---|---|---|---|
  | 0,953 | 0,977 | 0,978 | 0,814 |

- **Con las NoIR** (lab, 3 limones verdes, 20 cuadros): ve los 3 en los 20, sin falsos positivos; mediana 0,78.
- **Gráficos:** no están en el repo (quedaron en Drive, `arturito/limon_yolo_v1`).
- **Pesos:** Drive `arturito/limon_yolo_v1`; Pi `limon_yolo26n_ncnn_model`.

## v2: 28/10/2026 (solo limones verdes)

- **Cuaderno:** `v2/cuaderno_v2_2026-10-28.ipynb`, la **corrida ejecutada en Colab**, con salidas (copia de la
  Entrega 8 de R1).
- **Datos:** `lime-detection` (todo), `tree-fruit-detection` (solo `lime`) y `lemons-segmentation` (`good lemon`
  verdes y `lemon yellow`; sin `disease lemon`).
- **Entrenamiento:** 100 épocas (paciencia 20), imgsz 480, batch 16; cortó en la 90 y la mejor fue la 70.
- **Validación (época 70):**

  | P | R | mAP50 | mAP50-95 |
  |---|---|---|---|
  | 0,780 | 0,754 | 0,825 | 0,521 |

- **Test** (335 imágenes, 200 sin limón, 274 limones; mismas fuentes):

  | P | R | mAP50 | mAP50-95 |
  |---|---|---|---|
  | 0,894 | 0,832 | 0,919 | 0,709 |

- **Con las NoIR** (los mismos 20 cuadros que la v1): ve los 3, sin falsos positivos; mediana 0,79, empate con la v1.
- **Gráficos:** `v2/resultados/` (curvas P, R, F1 y PR, matrices de confusión, `results.png` y `results.csv`,
  lotes de entrenamiento y validación).
- **Prueba con foto propia:** `v2/prueba_foto_propia/` (capturas de Colab del 28/10; limón verde en maceta, 0,74).
- **Pesos:** Drive `arturito/limon_yolo_v2`; Pi `limon_yolo26n_v2_ncnn_model`.

## v3: 12/11/2026 (limones amarillos y fotos propias; en uso)

- **Cuaderno:** `v3/cuaderno_v3_2026-11-12.ipynb`, la corrida ejecutada de la Tarea VA de R2, con salidas. El
  original es `docs/TPF R2/TAREA VA/[2026S2]_R2_TPF2026S2_VA_Limones_G2_V2.ipynb`.
- **Datos:** `brinjalproject/lemons-segmentation` v5 (solo `Lemon yellow`) y el dataset propio `limones-amarillos`
  v3 (50 fotos con celular, 30/10/10, train ×3).
- **Entrenamiento:** 60 épocas (paciencia 20), imgsz 640, batch 16; cortó en la 51 y la mejor fue la 31.
- **Validación propia (época 31):**

  | P | R | mAP50 | mAP50-95 |
  |---|---|---|---|
  | 1,000 | 0,925 | 0,974 | 0,777 |

- **Con las NoIR:** detecta el limón (a ojo, sin cifras). En el arbusto, con el robot quieto, detectó el 100 % y
  el error en Z fue de +7 a +11 mm. En la Pi tarda 68 ms por imagen a 480.
- **Gráficos:** `v3/resultados/` (mismo contenido que la v2).
- **Pesos:** Drive `Mi unidad/R2_TPF2026S2_limones/`; Pi `limon_yolo26n_v3_ncnn_model`.

> Las cifras de la entrega de la Tarea VA son las de la corrida del 07/11 (20 fotos propias: P 0,929, R 0,922,
> mAP50 0,952), no las de esta.
