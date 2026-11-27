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
- **Demo con un arbolito y marcas ArUco, GPS solo para la rúbrica (13/11, usuario; detalle en
  `pruebas-esp32/notas/DECISIONES.md`):** el profesor acepta un árbol en el aula y marcas; la parada pide ±5 cm y el
  UP501 da ±20 m. Giros con el giróscopo y distancia con las ruedas (las ruedas se pasan ~2° cada 90°).
- **Celular como sensor de navegación: no por ahora (17/11):** no mejora la parada (±5 cm), el magnetómetro sufre
  junto a los motores y H2/H3 lo dejan en zona gris. Se reconsidera solo si sobra tiempo y la cátedra lo acepta.
- **Plan hasta la demo del 27/11 (17/11, usuario):** prioridad a la demo con el arbolito (BUSCAR, RODEAR, soltar,
  seguridad) y a pasarla a ROS; afuera la hilera, el EKF, la app nueva y las métricas detalladas.

- **Seguridad de la base (18/11, usuario):** solo el HC-SR04 del medio frena (tope lineal 50 → 20 cm); los de las
  esquinas solo publican. Bumpers, seta y vuelco enclavan hasta `r`.
- **Soltar el limón en una canasta sobre la tapa (18/11, usuario)**, con la pose plegada del brazo (J1 hasta 130).
  Pinza con el servo RDS3218 (el MG996R vibraba): abierta 500 µs, cerrada 1200.
- **Banderín único (19/11; detalle en `pruebas-esp32/notas/DECISIONES.md`):** una sola marca alcanza para ubicar el
  árbol (la pose da posición y rumbo); los limones se agarran siempre con la visión. Meta: cosecha con navegación el 27/11.
- **Demo afuera con un banderín y una hilera de 2-3 arbolitos (19/11, usuario):** reemplaza "un arbolito en el aula
  con 4 marcas"; ida por un lado y vuelta por el otro (vuelta en U antihoraria), el árbol siempre a la izquierda.
  En Gazebo: `mundo:=arbolitos`; navegación dentro de `nodo_mision` (`navegacion:=true`) para compartir con la misión
  cuándo la base está quieta (con un nodo aparte había una carrera entre APROXIMAR y el arranque de la base).
- **Simulación de la demo (19/11):** limones solo hasta 52 cm (usuario; el brazo simulado no llega más arriba por
  `Q3_LIM`, provisorio); cámara de navegación real en el urdf como `camara:=nav` (la v1 queda para la hilera);
  reposo del brazo J1 = 0° en ese mundo (a 75° la pinza tapa la cámara; el real espera sobre la canasta).
- **Seta y vuelco sin enclavar, sin `r` (21/11, usuario):** reemplaza "enclavan hasta `r`". Duran lo que dura la
  causa (vuelco con 3° de histéresis: entra a 25°, sale bajo 22°). Para que el robot no arranque solo al soltar la
  seta: el firmware anula el comando en curso y la capa ROS desarma la base (hace falta un `armar` nuevo; el puente
  lo manda al abrir cada sesión). Las fallas de rueda, que borraba `r`, ahora las borra `s`. La seta sigue cortando
  los 12 V por hardware (bloque A).
- **Homing desde la app con 1 s de tolerancia (21/11):** el puente corta el homing si pasa más de 1 s sin aviso de
  la app (los demás mandos siguen con 0,22 s); el homing lo hace el firmware a 1,5–5 °/s.
- **Ajuste fino del agarre solo con los puntos del 21/11** (detector v4); los 9 del 18/11 (v3) en `resultados/ajuste_viejo/`.
- **Cero de la recolección aproximado (21/11):** solo orienta el acercamiento (3,8 s, ≥ 2 lecturas, ≤ 30 mm); la
  medición que decide el agarre es la de al llegar (8 s, estricta). Si al llegar el limón no está donde se esperaba,
  se cosecha según esa medición siempre que el planificador dé agarre (pedido del usuario).
- **Modo Recolector (21/11, usuario):** cosecha desde donde está, sin mover la base ni necesitar cero; la lista del
  escaneo de 3 s vale solo para esa pose. Sin verificación final con la visión (pedido del usuario).
- **Visión a pedido apagando el grupo entero (22/11):** congelar los procesos con SIGSTOP dejó a la cámara izquierda
  sin publicar (Fast DDS por memoria compartida); se apaga y se relanza `start_limon.sh` (~21 s) con 30 s de margen
  sin pedido. A elección del usuario entre eso y "siempre encendida".
- **Profundidad (22/11):** el tamaño conocido del limón no se adopta por ahora (no cambió ninguna elección en las
  grabaciones); el candidato es el rechazo por pocos píxeles válidos. Esperando autorización del usuario.
- **Tablet por Tailscale (23/11):** el mando y la misión aceptan `127.0.0.1` (túnel USB) o `100.64.0.0/10`
  (Tailscale: cifrado, solo dispositivos de la cuenta); cualquier otra red, como la del lab, sigue rechazada.
- **Reset automático de la S3 solo si está en bootloader (23/11, OK del usuario):** excepción a "apagar los 12 V
  antes de resetear": en bootloader la S3 no controla los IBT-2, así que reiniciarla no agrega riesgo; si corre su
  firmware, `arrancar_pi.sh` no la toca. La costumbre sigue siendo prender la Pi con los 12 V apagados.
- **Mando manual como `teleop.html` (23/11, pedido del usuario):** brazo hasta 1 rad/s (60 % por defecto) y giro de
  la base hasta 1 rad/s (antes 0,15 y 0,15).

## 2026-11-25
- **Rodear árbol es una tarea aparte** (no una opción del Recolector), pedido del usuario: el Recolector queda para una
  estación. Paradas antihorario (árbol del lado del brazo), 1–4 según el espacio, y siempre vuelve al primer escaneo
  (con < 4, por donde vino y mirando hacia adelante: atrás no hay sensores).
- **Un limón que no se ve al medir no se agarra** (antes se agarraba con la posición guardada): pedido del usuario.
- **Prioridad del puente sobre la visión** (nice 0 / 5 / 10) en vez de apagar la visión durante la cosecha: apagarla
  y prenderla cuesta ~21 s y carga la Pi.
- **La batería se corrige en el puente** (× 0,959) y no en el firmware antes de la demo, para no reflashear la S3.
- **J1 sale de la canasta con el joystick** en vez de subir el despegue o el tiempo "sin cuentas" del firmware 20 (sin
  reflashear antes de la demo); no se bajan los plazos de supervisión del mando por el teléfono lento.

## 2026-11-27
- **J1 pasa de la correa GT2 18 → 84 a engranajes doble helicoidales 15 → 80 (5,333:1)**, misma distancia entre
  centros (57 mm) y ancho (17,5 mm); doble helicoidal como J2/J3 para no tener empuje axial. Datos en `ENGRANAJES_J1.md`.
- **Revertido el mismo 27/11: J1 vuelve a la correa GT2 18 → 84** por problemas de montaje de los engranajes. El firmware
  no cambia. Lo demás del robot sigue como estaba planeado (J2/J3 con helicoidales 15 → 75).
