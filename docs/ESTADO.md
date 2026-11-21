# Estado actual (al 2026-11-21 madrugada)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **27/11/2026** (demo; plan día por día en `PENDIENTES.md`).

## Avance
- **Recolección desde la app Arturito (20–21/11):** 1 limón a la canasta y vuelta al cero (0,9 cm / 4°, ~2 min); con
  2 limones, **1 de 2** (el bajo, a ~30 cm del piso, falló dos veces). Detalle abajo.
- **Recolección autónoma con scripts de `pruebas-esp32`:** primera completa el 13/11 (95 s); el 18/11 `cosechar 3`
  dejó 2 limones en la canasta (~34 s cada uno). Base + cosecha juntas todavía no se probaron. La misión ROS
  (`ros2_ws/src/mision`) ya tiene la navegación con el banderín (`navegacion.py`), solo probada en Gazebo.
- Potencia v0.6 (`CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y el divisor 100 k / 30 k.
  **Pi con la fuente oficial de 27 W:** con el power bank y la carga de la app se reiniciaba por bajo voltaje (21/11);
  afuera hace falta uno que dé 5 V / 5 A.
- LiPo 3S ~11,1 V (sin BMS, corte 10,5 V).

## App Arturito y puente (`app/`, desde el 20/11)
- **App** `app/android-app` 0.12.0 en la Xiaomi Pad 5 (instalada el 21/11, alertas sin probar con el robot: en Estado, dibujo del robot
  que ilumina cada sensor activo y 8 pitidos con SoundPool, `model/SensorAlerts.kt`; ultrasonidos a ≤ 20 cm, IMU > 25°
  o `VUELCO`; suenan en cualquier pestaña mientras haya conexión, se pueden silenciar) + **puente** `app/robot-bridge` (en la Pi `~/arturito-bridge-0.9.0`,
  `127.0.0.1:18006`; 92 pruebas). Tablet por USB a la notebook: `adb reverse tcp:18006 tcp:18006` y túnel
  `ssh -N -L 127.0.0.1:18006:127.0.0.1:18006 r2d2@100.116.96.71`. En la Pi: `bash ~/arturito-bridge-0.9.0/arrancar_pi.sh`
  (agentes, visión v4 y puente; datos y clave en `~/arturito-bridge-0.4.0/data`).
- Flujo en **Misión**: **Hacer homing** (un botón; si el firmware lo rechaza por la franja, `j 2 6` y reintenta) →
  **Calcular cero con el limón** (pose de la base respecto del limón más cercano, 3 s de estéreo) → **Iniciar
  recolección** (1–5 limones) / **Volver al cero**.
- Misión (`collection_mission.py`): limón a **50–55 cm de J1** (si ya está y tiene plan no se mueve; si no, se acerca en
  su dirección hasta 53,5 cm, nunca retrocede); en la parada solo vale el limón a < 12 cm de donde se esperaba;
  agarre de `punta.py` (+2 cm, `GRASP_RAISE_MM`) y canasta; el siguiente limón se mide desde ahí; al final (o tras un
  fallo) brazo al reposo y base al cero por la odometría (girar, retroceder recto a ≤ 6 cm/s, girar). Usa
  `~/scripts/27-aruco-arbol/tools` y `~/scripts/20-brazo-coordinado/tools` de la Pi (planificadores en otro proceso).
- Registros: `~/arturito-bridge-0.4.0/data/missions/` (eventos + rosbag); pedidos con tiempos en
  `~/arturito-bridge-0.9.0/bridge.log`. Reiniciar el puente borra el cero (se puede pasar con `ARTURITO_RESTORE_ORIGIN_JSON`).
- `recolectar.py` (marca → parada → `cosechar`, abajo) usa el firmware **serie** del brazo: con la WROOM en micro-ROS no le habla.
- Resumen ilustrado de todas las pruebas: `docs/resumen_pruebas_20261119.pdf`.
- **Manual v1.1 (19/11)** al día en `docs/manual/` (capítulo nuevo de la demo); `manual.pdf` fuera de git, falta subirlo a Drive.

## Demo y navegación (en `~/Documentos/pruebas-esp32`, carpeta `27-aruco-arbol`)
- **Demo (19/11): afuera, un banderín ArUco (ID 0) y una hilera de 2-3 arbolitos**, ida y vuelta (árbol siempre a la
  izquierda); GPS (±20 m) solo para la rúbrica. Lo de abajo (`pruebas-esp32`) es el enfoque anterior de 4 marcas.
- `recolectar.py`: homing → reposo → marca → `ir_a_parada.py` (gira con el giróscopo, avanza con las ruedas) →
  `cosechar --limones N`. Tiene que arrancar viendo la marca (~0,9–4 m, a la izquierda).
- Marcas DICT_4X4_50 de 15 cm, **IDs 0–3 pegadas** (antihorario, cara a 16,5 cm del tronco).
- **Sin probar en el robot:** RODEAR (`--rodear N`, `recolectar.py --paradas N`) y **banderín único + BUSCAR**
  (`--banderin --buscar`, gira de a 30° hasta ver la marca); `banderin.json` sin medir y `recolectar.py` no lo usa.
- **Parada:** tronco a 70 cm a la izquierda de J1 y 15 cm adelante; 4 paradas cada 90° = 100 % del arbolito.
- Cámara: calibración de agarre (12/11, < 70 cm) y de navegación (`27/resultados/tf_navegacion.json`, ~3 cm a 1–2 m).
- N3 de la guía: detención ✓ (18/11); seguimiento ≈ RODEAR (confirmar con la cátedra); evitación sin hacer.

## Base (`firmware/base`, S3)
- **En la S3: `base_ros_20261117_imu`** (env `ros`, `cc96d1f`): IMU que se recupera sola de un I2C colgado (`imu_rec`
  en `/base/estado`). Flasheo con `--after watchdog-reset`. Watchdog de 300 ms: `/cmd_vel` continuo.
- **Seguridad con motores probada (18/11):** frena solo el HC-SR04 del medio (para a 20 cm a 0,10 y 0,20 m/s);
  bumpers, seta y vuelco (25°) enclavan; `r` por `/base/comando` rearma.
- Odometría: recto < 1 % con las ruedas; giros con el giróscopo (~±1°); al volver al cero queda ~4° de rumbo.
- A vigilar: cortes del USB de la S3 (3 el 18/11; se reconecta pero queda desarmada); un `atasco` aislado del encoder
  izquierdo. Si la S3 no conecta tras reiniciar la Pi: `pkill -f micro_ros_agent`, `esptool ... --after
  watchdog-reset chip-id`, agente. `BATERIA_BAJA` no indica si hay 12 V.

## Brazo (WROOM)
- **En la WROOM (20/11): `pruebas-esp32/20-brazo-coordinado` env `ros` (micro-ROS) de la fuente `750ba4c`**
  (`~/arturito-build/20261120/firmware.bin`, `62695d4a…`; la usan la app y el teleop). El serie (para `recolectar.py`,
  `punta.py` sesión, `joystick.py`): `~/firmware/brazo20_serie_20261119.bin`. **No flashear `firmware/brazo`** (`d3644c8`, viejo).
- Agente: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`; si no
  se conecta, pulso en EN por software (RTS, DTR suelto) **con los 12 V apagados**. Respuestas por `/brazo/respuesta`.
- Pose plegada: J1 hasta 130 solo con J2 42–51 y J3 ≥ 78; J3 cerca de 80 está dura ("sin cuentas").
- Pinza **RDS3218**: abierta 500 µs, cerrada 1200. Muñeca GPIO 14.
- `punta.py cosechar N`: mide, entra, desprende, va a la canasta (pose plegada, J1 130), confirma y reintenta.
  Alcance: limón a ~48–65 cm de J1 y 33–54 cm del piso. Altura de la visión `z = 23,1 + 0,718·z_visión`.
- El 20 entiende texto por `/brazo/comando`, no `/brazo/joint_cmd` de `brazo_ik`.
- Detalle del brazo: `pruebas-esp32/notas/ESTADO.md`.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 55; `simulacion` 17. `largo_herramienta` = 0 (MEDIR).
- **Navegación con el banderín** (`mision/navegacion.py`, `nodo_banderin`, `nodo_mision navegacion:=true`, hilera en
  `mision/config/hilera_arboles.json` sin medir): solo en Gazebo. En el real falta la TF de la cámara de navegación
  (hoy la del urdf) y medir la hilera.
- `mision`: FSM ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR y TF `brazo_base → stereo_camera_link` (12/11).
  `autonomo:=true` (hilera) y `hilera_gps.py` (fix falso): solo simulados.
- No hay nodo de seguridad separado (S2) ni estados con los nombres de S3 de la guía.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh` (**v4** desde el 20/11, `limon_yolo26n_v4_ncnn_model`, NCNN fijo a 640, `IMGSZ=640`;
  volver al v3: la línea comentada, `IMGSZ=480`). `/limon/posicion` en el marco óptico rectificado izquierdo. No arranca sola.
  Ubica limones entre 0,40 y 0,95 m (u ≥ 280 px: el brazo tapa el resto); a veces mide el follaje delante del limón.
- v4: sin el falso limón sobre el panel de metal; ~2,5–4 img/s, `/limon/todos` ~1,8/s, disparidad ~1,5 Hz.
- Si tras reiniciar la visión una vista queda sin imagen: segmento de Fast DDS corrupto en `/dev/shm/fastrtps_port*`
  (borrarlo a mano; `fastdds shm clean` no lo ve).
- Mástil: cámaras mirando a la izquierda, ~58 cm del piso, baseline 100,3 mm (`calibracion_mastil`, RMS 0,22 px).
  Si `rpicam-hello --list-cameras` muestra una sola: revisar la cinta.
- Detector de una clase `limon`: v4 en uso (v3 0,61–0,66 en el metal, v4 nada; limón real 0,86–0,97 contra 0,77).
  Madurez: sin implementar.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, 9600, `nmea_navsat_driver ... -r fix:=/gps/fix`): σ ≈ 21 m afuera; adentro sin fix.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Wi-Fi por prioridad: **iPhone de Mathias** (hotspot, 20; desde
  20/11, IP 172.20.10.2, directo ~21 ms) > **LabEquiposMedicos** (10, ~6 ms) > el resto (0). `nmcli` pide `sudo`. FastAPI 0.101 instalado con apt (prueba `~/web_estado.py`, fuera del repo).
  `.commit` `4badf7a` (12/11). Después de reiniciar, a mano: `~/scripts/agente_base.sh` y `~/scripts/vision.sh`.
- **Fuente oficial de 27 W** (`vcgencmd get_throttled` → `0x0`). Con la app: `arrancar_pi.sh` (arriba). Carga alta
  (load 7–9: detector ~100 %, disparidad ~90 %, puente ~50 %).
- Rutas: binarios en `~/firmware/`, scripts en `~/scripts`, logs en `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`): 12 de 12 limones con la hilera de la guía.
- **`mundo:=arbolitos mision:=true`** (banderín + 3 árboles, ida y vuelta, cámara del mástil `camara:=nav`, reposo
  J1 = 0°): 3 poses → 15 de 18 paradas en ±5 cm y ±3° (las 3 que no, +5,5 cm: el detector mide el banderín ~2 % más
  lejos desde 2,8 m), 15-17 limones de 24, cierre 3-5 cm. CSV en `ros2_ws/src/simulacion/resultados/`. RTF ~0,43.
