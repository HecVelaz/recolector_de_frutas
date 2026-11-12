# Decisiones del proyecto

Movido de `CLAUDE.md` §6 el 22/10. Las de hardware y conexionado también en `CONEXIONES.md` (Decisiones de esta propuesta).

- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Base: frente = parte ancha (brazo), atrás = parte angosta (ruedas de tracción). 3 bumpers, sin trasero.
- Pi 5 arriba con las cámaras (no hay cable CSI largo): bajan USB a los ESP32 y el power bank va arriba, al lado de la Pi.
- Configuración RRR (opción 6 de la tabla R1); pinza con agarre + tracción + giro en vez de succión (aprobado por
  el profesor, 28/09).
- Medidas del brazo vigentes: las de la E4; motor de J1 = 36GP-555 160 rpm (el DC 895 de 2700 rpm fue un error de compra).
- Un ESP32 por subsistema y lazos cerrados en los ESP32: la Pi solo manda consignas y cada placa se detiene sola.
- Control en cascada posición → velocidad, porque la E5 identificó modelos de velocidad.
- Seguridad de la base decidida en la S3 (seta NC, vuelco, bumpers, distancia, watchdog), sin depender de la Pi.
- Armado por sesión en micro-ROS, para que un nodo que siga publicando no mueva el robot al reconectar.
- Cualquier nodo de ROS 2 en la misma LAN que la Pi ve y comanda los ESP32 reales (dominio 0): la simulación va
  aislada con `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`; con el robot real, no dejar agentes corriendo con el brazo
  armado si no se usa.
- EN común de tracción y GPS en la Pi (luz y buzzer, cuando vuelvan, también: GPIO 17 y 27): la S3 solo tiene libre el GPIO 40 (reservado para un 4.º bumper).
  GPS a la Pi (30/09) para dar un TRIG a cada HC-SR04: los 3 miran al frente y con TRIG común se pisaban los ecos.
- Videos (~500 MB) y artículos de terceros fuera de git.
- Cámaras (hallazgos de la simulación, valen para el robot real): el estéreo tiene una zona ciega a la izquierda de la
  imagen izquierda (42 % con la calibración vieja de la simulación; ~25 % con la del soporte rígido) y el brazo en reposo no puede quedar entre
  las cámaras y la fila. Con el brazo sobre el eje (29/09): mástil adelante a la derecha, cámara a 0,85 m mirando 94°
  a la izquierda y 28° abajo (del lado izquierdo quedaba tan cerca de la fila que ningún ángulo veía los 3 limones de
  un árbol), y reposo q = (75°, 94°, -50°) (provisorio, 18/10; antes 110°/-30°; con la cámara real la pinza en reposo se asoma hasta u ≈ 200 px, un poco fuera de la zona ciega: bitácora 17-18/10), girado a la izquierda: J1 no cruza el mástil (girado a la derecha lo
  atravesaba al ir al limón).
- Cámaras en el robot real (12/11): mástil adelante a la derecha, mirando a la izquierda (el limonero va a la
  izquierda), horizontales a ~58,7 cm del piso (no 0,85 m / 28° como en la simulación). La calibración estéreo se
  hace con el robot sobre una mesa (para cubrir el borde de abajo de la imagen parado) y los ensayos de distancia
  y cámara → brazo, en el piso.
- Simulación: brazo por velocidad (`JointController`, velocidad del perfil + corrección) y `/joint_states` a 50 Hz;
  con `JointPositionController` + `use_velocity_commands` el brazo temblaba (Gazebo va a la consigna en un paso).
- Simulación: no reentrenar YOLO con imágenes de Gazebo (arruinaría el modelo para los limones reales).
- Detector (28/10): una sola clase `limon` entrenada solo con limones verdes (el robot cosecha verdes); la madurez
  (B3) se decide por **tamaño** con el estéreo, no con clases de color: las NoIR corren el color y los datasets de
  Roboflow etiquetan colores distintos. Imágenes con limones de clases descartadas se sacan enteras.
