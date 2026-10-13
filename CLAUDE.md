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
- **Potencia v0.6 (08/10, solo con lo que hay):** motores con la **LiPo Zeee 3S** 11,1 V 8000 mAh, sin BMS
  (`docs/fotos/bateria 2/`), **directa al bus de 12 V, sin buck**: XT60 (el Deans de fábrica se cambia: no hay hembra) → **fusible de auto 20 A** (la protección contra
  cortos) → **selector WEG** (ON/OFF de motores: 2 bloques NA BC10 en paralelo; la térmica CHINT salió el 10/10); hay cargador balanceador. Pi y ESP32 desde el **power bank Xiaomi PB2030MI**
  5 V 3 A (`docs/fotos/bateria 3/`; 15 W, piden ~11 W: verificar `vcgencmd get_throttled` = 0x0). Divisor de batería
  **100 k / 27 k**, aviso a 10,5 V (no frena: parar a mano). Seta (ya está, `docs/fotos/llaves/`): **bloque A corta el + del bus de 12 V** (entre selector y bornera; 10/10,
  decisión del grupo; contacto `10(6)A 400V~`: solo emergencias) + bloque B avisa al GPIO 47 (`docs/html/seta.html`; directo, sin 100 nF:
  ponerlo si aparecen paradas por `SETA` sin tocarla); sin relé, TVS ni Schottky. Buck 3 (12 → 6 V) para los servos. **Guardada: la 10S** de 36 V
  (`bateria 1`): si vuelve, buck 1 y divisor 120 k / 8,2 k **antes** de conectarla (el de 27 k quema el GPIO).
  Ver `docs/CONEXIONES.md` (pines, potencia, autonomía ~2,1 h), `docs/html/conexiones.html` y `docs/html/potencia.html` (potencia cable por cable, con fotos;
  publicada en https://claude.ai/artifact/XgHwcJdBMFjG3Wtzww6Dbz, link compartido: republicar ahí si cambia). Otros HTML publicados
  (republicar en el mismo link): `conexiones` 5hi4sWhQBTHYNr3FLSfbBT, `placa_s3` Eh7aHHJxkqLbDRWDK8V4QC, `placa_wroom`
  9bNnuG8gzoY4JaQFYZkM2M, `seta` Xg44ttLdCxQPopHYMKNGdw (privada).
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión, IK, misión. Habla por USB (micro-ROS) con dos ESP32.
  Propuesta: la Pi arriba del mástil junto a las cámaras (cable CSI corto) y USB hacia los ESP32. **GPS UP501 en la
  Pi** (UART GPIO 14/15, `nmea_navsat_driver` → `/gps/fix`; Pi configurada, falta conectar el GPS) por un HAT pasivo de borneras.
- **ESP32-S3** (base): 2 motores de tracción + 2 IBT-2, encoders, IMU MPU-6500 (sin magnetómetro),
  3 HC-SR04 (un TRIG cada uno: 10/41/42, de a uno cada 40 ms), **3 bumpers** (frente y laterales), seta, batería. **ESP32-WROOM-32D** (brazo): J1 36GP-555 + IBT-2,
  2 servos. **J2/J3: 36-555 de 58 rpm (139:1; mismo encoder SCX-555 que J1, NO se autobloquean) con un IBT-2 cada uno y
  correa GT2 5:1 (poleas 20 → 100, correa de 240 mm, ~54 mm entre centros). Llegan entre el 19 y el 29/10**
  (por qué se cambió el sin fin 5840 y la versión de 98 rpm: `docs/BITACORA.md`); pines v0.5 en `firmware/brazo/include/pins.h` (12/10). Total: 5 IBT-2.
- Placas (05/10, `docs/html/placa_s3.html` y `docs/html/placa_wroom.html`, con vista de cableado): la **S3 va sobre la
  expansión Freenove** (bornera por pin) y sus componentes (divisores de ECHO, 20 k de encoders, pull-down
  del EN, divisor de batería; **sin capacitores** desde el 13/10: bumpers y seta directo a su bornera) en dos perforadas chicas, una sobre cada fila de borneras. La **WROOM es una HW-394 de
  30 pines** (USB-C, CH340) **en un shield de borneras** (12/10, foto en `docs/fotos/esp32 wroom 32D/`) + una perforada
  chica de distribución (rieles 5 V, 3,3 V, EN, GND y 6 V). **Pines v0.5:** encoder J2 en 36/39 y FC J1/J2 en 32/33:
  la única resistencia es el 10 k del EN (23); sin 100 nF (el homing pide 3 lecturas). Pinouts en `docs/fotos/esp32 s3 wroom/` y
  `docs/fotos/esp32 wroom 32D/`. **Verificar en qué pin está el LED RGB de la S3**: en la DevKitC-1 v1.1 es el 38 (EN
  de la tracción); `pins.h` supone el 48.
- Brazo RRR montado **atrás a la izquierda, sobre el eje de tracción**, a ~6 cm del costado (y = 0,11 m; preliminar). **Tipo uArm / Dobot Magician**: cuatro barras (medidas de la E4) y un paralelogramo que mantiene la
  herramienta **siempre horizontal**, apuntando en la dirección de J1 (E1). Pinza con 2 servos DSSERVO RDS3218
  20 kg·cm (apertura y giro J4 sobre el eje de la herramienta; foto en `docs/fotos/pinza/`). Pines y alimentación: `docs/CONEXIONES.md`.

## 3. Estructura
- `docs/`: consignas, `TPF R1/` y `TPF R2/` (una carpeta por entrega), `fotos/` (`motor_j1/2/3`, `motor_traccion`, pinza, rueda,
  `bateria 1` = 10S, `bateria 2` = LiPo, `bateria 3` = power bank, bumpers, `llaves` (seta y selector), `conectores` (XT60), `esp32 s3 wroom`, `esp32 wroom 32D`), `COMPRAS.md` (lista de
  compras con casillas), `INDICE.md`, `ARQUITECTURA.md`, `CONEXIONES.md`, `html/` (páginas: conexiones, potencia, placas y seta; `html/fotos` es un enlace a `fotos/`),
  inventario, bitácora.
- `firmware/lib/`: drivers y lógica compartidos (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, L298N,
  EncoderPCNT, HCSR04, MPU9250, UP501). `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/brazo_ik/`: nodo de cinemática inversa; `ros2_ws/src/mision/`: FSM de la demo y TF cámara → brazo. `ros2_ws/src/simulacion/`: Gazebo Harmonic (hilera + robot). `vision/entrenamiento_limon/`: cuaderno de Colab del
  detector. `graphify-out/`: grafo del repo (local, fuera de git).

## 4. Cómo trabajar acá
- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF** (bloqueados en
  `.claude/settings.local.json`): usar sus `.txt`/`.md`. Los `.ipynb` se pueden leer (11/10); preferir su `.md` si existe.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- **Entregas (`docs/TPF R*/`): el usuario las edita a mano en Drive/Colab** (el profesor sigue el panel de actividad).
  Claude edita el `.ipynb` y el `.md` locales y le pasa qué
  copiar. Imágenes por link `lh3.googleusercontent.com/d/<ID>=w2400`: al cambiar una, subir nueva versión en Drive (mismo
  ID) y cambiar el `=w` para saltear la caché. Diagramas: `.drawio` → PNG con Firefox headless + visor de diagrams.net
  (no hay draw.io instalado; el snap de Firefox no ve `/tmp`: usar `~/snap/firefox/common/render/`).
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor con `-s read-only`; sandbox arreglado el 28/09 con el perfil AppArmor `/etc/apparmor.d/bwrap`;
  lanzar con `< /dev/null` **desde la carpeta del repo** y esperar `tokens used`; confirmar a los 20 s que abrió
  sesión); **graphify** (grafo del repo); **ponytail**
  (instalado, sin usar todavía); **anatomy** (figuras isométricas, en `~/.claude/skills/`; para informes, no antes del 3/11).
  Locales (`.claude/`, fuera de git): **`/pi-sync`** (rsync a la Pi, `colcon build` y flasheo de los ESP32;
  sin probar con la Pi) y un hook que pide confirmar los 12 V apagados antes de `pio ... -t upload` o `esptool`. `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas
  (`codex --sandbox workspace-write` en el repo; lee este archivo por `AGENTS.md`); al volver, revisar `git log` antes de seguir.
- **Hardware: trabajar con lo que hay, no con lo ideal** (sin presupuesto ni tiempo para conseguir piezas). Antes de
  proponer un circuito, una lista de componentes o un cambio de hardware (sobre todo potencia: baterías, step-down,
  fusibles, protecciones, cableado, conectores; también sensores o placas): 1) revisar `docs/fotos/` y
  `docs/Componentes_inventario.md`; 2) **preguntar qué componentes hay ahora mismo** si no hay certeza, en vez de
  completar con el componente "ideal". Solo si es imposible con lo disponible: explicar por qué no alcanza y proponer
  la alternativa más simple y barata, sin listas largas de piezas nuevas.

## 5. Estado actual (al 2026-10-12)
- **Fecha límite: 9/11/2026** (robot completo). Estimado al 05/10: ~45 % (software ~70 % pero casi sin hardware real;
  conexiones ~10 %). Plan por semanas: 6-12/10 potencia + S3 + sensores + visión real; 13-19/10 base con teleop, GPS/IMU,
  soporte de cámaras, J1 por micro-ROS, IBT-2 de J2/J3 cableados; 20-26/10 hilera real, app, TF; 27/10-2/11 J2/J3
  (partiendo de J1) y `mision` real; 3-9/11 integración, 30 frutos, informes.
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 17 pruebas OK. **Pines v0.4 (05/10; v0.5 el 12/10, ver §2): J1-J3 con IBT-2 (J2 25/26, J3 16/17), EN común 23 (rueda libre solo de las tres juntas: si una se mueve, las otras quedan frenadas), FC J3 en 27 con pull-up interno, sin L298N; J2/J3 con 139:1 (8896 cuentas) y parámetros de J1 a 58 rpm, correa 5:1 (06/10) y signos sin medir.** **J1 con los parámetros medidos en `pruebas-esp32/10` (2026-10-02):** relación 5 (correa 18 → 90), zona muerta 17 %, PI 0,659 %/rpm y 4,8 (= 0,549 y 4 en °/s de la base), Kpp 2, tolerancia 0,3°, velMin 3 °/s, feedforward solo con la zona muerta (`ffSoloZonaMuerta`), `ENC_INVERTIDO` y `MOTOR_INVERTIDO` en true, duty máx 40 %, homing 25 s. Sin probar en este firmware. **Rango de J1 = 45°/225° en el marco de `brazo_ik`** (q1 = 0 al frente, antihorario; decisión del usuario 2026-10-02: −45/+135 desde el costado izquierdo, que es q1 = 90° = `POSE_CERO` de J1 y la marca del banco). Pasa por atrás y nunca cruza el mástil (adelante-derecha). Definido en `brazo_config.h`, `Q1_LIM` y `q1_en_rango()` de `cinematica.py` (atan2 da (−180°, 180°]) y el urdf; reposo por defecto de `fsm.py`: q = 75°/110°/−30°, el de la simulación. Pruebas OK: firmware 17, brazo_ik 7, mision 30, simulacion 13. **Sin probar en Gazebo:** limones de la simulación a menos de 45° (adelante-izquierda) ya no se alcanzan.
  Probado en la placa sola (sin motores ni sensores).
- `firmware/base`: tracción diferencial, odometría, sensores, seguridad local; serial o micro-ROS. 20 pruebas OK.
  Al 29/09: ruedas de 150 mm (radio 0,075), trocha 0,40, 3 bumpers (frente: no avanza; laterales: sin giro), batería
  LiPo 3S (aviso a 10,5 V, divisor 100 k / 27 k; 08/10).
  Probado en la placa sola (sin motores ni sensores).
- Capa micro-ROS: compila en las dos placas; cada sesión arranca **desarmada** (`armar` por `/<parte>/comando`).
  Las dos placas probadas con el agente, solas y a la vez (28/09): tasas nominales, armado y reconexión.
  S3: flashear con reset por watchdog (ya en `platformio.ini`); abrir el puerto con DTR/RTS bajos la deja en
  modo descarga. Usar `/dev/serial/by-id/` porque el puerto pasa de ACM0 a ACM1.
- `brazo_ik`: 6 pruebas OK. `/brazo/objetivo` es el punto de agarre (TCP); con la herramienta horizontal, la muñeca
  está `largo_herramienta` más adentro en horizontal (parámetro; 0 por defecto, MEDIR en el real).
- Pi 5 (`r2d2@100.116.96.71`, Tailscale `r2d2-desktop`): Jazzy, agente micro-ROS en `~/microros_ws`, copia del repo
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
  `~/venvs/esptool/bin/esptool --port <S3> --before no_reset --after watchdog-reset read-mac`.
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

## 6. Decisiones
- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Base: frente = parte ancha (brazo), atrás = parte angosta (ruedas de tracción). 3 bumpers, sin trasero.
- Pi 5 arriba con las cámaras (no hay cable CSI largo): bajan USB a los ESP32 y el power bank va arriba, al lado de la Pi.
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
- EN común de tracción y GPS en la Pi (luz y buzzer, cuando vuelvan, también: GPIO 17 y 27): la S3 solo tiene libre el GPIO 40 (reservado para un 4.º bumper).
  GPS a la Pi (30/09) para dar un TRIG a cada HC-SR04: los 3 miran al frente y con TRIG común se pisaban los ecos.
- Videos (~500 MB) y artículos de terceros fuera de git.
- Cámaras (hallazgos de la simulación, valen para el robot real): el estéreo tiene una zona ciega a la izquierda de la
  imagen izquierda (42 % con la calibración vieja de la simulación; ~25 % con la del soporte rígido) y el brazo en reposo no puede quedar entre
  las cámaras y la fila. Con el brazo sobre el eje (29/09): mástil adelante a la derecha, cámara a 0,85 m mirando 94°
  a la izquierda y 28° abajo (del lado izquierdo quedaba tan cerca de la fila que ningún ángulo veía los 3 limones de
  un árbol), y reposo q = (75°, 110°, -30°), girado a la izquierda: J1 no cruza el mástil (girado a la derecha lo
  atravesaba al ir al limón).
- Simulación: brazo por velocidad (`JointController`, velocidad del perfil + corrección) y `/joint_states` a 50 Hz;
  con `JointPositionController` + `use_velocity_commands` el brazo temblaba (Gazebo va a la consigna en un paso).
- Simulación: no reentrenar YOLO con imágenes de Gazebo (arruinaría el modelo para los limones reales).

## 7. Próximos pasos
1. Potencia v0.6 (`docs/CONEXIONES.md`): el fusible de 20 A y la seta (2 bloques NC) ya están: falta el portafusible; cambiar el Deans de la LiPo por XT60;
   buscar los capacitores (≥ 25 V). Armar el divisor
   100 k / 27 k antes de conectar la LiPo. Prueba integrada mínima: lista en `CONEXIONES.md`.
2. Cablear según `docs/CONEXIONES.md` v0.6 (LiPo → fusible 20 A → selector WEG → bus 12 V → motores; power bank → Pi → ESP32 por USB; GND común) y su lista
   "Antes de conectar". Primera prueba de la base con ruedas en el aire (README): sentidos, `cuentasPorVuelta` = 8316,
   radio, trocha y parada real por watchdog. Probar sensores en ROS (hoy nada probado con periféricos).
   Armar las placas según `docs/html/placa_s3.html` y `docs/html/placa_wroom.html` (orden de armado y prueba en cada página); en la S3,
   antes medir la tira roja (V) de la Freenove y probar si sus LEDs cargan los pines de los bumpers y la seta.
3. Visión: prueba de campo del limón (§5) y con las NoIR al sol; B3 (cosechable / no cosechable / obstáculo):
   hoy el detector tiene una sola clase. Recalibrar solo si el soporte de cámaras se mueve o cambia.
4. Brazo: **reflashear con los pines v0.5** (12/10; el binario de la Pi tiene los v0.4) y armar el shield y la perforada
   de distribución según `docs/html/placa_wroom.html`; medir que los encoders tengan su pull-up (A/B en 0 o 3,3 V, nunca a mitad;
   si falta, 10 k a 3V3). Probar el firmware con el motor de J1 en el lugar de J2; con los motores nuevos, pasos 0-3 de
   `pruebas-esp32/10` (hoy J2/J3 tienen los parámetros de J1 llevados a 58 rpm). Medir lo
   `MEDIR`. Falta sostener J2/J3 contra la gravedad (no se autobloquean).
5. Peso real del robot (estimado 6-9 kg; la guía pide ≥ 5 kg) y autonomía real (estimado ~2,1 h de cosecha con la LiPo).
6. Si la cátedra exige 4 bumpers: el 4.º en el GPIO 40 de la S3.
7. **Después de la prueba integrada (decisión 08/10: ahora se minimiza todo lo no esencial):** H8 de la guía R2 —
   luz, buzzer y habilitación física del brazo con estado visible (sacados de la v0.5); la seta ya corta los 12 V de
   todos los motores. R2: app del celular (E7), detección de árboles/troncos/caminos (E5), herramienta (E6).
8. Medir la TF cámara → brazo con el soporte rígido (argumentos de `mision.launch.py`) y probar `mision` con el
   brazo real: `cierre`, `reposo` y `largo_herramienta` (muñeca → centro del agarre, en horizontal; más un desfase
   vertical si lo hay, hoy no contemplado).
9. Preguntas a la cátedra que quedan (`docs/ARQUITECTURA.md` §11: eje lineal de 1,2 m, GDL en R2, cajones).
10. Simulación: validar la cadena real con un detector "perfecto" sobre las imágenes de Gazebo (`vision:=yolo`, en la
   PC de escritorio); el recorrido autónomo ya cosecha 12 de 12 con `limones_sim`; cargar las medidas reales que faltan
   (altura de la caja sobre el piso, trocha, eje, ruedas locas, cámaras, pinza). Pendiente: cajón para el limón.
