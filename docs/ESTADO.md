# Estado actual (al 2026-10-22)

Movido de `CLAUDE.md` §5 el 22/10. **El estado va acá, nunca en `CLAUDE.md`.** Lo hecho día por día: `BITACORA.md`; lo que falta: `PENDIENTES.md`.

- **Fecha límite: 9/11/2026** (robot completo). Estimado al 05/10: ~45 % (software ~70 % pero casi sin hardware real;
  conexiones ~10 %). Plan por semanas: 6-12/10 potencia + S3 + sensores + visión real; 13-19/10 base con teleop, GPS/IMU,
  soporte de cámaras, J1 por micro-ROS, IBT-2 de J2/J3 cableados; 20-26/10 hilera real, app, TF; 27/10-2/11 J2/J3
  (partiendo de J1) y `mision` real; 3-9/11 integración, 30 frutos, informes.
- **19/10 (potencia, decisión del grupo):** orden LiPo → XT60 → fusible 20 A → **seta (bloque A) → selector WEG** →
  bornera +12 V (cable 1 de la seta: fusible → A1; cable 2: A2 → borne 3 del selector); el selector usa **un solo
  bloque NA** (3-4; si calienta, sumar el otro en paralelo); **sin capacitores en el bus de 12 V**. El divisor del GPIO 1
  toma los 12 V de la bornera (después de seta y selector). El bloque B de la seta va al **GPIO 47, nunca al 1**:
  detalle borne por borne en el Paso 2b de `seta.html`. Bumpers: microinterruptor con C (abajo) a GND y NO (borne 3)
  al GPIO; NC (2) libre (`docs/fotos/bumpers/circuito.jpeg`). `armar_todo.py` solo reemplaza por base64 rutas dentro
  de atributos (una ruta en el texto estiraba la pestaña Seta a 5000 px). Pi sincronizada el 19/10 (repo, `brazo_ik`
  y `mision` compilados, binarios copiados); sin flashear: no había ESP32 enchufados.
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 18 pruebas OK; `m` y `j` rechazan J2/J3 con γ₄ = q2 + q3 − 90° fuera de −111,9…−30° (`cuatroBarrasOk()`, 18/10, revisado por Codex): una falla en J2 o J3 detiene la otra; `home 2`/`home 3` bloqueados (`HOME_J23_VERIFICADO`) hasta medir `HOME_Q`; `POSE_CERO` provisoria (90°, 90°, −40°). Sin cubrir: el camino entre objetivos y `d`/`v`. **Pines v0.4 (05/10; v0.5 el 12/10, ver §2): J1-J3 con IBT-2 (J2 25/26, J3 16/17), EN común 23 (rueda libre solo de las tres juntas: si una se mueve, las otras quedan frenadas), FC J3 en 27 con pull-up interno, sin L298N; J2/J3 con 139:1 (8896 cuentas) y parámetros de J1 a 58 rpm, relación 5 = engranajes helicoidales 15 → 75 (confirmado 17/10) y signos sin medir.** **J1 con los parámetros medidos en `pruebas-esp32/10` (2026-10-02):** relación 5 (correa 18 → 90), zona muerta 17 %, PI 0,659 %/rpm y 4,8 (= 0,549 y 4 en °/s de la base), Kpp 2, tolerancia 0,3°, velMin 3 °/s, feedforward solo con la zona muerta (`ffSoloZonaMuerta`), `ENC_INVERTIDO` y `MOTOR_INVERTIDO` en true, duty máx 40 %, homing 25 s. Sin probar en este firmware. **Rango de J1 = 45°/225° en el marco de `brazo_ik`** (q1 = 0 al frente, antihorario; decisión del usuario 2026-10-02: −45/+135 desde el costado izquierdo, que es q1 = 90° = `POSE_CERO` de J1 y la marca del banco). Pasa por atrás y nunca cruza el mástil (adelante-derecha). Definido en `brazo_config.h`, `Q1_LIM` y `q1_en_rango()` de `cinematica.py` (atan2 da (−180°, 180°]) y el urdf; reposo por defecto de `fsm.py`: q = 75°/94°/−50°, el de la simulación (provisorio desde el 18/10: con el balancín de 60 mm el de 110°/−30° no cierra el cuatro barras). Pruebas OK: firmware 18, brazo_ik 9, mision 31, simulacion 13. **Sin probar en Gazebo:** limones de la simulación a menos de 45° (adelante-izquierda) ya no se alcanzan.
  Probado en la placa sola (sin motores ni sensores).
- `firmware/base`: tracción diferencial, odometría, sensores, seguridad local; serial o micro-ROS. 20 pruebas OK.
  Al 29/09: ruedas de 150 mm (radio 0,075), trocha 0,40, 3 bumpers (frente: no avanza; laterales: sin giro), batería
  LiPo 3S (aviso a 10,5 V, divisor 100 k / 30 k; 08/10).
  **20/10, tracción probada con las ruedas en el aire (bitácora):** sentidos de motores y encoders correctos,
  arrancan con 20 %; medidos K 0,6 rpm/%, zona muerta 11 % y τ 80 ms (`scripts/escalon_tau.py`, env `serial_motores`
  para tener `log`), PI 0,89/11,1: `w 8 8` → las dos en 8 ± 0,1 rpm. 8316 cuentas confirmadas (rueda izq., 1 vuelta).
  **Teleop desde Android:** Termux + Tailscale → ssh → `teleop_twist_keyboard` (`repeat_rate:=10.0`); anda. Y una
  página con joystick, `firmware/base/scripts/teleop_web.py` (puerto 8000, sin rosbridge; base de la app de la E7):
  `http://100.116.96.71:8000` con Tailscale (**22/10: manejada desde el celular** con las ruedas en el aire, las dos placas en la Pi; cada botón destella al llegar el comando). Con `u` a
  velocidad máxima, > 4 A (normal: 2,6 A en vacío por motor). En la S3 está el env de prueba **`ros_motores`** (sin IMU
  ni distancia al frente; tope de `d` 25 %): nunca en el piso. Los 5 V de la Freenove salen de su jack (plug desde la
  bornera +12 V; el USB no los da). La rueda derecha patina en el eje (prisionero). `desarmar` por micro-ROS no
  funcionaba en ninguna placa (palabra cortada a 7 letras): corregido y flasheado en las dos.
- Capa micro-ROS: compila en las dos placas; cada sesión arranca **desarmada** (`armar` por `/<parte>/comando`).
  Las dos placas probadas con el agente, solas y a la vez (28/09): tasas nominales, armado y reconexión.
  S3: flashear con reset por watchdog (ya en `platformio.ini`); abrir el puerto con DTR/RTS bajos la deja en
  modo descarga. Usar `/dev/serial/by-id/` porque el puerto pasa de ACM0 a ACM1.
- `brazo_ik`: 9 pruebas OK (2 comparan sus límites y el rango de γ₄ con `brazo_config.h`). `/brazo/objetivo` es el punto de agarre (TCP); con la herramienta horizontal, la muñeca
  está `largo_herramienta` más adentro en horizontal (parámetro; 0 por defecto, MEDIR en el real).
- Pi 5 (`r2d2@100.116.96.71`, Tailscale `r2d2-desktop`; en el lab, Wi-Fi FIUNA 172.16.240.92 al 20/10: aísla los
  clientes, el celular entra solo por Tailscale): Jazzy, agente micro-ROS en `~/microros_ws`, copia del repo
  en `~/recolector_de_frutas` (por rsync, sin `.git`), esptool en `~/venvs/esptool`. Binarios para flashear en
  `~/firmware/<base|brazo|hola>`, scripts en `~/scripts`, logs en `~/logs`, workspaces de ROS en `~/ros/` y venvs en
  `~/venvs/` (ordenado el 01/10; `~/microros_ws`, `~/camera_ws`, `~/yolo_ws`, `~/yolo_env` y `~/keepon_env` quedan
  como symlinks: las rutas viejas siguen valiendo). Las dos placas conectadas a la
  Pi con sus agentes: todas las tasas nominales. Brazo a 115200 (a 921600 el CH340 pierde datos en la Pi).
  **Todo lo del 28/09 fue con las placas solas: sin motores, drivers, encoders, IMU, GPS, HC-SR04, bumpers ni
  seta.** Las tasas son de mensajes sin datos reales (distancias NaN, IMU y GPS no publican). Los drivers y
  sensores siguen sin probar en este proyecto.
  Agentes: `micro_ros_agent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` (brazo) y
  `.../usb-Espressif_USB_JTAG_serial_debug_unit_*-if00` (base). Si la S3 no abre sesión, está en modo descarga:
  `~/venvs/esptool/bin/esptool --port <S3> --before no_reset --after watchdog-reset read-mac` (sin `--before no_reset` la deja
  en modo descarga). Si el puerto da `OSError: [Errno 71] Protocol error`, el USB quedó trabado: 12 V apagados, desenchufar
  y enchufar el USB de la S3 (22/10, una vez al prender los 12 V; la segunda vez aguantó). Por ssh, `pkill -f` con un patrón
  anclado (`"^/home/r2d2/microros_ws.*Espressif"`): si no, coincide con el propio comando y corta la sesión.
  Ping del enlace a 100 ms (a 20 ms daba cortes falsos por latencia); contadores `enlace: pings_fallidos cortes`
  en `/<parte>/estado`; bajo carga fuerte, 0 cortes. Pendiente con ruedas: medir
  la parada real por el watchdog de 300 ms (revisión de Codex: a 1 m/s, ~30 cm antes de empezar a frenar).
- Visión: repo aparte `HecVelaz/vision_estereo` (en la Pi, `~/vision_estereo`; en la notebook, `~/Documentos/vision_estereo`;
  en GitHub al día; su `CLAUDE.md` §5-6 tiene el detalle). `datos/` (calibración, foco, pruebas; fuera de git) solo se genera en la Pi: respaldo en la
  notebook (01/10, con los logs de las pruebas) con `rsync -a r2d2@192.168.2.219:vision_estereo/datos/ ~/Documentos/vision_estereo/datos/`
  (repetir tras cada calibración o prueba). Cadena
  `scripts/start_limon.sh` = `launch/limon.launch.py` (cámaras, rectificación, disparidad **SGBM** por defecto, BM con
  `ALGORITMO=0`) + `detector_node` (`/yolo/detecciones`) + `localizador_node` (`/limon/posicion`, PointStamped en el
  marco óptico RECTIFICADO de la cámara izquierda: tenerlo en cuenta en la TF al brazo). Disparidad SGBM ~2,5 Hz
  (BM ~10). Revisado por Codex. Cámaras y calibración en `config/camaras.yaml` (cámara 0 de libcamera = izquierda).
  **Calibración en uso: `config/calibracion_soporte_2/`** (soporte rígido, 01/10): RMS 0,36 px, baseline 89,5 mm
  (regla: 90 mm), f 654,3 px, ventana 0,38-0,96 m. Zona ciega: el cuarto izquierdo de la imagen izquierda (u < ~163 px)
  se detecta pero no se localiza. Exposiciones izq/der sin sincronizar: localizar con el robot quieto.
- **Cámaras (01/10): las dos transmiten a 30 FPS con la cinta CSI nueva.** Si una falla: síntomas de cinta dañada
  `Failed to write reg`, `stream on failed`, `Camera frontend has timed out`; se aísla intercambiando cintas (con la
  Pi apagada). `~/scripts/probar_camaras.sh` en la Pi. Vista en crudo: `web_video_server` en el 8080.
- **Ensayos con un limón real (01/10, SGBM, logs en `vision_estereo/datos/pruebas/`):** YOLO lo detecta (confianza
  mediana 0,80); `/limon/posicion` contra cinta en el eje a 40/55/70/90 cm: error +4 a +15 mm; a los costados (6 puntos
  con regla): error 3D máximo **17 mm** (B5 pide ≤ 35 mm: cumple en laboratorio). Queda ~+1 cm de desfase en Z
  (origen de la cinta en el frente de la lente + ~1 % de escala). **Pendiente: prueba de campo** (limón en un arbusto
  a 40-90 cm, `guia_limon.py --campo`; lanzada y cancelada sin mediciones) y las NoIR al sol (colores rosados).
- Detector de limones (28/09): entrenado en Colab con `vision/entrenamiento_limon/` (datasets de Roboflow, una
  clase `limon`). Test: P 0,953, R 0,977, mAP50 0,978, mAP50-95 0,814 (285 imágenes, 200 sin limón, 173
  limones; mismas fuentes que el entrenamiento: números optimistas). En la Pi:
  `~/vision_estereo/modelos/limon_yolo26n_ncnn_model` (fuera de git; 23 FPS solo). El `.pt` quedó en Drive
  (`arturito/limon_yolo`). Probado con un limón real en el lab (arriba); falta el campo. **Una sola clase: B3 pide
  cosechable / no cosechable / obstáculo-oclusión.** Uso:
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
  (`joint_states` contra `joint_cmd`). Revisada por Codex y aplicada; con la seta en `/base/estado` desarma el
  brazo y pasa a FALLA (06/10, revisión de conexiones de Codex); probada en la notebook con
  brazo y limón simulados. Sin probar con el brazo real. Usa el mismo `largo_herramienta` que `brazo_ik` (MEDIR).
