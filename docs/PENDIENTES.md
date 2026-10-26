# Próximos pasos

Movido de `CLAUDE.md` §7 el 22/10. Fecha límite: 9/11/2026. Estado: `ESTADO.md`.

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
1. Potencia v0.6 (`docs/CONEXIONES.md`): el fusible de 20 A y la seta (2 bloques NC) ya están: falta el portafusible; cambiar el Deans de la LiPo por XT60
   (sin capacitores en el bus desde el 19/10). Armar el divisor
   100 k / 30 k antes de conectar la LiPo. Prueba integrada mínima: lista en `CONEXIONES.md`.
2. Cablear según `docs/CONEXIONES.md` v0.6 (LiPo → fusible 20 A → seta → selector WEG → bus 12 V → motores; power bank → Pi → ESP32 por USB; GND común) y su lista
   "Antes de conectar". Base con ruedas en el aire: hecha el 20/10. Falta, en el piso y con la IMU, el HC-SR04 del
   frente y el env `ros`: odometría contra cinta (radio, trocha, cuentas), parada real por watchdog y corriente con
   peso; antes, el prisionero de la rueda derecha. Probar sensores en ROS (hoy nada probado con periféricos).
   Armar las placas según `docs/html/placa_s3.html` y `docs/html/placa_wroom.html` (orden de armado y prueba en cada página); en la S3,
   antes medir la tira roja (V) de la Freenove y probar si sus LEDs cargan los pines de los bumpers y la seta.
3. Visión: prueba de campo del limón (§5) y con las NoIR al sol; B3 (cosechable / no cosechable / obstáculo):
   hoy el detector tiene una sola clase. Recalibrar solo si el soporte de cámaras se mueve o cambia.
4. Brazo: **flasheado el 26/10** (`3d94f4c`, jog J2/J3 50 %); con `teleop_web.py` medir los signos de J2/J3 (`ENC_INVERTIDO`/`MOTOR_INVERTIDO`, hoy sin medir) y si 50 % alcanza para levantar el brazo; armar el shield y la perforada
   de distribución según `docs/html/placa_wroom.html`; medir que los encoders tengan su pull-up (A/B en 0 o 3,3 V, nunca a mitad;
   si falta, 10 k a 3V3). El motor de J1 en J2 ya se probó (levantó el brazo, 17/10); con los motores nuevos, pasos 0-3 de
   `pruebas-esp32/10` (hoy J2/J3 tienen los parámetros de J1 llevados a 58 rpm). Medir lo
   `MEDIR`. Falta sostener J2/J3 contra la gravedad (no se autobloquean) y definir los límites articulares reales (hoy provisorios: q1 45°/225°, q2 −25…135°, q3 ±50°); el balancín rojo mide 60 mm (`L30`, 18/10): con él, el reposo y `HOME_Q` = (45°, −25°, −50°) del firmware tienen que caer en γ₄ = q2 + q3 − 90° entre −112° y −30°; hoy `HOME_Q` da −165° (no cierra: MEDIR).
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
11. Herramientas: decidir si `/pi-sync` prueba también el Wi-Fi FIUNA (172.16.240.92) cuando no responden Tailscale
   ni la LAN (sin verificar que esa IP siga valiendo).
12. Recorrido autónomo en el robot real: calibrar antes el sesgo del giróscopo (supone arrancar en el centro del pasillo).
