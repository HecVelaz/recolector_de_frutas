# mision — misión mínima y TF cámara → brazo (ROS 2 Jazzy)

Coordina la demo del objetivo mínimo: **detectar → localizar quieto → `/brazo/objetivo` → agarrar → soltar**.
La base no se mueve (el estéreo se usa con el robot quieto).

| Archivo | Qué tiene |
|---|---|
| `mision/fsm.py` | Máquina de estados **sin ROS** (se prueba sola) |
| `mision/nodo_mision.py` | Nodo `mision`: tópicos, TF y centro del limón |
| `launch/mision.launch.py` | TF `brazo_base → stereo_camera_link` + `brazo_ik` + `mision` |
| `test/test_fsm.py` | Ciclo completo con brazo simulado, muestras inestables, fuera de alcance, fallas, tiempos |

## Estados

```
INICIO ──(ARMADO)──> ESPERAR ──(5 posiciones seguidas a < 2 cm y alcanzable)──> APROXIMAR
   ^ manda armar       ^                                                            │ llego
   cada 1 s            └── SOLTAR (abre) <── RETIRAR (va a reposo) <── AGARRAR (cierra) <┘
Cualquier estado con el brazo moviéndose -> FALLA si: falla del brazo, desarmado, sin /brazo/estado 2 s,
/brazo/ik_estado "inalcanzable" o no llega en 20 s. FALLA manda `s` (detiene J1-J3, la pinza queda como está)
y se queda ahí: reiniciar el nodo.
```

- "Llegó" = las 3 articulaciones con `llego` en `/brazo/estado` **después** de haberlas visto sin `llego` (un
  `llego` viejo, de antes de recibir el objetivo, no cuenta). Si un objetivo coincide con la posición actual, no
  lo ve moverse y termina en FALLA por tiempo.
- En ESPERAR no manda nada si el brazo está desarmado o con falla (al reconectar el agente, el brazo vuelve
  desarmado a propósito: la misión solo arma en INICIO).
- La visión da la **superficie** del limón: el nodo le suma `radio_limon` (3 cm) sobre el rayo de la cámara.
- El objetivo es la **muñeca P3** (lo que resuelve `brazo_ik`), no la punta de la pinza. Ajustar con la prueba.

## TF

```
brazo_base ──(mision.launch.py, MEDIR)──> stereo_camera_link ──(limon.launch.py de vision_estereo)──> camera
```

`/limon/posicion` viene en `camera`, el marco óptico **rectificado** de la cámara izquierda (difiere del físico en
la rotación R de la calibración, unos pocos grados). Como la TF se mide igual contra la cinta, esa diferencia se
absorbe en `roll`/`pitch`/`yaw`. Valores por defecto (suposición): cámara 10 cm detrás del eje de J1 y 35 cm arriba,
mirando al frente. Con el soporte rígido: medir x, y, z con cinta y ajustar los ángulos hasta que un limón
medido a mano dé el mismo punto en `brazo_base`.

## Parámetros

`marco_brazo`, `radio_limon` y los de `Parametros` en `fsm.py`: `n_muestras`, `tol_muestras`, `ventana`,
`t_mov_max`, `t_pinza`, `t_estado_max`, `cierre` (MEDIR: sin aplastar) y `reposo` (donde suelta).

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
colcon test --packages-select mision && colcon test-result --verbose

# Pi: agente del brazo + visión (MODELO=... start_limon.sh) y después
ros2 launch mision mision.launch.py x:=-0.10 z:=0.35          # TF medida
ros2 topic echo /mision/estado --field data
```

Sin hardware: publicar `/brazo/estado` con las 3 en `llego` y un `/limon/posicion` falso en `camera` (con la TF
`stereo_camera_link → camera` de `limon.launch.py`); ver Resultados.

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-28 | `colcon test` (11 pruebas de la FSM) | OK |
| 2026-09-28 | Notebook, launch + brazo simulado + TF óptica: limón en `camera` (0; 0,05; 0,55) → ESPERAR → APROXIMAR con objetivo (0,480; 0; 0,297) m en `brazo_base` (a mano: igual) y `brazo_ik` ok q = (0°; 57,9°; −45,4°) | OK |
| | Con el brazo real y la TF medida | — |
