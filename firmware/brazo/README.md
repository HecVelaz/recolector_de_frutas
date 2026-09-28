# firmware/brazo — firmware del brazo (lazo cerrado)

Esqueleto del firmware del brazo en la **ESP32-WROOM-32D**: J1 (base), J2 (hombro), J3 (codo) y la pinza.
Control en **cascada**: posición (P con límite de velocidad y aceleración) → velocidad (PI + feedforward
con el modelo de la Entrega 5) → duty. Corre a 100 Hz en una tarea del núcleo 0; los comandos llegan por el
monitor serial. Más adelante la capa de comandos se cambia por micro-ROS (`/brazo/joint_cmd`,
`/brazo/joint_states`, ver `docs/ARQUITECTURA.md` del proyecto), sin tocar el control.

**Estado:** compila y las 14 pruebas del control pasan en la PC (`pio test -e native`, motor simulado).
Revisado por Codex (10 hallazgos, aplicados). **No probado en placa.** Los valores marcados `MEDIR` en `include/brazo_config.h` son estimaciones.

## Estructura

| Archivo | Qué tiene |
|---|---|
| `../lib/ControlArticulacion/` | Control de una articulación (compartido con la base), **sin Arduino**: cascada, anti-windup, zona muerta, límites, atasco, descarte de saltos del encoder |
| `include/brazo_config.h` | Parámetros por articulación (encoder, transmisión, límites de la E4, modelo y PI de la E5), pose de cero, servos |
| `include/pins.h` | Pines (usa los 15 GPIO de uso general de la placa) |
| `src/main.cpp` | Drivers, tarea de control, comandos serie, homing, watchdog, CSV |
| `test/test_control/` | 14 pruebas con el modelo de la E5 simulado |

Drivers compartidos en `firmware/lib/` (enlazados por `symlink://`): `BTS7960`, `EncoderPCNT` y `L298N`. Vienen del
repo de pruebas `~/pruebas-esp32` (proyectos 06 y 08, donde se caracterizaron los motores); este proyecto empezó
ahí como `09-brazo-control` (commits `cd8b420` y `f408f4e`).

## Conexiones

| Articulación | Motor / driver | Driver | Encoder |
|---|---|---|---|
| J1 base | 36GP-555 160 rpm + IBT-2 | RPWM 21, LPWM 22, R_EN+L_EN 23 | Hall A 34, B 35 (**pull-up externo 10 kΩ a 3V3**, encoder a 3V3) |
| J2 hombro | 5840-31ZY + L298N canal A | ENA 25, IN1 26, IN2 27 | A 32, B 33 (pull-up interno) |
| J3 codo | 5840-31ZY + L298N canal B | ENB 13, IN3 16, IN4 17 | A 18, B 19 (pull-up interno) |

| Otro | GPIO |
|---|---|
| Servo pinza (apertura) | 4 |
| Servo giro J4 | 14 (pulsa durante el arranque: el servo puede moverse un instante) |
| Final de carrera J1 / J2 | 36 / 39 (NA a GND, pull-up externo 10 kΩ); J3 sin pin |

- Servos alimentados con 5–6 V **aparte** (no del ESP32), GND común.
- Pull-down de 10 kΩ en EN del IBT-2 y en ENA/ENB del L298N (sin ellos: **apagar los 12 V antes de flashear o
  pulsar EN**).
- Canales LEDC: 0-1 IBT-2 (20 kHz), 2-3 y 4-5 L298N (1 kHz), 6-7 servos (50 Hz). PCNT: unidades 0, 1 y 2.

## Uso

```bash
PIO=~/.platformio/penv/bin/pio
$PIO test -e native               # pruebas del control en la PC
$PIO run -t upload -t monitor     # flashear (12 V apagados) y abrir el monitor
```

Secuencia de primera prueba (una articulación a la vez, con la fuente limitada a 2–3 A):

1. `d 2 45` repetido: mover J2 en lazo abierto y ver con `e` que `w` tenga el **mismo signo** que el duty. Si no,
   cambiar `ENC_INVERTIDO` en `brazo_config.h`.
2. `v 2 30 3`: lazo de velocidad solo (sirve para la **E6**). Con `log 2` antes, se obtiene el CSV de la respuesta.
3. Llevar el brazo a la pose de referencia con `d`, y `z` para fijar el cero.
4. `j 2 60`, `m 0 90 0`: movimientos en posición. `s` detiene, `l` libera, `r` borra fallas.

`?` muestra todos los comandos.

## micro-ROS (entorno `ros`)

El mismo firmware, con los comandos por tópicos en vez del monitor serial (el USB lo usa el agente, a
**921600 baudios**: a 115200 el enlace no alcanza y `joint_states` sale a 9 Hz en vez de 20). Todo pasa
por los mismos comandos de texto, con las mismas validaciones y protecciones.

| Tópico | Tipo | Sentido | Detalle |
|---|---|---|---|
| `/brazo/joint_states` | `sensor_msgs/JointState` | sale, 20 Hz | `j1..j3`: posición [rad], velocidad [rad/s] (sin effort) |
| `/brazo/estado` | `std_msgs/String` | sale, 2 Hz | armado, y modo, cero, duty, falla y "llego" de cada articulación |
| `/brazo/respuesta` | `std_msgs/String` | sale | lo que mostraría el monitor serial |
| `/brazo/joint_cmd` | `sensor_msgs/JointState` | entra | posiciones [rad] con nombres `j1..j3`, o las 3 en orden sin nombres. Se valida entero y se aplica todo o nada |
| `/pinza/cierre` | `std_msgs/Float32` | entra | 0 = abierta, 100 = cerrada |
| `/pinza/giro` | `std_msgs/Float32` | entra | grados, −90..90 |
| `/brazo/comando` | `std_msgs/String` | entra | cualquier comando del monitor (`z`, `home 2`, `s`, `r`…), más `armar` / `desarmar` |

**Cada sesión con el agente empieza DESARMADA**: los movimientos se rechazan hasta mandar `armar` por
`/brazo/comando` (así, un nodo que siguiera publicando no mueve el brazo solo al reconectar). Detener, liberar,
cero y diagnóstico se aceptan siempre. Si se pierde el agente (3 pings sin respuesta, ~1,5 s), J1-J3 se detienen
apenas se detecta y el brazo queda desarmado; los servos quedan donde están, para no soltar el limón. Se puede
reiniciar el agente sin resetear la placa. Sin la hora del agente no se publica nada. `log` no está disponible
con micro-ROS (usar `ros2 bag record`).

```bash
$PIO run -e ros -t upload            # detener antes el agente (usa /dev/ttyUSB0)
source ~/microros_ws/install/local_setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 921600
# en otra terminal
ros2 topic echo /brazo/respuesta --field data
ros2 topic pub --once /brazo/comando std_msgs/msg/String "{data: 'z'}"
ros2 topic pub --once /brazo/comando std_msgs/msg/String "{data: 'armar'}"
ros2 topic pub --once /brazo/joint_cmd sensor_msgs/msg/JointState "{name: [j2], position: [0.79]}"
```

`brazo_ik` publica en `/brazo/joint_cmd`: con los dos corriendo, un punto en `/brazo/objetivo` mueve el brazo.

## Protecciones

- Sin cero, las articulaciones no aceptan movimientos en posición.
- Objetivos recortados a los límites de la E4. En `d` y `v`, con cero, no empuja hacia afuera del límite.
  Fuera de los límites + 5° → falla y freno.
- Atasco (duty alto sin avanzar en el sentido pedido) → falla y freno.
- Lecturas imposibles del encoder (por ejemplo el salto falso de 32 000 cuentas pendiente en `EncoderPCNT`) se
  descartan; 5 seguidas → falla. El cero (`z`) usa la última lectura validada.
- `s`, el fin de `d`/`v` y el watchdog **frenan hasta que el eje queda quieto** y recién ahí sostienen esa
  posición: no vuelven hacia atrás por la inercia.
- Límites de puesta en marcha: `d` hasta 25 % (J1) / 45 % (J2, J3) y se corta a los 300 ms si no se repite; `v`
  hasta 30 rpm y 5 s. Subirlos recién con la relación de transmisión medida (`brazo_config.h`).
- Homing de a una articulación: rechaza un final de carrera ya apretado, pide 3 lecturas seguidas, corta por
  recorrido máximo (rango + 10°) o por tiempo, y se cancela si aparece una falla.
- Un comando nuevo cancela lo pendiente de esa articulación (homing, `d`, `v`).
- Watchdog de comandos opcional (`wd <ms>`, solo lo alimentan comandos aceptados). Para cuando mande la Pi.
- Watchdog de tareas del ESP32 (1 s): si la tarea de control se cuelga, la placa se reinicia.
- Los servos no reciben pulsos hasta el primer `pinza`/`giro`.
- J2 y J3 son de sin fin: con duty 0 (freno) el brazo queda sostenido sin corriente.

## Pendiente (MEDIR / hacer)

- [ ] Relación de transmisión de cada articulación (`relacion`, hoy 1).
- [ ] Signo de los encoders de J1 y J3 (`ENC_INVERTIDO`).
- [ ] Zona muerta real del 5840-31ZY (`u0`, hoy 30 %; arranca entre 20 y 40 %).
- [ ] Pose de referencia (`POSE_CERO`) y ángulos de los finales de carrera (`HOME_Q`).
- [ ] Pulsos de los servos (`PINZA_US_*`, `GIRO_US_*`).
- [ ] Ajustar `kpPos`, `velMax`, `accMax` con el brazo armado y con carga.
- [ ] Probar la capa micro-ROS con el brazo armado (en la placa sola ya anda; ver Resultados).

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-27 | `pio test -e native` (14 pruebas, motor simulado con el modelo de la E5) | OK |
| 2026-09-27 | `pio run -e ros` (micro-ROS Jazzy): RAM 15,3 %, flash 29,6 %, 0 warnings. Sin probar con el agente | OK |
| 2026-09-28 | Placa sola, serial: arranque, rechazo sin cero, atasco, watchdog, límites de `giro` | OK |
| 2026-09-28 | Placa sola, serial: J1 cuenta sola con 34/35 al aire (faltan los pull-ups externos) | esperado |
| 2026-09-28 | Placa sola, serial: `s` sobre una articulación con falla + `wd` → aviso del watchdog repetido | **bug abierto** |
| 2026-09-28 | Placa sola, micro-ROS a 921600: `joint_states` 20,0 Hz, `estado` 2,0 Hz; armado, validación de `joint_cmd` y `giro`; al perder el agente vuelve DESARMADO | OK |
| | Signo de encoders J1/J3 | — |
| | Lazo de velocidad J1/J2 en placa | — |
| | Movimiento en posición con carga | — |
