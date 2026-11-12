# Estado actual (al 2026-11-12; del robot, solo la alimentación de la Pi desde el 28/10)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **9/11/2026** (ya pasó: confirmar).

## Avance
- Software ~70 %, hardware real atrasado. Plan (atrasado): 20-26/10 hilera real, app, TF; 27/10-2/11 J2/J3 y `mision` real;
  3-9/11 integración, 30 frutos, informes.
- Potencia v0.6 (cadena en `CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y armar el divisor 100 k / 30 k.
- **Alimentación de la Pi:** el power bank cargado (4 LED) aguantó 10 min simulados (4 núcleos, 5,01 V, `0x0`; 10/11). Falta
  la prueba real (`registrar_tension.sh`, listo en la Pi) y 1 h seguida. Buck 2 por USB-C: no sirve (cable fino).

## Base (`firmware/base`, S3) — 20 pruebas OK
- **Ruedas en el aire (20-22/10; a fondo el 28/10, 30-40 rpm, sin atascos):** sentidos de motores y encoders correctos; K 0,6 rpm/%, zona muerta 11 %,
  τ 80 ms, PI 0,89/11,1 (`w 8 8` → 8 ± 0,1 rpm); 8316 cuentas por vuelta. Manejada desde el celular con
  `teleop_web.py` (`http://100.116.96.71:8000`, Tailscale; base y brazo; muestra la latencia: 38 ms directo, 26/10) y con `teleop_twist_keyboard`.
- En la S3 está el env de prueba **`ros_motores`** (sin IMU ni distancia al frente): nunca en el piso.
- Con `u` a velocidad máxima, > 4 A (2,6 A en vacío por motor). La rueda derecha patina en el eje (prisionero).
- La S3 queda a veces en modo descarga (al reconectar el USB o con un reset por RTS): `esptool --before no_reset
  --after watchdog_reset read_mac` desde la Pi. `BATERIA_BAJA` no indica si hay 12 V: preguntar.
- Enlace de la base: `pings_fallidos` 82 y `cortes=4` en ~1 h (el brazo, 0). Sin investigar.
- Sin probar: IMU, HC-SR04, bumpers y seta en ROS; odometría en el piso; parada real por el watchdog de 300 ms.

## Brazo (`firmware/brazo`, WROOM) — 18 pruebas OK
- **En la WROOM está `pruebas-esp32/20-brazo-coordinado` env `ros` (11/11)**, no este firmware: no flashear `d3644c8` (viejo).
  Este firmware: cascada J1-J3 + pinza, pines v0.5; falta pasarle lo de 20. Topes (jog y `dutyMax`): 50 % en las tres.
- El encoder de J2 no contaba (atasco a los 0,3 s); tras revisarlo el usuario el joystick funcionó, sin confirmar con `e`.
- Finales de carrera (GPIO 32/33/27, `home <n>`): previstos en el firmware, sin montar; falta medir `HOME_Q`.
- J1 con los parámetros de `pruebas-esp32/10` (sin probar en este firmware). J2/J3: motores 36-555 58 rpm 139:1 +
  doble helicoidales 15 → 75 (10/11); tienen los parámetros de J1 llevados a 58 rpm y signos sin medir.
- `m`/`j` rechazan γ₄ = q2 + q3 − 90° fuera de −111,9…−30°; `home 2/3` bloqueados hasta medir `HOME_Q`
  (hoy da −165°: no cierra con el balancín de 60 mm). `POSE_CERO` provisoria (90°, 90°, −40°).
- Rango de J1: 45°/225° en el marco de `brazo_ik` (pasa por atrás, nunca cruza el mástil). Reposo provisorio
  q = 75°/94°/−50°. Límites provisorios: q2 −25…135°, q3 ±50°.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 35; `simulacion` 13. `/brazo/objetivo` es el TCP; `largo_herramienta` = 0 (MEDIR).
- `mision`: FSM ESPERAR → APROXIMAR → AGARRAR → RETIRAR → SOLTAR (FALLA manda `s`; la seta desarma el brazo) y TF
  `brazo_base → stereo_camera_link` (argumentos obligatorios: MEDIR). Probada con brazo y limón simulados.
- Recorrido autónomo (`autonomo:=true`): 12 de 12 limones en Gazebo sin teleop. Sin probar en el robot real.
- Hilera por GPS (N1, `hilera_gps.py`): no arma la base hasta estar a < 10 m del inicio con σ ≤ 20 m. Probado con un
  fix falso. Falta: probar con el UP501 afuera y el regreso al inicio al terminar la hilera.
- micro-ROS: las dos placas abren sesión con sus agentes, a la vez, con tasas nominales; arrancan desarmadas.

## Visión (repo `HecVelaz/vision_estereo`)
- `scripts/start_limon.sh`: cámaras + rectificación + SGBM (~2,5 Hz) + `detector_node` + `localizador_node`
  (`/limon/posicion` en el marco óptico RECTIFICADO de la cámara izquierda).
- Calibración `config/calibracion_soporte_2/`: RMS 0,36 px, baseline 89,5 mm, ventana 0,38-0,96 m. Zona ciega:
  u < ~163 px de la imagen izquierda.
- Limón real en el lab: confianza mediana 0,80; error 3D máx. 17 mm (B5 pide ≤ 35 mm). Falta el campo y las NoIR al sol.
- **Cámaras montadas cabeza abajo** (28/10): `orientacion: 180` en `config/camaras.yaml` (`940548d`, sin push).
  **Calibración inválida** (~25 px de desnivel vertical): recalibrar antes de usar Z.
- Detector de una sola clase `limon`. En la Pi están la **v1** (28/09, `limon_yolo26n_ncnn_model`) y la **v2**
  (`limon_yolo26n_v2_ncnn_model`, en uso desde el 28/10; sin el enlace de la sección 12 del cuaderno).
- **v2 (28/10, solo limones verdes**; `vision/entrenamiento_limon/`): P 0,894, R 0,832, mAP50 0,919 en test de las
  mismas fuentes. Con las NoIR (lab, 3 limones, 20 cuadros): empate con la v1, mediana 0,79 contra 0,78.
- **v3** (Tarea VA, amarillos, celular; reentrenada el 12/11): en la Pi como `limon_yolo26n_v3_ncnn_model`, 68 ms a 480;
  detecta el limón con las NoIR (a ojo). Sin comparar con la v2 en cifras. Visor: `web_video_server` en el 8080.
- Madurez (B3 cosechable / no cosechable) por **tamaño** con el estéreo (ancho_px · Z / f ≥ `D_min`, MEDIR): sin
  implementar. No hay clases de color: las NoIR lo corren.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, `nmea_navsat_driver` → `/gps/fix`). Primer fix a cielo abierto (21/10): ~5 min,
  3 satélites, σ ≈ 21 m. Bajo techo no ve ninguno. Con la Pi apagada pierde los satélites (arranque en frío).

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`); en el lab, Wi-Fi FIUNA 172.16.240.92 (aísla clientes: el celular
  entra solo por Tailscale). `.commit`: `4badf7a` (12/11); `brazo_ik` y `mision` recompilados. Agentes y `teleop_web.py` se lanzan a mano en segundo
  plano (no arrancan solos); al reconectar los USB o reiniciar, relanzar los agentes y despertar la S3 con esptool.
- Rutas: agente en `~/microros_ws`, binarios en `~/firmware/<base|brazo|hola>`, scripts en `~/scripts`, logs en
  `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/` (las rutas viejas siguen como symlinks).
- Cámaras: las dos a 30 FPS con la cinta CSI nueva (`~/scripts/probar_camaras.sh`; vista cruda en el 8080).

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`, `vision:=yolo`, `gui:=false`): 12 de 12 limones.
  `vision:=yolo` parcial (YOLO no reconoce los limones sintéticos). Falta pasarla a la PC de escritorio.
- Sin probar en Gazebo: limones a menos de 45° (adelante-izquierda) ya no se alcanzan con el rango nuevo de J1.

## Repo y herramientas
- `EncoderPCNT` sin probar en placa más allá de 32 000 cuentas (girar a mano y ver que no salte).
