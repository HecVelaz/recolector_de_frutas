# CLAUDE.md — recolector_de_frutas

**Hablar siempre en castellano** (rioplatense, como el usuario): respuestas, avisos intermedios y explicaciones,
también en sesiones largas o mientras se depura. Nunca pasar al inglés. Detalle histórico en `docs/BITACORA.md`.

## 1. Proyecto
Robot móvil autónomo recolector de limones "Arturito R2D2" (Grupo 2, FIUNA Mecatrónica, 2026S2). Cubre dos
materias: **Robótica I** evalúa el brazo; **Robótica II**, el robot móvil con ROS 2. Objetivo mínimo para aprobar:
**el robot se mueve, detecta el limón con YOLO, lo localiza con estéreo y lo agarra** (`docs/ARQUITECTURA.md`).

## 2. Hardware y arquitectura
- Tracción: 2× 42GM-895H planetario, 12 V, 53 rpm, 189:1, encoder Hall 11 PPR a 5 V (A/B salen a 5 V: bajar
  a 3,3 V). Hoja del vendedor en `imagen_motor_traccion/`.
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión, IK, misión. Habla por USB (micro-ROS) con dos ESP32.
- **ESP32-S3** (base): 2 motores de tracción + IBT-2, encoders, IMU MPU-6500, GPS UP501, 3 HC-SR04, 4 bumpers,
  seta, batería. **ESP32-WROOM-32D** (brazo): J1 36GP-555 + IBT-2, J2/J3 5840-31ZY (sin fin) + L298N, 2 servos.
- Brazo RRR con cuatro barras (medidas de la E4) + pinza con 2 servos DSSERVO RDS3218 20 kg·cm (apertura y giro J4;
  foto en `imagen_pinza/`). Pines y alimentación: `docs/CONEXIONES.md`.

## 3. Estructura
- `docs/`: consignas, entregas R1/R2, `INDICE.md`, `ARQUITECTURA.md`, `CONEXIONES.md`, inventario, bitácora.
- `firmware/lib/`: drivers y lógica compartidos (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, L298N,
  EncoderPCNT, HCSR04, MPU9250, UP501). `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/brazo_ik/`: nodo de cinemática inversa; `ros2_ws/src/mision/`: FSM de la demo y TF cámara → brazo. `vision/entrenamiento_limon/`: cuaderno de Colab del
  detector. `graphify-out/`: grafo del repo (local, fuera de git).

## 4. Cómo trabajar acá
- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF ni `.ipynb`** (bloqueados en
  `.claude/settings.json`): usar sus `.txt`/`.md`.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor en solo lectura; en esta PC su sandbox no lee archivos: pegar el código en el prompt,
  lanzar con `< /dev/null` **desde la carpeta del repo** y esperar `tokens used`; confirmar a los 20 s que abrió
  sesión); **graphify** (grafo del repo); **ponytail**
  (instalado, sin usar todavía). `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas; al volver, revisar `git log` antes de seguir.

## 5. Estado actual (2026-09-28)
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 16 pruebas OK.
  Probado en la placa sola (sin motores ni sensores).
- `firmware/base`: tracción diferencial, odometría, sensores, seguridad local; serial o micro-ROS. 19 pruebas OK.
  Probado en la placa sola (sin motores ni sensores).
- Capa micro-ROS: compila en las dos placas; cada sesión arranca **desarmada** (`armar` por `/<parte>/comando`).
  Las dos placas probadas con el agente, solas y a la vez (28/09): tasas nominales, armado y reconexión.
  S3: flashear con reset por watchdog (ya en `platformio.ini`); abrir el puerto con DTR/RTS bajos la deja en
  modo descarga. Usar `/dev/serial/by-id/` porque el puerto pasa de ACM0 a ACM1.
- `brazo_ik`: 5 pruebas OK, en la notebook y en la Pi.
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
- Detector de limones (28/09): entrenado en Colab con `vision/entrenamiento_limon/` (datasets de Roboflow, una
  clase `limon`). Test: P 0,953, R 0,977, mAP50 0,978, mAP50-95 0,814 (285 imágenes, 200 sin limón, 173
  limones; mismas fuentes que el entrenamiento: números optimistas). En la Pi:
  `~/vision_estereo/modelos/limon_yolo26n_ncnn_model` (fuera de git; 23 FPS solo). El `.pt` quedó en Drive
  (`arturito/limon_yolo`). **Sin probar con limones reales ni con las NoIR.** Uso:
  `MODELO=~/vision_estereo/modelos/limon_yolo26n_ncnn_model CLASE=limon ~/vision_estereo/scripts/start_limon.sh`
- Revisados por Codex (brazo, base, micro-ROS, cambios del 28/09 y visión) y hallazgos aplicados.
- `mision` (28/09): FSM mínima (ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR, FALLA manda `s`) + TF
  `brazo_base → stereo_camera_link` en `mision.launch.py` (argumentos obligatorios: MEDIR). Llegada por posición
  (`joint_states` contra `joint_cmd`). Revisada por Codex y aplicada; 17 pruebas OK; probada en la notebook con
  brazo y limón simulados. Sin probar con el brazo real. Falta el desfase muñeca → pinza (medir la pinza).

## 6. Decisiones
- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Configuración RRR (opción 6 de la tabla R1); pinza con agarre + tracción + giro en vez de succión (aprobado por
  el profesor, 28/09).
- Medidas del brazo vigentes: las de la E4; motor de J1 = 36GP-555 160 rpm (el DC 895 de 2700 rpm fue un error de compra).
- Un ESP32 por subsistema y lazos cerrados en los ESP32: la Pi solo manda consignas y cada placa se detiene sola.
- Control en cascada posición → velocidad, porque la E5 identificó modelos de velocidad.
- Seguridad de la base decidida en la S3 (seta NC, vuelco, bumpers, distancia, watchdog), sin depender de la Pi.
- Armado por sesión en micro-ROS, para que un nodo que siga publicando no mueva el robot al reconectar.
- TRIG común de HC-SR04, EN común de tracción y luz/buzzer en la Pi: la S3 no tiene más GPIO libres.
- Videos (~500 MB) y artículos de terceros fuera de git.

## 7. Próximos pasos
1. Verificar `cuentasPorVuelta` = 8316 de la tracción girando la rueda a mano (`vueltas` en `e`, README de la base).
2. Probar el detector con limones verdes reales frente a las NoIR (con luz, a 40-90 cm): si falla, esas fotos van
   al entrenamiento (fotos propias, subirlas a Roboflow y sumarlas en la celda 3 del cuaderno).
3. Soporte rígido de las cámaras, recalibrar y medir la precisión de `/limon/posicion` contra cinta.
4. Cablear según la lista "Antes de conectar" de `docs/CONEXIONES.md` (pull-down 10 kΩ en los EN, divisores de
   ECHO, pull-ups externos) y probar drivers y sensores (hoy nada probado con periféricos).
5. Primera prueba del brazo con motores (secuencia de su README; `v` sirve para la demo de la E6) y medir lo `MEDIR`.
6. Primera prueba de la base con ruedas en el aire (README): sentidos, radio, trocha y la parada real por watchdog.
7. Medir la TF cámara → brazo con el soporte rígido (argumentos de `mision.launch.py`) y probar `mision` con el
   brazo real: `cierre`, `reposo` y el desfase muñeca → pinza (hoy el centro del limón va a la muñeca).
8. Preguntas a la cátedra que quedan (`docs/ARQUITECTURA.md` §11: eje lineal de 1,2 m, GDL en R2, cajones).
