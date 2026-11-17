# Próximos pasos

Movido de `CLAUDE.md` §7 el 22/10. Fecha límite: **27/11/2026** (demo). Estado: `ESTADO.md`.

000. **Plan hasta la demo del 27/11** (17/11; robot = usuario, software = Claude en paralelo, probado en Gazebo):
   | Días | Robot | Software |
   |---|---|---|
   | 18–19/11 | Seguridad con los motores andando (00a d) | BUSCAR (00a a) y paradas de seguridad en `movimiento.py` |
   | 20–21/11 | Pegar las marcas 1–3, probar BUSCAR, decidir dónde soltar | RODEAR (00a b) y soltar (00a c) |
   | 22–23/11 | Recolección en las 4 paradas | Misión ROS (00a e) con los estados de S3; nodo `seguridad` aparte (S2) |
   | 24–25/11 | WROOM al env `ros`; probar la misión ROS | Rosbag por misión (S5), GPS en el registro, estado y alarmas en `teleop_web.py` (S6) |
   | 26/11 | Ensayo general y video de respaldo | Ajustes |
   - **Recortado:** hilera (`recorrido.py`), EKF, app nueva, métricas detalladas, madurez por tamaño, celular como
     sensor. H8 (luz y buzzer) solo si sobra un día y hay piezas.
   - **Plan B:** si la misión ROS no llega, demostrar con `recolectar.py` y presentar la misión ROS como en curso.
   - **Riesgo:** los cortes del USB de la S3 (la base se desarma). Falta saber si el 27/11 hay además informe (E7/E8).
00a. **(Con a, b y d se cubre N3 de la guía.)** **Navegación y recolección autónoma (13/11, en `pruebas-esp32`; detalle en su `notas/PENDIENTES.md`), en orden:**
   a) **BUSCAR:** si no ve la marca, girar de a ~20° con el giróscopo; si no aparece en 360°, avanzar ~1 m esquivando
      con los HC-SR04. Hoy `recolectar.py` tiene que arrancar viendo la marca.
   b) **RODEAR:** pegar las marcas ID 1–3 (antihorario) e ir de parada en parada con arcos de 90°, el árbol a la izquierda.
   c) **Soltar el limón:** el lugar todavía no está decidido.
   d) **Seguridad con los motores andando:** HC-SR04 < 20 cm, bumper, vuelco y los cortes del USB de la S3.
   e) **Llevarlo a la misión ROS** (`ros2_ws/src/mision`), primero en Gazebo: mandar texto por `/brazo/comando` al
      firmware 20 (no entiende `/brazo/joint_cmd`) con la WROOM en el env `ros`; los giros con `movimiento.py` / el
      giróscopo o `robot_localization` con `/odom` + IMU; el GPS (±20 m) solo para la rúbrica.
000b. **Brazo: NO flashear `firmware/brazo`** (el binario `ros` de `d3644c8` en `~/firmware/brazo` de la Pi está viejo).
   Desde el 11/11 la WROOM tiene `pruebas-esp32/20-brazo-coordinado` (env `brazo`, serie, desde el 13/11; el `ros` en `respaldo_wroom_20261112.bin`) (franja, caja, homing 3/6/3, pinza y
   muñeca; lo usa el teleop `25-teleop-pi`). Falta pasar todo eso a `firmware/brazo` (pendiente "f" de
   `pruebas-esp32/notas/PENDIENTES.md`) y recién ahí flashearlo. Respaldo de 20: `~/firmware/brazo/respaldo_wroom_20261111.bin`.

00. **Entrega 7 de R1 (diseño final y demo, 17/10)** en `docs/TPF R1/Entrega 7/`, revisada con Codex (aclaraciones aplicadas; detalle en la bitácora) y
   con todos los IDs de Drive puestos. El usuario la siguió editando en Colab (Figs. 19a-c, servo, videos): el repo quedó
   igual a su versión de Drive (18:23). Falta: el video de la demo (lo agrega el usuario); confirmar los rodamientos (bridados 4×13×5 y axial 51105) y la clasificación de las 18 piezas por
   tipo. Propuesto y sin aplicar: sumar a Sensores el potenciómetro interno de los servos y la seta. Los PDF de
   `Partes_del_brazo/` (30 MB) y el `.rar` del CAD (121 MB, en Drive) quedan fuera de git. "Correa" para J2/J3 corregida (17/10) en `CONEXIONES.md`, `COMPRAS.md`, el manual, `conexiones.html` y `todo.html`
   (republicadas); siguen con correa solo la Entrega 4 de R2 (entregada: preguntar antes de tocarla).
0. **Power bank corregido (15/10):** es el **PB2020MI** (22,5 W), no el PB2030MI; corregido en docs, HTML, manual y Entrega 4 local,
   y republicados `potencia`, `conexiones` y `todo` (que además seguían con el divisor de 27 k). Falta: a) la Entrega 4 en **Drive**
   (4.4 y pie de la Figura 16: PB2020MI y 22,5 W; subir `potencia_v06.png` nuevo con el mismo ID y cambiar el `=w`);
   b) el `.drawio`/PNG de la entrega sigue con **divisor 100 k / 27 k** (no se tocó por ser una entrega: preguntar).
   `placa_s3` ya está republicada con 30 k (16/10).
0b. ~~**Alimentación de la Pi**~~ (12/11): prueba real de 1 h con el power bank OK (EXT5V ≥ 4,96 V, `0x0`; ESTADO).
   Cargarlo al 100 % antes de la demo.
1. Potencia v0.6 (`docs/CONEXIONES.md`): el fusible de 20 A y la seta (2 bloques NC) ya están: falta el portafusible; cambiar el Deans de la LiPo por XT60
   (sin capacitores en el bus desde el 19/10). Armar el divisor
   100 k / 30 k antes de conectar la LiPo. Prueba integrada mínima: lista en `CONEXIONES.md`.
2. Cablear según `docs/CONEXIONES.md` v0.6 (LiPo → fusible 20 A → seta → selector WEG → bus 12 V → motores; power bank → Pi → ESP32 por USB; GND común) y su lista
   "Antes de conectar". Base con ruedas en el aire: hecha el 20/10. **13/11: env `ros` con IMU, HC-SR04,
   bumpers y seta OK en ROS, y odometría en el piso medida (recto < 1 %).** Falta: parada real por watchdog, corriente
   con peso y las pruebas de seguridad con los motores (00a d); confirmar si el prisionero de la rueda derecha se arregló.
   Armar las placas según `docs/html/placa_s3.html` y `docs/html/placa_wroom.html` (orden de armado y prueba en cada página); en la S3,
   antes medir la tira roja (V) de la Freenove y probar si sus LEDs cargan los pines de los bumpers y la seta.
2b. **Tarea VA de R2 (si no se entregó):** corregir en Colab §6.1 (16 de 20, no 15), volver a poner "Autor: FB",
   §11 (mismo limonero, una foto repetida) y §5.2 (≈ 1,0). Detalle en la bitácora 11/11.
2c. **Detector v3 (amarillos):** ya en la Pi (12/11) y detecta con las NoIR. Falta compararlo con la v2 en cifras
   (confianza mediana, 20 cuadros, como el 28/10) y afuera al sol; confirmar el color de los limones de la demo.
3. Visión: estéreo recalibrado en el mástil y probado en el arbusto (12/11, `calibracion_mastil`). TF cámara → brazo
   **medida el 12/11** (9 puntos, ~2 cm; valores en el docstring de `mision.launch.py`, `radio_limon:=0.025`); el error
   viene sobre todo del modelo de la punta en z (`pruebas-esp32`, bitácora del 12/11). Falta: limones bajos (inclinar el soporte
   ~15°); caño del mástil **fijado** (12/11, usuario). v2 ya en la Pi: compararla con la v1 afuera, al sol y con limones lejos o
   tapados (en el lab empatan); después, el enlace de la sección 12. Prueba de campo al sol (§5; en el arbusto del lab hecha el 12/11). B3: madurez por tamaño (diámetro = ancho_px · Z / f) en la misión o en
   `vision_estereo`, medir `D_min` con limones reales; obstáculo sin hacer. Fotos propias con las NoIR para el
   detector. 
4. Brazo (J2/J3 con **doble helicoidales 15 → 75 desde el 10/11**: primero, a mano y sin 12 V, medir el juego en la
   salida; luego `d` (signo y zona muerta a cada lado), `log 2` + `v 2 30 3` (K, τ) y `j 2 60`): **flasheado el 26/10** (`072c403`, duty máx 50 % en las tres); con `teleop_web.py` medir los signos de J2/J3 (`ENC_INVERTIDO`/`MOTOR_INVERTIDO`, hoy sin medir) y si 50 % alcanza para levantar el brazo; armar el shield y la perforada
   de distribución según `docs/html/placa_wroom.html`; medir que los encoders tengan su pull-up (A/B en 0 o 3,3 V, nunca a mitad;
   si falta, 10 k a 3V3). El motor de J1 en J2 ya se probó (levantó el brazo, 17/10); con los motores nuevos, pasos 0-3 de
   `pruebas-esp32/10` (hoy J2/J3 tienen los parámetros de J1 llevados a 58 rpm). Medir lo
   `MEDIR`. Falta sostener J2/J3 contra la gravedad (no se autobloquean) y definir los límites articulares reales (hoy provisorios: q1 45°/225°, q2 −25…135°, q3 ±50°); el balancín rojo mide 60 mm (`L30`, 18/10): con él, el reposo y `HOME_Q` = (45°, −25°, −50°) del firmware tienen que caer en γ₄ = q2 + q3 − 90° entre −112° y −30°; hoy `HOME_Q` da −165° (no cierra: MEDIR).
5. Peso real del robot (estimado 6-9 kg; la guía pide ≥ 5 kg) y autonomía real (estimado ~2,1 h de cosecha con la LiPo).
6. Si la cátedra exige 4 bumpers: el 4.º en el GPIO 40 de la S3.
7. **Después de la prueba integrada (decisión 08/10: ahora se minimiza todo lo no esencial):** H8 de la guía R2 —
   luz, buzzer y habilitación física del brazo con estado visible (sacados de la v0.5); la seta ya corta los 12 V de
   todos los motores. R2: app del celular (E7), detección de árboles/troncos/caminos (E5), herramienta (E6).
8. ~~Medir la TF cámara → brazo~~ (12/11). Pasar a `brazo_ik` el modelo medido de la punta (`pruebas-esp32/20`,
   `cinematica.py`, hombro 165 mm; hoy E4 con 150) y probar `mision` con el
   brazo real: `cierre`, `reposo` y `largo_herramienta` (muñeca → centro del agarre, en horizontal; más un desfase
   vertical si lo hay, hoy no contemplado).
9. Preguntas a la cátedra que quedan (`docs/ARQUITECTURA.md` §11: eje lineal de 1,2 m, GDL en R2, cajones).
10. Simulación: validar la cadena real con un detector "perfecto" sobre las imágenes de Gazebo (`vision:=yolo`, en la
   PC de escritorio); el recorrido autónomo ya cosecha 12 de 12 con `limones_sim`; cargar las medidas reales que faltan
   (altura de la caja sobre el piso, trocha, eje, ruedas locas, cámaras, pinza). Pendiente: cajón para el limón.
11. Herramientas: decidir si `/pi-sync` prueba también el Wi-Fi FIUNA (172.16.240.92) cuando no responden Tailscale
   ni la LAN (sin verificar que esa IP siga valiendo).
12. Recorrido autónomo por hilera (`recorrido.py`) en el robot real: sin probar; la demo pasó a ser un arbolito con
   marcas (00a). El giróscopo ya se calibra solo al arrancar (13/11).
13. Red directa celular ↔ Pi para el piso y la demo afuera (datos compartidos del celular o red propia de la Pi): sin
   Wi-Fi de FIUNA no hay Tailscale directo garantizado, y por el relay de São Paulo el joystick tiene lag.
14. Encoder de J2: confirmar con `e` que cuenta (el 26/10 no contaba; después del arreglo del usuario no se midió).
15. Finales de carrera del brazo: montar 3 microinterruptores (GPIO 32/33/27), medir `HOME_Q` con `z` + `e`, signo de
   `HOME_RPM` y `HOME_J23_VERIFICADO = true`; J2/J3 cerca de la pose de cero, homing de J3 antes que J2.
16. Enlace de la base: `pings_fallidos` y `cortes` suben (82 y 4 en ~1 h; el brazo, 0): mirar `~/logs/agente_base.log`.
