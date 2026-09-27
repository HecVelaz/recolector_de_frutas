# firmware/base — firmware de la base (ESP32-S3)

Tracción diferencial en lazo cerrado, odometría, sensores y **seguridad local** en la Freenove ESP32-S3 N16R8.
El control corre a 100 Hz en una tarea del núcleo 0; los comandos llegan por el monitor serial. Más adelante la
capa de comandos se cambia por micro-ROS (`/cmd_vel` → `/odom`, `/imu/data_raw`, `/range/*`, `/bumpers`,
`/battery`, ver `docs/ARQUITECTURA.md`), sin tocar la lógica.

**Estado:** compila sin warnings y las 16 pruebas de la lógica pasan en la PC (`pio test -e native`). **No
probado en placa.** Los valores marcados `MEDIR` en `include/base_config.h` son estimaciones.

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
| `test/test_base/` | 16 pruebas: cinemática, odometría (recta, giro, círculo), cada regla de seguridad, lazo de una rueda |

## Seguridad (se decide en la S3, sin esperar a la Pi)

| Causa | Qué hace | Cómo se sale |
|---|---|---|
| Seta apretada (o cable cortado: contacto NC) | EMERGENCIA: puentes deshabilitados (EN = 0) | Soltar la seta y `r` |
| Roll o pitch > 25° | VUELCO: frena | Nivelar la base y `r` |
| Bumper delantero / trasero | No avanza / no retrocede; girar en el lugar sí | Solo, al soltarse |
| Obstáculo al frente < 0,20 m | No avanza | Solo |
| Obstáculo al frente entre 0,20 y 0,50 m | Avance escalado linealmente | Solo |
| Sin comandos por más de `wd` ms | Frena | Solo, con el próximo comando |
| Batería < 11 V | Aviso (no frena) | — |
| Rueda con atasco o saltos del encoder | Base detenida | `r` |

Además: watchdog de tareas del ESP32 (si el control se cuelga, la placa se reinicia) y, al arrancar, la base
queda liberada hasta el primer comando.

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
- [ ] Capa de comandos por micro-ROS.

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-27 | `pio test -e native` (16 pruebas) | OK |
| 2026-09-27 | `pio run -e esp32s3`: RAM 7,0 %, flash 5,5 %, 0 warnings | OK |
| | Sentido de ruedas y encoders | — |
| | Lazo de velocidad de las ruedas en placa | — |
| | Odometría contra cinta métrica | — |
