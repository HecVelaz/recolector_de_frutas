# CLAUDE.md — recolector_de_frutas

**Hablar siempre en castellano** (rioplatense, como el usuario): respuestas, avisos intermedios y explicaciones,
también en sesiones largas o mientras se depura. Nunca pasar al inglés. Detalle histórico en `docs/BITACORA.md`.

## 1. Proyecto
Robot móvil autónomo recolector de limones "Arturito R2D2" (Grupo 2, FIUNA Mecatrónica, 2026S2). Cubre dos
materias: **Robótica I** evalúa el brazo; **Robótica II**, el robot móvil con ROS 2. Objetivo mínimo para aprobar:
**el robot se mueve, detecta el limón con YOLO, lo localiza con estéreo y lo agarra** (`docs/ARQUITECTURA.md`).

## 2. Hardware y arquitectura
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión, IK, misión. Habla por USB (micro-ROS) con dos ESP32.
- **ESP32-S3** (base): 2 motores de tracción + IBT-2, encoders, IMU MPU-6500, GPS UP501, 3 HC-SR04, 4 bumpers,
  seta, batería. **ESP32-WROOM-32D** (brazo): J1 36GP-555 + IBT-2, J2/J3 5840-31ZY (sin fin) + L298N, 2 servos.
- Brazo RRR con cuatro barras (medidas de la E4) + giro de pinza J4. Pines y alimentación: `docs/CONEXIONES.md`.

## 3. Estructura
- `docs/`: consignas, entregas R1/R2, `INDICE.md`, `ARQUITECTURA.md`, `CONEXIONES.md`, inventario, bitácora.
- `firmware/lib/`: drivers y lógica compartidos (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, L298N,
  EncoderPCNT, HCSR04, MPU9250, UP501). `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/brazo_ik/`: nodo de cinemática inversa. `vision/entrenamiento_limon/`: cuaderno de Colab del detector. `graphify-out/`: grafo del repo (local, fuera de git).

## 4. Cómo trabajar acá
- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF ni `.ipynb`** (bloqueados en
  `.claude/settings.json`): usar sus `.txt`/`.md`.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor en solo lectura; en esta PC su sandbox no lee archivos: pegar el código en el prompt,
  lanzar con `< /dev/null` y esperar `tokens used` en la salida); **graphify** (grafo del repo); **ponytail**
  (instalado, sin usar todavía). `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas; al volver, revisar `git log` antes de seguir.

## 5. Estado actual (2026-09-28)
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 15 pruebas OK.
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
  Al reiniciar el agente o flashear el brazo, la base se reconectó una vez (vuelve DESARMADA): vigilar.
- Visión: repo aparte `HecVelaz/vision_estereo` (en la Pi, `~/vision_estereo`): calibración estéreo v2 (RMS
  0,32 px, baseline 99,3 mm), disparidad y nube `/points2`, nodo `yolo_ros` con `yolo26n.pt` (COCO: sin clase
  limón; ~5 FPS en CPU). Detector propio: `vision/entrenamiento_limon/` (sin correr; faltan fotos NoIR propias).
  Cadena visión → punto 3D (28/09, commit local `114f0f7` en la Pi, sin push): `detector_node` publica
  `/yolo/detecciones`, `localizador_node` publica `/limon/posicion`; `scripts/start_limon.sh` arranca todo.
  Con `launch/limon.launch.py` (commit `986182c`, sin push): NCNN + OpenMP pasivo + sin `/points2` + disparidad
  BM en 72-168 px (~0,40-0,94 m; la ventana 0-128 original no mide a menos de ~0,53 m) -> detección ~9 FPS,
  posición ~3 Hz. Calidad de BM y precisión sin medir: cámaras en soporte de cartón; recalibrar con el soporte
  rígido (el usuario avisa) y apuntar `limon.launch.py` a la calibración nueva (hoy usa la v1).
- Revisados por Codex (brazo, base, micro-ROS) y hallazgos aplicados. Misión: sin empezar.

## 6. Decisiones
- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Configuración RRR (opción 6 de la tabla R1); pinza con tracción + giro en vez de succión.
- Medidas del brazo vigentes: las de la E4; motor de J1 = 36GP-555 160 rpm (el DC 895 de 2700 rpm fue un error de compra).
- Un ESP32 por subsistema y lazos cerrados en los ESP32: la Pi solo manda consignas y cada placa se detiene sola.
- Control en cascada posición → velocidad, porque la E5 identificó modelos de velocidad.
- Seguridad de la base decidida en la S3 (seta NC, vuelco, bumpers, distancia, watchdog), sin depender de la Pi.
- Armado por sesión en micro-ROS, para que un nodo que siga publicando no mueva el robot al reconectar.
- TRIG común de HC-SR04, EN común de tracción y luz/buzzer en la Pi: la S3 no tiene más GPIO libres.
- Videos (~500 MB) y artículos de terceros fuera de git.

## 7. Próximos pasos
1. Confirmar el motor de tracción: notas = 36GP-555 53 rpm, inventario = DC 895 planetario 53 rpm.
2. Cablear según la lista "Antes de conectar" de `docs/CONEXIONES.md` (pull-down 10 kΩ en los EN, divisores de
   ECHO, pull-ups externos).
3. Primera prueba del brazo en placa (secuencia de su README; `v` sirve para la demo de la E6) y medir lo `MEDIR`.
4. Primera prueba de la base con ruedas en el aire (README) y medir sentidos, radio y trocha.
5. Probar micro-ROS con los agentes (`/dev/ttyACM0` base, `/dev/ttyUSB0` brazo) y medir con `ros2 topic hz`.
6. Probar las cámaras NoIR con YOLO y limones reales (riesgo de color); soporte rígido y calibración estéreo.
7. Nodos de visión y `mision_fsm` mínima para la demo del objetivo mínimo.
8. Preguntas a la cátedra (`docs/ARQUITECTURA.md` §11) y arreglar el salto de 32 000 cuentas de `EncoderPCNT`.
