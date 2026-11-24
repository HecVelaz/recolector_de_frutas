# Estado actual (al 2026-11-23, ~22:00)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **27/11/2026**: `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **Modo Recolector (23/11):** se reubica y cosecha todos los del escaneo: 3 de 3 probado. Agarre a ~60 cm de J1,
  limones a **40–55 cm del piso**. Punto de agarre ajustado en el robot (ver Brazo), todavía variable (~2 cm).
- **Riesgos abiertos:** **servo de la pinza sin moverse** (23/11, el firmware le manda el pulso: hardware); la Pi se
  apaga de golpe (21/11); la S3 a veces queda muda (cortes del enlace; 20:34 del 23/11 hizo falta reset).
- Misión ROS (`ros2_ws/src/mision`): navegación con el banderín solo en Gazebo. Potencia v0.6: falta portafusible,
  XT60 y divisor 100 k / 30 k. **Manual v1.1** en `docs/manual/` (falta subir el PDF a Drive).

## App Arturito y puente (`app/`)
- **App 0.15.2** en la Xiaomi Pad 5 (Recolector sin cantidad). Control: **Modo manual | Recolector | Recolección**. Brazo y pinza: velocidad del
  brazo 10–100 % de 1 rad/s (60 %), apertura y giro de la pinza 15–180 °/s (`pz w`/`mn w`; el firmware arranca en 45).
  Giro de la base hasta 1 rad/s (como `teleop.html`). Alertas de sensores (0.12.0) sin la prueba completa.
- **Conexión: tablet por Tailscale** (misma cuenta que la Pi), en la app `http://100.116.96.71:18006` y la clave de
  siempre. Con el teclado físico Xiaomi enganchado no aparece el de pantalla. Sin Tailscale: túnel USB con
  `bash app/robot-bridge/conectar_tablet.sh` en la notebook (la app lo acepta en `127.0.0.1:18006`).
- **Puente** `app/robot-bridge` (Pi `~/arturito-bridge-0.9.0`): **arranca solo al prender** (`arturito.service`, de
  usuario: agentes, visión y puente). Apagar todo: `systemctl --user stop arturito`. Cargar un cambio: copiar el
  archivo y reiniciar solo el puente (`pkill -f "[r]un_pi.py --source ros2"` y `arrancar_pi.sh`; no reiniciar el
  servicio entero: relanza los agentes y la S3 puede colgarse). `bridge.log` se acumula: rechazos, cortes con el
  estado del brazo y mediciones. Datos en `~/arturito-bridge-0.4.0/data`. Reiniciar sin perder el cero:
  `ARTURITO_RESTORE_ORIGIN_JSON` con el `navigation_origin` de `/api/v1/telemetry`.
- **Estados del brazo** (firmware 20): 0 suelta, 1 yendo, 2 llegó, 3 firme, 4 frenada, 5 mov, 6 homing. Puente: Fast
  DDS solo por UDP; tras un corte breve la pinza/muñeca no bloquean; homing con J2 > 25° pasa por `mv 3 17 4`.
- **Recolección:** homing → Calcular cero (3,8 s, criterio flojo; sin limón guarda la pose y al iniciar gira ±15/25°)
  → Iniciar (se acerca a **60 cm** de J1, sin probar; más cerca no retrocede; mide 8 s y cosecha lo medido) → Volver
  al cero (90 s propios).
- **Modo Recolector:** escanea y **cosecha todos los vistos** (sin cantidad), guardados en el marco odom; reubica el
  Móvil (60 cm, 15–35°, lo que menos mueva; atrás ≤ 20 cm), mide (corrige) y agarra; uno perdido, con la guardada.
  Visión prendida toda la misión; sin verificación final. Plan del brazo: 2–3,5 s en la Pi.
- **Visión a pedido:** la app la pide en Recolector, Recolección y Visión; sin pedido 30 s (y sin misión) el puente
  apaga el grupo de `start_limon.sh`; prenderla tarda ~21 s. Interruptor `VISION_ON_DEMAND` en `collection_mission.py`.
- Homing fallido → `arm-homing-pending` bloquea el joystick del brazo hasta un homing completo. `recolectar.py`
  (banderín, RODEAR) usa el firmware **serie** del brazo: con la WROOM en micro-ROS no le habla.

## Demo y navegación (`pruebas-esp32/27-aruco-arbol`)
- **Demo: afuera, un banderín ArUco (ID 0) y una hilera de 2-3 arbolitos**; GPS (±20 m) solo para la rúbrica.
- `recolectar.py`: RODEAR y banderín único + BUSCAR **sin probar en el robot**; `banderin.json` sin medir.
- N3 de la guía: detención ✓ (18/11); seguimiento ≈ RODEAR (confirmar con la cátedra); evitación sin hacer.

## Base (`firmware/base`, S3)
- **En la S3: `~/firmware/base_ros_20261121_sin_r`** (env `ros`, `ff9172d`). Flasheo con `--after watchdog-reset`.
  Seta y vuelco sin enclavar: desarman la base (hace falta `armar`); `s` borra fallas de rueda. Watchdog 300 ms.
- **Al prender la Pi la S3 arranca en bootloader** (se alimenta del USB de la Pi): `arrancar_pi.sh` lo detecta
  (esptool sin reset) y la reinicia solo en ese caso; registro en `~/logs/s3_bootloader.log` (probado 23/11 18:35).
- **Enlace micro-ROS:** ping cada 500 ms, espera 100 ms, 3 fallidos = corte (se reconecta solo; en combinado o base
  corta el mando). ~2,5 pings fallidos/min sin relación con la carga (23/11); medir con `medir_enlace_base.py`.

## Brazo (WROOM)
- **En la WROOM: `pruebas-esp32/20-brazo-coordinado` env `ros` (micro-ROS), fuente `750ba4c`.** Serie:
  `~/firmware/brazo20_serie_20261119.bin` (imagen completa, en 0x0). **No flashear `firmware/brazo`** (`d3644c8`).
- Si no abre sesión: pulso en EN por RTS (pyserial, DTR bajo) **con los 12 V apagados**.
- **Homing:** `homingDutyMax` 50 % / 1,5 s no despega J3 quieta en el reposo ("J3 CORTADA … no avanza"): moverla un
  poco con el joystick y repetir. Arreglo de fondo (firmware) pendiente.
- `punta.py` (probado 23/11): entrada horizontal la más larga (20…5 cm; = distancia a J1 − ~44 cm); tras cerrar
  **baja** 5 cm. Agarre: **+3,25 cm arriba** (`GRASP_RAISE_MM` 32,5, puente), **2,7 cm antes del centro**
  (`AGARRAR_ADELANTE` −27) y **0,75 cm a la derecha** (`AGARRAR_IZQUIERDA` −7,5); ajuste fino 21/11 encima.
  Pinza RDS3218 500/1200 µs.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 55; `simulacion` 17. `largo_herramienta` = 0 (MEDIR). Sin nodo de seguridad (S2).
- Navegación con el banderín solo en Gazebo; en el real falta la TF de la cámara y medir `hilera_arboles.json`.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector **v4**, ~2–3 img/s, disparidad ~1–2 Hz, 0,40–0,95 m. Foco fijo (izq 2,90 / der
  2,15), calibración del mástil (fx 672,1, baseline 100,3 mm); `approximate_sync` sin tolerancia (desfase mediano 17 ms).
- **Validación de profundidad (22/11):** datos en `datos/validacion_profundidad_20261122/` (Pi y notebook, fuera de
  git), `herramientas/comparar_profundidad.py`. Limón a la vista: estable (~1 mm), error −1 a −3 cm. Detrás de ramas
  el localizador actual da coordenadas falsas (> 3 cm); rechazarlas con < 15 % de píxeles válidos las elimina.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Wi-Fi: iPhone de Mathias > LabEquiposMedicos. Al prender arranca
  `arturito.service`. **Fuente oficial de 27 W**; con el power bank se reinicia. GPS UP501 σ ≈ 21 m.
- Rutas: binarios `~/firmware/`, scripts `~/scripts`, logs `~/logs`, workspaces `~/ros/`, venvs `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `sim.launch.py mision:=true`: 12 de 12; `mundo:=arbolitos`: 15 de 18 paradas. `base_sim` sigue esperando `r`.
