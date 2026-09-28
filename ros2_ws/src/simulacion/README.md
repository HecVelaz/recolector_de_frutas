# simulacion — Arturito en Gazebo Harmonic

Hilera de limoneros de la opción B de la guía R2 y el robot con **los mismos tópicos y marcos que los ESP32**, para
probar `mision`, `brazo_ik` y la visión sin hardware. Se arma por etapas:

| Etapa | Qué | Estado |
|---|---|---|
| 1 | Mundo (hilera, obstáculos, GPS de la FIUNA) + base diferencial con IMU y GPS | **hecha** |
| 2 | Brazo (J1-J3 como cadena serie equivalente al cuatro barras) + pinza, respondiendo a `brazo_ik` | **hecha** |
| 3 | Cámaras estéreo de Gazebo + cadena de visión real (YOLO puede no ver limones sintéticos) | — |
| 4 | Agarre + `mision` completa con "visión" simulada (`limones_sim`) | **hecha** |
| 5 | Ultrasonidos, bumpers y `/base/estado` imitando el firmware de la base | — |

## Mundo (`worlds/hilera.sdf`)

- Pasillo a lo largo de +x, robot en el origen, **4 limoneros por lado** en x = 1,5 / 3 / 4,5 / 6 m, y = ±0,70 m.
- Limonero (`models/limonero`) con las medidas de **R1**: tronco de 0,23 m y copa entre ~0,21 y 0,53 m (dibujo del
  árbol de la E2); 10 limones verdes entre 0,22 y 0,50 m, dentro de la esfera de trabajo de la consigna (Ø 30 cm,
  centro a ~35 cm del suelo). 2 hundidos en la copa: oclusión parcial.
- Con el robot centrado, los limones del lado del pasillo quedan a ~0,45 m del eje de J1 (la esfera de R1 está en
  r = 450 mm): el brazo sobre el chasis alcanza **19 de 21** (21 de 21 con el robot 5 cm más cerca de la fila).
- 3 obstáculos en el pasillo (caja, balde, cono) y marca de regreso en x = 7,5 m.
- `spherical_coordinates` en la FIUNA (aproximado): `/gps/fix` da lat/lon reales; x = este, y = norte.

## Robot (`urdf/arturito.urdf.xacro`)

Radio 0,05 m y trocha 0,30 m de `base_config.h`; chasis 0,50 × 0,24 × 0,15 m **supuesto (MEDIR)**. Tracción con el
plugin DiffDrive de Gazebo y los límites de `CFG_DIF` (0,25 m/s, 1 rad/s, 0,3 m/s², 1,5 rad/s²).

| Tópico | Tipo | Como el firmware |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | sí |
| `/odom` | `nav_msgs/Odometry`, 25 Hz, `odom → base_link` | sí (+ `/tf`) |
| `/imu/data_raw` | `sensor_msgs/Imu`, 50 Hz, `imu_link` | sí (Gazebo además da orientación) |
| `/gps/fix` | `sensor_msgs/NavSatFix`, 1 Hz, `gps_link` | sí |
| `/joint_states` | ruedas | — |

## Brazo y pinza (etapa 2)

- Montado en la **esquina delantera izquierda** del chasis, junto a las ruedas, a 0,20 m del piso; J1 = 0° mira al
  frente, paralelo al costado. Posición supuesta (`brazo_x`, `brazo_y` en el xacro): MEDIR.
- El cuatro barras no entra en URDF (cadena cerrada): se simula la **cadena serie equivalente** (`j2` = q2, `j3o` =
  q3O) y `brazo_sim` convierte el q3 del actuador con `cinematica.py`. Verificado: la muñeca de la cadena serie cae
  donde la directa de la E4 (500 configuraciones). Cerca del pliegue del cuatro barras (q3O ≈ -131,7°, borde del
  espacio de trabajo) dos q3 a ~2,5° dan el mismo q3O: el q3 informado lo decide la continuidad.
- **`brazo_sim`** reemplaza al firmware del brazo con sus mismos tópicos: `/brazo/joint_cmd` (todo o nada, límites
  de la E4), `/brazo/estado` (mismo texto, 2 Hz), `/brazo/joint_states`, `armar` / `desarmar` / `s`, `/pinza/cierre`
  y `/pinza/giro` (solo ARMADO), perfil a 30 °/s (J1) y 20 °/s (J2, J3), "llego" a 0,5°. Arranca DESARMADO en la
  pose de reposo de `mision`, q = (0°, 45°, 0°).
- Pinza: giro J4 y dos dedos (servos RDS3218); punta de los dedos 0,11 m más allá de la muñeca (MEDIR). Los dedos
  no tienen colisión ni gravedad: el agarre se hará fijando el limón a la pinza al cerrar (etapa 4).

## Agarre y misión (etapa 4)

- **4 limones cosechables** (`limon_1..4` en `worlds/hilera.sdf`), uno por árbol de la fila izquierda, del lado del
  pasillo, entre 0,32 y 0,45 m de altura. Sin gravedad ni colisión: flotan donde están y la pinza no los empuja.
- **`limones_sim`** hace de visión: publica `/limon/posicion` como `localizador_node` (marco `camera`, superficie
  del limón, hora de la imagen, ~3 Hz) solo si el limón está en el campo visual (33° × 25°, calibración v1) y a
  0,40-0,95 m; y hace el agarre: dedos cerrados con la muñeca a < 3 cm del centro → engancha el limón a la pinza
  (DetachableJoint); dedos abiertos → lo suelta y lo da por cosechado. Los enganches arrancan enganchados: el nodo
  los suelta en los primeros 5 s.
- **Cámara** (`stereo_camera_link` + marco óptico `camera`, como `limon.launch.py`): mástil del lado derecho a 0,50 m
  del piso, mirando 55° a la izquierda y 14° abajo (MEDIR). Mirando de costado (90°) veía limones detrás del alcance
  de J1 (±75°). La TF brazo → cámara sale del urdf: acá no se usa `mision.launch.py`.
- Con `mision:=true` corre `mision` sin cambios. Arrimar el robot con el teleop hasta que el limón quede adelante a la
  izquierda: **x ≈ 1,0 / 2,6 / 4,0 / 5,5 m** para los limones 1 a 4, y frenar (`k`). Después la misión sola: detecta
  quieto, aproxima, cierra, retira al reposo y suelta.
- Limitación: el limón soltado queda flotando en el reposo (sin gravedad); falta el cajón.

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select simulacion && source install/setup.bash
ros2 launch simulacion sim.launch.py                 # gui:=false: solo el servidor (más liviano); mision:=true
ros2 run teleop_twist_keyboard teleop_twist_keyboard  # otra terminal: i/j/l/, para mover

# brazo (otra terminal): armar y mandar un punto en brazo_base
ros2 topic pub --once /brazo/comando std_msgs/msg/String "{data: armar}"
ros2 topic pub --once /brazo/objetivo geometry_msgs/msg/PointStamped \
  "{header: {frame_id: brazo_base}, point: {x: 0.40, y: 0.25, z: 0.30}}"
ros2 topic pub --once /pinza/cierre std_msgs/msg/Float32 "{data: 100}"
```

Si Gazebo o algún nodo queda colgado después de cortar (pasa al matar solo el proceso del launch, no con Ctrl+C en la
terminal): `pkill -9 -f "[g]z sim"` y `pkill -9 -f "[b]razo_sim|[l]imones_sim|[p]arameter_bridge"`. Un `brazo_sim`
viejo armado engaña a la misión, y varios Gazebo a la vez publican en los mismos tópicos: todo se vuelve errático.

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-28 | Notebook, sin ventana, etapa 4 con `mision:=true`: base a x = 1,02 m → `mision` ESPERAR → APROXIMAR (0,285; 0,394; 0,170) m → `brazo_ik` q = (54,1°; 44,9°; −28,6°) → AGARRAR (limón 1 enganchado, muñeca a 0,1 cm del centro) → RETIRAR al reposo → SOLTAR (cosechado) → ESPERAR. 28 pruebas `colcon test` | OK |
| 2026-09-28 | Notebook, sin ventana, etapa 2: arranca en reposo (muñeca en (0,368; 0; 0,091) m = ejemplo E4); `armar` + `/brazo/objetivo` (0,40; 0,25; 0,30) → `brazo_ik` q = (32,0°; 59,3°; −45,1°) → llega en ~3 s con "llego" en las 3 y la muñeca **exacta** en el objetivo (TF); pinza cerrada y girada 45° (dedos a ≤ 1 mm). Factor de tiempo real 0,6-0,7 con el brazo. 25 pruebas `colcon test` | OK |
| 2026-09-28 | Notebook (i5 de 4 hilos, Intel HD 5500), sin ventana: `/odom` 24,9 Hz, `/imu/data_raw` 49,8 Hz, `/gps/fix` 1,0 Hz con lat −25,3320 lon −57,5190; `/cmd_vel` 0,2 m/s por 6 s → x = 1,16 m (con la rampa); factor de tiempo real 1,0 | OK |
