# mision — misión mínima y TF cámara → brazo (ROS 2 Jazzy)

Coordina la demo del objetivo mínimo: **detectar → localizar quieto → `/brazo/objetivo` → agarrar → soltar**.
Con `autonomo:=true` además **recorre la hilera sola** (`recorrido.py`): avanza de corrido por el centro del pasillo,
frena cuando YOLO (`/yolo/detecciones`) ve un limón en la zona que localiza el estéreo (u >= 271 px, 0,40-0,95 m por
el tamaño de la caja), deja mirar a la misión con la base quieta, se arrima lo mínimo si el limón está fuera de
alcance, retrocede (con tope) si un limón quedó atrás en la zona ciega de la imagen, y esquiva los obstáculos del
pasillo con los 3 HC-SR04 del frente (lado con lugar, peor caso del cono de ±7,5°, carril y = ±0,25 m) hasta el fin
de la hilera. Posición: avance de las ruedas (`/odom`) y **rumbo del giróscopo** (`/imu/data_raw`): en los giros
cerrados las ruedas patinan y la odometría sola dejaba el robot 13 cm corrido sin enterarse. Supone que arranca en
el centro del pasillo mirando a lo largo.

| Archivo | Qué tiene |
|---|---|
| `mision/fsm.py` | Máquina de estados **sin ROS** (se prueba sola) |
| `mision/recorrido.py` | Recorrido autónomo **sin ROS**: avanzar, mirar, arrimar, esquivar; odometría con giróscopo |
| `mision/nodo_mision.py` | Nodo `mision`: tópicos, TF y centro del limón (y el recorrido con `autonomo:=true`) |
| `launch/mision.launch.py` | TF `brazo_base → stereo_camera_link` + `brazo_ik` + `mision` |
| `test/test_fsm.py` | Ciclo completo con brazo simulado, muestras inestables o viejas, fuera de alcance, fallas, estados viejos, tiempos |
| `test/test_recorrido.py` | Avance y frenado por YOLO, arrime, retroceso con tope, esquive, bloqueo, giróscopo |

## Estados

```
INICIO ──(ARMADO)──> ESPERAR ──(brazo quieto + 5 posiciones seguidas a < 2 cm y alcanzable)──> APROXIMAR
   ^ manda armar       ^                                                            │ llego
   cada 1 s            └── SOLTAR (abre) <── RETIRAR (va a reposo) <── AGARRAR (cierra) <┘
Cualquier estado con el brazo moviéndose -> FALLA si: falla del brazo, desarmado, sin /brazo/estado 2 s,
/brazo/ik_estado "inalcanzable" o no llega en 20 s. FALLA manda `s` (detiene J1-J3, la pinza queda como está)
y se queda ahí: reiniciar el nodo. Al cerrar el nodo (Ctrl+C, fin del launch) también manda `s`.
```

- "Llegó" = `/brazo/joint_states` a menos de 1° de los ángulos que calculó `brazo_ik` para **este** objetivo
  (`/brazo/joint_cmd`), quieto (< 0,02 rad/s), y `llego` en las 3 en `/brazo/estado`. Un estado viejo no alcanza:
  la posición de un movimiento anterior no coincide con el objetivo nuevo.
- Las fallas y el desarmado se atienden en el mismo callback de `/brazo/estado` (un estado bueno posterior no las
  tapa). Una articulación `SIN_CERO` cuenta como falla.
- En ESPERAR solo junta muestras con el brazo armado, con cero, sin falla, quieto (`llego`) y con `/brazo/estado`
  de hace menos de 2 s (al reconectar el agente, el brazo vuelve desarmado a propósito: la misión solo arma en
  INICIO).
- Las muestras usan el tiempo de la imagen: se descartan las de más de 1 s (`edad_max_imagen`) y las repetidas.
- La visión da la **superficie** del limón: el nodo le suma `radio_limon` (3 cm) sobre el rayo de la cámara.
- El objetivo es el **punto de agarre (TCP)**: `brazo_ik` lo pasa a muñeca con `largo_herramienta` (herramienta
  horizontal, brazo tipo uArm). `mision` usa el mismo `largo_herramienta` para ver si el limón es alcanzable.

## TF

```
brazo_base ──(mision.launch.py, MEDIR)──> stereo_camera_link ──(limon.launch.py de vision_estereo)──> camera
```

`/limon/posicion` viene en `camera`, el marco óptico **rectificado** de la cámara izquierda (difiere del físico en
la rotación R de la calibración, unos pocos grados). Como la TF se mide igual contra la cinta, esa diferencia se
absorbe en `roll`/`pitch`/`yaw`. **Sin valores por defecto**: el launch no arranca sin los 6 argumentos, para no
mover el brazo con una TF inventada. Con el soporte rígido: medir x, y, z con cinta y ajustar los ángulos hasta que
un limón medido a mano dé el mismo punto en `brazo_base`.

**Pendiente antes de agarrar de verdad:** medir `largo_herramienta` (muñeca P3 → centro del agarre entre los dedos,
en horizontal) y pasarlo igual a `brazo_ik` y a `mision`. Si el centro del agarre no queda a la altura de la muñeca,
hay que sumar ese desfase vertical (hoy no está contemplado). Hasta entonces, probar con `cierre` bajo y la mano en
la seta.

## Parámetros

`marco_brazo`, `radio_limon`, `edad_max_imagen` y los de `Parametros` en `fsm.py`: `n_muestras`, `tol_muestras`,
`ventana`, `t_mov_max`, `t_pinza`, `t_estado_max`, `tol_q`, `tol_v`, `cierre` (MEDIR: sin aplastar) y `reposo`.

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
colcon test --packages-select mision && colcon test-result --verbose

# Pi: agente del brazo + visión (MODELO=... start_limon.sh) y después
ros2 launch mision mision.launch.py x:=-0.10 y:=0 z:=0.35 roll:=0 pitch:=0 yaw:=0   # TF medida
ros2 topic echo /mision/estado --field data
```

Sin hardware: publicar `/brazo/estado` con las 3 en `llego`, `/brazo/joint_states` y un `/limon/posicion` falso
en `camera` con la hora de cada mensaje (`ros2 topic pub` con `stamp: now` repite la misma hora y se descarta),
más la TF `stereo_camera_link → camera` de `limon.launch.py`; ver Resultados.

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-28 | `colcon test` (11 pruebas de la FSM) | OK |
| 2026-09-28 | Notebook, launch + brazo simulado + TF óptica: limón en `camera` (0; 0,05; 0,55) → ESPERAR → APROXIMAR con objetivo (0,480; 0; 0,297) m en `brazo_base` (a mano: igual) y `brazo_ik` ok q = (0°; 57,9°; −45,4°) | OK |
| 2026-09-28 | Revisión de Codex (11 hallazgos). Aplicados: estado vencido, falla tapada por un estado posterior, llegada por posición contra `joint_cmd` (antes: "no llegó → llegó", engañable por estados viejos y con timeout falso si ya estaba en el objetivo), tiempo de imagen y repetidas, `s` al cerrar, TF obligatoria, `SIN_CERO` y brazo quieto antes de muestrear, `n_muestras = 1`. Pendiente: desfase muñeca → pinza (sin medidas de la pinza). No aplicado: no abrir la pinza en INICIO (arrancar la misión es un acto del operador con el brazo en reposo) | 17 pruebas OK |
| 2026-09-28 | Notebook, de nuevo tras la revisión: APROXIMAR con el mismo objetivo; con `joint_states` en reposo y `llego` en el estado **no** cierra; Ctrl+C → `s` en `/brazo/comando`; sin argumentos de TF el launch no arranca | OK |
| | Con el brazo real y la TF medida | — |
