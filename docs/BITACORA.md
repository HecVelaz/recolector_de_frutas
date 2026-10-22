# Bitácora

Detalle de lo hecho, en orden. El resumen vigente está en `CLAUDE.md`.

## 2026-09-27

### Entorno
- Node.js v24.21.0 instalado con nvm (sin sudo). Enlaces de `node`, `npm` y `npx` en `~/.local/bin` para que los
  hooks que corren con `/bin/sh` los encuentren (apuntan a la versión v24.21.0 de nvm).
- Codex CLI 0.156.1 con sesión de ChatGPT de la cuenta **pjotazu@fiuna.edu.py** (se intentó entrar con otra cuenta;
  el navegador reutilizaba esa sesión y se decidió seguir con ella).
- Barra de estado de Claude Code: `~/.claude/statusline-command.sh` (modelo, % de contexto, tokens).

### Documentación
- `docs/INDICE.md`: una línea por documento (.txt/.md). `docs/ARQUITECTURA.md`: objetivo mínimo (moverse + YOLO +
  estéreo + agarrar), reparto de hardware, nodos ROS 2, control en cascada, máquina de estados, plan en 5 etapas.
- `docs/Componentes_inventario.md`: planilla de compras convertida desde `Componentes para R1 y R2.xlsx`.
- `docs/CONEXIONES.md` y `docs/conexiones.html`: pines de las dos placas y de la Pi, alimentación, lista de
  verificación. Página publicada: https://claude.ai/artifact/8eJqFaVCGBz39B3EGmGByN (privada).
- Correcciones del usuario incorporadas: el limón fue aprobado por el profesor; las medidas del brazo cambiaron
  con las entregas (vigentes las de la E4); el diseño es RRR (opción 6 de la tabla R1); el motor DC 895 de 2700 rpm
  fue una compra errónea (se usa el 36GP-555 de 160 rpm en J1).

### Revisiones de Codex (solo lectura)
- Proyecto y arquitectura: acordó la división por subsistema; señaló el riesgo de color de las cámaras NoIR, el
  L298N, el control en cascada (la E5 identifica velocidad, no posición) y requisitos de R1 sin cubrir.
- Firmware del brazo: 10 hallazgos aplicados (concurrencia de marcas de tiempo, parada sin retroceso, límites de
  puesta en marcha, homing, watchdog de tareas, servos sin pulsos al arrancar).
- Firmware de la base: 9 aplicados (IMU sin datos, bumper, ultrasonido sin eco, tope por cercanía que no se acumula
  con la rampa, rampa a cero, watchdog que anula, `cal` solo detenido).
- Capa micro-ROS: 10 aplicados, 1 verificado (MTU 512 B × historial 4 = 2048 B por mensaje reliable).

### Grafos (graphify, `graphify-out/`, fuera de git)
- Primero solo de `docs/` (259 nodos). Después del repo completo: 1009 nodos, 1824 aristas, 54 comunidades,
  996 nodos conectados; ~269 mil tokens de extracción de documentos. Ignorados por `.graphifyignore` (raíz) y
  `docs/.graphifyignore`.
- El grafo marcó una arista inferida incorrecta: "NodoIK implementa B7"; no hay planificador sin colisiones.

### Firmware y ROS 2
- Brazo empezó como `~/pruebas-esp32/09-brazo-control` (commits `cd8b420`, `f408f4e`) y se movió a este repo
  (`2a5fc54` allá). Las pruebas en la PC detectaron que sin feedforward de zona muerta cerca del objetivo el motor
  se clavaba a ~1,4°; se corrigió.
- Commits en este repo:
  - `664fb94` repo: documentación y firmware del brazo
  - `69d81c6` nodo `brazo_ik` (cinemática inversa de la E4)
  - `b3d91bd` diagrama de conexiones
  - `35ef366` firmware de la base; `658f6cc` revisión de Codex
  - `04e6bdf` capa micro-ROS; `ec7c70a` revisión de Codex
  - `99231c5` tópicos al día en ARQUITECTURA y README de `brazo_ik`
- Al probar `brazo_ik` a mano, `kill` del `ros2 run` deja vivo el proceso Python del nodo (quedaron 3 nodos
  respondiendo duplicado): cerrarlo con `pkill -f lib/brazo_ik/nodo_ik`.
- Prueba del nodo `brazo_ik` en la notebook: ejemplo de la E4 → q = (0,00°, 45,00°, 0,00°), error 5e-13 mm; punto
  lejano, q1 = 108° y marco equivocado rechazados con su motivo.
- Compilación: brazo `esp32dev` y `ros`, base `esp32s3` y `ros`, sin warnings. micro-ROS: RAM 15,3 % / flash 29,6 %
  (brazo), RAM 22,7 % / flash 7,3 % (base); primera compilación ~8 min cada una.

### Comandos usados
```bash
PIO=~/.platformio/penv/bin/pio
$PIO test -e native            # en firmware/brazo y firmware/base
$PIO run -e esp32dev|esp32s3   # modo serial
$PIO run -e ros                # micro-ROS
cd ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install && colcon test
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0   # base (source ~/microros_ws/install/local_setup.bash)
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0   # brazo
codex exec --skip-git-repo-check -s read-only "<prompt con el código pegado>" < /dev/null > salida.txt
```

## 2026-09-28 / 29

### Hardware y documentación
- Tracción confirmada: 42GM-895H planetario 189:1, encoder Hall 11 PPR a 5 V (`cuentasPorVuelta` = 8316; A/B bajar a
  3,3 V). Pinza con 2 servos RDS3218 (agarre + tracción + giro aprobado por el profesor). IMU MPU-6500.
- Base real de la R2 E3: caja en T (adelante 40 × 23 cm con el brazo, atrás 34 × 17 cm con las ruedas), ruedas
  inflables de 150 mm, 3 bumpers. Batería 10S de 36 V (30-42 V): buck 36 → 12 V para motores, divisor 120 k / 8,2 k.
- `docs` reorganizado: `TPF R1/`, `TPF R2/`, `fotos/`; entregas nuevas (R2 E2, R2 E3, R1 E5) convertidas a `.md`.

### Software
- `mision` (FSM de la demo + TF cámara → brazo), revisada por Codex; llegada por posición (`joint_states` contra
  `joint_cmd`). `brazo_ik`: herramienta horizontal (brazo tipo uArm), `/brazo/objetivo` es el TCP.
- `EncoderPCNT`: sin interrupción, desenvuelve el contador por software (salto de 32 000 corregido), revisado por Codex.
- `firmware/base`: ruedas de 150 mm, trocha 0,40, 3 bumpers, batería 10S.
- `simulacion` (Gazebo Harmonic): hilera con medidas de R1, base real, brazo con `brazo_sim`, `limones_sim`, cámaras y
  cadena real (`vision:=yolo`, parcial: YOLO no reconoce limones sintéticos). Con `mision:=true`: 12 de 12 limones.

### Lecciones
- La simulación veía por la LAN los ESP32 reales de la Pi (el brazo real ARMADO): ahora va aislada con
  `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`. Cualquier nodo en la LAN puede comandar el robot real.
- En Gazebo: servidores y nodos quedan vivos si se corta solo el launch (limpiar siempre); la base se deslizaba por
  los impulsos del brazo movido por velocidad (masas del brazo al 5 %); el estéreo solo localiza con u >= 271 px y el
  brazo en reposo no debe tapar las cámaras.

### Comandos
```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash
ros2 launch simulacion sim.launch.py mision:=true            # otra terminal: export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 run teleop_twist_keyboard teleop_twist_keyboard          # frenar con el eje sobre las franjas blancas
```

## 2026-09-29 (noche): simulación, brazo atrás, etapa 5 y recorrido autónomo

### Cambios
- **Temblor del brazo en Gazebo**: `JointPositionController` con `use_velocity_commands` va a la consigna en un paso
  de física (±1 rad/s y frenar, 50 veces por segundo). Ahora `JointController` por velocidad: `brazo_sim` manda la del
  perfil + 5/s por el error. Además `/joint_states` salía a 1 kHz y ahogaba a los nodos de Python: ahora 50 Hz.
- **Brazo atrás a la izquierda, sobre el eje de tracción** (pedido del usuario), a 6 cm del costado (y = 0,11).
  Mástil de cámaras adelante a la derecha (0,255; -0,17), cámara a 0,85 m mirando 94° a la izquierda y 28° abajo:
  buscado para que los 3 limones de cada árbol se vean (u >= 271) y se alcancen (J1 ±75°) desde la misma parada. Del
  lado izquierdo quedaba muy cerca de la fila y ningún ángulo servía. Mástil y cámaras dibujados.
- **Reposo del brazo q = (75°, 110°, -30°)**, girado a la izquierda: el de la derecha (-75°) atravesaba el mástil al
  ir a cada limón (2 mm del eje). Buscado simulando los recorridos a los 12 limones (≥ 33 cm del mástil).
- **Etapa 5**: `base_sim` imita la S3 (`SeguridadBase.cpp` portada, arranca DESARMADA, watchdog 300 ms) y publica
  `/range/*`, `/bumpers`, `/battery`, `/base/estado`. HC-SR04 como `gpu_lidar` de 5 rayos horizontales (con rayos
  hacia abajo veía el piso a 1,07 m). Bumpers: planchas con resorte en prismáticas (el sensor de contacto de Gazebo
  no informaba nada en links fijos). Teleop: `armar` por `/base/comando` y `repeat_rate:=10.0`.
- **HC-SR04 los 3 en el frente** (central recto, esquinas ±15°): mirando a los costados, un obstáculo corrido a un
  lado del pasillo no lo veía nadie hasta chocarlo con la esquina. **Vale para el robot real** (ubicación MEDIR).
- **Recorrido autónomo** (`mision/recorrido.py`, `autonomo:=true`): avanza de a 10 cm, frena y deja mirar; si la
  misión ve un limón fuera de alcance, se arrima lo mínimo (`desplazamiento_para_alcanzar`); si un eco cae dentro
  del ancho del robot, esquiva por el lado con lugar (peor caso del cono de ±7,5°) al carril y = ±0,25 m, pasa y
  vuelve al centro. La misión solo junta muestras con la base quieta (`base_quieta`).
- Obstáculos del mundo corridos a un costado (y = 0,25 / -0,28 / 0,25): centrados no dejaban pasar por ningún lado
  entre las copas (a 0,48 m del centro, robot de 0,445 m).

### Lecciones
- El usuario manejando con teclado no clavaba las marcas (±2 cm): la parada la tiene que decidir la visión.
- Probar en paralelo sin tocar la simulación del usuario: `ROS_DOMAIN_ID=42 GZ_PARTITION=prueba_claude`.
- **Resultado del recorrido autónomo**: 12 de 12 limones sin teleop, sin tocar obstáculos (corridas: 5/12 por la
  odometría de ruedas desviada 13 cm → rumbo del giróscopo; 8/12 por pasar el árbol 3 al volver del balde →
  retroceso con tope hacia limones en la zona ciega; 11/12 por terminar el corrimiento torcido → exigir rumbo < 3°).
  `limones_sim` hace de YOLO (`/yolo/detecciones`, también en movimiento) y de estéreo (posición solo quieto). El cono
  se sacó del mundo a pedido del usuario.
- Error propio: dejé viva una simulación de prueba y la siguiente se mezcló en la misma partición (15 min perdidos):
  cerrar siempre las de `GZ_PARTITION=prueba_claude` al terminar.

## 2026-09-29/30 (noche): batería, buck, GPS en la Pi y TRIG separados

### Cambios
- **Batería 10S (36 V)**: opinión propia y de Codex. Sirve (158 Wh sobran para 45 min); lo difícil es bajar a 12 V
  con corriente. Codex encontró: servos fuera de la seta, INA219 no aguanta 42 V, corriente del BMS sin documentar.
- **Buck disponibles** (`docs/fotos/bucks/`): solo el buck 1 (10,5-60 V, 12 A) aguanta la batería; los 2, 3 (×2) y
  4 llegan a 32-40 V. Esquema: buck 1-A → motores (Schottky, 2200 µF, TVS, relé automotriz de la seta del lado de
  12 V, servos adentro); otro buck 1 (falta comprar) → lógica, buck 2 → Pi, buck 3 → servos. `CONEXIONES.md` v0.3 y
  `conexiones.html` al día (el HTML seguía con 12 V, 4 bumpers y 36GP-555 en la tracción).
- **¿Alcanza Pi 5 + 2 ESP32?** Sí (Claude y Codex). La reserva de GPIO está en la Pi. HAT de la Pi: borneras pasivas.
- **GPS a la Pi** (UART GPIO 14/15, `nmea_navsat_driver` → `/gps/fix`): libera 41/42 de la S3 para un TRIG por
  HC-SR04 (los 3 miran al frente y con TRIG común se pisaban). Disparo de a uno cada 40 ms (~8 Hz por sensor).
  Firmware compila sin warnings, 20 pruebas; revisado por Codex sin hallazgos. En la Pi: UART0 y driver instalados.
- `pins.h` de la base decía divisor 100 k / 27 k en un comentario (el valor del firmware ya era 120 k / 8,2 k).

### Lecciones
- El vigilante de Codex no puede buscar "tokens used" con `grep -q`: aparece en CLAUDE.md si Codex lo lee. Usar `grep -qx`.
- Los comandos para la Pi el usuario los corre en la propia Pi: no anteponer `ssh`.

## 2026-09-30 (tarde): cámaras en el soporte nuevo, cinta CSI dañada

### Cambios
- Cámaras pasadas a otro soporte: después, una sola se detectaba o transmitía. Pruebas, cada una con la Pi apagada y
  reiniciada: al intercambiar las cintas la falla pasó al otro puerto; con la cinta mala y una cámara sola, falló
  igual; con la buena, la misma cámara y el mismo puerto andan. **Una cinta está dañada**: cámaras y puertos, bien.
- Síntomas de la cinta mala: sin detección, `Failed to write reg 0x0100` + `stream on failed`, o arranca y a los
  segundos `Camera frontend has timed out`.
- Vista web de las dos cámaras en crudo (página en el 8081, `web_video_server` en el 8080) y `~/probar_camaras.sh`
  en la Pi (detección + 10 s de transmisión por cámara; la parte de transmitir sin probar).
- `estereo.launch.py` (disparidad 0-128) solo mide desde 0,84 m con la v1: para objetos cercanos, `limon.launch.py`.
- `docs/RESUMEN_PROYECTO.md`: resumen del proceso completo, en 35 puntos.

### Lecciones
- Las cámaras se detectan solo al arrancar: reconectar en caliente no sirve (y puede dañarlas).
- `pkill -f "[p]atrón"` por ssh igual se mata a sí mismo si el patrón aparece más adelante en la misma línea de
  comando (cortó la sesión dos veces): limpiar en un ssh aparte.
- `sudo reboot` de la Pi lo bloquea el modo automático: pedírselo al usuario.

## 2026-10-05: docs unificados, conexionado v0.4, compras y plan al 9/11
- `pruebas-esp32/docs` era una copia vieja de `docs/`: se pasó lo que faltaba (sin pisar nada), la copia quedó como
  `pruebas-esp32/docs_viejo` y `pruebas-esp32/docs` ahora es un enlace a `recolector_de_frutas/docs`.
- J2/J3 cambian a 36-555 de 98 rpm con IBT-2 y correa (J2 no levantaba el brazo con el 5840; J3 tambaleaba).
  Llegan entre el 19 y el 29/10.
- Conexionado v0.4 (`CONEXIONES.md`, `conexiones.html`): WROOM con 3 IBT-2 (J2 25/26, J3 16/17, EN común 23, FC J3
  en 27, libre 13); dos baterías (10S → motores; LiPo Zeee 3S 8000 mAh → lógica, sin segundo buck 1); cables de cada
  motor; autonomía estimada ~3,4 h de cosecha (10S) y ~4,7 h de lógica (LiPo). `COMPRAS.md` con casillas.
- `L298N.cpp`: el duty se escribe después de `ledcAttachPin()` (en el core 2.0.x lo pisaba). 17 pruebas OK.
- Cinta CSI reemplazada (falta verificar las dos cámaras). Avance estimado ~45 %; plan por semanas en CLAUDE.md §5.

## 2026-10-05 (noche): placas de las ESP32
- Placa de la S3: va sobre la expansión Freenove (Breakout Board for ESP32/ESP32-S3), que trae bornera y tira G-V-S
  por pin, LEDs por GPIO y entrada de 7-12 V. Los componentes van en dos perforadas chicas, una sobre cada fila de
  borneras: arriba los ECHO (1 k en serie, 2 k a GND), el bumper del frente y las salidas de los encoders (20 k a
  GND); abajo bumpers, seta, reserva 40, EN 38 (10 k a GND) y la batería (120 k / 8,2 k / 100 nF, zona de 36 V).
  El resto (IBT-2, IMU, TRIG, 5V, 3V3) va directo a las borneras.
- Placa de la WROOM: es una HW-394 de 30 pines (USB-C, CH340). No se compra expansión: perforada de 7 × 9 cm con
  zócalo de 2 × 15, 3 IBT-2 (conector de 8 en el orden del módulo), 3 encoders a 3V3, 3 finales de carrera (100 nF
  y 10 k a 3V3) y 2 servos con riel de 6 V del buck 3 en alambre grueso. Pines v0.4, todavía no en `pins.h`.
- `docs/placa_s3.html` y `docs/placa_wroom.html` (publicadas, privadas): vista de cableado (ESP32 al centro, un cable
  de color por pin, componentes sobre el cable, filtros por grupo), montaje físico, tabla y orden de armado y prueba.
- Pinouts de las dos placas en `docs/fotos/` (coinciden con los planos); el de la S3 venía en AVIF con extensión
  `.png` y se pasó a PNG. `COMPRAS.md` con los materiales de las placas (~12 × 10 k, ~10 × 100 nF).

### Lecciones
- El voltímetro LED de 2 hilos no reemplaza al salvalipo: no avisa, mide el total y no cada celda, y consume siempre.
- En la DevKitC-1 v1.1 el LED RGB está en el GPIO 38 (en la base es el EN de la tracción): verificar en la placa.
- Firefox de snap no lee `/tmp`: para capturas sin ventana, usar una carpeta temporal en el home y borrarla.

## 2026-10-05 (noche): pines v0.4 en el firmware del brazo
- `firmware/brazo/include/pins.h`: J1 21/22, J2 25/26, J3 16/17, EN común 23, encoders 34/35, 32/33 y 18/19
  (SCX-555 a 3V3), servos 4 y 14, finales de carrera 36, 39 y 27; libre el 13.
- `main.cpp`: J2 y J3 pasan del L298N al BTS7960 (sin L298N en `platformio.ini`). Con el EN compartido, la rueda
  libre es de las tres a la vez: si una se mueve, las que están libres reciben duty 0 (frenadas); así los tres
  drivers coinciden siempre en habilitado o no. FC de J3 en el 27 con pull-up interno (36/39 siguen con externo).
- `brazo_config.h`: J2/J3 con 5248 cuentas (16 × 4 × 82) y los parámetros de J1 llevados a 98 rpm (K × 98/160,
  Kp y Ki × 160/98), duty máx 40 %, jog 30 %; `relacion` 1 y signos sin medir (todo MEDIR).
- Prueba `test_manual_no_empuja_afuera_del_limite`: con 45 % y la relación provisoria de 1, J3 pasaba de largo el
  margen de 5° (el motor nuevo gira más rápido que el 5840); ahora usa `JOG_DUTY_MAX`. 17 pruebas OK; compila
  `esp32dev` y `ros` sin warnings. Sin probar en la placa.
- README del brazo, `CONEXIONES.md`, `conexiones.html`, `placa_wroom.html` y CLAUDE.md al día.

### Lecciones
- Un EN compartido entre varios BTS7960 obliga a decidir la rueda libre en conjunto: si un driver hace `coast()`
  mientras otro sigue activo, el segundo cree que sigue habilitado y no vuelve a subir el EN.

## 2026-10-05 (noche): informes de R2 corregidos
- E2 (`Entrega2.md` y `.ipynb`): MPU-6050 → MPU-6500, ROS 2 Humble → Jazzy, Ubuntu 22.04.5 → 24.04.5 y la
  referencia [3] a la documentación de Jazzy.
- E3 (`Entrega3.md` y `.ipynb`): "4 drivers" → 5 IBT-2 (2 de tracción y 3 del brazo, uno por articulación), según
  el conexionado v0.4. La tabla ya decía 3 drivers del brazo: el pendiente anotado (2) era de antes del cambio de
  J2/J3. Las fotos de la E3 siguen mostrando el montaje de ese momento.
- Pendiente quitado de CLAUDE.md y marcado en `INDICE.md`.

### Lecciones
- En los `.ipynb`, reemplazar las frases sobre el texto del archivo (probando también la forma con escapes
  `\uXXXX`) en vez de cargar y volver a guardar el JSON: así el diff es de una línea y no reformatea todo.

## 2026-10-06: revisión de conexiones de Codex (S3, WROOM y Pi) y arreglos sin costo
- Codex (solo lectura) revisó `CONEXIONES.md`, `placa_s3.html`, `placa_wroom.html` y los dos `pins.h`: sin pines de
  arranque, flash ni USB mal usados; divisores bien (42 V → 2,69 V; 5 V → 3,33 V). Hallazgos en seta, protecciones
  y supuestos sin medir.
- **Sin presupuesto para compras** (dicho por el usuario): se aplicó solo lo que no cuesta.
- `mision`: `al_estado_base()` en `fsm.py`; con `SETA` en `/base/estado` manda `desarmar` al brazo y pasa a FALLA
  (antes la WROOM seguía armada y al soltar la seta el brazo arrancaba con el error acumulado). `nodo_mision`
  suscribe `/base/estado` siempre (antes solo con `autonomo`). 3 pruebas nuevas: 30 OK.
- `CONEXIONES.md`: bus de lógica = LiPo directa (no "buck 1-B"); buck 2 desde la LiPo; 1N4007 en la bobina del relé,
  fusible ≥ 58 V DC e interruptor ≥ 60 V DC en el esquema; seta y brazo a mano (mandar `desarmar`); margen del TVS
  y del capacitor de 25 V; pull-ups de 34/35 (los da la SCX-555) contra 36/39 (obligatorios); en "Antes de
  conectar": salida real de los encoders de tracción, entrada de los IBT-2 a 3,3 V (74HC244), LED RGB en el 38,
  servo del GPIO 14, LEDs de la Freenove sobre GPIO 1/encoders/I²C y el divisor con la lógica apagada.
- Quedan sin resolver por costo: freno de J2/J3 (contrapeso o resorte con lo que haya), corte por subtensión de la
  LiPo (INA219 y alarma siguen "a comprar"), protección de corriente por motor.

### Lecciones
- Vigilante de Codex: buscar `tokens used` como línea exacta (`grep -qx`); CLAUDE.md contiene ese texto y Codex lo
  imprime al leerlo, así que el `grep -q` lo cortó a mitad de camino.

## 2026-10-06: J2/J3 pasan a 58 rpm; sin INA219 ni salvalipo
- J2/J3: 36-555 de 58 rpm (139:1) en vez del de 98 rpm (82:1). Tabla del vendedor (`fotos/motor_j2/`): 22 kgf·cm
  nominal y 75 trabado (contra 12 y 46). `brazo_config.h`: 8896 cuentas (16 × 4 × 139), parámetros de J1 llevados a
  58 rpm (K 0,57; PI 1,82 y 13,2; atasco 0,6 rpm), todo MEDIR. 17 pruebas OK; compilan `esp32dev` y `ros` sin warnings.
- Sin INA219 ni salvalipo: solo pruebas vigiladas de ≤ 30 min con el indicador de barras de la LiPo.
- Correa de J2 y J3: GT2 5:1 (`relacion` 5) con poleas 20 → 100 y correa cerrada de 240 mm: ~54 mm entre centros
  (18 → 90 pediría ~62 mm). Velocidad máxima de la articulación: 58 / 5 ≈ 11,6 rpm (70 °/s).

## 2026-10-12

### Brazo: shield de borneras y pines v0.5
- La HW-394 va en un shield de borneras de 30 pines (foto en `fotos/esp32 wroom 32D/`): sale la perforada de 7 × 9 con
  zócalo; queda una perforada chica de distribución (rieles 5 V, 3,3 V, EN, GND y 6 V), porque el shield trae un solo VIN y un solo 3V3.
- Pines v0.5: encoder de J2 de 32/33 a 36/39 (VP/VN) y finales de carrera de J1/J2 de 36/39 a 32/33. Los encoders SCX-555
  traen pull-up de 5,1 kΩ y los finales de carrera usan el interno: la única resistencia de la WROOM es el pull-down
  de 10 kΩ del EN (23). Sin 100 nF en los finales de carrera: el homing ya pide 3 lecturas seguidas (`HOME_FC_LECTURAS`).
- `pins.h`, `CONEXIONES.md`, `conexiones.html` y `placa_wroom.html` (plano nuevo del shield y la distribución). 17 pruebas
  OK; compilan `esp32dev` y `ros` sin warnings. Falta reflashear el brazo y probar en la placa.

## 2026-10-13

### Base: la S3 sin capacitores
- Como en la WROOM: salen los 100 nF de los 3 bumpers, la seta, la reserva (40) y la batería. Bumpers, seta y reserva
  van directo a su bornera con el pull-up interno; la perforada de abajo queda con el EN y la batería.
- No se pueden sacar: divisores 1 k / 2 k de los ECHO (5 V), 20 k de los encoders de tracción (salen a 5 V y la hoja
  pide Vcc 5-24 V: no se pueden alimentar a 3,3 V), 10 k del EN (38) y el divisor 100 k / 27 k. Quedan 14 resistencias.
- Si un bumper o la seta disparan sin tocarlos, o la lectura de batería salta: 100 nF de ese pin a GND.
- `placa_s3.html`, `seta.html` (4 cables en vez de 5), `potencia.html`, `conexiones.html`, `CONEXIONES.md`. Sin cambios de firmware.

## 2026-10-14

### Revisión de Codex de lo cambiado desde el 08/10 (potencia, seta, brazo v0.5, S3 sin capacitores)
- Pines v0.5 bien y coherentes entre `CONEXIONES.md`, los HTML y los dos `pins.h`; sin strapping ni ADC2/Wi-Fi nuevos.
  Bien: cortar el +, fusible antes de los mandos, bloque B separado de los 12 V, pull-down de los EN, sacar los 100 nF.
- Hallazgos (límites de componentes sin presupuesto, no errores de conexión): la seta `10(6)A 400V~` no tiene corte
  DC garantizado (riesgo real: soldarse tras muchos cortes con carga); 2 BC10 en paralelo no suman 20 A al abrir;
  el fusible de 20 A solo protege contra cortos (2 motores trabados = su nominal); al soltar la seta el brazo puede
  rearmarse antes de que llegue `desarmar`; no estañar cables bajo tornillo. El de la regeneración con la seta abierta
  se descartó: con el EN bajo, la fuerza contraelectromotriz no supera los 12 V.
- Decisión del usuario: está bien así, con pruebas acotadas y vigiladas. Reglas en "Antes de conectar" de
  `CONEXIONES.md`. HTML sin cambios.
- `docs/html/todo.html` (`armar_todo.py`): las 5 páginas en una, con cajas clickeables que llevan al detalle.

## 2026-10-17: Entrega 7 de R1 (diseño final y demo) y transmisión de J2/J3
- `docs/TPF R1/Entrega 7/`: `Entrega7.md` (con links de Drive) y `Entrega7.ipynb` (las imágenes locales van incrustadas
  en base64; se arma desde el `.md`). Diagramas draw.io en `Diagramas/`, fotos y pesos de las piezas en `Partes_del_brazo/`.
  Revisado con Codex y corregido (sus aclaraciones son las de esta entrada).
- **J2/J3 no usan correa: engranajes helicoidales 15 → 75 (5:1).** La correa GT2 5:1 es solo de J1. En el firmware la
  relación ya era 5: solo cambiaron comentarios (17 pruebas OK, compila sin warnings).
- Historia del 5840-31ZY (8 kgf·cm, descartado): con L298N no levantaba el brazo; con IBT-2 tampoco; con resorte subía
  pero oscilaba mucho, aunque las gráficas de la E6 parecían cumplir (no tomarlas como validación mecánica de J2/J3).
  El motor de J1 (36GP-555, 160 rpm) en J2 con los helicoidales **sí levantó el brazo** (prueba hecha). Por eso se
  compraron 2 × 36-555 de 58 rpm + 2 IBT-2 (llegan 19-29/10).
- Pinza pesada armada (dedos, mecanismo, soporte y los 2 servos): **246 g** (la E6 estimaba 322 g). Cotas estáticas con
  ese valor: J2 8,00 N·m, J3 3,45 N·m; disponible 22 kgf·cm × 5 = 10,8 N·m (nominal, sin pérdidas: cálculo, no ensayo).
- Los 2 servos RDS3218 probados por separado: funcionan. Impresora: Elegoo Neptune 4 (PLA-CF negro 1,75 mm); los demás
  parámetros de impresión no quedaron registrados. 17 piezas impresas = 1177 g.
- Homing: el final de carrera asigna un ángulo conocido (`HOME_Q`), no 0°; distinto de la marca de J1 a 90° (cero manual).
  Finales de carrera sin montar ni probar.

## 2026-10-17/18: grafo del repo, documentos al día y cuatro barras con el balancín de 60 mm
- **Grafo de graphify rehecho** (el anterior era del 27/09; `graphify-out/`, fuera de git) y usado para buscar
  inconsistencias. Corregidos: README del brazo (encoder J2 en 36/39, finales de carrera 32/33/27 sin 100 nF, 17
  pruebas), `conexiones.html` (encoder J2 en 32/33 y pull-ups externos que la v0.5 sacó; republicada con `todo.html`),
  "correa" para J2/J3 en `CONEXIONES.md`, `COMPRAS.md`, el manual y los HTML (son helicoidales 15 → 75), conteos de
  pruebas del README raíz y `ARQUITECTURA.md` a la v0.6 (J2/J3 no se autobloquean: el brazo cae al cortar; sin
  `supervisor_seguridad` en la Pi: la seguridad la deciden la S3 y `mision`). Las entregas no se tocan.
- Borrados: la librería `L298N` (sin uso desde la v0.4; queda en el historial y en `pruebas-esp32/08`) y `docs/llave.jpeg`.
- **Balancín rojo del cuatro barras: 60 mm** (medido por el usuario; la E4 tenía 40 y proponía 60 para que fuera
  Grashof). `L30 = 60` en `cinematica.py`. El cuatro barras cierra con γ₄ = q2 + q3 − 90° entre −111,95° y −29,64°
  (lo impone `MU_MIN` = 15°); con 40 mm era −129…0°. Las 2 pruebas del ejemplo de la E4 fijan 40 mm adentro.
- **Reposo provisorio q = (75°, 94°, −50°)**: el de antes (110°, −30°) daba γ₄ = −10° y no cierra con 60 mm. q3 = −50°
  es el borde de `Q3_LIM` (de la E4): revisar con los límites reales. Simulación autónoma sin ventana: **12 de 12**.
  Prueba nueva en `mision`: el reposo por defecto tiene que ser alcanzable.
- **J2 y J3 no son independientes**: los límites de cada una juntos dejan pasar γ₄ entre −165° y +95°, y con 60 mm solo
  cierra entre −112° y −30°. Achicar los límites individuales para cubrirlo dejaría al hombro con ~32° de recorrido.
  Firmware: `cuatroBarrasOk()` en `brazo_config.h`; `m` y `j` rechazan el objetivo (recortado como `irA()`) que lo
  saque del rango. Revisado por Codex y aplicado: se recorta solo el objetivo, no la posición de la otra; `j 2/3` se
  rechaza si la otra se mueve en `v`, `d` u homing; una falla en J2 o J3 detiene la otra; `home 2/3` bloqueados
  (`HOME_J23_VERIFICADO = false`) hasta medir `HOME_Q` (hoy γ₄ = −165°); `POSE_CERO` de J3 a −40° (provisoria,
  con `static_assert`); borde inferior −111,9° (−112° dejaba μ en 165,3°). Sin cubrir: el camino entre dos objetivos
  (perfiles distintos de J2 y J3) y `d`/`v`. `brazo_ik`: `test_limites_firmware.py` compara `Q*_LIM` y el rango de γ₄
  con `brazo_config.h`. Pruebas: firmware 18, `colcon` 53.
- **Reposo y cámaras** (cuenta con la geometría del urdf; mástil y cámara son MEDIR): en reposo solo la pinza entra en
  la imagen izquierda, a ~0,6 m de la lente y contra el borde izquierdo. Con la cámara real (f = 654 px) llega hasta
  u ≈ 200 px con el reposo nuevo (177 px con el viejo), un poco fuera de la zona ciega del estéreo (u < 163): puede
  tapar un limón en ese borde. Con la cámara simulada (f = 1076 px) queda en u < 122 px. Brazo al mástil en reposo:
  37 cm (33 cm el viejo). Los "17 cm de la vista" del 29/09 no se reproducen con este método.
- Prueba del LED RGB de la S3 armada en `pruebas-esp32/11-led-rgb-s3` (¿GPIO 48 o 38, el EN de la tracción?): el
  diagrama dice 38 en la DevKitC-1 v1.1 y la foto del clon no muestra la versión. Se prueba el 19/10.

## 2026-10-19
- LED RGB de la S3 (`pruebas-esp32/11-led-rgb-s3`): **está en el GPIO 48**. Solo el 48 en verde: parpadea; solo el 38:
  nada. En la primera prueba (48 y 38 alternados) también se veía rojo: el núcleo deja el canal RMT ruteado al 48, así
  que lo escrito "por el 38" también salía por el 48. Probar cada pin en un programa aparte. El EN de la tracción
  (38) queda sin conflicto; `pins.h` ya lo suponía en el 48.
- **Orden de la potencia cambiado (decisión del grupo):** LiPo → XT60 → fusible 20 A → **seta (bloque A) → selector WEG**
  → bornera +12 V (antes, selector → seta). Eléctricamente cortan igual; el divisor del GPIO 1 y el voltímetro siguen
  después de los dos (con la seta apretada o el selector en OFF marcan 0 V). Cable 1 de la seta: fusible → A1; cable 2:
  A2 → borne 3 del selector. Actualizados `seta`, `potencia`, `conexiones` y `todo` (republicados), `CONEXIONES.md`,
  `ARQUITECTURA.md`, el manual (cap. 2 y 4, figuras regeneradas) y `CLAUDE.md`. La Entrega 4 de R2 no se tocó.
- **Selector con un solo bloque (decisión del grupo):** de los 2 BC10 NA se usa uno (10 A térmicos; promedio ~3 A,
  picos ~15 A cortos); el otro queda libre. Si calienta con el uso, sumar el segundo en paralelo.
- `seta.html`: nuevo **Paso 2b**, el bloque B (GPIO 47, directo) y el divisor de batería (GPIO 1, perforada de abajo)
  borne por borne sobre la fila de borneras de la Freenove. Aclaración: el bloque B nunca va al GPIO 1.
- `todo.html` se veía con la pestaña Seta de 5316 px de ancho: `armar_todo.py` cambiaba por base64 también la ruta
  de la foto citada en el pie (texto). Ahora solo reemplaza rutas dentro de atributos. Republicado.
- **Sin capacitores en el bus de 12 V (decisión del usuario):** salen los electrolíticos ≥ 25 V que iban cerca de los
  IBT-2 (estaban desde la v0.6). Sacados de `potencia`, `conexiones`, `CONEXIONES.md`, `COMPRAS.md` y el manual.

## 2026-10-20: informe de visión y prueba de carga del power bank
- Informe resumido de visión (YOLO + estéreo) en `docs/TPF R2/Entrega 5/Informe_vision/` (LaTeX y PDF, 4 páginas).
- Las cámaras no estaban conectadas (por eso `probar_camaras.sh` daba "Ninguna"); conectadas sin el soporte rígido:
  las dos a 30 FPS. **Sin el soporte la calibración no vale** (distancias inválidas); la detección sí.
- **Prueba de carga del PB2020MI:** Pi 5 solo con el power bank, dos cámaras y `start_limon.sh` (SGBM ~3 Hz, YOLO
  ~5 Hz, CPU ~250 %) + `web_video_server`, 15 min (90 lecturas cada 10 s): EXT5V 5,03-5,13 V (medio 5,07),
  `throttled` = 0x0 en todas, temperatura máxima 65,9 °C, CPU a 2400 MHz (una lectura a 2000: ajuste normal, no
  recorte). **El power bank alcanza.** Sin probar: con los dos ESP32 por USB (~1 W más), con el power bank casi
  descargado y con calor dentro del robot o al sol. Registro en la Pi: `~/logs/carga_powerbank_20261020_1302.csv`
  (el voltaje quedó partido en dos líneas: el `grep` agarró también el "5V" de `EXT5V_V`).

## 2026-10-20: primera prueba de la tracción (ruedas en el aire)
- Continuidad sin energizar (`checklist_traccion.html`), valores con todo conectado: GPIO 38 ↔ GND ≈ 5 kΩ (el 10 k en
  paralelo con los EN de los IBT-2 y la S3 sin alimentar), GPIO 15-18 ↔ GND ≈ 10 kΩ (el 20 k en paralelo con el
  pull-up de 10 k del encoder), divisor de batería ≈ 23 kΩ que sube de a poco (los capacitores de los IBT-2 ponen el
  100 k en paralelo con el 30 k mientras se cargan). M+/M− pitan los dos contra el rojo del motor: es el bobinado.
  Checklist corregida.
- Divisor de batería: 0,6 V en el GPIO 1 con la S3 **apagada** (el diodo de protección del pin a 3V3); con la S3
  encendida, 2,8 V (= 12 V × 30/130). Arrancar primero la lógica (power bank) y después los 12 V.
- **Firmware de prueba `ros_motores`** (`-DPRUEBA_MOTORES`): ignora la IMU y la distancia al frente, que no estaban
  conectadas (con el firmware normal la base no se mueve sin IMU). Tope de `d` bajado de 40 a 25 %. **Solo con las
  ruedas en el aire**; está flasheado en la S3: volver al env `ros` cuando estén la IMU y el HC-SR04 del frente.
- La Pi perdió el USB dos veces (`xHCI host controller not responding, assume dead`; la segunda, con `usb2-port2:
  disabled by hub (EMI?)`): solo se recupera reiniciando la Pi. La segunda pasó con la Freenove alimentada por el jack.
  Después se midió **0 V en el VBUS** del cable USB suelto con la Freenove encendida (sin retorno) y no se repitió.
  Causa sin confirmar. Al reconectar la S3, a veces queda en modo descarga: `esptool read-mac` con `--before no_reset
  --after watchdog-reset` (un reset con los 12 V prendidos es seguro: el 10 k del EN deja los IBT-2 deshabilitados;
  flashear, con los 12 V apagados). Por ssh, `pkill -f micro_ros_agent` mata la propia sesión: usar
  `pkill -f "[m]icro_ros_agent serial"`.
- **La tira de 5 V de la Freenove (y la "V" de cada G-V-S) no tiene tensión con solo el USB:** sale del regulador de
  la expansión, alimentado por el jack de 7-12 V. Medido: 2,3 / 0,5 V (nodo flotante) con el 3V3 a 3,3 V. Los encoders
  no contaban y la lógica del IBT-2 derecho andaba a medias. **Solución (decisión del usuario):** plug de la bornera
  +12 V al jack de la Freenove. Consecuencias: con la seta o el selector en OFF se apagan los encoders y la lógica de
  los IBT-2 (los puentes quedan sin mando: no mueven); la LiPo llena (12,6 V) supera un 5 % los 12 V del rótulo.
  La alternativa era el 5 V de la Pi (pin 2) al header 5V, descartada por la distancia Pi-S3.
- **Resultados con `d` (lazo abierto), LiPo ~12 V, ruedas en el aire:** las dos ruedas arrancan recién con 20 %
  (a 10 y 15 no); la izquierda gira hacia adelante (antihorario vista desde la izquierda). Al 25 %, las dos juntas:
  izquierda +8,5 rpm, derecha +7,6 rpm, encoders positivos y sin saltos: **`MOTOR_INVERTIDO` y `ENC_INVERTIDO`
  correctos**. Corriente: izquierda 0,6-0,7 A, derecha 0,8-0,9 A, las dos juntas 1,4 A (la derecha tiene más
  fricción). Encoder izquierdo a mano: +0,139 vueltas al girarla hacia adelante.
- Modelo de la rueda en `base_config.h`: K 0,52 → **0,6 rpm/%**, zona muerta girando 8 → **11 %** (de 25 % → 8,5 rpm y
  los 53 rpm de la hoja al 100 %), PI recalculado con la misma regla (Kp 0,72, Ki 11,1). τ sigue sin medir.
  **Sin flashear todavía** (no cambia `d`; sí `w`, `v` y `/cmd_vel`).
- **La rueda derecha patina sobre el eje** (el motor gira y la rueda no siempre): ajustar el prisionero sobre la cara
  plana del eje antes de apoyar el robot. Explica que al principio "no giraba".
- Pendiente: `cuentasPorVuelta` con 10 vueltas marcadas, τ con `log`, prueba con IMU y HC-SR04 y el firmware normal.
- **τ de las ruedas:** env `serial_motores` (como `ros_motores`, pero por serial para tener `log`) y
  `firmware/base/scripts/escalon_tau.py` (escalón de 0 a 25 % en las dos ruedas, log a 100 Hz). Resultado
  (`firmware/base/datos/escalon_25_20261020.csv`): **τ = 80 ms en las dos**, ~10 ms de retardo, finales 8,5 y 7,9 rpm.
  En `base_config.h`: τ 0,065 → 0,08 y Kp 0,72 → 0,89 (Ki queda en 11,1). Antes, `w 8 8` con micro-ROS: las dos
  ruedas en 7,9 rpm (izquierda con 24,4 %, derecha con 25,5 %). Con micro-ROS un comando de movimiento hay que
  repetirlo a ≥ 10 Hz (watchdog de 300 ms). Abrir el puerto con el script reinicia la S3 (el log arranca en t ≈ 1,6 s).
- **`w 8 8` con el PI nuevo** (τ 0,08, Kp 0,89; micro-ROS, `ros_motores`, ruedas en el aire): tres lecturas
  mientras giraban, izquierda 8,0-8,1 rpm con 24,4-24,5 %, derecha 7,9-8,1 rpm con 25,3-25,8 %; sin oscilación. Vueltas
  al final: 1,655 y 1,650 (0,3 % de diferencia). Frenaron por el watchdog al cortar el comando; sin fallas ni saltos.
  **Tracción en el aire probada** (sentidos, encoders, lazo abierto y de velocidad). Falta: prisionero de la rueda
  derecha, `cuentasPorVuelta` con 10 vueltas, y en el piso con la IMU, el HC-SR04 y el firmware normal.
- **Bug: `desarmar` no funcionaba por micro-ROS** en ninguna de las dos placas: `capa_ros.cpp` leía la primera palabra
  en `char primera[8]` con `%7s` y "desarmar" (8 letras) quedaba "desarma". La S3 seguía ARMADA, y el brazo no se
  desarmaba cuando `mision` lo pedía (seta o FALLA, `fsm.py`). La simulación no lo veía (`brazo_sim.py` compara el
  texto entero). Corregido a `[16]`/`%15s` en las dos; compila sin warnings. Binarios copiados a la Pi
  (`base_motores`, `base`, `brazo`). Base (`ros_motores`) flasheada **con los 12 V prendidos, a pedido del usuario**:
  no se movió nada; `armar` → ARMADA y `desarmar` → DESARMADA (modo parado). **Brazo flasheado** (sin nada
  conectado; primera vez con los pines v0.5 y el chequeo del cuatro barras): abre sesión, `/brazo/estado` DESARMADO,
  J1-J3 SIN_CERO, y `armar`/`desarmar` andan.
- **`cuentasPorVuelta` (rueda izquierda, a mano, base en modo libre):** una vuelta marcada dio 0,994 vueltas
  (1,655 → 2,649): 8316 de la hoja confirmado (0,6 % = 2° de marca). Girarla a mano cuesta mucho (189:1): el ajuste
  fino va con la odometría contra cinta en el piso (corrige también radio y trocha). Derecha: después del prisionero.
- **Teleoperado desde Android (ruedas en el aire, fuente de laboratorio):** Termux en el celular → ssh a la Pi →
  `armar` + `teleop_twist_keyboard --ros-args -p repeat_rate:=10.0`. Por la IP del Wi-Fi FIUNA (172.16.240.92) daba
  time out: la red aísla los clientes; con Tailscale en el celular (100.116.96.71) anda. Funciona: adelante, atrás y
  giros. Con `u` a velocidad máxima pasa de 4 A (esperable: 2,6 A en vacío por motor a 12 V, con la rueda de afuera
  cerca de 50 rpm y ~85 % de PWM). El "fuse 3 A" de atrás de la fuente es el de 220 V, no el límite de salida. Para
  las pruebas, bajar la velocidad con `z`; la máxima, con la LiPo.
- **Teleop web** (`firmware/base/scripts/teleop_web.py`): página con joystick táctil servida desde la Pi (puerto 8000,
  solo biblioteca estándar + rclpy, sin rosbridge); manda `/cmd_vel` cada 100 ms mientras se toca (si se corta, la S3
  frena por su watchdog) y botones ARMAR / DESARMAR / r / PARAR, con `/base/estado` en pantalla. Probado en la Pi con
  la base desarmada: `/cmd?v=0.5&w=-0.2` publica 0,125 m/s y −0,2 rad/s; comandos fuera de la lista, 400. Desde el
  celular: `http://100.116.96.71:8000` con Tailscale. Base de la app de la E7 de R2.

## 2026-10-21: IMU, página de la Pi y primera prueba del GPS
- IMU: foto del módulo (GY-9250/6500, `docs/fotos/IMU/`) y sección de montaje en `placa_s3.html`: plana en el medio
  del eje de tracción, flecha X al frente, VCC a 3V3, SDA 8, SCL 9, AD0 y NCS sueltos (0x68, I²C).
- `docs/html/pi5.html` (pestaña "Pi 5 y GPS" de `todo.html`): diagrama sobre la foto de la Pi y del GPS. Pines del UP501
  según la hoja técnica (rev. 1.2): 1 RXD, 2 TXD, 3 GND, 4 VDD, 5 VDD_B, 6 PPS; pin 1 a la derecha mirando el blindaje.
  **VDD_B es obligatorio** (unido al VDD a 3V3).
- **GPS conectado a la Pi y probado bajo techo:** `/dev/ttyAMA0` a 9600 trae GGA, GSA, GSV y RMC una vez por segundo
  (checksums válidos; basura solo al abrir el puerto). `nmea_serial_driver` publica `/gps/fix` (`gps_link`) con
  `status: -1` y 0 satélites: normal adentro. Falta la prueba a cielo abierto hasta tener fix.
- Prueba afuera (16:07): la Pi se apagó por accidente y al volver el GPS siguió leyendo bien (`throttled` = 0x0).
  Arrancó en frío: VDD_B sale de los 3V3 de la Pi, así que con la Pi apagada pierde la hora y los satélites
  guardados (solo una pila en VDD_B lo evitaría). Driver lanzado con `nohup` (log en `~/logs/gps_*.log` de la Pi):
  a los ~2 min seguía en `status: -1`. **Sin fix todavía: repetir a cielo abierto dejándolo 5-10 min quieto.**
  Ojo: `pkill -f nmea_serial_driver` por ssh mata la propia sesión (el patrón está en su línea de comando): usar
  `pgrep -f "[n]mea_serial_driver"`.
- **Primer fix del GPS (16:40, afuera de verdad):** antes estaba bajo techo (0 satélites en 14 min). A cielo
  abierto: hora real en ~1 min, 8 satélites a la vista y 3 enganchados (SNR 29-32) en ~5 min, y fix con 3 satélites
  (HDOP 5,4). `/gps/fix`: `status: 0`, lat/lon con covarianza 451 m² (σ ≈ 21 m, fix pobre por usar solo 3 satélites).
  Falta comparar con el celular y ver cuánto mejora con más satélites. El contador de SNR del script de vigilancia
  estaba mal (marcaba 0): mirar las `$GPGSV` crudas.

## 2026-10-21: hilera definida por GPS (N1)

- La demo final es **afuera** (confirmado por el usuario): el GPS cuenta para N1 de la guía R2 ("la hilera estará
  definida por GPS y verificada mediante visión").
- `mision/hilera_gps.py` (sin ROS) + `nodo_mision`: con `hilera_inicio_lat/lon` (y opcional `hilera_fin_lat/lon`)
  lee `/gps/fix`, publica `/hilera/estado` (distancia al inicio, σ, avance, lateral) y el recorrido autónomo no arma
  la base hasta estar a menos de 10 m del inicio con σ ≤ 20 m; ya en la hilera el GPS no lo frena (manda la
  odometría). `ros2 run mision marcar_gps` promedia el fix para marcar los puntos. Sin parámetros, nada cambia.
- 35 pruebas de `mision` OK; probado en la notebook con un `/gps/fix` falso. Falta probarlo con el UP501 afuera.
- No hecho: el regreso al punto de inicio al terminar la hilera (N1 también lo pide); hoy el recorrido frena en FIN.

## 2026-10-22: tracción con el joystick del celular

- Pi con las dos placas por USB: agentes de la base y del brazo y `teleop_web.py`. Ruedas en el aire.
- Primero no se movían (`rueda_izq/der=atasco`: el firmware mandaba PWM y los encoders no contaban): los motores y los
  encoders estaban desconectados. Con 12 V apagados, `/battery` ≈ 0 da `BATERIA_BAJA`; con 12 V, 11,7 V.
- Al prender los 12 V una vez la S3 dejó de publicar y su USB quedó trabado (`Errno 71 Protocol error`, esptool no
  conectaba): se recuperó desenchufando y enchufando el USB (con 12 V apagados) y el reset por watchdog. La segunda vez,
  grabando el kernel y `/base/estado` cada 0,5 s, el encendido no la cortó. Causa sin confirmar (¿pico en los 5 V del
  jack de la Freenove o en el GND?): si se repite, mirar `journalctl -k` por un `USB disconnect` justo al encender.
- `armar` + joystick: **funciona** desde el celular. `teleop_web.py`: los botones destellan cuando la Pi recibe el
  comando (antes no había forma de saber si se habían tocado).
- Pendiente: lo mismo en el piso (antes, firmware `ros` con IMU y HC-SR04 en vez de `ros_motores`).

## 2026-10-22: CLAUDE.md corto y comandos de sesión

- `CLAUDE.md` pesaba 33 KB (~10 k tokens) y `AGENTS.md` es un symlink a él (Codex lo corta a 32 KiB): pasó a
  **6 112 bytes, 71 líneas** (proyecto, hardware clave, reglas y un mapa de qué leer). Nada se borró, solo se movió:
  §5 → `docs/ESTADO.md`, §6 → `docs/DECISIONES.md`, §7 → `docs/PENDIENTES.md`, §4 completo → `docs/FLUJO_DE_TRABAJO.md`,
  §2 → final de `docs/CONEXIONES.md`, §3 → `docs/INDICE.md` (verificado línea por línea). Regla nueva: **el estado va
  en `docs/ESTADO.md`, nunca en `CLAUDE.md`.**
- `firmware/CLAUDE.md` (PlatformIO, flasheo, micro-ROS) y `docs/TPF R1/CLAUDE.md` (entregas Colab/Drive), cada uno con
  su `AGENTS.md` symlink. Codex solo los lee si se lanza desde esa carpeta (lee los `AGENTS.md` de la raíz hasta el cwd).
- Comandos `/cerrar` y `/retomar` en `.claude/commands/`. Versionados también la skill `pi-sync`, el hook de pruebas y
  `.claude/settings.json` (los dos hooks y el bloqueo de PDF); `settings.local.json` queda fuera de git solo con los
  plugins. `.gitignore`: `.claude/*` con excepciones.
- Rama `claude-md-corto` mergeada a `main` (fast-forward) y borrada; push hecho. `/pi-sync repo`: la Pi estaba apagada
  (Tailscale offline 12 h); al prenderla entró por Tailscale y quedó en `d688339` (solo documentos: sin compilar ni flashear).
- Commits: `e061024`, `b69d52e`, `d688339`.

## 2026-10-22: revisión de los CLAUDE.md contra el viejo

- Revisados `CLAUDE.md`, `firmware/CLAUDE.md` y `docs/ESTADO.md` contra el CLAUDE.md de 33 KB (`f082c83`; `HEAD~3`
  ya era el corto). Sin reglas contradictorias. Recortes: la regla de la simulación aislada salió de
  `firmware/CLAUDE.md` (queda en la raíz y en `DECISIONES.md`); en ESTADO, la cadena de potencia (está en
  `CONEXIONES.md`) y la línea de historia del CLAUDE.md corto.
- Recuperado lo que solo había quedado en la bitácora: métricas del detector **optimistas** (test de las mismas
  fuentes que el entrenamiento) y la parada por watchdog (Codex: ~30 cm a 1 m/s) en ESTADO; calibrar el sesgo del
  giróscopo antes del recorrido real, en PENDIENTES.
- `FLUJO_DE_TRABAJO.md` corregido: ponytail se activa con un hook al arrancar cada sesión (modo `full`, rige el
  código) y `/pi-sync` ya se usó en modo `repo` (falta compilar y flashear con él).
- `/pi-sync` dos veces (Tailscale): solo documentos, sin compilar ni flashear; la Pi quedó en `a90bdc4`. ESTADO dice
  `84c5531` a propósito: `a90bdc4` solo cambia esa línea (actualizarla en cada sync sería un ciclo sin fin).
- Commits: `f257c08`, `84c5531`, `a90bdc4` (con push).

## 2026-10-22: comandos genéricos de usuario

- En `~/.claude/commands/` (fuera del repo, para cualquier proyecto): `adelgazar-claude.md` (rama nueva; estado,
  decisiones y pendientes a `docs/` sin borrar nada; `CLAUDE.md` < 8 KB con tabla "qué leer" sin `@`; `AGENTS.md`
  symlink, preguntando si ya hay uno distinto; tamaños antes/después; sin push) y versiones genéricas de `cerrar`,
  `retomar` y `verificar` (esta detecta los tests: npm, pytest, cargo, go, make, pio, colcon).
- `.claude/commands/verificar.md` del repo versionado. Ojo: este `/cerrar` corrió la versión **genérica** (de usuario),
  no la del repo: con el mismo nombre parece ganar la de usuario (pendiente confirmar).
- Commits: `0de1dc6` y el de este cierre.
