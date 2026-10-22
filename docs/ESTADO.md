# Estado actual (al 2026-10-22)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **9/11/2026**.

## Avance
- Software ~70 %, hardware real atrasado. Plan: 20-26/10 hilera real, app, TF; 27/10-2/11 J2/J3 y `mision` real;
  3-9/11 integración, 30 frutos, informes.
- Potencia v0.6 (cadena en `CONEXIONES.md`): falta el portafusible, el XT60 en la LiPo y armar el divisor 100 k / 30 k.
- Power bank PB2020MI probado (20/10): 15 min con la cadena de visión completa, 5,03-5,13 V, `throttled` 0x0.
  Falta repetir con los ESP32 por USB.

## Base (`firmware/base`, S3) — 20 pruebas OK
- **Ruedas en el aire (20-22/10):** sentidos de motores y encoders correctos; K 0,6 rpm/%, zona muerta 11 %,
  τ 80 ms, PI 0,89/11,1 (`w 8 8` → 8 ± 0,1 rpm); 8316 cuentas por vuelta. Manejada desde el celular con
  `teleop_web.py` (`http://100.116.96.71:8000`, Tailscale) y con `teleop_twist_keyboard` por ssh desde Termux.
- En la S3 está el env de prueba **`ros_motores`** (sin IMU ni distancia al frente; tope 25 %): nunca en el piso.
- Con `u` a velocidad máxima, > 4 A (2,6 A en vacío por motor). La rueda derecha patina en el eje (prisionero).
- Una vez, al prender los 12 V, el USB de la S3 se trabó (`Errno 71`); causa sin confirmar.
- Sin probar: IMU, HC-SR04, bumpers y seta en ROS; odometría en el piso; parada real por el watchdog de 300 ms
  (Codex: a 1 m/s recorre ~30 cm antes de empezar a frenar).

## Brazo (`firmware/brazo`, WROOM) — 18 pruebas OK
- Cascada J1-J3 + pinza; flasheado con pines v0.5 el 20/10. Probado solo en la placa (sin motores ni sensores).
- J1 con los parámetros de `pruebas-esp32/10` (sin probar en este firmware). J2/J3: motores 36-555 58 rpm 139:1 +
  helicoidales 15 → 75, llegan 19-29/10; tienen los parámetros de J1 llevados a 58 rpm y signos sin medir.
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
- Detector de una sola clase (`limon`; P 0,953, R 0,977, mAP50 0,978: **optimistas**, el test sale de las mismas
  fuentes que el entrenamiento): B3 pide cosechable / no cosechable / obstáculo.
  Modelo en la Pi: `~/vision_estereo/modelos/limon_yolo26n_ncnn_model`.

## GPS
- UP501 en la Pi (`/dev/ttyAMA0`, `nmea_navsat_driver` → `/gps/fix`). Primer fix a cielo abierto (21/10): ~5 min,
  3 satélites, σ ≈ 21 m. Bajo techo no ve ninguno. Con la Pi apagada pierde los satélites (arranque en frío).

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`); en el lab, Wi-Fi FIUNA 172.16.240.92 (aísla clientes: el celular
  entra solo por Tailscale). Repo sincronizado el 22/10 (`d688339`); `brazo_ik` y `mision` compilados.
- Rutas: agente en `~/microros_ws`, binarios en `~/firmware/<base|brazo|hola>`, scripts en `~/scripts`, logs en
  `~/logs`, workspaces en `~/ros/`, venvs en `~/venvs/` (las rutas viejas siguen como symlinks).
- Cámaras: las dos a 30 FPS con la cinta CSI nueva (`~/scripts/probar_camaras.sh`; vista cruda en el 8080).

## Simulación (Gazebo Harmonic, notebook)
- `ros2 launch simulacion sim.launch.py` (`mision:=true`, `vision:=yolo`, `gui:=false`): 12 de 12 limones.
  `vision:=yolo` parcial (YOLO no reconoce los limones sintéticos). Falta pasarla a la PC de escritorio.
- Sin probar en Gazebo: limones a menos de 45° (adelante-izquierda) ya no se alcanzan con el rango nuevo de J1.

## Repo y herramientas
- `EncoderPCNT` sin probar en placa más allá de 32 000 cuentas (girar a mano y ver que no salte).
