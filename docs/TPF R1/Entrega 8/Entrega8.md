---
**UNIVERSIDAD NACIONAL DE ASUNCIÓN**

**FACULTAD DE INGENIERÍA**

# **ROBÓTICA I**

TRABAJO PRÁCTICO FINAL 2026S2

## **"Robot móvil recogedor de frutas"**

<!-- celda -->
---
###**Grupo [2]:**

---

*   Pablo Junior Otazu Lujan
*   Gabriela Belén Orrego Arzamendia
*   Héctor Dejesús Velázquez Ojeda
*   Mathias Ramón Aguilar Delvalle

**ENTREGA [8]:**  Sistema de visión artificial (Demo)

**Fecha:** 01/11/2026

**Versión:** [1.1]

<!-- celda -->
---
## **Resumen**

Esta entrega documenta el sistema de visión del robot "Arturito R2D2". Lo que está terminado y probado es la **detección**: las cámaras del robot buscan el limón en la planta y una red YOLO lo marca en la imagen. El cálculo de la posición del limón en metros con visión estéreo, que necesita el brazo para ir a agarrarlo, **queda pendiente**: se describe el diseño previsto. El informe sigue los cuatro puntos de la consigna:

| # | Sección | Punto de la consigna |
| :---: | :--- | :--- |
| 1 | Tarea de visión: objetivo, resultado esperado, componentes, interfaces y diagrama de bloques | 1 |
| 2 | Setup de captura de imágenes: cámaras, montaje y calibración | 2 |
| 3 | Detector YOLO: datos, entrenamiento y resultados | 3 |
| 4 | Código de detección y localización (se puede ejecutar en este cuaderno) | 3 |
| 5 | Video demo | 4 |
| 6 | Limitaciones y trabajo pendiente | — |
| 7 | Referencias | — |

#### Estado del sistema de visión en esta entrega

| Parte | Estado |
| :--- | :--- |
| Detector YOLO26n, clase `limon` (modelo v2) | Entrenado en Colab. En el conjunto de prueba: precisión 0,894 y recobrado 0,832. Ya corre en la Raspberry Pi del robot: en el laboratorio detectó 3 de 3 limones en 20 imágenes de las cámaras NoIR |
| Visión estéreo (calibración, disparidad SGBM, localizador) | **Pendiente.** Calibración, disparidad y localizador programados y con ensayos preliminares en banco (sección 4.2), pero sin terminar ni validar: falta recalibrar el par en el mástil y medir el error con limones a distancias conocidas |
| Cámaras en el robot | Montadas en el mástil, junto con la Raspberry Pi 5 (Figs. 7 a 14). La detección ya funciona en esa posición |
| Paso de la posición del limón al brazo (`tf2`, la librería de ROS 2 que convierte coordenadas entre sistemas) | Programado y probado en simulación. Falta medir la posición real de las cámaras respecto del brazo |
| Madurez por tamaño | No implementada todavía |

<!-- celda -->
---
## **1. Tarea de visión**

<!-- celda -->
#### Objetivo

Cuando el robot se detiene frente al limonero, el sistema de visión responde dos preguntas:

1. **¿Hay un limón en la imagen, y dónde?** Una red YOLO marca cada limón con una caja y una confianza.
2. **¿A qué distancia está?** Las dos cámaras forman un par estéreo. Con la diferencia entre las dos imágenes (disparidad) se calcula la posición $(X, Y, Z)$ del limón en metros. **Esta parte está pendiente.**

Con esa posición, la cinemática inversa calcula los ángulos de J1, J2 y J3 para llevar la pinza hasta el limón. La visión reemplaza a una persona que diga "el limón está acá".

Es el esquema habitual de los robots cosechadores con visión: primero reconocer el fruto y después localizarlo en el espacio [2]. Font et al. [1] lo aplicaron con una cámara estéreo de bajo costo y un brazo robótico, igual que en este robot.

#### Resultado esperado

| Salida | Formato | Criterio de aceptación |
| :--- | :--- | :--- |
| Detección del limón (**esta entrega**) | Caja $(u, v, \text{ancho}, \text{alto})$ en píxeles y confianza entre 0 y 1 | Precisión y recobrado de 0,80 o más (requisito B4 de la guía) |
| Posición del limón (**pendiente**) | $(X, Y, Z)$ en metros, en el sistema óptico rectificado de la cámara izquierda. Es un punto de la superficie que ve la cámara: `mision` lo corre 3 cm (el radio de un limón) para obtener el centro | Error de 35 mm o menos (requisito B5 de la guía) |
| Imagen anotada | Imagen con las cajas dibujadas | Que el operador vea qué detecta el robot |

El sistema trabaja con el robot **quieto**: las dos cámaras no disparan al mismo tiempo, así que con el robot en movimiento las dos imágenes no coincidirían.

#### Componentes

| Componente | Cantidad | Función |
| :--- | :---: | :--- |
| Raspberry Pi Camera Module 3 NoIR (sensor IMX708) | 2 | Tomar las imágenes izquierda y derecha |
| Soporte de las cámaras, en un mástil sobre la base | 1 | Sostener las dos cámaras a 90 mm una de otra y la Raspberry Pi 5; si se mueve, hay que recalibrar |
| Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy) | 1 | Procesar las imágenes: detección, disparidad y localización. Todo corre en la CPU, sin GPU |
| ESP32-WROOM-32D | 1 | Recibir los ángulos del brazo por USB (micro-ROS) y mover los motores |
| Google Colab (GPU T4) | — | Entrenar el detector; no va en el robot |

#### Interfaces

Los nodos de ROS 2 se comunican por tópicos. En la Fig. 1, algunos bloques agrupan dos nodos (captura y rectificación de cada cámara):

| Tópico | Tipo de mensaje | Publica | Lo usa |
| :--- | :--- | :--- | :--- |
| `/left/image_rect`, `/right/image_rect` | `sensor_msgs/Image` | `rectify_left`, `rectify_right` (paquete `image_proc`) | detector y disparidad |
| `/left/camera_info` | `sensor_msgs/CameraInfo` | nodo de la cámara izquierda (`camera_ros`) | localizador: toma el centro óptico de la calibración |
| `/disparity` | `stereo_msgs/DisparityImage` | `disparity` (paquete `stereo_image_proc`, SGBM) | localizador |
| `/yolo/detecciones` | `vision_msgs/Detection2DArray` | `detector_node` | localizador |
| `/yolo/left/image_annotated` | `sensor_msgs/Image` | `detector_node` | pantalla del operador |
| `/limon/posicion` | `geometry_msgs/PointStamped` [m] | `localizador_node` | `mision` |
| `/brazo/objetivo` | `geometry_msgs/PointStamped` [m] | `mision` (con `tf2`) | `brazo_ik` |
| `/brazo/joint_cmd` | `sensor_msgs/JointState` [rad] | `brazo_ik` | ESP32 del brazo |

Las cámaras se conectan a la Pi por **CSI** (cinta plana) y el ESP32 por **USB**.

<!-- celda -->
### **1.1 Diagrama de bloques**

<!-- celda -->
<p align="center">
  <img src="https://lh3.googleusercontent.com/d/18tOV0IkDOgn7ID_Xsw-PA0xZ7EvbNp2A=w2400" width="900" alt="Diagrama de bloques del sistema de visión" />
  <br>
  <b>Fig. 1.</b> Diagrama de bloques del sistema de visión. En verde, los dos nodos desarrollados para este trabajo: el detector (probado en esta entrega) y el localizador (pendiente). Las flechas indican los tópicos de ROS 2.
</p>

El recorrido de una imagen por el diagrama de la Fig. 1 es el siguiente:

1. Cada cámara toma una imagen y `image_proc` la **rectifica**: corrige la distorsión de la lente y alinea las dos imágenes, para que un mismo punto quede en la misma fila en ambas.
2. `detector_node` corre **YOLO** sobre la imagen izquierda y publica una caja por cada limón.
3. `stereo_image_proc` compara las dos imágenes con **SGBM**, una variante del *semi-global matching* que también se usa para estimar la profundidad de frutos en robots cosechadores [6], y calcula la **disparidad** de cada píxel: cuánto se corre entre la imagen izquierda y la derecha.
4. `localizador_node` junta la caja con la disparidad, intenta separar el limón de las hojas que están detrás y publica la posición de su superficie en metros.
5. `mision` corre ese punto 3 cm hacia adentro para estimar el centro del limón y lo pasa al sistema de la base del brazo con `tf2`. Después, `brazo_ik` calcula los ángulos de las articulaciones.

<!-- celda -->
---
## **2. Setup de captura de imágenes**

<!-- celda -->
#### Cámaras

Se usan dos cámaras Raspberry Pi Camera Module 3 **NoIR**, que no tienen filtro infrarrojo. Ya estaban disponibles en el laboratorio. Ven bien con poca luz; al sol, los colores salen corridos hacia el rosado (sección 6). La Fig. 2 muestra el modelo de cámara. Cada cámara se conecta a la Raspberry Pi 5 con una cinta plana por el puerto **CSI** (Figs. 3 y 4).

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1FZm4lSCPdtrIkh_0IrvnPK-3t0xWC_Zm=w2400" width="400" alt="Cámara" />
  <br>
  <b>Fig. 2.</b> Cámara Raspberry Pi Camera Module 3 NoIR (imagen del fabricante). El par estéreo usa dos.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG3=w2400" height="300" alt="Raspberry Pi 5" />
  <img src="https://lh3.googleusercontent.com/d/ID_FIG4=w2400" height="300" alt="Cámara conectada por CSI" />
  <br>
  <b>Fig. 3.</b> Raspberry Pi 5, la computadora que procesa las imágenes (imagen del fabricante). <b>Fig. 4.</b> Conexión de una cámara a la Raspberry Pi 5 por la cinta CSI (imagen de referencia).
</p>

| Parámetro | Valor | Por qué |
| :--- | :--- | :--- |
| Resolución | 640 × 480 px | Con esta resolución, la Pi calcula la disparidad a unas 2,5 imágenes por segundo y corre YOLO a 4 o 5 |
| Modo del sensor | Completo (2304 × 1296), reducido a 640 × 480 | Más campo de visión que el modo por defecto |
| Campo de visión horizontal | ≈ 52° (focal de 654 px) | Calculado con la calibración |
| Cuadros por segundo | 10, fijos en las dos cámaras | Si se deja libre, con poca luz cada cámara elige otra exposición y las imágenes no coinciden. No hace falta más: la disparidad no pasa de 2,5 por segundo |
| Foco | Fijo, ajustado por cámara con un tablero a 55 cm | Un cambio de foco cambia la calibración |
| Separación entre cámaras (*baseline*) | 89,5 mm (calibrado el 01/10; con regla, 90 mm) | Elegida para medir entre 0,4 y 1 m |
| Orientación | Cámaras montadas cabeza abajo en el soporte | La imagen se gira 180° por software, en la captura |
| Distancia de trabajo | 0,38 a 0,96 m | El rango en el que se busca la disparidad |

<!-- celda -->
#### Montaje

Las cámaras y la Raspberry Pi 5 van en un **soporte impreso en 3D** (diseño en la Fig. 6), arriba de un **mástil** fijado a la base del robot (Figs. 10 a 14). Las cámaras miran hacia el limonero, que en el laboratorio es una planta en maceta (Figs. 7 a 9). La Fig. 5 muestra la geometría prevista en vista superior; la altura y la inclinación finales se miden con el robot armado.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1-46bdhtaXrDMPti-Co7qvd3-FMhHN_B-=w2400" width="900" alt="Setup de captura previsto" />
  <br>
  <b>Fig. 5.</b> Setup de captura previsto en el robot, en vista superior. La zona amarilla es la región donde el par estéreo va a medir la distancia (0,38 a 0,96 m).
</p>

<!-- PENDIENTE: subir Evidencias/Fig3_, Fig4_ y Fig6_ a Fig14_ a Drive y poner sus IDs en lugar de ID_FIG3 ... ID_FIG14 -->
<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG6=w2400" width="700" alt="Diseño CAD del soporte" />
  <br>
  <b>Fig. 6.</b> Diseño en CAD del soporte de las cámaras. El aro se encastra en el mástil, la placa lleva la Raspberry Pi 5 y las cámaras se atornillan en el ala vertical.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG7=w2400" height="330" alt="Estación de prueba" />
  <img src="https://lh3.googleusercontent.com/d/ID_FIG8=w2400" height="330" alt="Robot frente al limonero" />
  <br>
  <b>Fig. 7.</b> Estación de prueba en el laboratorio: el robot, con el brazo y el mástil de las cámaras, y el limonero en maceta. <b>Fig. 8.</b> El robot frente al limonero de prueba.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG9=w2400" height="330" alt="Otra vista de la estación" />
  <img src="https://lh3.googleusercontent.com/d/ID_FIG10=w2400" height="330" alt="Mástil sobre la base" />
  <br>
  <b>Fig. 9.</b> Otra vista de la estación: base, brazo y limonero. <b>Fig. 10.</b> El mástil sobre la base del robot, con el soporte de las cámaras arriba.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG11=w2400" height="330" alt="Soporte de las cámaras, vista frontal" />
  <img src="https://lh3.googleusercontent.com/d/ID_FIG12=w2400" height="330" alt="Detalle del soporte" />
  <br>
  <b>Fig. 11.</b> Soporte de las cámaras, vista frontal: una cámara en cada extremo y la Raspberry Pi 5 en el centro. <b>Fig. 12.</b> Detalle de las dos cámaras NoIR, separadas 90 mm, con sus cintas CSI hacia la Pi.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG13=w2400" height="330" alt="Soporte visto desde un costado" />
  <img src="https://lh3.googleusercontent.com/d/ID_FIG14=w2400" height="330" alt="Vista lateral con la Raspberry Pi 5" />
  <br>
  <b>Fig. 13.</b> El soporte fijado al mástil, visto desde un costado. <b>Fig. 14.</b> Vista lateral: la Raspberry Pi 5 sobre el soporte, con su disipador y las cintas CSI de las dos cámaras.
</p>

**Condiciones de captura:**

* El robot se detiene antes de tomar las imágenes, porque las dos cámaras no disparan sincronizadas.
* El limón tiene que quedar entre 0,38 y 0,96 m de las cámaras. Más cerca, la disparidad se sale del rango de búsqueda; más lejos, el error crece con el cuadrado de la distancia.
* Un limón que cae en el borde izquierdo de la imagen izquierda (u < 163 px) se detecta, pero no se puede localizar: no aparece en la imagen derecha dentro del rango de búsqueda.

<!-- celda -->
#### Calibración

Para calcular distancias hay que conocer bien cada cámara y la posición de una respecto de la otra. Se fotografió un tablero de ajedrez (9 × 6 esquinas, cuadros de 25 mm) en 34 posiciones (Fig. 15). Con esas fotos, las funciones de calibración estéreo de OpenCV calcularon la focal, la distorsión de cada lente y la posición relativa de las dos cámaras.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/188XzGBPuh9FpO7W2wFS0yFkt_ZIbtZ2u=w2400" width="800" alt="Par de calibración" />
  <br>
  <b>Fig. 15.</b> Uno de los 34 pares de imágenes de la calibración: cámara izquierda (izq.) y derecha (der.). El tablero aparece corrido entre las dos: esa diferencia es la disparidad.
</p>

| Resultado de la calibración (01/10/2026, soporte de banco) | Valor |
| :--- | :--- |
| Error de reproyección (RMS) | 0,36 px |
| Error vertical entre imágenes rectificadas | 0,08 px (medio) |
| Separación entre cámaras calculada | 89,5 mm |
| Distancia focal | 654,3 px |

Si el soporte se mueve o se cambia el foco, hay que **recalibrar**. Al montarlas en el mástil, las cámaras quedaron cabeza abajo y las dos imágenes muestran un desnivel vertical de unos 25 px: **la calibración del 01/10 ya no vale en el robot**. Se va a repetir con el mismo tablero antes de medir distancias. La detección no depende de la calibración y ya funciona en esta posición.

<!-- celda -->
---
## **3. Detector YOLO**

<!-- celda -->
**¿Por qué YOLO?** *You Only Look Once* es una familia de redes de detección de objetos [3]. En una sola pasada entrega, para cada objeto, una caja, una clase y una confianza. Es rápida, y ya se usó para detectar limones en su ambiente natural [4].

Se usa **YOLO26n** de la biblioteca Ultralytics [7], la versión más chica, porque tiene que correr en la CPU de la Raspberry Pi 5. Se parte de una red preentrenada en COCO, un dataset de 80 clases de objetos comunes, y se ajusta a una sola clase nueva, `limon` (*transfer learning*).

Alcanza con **detección** (cajas), sin segmentación: el centro de la caja indica hacia dónde está el limón, y la distancia la va a dar el estéreo.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1Y4Xa-2wz8JddWXtEwnGgcxfpWPjlQPuS=w2400" width="900" alt="Flujo del detector" />
  <br>
  <b>Fig. 16.</b> Del dataset al detector que corre en el robot.
</p>

La Fig. 16 resume el proceso. El entrenamiento completo está en el cuaderno [entrenar_limon.ipynb](LINK_CUADERNO_ENTRENAMIENTO), que se entrega junto con este.

<!-- celda -->
#### Datos

Se juntaron tres datasets públicos de Roboflow Universe. Todas las etiquetas de limón pasan a la clase `limon`. Las imágenes con otras frutas (naranjas, manzanas…) se dejan sin etiquetas, como ejemplos de "esto no es un limón". Las imágenes con limones enfermos se sacan enteras: si quedaran sin etiqueta, el modelo aprendería que ese limón es fondo.

| Dataset | Qué aporta | Imágenes (train / val / test) | Limones etiquetados |
| :--- | :--- | :---: | :---: |
| [brinjalproject/lemons-segmentation](https://universe.roboflow.com/brinjalproject/lemons-segmentation) | Limones en el árbol, lo más parecido a lo que ve el robot | 1925 / 650 / 50 | 4580 |
| [dip-dqsgr/lime-detection](https://universe.roboflow.com/dip-dqsgr/lime-detection) | Limones verdes | 1557 / 117 / 46 | 3054 |
| [smart-harvesting-system/tree-fruit-detection](https://universe.roboflow.com/smart-harvesting-system/tree-fruit-detection) | Frutas en el árbol; solo la clase `lime` es limón | 3553 / 710 / 239 | 900 |
| **Total** | | **7035 / 1477 / 335** | **8534** |

De las 8847 imágenes, 4127 no tienen ningún limón. Sirven para que el modelo no marque hojas ni otras frutas.

#### Entrenamiento

| Parámetro | Valor | Motivo |
| :--- | :--- | :--- |
| Modelo base | YOLO26n preentrenado en COCO | El más liviano; corre en la Pi |
| Tamaño de imagen | 480 px | El mismo con el que predice la Pi |
| Épocas | 100 como máximo; paró en la 90 (la mejor fue la 70) | Parada temprana: 20 épocas sin mejorar |
| Lote (*batch*) | 16 | Lo que entra en la memoria de la T4 |
| Variación de tono (`hsv_h`) | 0,05 (de fábrica: 0,015) | Las NoIR corren el color; así el modelo depende menos del verde exacto |
| Tiempo | ≈ 3 h en una GPU T4 de Colab | |

<!-- celda -->
#### Resultados

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1yqa8vF8MsLOyJRqCcFh3InlAPBu68-ub=w2400" width="900" alt="Curvas de entrenamiento" />
  <br>
  <b>Fig. 17.</b> Curvas de entrenamiento, por época. Arriba, las pérdidas sobre las imágenes de entrenamiento, la precisión y el recobrado; abajo, las pérdidas de validación y las dos mAP.
</p>

La Fig. 17 muestra cómo mejoró el modelo durante el entrenamiento. Resultado final sobre el **conjunto de prueba**: 335 imágenes que el modelo no vio al entrenar, con 274 limones y 200 imágenes sin limón.

| Métrica | Qué mide | Valor |
| :--- | :--- | :---: |
| Precisión (P) | De las cajas que marca, cuántas son limones | **0,894** |
| Recobrado (R) | De los limones que hay, cuántos encuentra | **0,832** |
| mAP50 | Resume precisión y recobrado para todos los umbrales de confianza. Una caja cuenta como acierto si se superpone al menos 50 % con la real (IoU ≥ 0,5) | 0,919 |
| mAP50-95 | Lo mismo, promediando exigencias de superposición de 50 a 95 % | 0,709 |

**En este conjunto de prueba supera los umbrales del requisito B4** (P y R de 0,80 o más). Estos números son algo optimistas: las imágenes de prueba vienen de las mismas fuentes que las de entrenamiento. Falta medir P y R con un set propio de fotos tomadas por las cámaras NoIR del robot. La Fig. 18 muestra los errores en validación y la Fig. 19, ejemplos de predicciones.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1_uZyYC9sqZqL3eMc2kwCZOqO0Vw-MZa-=w2400" width="900" alt="Matriz de confusión" />
  <br>
  <b>Fig. 18.</b> Matriz de confusión normalizada (validación). Cuenta los limones que el modelo confunde con fondo y las cajas que marca sobre el fondo.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1DtRCLK73LE2oCPNKdYP4Ot_cZu8QU2q6=w2400" width="800" alt="Predicciones en validación" />
  <br>
  <b>Fig. 19.</b> Predicciones del modelo sobre 16 imágenes de validación de limones en el árbol. Cada caja azul lleva la confianza. Hay limones lejanos o tapados por hojas que quedan sin marcar.
</p>

**Prueba con fotos propias.** El modelo también se probó con 6 fotos propias de limoneros en maceta (Fig. 20). Ninguna estaba en el entrenamiento, y no se tomaron con las cámaras del robot. Marcó 8 limones, con confianzas entre 0,71 y 0,79, sin falsos positivos. En la primera foto no detectó un segundo limón medio tapado por las hojas: la oclusión por hojas y ramas es una dificultad conocida en la detección de cítricos [5].

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1Q9oHDZBDLJJfrZMsVBtG_MPQ_Jd7CgFg=w2400" width="900" alt="Detección en fotos propias" />
  <br>
  <b>Fig. 20.</b> Detección del modelo v2 sobre fotos propias de limoneros en maceta, con umbral de confianza de 0,40.
</p>

**Prueba en el robot, con las cámaras NoIR.** Con el modelo ya en la Raspberry Pi, se compararon la v1 y la v2 sobre las mismas 20 imágenes rectificadas de la cámara izquierda. La escena era el limonero en maceta con 3 limones verdes, a entre 0,5 y 1 m, en el laboratorio. Las dos versiones detectaron los 3 limones en las 20 imágenes, sin falsos positivos, con una confianza mediana de 0,78 (v1) y 0,79 (v2). Falta repetir la prueba al aire libre, con sol.

**En la Raspberry Pi** el modelo se exporta a **NCNN**, un formato optimizado para procesadores ARM. Con la v1 se midieron 23 imágenes por segundo con el detector solo. Dentro de la cadena completa, que comparte la CPU con la disparidad, la v2 procesa 4 a 5 imágenes por segundo: alcanza, porque el robot se detiene para localizar.

<!-- celda -->
---
## **4. Código de detección**

<!-- celda -->
El código tiene dos partes:

* **4.1 y 4.2:** se pueden **ejecutar en este cuaderno**. La 4.1 detecta limones en una imagen (lo probado en esta entrega). La 4.2 muestra cómo se va a calcular la posición 3D, con datos sintéticos (pendiente en el robot).
* **4.3:** los nodos de ROS 2 que corren en la Raspberry Pi. Se muestran como referencia; no se ejecutan en Colab.

### **4.1 Detección en una imagen**

Primero se instala `ultralytics` y se carga el modelo v2 desde Google Drive. El modelo está en la carpeta de la entrega: `Entrega 8/arturito_v2/limon_yolo_v2/limon_yolo26n_v2.pt`.

> **Para correrlo desde otra cuenta:** la celda busca el modelo en "Mi unidad". Si la carpeta compartida no está ahí, la celda pide subirlo a mano: hay que bajar `limon_yolo26n_v2.pt` de la carpeta de la entrega (unos 5 MB) y elegirlo en el botón. La otra opción es agregar antes un acceso directo de la carpeta "TPF R1 Grupo 2" en "Mi unidad" (clic derecho → *Organizar* → *Agregar acceso directo*); así la celda lo encuentra sola.

<!-- celda -->
```python
# Instalamos ultralytics (YOLO). -q (quiet) reduce los mensajes en pantalla.
!pip install -q ultralytics

from pathlib import Path
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from google.colab import drive, files
from ultralytics import YOLO

# Montamos Drive y cargamos el modelo v2 (pesos de PyTorch, entrenados en entrenar_limon.ipynb).
drive.mount("/content/drive")
CARPETAS = ["/content/drive/MyDrive/TPF R1 Grupo 2/Entrega 8/arturito_v2/limon_yolo_v2",  # carpeta de la entrega
            "/content/drive/MyDrive/arturito/limon_yolo_v2"]
MODELO = next((Path(c) / "limon_yolo26n_v2.pt" for c in CARPETAS if (Path(c) / "limon_yolo26n_v2.pt").exists()), None)
if MODELO is None:
    # No está en esas carpetas: lo buscamos en todo el Drive (puede tardar).
    MODELO = next(Path("/content/drive/MyDrive").rglob("limon_yolo26n_v2.pt"), None)
while MODELO is None or MODELO.suffix != ".pt":
    # Sin acceso al Drive del grupo: subir a mano el archivo del modelo (.pt), no una foto.
    print("No se encontró el modelo: elegir el archivo limon_yolo26n_v2.pt")
    MODELO = Path(next(iter(files.upload())))
print("Modelo:", MODELO)
modelo = YOLO(str(MODELO), task="detect")
print("Clases del modelo:", modelo.names)
```

<!-- celda -->
La celda siguiente pide una o más fotos y corre el detector con los mismos parámetros que el robot: imagen de 480 px y confianza mínima de 0,40. Para cada limón muestra la caja que recibe el localizador: centro $(u, v)$, ancho y alto en píxeles, y confianza.

<!-- celda -->
```python
CONF_MIN = 0.40   # confianza mínima, la misma que usa detector_node en la Pi
IMGSZ = 480       # tamaño de imagen, el mismo del entrenamiento

for nombre in files.upload():
    r = modelo.predict(nombre, imgsz=IMGSZ, conf=CONF_MIN, verbose=False)[0]

    # Imagen con las cajas dibujadas (equivale a /yolo/left/image_annotated).
    plt.figure(figsize=(10, 8))
    plt.imshow(cv2.cvtColor(r.plot(), cv2.COLOR_BGR2RGB))
    plt.title(f"{nombre}: {len(r.boxes)} limones")
    plt.axis("off")
    plt.show()

    # Una fila por limón: lo mismo que publica /yolo/detecciones.
    cajas = pd.DataFrame(r.boxes.xywh.tolist(), columns=["u [px]", "v [px]", "ancho [px]", "alto [px]"])
    cajas["confianza"] = r.boxes.conf.tolist()
    display(cajas.round(2))
```

<!-- celda -->
### **4.2 De la caja a la posición 3D (pendiente)**

La localización con visión estéreo **todavía no está terminada ni validada en el robot**. Esta sección muestra el método previsto y su función, probada solo con datos sintéticos.

**Lo que ya se hizo.** Con las cámaras en un soporte de banco, antes de montarlas en el robot:

* Se calibró el par estéreo (sección 2).
* Se compararon dos algoritmos de disparidad de OpenCV. **BM** es más rápido, pero da un mapa con mucho ruido. **SGBM** es más lento (unas 2,5 imágenes por segundo en la Pi), pero más limpio. Se eligió SGBM, porque el robot se detiene para localizar.
* Se programó el localizador y se hicieron ensayos preliminares con un limón real, entre 0,4 y 0,9 m. Los errores rondaron uno o dos centímetros.

Esos ensayos no se documentaron con imágenes y se hicieron con otro montaje, así que no se presentan como resultado. Se van a repetir con las cámaras en el mástil, después de recalibrar.

Con un par estéreo rectificado, la distancia de un punto sale de su disparidad $d$, la focal $f$ (en píxeles) y la separación $B$ entre cámaras:

$$Z = \frac{f \, B}{d}, \qquad X = \frac{(u - c_x)\,Z}{f}, \qquad Y = \frac{(v - c_y)\,Z}{f}$$

donde $(c_x, c_y)$ es el centro óptico de la imagen. Por ejemplo, un limón a 40 cm se corre 146 px entre las dos imágenes, y uno a 90 cm, 65 px.

La caja de YOLO no tiene solo limón: también tiene hojas o ramas detrás. Por eso la función `posicion` no promedia toda la caja:

1. Toma la zona central de la caja (la mitad del ancho y del alto).
2. Ordena las profundidades de esos píxeles y corta donde hay un **salto de más de 5 cm**. Ese salto suele separar el limón del fondo.
3. Se queda con el grupo más cercano que tenga al menos 15 píxeles, recortado a sus primeros 8 cm de profundidad (un limón mide unos 6 cm), y devuelve la mediana de su $(X, Y, Z)$.

Es una heurística: supone que el limón es lo primero que se ve dentro de la caja. Si una hoja lo tapa por delante, puede quedarse con la hoja.

Es el mismo código que corre en el robot (`localizar.py`, en el repositorio `vision_estereo`).

<!-- celda -->
```python
# Parámetros del localizador
FRACCION_CENTRAL = 0.5  # lado de la zona central de la caja que se usa, relativo a la caja
SALTO_M = 0.05          # salto de profundidad que separa el limón del fondo (hojas, ramas) [m]
EXTENSION_M = 0.08      # profundidad máxima del grupo: un limón mide ~6 cm [m]
MIN_PUNTOS = 15         # puntos mínimos para aceptar un grupo


# --------
# Función que calcula la posición 3D de un objeto a partir de su caja y de la disparidad.
#   - Recibe: disp (disparidad en píxeles, matriz alto x ancho), caja (u, v, ancho, alto) en píxeles,
#     f y t (focal [px] y baseline [m]), cx y cy (centro óptico [px]) y el rango de trabajo [m].
#   - Devuelve: (x, y, z, puntos) en metros, en el sistema óptico rectificado de la cámara izquierda
#     (x a la derecha, y hacia abajo, z hacia adelante), o None si no lo pudo localizar.
# --------
def posicion(disp, caja, f, t, cx, cy, z_min=0.15, z_max=2.0, min_disparidad=0.0):
    u, v, ancho, alto = caja
    alto_img, ancho_img = disp.shape
    medio_u = max(1.0, ancho * FRACCION_CENTRAL / 2.0)
    medio_v = max(1.0, alto * FRACCION_CENTRAL / 2.0)
    u0, u1 = int(max(0, np.floor(u - medio_u))), int(min(ancho_img, np.ceil(u + medio_u)))
    v0, v1 = int(max(0, np.floor(v - medio_v))), int(min(alto_img, np.ceil(v + medio_v)))
    if u0 >= u1 or v0 >= v1:
        return None

    # Profundidad de cada píxel válido de la zona central: Z = f·B/d.
    vv, uu = np.mgrid[v0:v1, u0:u1]
    d = disp[v0:v1, u0:u1].astype(np.float64)
    validos = np.isfinite(d) & (d > 0.0) & (d >= min_disparidad)
    d, uu, vv = d[validos], uu[validos], vv[validos]
    z = f * t / d
    en_rango = (z > z_min) & (z < z_max)
    z, uu, vv = z[en_rango], uu[en_rango], vv[en_rango]
    if z.size < MIN_PUNTOS:
        return None

    # Ordenamos por profundidad y cortamos en cada salto mayor a SALTO_M.
    orden = np.argsort(z, kind='stable')
    z, uu, vv = z[orden], uu[orden], vv[orden]
    cortes = np.where(np.diff(z) > SALTO_M)[0] + 1
    for ini, fin in zip(np.r_[0, cortes], np.r_[cortes, z.size]):
        if fin - ini < MIN_PUNTOS:
            continue  # pocos píxeles sueltos más cerca: ruido
        # Del grupo usamos solo el frente (EXTENSION_M), y la mediana de sus píxeles.
        n_frente = int(np.searchsorted(z[ini:fin], z[ini] + EXTENSION_M, 'right'))
        zg, ug, vg = z[ini:ini + n_frente], uu[ini:ini + n_frente], vv[ini:ini + n_frente]
        if zg.size < MIN_PUNTOS:
            continue
        x = float(np.median((ug - cx) * zg / f))
        y = float(np.median((vg - cy) * zg / f))
        return (x, y, float(np.median(zg)), int(zg.size))
    return None
```

<!-- celda -->
Para probar la función sin las cámaras, la celda siguiente arma un **mapa de disparidad sintético**: un limón de 6 cm a 0,55 m, delante de hojas a 0,80 m, con ruido. La caja es más grande que el limón, como pasa con las cajas reales, así que su zona central también ve hojas del fondo.

<!-- celda -->
```python
# Armamos un mapa de disparidad sintético de 640 x 480, como el que publica /disparity:
#   - fondo de hojas a 0,80 m;
#   - un limón de 6 cm de diámetro a 0,55 m, centrado en el píxel (400, 260).
F_PX, B_M = 654.3, 0.0895      # focal [px] y baseline [m] de la calibración
CX, CY = 320.0, 240.0          # centro óptico [px] (aproximado, para el ejemplo)
Z_HOJAS, Z_LIMON, R_LIMON = 0.80, 0.55, 0.03
U0, V0 = 400, 260

rng = np.random.default_rng(0)
vv, uu = np.mgrid[0:480, 0:640]
z_real = np.full((480, 640), Z_HOJAS)
r_px = R_LIMON * F_PX / Z_LIMON                       # radio del limón en la imagen [px]
z_real[(uu - U0) ** 2 + (vv - V0) ** 2 <= r_px ** 2] = Z_LIMON
disp = F_PX * B_M / z_real + rng.normal(0, 0.3, z_real.shape)   # d = f·B/Z, con ruido de 0,3 px

# Caja de YOLO un poco más grande que el limón: su zona central también ve hojas del fondo.
caja = (U0, V0, 3.6 * r_px, 3.6 * r_px)
u0, u1 = int(caja[0] - caja[2] / 4), int(caja[0] + caja[2] / 4)
v0, v1 = int(caja[1] - caja[3] / 4), int(caja[1] + caja[3] / 4)
zona = z_real[v0:v1, u0:u1]
print(f"Zona central de la caja: {zona.size} px, {np.mean(zona == Z_HOJAS):.0%} de hojas del fondo")
x, y, z, n = posicion(disp, caja, F_PX, B_M, CX, CY, z_min=0.38, z_max=0.96)
print(f"Radio del limón en la imagen: {r_px:.1f} px")
print(f"Posición medida: X = {x:+.3f} m, Y = {y:+.3f} m, Z = {z:.3f} m ({n} píxeles del limón)")
print(f"Posición real:   X = {(U0 - CX) * Z_LIMON / F_PX:+.3f} m, Y = {(V0 - CY) * Z_LIMON / F_PX:+.3f} m, Z = {Z_LIMON:.3f} m")
z_prom = np.mean(F_PX * B_M / disp[v0:v1, u0:u1])
print(f"Promediando toda la zona (sin separar el fondo): Z = {z_prom:.3f} m, error {1000 * (z_prom - Z_LIMON):+.0f} mm")
```

<!-- celda -->
Resultado esperado: la función encuentra la posición real (Z = 0,550 m). Si en cambio se promedia toda la zona central, las hojas del fondo agregan unos **+29 mm** de error en $Z$, casi todo el margen del requisito B5 (35 mm). Falta validar la función con el par recalibrado en el mástil y limones a distancias medidas.

<!-- celda -->
### **4.3 Código que corre en el robot**

En la Raspberry Pi, la detección es un nodo de ROS 2 (`detector_node.py`, paquete `yolo_ros` del repositorio `vision_estereo`). Recibe cada imagen rectificada de la cámara izquierda, corre el modelo en formato NCNN y publica las cajas y la imagen anotada. Es el mismo `predict` de la sección 4.1, dentro de un nodo (extracto; los archivos completos están en el repositorio):

```python
class DetectorNode(Node):
    """Corre YOLO sobre cada imagen y publica /yolo/detecciones."""

    def __init__(self):
        super().__init__('detector_node')
        self.declare_parameter('modelo', '/home/r2d2/yolo26n.pt')
        self.declare_parameter('imagen', '/left/image_rect')
        self.declare_parameter('imgsz', 480)
        self.declare_parameter('conf', 0.40)
        self.declare_parameter('clases', [''])  # nombres a publicar; vacío = todas
        self.declare_parameter('anotada', True)

        modelo = self.get_parameter('modelo').value
        self.imgsz = int(self.get_parameter('imgsz').value)
        self.conf = float(self.get_parameter('conf').value)
        self.clases = {c for c in self.get_parameter('clases').value if c}
        self.anotada = bool(self.get_parameter('anotada').value)

        self.bridge = CvBridge()
        self.model = YOLO(modelo, task='detect')
        qos = QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=1,
                         reliability=QoSReliabilityPolicy.BEST_EFFORT)
        imagen = self.get_parameter('imagen').value
        self.create_subscription(Image, imagen, self.al_recibir, qos)
        self.pub_det = self.create_publisher(Detection2DArray, '/yolo/detecciones', 10)
        self.pub_img = self.create_publisher(Image, '/yolo/left/image_annotated', 10)

    def al_recibir(self, msg):
        """Detecta y publica, con el mismo header que la imagen (sirve para sincronizar)."""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            r = self.model.predict(source=frame, imgsz=self.imgsz, conf=self.conf,
                                   device='cpu', verbose=False)[0]
        except Exception as error:  # una imagen mala no debe tirar el nodo
            self.get_logger().error(f'Error procesando la imagen: {error}')
            return

        salida = Detection2DArray()
        salida.header = msg.header
        for caja, clase, score in zip(r.boxes.xywh.tolist(), r.boxes.cls.tolist(),
                                      r.boxes.conf.tolist()):
            nombre = r.names[int(clase)]
            if self.clases and nombre not in self.clases:
                continue
            d = Detection2D()
            d.header = msg.header
            d.bbox.center.position.x, d.bbox.center.position.y = caja[0], caja[1]
            d.bbox.size_x, d.bbox.size_y = caja[2], caja[3]
            h = ObjectHypothesisWithPose()
            h.hypothesis.class_id = nombre
            h.hypothesis.score = float(score)
            d.results.append(h)
            salida.detections.append(d)
        self.pub_det.publish(salida)

        if self.anotada:
            anotada = self.bridge.cv2_to_imgmsg(r.plot(), encoding='bgr8')
            anotada.header = msg.header
            self.pub_img.publish(anotada)
```

El localizador (`localizador_node.py`, en desarrollo) espera una detección y una disparidad **de la misma imagen**: las empareja por su marca de tiempo. Por cada limón llama a la función `posicion` de la sección 4.2 y publica el de mayor confianza:

```python
    def al_recibir(self, dets, disp_msg):
        """Localiza cada detección y publica la de mayor confianza."""
        if self.info is None or not dets.detections:
            return
        img = disp_msg.image
        disp = np.frombuffer(img.data, dtype=np.float32).reshape(img.height, img.width)
        cx, cy = self.info.p[2], self.info.p[6]   # centro óptico de la imagen rectificada

        mejor = None
        for d in dets.detections:
            if not d.results:
                continue
            hip = d.results[0].hypothesis
            if self.clase and hip.class_id != self.clase:
                continue
            caja = (d.bbox.center.position.x, d.bbox.center.position.y,
                    d.bbox.size_x, d.bbox.size_y)
            p = posicion(disp, caja, disp_msg.f, disp_msg.t, cx, cy, self.z_min, self.z_max,
                         disp_msg.min_disparity)
            if p is not None and (mejor is None or hip.score > mejor[0]):
                mejor = (hip.score, hip.class_id, p)
        if mejor is None:
            return

        score, clase, (x, y, z, n) = mejor
        salida = PointStamped()
        salida.header = disp_msg.header
        salida.point.x, salida.point.y, salida.point.z = x, y, z
        self.pub.publish(salida)
```

En la Pi, las cámaras, la rectificación, la disparidad, el detector y el localizador se lanzan con un solo script. Para esta entrega se usa la salida del detector:

```bash
MODELO=~/vision_estereo/modelos/limon_yolo26n_v2_ncnn_model CLASE=limon ./scripts/start_limon.sh
```

<!-- celda -->
---
## **5. Video demo**

<!-- celda -->
<!-- PENDIENTE: subir el video a YouTube y reemplazar ID_VIDEO (dos veces) por el código del video -->
**[Espacio para el video demo]**

[![Ver video demo del sistema de visión](https://img.youtube.com/vi/ID_VIDEO/hqdefault.jpg)](https://youtu.be/ID_VIDEO)

**Guion del video** (lo que se graba para esta demo):

1. El setup: el robot con las dos cámaras NoIR y la Raspberry Pi 5 en el mástil, frente al limonero de prueba.
2. El arranque de la cadena con `start_limon.sh`.
3. La imagen anotada (`/yolo/left/image_annotated`): el limón marcado con su caja y su confianza.
4. El limón se mueve dentro de la imagen y la caja lo sigue; con hojas delante, se ve cuándo deja de detectarlo.

La posición en metros no se muestra: la visión estéreo está pendiente.

<!-- celda -->
---
## **6. Limitaciones y trabajo pendiente**

<!-- celda -->
| Limitación | Efecto | Qué se va a hacer |
| :--- | :--- | :--- |
| Cámaras NoIR (sin filtro infrarrojo) | En el laboratorio la v2 detecta bien; al sol, los colores salen corridos y el detector podría fallar. La demo final es al aire libre | Probar al sol; sacar fotos propias con las NoIR, etiquetarlas y sumarlas al entrenamiento |
| Imágenes de prueba de las mismas fuentes que las de entrenamiento | P y R pueden ser optimistas | Medir P y R con un set propio tomado con las cámaras del robot |
| Cámaras no sincronizadas | Hay que localizar con el robot quieto | La misión detiene el robot antes de localizar |
| Zona ciega (u < 163 px en la imagen izquierda) | Un limón en ese borde se detecta, pero no se localiza | Ubicar el robot para que el limón quede en el centro de la imagen |
| Una sola clase (`limon`) | No distingue limón maduro de verde | Decidir la madurez por el tamaño: diámetro = ancho de la caja [px] · Z / f |
| Visión estéreo sin terminar | Todavía no se entrega la posición del limón en metros; la calibración del 01/10 ya no vale con las cámaras en el mástil | Recalibrar con el tablero, terminar y validar el localizador con limones a distancias medidas (B5) y medir la transformación cámara → brazo llevando la pinza a puntos conocidos |

<!-- celda -->
---
## **7. Referencias**

<!-- celda -->
Las referencias [1] a [6] son artículos de acceso abierto (licencia Creative Commons BY); [7] es documentación en línea de libre acceso.

[1] D. Font, T. Pallejà, M. Tresanchez, D. Runcan, J. Moreno, D. Martínez, M. Teixidó y J. Palacín, "A Proposal for Automatic Fruit Harvesting by Combining a Low Cost Stereovision Camera and a Robotic Arm", *Sensors*, vol. 14, n.º 7, pp. 11557–11579, 2014. DOI: [10.3390/s140711557](https://doi.org/10.3390/s140711557).

[2] Y. Tang, M. Chen, C. Wang, L. Luo, J. Li, G. Lian y X. Zou, "Recognition and Localization Methods for Vision-Based Fruit Picking Robots: A Review", *Frontiers in Plant Science*, vol. 11, art. 510, 2020. DOI: [10.3389/fpls.2020.00510](https://doi.org/10.3389/fpls.2020.00510).

[3] J. Terven, D.-M. Córdova-Esparza y J.-A. Romero-González, "A Comprehensive Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS", *Machine Learning and Knowledge Extraction*, vol. 5, n.º 4, pp. 1680–1716, 2023. DOI: [10.3390/make5040083](https://doi.org/10.3390/make5040083).

[4] G. Li, X. Huang, J. Ai, Z. Yi y W. Xie, "Lemon-YOLO: An efficient object detection method for lemons in the natural environment", *IET Image Processing*, vol. 15, n.º 9, pp. 1998–2009, 2021. DOI: [10.1049/ipr2.12171](https://doi.org/10.1049/ipr2.12171).

[5] Y. Lin, Z. Huang, Y. Liang, Y. Liu y W. Jiang, "AG-YOLO: A Rapid Citrus Fruit Detection Algorithm with Global Context Fusion", *Agriculture*, vol. 14, n.º 1, art. 114, 2024. DOI: [10.3390/agriculture14010114](https://doi.org/10.3390/agriculture14010114).

[6] L. Zhang, Q. Hao, Y. Mao, J. Su y J. Cao, "Beyond Trade-Off: An Optimized Binocular Stereo Vision Based Depth Estimation Algorithm for Designing Harvesting Robot in Orchards", *Agriculture*, vol. 13, n.º 6, art. 1117, 2023. DOI: [10.3390/agriculture13061117](https://doi.org/10.3390/agriculture13061117).

[7] Ultralytics, "Ultralytics YOLO Docs", documentación en línea de libre acceso. Disponible en: [docs.ultralytics.com](https://docs.ultralytics.com).

<!-- celda -->
---
### **Carpeta del proyecto**
En el link se encuentra la carpeta del proyecto.
[TPF R1 Grupo 2](https://drive.google.com/drive/folders/1d2jONLnkB8FMkP2iqF4ia4UeQ2jRpffz)
