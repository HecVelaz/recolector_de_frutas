# Estado actual (al 2026-11-23, ~18:45)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **27/11/2026**: `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **Recolección desde la app (21/11):** 1 limón con acercamiento y vuelta al cero; **2 de 3 sin mover la base**.
  Limonero subido 19 cm → limones a ~63 cm del piso: el agarre pasa ~3 cm abajo (sin camino seguro a la canasta más
  arriba). Mejor zona: limón a 50–55 cm de J1 y **40–55 cm del piso**, a la izquierda y ≥ 8° adelante de J1.
- **Riesgos abiertos:** la Pi se apaga de golpe (~6 veces el 21/11; alimentación sin resolver); cortes del enlace de
  la S3 (6 el 23/11, sin desconexión USB; causa sin encontrar, ver Base); homing con "J3 CORTADA" desde el reposo.
- Misión ROS (`ros2_ws/src/mision`): navegación con el banderín solo en Gazebo. Potencia v0.6: falta portafusible,
  XT60 y divisor 100 k / 30 k. **Manual v1.1** en `docs/manual/` (falta subir el PDF a Drive).

## App Arturito y puente (`app/`)
- **App 0.15.1** en la Xiaomi Pad 5. Control: **Modo manual | Recolector | Recolección**. Brazo y pinza: velocidad del
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
- **Estados del brazo** (firmware 20): 0 suelta, 1 yendo, 2 llegó, 3 firme, 4 frenada, 5 mov, 6 homing. El puente
  acepta 1 moviendo, 1 s después de soltar y hasta 2 s con el brazo quieto (corrección del sostén).
- **Recolección:** homing → Calcular cero (3,8 s, criterio flojo; sin limón guarda la pose y al iniciar gira ±15/25°)
  → Iniciar (se acerca a **60 cm** de J1 desde el 23/11, sin probar; más cerca no retrocede, mide estricto 8 s y cosecha lo medido ahí si el brazo tiene plan; limón alto:
  prueba sin los +2 cm) → Volver al cero (90 s propios). 360 s para el primer limón.
- **Modo Recolector:** base quieta, escaneo 3 s, lista guardada, visión apagada, un agarre por vez, sin verificación
  final; saltea limones a < 8° adelante de J1. Planear un limón alto tarda ~30 s por intento.
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
- `punta.py` (23/11, sin probar en el robot): entra horizontal desde 20/15/10/7/5 cm, la más larga que entre
  (= distancia del limón a J1 − ~44 cm); tras cerrar **baja** 5 cm (antes subía) y sigue igual. Alcance ~48–65 cm de J1; ajuste fino 21/11 (+2,7 cm adelante, ~+2,4 izq). A ~66 cm del piso el camino a
  la canasta sale de la franja de J2/J3. Pinza RDS3218 500/1200 µs (rampa 45 °/s al arrancar); "entrar de frente" a vel 0,5.

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
