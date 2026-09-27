# firmware/base — firmware de la base (ESP32-S3)

Tracción diferencial en lazo cerrado, odometría, sensores y **seguridad local** en la Freenove ESP32-S3 N16R8.
El control corre a 100 Hz en una tarea del núcleo 0; los comandos llegan por el monitor serial. Más adelante la
capa de comandos se cambia por micro-ROS (`/cmd_vel` → `/odom`, `/imu/data_raw`, `/range/*`, `/bumpers`,
`/battery`, ver `docs/ARQUITECTURA.md`), sin tocar la lógica.

**Estado:** compila sin warnings y las 19 pruebas de la lógica pasan en la PC (`pio test -e native`). Revisado
por Codex (9 hallazgos, aplicados). **No probado en placa.** Los valores marcados `MEDIR` en `include/base_config.h` son estimaciones.

## Estructura

| Archivo | Qué tiene |
|---|---|
| `lib/BaseLogica/Diferencial` | Cinemática diferencial (v, w ↔ rpm de cada rueda, saturación que conserva la curvatura), rampa y odometría. **Sin Arduino** |
| `lib/BaseLogica/SeguridadBase` | Seta, vuelco, bumpers, distancia al frente, watchdog y batería baja. **Sin Arduino** |
| `../lib/ControlArticulacion` | PI de velocidad + feedforward de cada rueda (el mismo control del brazo, en modo velocidad) |
| `../lib/HCSR04` | Los 3 HC-SR04 con TRIG común y ECHO por interrupción (no bloquea) |
| `../lib/MPU9250`, `../lib/UP501` | IMU y GPS (copiados de `~/pruebas-esp32`, probados en placa) |
| `include/pins.h` | Pines, según `docs/CONEXIONES.md` |
| `include/base_config.h` | Motor, geometría, seguridad y límites de puesta en marcha |
| `test/test_base/` | 19 pruebas: cinemática, odometría (recta, giro, círculo), cada regla de seguridad, tope por cercanía con la rampa, lazo de una rueda |

## Seguridad (se decide en la S3, sin esperar a la Pi)

| Causa | Qué hace | Cómo se sale |
|---|---|---|
| Seta apretada (o cable cortado: contacto NC) | EMERGENCIA: puentes deshabilitados (EN = 0) | Soltar la seta y `r` |
| Roll o pitch > 25° | VUELCO: frena | Nivelar la base y `r` |
| IMU sin muestras por más de 200 ms (o sin responder al arrancar) | No se mueve: sin IMU no se puede vigilar el vuelco | Solo, al volver los datos |
| Bumper delantero / trasero | Solo se permite alejarse **en línea recta** (sin giro) | Solo, al soltarse |
| Ultrasonido del frente sin eco (desconectado o sin medir) | No avanza; retroceder y girar sí | Solo, al volver el eco |
| Obstáculo al frente < 0,20 m | No avanza | Solo |
| Obstáculo al frente entre 0,20 y 0,50 m | Tope de velocidad que baja linealmente hasta 0 | Solo |
| Sin comandos por más de `wd` ms | Frena y **anula** el comando vigente | Con un comando nuevo |
| Cualquier recorte en lazo abierto (`d`) | Corta el lazo abierto | Con un comando nuevo |
| Batería < 11 V | Aviso (no frena) | — |
| Rueda con atasco o saltos del encoder | Base detenida | `r` |

Además: watchdog de tareas del ESP32 (si el control se cuelga, la placa se reinicia); al arrancar, la base queda
liberada hasta el primer comando; al detenerse, la rampa vuelve a cero (el próximo comando no hereda el anterior);
si una rueda falla, las dos se frenan en el mismo paso; `cal` solo con la base detenida. Un ECHO que responde pero
sin obstáculo al alcance cuenta como libre; ningún pulso de ECHO cuenta como sensor sin dato.

## micro-ROS (entorno `ros`)

El mismo firmware, con `/cmd_vel` y los comandos por tópicos en vez del monitor serial (el USB lo usa el agente).
Con micro-ROS el **watchdog de comandos arranca en 300 ms**: si `/cmd_vel` deja de llegar, la base frena. Si se
pierde el agente (~1,5 s), la base se detiene. Sin la hora del agente no se publica nada.

| Tópico | Tipo | Sentido | Detalle |
|---|---|---|---|
| `/odom` | `nav_msgs/Odometry` | sale, 25 Hz | `odom` → `base_link` |
| `/imu/data_raw` | `sensor_msgs/Imu` | sale, 50 Hz | m/s² y rad/s, sin orientación (para `imu_filter_madgwick`) |
| `/range/frente`, `/range/izq`, `/range/der` | `sensor_msgs/Range` | sale, 10 Hz | +Inf = nada al alcance; NaN = sin eco (REP-117) |
| `/bumpers` | `std_msgs/UInt8` | sale, 10 Hz | bits 0..3: frente-izq, frente-der, atrás-izq, atrás-der |
| `/gps/fix` | `sensor_msgs/NavSatFix` | sale, ~1 Hz | un mensaje por epoch; covarianza aproximada por HDOP |
| `/battery` | `sensor_msgs/BatteryState` | sale, 1 Hz | tensión |
| `/base/estado` | `std_msgs/String` | sale, 2 Hz | modo, seguridad, bloqueos, IMU y fallas |
| `/base/respuesta` | `std_msgs/String` | sale | lo que mostraría el monitor serial |
| `/cmd_vel` | `geometry_msgs/Twist` | entra | `linear.x` [m/s], `angular.z` [rad/s] |
| `/base/comando` | `std_msgs/String` | entra | cualquier comando del monitor: `r`, `s`, `l`, `cal`, `odo0`, `wd`… |

```bash
$PIO run -e ros -t upload            # detener antes el agente (usa /dev/ttyACM0)
source ~/microros_ws/install/local_setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0
# en otra terminal
ros2 topic echo /base/estado --field data
ros2 run teleop_twist_keyboard teleop_twist_keyboard   # manejar con el teclado
```

Los dos ESP32 usan un agente cada uno (uno por puerto): `/dev/ttyACM0` (base) y `/dev/ttyUSB0` (brazo).

## Uso

```bash
PIO=~/.platformio/penv/bin/pio
$PIO test -e native               # pruebas de la lógica en la PC
$PIO run -t upload -t monitor     # flashear (12 V de los motores APAGADOS) y abrir el monitor
```

Primera prueba, **con las ruedas en el aire** y la fuente limitada a 3 A:

1. `sens`: ver que respondan IMU, GPS, distancias, bumpers, seta y batería.
2. `d 25 0` repetido, después `d 0 25`: cada rueda debe girar **hacia adelante** y `e` mostrar rpm positivas. Si
   gira al revés, cambiar `MOTOR_INVERTIDO`; si gira bien pero las rpm salen negativas, `ENC_INVERTIDO`.
3. `log 20` y `w 20 20 3`: lazo de velocidad de las ruedas (CSV para graficar la respuesta).
4. `v 0.1 0 2`, `v 0 0.5 2`: movimiento con rampa. Con las ruedas en el piso, medir con cinta la distancia
   recorrida y compararla con `e` para corregir `radioRueda` y `trocha`.

`?` muestra todos los comandos.

## Pendiente (MEDIR / hacer)

- [ ] **Qué motor de tracción es**: las notas dicen 36GP-555 de 53 rpm; el inventario, DC 895 planetario de 53 rpm.
      Define `cuentasPorVuelta` (hoy 9600 = 16 PPR × 4 × 150), `K`, `tau` y la zona muerta.
- [ ] Sentido de motores y encoders (`MOTOR_INVERTIDO`, `ENC_INVERTIDO`).
- [ ] Radio de rueda y trocha (`CFG_DIF`).
- [ ] Umbral de batería según la química.
- [ ] Detección de "plataforma levantada" (H9): la IMU sola no la distingue bien.
- [ ] Probar la capa micro-ROS en placa (compila; ver la tabla de Resultados).

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-27 | `pio test -e native` (19 pruebas, después de la revisión de Codex) | OK |
| 2026-09-27 | `pio run -e esp32s3`: RAM 7,0 %, flash 5,5 %, 0 warnings | OK |
| 2026-09-27 | `pio run -e ros` (micro-ROS Jazzy): RAM 22,7 %, flash 7,3 %, 0 warnings. Sin probar con el agente | OK |
| | Sentido de ruedas y encoders | — |
| | Lazo de velocidad de las ruedas en placa | — |
| | Odometría contra cinta métrica | — |
