# simulacion — Arturito en Gazebo Harmonic

Hilera de limoneros de la opción B de la guía R2 y el robot con **los mismos tópicos y marcos que los ESP32**, para
probar `mision`, `brazo_ik` y la visión sin hardware. Se arma por etapas:

| Etapa | Qué | Estado |
|---|---|---|
| 1 | Mundo (hilera, obstáculos, GPS de la FIUNA) + base diferencial con IMU y GPS | **hecha** |
| 2 | Brazo (J1-J3 como cadena serie equivalente al cuatro barras) + pinza, respondiendo a `brazo_ik` | **hecha** |
| 3 | Cámaras estéreo de Gazebo + cadena de visión real (`vision:=yolo`) | **parcial**: estéreo OK, YOLO no reconoce los limones sintéticos sobre la copa |
| 4 | Agarre + `mision` completa con "visión" simulada (`limones_sim`) | **hecha** |
| 5 | Ultrasonidos, bumpers y `/base/estado` imitando el firmware de la base | — |

## Mundo (`worlds/hilera.sdf`)

- Pasillo a lo largo de +x, robot en el origen, **4 limoneros por lado** en x = 1,5 / 3 / 4,5 / 6 m, y = ±0,70 m.
- Limonero (`models/limonero`) con las medidas de **R1**: tronco de 0,23 m y copa entre ~0,21 y 0,53 m (dibujo del
  árbol de la E2); 10 limones verdes entre 0,22 y 0,50 m, dentro de la esfera de trabajo de la consigna (Ø 30 cm,
  centro a ~35 cm del suelo). 2 hundidos en la copa: oclusión parcial.
- Con el robot centrado, los limones del lado del pasillo quedan a ~0,45 m del eje de J1 (la esfera de R1 está en
  r = 450 mm): el brazo sobre el chasis alcanza **19 de 21** (21 de 21 con el robot 5 cm más cerca de la fila).
- 3 obstáculos en el pasillo (caja, balde, cono) en x = 2,0 / 3,5 / 5,0, entre las marcas de parada: hay que
  esquivarlos (y volver al centro del pasillo antes de la marca), pero no tocan al robot parado en una marca ni al
  brazo, que al barrer J1 llega a ~0,70 m delante de la marca. Marca de regreso en x = 7,5 m.
- **Marcas de parada**: franjas blancas en el piso en x = 0,95 / 2,45 / 3,95 / 5,45 m, 0,55 m antes del tronco de
  cada árbol izquierdo. Frenando con el eje de las ruedas de tracción (atrás) sobre una franja, los 3 limones de ese
  árbol quedan en la zona que ve el estéreo y al alcance del brazo (calculado con la geometría de la base).
- `spherical_coordinates` en la FIUNA (aproximado): `/gps/fix` da lat/lon reales; x = este, y = norte.

## Robot (`urdf/arturito.urdf.xacro`)

Base de la **R2 E3**: caja de madera en T de 40 cm de largo y 0,20 m de alto; **adelante** la parte ancha (40 × 23 cm,
con el brazo), **atrás** la angosta (34 × 17 cm) con las ruedas de tracción en los rebajes. Ruedas inflables de 150 mm
(radio 0,075 m) y trocha 0,40 m, como `base_config.h`; `base_link` en el eje de las ruedas, a 8,5 cm del borde
trasero; dos ruedas locas bajo la parte ancha; 20 kg. Estimado (**MEDIR**): trocha, posición del eje y de las ruedas
locas, altura de la caja sobre el piso (0,03 m: tapa a 0,23 m). Tracción con el plugin DiffDrive de Gazebo y los
límites de `CFG_DIF` (0,25 m/s, 1 rad/s, 0,3 m/s², 1,5 rad/s²).

| Tópico | Tipo | Como el firmware |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | sí |
| `/odom` | `nav_msgs/Odometry`, 25 Hz, `odom → base_link` | sí (+ `/tf`) |
| `/imu/data_raw` | `sensor_msgs/Imu`, 50 Hz, `imu_link` | sí (Gazebo además da orientación) |
| `/gps/fix` | `sensor_msgs/NavSatFix`, 1 Hz, `gps_link` | sí |
| `/joint_states` | ruedas | — |

## Brazo y pinza (etapa 2)

- Montado **adelante a la izquierda**, sobre la parte ancha, a ~6 cm del frente y del costado (preliminar), sobre la
  tapa (0,23 m del piso); J1 = 0° mira al frente, paralelo al costado.
- El cuatro barras no entra en URDF (cadena cerrada): se simula la **cadena serie equivalente** (`j2` = q2, `j3o` =
  q3O) y `brazo_sim` convierte el q3 del actuador con `cinematica.py`. Verificado: la muñeca de la cadena serie cae
  donde la directa de la E4 (500 configuraciones). Cerca del pliegue del cuatro barras (q3O ≈ -131,7°, borde del
  espacio de trabajo) dos q3 a ~2,5° dan el mismo q3O: el q3 informado lo decide la continuidad.
- **La base no se mueve cuando trabaja el brazo.** Las articulaciones se mueven por velocidad (fuerza ilimitada) y,
  con las masas reales del brazo, cada movimiento deslizaba la base con las ruedas frenadas (hasta 7 cm y 10° por
  movimiento, siempre hacia adelante). Las masas del brazo van al 5 % (`k_masa`; el brazo se controla
  cinemáticamente) y la base pesa 20 kg (MEDIR): 6 movimientos seguidos, 0,00 cm.
- **`brazo_sim`** reemplaza al firmware del brazo con sus mismos tópicos: `/brazo/joint_cmd` (todo o nada, límites
  de la E4), `/brazo/estado` (mismo texto, 2 Hz), `/brazo/joint_states`, `armar` / `desarmar` / `s`, `/pinza/cierre`
  y `/pinza/giro` (solo ARMADO), perfil trapezoidal como el firmware (30 °/s y 60 °/s² J1, 20 °/s y 40 °/s² J2/J3),
  "llego" a 0,5°. Arranca DESARMADO en la
  pose de reposo de `mision`, q = (0°, 45°, 0°).
- **Herramienta horizontal** (brazo tipo uArm / Dobot Magician): `j_nivel` en la muñeca, al que `brazo_sim` le manda
  -(q2 + q3O), hace lo del paralelogramo. Medido: 0,0° de inclinación en todo el movimiento.
- Pinza: giro J4 alrededor del eje de la herramienta y dos dedos (servos RDS3218) que abren 45 mm cada uno; punto de
  agarre `tcp` a 0,075 m de la muñeca, entre los dedos, y punta a 0,11 m (MEDIR). `/brazo/objetivo` es el TCP
  (`largo_herramienta` = 0,075 en `brazo_ik` y `mision`). Los dedos no tienen colisión.

## Agarre y misión (etapa 4)

- Limones cosechables sin gravedad ni colisión: flotan donde están y la pinza no los empuja.
- `limones_sim` usa la **pose real** del robot en Gazebo (`/world/hilera/dynamic_pose/info`), no `odom`: si la base
  patina, la odometría no se entera.
- **`limones_sim`** hace de visión: publica `/limon/posicion` como `localizador_node` (marco `camera`, superficie
  del limón, hora de la imagen, ~3 Hz) solo si el limón está en el campo visual (33° × 25°, calibración v1) y a
  0,40-0,95 m; y hace el agarre: dedos cerrados (cierre 40 %: sobre un limón de 56 mm) con el TCP a < 3 cm del
  centro → mientras está agarrado, lo pone en el TCP 30 veces por segundo (`set_pose` de Gazebo); dedos abiertos → lo
  deja y lo da por cosechado. Con un DetachableJoint el limón se atrasaba hasta 26 cm al girar J1 (unión blanda con
  las articulaciones movidas por velocidad).
- **Cámara** (`stereo_camera_link` + marco óptico `camera`, como `limon.launch.py`): mástil detrás del brazo, del lado
  izquierdo, a 0,55 m del piso, mirando 40° a la izquierda y 17° abajo (MEDIR; por qué ahí: ver etapa 3). La TF
  brazo → cámara sale del urdf: acá no se usa `mision.launch.py`. Mástil atrás a la izquierda, a (-0,06; 0,14) del
  eje: la Pi 5 iría arriba con las cámaras (ver `docs/CONEXIONES.md`). `limones_sim` solo "ve" lo que el estéreo real
  podría localizar (u >= 271 px, 0,40-0,95 m).
- 12 limones cosechables (3 por árbol de la fila izquierda, `limon_1..12` en el mundo); la fila derecha tiene limones
  fijos de decoración.
- Reposo del brazo: q = (-60°, 45°, 0°), estacionado hacia la derecha (no tapa las cámaras).
- Con `mision:=true` corre `mision` sin cambios. Arrimar el robot con el teleop hasta que el limón quede adelante a la
  izquierda: con el eje de las ruedas (atrás) sobre una **marca de parada** (x = 0,95 / 2,45 / 3,95 / 5,45 m), y
  frenar (`k`). Después la
  misión sola: detecta quieto, aproxima, cierra, retira al reposo y suelta; y sigue con el siguiente limón visible.
- Limitación: el limón soltado queda flotando en el reposo (sin gravedad); falta el cajón.

## Cámaras y cadena real de visión (etapa 3, `vision:=yolo`)

- Dos cámaras de Gazebo como la calibración v1: 640x480, f = 1076,5 px (33,1°), separación 99,26 mm, 10 Hz.
  Imágenes ideales: salen directo como `/left/image_rect` y `/right/image_rect`; `camara_info_sim` publica los
  `camera_info` (con Tx = -f·B en la derecha, que Gazebo no pone). Después corre la cadena de `vision_estereo` sin
  cambios: `disparity_node` (BM, ventana 0,40-0,95 m) → `detector_node` (tu modelo NCNN) → `localizador_node`.
- Texturas (`models/texturas`): el BM necesita textura para encontrar correspondencias; con colores lisos daba 0 %
  de disparidad válida. Con textura: **100 % válida sobre los limones y z = 0,82-0,88 m, igual que una correlación
  a mano**.
- **Hallazgos que valen para el robot real:**
  1. El estéreo solo localiza en la parte derecha de la imagen izquierda: u >= 271 px (con disparidad mínima 112
     y rango 160, más a la izquierda la búsqueda se sale de la imagen derecha). Un limón en el 42 % izquierdo de la
     imagen nunca tiene posición.
  2. El brazo no puede quedar entre las cámaras y la fila: con J1 = 0° en reposo, la barra l2 tapaba los limones
     en la cámara derecha. Reposo con J1 = -60° (estacionado hacia la derecha) y cámaras en un mástil detrás del
     brazo del lado izquierdo, mirando 40° a la izquierda.
- **Lo que no anda:** YOLO (entrenado con fotos reales) no reconoce los limones de Gazebo sobre la copa texturada
  (≤ 0,27 de confianza; sobre copa lisa les daba 0,73-0,79), y marca como limón la copa de un árbol lejano (0,4-0,6),
  que el localizador descarta por distancia. Por eso `/limon/posicion` no sale en esta configuración y la misión
  completa se prueba con `vision:=simulada` (por defecto). En la simulación el detector usa conf 0,25 (en el robot,
  0,40). No reentrenar con imágenes de Gazebo: arruinaría el modelo para los limones reales.
- Requisitos: `sudo apt install ros-jazzy-stereo-image-proc ros-jazzy-image-proc`; `~/vision_estereo` (clonado) con
  el modelo en `modelos/limon_yolo26n_ncnn_model`; `~/yolo_ws` con `yolo_ros` (enlace a
  `~/vision_estereo/ros_pkgs/yolo_ros`); venv `~/yolo_env` con ultralytics, ncnn, torch CPU y **numpy < 2,
  opencv-python < 4.12, contourpy < 1.4** (con numpy 2 falla `cv_bridge` de Jazzy). Lanzar con
  `source ~/yolo_ws/install/setup.bash` después del workspace. Rinde poco en la notebook: cámaras ~4 Hz, disparidad
  ~1 Hz, detector ~1,2 Hz, factor de tiempo real ~0,5.

## Uso

**La simulación no sale de la notebook** (`sim.launch.py` pone `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` y
`GZ_IP=127.0.0.1`). Sin eso, ROS 2 descubría por la red los ESP32 reales conectados a la Pi: la misión simulada
leyó el `/brazo/estado` del brazo real (ARMADO) y los comandos de la simulación le llegaban también a él. **Cada
terminal que hable con la simulación** (teleop, `ros2 topic`) necesita lo mismo:
`export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.

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
| 2026-09-29 | Base real de la R2 E3 (T de 40 cm, ruedas de 150 mm, trocha 0,40, brazo adelante a la izquierda a 6 cm de los bordes, mástil atrás a la izquierda) y marcas recalculadas: **12 de 12 limones cosechados** en las 4 paradas, TCP a 0,0-0,1 cm, base quieta. 30 pruebas `colcon test` | OK |
| 2026-09-29 | Cuatro paradas (usuario: "la segunda no recoge", "la base se mueve", "el limón no queda en el centro"): la base se deslizaba con las ruedas frenadas por los impulsos del brazo (26 cm y 19° en una parada) y la odometría no se enteraba, así que la visión simulada erraba cada vez más; además la caja del pasillo tapaba la parada 2 y, movida a 1,75 m, el brazo le pegaba al barrer. Con perfil trapezoidal, masas del brazo al 5 %, pose real en `limones_sim` y obstáculos en 2,05 / 3,55 / 5,05: **10 de 12 limones cosechados en las 4 paradas**, TCP a 0,0-0,2 cm de cada limón, base quieta (0,0 cm, ≤ 0,01°). Los 2 restantes: uno fuera de alcance y uno fuera de la zona que ve el estéreo | OK |
| 2026-09-29 | Herramienta horizontal y TCP: con `mision:=true`, inclinación de la pinza 0,0° en todo el movimiento; limón agarrado a 0,2 cm del TCP y, durante el retiro, a 0-1,2 cm del TCP (medido en el mismo instante de simulación; con DetachableJoint llegaba a 26 cm). 29 pruebas `colcon test` | OK |
| 2026-09-28 | Con ventana (usuario), la misión no arrancaba: `/brazo/estado` tenía dos publicadores, `brazo_sim` y el ESP32 real del brazo (ARMADO, por la red desde la Pi). Aislada con `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`: único publicador `brazo_sim`, la misión cosecha de nuevo | OK |
| 2026-09-28 | Notebook, sin ventana, etapa 4 de nuevo tras los cambios de la etapa 3 (12 limones que aparecen a los 4 s, reposo J1 = -60°, cámara a 40°): en una misma parada, `mision` cosechó el limón 3 y después el 1 (muñeca a 0,0 cm del centro de cada uno), soltándolos en el reposo | OK |
| 2026-09-28 | Notebook, sin ventana, etapa 3 (`vision:=yolo`): cámaras ~4 Hz, disparidad ~1 Hz, detector ~1,2 Hz; con texturas y la cámara a 40°, disparidad 100 % válida sobre los limones (z = 0,820 y 0,883 m = correlación a mano); YOLO no reconoce los limones sobre la copa texturada (≤ 0,27) → sin `/limon/posicion`. 29 pruebas `colcon test` | parcial |
| 2026-09-28 | Notebook, sin ventana, etapa 4 con `mision:=true`: base a x = 1,02 m → `mision` ESPERAR → APROXIMAR (0,285; 0,394; 0,170) m → `brazo_ik` q = (54,1°; 44,9°; −28,6°) → AGARRAR (limón 1 enganchado, muñeca a 0,1 cm del centro) → RETIRAR al reposo → SOLTAR (cosechado) → ESPERAR. 28 pruebas `colcon test` | OK |
| 2026-09-28 | Notebook, sin ventana, etapa 2: arranca en reposo (muñeca en (0,368; 0; 0,091) m = ejemplo E4); `armar` + `/brazo/objetivo` (0,40; 0,25; 0,30) → `brazo_ik` q = (32,0°; 59,3°; −45,1°) → llega en ~3 s con "llego" en las 3 y la muñeca **exacta** en el objetivo (TF); pinza cerrada y girada 45° (dedos a ≤ 1 mm). Factor de tiempo real 0,6-0,7 con el brazo. 25 pruebas `colcon test` | OK |
| 2026-09-28 | Notebook (i5 de 4 hilos, Intel HD 5500), sin ventana: `/odom` 24,9 Hz, `/imu/data_raw` 49,8 Hz, `/gps/fix` 1,0 Hz con lat −25,3320 lon −57,5190; `/cmd_vel` 0,2 m/s por 6 s → x = 1,16 m (con la rampa); factor de tiempo real 1,0 | OK |
