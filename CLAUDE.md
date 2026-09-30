# CLAUDE.md — recolector_de_frutas

**Hablar siempre en castellano** (rioplatense, como el usuario): respuestas, avisos intermedios y explicaciones,
también en sesiones largas o mientras se depura. Nunca pasar al inglés. Detalle histórico en `docs/BITACORA.md`.

## 1. Proyecto
Robot móvil autónomo recolector de limones "Arturito R2D2" (Grupo 2, FIUNA Mecatrónica, 2026S2). Cubre dos
materias: **Robótica I** evalúa el brazo; **Robótica II**, el robot móvil con ROS 2. Objetivo mínimo para aprobar:
**el robot se mueve, detecta el limón con YOLO, lo localiza con estéreo y lo agarra** (`docs/ARQUITECTURA.md`).

## 2. Hardware y arquitectura
- Base (R2 E3): caja de madera en **T** de 40 cm de largo y ~20 cm de alto. **Adelante** la parte ancha (40 × 23 cm,
  con el brazo); **atrás** la angosta (34 × 17 cm) con las ruedas de tracción en rebajes de 3 cm; 2 ruedas locas.
  Ruedas inflables de **150 mm** × 45 mm (`docs/fotos/rueda/`), trocha ~0,40 m (MEDIR).
- Tracción: 2× 42GM-895H planetario, 12 V, 53 rpm, 189:1, encoder Hall 11 PPR a 5 V (A/B salen a 5 V: bajar
  a 3,3 V). Hoja del vendedor en `docs/fotos/motor_traccion/`.
- **Batería: 10S2P Li-ion de 36 V (30-42 V), 4400 mAh, 158 Wh, XT60** (`docs/fotos/bateria/`). Los motores son de
  12 V. Buck (`docs/fotos/bucks/`): solo el **buck 1** (10,5-60 V, 12 A) aguanta la batería; los 2, 3 y 4 van
  colgados de 12 V. Falta un segundo buck 1 (motores y lógica separados). Divisor de batería 120 k / 8,2 k (el viejo
  de 12 V quemaría el GPIO). Ver `docs/CONEXIONES.md` (v0.2) y `docs/conexiones.html`.
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión, IK, misión. Habla por USB (micro-ROS) con dos ESP32.
  Propuesta: la Pi arriba del mástil junto a las cámaras (cable CSI corto) y USB hacia los ESP32. **GPS UP501 en la
  Pi** (UART GPIO 14/15, `nmea_navsat_driver` → `/gps/fix`; Pi configurada, falta conectar el GPS) por un HAT pasivo de borneras.
- **ESP32-S3** (base): 2 motores de tracción + 2 IBT-2, encoders, IMU MPU-6500 (sin magnetómetro),
  3 HC-SR04 (un TRIG cada uno: 10/41/42, de a uno cada 40 ms), **3 bumpers** (frente y laterales), seta, batería. **ESP32-WROOM-32D** (brazo): J1 36GP-555 + IBT-2,
  J2/J3 5840-31ZY (sin fin) + un L298N, 2 servos. En total 4 drivers.
- Brazo RRR montado **atrás a la izquierda, sobre el eje de tracción**, a ~6 cm del costado (y = 0,11 m; preliminar). **Tipo uArm / Dobot Magician**: cuatro barras (medidas de la E4) y un paralelogramo que mantiene la
  herramienta **siempre horizontal**, apuntando en la dirección de J1 (E1). Pinza con 2 servos DSSERVO RDS3218
  20 kg·cm (apertura y giro J4 sobre el eje de la herramienta; foto en `docs/fotos/pinza/`). Pines y alimentación: `docs/CONEXIONES.md`.

## 3. Estructura
- `docs/`: consignas, `TPF R1/` y `TPF R2/` (una carpeta por entrega), `fotos/` (motor, pinza, rueda, batería),
  `INDICE.md`, `ARQUITECTURA.md`, `CONEXIONES.md`, inventario, bitácora.
- `firmware/lib/`: drivers y lógica compartidos (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, L298N,
  EncoderPCNT, HCSR04, MPU9250, UP501). `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/brazo_ik/`: nodo de cinemática inversa; `ros2_ws/src/mision/`: FSM de la demo y TF cámara → brazo. `ros2_ws/src/simulacion/`: Gazebo Harmonic (hilera + robot). `vision/entrenamiento_limon/`: cuaderno de Colab del
  detector. `graphify-out/`: grafo del repo (local, fuera de git).

## 4. Cómo trabajar acá
- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF ni `.ipynb`** (bloqueados en
  `.claude/settings.json`): usar sus `.txt`/`.md`.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor con `-s read-only`; sandbox arreglado el 28/09 con el perfil AppArmor `/etc/apparmor.d/bwrap`;
  lanzar con `< /dev/null` **desde la carpeta del repo** y esperar `tokens used`; confirmar a los 20 s que abrió
  sesión); **graphify** (grafo del repo); **ponytail**
  (instalado, sin usar todavía). `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas
  (`codex --sandbox workspace-write` en el repo; lee este archivo por `AGENTS.md`); al volver, revisar `git log` antes de seguir.

## 5. Estado actual (2026-09-30)
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 17 pruebas OK.
  Probado en la placa sola (sin motores ni sensores).
- `firmware/base`: tracción diferencial, odometría, sensores, seguridad local; serial o micro-ROS. 20 pruebas OK.
  Al 29/09: ruedas de 150 mm (radio 0,075), trocha 0,40, 3 bumpers (frente: no avanza; laterales: sin giro), batería
  10S (aviso a 32 V, divisor 120 k / 8,2 k).
  Probado en la placa sola (sin motores ni sensores).
- Capa micro-ROS: compila en las dos placas; cada sesión arranca **desarmada** (`armar` por `/<parte>/comando`).
  Las dos placas probadas con el agente, solas y a la vez (28/09): tasas nominales, armado y reconexión.
  S3: flashear con reset por watchdog (ya en `platformio.ini`); abrir el puerto con DTR/RTS bajos la deja en
  modo descarga. Usar `/dev/serial/by-id/` porque el puerto pasa de ACM0 a ACM1.
- `brazo_ik`: 6 pruebas OK. `/brazo/objetivo` es el punto de agarre (TCP); con la herramienta horizontal, la muñeca
  está `largo_herramienta` más adentro en horizontal (parámetro; 0 por defecto, MEDIR en el real).
- Pi 5 (`r2d2@100.116.96.71`, Tailscale `r2d2-desktop`): Jazzy, agente micro-ROS en `~/microros_ws`, copia del repo
  en `~/recolector_de_frutas` (por rsync, sin `.git`), esptool en `~/esptool_env`. Las dos placas conectadas a la
  Pi con sus agentes: todas las tasas nominales. Brazo a 115200 (a 921600 el CH340 pierde datos en la Pi).
  **Todo lo del 28/09 fue con las placas solas: sin motores, drivers, encoders, IMU, GPS, HC-SR04, bumpers ni
  seta.** Las tasas son de mensajes sin datos reales (distancias NaN, IMU y GPS no publican). Los drivers y
  sensores siguen sin probar en este proyecto.
  Agentes: `micro_ros_agent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` (brazo) y
  `.../usb-Espressif_USB_JTAG_serial_debug_unit_*-if00` (base). Si la S3 no abre sesión, está en modo descarga:
  `~/esptool_env/bin/esptool.py --port <S3> --before no_reset --after watchdog_reset read_mac`.
  La base se había cortado 2 veces (ping de 20 ms, cortes falsos por latencia): ping a 100 ms y contadores
  `enlace: pings_fallidos cortes` en `/<parte>/estado`; bajo carga fuerte, 0 cortes. Pendiente con ruedas: medir
  la parada real por el watchdog de 300 ms (revisión de Codex: a 1 m/s, ~30 cm antes de empezar a frenar).
- Visión: repo aparte `HecVelaz/vision_estereo` (en la Pi, `~/vision_estereo`; en GitHub al día). Cadena
  `scripts/start_limon.sh` = `launch/limon.launch.py` (cámaras, rectificación, disparidad BM) + `detector_node`
  (`/yolo/detecciones`) + `localizador_node` (`/limon/posicion`, PointStamped en el marco óptico RECTIFICADO de
  la cámara izquierda: tenerlo en cuenta en la TF al brazo). Con NCNN y OpenMP pasivo: detección ~7-9 FPS,
  posición ~2-4 Hz. La ventana de disparidad sale de la calibración para 0,40-0,95 m (v1: f = 1076,5 px ->
  112-271 px). Revisado por Codex. Calibración en uso: v1 (`config/calibracion/`); la v2 (RMS 0,32 px, baseline
  99,3 mm, f ~680) es de un montaje de cartón: recalibrar con el soporte rígido (el usuario avisa) y apuntar
  `CARPETA_CALIBRACION`. Exposiciones izq/der sin sincronizar: localizar con el robot quieto.
- **Cinta CSI dañada (30/09)**, al pasar al soporte nuevo: con ella la cámara no se detecta, o se detecta y falla al
  transmitir (`Failed to write reg`, `stream on failed`, `Camera frontend has timed out`). Aislada intercambiando
  cintas: las 2 cámaras y los 2 puertos andan. **Hoy funciona una sola cámara**: falta una cinta nueva (Pi 5, 22 a
  15 pines). Detección: `journalctl -k -b | grep "found subdevice"` (solo al arrancar: cambiar cintas con la Pi apagada).
  Transmisión: `start_cameras_full.sh`; `~/probar_camaras.sh` en la Pi prueba las dos cosas (la parte de transmitir sin
  probar). Vista de las dos en crudo: `/tmp/vista/index.html` servido en el puerto 8081 + `web_video_server` en el 8080
  (`/tmp` se borra al reiniciar). `limon.launch.py` no usa el modo de sensor, el foco ni los índices de
  `start_cameras_full.sh` (izquierda = 1 contra 0): igualarlos antes de recalibrar.
- Detector de limones (28/09): entrenado en Colab con `vision/entrenamiento_limon/` (datasets de Roboflow, una
  clase `limon`). Test: P 0,953, R 0,977, mAP50 0,978, mAP50-95 0,814 (285 imágenes, 200 sin limón, 173
  limones; mismas fuentes que el entrenamiento: números optimistas). En la Pi:
  `~/vision_estereo/modelos/limon_yolo26n_ncnn_model` (fuera de git; 23 FPS solo). El `.pt` quedó en Drive
  (`arturito/limon_yolo`). **Sin probar con limones reales ni con las NoIR.** Uso:
  `MODELO=~/vision_estereo/modelos/limon_yolo26n_ncnn_model CLASE=limon ~/vision_estereo/scripts/start_limon.sh`
- Revisados por Codex (brazo, base, micro-ROS, cambios del 28/09 y visión) y hallazgos aplicados.
- `EncoderPCNT` (28/09): sin interrupción; desenvuelve el contador por software en cada `count()` (salto falso de
  32 000 corregido). Hay que leer antes de ~1,5 s (J2/J3); si no, `ControlArticulacion` entra en falla de encoder.
  Revisado por Codex. **Sin probar en placa**: girar un motor a mano más de 32 000 cuentas y ver que no salte.
- `simulacion` (Gazebo Harmonic en la notebook; README del paquete): `ros2 launch simulacion sim.launch.py`
  (`gui:=false`, `mision:=true`, `vision:=yolo`). Mismos tópicos que los ESP32 (`brazo_sim` imita al firmware del
  brazo), así que `mision`, `brazo_ik` y la visión corren sin cambios. Base real de la R2 E3 (T, ruedas de 150 mm,
  brazo atrás a la izquierda sobre el eje, mástil de cámaras adelante a la derecha, dibujado). Hilera de 4+4 limoneros con las medidas de
  R1, 12 limones cosechables, 2 obstáculos (caja y balde) entre las **marcas de parada** (x = 1,19 / 2,70 / 4,17 / 5,69: frenar
  con el eje de las ruedas sobre la franja, ±2 cm, en el centro del pasillo). Con `mision:=true`, **12 de 12 limones cosechados** en las 4 paradas
  (TCP a ≤ 0,1 cm, base quieta). Etapa 3 (`vision:=yolo`, cámaras de Gazebo + cadena real) parcial: el estéreo
  localiza, YOLO no reconoce los limones sintéticos. Etapa 5 (29/09): `base_sim` imita la S3 (seguridad de
  `SeguridadBase` portada, arranca DESARMADA: `armar` por `/base/comando`, teleop con `repeat_rate:=10.0`), 3 HC-SR04
  (`gpu_lidar`) y 3 bumpers con resorte. Falta pasarla a la PC de escritorio. **Aislada de la red** (`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` en el launch y en cada terminal): si
  no, ve y comanda los ESP32 reales de la Pi. Trucos de la física: masas del brazo al 5 % (si no, la base se deslizaba
  con las ruedas frenadas), el limón agarrado se lleva con `set_pose` y `limones_sim` usa la pose real de Gazebo.
- Recorrido autónomo (29/09, `mision/recorrido.py`, `autonomo:=true`): avanza de corrido, frena por YOLO en la zona
  útil del estéreo, se arrima, retrocede por limones que quedaron atrás, esquiva con los 3 HC-SR04 (ahora los 3 al
  frente) y usa el rumbo del giróscopo. En la simulación: **12 de 12 limones sin teleop**, sin tocar la caja ni el
  balde. Sin probar en el robot real (calibrar el sesgo del giróscopo; supone arrancar en el centro del pasillo).
- `mision` (28/09): FSM mínima (ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR, FALLA manda `s`) + TF
  `brazo_base → stereo_camera_link` en `mision.launch.py` (argumentos obligatorios: MEDIR). Llegada por posición
  (`joint_states` contra `joint_cmd`). Revisada por Codex y aplicada; 17 pruebas OK; probada en la notebook con
  brazo y limón simulados. Sin probar con el brazo real. Usa el mismo `largo_herramienta` que `brazo_ik` (MEDIR).

## 6. Decisiones
- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Base: frente = parte ancha (brazo), atrás = parte angosta (ruedas de tracción). 3 bumpers, sin trasero.
- Pi 5 arriba con las cámaras (no hay cable CSI largo): bajan USB a los ESP32 y sube 12 V con el buck de 5 V arriba.
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
- EN común de tracción, luz/buzzer y GPS en la Pi: la S3 solo tiene libre el GPIO 40 (reservado para un 4.º bumper).
  GPS a la Pi (30/09) para dar un TRIG a cada HC-SR04: los 3 miran al frente y con TRIG común se pisaban los ecos.
- Videos (~500 MB) y artículos de terceros fuera de git.
- Cámaras (hallazgos de la simulación, valen para el robot real): el estéreo solo localiza con u >= 271 px en la
  imagen izquierda (ventana 0,40-0,95 m: el 42 % izquierdo queda ciego) y el brazo en reposo no puede quedar entre
  las cámaras y la fila. Con el brazo sobre el eje (29/09): mástil adelante a la derecha, cámara a 0,85 m mirando 94°
  a la izquierda y 28° abajo (del lado izquierdo quedaba tan cerca de la fila que ningún ángulo veía los 3 limones de
  un árbol), y reposo q = (75°, 110°, -30°), girado a la izquierda: J1 no cruza el mástil (girado a la derecha lo
  atravesaba al ir al limón).
- Simulación: brazo por velocidad (`JointController`, velocidad del perfil + corrección) y `/joint_states` a 50 Hz;
  con `JointPositionController` + `use_velocity_commands` el brazo temblaba (Gazebo va a la consigna en un paso).
- Simulación: no reentrenar YOLO con imágenes de Gazebo (arruinaría el modelo para los limones reales).

## 7. Próximos pasos
1. Verificar `cuentasPorVuelta` = 8316 de la tracción girando la rueda a mano (`vueltas` en `e`, README de la base).
2. Probar el detector con limones verdes reales frente a las NoIR (con luz, a 40-90 cm): si falla, esas fotos van
   al entrenamiento (fotos propias, subirlas a Roboflow y sumarlas en la celda 3 del cuaderno).
3. Cinta CSI nueva para la segunda cámara (§5). Soporte rígido de las cámaras (con los hallazgos de §6: que el limón caiga en la parte derecha de la imagen
   izquierda y el brazo en reposo no las tape), recalibrar y medir la precisión de `/limon/posicion` contra cinta.
4. Cablear según la lista "Antes de conectar" de `docs/CONEXIONES.md` (pull-down 10 kΩ en los EN, divisores de
   ECHO, pull-ups externos) y probar drivers y sensores (hoy nada probado con periféricos).
5. Primera prueba del brazo con motores (secuencia de su README; `v` sirve para la demo de la E6) y medir lo `MEDIR`.
6. Primera prueba de la base con ruedas en el aire (README): sentidos, radio, trocha y la parada real por watchdog.
7. Comprar un segundo buck 1 (lógica), Schottky ≥ 30 A, 2200 µF 25 V, TVS de 15 V y relé automotriz 12 V 40 A
   para la seta (corta del lado de 12 V); armar el divisor 120 k / 8,2 k antes de conectar la batería.
8. Medir la TF cámara → brazo con el soporte rígido (argumentos de `mision.launch.py`) y probar `mision` con el
   brazo real: `cierre`, `reposo` y `largo_herramienta` (muñeca → centro del agarre, en horizontal; más un desfase
   vertical si lo hay, hoy no contemplado).
9. Preguntas a la cátedra que quedan (`docs/ARQUITECTURA.md` §11: eje lineal de 1,2 m, GDL en R2, cajones).
10. Simulación: validar la cadena real con un detector "perfecto" sobre las imágenes de Gazebo (`vision:=yolo`, en la
   PC de escritorio); el recorrido autónomo ya cosecha 12 de 12 con `limones_sim`; cargar las medidas reales que faltan
   (altura de la caja sobre el piso, trocha, eje, ruedas locas, cámaras, pinza). Pendiente: cajón para el limón.
11. Corregir los informes: R2 E2 (MPU-6050 → MPU-6500; Humble/22.04 → Jazzy/24.04.5), R2 E3 (drivers del brazo: 2).
