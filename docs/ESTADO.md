# Estado actual (al 2026-11-26, ~00:10)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **viernes 4/12/2026** (antes 27/11): `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **Modo Recolector y Rodear árbol** andan de punta a punta con arco y lidar, pero **la pinza falla por unos cm**
  (usuario, 25/11): casi todos los limones salen al 2.º intento (verificación con reintento). Plan: ajuste fino.
- **Riesgos:** enlace USB de la S3 (se colgó una vez y cortó dos veces por datos viejos el 25/11); pinza; batería
  (< 11 V el brazo sin fuerza); J1 en la canasta; visión a pedido deja nodos huérfanos.
- **Al cierre:** Pi recién reiniciada (00:06), visión ~2 FPS, agentes con sesión. **WROOM sin cero** (`c=000`):
  hacer homing (el brazo quedó cerca de J1 90°, J2 36°, J3 35°). 12 V los maneja el usuario.

## Rodear árbol (`app/robot-bridge/collection_mission.py`, en la Pi desde `eb6d2d8`)
- Paradas antihorario cada 90° (1–4 desde la app); tronco del primer escaneo (lateral corregido con el lidar en cada
  parada, `trunk_from_lidar`; el de adelante sale de los limones y erra: 27–40 cm en vez de 15).
- **Entre paradas en arco** (`ARC_AROUND_TREE`): girar hasta tener el tronco sobre el eje de las ruedas → arco a
  8 cm/s (radio y rumbo por odometría) → rumbo de la parada. Bloqueado o con objetos guardados: saltos de 45°.
  Probado en el robot (25/11): 3 arcos bien; llega a ±12 cm y el lidar corrige.
- **Lidar en cada parada** (`lidar_trim`): mediana de 5; **franja 20–30 cm** (usuario, 25/11 noche; corrige a 25;
  confía en 12–60 cm). 26-sim recomendaba 40–44 cm (100 %); con 20–30 los limones quedan a ~40 cm de J1.
- **La pinza no pasa del tronco:** se saltean los limones más a la izquierda que el tronco (`beyond_trunk`).
- **Verificación con reintento:** tras cada agarre mide de nuevo (brazo en la canasta); si hay un limón a < 60 mm
  (`VERIFICAR_MM`) otro intento (`PICK_TRIES` 2). Sin profundidad útil 4 s = "no se ve" (no corta la misión).
- HC-SR04: lecturas sin eco sueltas toleradas 0,5 s (`ULTRASONIC_HOLD_S`, `ros_source.py`).

## TFmini-S (lidar lateral izquierdo)
- Verde TX → WROOM GPIO 13, rojo 5 V, negro GND, blanco aislado. `/range/lidar_izq` (Range, 10 Hz, NaN si inválido).
- Montaje (usuario): 14 cm del suelo, 13,4 cm detrás del frente, **19,1 cm adelante y 13 cm a la izquierda de J1**.
  Maceta redonda de 29,5–30 cm × 22 cm. Lectura ≈ D − 27,3 cm (D = J1 → eje del árbol). Tensión sin medir.
- App 0.15.6 en el Poco: fila «LiDAR izquierdo» en Estado.

## App Arturito y puente (`app/`)
- **App 0.15.6** en el Poco X6 Pro; 0.15.3 en la Xiaomi Pad 5. Modos: manual | Recolector | Recolección | Rodear árbol.
- Conexión por Tailscale `http://100.116.96.71:18006`; clave en `~/arturito-bridge-0.4.0/data/.connection-token`.
  Teléfono con ~1 s de demora fuera de la red de la Pi.
- **Puente** en la Pi `~/arturito-bridge-0.9.0` (Python `~/arturito-bridge-0.4.1/.venv`, datos `~/arturito-bridge-0.4.0/data`),
  arranca con `arturito.service`. **Cargar un cambio:** copiar el archivo (guardar el viejo `.antes_*`), cortar
  `pkill -f "^/home/r2d2/arturito-bridge-0.4.1/.venv/bin/python run_pi.py"` y correr `arrancar_pi.sh`.
  `bridge.log` se acumula (rechazos y cortes con el estado del brazo). Informes: `data/missions/*.json`.
- **`arrancar_pi.sh` no relanza el agente de la S3** si ya corre el del brazo (`agente_base.sh` ve "algún agente").
- **Homing** (`physical_control.home_recovery`, hasta 3): en la canasta primero J1 a 100° plegado; plegado → intermedio
  (J2 46,7 / J3 50); J2 > 25° → `mv 3 17 4`; fuera de la franja sube J2. **Exige el frente fresco** (`control_gate`).
- Suite del puente: 133 pruebas OK (`/tmp/arturito-lidar-venv/bin/python -m unittest discover -s tests`; `.venv` local es de Windows).

## Brazo (WROOM)
- **`pruebas-esp32/20-brazo-coordinado` env `ros` con TFmini-S (`67f5d7f`)**, flasheado el 25/11 (app en 0x10000).
  Respaldo previo: `~/arturito-build/20261125_lidar/respaldo_wroom_20261125.bin`. **No flashear `firmware/brazo`.**
- Canasta: J1 sale con el joystick (`jog_j1_out`); si queda plegado con J2 > 50,7° baja J3 a 55° con `j` (`unfold_j3`).
  Tras soltar, J2 a veces queda en ~54° (fuera de la zona plegada 42–51°): causa sin ver.
- Agarre: `GRASP_RAISE_MM` 32,5 (puente), `AGARRAR_ADELANTE` −27, `AGARRAR_IZQUIERDA` −7,5 (punta.py); ajuste fino
  de 5 puntos del 21/11 (`~/scripts/20-brazo-coordinado/resultados/ajuste_agarre.json`). **No tocar de a una.**
- Cámara (TF del 12/11, 9 puntos, error esperado ~22 mm): 13,8° hacia abajo, mira a la izquierda (90,6°).

## Base (S3, `firmware/base`)
- En la S3 `~/firmware/base_ros_20261121_sin_r` (env `ros`). Si deja de publicar con el USB presente: 12 V apagados,
  `esptool --before usb-reset --after watchdog-reset chip-id` y agente a mano. Al prender puede quedar en bootloader
  (`arrancar_pi.sh` lo detecta). Enlace: `pings_fallidos` y `cortes` en `/base/estado`.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector v4, ~2 img/s, profundidad 0,40–0,95 m (el localizador no publica si no ubica
  ningún limón). **Pausa a pedido (`VISION_STOP`) deja vivos detector y localizador** → huérfanos; el 25/11 la cámara
  derecha quedó trabada y hizo falta reiniciar la Pi.
- En la Pi `ros2 topic echo` se cuelga seguido: usar `timeout -k 2 8`. `pkill -f` siempre con patrón anclado.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Fuente oficial de 27 W. `arturito.service` al prender.
