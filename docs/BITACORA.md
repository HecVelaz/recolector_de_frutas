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
