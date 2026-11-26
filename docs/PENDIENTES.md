# Próximos pasos

Movido de `CLAUDE.md` §7 el 22/10. Fecha límite: **27/11/2026** (demo). Estado: `ESTADO.md`.

0000z. **Para la demo (25/11 noche), en orden** (detalle en la bitácora del 25/11):
   1. **Probar en el robot:** salida de la canasta con el joystick (`jog_j1_out`) y el homing desde el brazo plegado.
   2. **Corte por "sin comandos" (BASE_SAFETY_NOT_OK):** si vuelve, leer `Timeout (0:00:00` en `bridge.log` (traza
      de faulthandler) y arreglar ahí; sacar `watch_stalls` de `run_pi.py` cuando se sepa.
   3. Recolector en una estación: 3 limones seguidos con la batería cargada; después Rodear árbol con 2 paradas.
   4. Teléfono: sin ahorro de batería y en la red de la Pi (o hotspot); medir `tailscale ping` < 50 ms. Si no, tablet.
   5. `SENSOR_AHEAD_MM` (MEDIR) en `collection_mission.py`; segundo punto de la batería para `BATTERY_SCALE`.
   5b. **Prioridad actual por pedido del usuario: TFmini-S + Estado de la app (25/11, ~21:31).** Cableado
       confirmado (verde GPIO 13 WROOM, rojo 5 V, negro GND; blanco aislado). Firmware 20 y puente implementados;
       APK 0.15.6 compilada, **sin instalar ni flashear ni copiar a la Pi**. Ver `docs/CONTINUAR_CLAUDE.md`.
       Repetir suite completa del puente en `/tmp/arturito-lidar-venv` con NumPy/OpenCV ya instalados; no commitear
       si falla. Después instalar en Poco X6 Pro, avisar antes de copiar a la Pi, confirmar 12 V apagados antes
       del respaldo/flasheo de la WROOM. Medir tensión, validar distancias quieto, medir montaje antes de navegar.
   6. Después de la demo: `sinCuentasMs` de J1 y `BATERIA_DIVISOR` en el firmware.
000a. **Para la demo (23/11 noche), en orden:**
   1. **Servo de la pinza:** no se mueve aunque el firmware le manda el pulso. ¿La muñeca se mueve? Buck 3 (6 V),
      conector de señal en la WROOM, servo caliente o dañado. Si fue por forzar: cerrar a menos de 1200 µs.
   2. **Afinar el punto de agarre** con 2–3 agarres seguidos (hoy varía ~2 cm entre mediciones; valores en ESTADO).
   3. **Probar la Recolección** con la parada a 60 cm (no se probó) y el Recolector con limones a ambos lados del árbol.
   4. S3 muda en medio del uso (20:34): si se repite, revisar `EnlaceMicroRos` (reconexión) antes de reflashear.
0000. **Recolección desde la app Arturito (actualizado 22/11; detalle en la bitácora 21–22/11), en orden:**
   0. **Alimentación de la Pi:** se apagó de golpe ~6 veces el 21/11 (sin apagado en el journal; a veces 4,90 V y
      `throttled=0x50000`). Revisar fuente, cable USB-C y enchufe (que no tire al girar la base); para afuera, 5 V / 5 A.
   1. **Sujetar los cables USB de la WROOM y la S3** (se cayeron con la base en movimiento: error -71, `cortes=4`).
      **Cortes del enlace de la S3 (23/11):** 6 sin desconexión USB; la carga de la Pi no los explica (medición de
      15 min sin cortes). Si vuelven: medir en ese momento con `~/scripts/medir_enlace_base.py`; arreglo posible en
      `firmware/lib/EnlaceMicroRos` (espera del ping 100 → 250 ms o 5 pings para corte; reflashear con 12 V apagados).
   1b. **Probar el mando manual nuevo (app 0.15.1, 23/11):** combinado (base + brazo) sin cortes de "Brazo ocupado";
      giro a 1 rad/s con cuidado; velocidades de la pinza. Si corta, la hora y `bridge.log` (anota el estado del brazo).
   2. **Altura del limonero:** con el objeto de 19 cm los limones quedan a ~63 cm del piso y el agarre pasa ~3 cm abajo.
      Bajarlo (~10 cm) para limones a 45–55 cm. Opcional: no intentar agarres por encima de ~56 cm, o bajar el limón
      antes de ir a la canasta (cambio en `punta.py`, probar con cuidado).
   3. **Homing de J3 desde el reposo** ("J3 CORTADA … no avanza"): hoy, mover J3 con el joystick y repetir. Arreglo:
      `homingDutyMax` de J3 ~65 % o `homingTrabadaMs` 3 s en `pruebas-esp32/20` (reflashear la WROOM, probar con tiempo).
   4. **Visión, criterio de confiabilidad** (autorizar): en `vision_estereo/localizar.py`, rechazar con < 15 % de píxeles
      válidos y calcular la MAD (eliminó 24 coordenadas falsas detrás de ramas sin perder mediciones buenas). Antes
      de decidir el tamaño conocido: grabar 2–3 casos con hoja delante y limón visible (`grabar.sh`) y correr
      `herramientas/comparar_profundidad.py`.
   5. **Tiempos:** saltear el intento con +2 cm en limones altos (> 58 cm) para ahorrar ~20–30 s de plan.
   6. Probar en el robot: seta suelta sin `r`, alertas 0.12.0 (cada ultrasonido, bumper, seta, IMU > 25°) y el modo
      Recolector con 2–3 limones a la altura buena. Adaptar `base_sim` y el teleop 25 (esperan `r`).
   7. **Varios limones en Recolección** (elegir la parada sin perder de vista a los demás) y **rumbo al volver al cero**
      (~4°).
   8. **Firmware del brazo para la demo:** micro-ROS (app) o serie (`recolectar.py`, banderín, RODEAR): decidir.
   9. Push de `recolector_de_frutas`, `vision_estereo` y `pruebas-esp32` cuando el usuario lo pida (`/verificar-robot` antes).
   10. Después de la demo: segundo revisor de código (Gemini CLI en solo lectura, no Antigravity) si hace falta.
000. **Plan hasta la demo del 27/11** (17/11; robot = usuario, software = Claude en paralelo, probado en Gazebo):
   | Días | Robot | Software |
   |---|---|---|
   | 18–19/11 | ~~Seguridad con los motores (00a d)~~ ✓; `cosechar N` y canasta ✓ | BUSCAR y RODEAR programados (sin probar) |
   | 20–21/11 | ~~Medir `banderin.json`; probar BUSCAR, RODEAR~~ → se usó en la app Arturito: base + cosecha juntas ✓ (1 limón; 1 de 2) | ~~Misión ROS (00a e) en Gazebo~~: navegación con banderín e hilera hecha (19/11, 15/18 paradas) |
   | 22–23/11 | Recolección en las 4 paradas | Misión ROS (00a e) con los estados de S3; nodo `seguridad` aparte (S2) |
   | 24–25/11 | ~~WROOM al env `ros`~~ (20/11); probar la misión ROS | Rosbag por misión (S5), GPS en el registro, estado y alarmas en `teleop_web.py` (S6) |
   | 26/11 | Ensayo general y video de respaldo | Ajustes |
   - **Recortado:** hilera (`recorrido.py`), EKF, app nueva, métricas detalladas, madurez por tamaño, celular como
     sensor. H8 (luz y buzzer) solo si sobra un día y hay piezas.
   - **Plan B:** si la misión ROS no llega, demostrar con `recolectar.py` y presentar la misión ROS como en curso.
   - **Manual v1.1 (19/11):** subir `docs/manual/manual.pdf` a Drive; actualizar el capítulo de la demo (`11b_demo.tex`) y el
     de estado después de probar BUSCAR/RODEAR y si la misión ROS llega.
   - **S3 sin sesión (19/11 tarde):** con 12 V apagados, reset (`esptool --after watchdog-reset chip-id`) y relanzar el agente.
   - **Riesgo:** los cortes del USB de la S3 (la base se desarma; 3 el 18/11). Falta saber si el 27/11 hay además informe (E7/E8).
00a. **(Con a, b y d se cubre N3 de la guía.)** **Navegación y recolección autónoma (13/11, en `pruebas-esp32`; detalle en su `notas/PENDIENTES.md`), en orden:**
   a) **BUSCAR:** programado el 19/11 (`ir_a_parada.py --banderin --buscar`, gira de a 30°), sin probar en el robot;
      falta medir `27/banderin.json`, que `recolectar.py` lo use y el esquive si no aparece en 360°.
   b) **RODEAR:** marcas 1–3 pegadas; `--rodear N` / `recolectar.py --paradas N` programados, sin probar en el robot.
   c) ~~**Soltar el limón**~~ (18/11): canasta sobre la tapa, `soltar` 28–30 s ida y vuelta. Falta probar el ajuste
      fino en una cosecha y base + cosecha juntas.
   d) ~~**Seguridad con los motores**~~ (18/11): HC-SR04 del medio, bumpers, seta y vuelco OK. Quedan los cortes del USB (16).
   e) **Llevarlo a la misión ROS** (`ros2_ws/src/mision`). **Gazebo hecho el 19/11** (`navegacion.py`, demo afuera
      con banderín e hilera de arbolitos; ver ESTADO). Sigue: (1) volver a medir el banderín desde ~1,2 m antes de la
      parada 1 (las 3 paradas que no cumplen: sesgo de ~2 % del detector desde 2,8 m); (2) en la Pi: `nodo_banderin`
      con la TF de navegación real y medir `hilera_arboles.json`; (3) opcional: ruido de odometría en la sim. Mandar texto por `/brazo/comando` al
      firmware 20 (no entiende `/brazo/joint_cmd`) con la WROOM en el env `ros`; los giros con `movimiento.py` / el
      giróscopo o `robot_localization` con `/odom` + IMU; el GPS (±20 m) solo para la rúbrica.
000b. **Brazo: NO flashear `firmware/brazo`** (el binario `ros` de `d3644c8` en `~/firmware/brazo` de la Pi está viejo).
   Desde el 11/11 la WROOM tiene `pruebas-esp32/20-brazo-coordinado` (desde el 20/11 env `ros`, micro-ROS, fuente `750ba4c`; el serie en `brazo20_serie_20261119.bin`; pinza RDS3218 500/1200) (franja, caja, homing 3/6/3, pinza y
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
0b. **Alimentación de la Pi:** el 12/11 la prueba de 1 h con el power bank dio OK, pero el 21/11, con la app
   (visión v4 + puente), se reiniciaba por bajo voltaje; con la fuente oficial de 27 W, `0x0`. Ver 0000.6.
1. Potencia v0.6 (`docs/CONEXIONES.md`): el fusible de 20 A y la seta (2 bloques NC) ya están: falta el portafusible; cambiar el Deans de la LiPo por XT60
   (sin capacitores en el bus desde el 19/10). Armar el divisor
   100 k / 30 k antes de conectar la LiPo. Prueba integrada mínima: lista en `CONEXIONES.md`.
2. Cablear según `docs/CONEXIONES.md` v0.6 (LiPo → fusible 20 A → seta → selector WEG → bus 12 V → motores; power bank → Pi → ESP32 por USB; GND común) y su lista
   "Antes de conectar". Base con ruedas en el aire: hecha el 20/10. **13/11: env `ros` con IMU, HC-SR04,
   bumpers y seta OK en ROS, y odometría en el piso medida (recto < 1 %).** Seguridad con motores OK (18/11). Falta: parada real por watchdog, corriente
   con peso; confirmar si el prisionero de la rueda derecha se arregló y el falso contacto del encoder izquierdo.
   Armar las placas según `docs/html/placa_s3.html` y `docs/html/placa_wroom.html` (orden de armado y prueba en cada página); en la S3,
   antes medir la tira roja (V) de la Freenove y probar si sus LEDs cargan los pines de los bumpers y la seta.
2b. **Tarea VA de R2 (si no se entregó):** corregir en Colab §6.1 (16 de 20, no 15), volver a poner "Autor: FB",
   §11 (mismo limonero, una foto repetida) y §5.2 (≈ 1,0). Detalle en la bitácora 11/11.
2c. **Detector:** desde el 20/11 el **v4** (comparado con el v3 en la bitácora de `pruebas-esp32`). Del v3 faltaba compararlo con la v2 en cifras
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
12. Recorrido autónomo por hilera (`recorrido.py`) en el robot real: sin probar; la demo (19/11) es afuera con un
   banderín y una hilera de arbolitos, con `navegacion.py` (00a e). El giróscopo ya se calibra solo al arrancar (13/11).
13. Red directa celular ↔ Pi para el piso y la demo afuera (datos compartidos del celular o red propia de la Pi): sin
   Wi-Fi de FIUNA no hay Tailscale directo garantizado, y por el relay de São Paulo el joystick tiene lag.
14. Encoder de J2: confirmar con `e` que cuenta (el 26/10 no contaba; después del arreglo del usuario no se midió).
15. Finales de carrera del brazo: montar 3 microinterruptores (GPIO 32/33/27), medir `HOME_Q` con `z` + `e`, signo de
   `HOME_RPM` y `HOME_J23_VERIFICADO = true`; J2/J3 cerca de la pose de cero, homing de J3 antes que J2.
16. Enlace de la base: `pings_fallidos` y `cortes` suben (82 y 4 en ~1 h; 3 cortes el 18/11 al apretar la seta y mover
   la base; el brazo, 0): mirar `~/logs/agente_base.log`.
