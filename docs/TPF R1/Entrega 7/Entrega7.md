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

**ENTREGA [7]:**  Diseño final del robot e implementación de estructura (Demo)

**Fecha:** 18/10/2026

**Versión:** [1.0]

<!-- celda -->
---
## **Resumen**

Esta entrega presenta el diseño final del brazo recolector de limones, su fabricación y su montaje sobre la base móvil. El informe se organiza en once secciones:

| # | Sección | Qué se muestra |
| :---: | :--- | :--- |
| 1 | Morfología | Tipo de robot, grados de libertad y cadena cinemática |
| 2 | Diseño | Medidas, masas, rangos articulares y modelo CAD |
| 3 | Materiales | PLA con fibra de carbono para el brazo; madera para la base |
| 4 | Actuadores | Motores, transmisiones, servos y cambio de motores de J2/J3 |
| 5 | Sensores | Encoders, finales de carrera y cámaras estéreo |
| 6 | Drivers | IBT-2 (BTS7960) y alimentación de los servos |
| 7 | Fabricación | Del CAD a la pieza impresa, con el peso de cada pieza |
| 8 | Montaje | Orden de armado del brazo y su fijación a la base |
| 9 | Lazo abierto | Síntesis de los ensayos de las Entregas 5 y 6 |
| 10 | Videos | Demo del brazo |
| 11 | Referencias | 8 artículos de acceso abierto |

#### Estado del brazo en esta entrega

El informe distingue tres cosas: el diseño final previsto, lo que muestran las fotos del montaje y lo que efectivamente se probó.

| Parte | Diseño final | En las fotos | Probado |
| :--- | :--- | :--- | :--- |
| J1 (base) | 36GP-555 + correa 5:1 + IBT-2 | El mismo | Lazo abierto y lazo cerrado |
| J2 (hombro) | 36-555 + engranajes 5:1 + IBT-2 | 5840, descartado | Pendiente: motor en camino |
| J3 (codo) | 36-555 + engranajes 5:1 + IBT-2 | 5840, descartado | Pendiente: motor en camino |
| Pinza | 2 servos RDS3218 | Montada | Sí, cada servo por separado |
| Finales de carrera | 3, para el homing | — | No |
| Cámaras | Estéreo + YOLO en la Raspberry Pi 5 | — | En laboratorio |

Los motores 5840 que aparecen en las fotos se descartaron. Como prueba, el motor de J1 se montó en J2 y levantó el brazo. La sección 4.1 cuenta esos ensayos.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/106iN-Yo390xJS2KZNlywJeFAigkwcI13=w2400" width="650" alt="Robot completo" />
  <br>
  <b>Fig. 1.</b> Robot "Arturito R2D2" con el brazo montado sobre la base móvil, sujetando un limón. Foto del 04/10, todavía con los motores 5840 en J2 y J3.
</p>

<!-- celda -->
---
## **1. Morfología del robot**

<!-- celda -->
El robot tiene dos partes. La base móvil (de madera, con tracción diferencial) recorre la hilera de limoneros; corresponde a Robótica II. El brazo cosecha el limón; es lo que evalúa Robótica I y lo que se describe en este informe.

La consigna general pide montar el brazo sobre una plataforma con recorrido lineal de 1,20 m, cosechar con succión y torsión, y dejar los limones en dos cajones según su tamaño. En este robot, la base móvil hace de plataforma y recorre la hilera completa; falta confirmar con la cátedra que cumple ese papel. La herramienta es una pinza que agarra y gira, en lugar de succión: el cambio lo aprobó el profesor el 28/09. Los cajones y la prueba en la zona de cosecha de 30 cm se presentan con el robot completo.

El brazo es un manipulador RRR articulado, del mismo tipo que el uArm Swift y el Dobot Magician [5]. Tiene tres articulaciones rotativas motorizadas que posicionan la pinza en el espacio.

Un paralelogramo mantiene la pinza siempre horizontal y apuntando en la dirección de J1. Así, tres motores alcanzan para llevarla hasta el limón. Aparte, dos servos giran la pinza sobre su eje (J4) y la abren y cierran.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1n2a3QFC-G6gsRmoV6bSt8o49scDKhVzS=w2400" width="950" alt="Morfología del brazo" />
  <br>
  <b>Fig. 2.</b> Cadena cinemática del brazo, desde la base móvil hasta la pinza. Diagrama propio (draw.io).
</p>

#### Grados de libertad

| Articulación | Tipo | Función | Rango de diseño | Actuador |
| :--- | :---: | :--- | :---: | :--- |
| J1 (base) | Rotativa, eje vertical | Orienta el brazo hacia el limón | 45° a 225° | Motor DC con encoder |
| J2 (hombro) | Rotativa, eje horizontal | Levanta la barra principal | −25° a 135° | Motor DC con encoder |
| J3 (codo) | Rotativa, por cuatro barras | Mueve el antebrazo | −50° a 50° | Motor DC con encoder |
| J4 (giro de pinza) | Rotativa | Retuerce el pedúnculo | −90° a 90° | Servo |
| Pinza | Apertura | Agarra el limón | 0 a 100 % | Servo |

#### Por qué esta morfología

* **El motor del codo va abajo.** J3 mueve un balancín junto al hombro, y un acoplador lleva ese giro hasta el codo. El antebrazo no carga el peso de un motor, y el brazo resulta más liviano y rígido [4], [6].
* **La pinza se mantiene horizontal sin un motor de muñeca.** El paralelogramo la deja en la posición útil para tomar un limón colgado de la rama. Solo se suma el servo J4, que gira la pinza para retorcer el pedúnculo. El mismo recurso usan otros robots de campo con paralelogramo [4].
* **El espacio de trabajo es amplio.** Una cadena RRR articulada alcanza un volumen esférico alrededor de J1, adecuado para frutos a distintas alturas y distancias [1], [3].

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1iJaOeZGYvsNW7vhEa2rceqs7W9GXJiXV=w2400" width="800" alt="Mecanismo de cuatro barras" />
  <br>
  <b>Fig. 3.</b> Mecanismo de cuatro barras del brazo (Entrega 3).
</p>

<!-- celda -->
---
## **2. Diseño**

<!-- celda -->
El diseño se hizo en SolidWorks, a partir de las medidas de la Entrega 4. El brazo va montado atrás a la izquierda de la base, sobre el eje de las ruedas de tracción. Desde ahí, su rango de giro nunca cruza el mástil de las cámaras, que está adelante a la derecha.

#### Medidas principales

| Símbolo | Elemento | Medida [mm] |
| :---: | :--- | :---: |
| $H_1$ | Altura del hombro | 150,00 |
| $L_2$ | Barra principal (hombro → codo) | 350,22 |
| $L_3$ | Antebrazo (codo → muñeca) | 329,51 |
| $L_4$ | Acoplador del cuatro barras | 338,00 |
| $L_{3,0}$ | Balancín de entrada (rojo), movido por J3 | **60,00** (40,00 en la E4) |
| $L_{3,1}$ | Balancín de salida (tramo corto del antebrazo) | 40,00 |
| $L_p$ | Pinza | 190,00 |

#### Cuatro barras: balancín rojo de 60 mm

El codo se mueve con un cuatro barras: el motor de J3 gira el balancín rojo y el acoplador lleva ese giro hasta el antebrazo.

En la Entrega 4 el balancín rojo medía 40 mm y el mecanismo no cumplía el criterio de Grashof. En la práctica, eso significa que tenía posiciones donde se trababa, llamadas puntos muertos, y que el codo se movía poco.

Para corregirlo, el balancín rojo se alargó a 60 mm. El criterio se cumple cuando la barra más corta más la más larga no superan a las otras dos sumadas:

| Balancín rojo | Más corta + más larga | Las otras dos | ¿Cumple Grashof? |
| :---: | :---: | :---: | :---: |
| 40 mm | 40 + 350,22 = 390,22 | 40 + 338 = 378 | No |
| **60 mm** | 40 + 350,22 = 390,22 | 60 + 338 = 398 | **Sí** |

Resultado: el codo ahora recorre unos 147°, contra 113° con el balancín de 40 mm.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/ID_FIG3B=w2400" width="650" alt="Cuatro barras con balancín de 60 mm" />
  <br>
  <b>Fig. 3b.</b> Cuatro barras del codo con el balancín rojo de 60 mm, dibujado a escala en la pose de reposo. Diagrama propio (draw.io).
</p>

El cambio trajo tres consecuencias:

* **J2 y J3 se mueven juntas.** El cuatro barras depende de la suma de los dos ángulos, así que no se puede mover una sin mirar la otra. El software rechaza las posiciones donde el mecanismo se trabaría.
* **Cambió la pose de reposo.** La anterior quedaba en una posición imposible con 60 mm. La nueva es $q = (75°, 94°, -50°)$, provisoria hasta medir el brazo real.
* **J3 necesita más fuerza.** Con balancines de distinto largo, el codo gira más que el balancín: entre 1,4 y 5 veces, según la posición. Por eso el motor de J3 tiene que hacer más torque. La sección 4 lo calcula.

#### Masas

| Componente | Masa [g] | Origen |
| :--- | ---: | :--- |
| Eslabón 1 (barra principal) | 515,9 | Estimación de la E6 |
| Eslabón 2 (antebrazo, sin pinza) | 362,6 | Estimación de la E6 |
| Pinza armada | **246** | **Pesada (sección 7)** |
| **Masa móvil del brazo** | **≈ 1125** | |
| Limón (carga de diseño) | 200 | Supuesto del grupo: un limón pesa entre 150 y 200 g |

La pinza se pesó armada: dedos, mecanismo, soporte trasero, los dos servos y su tornillería. Pesa 246 g, menos que los 322 g estimados en la Entrega 6; los cálculos de torque de este informe usan el valor pesado.

#### Rangos de diseño y recorridos ensayados

Los rangos de diseño son límites provisorios de cada articulación. Además, J2 y J3 tienen que combinarse de forma que el cuatro barras se pueda armar, como se explicó arriba, y el recorrido con carga se va a validar con los motores nuevos. Los recorridos ensayados son los que se movieron realmente en las pruebas.

| Articulación | Rango de diseño | Recorrido ensayado |
| :--- | :---: | :--- |
| J1 | 45° a 225° | 36GP-555 con correa (E6): escalones de ±20° alrededor de la marca de 90° (70° a 110°) y una orden a 135° |
| J2 | −25° a 135° | 5840 con resorte (E6, descartado): barrido de −10° a +20° en el marco del banco. Con el 36-555: sin ensayar |
| J3 | −50° a 50° | 5840 (E6, descartado): escalones de ±10° en el marco del banco. Con el 36-555: sin ensayar |
| J4 y apertura | −90° a 90° / 0 a 100 % | Cada servo probado por separado; recorrido no medido |

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/17IUc7jgzLv53_FPtIxN9IcOiOrplFCyO=w2400" width="750" alt="CAD isométrico" />
  <br>
  <b>Fig. 4.</b> Modelo CAD del brazo.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1LSZz1KtIffdb6an-XwE2cWzZ_8TZmWqp=w2400" width="750" alt="Dimensiones" />
  <br>
  <b>Fig. 5.</b> Dimensiones principales del manipulador.
</p>

#### Pinza

La pinza combina tres acciones, como recomiendan las revisiones sobre efectores para cosecha [2], [3]: agarrar el limón, traccionar un poco y girar para cortar el pedúnculo. Un servo abre y cierra los dedos; el otro gira toda la pinza (J4).

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1oY4ByWm0oYS7uPQxp1sQUAR5QsVV044d=w2400" width="650" alt="Pinza" />
  <br>
  <b>Fig. 6.</b> Modelo CAD de la pinza.
</p>

<!-- celda -->
---
## **3. Materiales**

<!-- celda -->
El brazo se imprimió en PLA reforzado con fibra de carbono (PLA-CF), filamento negro de 1,75 mm. La base móvil es de madera (Robótica II).

#### Por qué PLA-CF

* **Más rígido que el PLA común.** La fibra de carbono aumenta notablemente la rigidez del material [7]. En un brazo largo, esto reduce la flexión de los eslabones bajo el peso de la pinza y el limón.
* **Liviano.** Mantiene baja la masa en movimiento, y con ella el torque que deben dar los motores.
* **Fácil de fabricar.** Se imprime en una impresora FDM común, sin mecanizado.

Su resistencia depende de cómo se imprime: la temperatura de la cama, la orientación de la pieza y el espesor de capa cambian la resistencia a tracción [7], [8]. Por eso conviene imprimir las piezas que trabajan a flexión con las capas a lo largo del eslabón.

#### Materiales por parte

| Parte | Material | Motivo |
| :--- | :--- | :--- |
| Eslabones, balancines y acoplador | PLA-CF negro, 1,75 mm | Rigidez y bajo peso |
| Base giratoria del brazo y soportes de motor | PLA-CF negro, 1,75 mm | Geometría compleja, una sola pieza |
| Pinza (dedos y soporte de servos) | PLA-CF negro, 1,75 mm | Liviana, en el extremo del brazo |
| Transmisión de J1 | Correa y poleas GT2 (18 → 90) | Reducción 5:1 |
| Transmisión de J2 y J3 | Engranajes helicoidales (15 → 75) | Reducción 5:1 |
| Apoyos de los ejes | Rodamientos de bolas (bridados 4 × 13 × 5 mm y axial 51105) | Giro suave, soporta el peso del brazo |
| Ejes y tornillería | Acero | Uniones desmontables |
| Base móvil (R2) | Madera de 1 cm, pintada de negro | Barata y fácil de cortar |

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1FcQmQkq7vvsC2Uh_4IdbDWidSIICTl4j=w2400" width="700" alt="Base impresa" />
  <br>
  <b>Fig. 7.</b> Base giratoria del brazo impresa en PLA-CF, sobre la tapa de madera.
</p>

<!-- celda -->
---
## **4. Actuadores**

<!-- celda -->
Las tres articulaciones usan motores DC con reductora y encoder, con una reducción externa de 5:1: correa GT2 en J1 y engranajes helicoidales en J2 y J3. La pinza usa dos servos digitales.

#### Resumen (diseño final)

| | J1 (base) | J2 (hombro) | J3 (codo) | Pinza (×2) |
| :--- | :---: | :---: | :---: | :---: |
| Actuador | 36GP-555 | 36-555 | 36-555 | DSSERVO RDS3218 |
| Tensión | 12 V | 12 V | 12 V | 6 V |
| Reductora del motor | Planetaria 50:1 | 139:1 (vendedor) | 139:1 (vendedor) | Engranajes |
| Velocidad del motor | 160 rpm | 58 rpm | 58 rpm | 0,17 s/60° |
| Transmisión externa | Correa GT2 18 → 90 (5:1) | Engranajes helicoidales 15 → 75 (5:1) | Engranajes helicoidales 15 → 75 (5:1) | — |
| Velocidad de la articulación (calculada) | 192 °/s | 70 °/s | 70 °/s en el balancín | — |
| Torque del motor | — | 22 kgf·cm nominal (vendedor) | 22 kgf·cm nominal (vendedor) | 20 kgf·cm |
| Estado | Montado y probado | Pendiente de llegada | Pendiente de llegada | Montados y probados |

En J3, la velocidad es la del balancín rojo; la del codo cambia con la posición del cuatro barras.

Los dos servos se probaron por separado: el de apertura abre y cierra los dedos, y el de giro rota la pinza. Los dos funcionan bien.

#### Engranajes helicoidales de J2 y J3

| Parámetro | Valor |
| :--- | :---: |
| Piñón helicoidal (en el motor) | 15 dientes |
| Engranaje helicoidal (en la articulación) | 75 dientes |
| Relación | 5:1 |
| Ancho de cara | 15 mm |
| Ángulo de hélice | 25° |
| Ángulo de presión normal | 20° |

Se eligieron engranajes helicoidales porque los dientes entran en contacto de a poco: hacen menos ruido y vibran menos que los rectos. A cambio, empujan los ejes a lo largo, y ese esfuerzo lo tienen que absorber los apoyos. El piñón y la rueda tienen hélices de sentido contrario.

Falta completar con el CAD el módulo, los diámetros y la distancia entre ejes. Con esos datos se puede calcular el empuje sobre los apoyos: $F_a = F_t \tan 25° \approx 0,47\,F_t$, con $F_t = 2T/d$.

#### Torque requerido contra torque disponible

Para estimar el torque se toma el caso más exigente: el brazo en horizontal con un limón de 200 g en la pinza. Se usa el peso medido de la pinza, 246 g.

En J2, el torque del motor pasa solo por los engranajes, que lo multiplican por 5. En J3 hay una etapa más, el cuatro barras: según la posición, el balancín tiene que hacer entre 1,4 y 5 veces el torque que necesita el codo (sección 2).

| Articulación | Torque requerido | Torque disponible | Margen |
| :--- | :---: | :---: | :---: |
| J2 (hombro) | 8,0 N·m | 10,8 N·m | 1,35 |
| J3, mitad del rango | 5,0 N·m | 10,8 N·m | 2,2 |
| J3, cerca del borde inferior | 13,7 N·m | 10,8 N·m | **0,79** |

Los torques son los del eje de cada articulación, después de los engranajes. El disponible es 22 kgf·cm × 5. El margen es el disponible dividido por el requerido: si es menor que 1, el motor no alcanza.

* **J2** tiene margen, aunque justo.
* **J3** alcanza en la mayor parte del rango, pero no cerca del borde inferior. Ese caso es con $q_2 = 26°$ y $q_3 = -47°$, el antebrazo horizontal y el limón en la pinza. En el extremo mismo del rango, la cuenta llega a 17,5 N·m. Falta definir qué recorrido se va a usar con carga y probarlo con los motores nuevos.
* Es un cálculo, no un ensayo: usa el torque nominal del vendedor y no descuenta las pérdidas de los engranajes.

J1 gira en el plano horizontal: la gravedad no le pide torque, solo la inercia y la fricción.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1Pr8gyXGx4nPgvVkYJcDFzcoqgBlERl8A=w2400" width="550" alt="36GP-555" />
  <br>
  <b>Fig. 8.</b> Motor 36GP-555 de J1, con encoder Hall.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1HBp_QuTC6vBkhwrPOcGAmCj0yufkY4Bo=w2400" width="550" alt="36-555" />
  <br>
  <b>Fig. 9.</b> Motor 36-555 de 58 rpm, previsto para J2 y J3, con encoder Hall de 16 PPR (imagen del vendedor; los motores todavía no llegaron).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1VDLs7ZPKZzq93PbYdojtQ8d4BDR3ruRI" width="550" alt="Servo" />
  <br>
  <b>Fig. 10.</b> Servo DSSERVO RDS3218 de la pinza.
</p>

<!-- celda -->
---
### **4.1 Cambio de motores en J2 y J3**

<!-- celda -->
Los motores de J2 y J3 se están cambiando. Esta sección explica qué se probó, por qué se descartó el motor anterior y en qué estado está el cambio.

#### Qué se probó

1. **Lazo abierto (Entrega 5).** El motor **5840-31ZY** (tornillo sin fin, **8 kgf·cm**) se caracterizó con el eje libre y el driver L298N. Respondió bien: ganancia de 1,33 rpm/% y constante de tiempo de 59 ms.
2. **Montado en el brazo, con L298N.** No levantaba el brazo.
3. **Con IBT-2.** Se cambió el L298N por un IBT-2 para no perder los ~2,4 V del L298N y aprovechar toda la alimentación. Aun así, no levantaba el brazo.
4. **Con un resorte.** Con un resorte que compensaba parte del peso, el brazo subió. Pero el control quedó muy inestable, con una oscilación física considerable.
5. **Motor de J1 en J2.** Se probó el motor de J1 (36GP-555, 160 rpm) en la posición de J2, con la transmisión helicoidal. **Levantó el brazo.**
6. **Decisión.** Se descartaron los 5840 y se compraron **2 motores 36-555 de 58 rpm**, de más par que el de J1, y **2 drivers IBT-2**.

> **Sobre las gráficas de la Entrega 6:** las curvas de lazo cerrado de J3 con el 5840 parecían cumplir las especificaciones, pero no mostraban la oscilación que se veía en el brazo. Por eso no se toman como validación del funcionamiento mecánico de J2 y J3.

#### Antes y después

| | Antes: 5840-31ZY | Después: 36-555 de 58 rpm |
| :--- | :--- | :--- |
| Reducción | Tornillo sin fin | Reductora 139:1 + engranajes helicoidales 15 → 75 |
| Torque del motor | 8 kgf·cm | 22 kgf·cm nominal (vendedor) |
| Driver | L298N, después IBT-2 | IBT-2 (BTS7960) |
| Encoder | Óptico externo, 1000 PPR | Hall incluido, 16 PPR |
| Resultado | Sin resorte no levantó el brazo; con resorte, oscilaba | Sin probar: los motores todavía no llegaron |

#### Estado

| Paso | Estado |
| :--- | :--- |
| Pruebas con el 5840 (L298N, IBT-2 y resorte) | Hecho: descartado |
| Prueba del motor de J1 en J2, con engranajes helicoidales | Hecho: levantó el brazo |
| Compra de los 2 motores 36-555 y los 2 IBT-2 | Hecho |
| Firmware para los 36-555 (pines, relación 5:1 y driver IBT-2) | Escrito y compilado; sin probar con los motores |
| Llegada de los motores | Pendiente: entre el 19 y el 29/10 |
| Montaje, lazo abierto y lazo cerrado con los motores nuevos | Pendiente: al llegar |

<!-- celda -->
---
## **5. Sensores**

<!-- celda -->
El brazo usa tres tipos de sensores, cada uno con una función distinta:

| Sensor | Cantidad | Mide | Para qué |
| :--- | :---: | :--- | :--- |
| Encoder Hall (cuadratura) | 3 | Giro de cada motor | Control de posición de J1, J2 y J3 |
| Final de carrera V-152-1C25 | 3 | Contacto al llegar al tope | Homing: asignar un ángulo conocido al encender |
| Cámara Pi Camera Module 3 NoIR | 2 | Imagen estéreo | Detectar el limón y medir su posición |

#### Encoders

Cada motor trae un encoder Hall de **16 pulsos por vuelta**, con dos canales en cuadratura. El ESP32 los cuenta por hardware (PCNT) en modo ×4. Con la reductora y la transmisión externa, la resolución en la articulación queda en:

| Articulación | Cuentas por vuelta | Resolución |
| :--- | :---: | :---: |
| J1 (correa 18 → 90) | 16 × 4 × 50 × 5 = 16 000 | 0,023° (verificada en la E6) |
| J2 y J3 (engranajes 15 → 75) | 16 × 4 × 139 × 5 = 44 480 | 0,008° (calculada; sin medir; en J3, del balancín) |

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1DtKXAiR-xmWliY_SiW1RXKpvLsRmcdRu=w2400" width="550" alt="Encoder" />
  <br>
  <b>Fig. 11.</b> Encoder Hall en la parte trasera del motor.
</p>

#### Finales de carrera

El encoder es incremental: al apagar el robot pierde la posición. Para recuperarla, al encender cada articulación gira despacio hasta tocar su final de carrera. El firmware asigna a ese punto un ángulo conocido, que no es necesariamente 0°: el extremo del rango de cada articulación (J1 45°, J2 −25°, J3 −50°, a confirmar con la mecánica). Para evitar falsos disparos, pide 3 lecturas seguidas del contacto.

Son microinterruptores con palanca de rodillo, conectados a GND y leídos con el pull-up interno del ESP32. El homing está programado, pero todavía no se probó. En J2 y J3 está bloqueado hasta medir sus posiciones de referencia: J2 en −25° y J3 en −50° forman una combinación en la que el cuatro barras no se puede armar.

**Marca de referencia de J1.** Es otra cosa: una marca en la base, con J1 a 90° (brazo hacia la izquierda). En los ensayos de la E6, el cero se fijó a mano en esa marca, sin final de carrera.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1D3LCphASRbrWOr3G95Ptc1c4NPM_eUct=w2400" width="451" alt="Final de carrera" />
  <br>
  <b>Fig. 12.</b> Microinterruptor V-152-1C25 con palanca de rodillo (imagen del vendedor).
</p>

#### Cámaras estéreo

Dos cámaras Raspberry Pi Camera Module 3 NoIR, separadas 90 mm, van conectadas a la Raspberry Pi 5. La red YOLO detecta el limón en la imagen y el par estéreo da su distancia, igual que en el trabajo de Font et al. [1]. En el laboratorio, el error de posición fue de 17 mm como máximo entre 40 y 90 cm.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1kOzJ7IH-kLjQhXKfCvtDKdtKeP1vG9Ju=w2400" width="400" alt="Cámara" />
  <br>
  <b>Fig. 13.</b> Cámara Raspberry Pi Camera Module 3 NoIR (imagen del fabricante). El par estéreo usa dos.
</p>

<!-- celda -->
---
## **6. Drivers**

<!-- celda -->
Cada motor del brazo tiene su propio **IBT-2**, un puente H completo basado en dos BTS7960. Los tres reciben las órdenes de un **ESP32-WROOM-32D**, que cierra los lazos de control.

#### Por qué el IBT-2

* **Margen de corriente:** el BTS7960 limita la corriente en unos 43 A (valor típico de su protección, según la hoja de datos). No es una corriente continua del módulo, que depende de cómo disipe el calor. El motor trabado consume hasta 10 A. No se midió la temperatura del driver.
* **Cae poca tensión:** usa transistores MOSFET. El L298N de la Entrega 5 perdía ~2,4 V y el motor recibía solo 9,6 V.
* **Es el mismo en las tres articulaciones:** un solo código de driver y repuestos intercambiables.

#### Configuración

| Parámetro | Valor |
| :--- | :--- |
| Frecuencia de PWM | 20 kHz |
| Señales por motor | RPWM (un sentido) y LPWM (el otro) |
| Habilitación | GPIO 23, común a los tres drivers |
| Lógica | 3,3 V, compatible con el ESP32 |
| Potencia | Bus de 12 V: LiPo 3S → fusible de 20 A → selector → seta de emergencia |

A 20 kHz el PWM queda fuera del rango audible. Todavía no se probó con los motores nuevos: el ensayo anterior de J3 se hizo a 1 kHz. Los pines R_EN y L_EN de los tres IBT-2 van unidos al GPIO 23, con una resistencia de 10 kΩ a GND que mantiene los motores apagados mientras el ESP32 se reinicia.

Los servos no necesitan driver: reciben la señal PWM de 50 Hz directo del ESP32. Su alimentación de 6 V sale de un convertidor buck de 12 a 6 V, aparte de la del ESP32.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1emxgWWbqDXQjHAXYHlnz8Uj_UmHrhHtg=w2400" width="500" alt="IBT-2" />
  <br>
  <b>Fig. 14.</b> Driver IBT-2 (BTS7960).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1-TKn9yKJswsxG3db3FCQCg0cOGQ6QCoY=w2400" width="1000" alt="Hardware del brazo" />
  <br>
  <b>Fig. 15.</b> Hardware del brazo: sensores, controlador, drivers y actuadores. Diagrama propio (draw.io).
</p>

#### Pines del ESP32-WROOM-32D

| Elemento | J1 | J2 | J3 |
| :--- | :---: | :---: | :---: |
| RPWM / LPWM | 21 / 22 | 25 / 26 | 16 / 17 |
| Encoder A / B | 34 / 35 | 36 / 39 | 18 / 19 |
| Final de carrera | 32 | 33 | 27 |
| EN común | 23 | 23 | 23 |

Servos: apertura en el GPIO 4 y giro (J4) en el GPIO 14.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1SexNqtTubAEHU4WK-ltrCVwJCkdCHBce=w2400" width="850" alt="Cableado WROOM" />
  <br>
  <b>Fig. 16.</b> Cableado del ESP32-WROOM-32D en su shield de borneras.
</p>

<!-- celda -->
---
## **7. Fabricación**

<!-- celda -->
Todas las piezas del brazo se fabricaron por impresión 3D FDM en PLA-CF. La Fig. 17 resume el proceso, del modelo CAD a la pieza lista para montar.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1bYoLvVuEOqUlNeWIvjwBTyz5VmJ_-7NU=w2400" width="1000" alt="Proceso de fabricación" />
  <br>
  <b>Fig. 17.</b> Proceso de fabricación y montaje del brazo. Diagrama propio (draw.io).
</p>

#### Impresión de las piezas

| Parámetro | Valor |
| :--- | :--- |
| Proceso | Impresión 3D por deposición de material fundido (FDM) |
| Impresora | Elegoo Neptune 4 |
| Filamento | PLA-CF negro, 1,75 mm |


<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1UaVvCaslryVbGX-ockjQYEINVTLPPbk-=w2400" width="450" alt="Impresora Elegoo Neptune 4" />
  <br>
  <b>Fig. 17b.</b> Impresora Elegoo Neptune 4, usada para imprimir todas las piezas del brazo (imagen del fabricante).
</p>

#### Piezas impresas

El brazo tiene 17 piezas impresas más la pinza. Cada una se fotografió y se pesó en una balanza de cocina (resolución de 1 g). Las fotos están en la carpeta `Partes_del_brazo`.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1viy8l2DI9S6iTvBRsTDxyjnlv_MRQbsT=w2400" width="1000" alt="Piezas impresas" />
  <br>
  <b>Fig. 18a.</b> Las 18 piezas del brazo en la balanza, con su masa.
</p>

| Tipo de pieza | Piezas | Masa [g] |
| :--- | :--- | ---: |
| Barras (eslabones del brazo y del cuatro barras) | 05, 06, 07, 11, 12, 14, 16 | 693 |
| Soportes y piezas de base | 04, 10, 13, 15, 17 | 405 |
| Ruedas dentadas y discos | 02, 03, 08, 09 | 58 |
| Balancín | 01 | 21 |
| **Total de piezas impresas** | 17 piezas | **1177** |
| Pinza armada | 18 | 246 |
| Motor de J1 con su soporte | — | 459 |

Las piezas más pesadas son las barras largas y el soporte central (pieza 04, 164 g). Las ruedas dentadas y los discos casi no suman peso.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1sd3aVw9xszHSuvm0Kivtu1Q7H88vYEoX=w2400" width="450" alt="Motor de J1 pesado" />
  <br>
  <b>Fig. 18b.</b> Motor de J1 con su soporte, en la balanza: 459 g.
</p>

<!-- celda -->
---
## **8. Montaje**

<!-- celda -->
El brazo se arma de abajo hacia arriba, probando cada articulación antes de montar la siguiente. La tabla indica qué está hecho y qué falta.

| Paso | Qué se hace | Estado |
| :---: | :--- | :--- |
| 1 | Se atornilla la base giratoria a la tapa de madera, atrás a la izquierda | Hecho |
| 2 | Se monta el motor de J1 y se tensa su correa 18 → 90 | Hecho |
| 3 | Se montan el hombro (J2) y la barra principal $L_2$ | Hecho. Motor: estaba el 5840 (descartado); falta el 36-555 con sus engranajes 15 → 75 |
| 4 | Se arma el cuatro barras: balancín, acoplador $L_4$ y antebrazo $L_3$ | Hecho. Motor de J3: igual que J2 |
| 5 | Se monta la pinza con sus dos servos | Hecho |
| 6 | Se colocan los finales de carrera en los topes | Pendiente |
| 7 | Se cablea: shield del ESP32, IBT-2, encoders y servos | J1 y servos hechos; J2 y J3 al llegar los motores |
| 8 | Se fija la referencia de cada articulación | J1: marca de 90° (hecho). J2 y J3: homing con final de carrera (pendiente) |

**Seguridad:** los motores planetarios previstos para J2 y J3 no se autobloquean. Sin corriente, el brazo baja por su peso. Por eso, sin corriente, el brazo queda apoyado en un tope mecánico (no necesariamente en la pose de reposo del software) y nunca se ponen las manos debajo.
<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1u3gF2g76K8jLCoQNvhEgt_7o8tkBsWAk" width="550" alt="Cuatro barras" />
  <br>
  <b>Fig. 19a.</b> brazo armado desmontado de su parte movil.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/11gUEm1KUH7Bl9YTKgZ5dhAg-t5EX4Uij" width="550" alt="Cuatro barras" />
  <br>
  <b>Fig. 19b.</b> brazo parcialmente armado.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1v_UOCUFZcUkiQWg-O_NUcCsHj1GHqF6I" width="550" alt="Cuatro barras" />
  <br>
  <b>Fig. 19c.</b> brazo parcialmente armado ,fijo sobre el robot movil.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1EZPMEAh6mL63r4pmhRwYT68sGi8LU8I4" width="550" alt="Cuatro barras" />
  <br>
  <b>Fig. 19d.</b> Ajustando conexiones de los drivers.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1l5OBX-CgCT1R9NGPI-vaoIizwUyPqise=w2400" width="550" alt="Cuatro barras" />
  <br>
  <b>Fig. 19.</b> Cuatro barras del codo montado, resaltado en violeta (03/10, montaje anterior con el motor 5840).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1ETBieb0k10YYzvpCbtmBRDcwS6AsL-Ky=w2400" width="550" alt="Motor J2" />
  <br>
  <b>Fig. 20.</b> Motor del hombro en el montaje anterior, resaltado en verde: 5840-31ZY, ya descartado (03/10).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1KstIwrjeFv-_wlAyfdpIvqDGZjNrl5oO=w2400" width="750" alt="Brazo en la base" />
  <br>
  <b>Fig. 21.</b> Brazo montado sobre la base móvil (04/10, montaje anterior con los motores 5840).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1HyaP275RmrgxX_qIGajPzEu_cgAfFLFs=w2400" width="550" alt="Equipo" />
  <br>
  <b>Fig. 22.</b> Ajustes del montaje (04/10).
</p>

<!-- celda -->
---
## **9. Pruebas en lazo abierto**

<!-- celda -->
En lazo abierto se aplica un PWM fijo al motor y solo se mide cómo responde, sin corregir nada. Estos ensayos se hicieron en la Entrega 5, con cada motor suelto, y sirvieron para obtener su modelo y diseñar el control de la Entrega 6. Son resultados históricos: valen para el motor, el driver y la transmisión con que se hicieron, y no se trasladan a los 36-555 de J2 y J3.

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1-JUJ8dF6WeEokr63-4hQyecQUUzOfPHo=w2400" width="1000" alt="Montaje del ensayo" />
  <br>
  <b>Fig. 23.</b> Montaje de los ensayos en lazo abierto. Diagrama propio (draw.io).
</p>

#### Ensayos

| Ensayo | Qué se aplica | Qué se obtiene |
| :--- | :--- | :--- |
| Barrido | PWM de 0 a 100 %, en los dos sentidos | Ganancia $K$ y zona muerta |
| Escalón | Salto de 0 a 50 % | Constante de tiempo $\tau$ |
| Escalera | Escalones de ±20 a 100 % | $K$ y $\tau$ en cada nivel |
| Rampa | 0 a 100 % en 3 s, con y sin carga | Efecto de la carga |

#### Resultados (Entrega 5, eje libre)

| Parámetro | 36GP-555 + IBT-2, sin correa (motor de J1) | 5840-31ZY + L298N (motor anterior de J2/J3, descartado) |
| :--- | :---: | :---: |
| Ganancia $K$ | 1,58 rpm/% | 1,33 rpm/% |
| Constante de tiempo $\tau$ | 65 ms | 59 ms |
| Zona muerta | 16 % (vacío), 25 % (con carga) | 20 a 40 % |
| Rango lineal | 20 a 85 % | 40 a 100 % |
| Velocidad máxima | ~145 rpm | ~140 rpm |

Con eso, cada motor se modela como un sistema de primer orden:

$$
G_{J1}(s) = \frac{1{,}58}{0{,}065\,s + 1}, \qquad G_{J2,J3}(s) = \frac{1{,}33}{0{,}059\,s + 1} \qquad \left[\frac{\text{rpm}}{\%}\right]
$$

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1nMkaTB0E_o838c02K2qYTp8ZsxVp0GWJ=w2400" width="850" alt="Barrido J1" />
  <br>
  <b>Fig. 24.</b> Barrido de PWM del motor de J1: la velocidad crece en forma lineal y es igual en los dos sentidos.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1AI-9Ek6PiuZWjWYRvRpKN9Sw8G9Pbxs3=w2400" width="850" alt="Escalera J2/J3" />
  <br>
  <b>Fig. 25.</b> Perfil en escalera del motor de articulación: con ±20 % no se mueve (zona muerta); desde 40 % responde en forma lineal.
</p>

#### Con el brazo montado

En la Entrega 6 se repitió la medición de la zona muerta con el **5840 montado en el brazo** y el driver IBT-2 a 1 kHz, con barridos lentos. La gravedad la cambia, porque el motor tiene que levantar el peso del brazo:

| Articulación | PWM para subir | PWM para bajar |
| :--- | :---: | :---: |
| J3 (codo) | $26{,}1 + 1{,}42\,\theta$ % (crece con el ángulo) | 5,7 % |
| J2 (hombro, con resorte) | 48 a 59 % | 9 a 10 % |

#### Conclusiones

* **J1:** el modelo de primer orden del 36GP-555 alcanzó para diseñar el control en cascada. En la E6, montado en el brazo con su correa, cumplió: sin sobrepico y con error final menor a 0,5°.
* **5840 (J2/J3):** su modelo con el eje libre era bueno, pero el motor no sirvió en el brazo. Lo decisivo no fue el PWM necesario para subir, sino que sin resorte no levantaba el brazo y con resorte oscilaba (sección 4.1).
* **La zona muerta es la principal no linealidad.** El firmware la compensa sumando el PWM mínimo según el sentido.
* **Pendiente:** hacer el barrido y el escalón con los 36-555 y sus engranajes cuando lleguen, para obtener su $K$ y su $\tau$.

<!-- celda -->
---
## **10. Videos**

<!-- celda -->
**Demo del brazo:** pendiente. Se agrega cuando estén montados y probados los motores nuevos de J2 y J3.

**Lazo cerrado:** pruebas del control de cada articulación por separado.

[![Ver lista de reproducción de lazo cerrado](https://img.youtube.com/vi/N8ZAt2xnw8k/hqdefault.jpg)](https://www.youtube.com/playlist?list=PLQCLakFxinI0)

**Simulación en Gazebo:** el robot completo en una hilera virtual de limoneros. Avanza por el pasillo, se detiene frente a cada limón, y el brazo lo agarra, lo retira y lo suelta. En la simulación se cosecharon los 12 limones de la hilera. Usa la misma cinemática inversa y la misma lógica de la misión que el robot real. La posición de cada limón la entrega el simulador, porque el detector YOLO no reconoce los limones dibujados en Gazebo. Es una simulación, no un ensayo del brazo físico.

[![Ver simulación en Gazebo](https://img.youtube.com/vi/1bYreQDusFI/hqdefault.jpg)](https://youtu.be/1bYreQDusFI)

**Lazo abierto:** pruebas del motor 36GP-555 de J1 y del 5840 que se usó en J2 y J3, ya descartado.

[![Ver lista de reproducción de lazo abierto](https://img.youtube.com/vi/RdY4UUS9w7Y/hqdefault.jpg)](https://www.youtube.com/playlist?list=PLWtzqMv9awVo)




<!-- celda -->
---
## **11. Referencias**

<!-- celda -->
Todas las referencias son de acceso abierto (licencias Creative Commons).

[1] D. Font, T. Pallejà, M. Tresanchez, D. Runcan, J. Moreno, D. Martínez, M. Teixidó y J. Palacín, "A Proposal for Automatic Fruit Harvesting by Combining a Low Cost Stereovision Camera and a Robotic Arm", *Sensors*, vol. 14, n.º 7, pp. 11557–11579, 2014. DOI: [10.3390/s140711557](https://doi.org/10.3390/s140711557).

[2] C. Han, J. Lv, C. Dong, J. Li, Y. Luo, W. Wu y M. A. Abdeen, "Classification, Advanced Technologies, and Typical Applications of End-Effector for Fruit and Vegetable Picking Robots", *Agriculture*, vol. 14, art. 1310, 2024. DOI: [10.3390/agriculture14081310](https://doi.org/10.3390/agriculture14081310).

[3] M. Ghonimy y N. F. Abdel-Baky, "Robotic Fruit Harvesting Systems: Integration of Perception, Manipulation, and Detachment for Autonomous Harvesting", *Agronomy*, vol. 16, art. 1127, 2026. DOI: [10.3390/agronomy16121127](https://doi.org/10.3390/agronomy16121127).

[4] T. Nguyen, H. Nguyen, T. Ngo *et al.*, "Design and implementation of a field robot using a parallelogram mechanism", *Science Progress*, vol. 107, n.º 4, 2024. DOI: [10.1177/00368504241291124](https://doi.org/10.1177/00368504241291124).

[5] D. Schütz y J. H. Hepworth, "uArm Swift simulation and control", *MATEC Web of Conferences*, vol. 406, art. 04014, 2024. DOI: [10.1051/matecconf/202440604014](https://doi.org/10.1051/matecconf/202440604014).

[6] Y. Tao, F. Chen y H. Xiong, "Kinematics and Workspace of a 4-DOF Hybrid Palletizing Robot", *Advances in Mechanical Engineering*, vol. 6, art. 125973, 2014. DOI: [10.1155/2014/125973](https://doi.org/10.1155/2014/125973).

[7] A. Wang, X. Tang, Y. Zeng, L. Zou, F. Bai y C. Chen, "Carbon Fiber-Reinforced PLA Composite for Fused Deposition Modeling 3D Printing", *Polymers*, vol. 16, n.º 15, art. 2135, 2024. DOI: [10.3390/polym16152135](https://doi.org/10.3390/polym16152135).

[8] D. Lee y G.-Y. Wu, "Parameters Affecting the Mechanical Properties of Three-Dimensional (3D) Printed Carbon Fiber-Reinforced Polylactide Composites", *Polymers*, vol. 12, n.º 11, art. 2456, 2020. DOI: [10.3390/polym12112456](https://doi.org/10.3390/polym12112456).

<!-- celda -->
---
### **Carpeta del proyecto**
En el link se encuentra la carpeta del proyecto.
[TPF R1 Grupo 2](https://drive.google.com/drive/folders/1d2jONLnkB8FMkP2iqF4ia4UeQ2jRpffz)
