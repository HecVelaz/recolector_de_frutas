# Estado actual (al 2026-11-22, ~02:30)

Foto del estado: se reescribe en cada `/cerrar`. **El estado va acá, nunca en `CLAUDE.md`.** Historia y mediciones
con fecha: `BITACORA.md`; lo que falta: `PENDIENTES.md`. Fecha límite: **27/11/2026** (demo; plan día por día en `PENDIENTES.md`).

## Avance
- **Recolección desde la app (21/11):** 1 limón con acercamiento y vuelta al cero; **2 de 3 sin mover la base**.
  Limonero subido 19 cm → limones a ~63 cm del piso: el agarre pasa ~3 cm abajo (sin camino seguro a la canasta más
  arriba). Mejor zona: limón a 50–55 cm de J1 y **40–55 cm del piso**, a la izquierda y ≥ 8° adelante de J1.
- **Riesgos abiertos:** la Pi se apaga de golpe (~6 veces el 21/11; alimentación sin resolver); cortes del USB de la
  WROOM y la S3 con la base en movimiento (sujetar cables); homing con "J3 CORTADA" desde el reposo (ver Brazo).
- Misión ROS (`ros2_ws/src/mision`): navegación con el banderín solo en Gazebo. Potencia v0.6: falta portafusible,
  XT60 y divisor 100 k / 30 k. **Manual v1.1** en `docs/manual/` (falta subir el PDF a Drive).

## App Arturito y puente (`app/`)
- **App 0.14.0** en la Xiaomi Pad 5. Control: **Modo manual | Modo Recolector | Modo Recolección** (sin pestaña Misión).
  Alertas de sensores (0.12.0) sin la prueba completa.
- **Puente** `app/robot-bridge` (Pi `~/arturito-bridge-0.9.0`, `127.0.0.1:18006`). **Todo junto y con reconexión:**
  `bash app/robot-bridge/conectar_tablet.sh` en la notebook. A mano, tablet por USB:
  `~/Android/Sdk/platform-tools/adb reverse tcp:18006 tcp:18006` y
  `ssh -N -L 127.0.0.1:18006:127.0.0.1:18006 r2d2@100.116.96.71`. En la Pi: `bash ~/arturito-bridge-0.9.0/arrancar_pi.sh`
  (datos en `~/arturito-bridge-0.4.0/data`; rechazos del mando y mediciones en `bridge.log`). Para reiniciar el puente
  sin perder el cero: `ARTURITO_RESTORE_ORIGIN_JSON` con el `navigation_origin` de `/api/v1/telemetry`.
- **Recolección:** homing → Calcular cero (3,8 s, criterio flojo; sin limón guarda la pose y al iniciar gira ±15/25°)
  → Iniciar (se acerca a 53,5 cm de J1, mide estricto 8 s y cosecha lo medido ahí si el brazo tiene plan; limón alto:
  prueba sin los +2 cm) → Volver al cero (90 s propios). 360 s para el primer limón.
- **Modo Recolector:** base quieta, escaneo 3 s, lista guardada, visión apagada, un agarre por vez, sin verificación
  final; saltea limones a < 8° adelante de J1. Planear un limón alto tarda ~30 s por intento.
- **Visión a pedido:** la app la pide en Recolector, Recolección y Visión; sin pedido 30 s (y sin misión) el puente
  apaga el grupo de `start_limon.sh`; prenderla tarda ~21 s. Interruptor `VISION_ON_DEMAND` en `collection_mission.py`.
- Homing fallido → `arm-homing-pending` bloquea el joystick del brazo hasta un homing completo.
- `recolectar.py` (banderín, RODEAR) usa el firmware **serie** del brazo: con la WROOM en micro-ROS no le habla.

## Demo y navegación (`pruebas-esp32/27-aruco-arbol`)
- **Demo: afuera, un banderín ArUco (ID 0) y una hilera de 2-3 arbolitos**; GPS (±20 m) solo para la rúbrica.
- `recolectar.py`: RODEAR y banderín único + BUSCAR **sin probar en el robot**; `banderin.json` sin medir.
- N3 de la guía: detención ✓ (18/11); seguimiento ≈ RODEAR (confirmar con la cátedra); evitación sin hacer.

## Base (`firmware/base`, S3)
- **En la S3: `~/firmware/base_ros_20261121_sin_r`** (env `ros`, `ff9172d`). Flasheo con `--after watchdog-reset`.
  Seta y vuelco sin enclavar: desarman la base (hace falta `armar`); `s` borra fallas de rueda. Watchdog 300 ms.
- Encoder izquierdo arreglado el 21/11 (`w 15 0 0.5` en el aire: izq y der simétricas). Odometría recto < 1 %.
- Si no conecta tras reiniciar la Pi (12 V apagados): matar solo su agente, `~/venvs/esptool/bin/esptool --port
  /dev/serial/by-id/usb-Espressif* --after watchdog-reset chip-id` y relanzar el agente (`agente_base.sh` no arranca
  si ya corre el del brazo: lanzarlo a mano).

## Brazo (WROOM)
- **En la WROOM: `pruebas-esp32/20-brazo-coordinado` env `ros` (micro-ROS), fuente `750ba4c`.** Serie:
  `~/firmware/brazo20_serie_20261119.bin` (imagen completa, en 0x0). **No flashear `firmware/brazo`** (`d3644c8`).
- Si no abre sesión: pulso en EN por RTS (pyserial, DTR bajo) **con los 12 V apagados**.
- **Homing:** `homingDutyMax` 50 % / 1,5 s no despega J3 quieta en el reposo ("J3 CORTADA … no avanza"): moverla un
  poco con el joystick y repetir. Arreglo de fondo (firmware) pendiente.
- `punta.py`: alcance ~48–65 cm de J1; ajuste fino 21/11 (+2,7 cm adelante, ~+2,4 izq). A ~66 cm del piso el camino a
  la canasta sale de la franja de J2/J3. Pinza RDS3218 500/1200 µs (salto directo); "entrar de frente" a vel 0,5.

## ROS 2
- `brazo_ik` 9 pruebas; `mision` 55; `simulacion` 17. `largo_herramienta` = 0 (MEDIR). Sin nodo de seguridad (S2).
- Navegación con el banderín solo en Gazebo; en el real falta la TF de la cámara y medir `hilera_arboles.json`.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector **v4**, ~2–3 img/s, disparidad ~1–2 Hz, 0,40–0,95 m. Foco fijo (izq 2,90 / der
  2,15), calibración del mástil (fx 672,1, baseline 100,3 mm); `approximate_sync` sin tolerancia (desfase mediano 17 ms).
- **Validación de profundidad (22/11):** datos en `datos/validacion_profundidad_20261122/` (Pi y notebook, fuera de
  git), `herramientas/comparar_profundidad.py`. Limón a la vista: estable (~1 mm), error −1 a −3 cm. Detrás de ramas
  el localizador actual da coordenadas falsas (> 3 cm); rechazarlas con < 15 % de píxeles válidos las elimina.
- `ros2 topic hz` desde otra terminal no ve los tópicos tras un rearranque de la visión (Fast DDS): verificar con el
  puente o el log del detector.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Wi-Fi: iPhone de Mathias > LabEquiposMedicos. Después de reiniciar:
  `arrancar_pi.sh`. **Fuente oficial de 27 W**; con el power bank se reinicia. GPS UP501 σ ≈ 21 m.
- Rutas: binarios `~/firmware/`, scripts `~/scripts`, logs `~/logs`, workspaces `~/ros/`, venvs `~/venvs/`.

## Simulación (Gazebo Harmonic, notebook)
- `sim.launch.py mision:=true`: 12 de 12; `mundo:=arbolitos`: 15 de 18 paradas. `base_sim` sigue esperando `r`.
