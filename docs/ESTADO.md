# Estado actual (al 2026-11-19; el robot, al 18/11)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **27/11/2026** (demo; plan día por día en `PENDIENTES.md`).

## Avance
- **Recolección autónoma con scripts de `pruebas-esp32`:** primera completa el 13/11 (95 s); el 18/11 `cosechar 3`
  dejó 2 limones en la canasta (~34 s cada uno). Base + cosecha juntas todavía no se probaron. La misión ROS
  (`ros2_ws/src/mision`) todavía no tiene este enfoque.
- Potencia v0.6 (`CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y el divisor 100 k / 30 k.
  Pi con el power bank: OK.
- Resumen ilustrado de todas las pruebas: `docs/resumen_pruebas_20261119.pdf`.
- **Manual v1.1 (19/11)** al día en `docs/manual/` (capítulo nuevo de la demo); `manual.pdf` fuera de git, falta subirlo a Drive.

## Demo y navegación (en `~/Documentos/pruebas-esp32`, carpeta `27-aruco-arbol`)
- **Demo:** un solo arbolito en el aula con marcas ArUco; GPS (±20 m) solo para la rúbrica. Espacio: ≥ 4 × 4 m.
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
- Odometría: recto < 1 % con las ruedas; giros con el giróscopo (~±1°).
- A vigilar: cortes del USB de la S3 (3 el 18/11; se reconecta pero queda desarmada); un `atasco` aislado del encoder
  izquierdo. Si la S3 no conecta tras reiniciar la Pi: `pkill -f micro_ros_agent`, `esptool ... --after
  watchdog-reset chip-id`, agente. `BATERIA_BAJA` no indica si hay 12 V.

## Brazo (WROOM)
- **En la WROOM: `pruebas-esp32/20-brazo-coordinado` env `brazo` (`brazo20_serie_20261118h.bin`, serie)**; el env
  `ros` (teleop) en `~/firmware/respaldo_wroom_20261112.bin`. **No flashear `firmware/brazo`** (`d3644c8`, viejo).
- Pinza **RDS3218**: abierta 500 µs, cerrada 1200. Muñeca GPIO 14.
- `punta.py cosechar N`: mide, entra, desprende, va a la canasta (pose plegada, J1 130), confirma y reintenta.
  Alcance: limón a ~48–65 cm de J1 y 33–54 cm del piso. Altura de la visión `z = 23,1 + 0,718·z_visión`.
- El 20 entiende texto por `/brazo/comando`, no `/brazo/joint_cmd` de `brazo_ik`.
- Detalle del brazo: `pruebas-esp32/notas/ESTADO.md`.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 35; `simulacion` 13. `largo_herramienta` = 0 (MEDIR).
- `mision`: FSM ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR y TF `brazo_base → stereo_camera_link` (12/11).
  `autonomo:=true` (hilera) y `hilera_gps.py` (fix falso): solo simulados.
- No hay nodo de seguridad separado (S2) ni estados con los nombres de S3 de la guía.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh` (v3, `/limon/posicion` en el marco óptico rectificado izquierdo). No arranca sola.
  Ubica limones entre 0,40 y 0,95 m (u ≥ 280 px: el brazo tapa el resto).
- Mástil: cámaras mirando a la izquierda, ~58 cm del piso, baseline 100,3 mm (`calibracion_mastil`, RMS 0,22 px).
  Si `rpicam-hello --list-cameras` muestra una sola: revisar la cinta.
- Detector de una clase `limon`: v3 (amarillos, en uso), sin comparar con la v2 en cifras. Madurez: sin implementar.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, 9600, `nmea_navsat_driver ... -r fix:=/gps/fix`): σ ≈ 21 m afuera; adentro sin fix.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). En el lab elige **LabEquiposMedicos** (prioridad 10, directo ~6 ms);
  afuera, el hotspot del celular (5 GHz). FastAPI 0.101 instalado con apt (prueba `~/web_estado.py`, fuera del repo).
  `.commit` `4badf7a` (12/11). Después de reiniciar, a mano: `~/scripts/agente_base.sh` y `~/scripts/vision.sh`.
- Rutas: binarios en `~/firmware/`, scripts en `~/scripts`, logs en `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`): 12 de 12 limones con la hilera; no tiene el arbolito con marcas.
