# Estado actual (al 2026-11-25, ~21:31; traspaso de Codex a Claude)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **27/11/2026**: `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **Modo Recolector:** 3 de 3 (23/11); el 25/11 cortes por J1 trabada en la canasta y por el puente atrasado ("sin
  comandos"): arreglos cargados **sin probar** (ver Brazo y Puente). ~50 s por limón; agarre a ~60 cm de J1.
- **Rodear árbol** (25/11): programado y simulado, **sin probar en el robot**.
- **Riesgos:** J1 en la canasta; trabas del puente; batería (con < 11 V el brazo no tiene fuerza); la Pi se reinició
  sola (25/11, `throttled=0x50000`); servo de la pinza (23/11). Potencia v0.6: falta portafusible, XT60 y divisor.
- **Manual v1.2** (25/11) en `docs/manual/` (falta subir el PDF a Drive). Misión ROS: navegación solo en Gazebo.

## TFmini-S: trabajo local pendiente de cargar (25/11, ~21:31)
- Usuario confirmó cableado: verde TX → WROOM GPIO 13, rojo → bornera 5 V, negro → GND; blanco aislado.
  Sensor de un punto, no escáner 2D. Montaje lateral izquierdo sobre bumper; posición/orientación **MEDIR**.
- Implementado en `../pruebas-esp32/20-brazo-coordinado`: UART1 RX, parser y `/range/lidar_izq` (Range, 10 Hz).
  5 pruebas nativas OK; compilaciones `brazo` y `ros` OK sin warnings. **No flasheado**; tensión no medida.
- Puente y app 0.15.6 preparados; Android: 34 tests OK, lint sin errores (7 avisos). Poco X6 Pro todavía en
  **0.15.5**, confirmado por ADB. **No se copió nada a la Pi ni se instaló la APK nueva**.
- Suite puente: 124 ejecutadas, 6 fallos + 4 errores por falta de NumPy, 8 omitidas. NumPy/OpenCV ya instalados
  en `/tmp/arturito-lidar-venv`, pero la repetición final fue interrumpida antes de arrancar. **No hay commits**.
- Continuar con `docs/CONTINUAR_CLAUDE.md`: incluye cambios de ambos repos, comandos y tareas previas de la demo.

## App Arturito y puente (`app/`)
- **App 0.15.5** en el Poco X6 Pro (horizontal, panel escalado); 0.15.3 en la Xiaomi Pad 5. Control: **Modo manual |
  Recolector | Recolección | Rodear árbol** (paradas 1–4). Brazo y pinza: velocidad del
  brazo 10–100 % de 1 rad/s (60 %), apertura y giro de la pinza 15–180 °/s (`pz w`/`mn w`; el firmware arranca en 45).
  Giro de la base hasta 1 rad/s. Alertas de sensores sin la prueba completa.
- **Conexión: tablet por Tailscale** (misma cuenta que la Pi), en la app `http://100.116.96.71:18006` y la clave de
  siempre. Con el teclado físico Xiaomi enganchado no aparece el de pantalla. Sin Tailscale: túnel USB con
  `bash app/robot-bridge/conectar_tablet.sh` en la notebook (la app lo acepta en `127.0.0.1:18006`). La clave está en
  la Pi en `~/arturito-bridge-0.4.0/data/.connection-token`. **Teléfono: ~1 s de demora** (ahorro de energía, otra
  subred): el puente corta el mando (plazo 0,22 s); usarlo en la red de la Pi o con hotspot, si no la tablet.
- **Puente** `app/robot-bridge` (Pi `~/arturito-bridge-0.9.0`): **arranca solo al prender** (`arturito.service`, de
  usuario: agentes, visión y puente). Apagar todo: `systemctl --user stop arturito`. Cargar un cambio: copiar el
  archivo y reiniciar solo el puente (`pkill -f "[r]un_pi.py --source ros2"` y `arrancar_pi.sh`; no reiniciar el
  servicio entero: relanza los agentes y la S3 puede colgarse). `bridge.log` se acumula: rechazos, cortes con el
  estado del brazo y mediciones. Datos en `~/arturito-bridge-0.4.0/data`. Reiniciar sin perder el cero:
  `ARTURITO_RESTORE_ORIGIN_JSON` con el `navigation_origin` de `/api/v1/telemetry`. Prioridades: puente 0,
  planificador 5, visión 10 (`vision.sh`); reiniciar el puente desde una sesión con `nice` 0. `faulthandler` escribe
  en `bridge.log` la traza si el lazo se atrasa > 0,3 s (`Timeout (0:00:00`). Batería × 0,959 (`BATTERY_SCALE`).
- **Estados del brazo** (firmware 20): 0 suelta, 1 yendo, 2 llegó, 3 firme, 4 frenada, 5 mov, 6 homing. Puente: Fast
  DDS solo por UDP; tras un corte breve la pinza/muñeca no bloquean. Homing con J2 > 25°: `mv 3 17 4` (plegado,
  antes por J2 46,7° / J3 50°); fuera de la franja sube J2 hasta 24°; hasta 2 recuperaciones.
- **Recolección:** homing → Calcular cero (3,8 s, criterio flojo; sin limón guarda la pose y al iniciar gira ±15/25°)
  → Iniciar (se acerca a **60 cm** de J1, sin probar; más cerca no retrocede; mide 8 s y cosecha lo medido) → Volver
  al cero (90 s propios).
- **Modo Recolector:** escanea y **cosecha todos los vistos**, guardados en el marco odom; reubica el Móvil (60 cm,
  15–35°; atrás ≤ 20 cm) con el brazo en la canasta, mide hasta 3 lecturas firmes (≤ 8 s) y agarra; el que no se ve
  se saltea; "sin cuentas" se repite 3 veces y un limón fallido se reintenta una vez. Visión prendida toda la misión.
- **Rodear árbol** (`mode=rodear`, `stops` 1–4): tronco del primer escaneo; paradas antihorario cada 90° (saltos de
  45°), en cada una como el Recolector; vuelve siempre al primer escaneo (con < 4 por donde vino, sin marcha atrás).
  Objetos: espera 5 s y rodea por un círculo 50/80 cm más afuera. Espacio: 3 × 3 m. `SENSOR_AHEAD_MM` sin medir.
- **Visión a pedido:** la app la pide en Recolector, Recolección y Visión; sin pedido 30 s (y sin misión) el puente
  apaga el grupo de `start_limon.sh`; prenderla tarda ~21 s. Interruptor `VISION_ON_DEMAND` en `collection_mission.py`.
- Homing fallido → `arm-homing-pending` bloquea el joystick del brazo hasta un homing completo.

## Demo y navegación (`pruebas-esp32/27-aruco-arbol`)
- **Demo afuera:** banderín ArUco (ID 0) y arbolitos; GPS solo para la rúbrica. `recolectar.py` (plan B) sin probar.

## Base (`firmware/base`, S3)
- **En la S3: `~/firmware/base_ros_20261121_sin_r`** (env `ros`, `ff9172d`). Flasheo con `--after watchdog-reset`.
  Seta y vuelco sin enclavar: desarman la base (hace falta `armar`); `s` borra fallas de rueda. Watchdog 300 ms.
- **Al prender la Pi la S3 arranca en bootloader** (se alimenta del USB de la Pi): `arrancar_pi.sh` lo detecta
  (esptool sin reset) y la reinicia solo en ese caso; registro en `~/logs/s3_bootloader.log` (probado 23/11 18:35).
- Enlace micro-ROS: ping cada 500 ms, 3 fallidos = corte (se reconecta solo); medir con `medir_enlace_base.py`.

## Brazo (WROOM)
- **En la WROOM: `pruebas-esp32/20-brazo-coordinado` env `ros` (micro-ROS), fuente `750ba4c`.** Serie:
  `~/firmware/brazo20_serie_20261119.bin` (imagen completa, en 0x0). **No flashear `firmware/brazo`** (`d3644c8`).
- **Homing:** `homingDutyMax` 50 % / 1,5 s no despega J3 quieta en el reposo ("J3 CORTADA … no avanza"): moverla un
  poco con el joystick y repetir. Arreglo de fondo (firmware) pendiente.
- **J1 en la canasta (130°):** con `mv` corta "sin cuentas" a los 150 ms (aun con `ff 1 17 17 45 17`); con el
  joystick sale. El puente la saca con `jv -0.90 0 0` hasta el destino (`jog_j1_out`). Fondo: `sinCuentasMs` de J1.
- `punta.py` (probado 23/11): entrada horizontal la más larga (20…5 cm; = distancia a J1 − ~44 cm); tras cerrar
  **baja** 5 cm. Agarre: **+3,25 cm arriba** (`GRASP_RAISE_MM` 32,5, puente), **2,7 cm antes del centro**
  (`AGARRAR_ADELANTE` −27) y **0,75 cm a la derecha** (`AGARRAR_IZQUIERDA` −7,5); ajuste fino 21/11 encima.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 55; `simulacion` 17. `largo_herramienta` = 0 (MEDIR). Sin nodo de seguridad (S2).
- Gazebo: `mision:=true` 12 de 12; `mundo:=arbolitos` 15 de 18 paradas; en el real falta la TF de la cámara.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector **v4**, ~2–3 img/s, disparidad ~1–2 Hz, 0,40–0,95 m. Foco fijo (izq 2,90 / der
  2,15), calibración del mástil (fx 672,1, baseline 100,3 mm); `approximate_sync` sin tolerancia (desfase mediano 17 ms).
- Profundidad (22/11): error −1 a −3 cm con el limón a la vista; detrás de ramas da falsas (filtro < 15 % sin aplicar).

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Wi-Fi: iPhone de Mathias > LabEquiposMedicos. Al prender arranca
  `arturito.service`. **Fuente oficial de 27 W**; con el power bank se reinicia. GPS UP501 σ ≈ 21 m.
