# Estado actual (al 2026-11-21 madrugada)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **27/11/2026** (demo; plan día por día en `PENDIENTES.md`).

## Avance
- **Recolección desde la app Arturito (20–21/11):** 1 limón a la canasta y vuelta al cero (0,9 cm / 4°, ~2 min); con
  2 limones, **1 de 2** (el bajo, a ~30 cm del piso, falló dos veces).
- Con scripts de `pruebas-esp32`: primera recolección completa el 13/11; `cosechar 3` dejó 2 de 3 (18/11). La misión
  ROS (`ros2_ws/src/mision`) tiene la navegación con el banderín, solo probada en Gazebo.
- Potencia v0.6 (`CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y el divisor 100 k / 30 k. LiPo 3S
  ~11,1 V (sin BMS, corte 10,5 V).
- Resumen ilustrado de las pruebas: `docs/resumen_pruebas_20261119.pdf`. **Manual v1.1** en `docs/manual/`
  (`manual.pdf` fuera de git, falta subirlo a Drive).

## App Arturito y puente (`app/`)
- **App** `app/android-app` **0.12.0** en la Xiaomi Pad 5. En Estado, dibujo del robot que ilumina cada sensor activo
  y 8 pitidos (ultrasonidos ≤ 20 cm, bumpers, IMU > 25° o `VUELCO`, seta; se pueden silenciar): sin probar con el robot.
- **Puente** `app/robot-bridge` (en la Pi `~/arturito-bridge-0.9.0`, `127.0.0.1:18006`). Tablet por USB a la notebook:
  `adb reverse tcp:18006 tcp:18006` y `ssh -N -L 127.0.0.1:18006:127.0.0.1:18006 r2d2@100.116.96.71`. En la Pi:
  `bash ~/arturito-bridge-0.9.0/arrancar_pi.sh` (agentes, visión v4 y puente; datos en `~/arturito-bridge-0.4.0/data`).
- **Misión:** Hacer homing → Calcular cero con el limón (pose de la base respecto del limón más cercano) → Iniciar
  recolección (1–5 limones) / Volver al cero. Cosecha con el limón a 50–55 cm de J1 y vuelve al cero por la odometría
  (detalle y registros: bitácora 20–21/11).
- `recolectar.py` (marca → parada → `cosechar`) usa el firmware **serie** del brazo: con la WROOM en micro-ROS no le habla.

## Demo y navegación (`pruebas-esp32/27-aruco-arbol`)
- **Demo: afuera, un banderín ArUco (ID 0) y una hilera de 2-3 arbolitos**, ida y vuelta (árbol a la izquierda); GPS
  (±20 m) solo para la rúbrica.
- `recolectar.py`: homing → marca → `ir_a_parada.py` → `cosechar --limones N` (enfoque anterior de 4 marcas, IDs 0–3
  pegadas). **Sin probar en el robot:** RODEAR y banderín único + BUSCAR; `banderin.json` sin medir.
- N3 de la guía: detención ✓ (18/11); seguimiento ≈ RODEAR (confirmar con la cátedra); evitación sin hacer.

## Base (`firmware/base`, S3)
- **En la S3: `base_ros_20261117_imu`** (env `ros`, `cc96d1f`): la IMU se recupera sola de un I2C colgado. Flasheo
  con `--after watchdog-reset`. Watchdog de 300 ms: `/cmd_vel` continuo.
- **Seguridad con motores probada (18/11):** frena el HC-SR04 del medio (para a 20 cm); bumpers, seta y vuelco (25°)
  frenan. **Desde el 21/11 (sin flashear todavía) seta y vuelco no enclavan ni hay `r`:** desarman la base y hace falta `armar`.
- Odometría: recto < 1 %; giros con el giróscopo (~±1°); al volver al cero queda ~4° de rumbo.
- A vigilar: cortes del USB de la S3 (se reconecta desarmada). Si no conecta tras reiniciar la Pi: `pkill -f
  micro_ros_agent`, `esptool ... --after watchdog-reset chip-id`, agente. `BATERIA_BAJA` no indica si hay 12 V.

## Brazo (WROOM)
- **En la WROOM (20/11): `pruebas-esp32/20-brazo-coordinado` env `ros` (micro-ROS), fuente `750ba4c`**
  (`~/arturito-build/20261120/firmware.bin`). El serie (para `recolectar.py`, `punta.py` sesión, `joystick.py`):
  `~/firmware/brazo20_serie_20261119.bin`. **No flashear `firmware/brazo`** (`d3644c8`, viejo).
- Agente: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`; si no
  se conecta, pulso en EN por software (RTS) **con los 12 V apagados**.
- Pose plegada: J1 hasta 130 solo con J2 42–51 y J3 ≥ 78; J3 cerca de 80 está dura ("sin cuentas").
  Pinza **RDS3218**: abierta 500 µs, cerrada 1200. Muñeca GPIO 14.
- `punta.py cosechar N`: alcance limón a ~48–65 cm de J1 y 33–54 cm del piso; `z = 23,1 + 0,718·z_visión`.
- El 20 entiende texto por `/brazo/comando`, no `/brazo/joint_cmd` de `brazo_ik`. Detalle: `pruebas-esp32/notas/ESTADO.md`.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 55; `simulacion` 17. `largo_herramienta` = 0 (MEDIR).
- Navegación con el banderín (`mision/navegacion.py`, `nodo_mision navegacion:=true`): solo en Gazebo; en el real falta
  la TF de la cámara de navegación y medir `mision/config/hilera_arboles.json`.
- FSM ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR. Sin nodo de seguridad separado (S2) ni estados de S3.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector **v4** (NCNN fijo a 640; volver al v3: la línea comentada, `IMGSZ=480`).
  ~2,5–4 img/s, disparidad ~1,5 Hz. No arranca sola. Limones entre 0,40 y 0,95 m; a veces mide el follaje delante.
- Si tras reiniciar una vista queda sin imagen: borrar a mano el segmento de Fast DDS en `/dev/shm/fastrtps_port*`.
- Mástil: cámaras mirando a la izquierda, ~58 cm del piso, baseline 100,3 mm. Una sola cámara en
  `rpicam-hello --list-cameras`: revisar la cinta. Madurez: sin implementar.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, 9600, `nmea_navsat_driver ... -r fix:=/gps/fix`): σ ≈ 21 m afuera; adentro sin fix.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Wi-Fi por prioridad: **iPhone de Mathias** (hotspot, 20; desde
  20/11, IP 172.20.10.2, directo ~21 ms) > **LabEquiposMedicos** (10, ~6 ms) > el resto (0). `nmcli` pide `sudo`.
  FastAPI 0.101 con apt. Después de reiniciar: `arrancar_pi.sh` (app) o `~/scripts/agente_base.sh` y `~/scripts/vision.sh`.
- **Fuente oficial de 27 W** (`get_throttled` → `0x0`); con el power bank se reinicia. Carga alta (load 7–9).
- Rutas: binarios en `~/firmware/`, scripts en `~/scripts`, logs en `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`): 12 de 12 limones. `mundo:=arbolitos mision:=true`
  (banderín + 3 árboles): 15 de 18 paradas en ±5 cm y ±3° (resultados en la bitácora del 19/11).
