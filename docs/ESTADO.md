# Estado actual (al 2026-11-27, noche)

Foto del estado (se reescribe en cada `/cerrar`). Historia: `BITACORA.md`; lo que falta y el plan hasta la demo
del **viernes 4/12/2026** (antes 27/11): `PENDIENTES.md`. **El estado va acá, nunca en `CLAUDE.md`.**

## Avance
- **El brazo se rompió (26/11 tarde): se está reimprimiendo.** Hasta entonces, Recolector y Rodear árbol andaban de
  punta a punta (última misión: 2 de 4 limones al 2.º intento, con agarre a 60 cm; ahora 55). Al volver: tensar la
  correa de J1, homing, ajuste fino si se movió algo y un Recolector completo con la visión nueva.
- **Riesgos:** **correa de J1** (saltó 2 veces el 26/11 con la pinza enganchada en una rama; 51°); enlace USB de la S3;
  batería (< 11 V el brazo sin fuerza); **visión al sol sin probar** (NoIR, detector v4); hoja delante del limón.
- **J1 sigue con la correa GT2 18 → 84** (engranajes 15 → 80 descartados el 27/11; firmware sin cambios).
  **J1-J3 no se mueven a mano** (reductoras duras, rompe lo impreso): probar con el joystick, en pasos cortos.
- **Buzzer (H8):** `ros2 run mision nodo_buzzer`, probado en la Pi sin el buzzer (GPIO 27); falta reiniciar, conectarlo
  y oírlo (`PENDIENTES` 1b). Faltan luz y habilitación del brazo. Planilla de componentes al día (27/11).
- **Guía del día de la demo:** `docs/html/checklist_demo.html` (publicada, ID en `CONEXIONES.md`).
- **Al cierre:** visión pausada (la prende la pestaña «Visión» de la app); arbolito en el lab con 3 limones a 74-79 cm.

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
  (J2 46,7 / J3 50); J2 > 25° → `mv <J1 actual> 17 4` (J1 no se mueve); fuera de la franja sube J2. Solo brazo y homing ya no exigen el
  HC-SR04 del frente (base y misiones sí).
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
  `arrancar_pi.sh` relanza el agente de la S3 aunque corra el del brazo (`agente_base.sh` mira solo el de la S3).

## Visión (repo `HecVelaz/vision_estereo`, `671ac3b`, igual en la Pi y en GitHub)
- `bash ~/scripts/vision.sh` (la lanza el puente a pedido); apagar con `~/vision_estereo/scripts/parar_vision.sh`
  (TERM al grupo de procesos, KILL a los 5 s: sin huérfanos). Nunca `pkill` sueltos.
- Cámaras **sincronizadas** (`SyncMode` de libcamera, 0,03 ms entre izq. y der.), 640×480 a 10 FPS. Detector v4,
  ~3 img/s; SGBM con los valores por defecto de `stereo_image_proc` (ventana 15) a ~1,7-2,5 pares/s.
- Profundidad **0,40-1,15 m** (antes 0,95). Error contra cinta: −0,8 a −2,6 cm a 74-79 cm; ~±1,5 cm a ~1 m.
- Localizador: el **grupo de profundidad más cercano** de la caja (el más grande o el más centrado elegían el fondo:
  el limón liso solo tiene disparidad en el borde). **Una hoja delante, dentro de la caja, gana** (61 cm en vez de 94).
  Chequeo por tamaño (`diametro`) programado y apagado: las cajas no sirven para estimar el diámetro (5,5-8,5 cm).
- En la Pi `ros2 topic echo` se cuelga seguido: usar `timeout -k 2 8`. `pkill -f` siempre con patrón anclado.

## Pi 5
- `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`). Fuente oficial de 27 W. `arturito.service` al prender.
