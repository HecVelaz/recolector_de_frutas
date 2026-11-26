# Estado actual (al 2026-11-26, ~17:00)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **viernes 4/12/2026** (antes 27/11): `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **Modo Recolector y Rodear árbol** andan de punta a punta. Ajuste fino de la pinza rehecho (10 puntos, 26/11);
  última misión: 2 de 4 limones, los dos al 2.º intento (agarre a 60 cm, ahora 55).
- **Riesgos:** **correa de J1** (saltó 2 veces el 26/11 con la pinza enganchada en una rama; 51°); enlace USB de la S3;
  batería (< 11 V el brazo sin fuerza); visión a pedido deja nodos huérfanos; profundidad estéreo inestable > 80 cm.
- **Al cierre:** WROOM con cero (homing del firmware 16:4x), brazo en reposo de homing con un limón en la pinza.
  Falta tensar la correa de J1 y probar un agarre suelto. 12 V los maneja el usuario.

## Recolector y Rodear árbol (`app/robot-bridge/collection_mission.py`, en la Pi)
- **Recolector:** lidar a la maceta (franja 30–36 cm) sin paradas → escaneo → por limón reubica la base para dejarlo a
  **55 cm de J1** (zona 53–58, `LEMON_STOP_MM`, `STOP_RADIUS_MM`, `REACH_MM`) → al final brazo al reposo y **vuelta
  al origen** (marcha atrás sin sensor atrás).
- **Rodear árbol:** paradas antihorario cada 90° en arco (`ARC_AROUND_TREE`), lidar en cada parada (franja 30–36 cm),
  saltea limones más allá del tronco (`beyond_trunk`) y a más de **63 cm de J1** (`AROUND_MAX_MM`).
- **Escaneo:** solo limones con profundidad en el 60 % de las imágenes (`SCAN_STABLE_FRACTION`).
- **Verificación con reintento:** mide de nuevo tras cada agarre; si sigue ahí (< 60 mm), otro intento (`PICK_TRIES` 2).
- **Camino a la canasta** (`punta.py`, pruebas-esp32 `af172b0`, **sin probar**): con el limón, tirón, muñeca,
  arrastre 5° con J1, salida horizontal; después **pliega sin girar J1** (punta a ~25 cm) y recién gira a 130°.

## Agarre
- `ajuste_agarre.json` (Pi `~/scripts/20-brazo-coordinado/resultados/`): 10 puntos del 26/11, limones a 52–57 cm de J1;
  constantes +31,9 / +38,6 / +11,9 mm (adelante, izquierda, arriba). `GRASP_RAISE_MM` 0. **No tocar de a una.**
- Cámara (TF del 12/11, 9 puntos, error esperado ~22 mm): 13,8° hacia abajo, mira a la izquierda (90,6°).

## TFmini-S (lidar lateral izquierdo)
- Verde TX → WROOM GPIO 13, rojo 5 V, negro GND. `/range/lidar_izq` (Range, 10 Hz, NaN si inválido).
- 14 cm del suelo, **19,1 cm adelante y 13 cm a la izquierda de J1**. Lectura ≈ D − 27,3 cm (D = J1 → eje del árbol).

## App Arturito y puente (`app/`)
- **App 0.15.6** en el Poco X6 Pro; 0.15.3 en la Xiaomi Pad 5. Modos: manual | Recolector | Recolección | Rodear árbol.
- Conexión por Tailscale `http://100.116.96.71:18006`; clave en `~/arturito-bridge-0.4.0/data/.connection-token`.
- **Puente** en la Pi `~/arturito-bridge-0.9.0` (Python `~/arturito-bridge-0.4.1/.venv`, datos `~/arturito-bridge-0.4.0/data`),
  arranca con `arturito.service`. **Cargar un cambio:** copiar el archivo (guardar el viejo `.antes_*`), cortar
  `pkill -f "^/home/r2d2/arturito-bridge-0.4.1/.venv/bin/python run_pi.py"` y correr `arrancar_pi.sh`.
  `bridge.log` (rechazos y cortes con el estado del brazo; los mensajes del homing no quedan). Informes: `data/missions/*.json`.
- **Homing de la app** (`physical_control.home_recovery`, hasta 3): canasta → J1 a 100° plegado; plegado → intermedio
  (J2 46,7 / J3 50); J2 > 25° → `mv <J1 actual> 17 4` (J1 no se mueve); fuera de la franja sube J2. Exige el frente fresco.
- **Correa saltada:** el puente corta el brazo si J1 aprieta su final de carrera con el encoder > 6° (`J1_SWITCH_MAX_Q`),
  salvo en el homing del firmware y con el joystick del brazo. Recuperación a mano: J2/J3 al reposo con J1 quieta
  (`mv <J1> 17 4` por `/brazo/comando`) y `h`.
- Suite del puente: 138 pruebas OK **en la Pi** (rsync a `/tmp/puente_pruebas`, `~/arturito-bridge-0.4.1/.venv/bin/python
  -m unittest discover -s tests`); la local falla 13 por el entorno.

## Brazo (WROOM)
- **`pruebas-esp32/20-brazo-coordinado` env `ros` con TFmini-S** (`~/arturito-build/20261125_lidar/firmware.bin`, app en
  0x10000). Serie (para `punta.py ajustar`): `~/arturito-build/20261126_ajuste/brazo20_serie_67f5d7f.bin`.
  **No flashear `firmware/brazo`.** Respaldo: `~/arturito-build/20261126_ajuste/respaldo_wroom_20261126.bin`.
- Finales de carrera: el firmware los usa **solo en el homing** (los `mv` y el joystick no frenan con ellos). En el
  homing con cero, si lo toca rápido se aleja ~2° y lo toma despacio.
- J1 "sin cuentas" con pasos muy chicos (< ~1°). Tras soltar, J2 a veces queda en ~54° (fuera de la zona plegada).

## Base (S3, `firmware/base`)
- En la S3 `~/firmware/base_ros_20261121_sin_r` (env `ros`). Si deja de publicar con el USB presente: 12 V apagados,
  desenchufar el USB o reiniciar la Pi (`esptool --before usb-reset` dio Errno 71 el 26/11; sin sudo sin clave).
  `arrancar_pi.sh` no relanza el agente de la S3 si ya corre el del brazo.

## Visión (repo `HecVelaz/vision_estereo`)
- `bash ~/scripts/vision.sh`: detector v4, ~2 img/s, profundidad 0,40–0,95 m. YOLO estable; la profundidad estéreo
  falla en limones a > ~80 cm. **Pausa a pedido (`VISION_STOP`) deja vivos detector y localizador** → huérfanos.
- En la Pi `ros2 topic echo` se cuelga seguido: usar `timeout -k 2 8`. `pkill -f` siempre con patrón anclado.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Fuente oficial de 27 W. `arturito.service` al prender.
