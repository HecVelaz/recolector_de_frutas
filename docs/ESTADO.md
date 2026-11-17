# Estado actual (al 2026-11-17; el robot, al 13/11)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **27/11/2026** (demo; plan día por día en `PENDIENTES.md`).

## Avance
- **Primera recolección autónoma completa en el robot real (13/11, 95 s)**, con scripts de `pruebas-esp32`; la
  misión ROS (`ros2_ws/src/mision`) todavía no la tiene.
- Potencia v0.6 (`CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y el divisor 100 k / 30 k.
  Pi con el power bank: OK (prueba real de 1 h, 12/11).

## Demo y navegación (13/11, en `~/Documentos/pruebas-esp32`)
- **Demo:** un solo arbolito en el aula (el profesor lo acepta), con marcas ArUco; el GPS (±20 m) solo para la rúbrica.
- `27-aruco-arbol/tools/recolectar.py`: homing → reposo → marca → `ir_a_parada.py` (gira con el giróscopo, avanza
  con las ruedas, gira) → mide el limón 5 s → `agarrar`. Tiene que arrancar viendo la marca (~0,9–4 m, a la izquierda).
- Marcas DICT_4X4_50 de 15 cm; ID 0 en la maceta (cara a 16,5 cm del tronco); **faltan las IDs 1–3** (antihorario).
  En la parada la marca queda cortada: ahí mandan los limones.
- **Parada:** tronco a 70 cm a la izquierda de J1 y 15 cm adelante; 4 paradas cada 90° = 100 % del arbolito medido
  (`26-sim-alcance-arbolito`). Validada agarrando.
- Cámara: calibración de agarre (12/11, < 70 cm) y de navegación (`27/resultados/tf_navegacion.json`, ~3 cm a 1–2 m).
- **N3 de la guía (análisis del 17/11):** con BUSCAR + esquive, RODEAR y la seguridad andando (PENDIENTES 00a) se
  cubre; `recorrido.py` (hilera + YOLO, 12/12 en Gazebo) sigue sin probar en el robot y pasó a segundo plano.

## Base (`firmware/base`, S3)
- **En ROS con los 12 V (13/11):** env `ros` (flasheo con `--after watchdog-reset`: arranca sola); IMU (calibra el
  giróscopo sola al arrancar), 3 HC-SR04, 3 bumpers y seta OK. Watchdog de 300 ms: `/cmd_vel` continuo.
- **Odometría en el piso:** recto < 1 % con las ruedas; giros con el giróscopo (~±1°; las ruedas se pasan ~2°/90°).
  `pruebas-esp32/25-teleop-pi/tools/movimiento.py` (frenado proporcional) y `prueba_odom.py`.
- Sin probar con los motores andando: frenado por HC-SR04 (< 20 cm), bumper y vuelco. Enlace USB de la S3 con cortes
  (uno durante un giro el 13/11; la base se desarma al reconectar). Rueda derecha: patinaba en el eje (¿arreglada?).
- `BATERIA_BAJA` no indica si hay 12 V. Si la S3 queda en modo descarga: `esptool --before no_reset --after
  watchdog_reset read_mac` desde la Pi.

## Brazo (WROOM)
- **En la WROOM está `pruebas-esp32/20-brazo-coordinado` env `brazo` (serie)**; el env `ros` en
  `~/firmware/respaldo_wroom_20261112.bin`. **No flashear `firmware/brazo`** (`d3644c8`, viejo: falta pasarle lo de 20).
- `punta.py agarrar` (visión → brazo, pinza 1300 µs) funciona. El 20 entiende texto por `/brazo/comando`, no
  `/brazo/joint_cmd` de `brazo_ik`.
- Detalle del brazo (homing, límites, cinemática): `pruebas-esp32/notas/ESTADO.md`.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 35; `simulacion` 13. `largo_herramienta` = 0 (MEDIR).
- `mision`: FSM ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR y TF `brazo_base → stereo_camera_link` (medida el
  12/11). `autonomo:=true` (hilera) y `hilera_gps.py` (fix falso): solo simulados.
- No hay nodo de seguridad separado (S2) ni estados con los nombres de S3 de la guía.

## Visión (repo `HecVelaz/vision_estereo`)
- `~/scripts/vision.sh` = `start_limon.sh` con el v3 (`/limon/posicion` en el marco óptico rectificado izquierdo).
  No arranca sola. Ubica limones entre 0,40 y 0,95 m (u ≥ 280 px: el brazo tapa el resto).
- Mástil: cámaras mirando a la izquierda, ~58 cm del piso, baseline 100,3 mm (`calibracion_mastil`, RMS 0,22 px).
- Detector de una clase `limon`: v1, v2 (verdes) y **v3** (amarillos, en uso). v3 sin comparar con la v2 en cifras.
- Madurez por tamaño con el estéreo: sin implementar.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, 9600, `nmea_navsat_driver ... -r fix:=/gps/fix`): σ ≈ 21 m afuera; adentro sin fix.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`); Wi-Fi FIUNA aísla clientes (celular solo por Tailscale).
  `.commit` `4badf7a` (12/11). Después de reiniciar, a mano: `~/scripts/agente_base.sh` y `~/scripts/vision.sh`.
- Rutas: binarios en `~/firmware/`, scripts en `~/scripts`, logs en `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`): 12 de 12 limones con la hilera; no tiene el arbolito con marcas.
