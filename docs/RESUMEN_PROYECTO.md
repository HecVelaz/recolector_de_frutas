# Resumen del proceso — Robot recolector de limones "Arturito R2D2"

Grupo 2, FIUNA Mecatrónica, 2026S2. Materias: **Robótica I** (brazo) y **Robótica II** (robot móvil con ROS 2).
Objetivo mínimo: **el robot se mueve, detecta el limón con YOLO, lo localiza con estéreo y lo agarra.**
Resumen al 30/09/2026. El detalle está en `BITACORA.md` y el estado vigente, en `CLAUDE.md`.

---

## Etapa 1 — Definición y diseño (entregas de R1 y R2, agosto-septiembre)

### 1. Consignas de las dos materias
R1 pide un brazo RRP/RRR sobre un eje lineal, cámaras estéreo y fruta real sin daño. R2 pide un robot con ROS 2 de
al menos 40 × 35 cm con encoders, IMU, GPS, sensores de distancia, bumpers, seta, 45 min de autonomía y una FSM.
El limón no figura en la guía de R2, pero **el profesor lo aprobó**.

### 2. R1 E1 y E2: concepto del brazo (18/08 y 27/08)
Brazo 4R: 3 articulaciones de posición y una J4 que gira la pinza. Usa un paralelogramo tipo uArm con los motores en
la base. Se definieron el primer espacio de trabajo (q1 ±75°, q2 −25…135°, q3 ±50°) y el CAD de la pinza. Se eligió
la **opción 6 de la tabla R1 (RRR-Limón)**.

### 3. R2 E1: estado del arte y primeras pruebas (30/08)
Estado del arte de la cosecha de cítricos, lista de componentes y pruebas sueltas de IMU, GPS, bumpers y ultrasonido
con video. Estas pruebas están en el repo aparte `~/pruebas-esp32`.

### 4. R1 E3: cinemática directa (13/09)
Cinemática directa por geometría y por DH, cierre del cuatro barras y simulación 3D.

### 5. R1 E4: cinemática inversa (23/09)
Cinemática inversa con filtros. Sus **medidas son las vigentes**: 150 / 350,22 / 329,51 mm, l4 = 338 mm y
balancines de 40 mm. Con 40 mm el mecanismo no era Grashof: **el balancín rojo se cambió a 60 mm** (verificado
en el brazo armado, 2026-10-03) y ahora sí lo es (40 + 350,22 < 338 + 60). La roja se mueve unos 82° respecto de
la verde (γ₄ entre −112° y −30°, con μ entre 15° y 165°); J2 y J3 son de sin fin, así que con uno quieto el otro
cambia γ₄ grado por grado (`pruebas-esp32/10-control-lazo-cerrado/tools/cuatro_barras.py`).

### 6. R1 E5: identificación en lazo abierto (27/09)
Modelos de primer orden de velocidad: base G = 1,58/(0,065s+1) y articulación G = 1,33/(0,059s+1). Zona muerta del
16 % (25 % con carga). Como lo que se identificó fue la velocidad, se eligió un **control en cascada
posición → velocidad**.

### 7. R2 E2 y E3: base del robot (27/09)
Base de madera en **T** de 40 cm de largo. Adelante va la parte ancha (40 × 23 cm) con el brazo y atrás la angosta
(34 × 17 cm), con las ruedas de tracción en rebajes de 3 cm. Lleva 2 ruedas locas, 3 bumpers y una batería de 36 V.

---

## Etapa 2 — Repositorio, firmware y ROS 2 (27/09)

### 8. Entorno de trabajo
Se instalaron Node.js y Codex CLI (que solo revisa) y se armó la barra de estado de Claude Code. Además se hizo el
grafo del repo con graphify: 1009 nodos y 54 comunidades.

### 9. Documentación base
- `INDICE.md`: una línea por documento.
- `ARQUITECTURA.md`: objetivo mínimo, nodos, control y FSM.
- `Componentes_inventario.md`: inventario de componentes.
- `CONEXIONES.md` y `conexiones.html`: pines de las dos placas y de la Pi, y alimentación.

### 10. Arquitectura: un ESP32 por subsistema
La Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy) se ocupa de la visión, la IK y la misión. Habla por USB (micro-ROS)
con dos ESP32:
- una **ESP32-S3** para la base: tracción, encoders, IMU, HC-SR04, bumpers, seta y batería;
- una **ESP32-WROOM** para el brazo: J1, J2, J3 y 2 servos.

Los lazos se cierran en los ESP32 y cada placa se detiene sola.

### 11. Firmware del brazo
Control en cascada de J1 a J3 más la pinza, con comandos por serial. Nació en `pruebas-esp32` y se pasó a este repo.
Las pruebas en la PC encontraron que el motor se clavaba a ~1,4° del objetivo: se agregó feedforward de zona muerta.
Codex lo revisó y se aplicaron sus 10 hallazgos (homing, watchdog, servos sin pulsos al arrancar, entre otros).

### 12. Firmware de la base
Tracción diferencial, odometría, sensores y seguridad local en la S3: seta, vuelco, bumpers, distancia y watchdog.
Codex lo revisó y se aplicaron sus 9 hallazgos.

### 13. Capa micro-ROS
Las dos placas publican y reciben tópicos de ROS 2. Cada sesión arranca **desarmada**, así que hay que mandar
`armar`. Esto evita que un nodo viejo mueva el robot al reconectar. Codex lo revisó y se aplicaron sus 10 hallazgos.

### 14. Nodo `brazo_ik`
Es la cinemática inversa de la E4 en ROS 2. Probado con el ejemplo de la E4: error de 5e-13 mm. Rechaza, con su
motivo, los puntos fuera de alcance y los marcos equivocados.

---

## Etapa 3 — Primeras pruebas en placa, visión y misión (28/09)

### 15. Placas en la Pi con el agente micro-ROS
Las dos placas se probaron con el agente, solas y a la vez, y dieron tasas nominales, armado y reconexión. El brazo va
a 115200 porque el CH340 pierde datos a 921600. La S3 se flashea con reset por watchdog. El ping se subió a 100 ms
porque había cortes falsos por latencia. **Todo esto fue con las placas solas, sin motores ni sensores.**

### 16. Hardware de tracción confirmado
Motor 42GM-895H planetario 189:1 con encoder Hall de 11 PPR a 5 V (`cuentasPorVuelta` = 8316). Hay que bajar las
señales A/B a 3,3 V.

### 17. Visión estéreo en la Pi
Está en el repo aparte `vision_estereo`: cámaras, rectificación, disparidad BM, YOLO y localizador, que publica
`/limon/posicion`. Con NCNN detecta a ~7-9 FPS y localiza a ~2-4 Hz, en una ventana de 0,40 a 0,95 m.

### 18. Detector de limones entrenado
YOLO entrenado en Colab con datasets de Roboflow y una sola clase, `limon`. En test da mAP50 0,978 (números
optimistas). **Todavía no se probó con limones reales ni con las cámaras NoIR.**

### 19. Nodo `mision`
FSM mínima: ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR, más un estado FALLA. Incluye la TF de la cámara al
brazo. La llegada se decide por posición. Codex la revisó y tiene 17 pruebas.

### 20. `EncoderPCNT` sin salto falso
El contador por hardware se desenvuelve por software, lo que corrige un salto de 32 000 cuentas. Codex lo revisó.

### 21. Pinza y brazo tipo uArm
La pinza tiene 2 servos RDS3218 para agarre, tracción y giro, en vez de succión (aprobado por el profesor). La
herramienta queda siempre horizontal y `/brazo/objetivo` pasa a ser el punto de agarre (TCP).

---

## Etapa 4 — Simulación en Gazebo Harmonic (28 y 29/09)

### 22. Etapas 1 a 4 de la simulación
- Hilera de 4 + 4 limoneros con las medidas de R1.
- Base real de la R2 E3.
- Brazo con `brazo_sim`, que imita al firmware.
- 12 limones cosechables y obstáculos entre las paradas.

Con `mision:=true` cosecha **12 de 12 limones**. Con `vision:=yolo` la cadena real funciona a medias: el estéreo
localiza, pero YOLO no reconoce los limones sintéticos.

### 23. Aislamiento de la red
La simulación veía y comandaba por la LAN los ESP32 reales de la Pi, con el brazo ARMADO. Ahora va aislada con
`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.

### 24. Brazo atrás y mástil de cámaras
El brazo quedó atrás a la izquierda, sobre el eje de tracción. El mástil va adelante a la derecha, con la cámara a
0,85 m mirando 94° a la izquierda y 28° abajo. El reposo del brazo es q = (75°, 110°, -30°), para no cruzar el
mástil. Se arregló también el temblor del brazo, que ahora se controla por velocidad con `/joint_states` a 50 Hz.

### 25. Etapa 5: seguridad de la base simulada
`base_sim` porta la seguridad de la S3: arranca desarmada y tiene watchdog de 300 ms. Se agregaron 3 HC-SR04 al frente
y 3 bumpers con resorte.

### 26. Recorrido autónomo
`mision/recorrido.py`, con `autonomo:=true`. El robot:
- avanza y frena cuando ve un limón;
- se arrima o retrocede para alcanzarlo;
- esquiva obstáculos con los HC-SR04;
- mantiene el rumbo con el giróscopo.

Resultado: **12 de 12 limones sin teleop**, sin tocar los obstáculos.

---

## Etapa 5 — Alimentación y conexiones (29 y 30/09)

### 27. Batería 10S de 36 V
10S2P Li-ion de 4400 mAh y 158 Wh: alcanza de sobra para 45 min. Lo difícil es bajar a 12 V con corriente. Codex
encontró tres problemas:
- los servos quedaban fuera de la seta;
- el INA219 no aguanta 42 V;
- la corriente del BMS no está documentada.

### 28. Árbol de alimentación con los buck disponibles
Solo el buck 1 aguanta la batería. El reparto queda así:
- buck 1-A para los motores, con Schottky, capacitor, TVS y el relé de la seta del lado de 12 V;
- un segundo buck 1 para la lógica (falta comprarlo);
- el buck 2 para la Pi;
- el buck 3 para los servos.

El divisor de batería es de 120 k / 8,2 k. Está en `CONEXIONES.md` v0.3.

### 29. GPS en la Pi y un TRIG por HC-SR04
El GPS pasó a la UART de la Pi (`nmea_navsat_driver`, que publica en `/gps/fix`). Eso libera 2 pines de la S3, y
ahora cada HC-SR04 tiene su propio TRIG y se disparan de a uno cada 40 ms. Con el TRIG común se pisaban los ecos.
Codex lo revisó sin hallazgos. **En la Pi ya está configurado, pero falta conectar el GPS.**

---

## Etapa 6 — Próximos pasos

### 30. Calibración y medidas
- Verificar que `cuentasPorVuelta` da 8316.
- Armar el soporte rígido de las cámaras y recalibrar.
- Medir la TF de la cámara al brazo, `largo_herramienta` y todo lo marcado `MEDIR`.

### 31. Visión con limones reales
Probar YOLO con limones verdes frente a las NoIR a 40-90 cm. Si falla, sumar fotos propias al entrenamiento.

### 32. Cableado y periféricos
Cablear según "Antes de conectar", conectar el GPS y probar los drivers y sensores. Hasta ahora no se probó nada con
periféricos.

### 33. Primeras pruebas con motores
- Brazo con motores, con la secuencia de su README.
- Base con las ruedas en el aire: sentidos, radio, trocha y la parada real por el watchdog.
- `mision` con el brazo real.

### 34. Compras y seguridad eléctrica
Comprar el segundo buck 1, el Schottky, el capacitor de 2200 µF, el TVS de 15 V y el relé de 40 A. Armar el divisor
**antes** de conectar la batería.

### 35. Informes y cátedra
- Corregir R2 E2: MPU-6050 → MPU-6500, y Humble/22.04 → Jazzy/24.04.
- Corregir R2 E3: son 2 drivers en el brazo.
- Preguntar a la cátedra por el eje lineal, los GDL en R2 y los cajones.
