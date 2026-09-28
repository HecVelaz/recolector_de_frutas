# simulacion — Arturito en Gazebo Harmonic

Hilera de limoneros de la opción B de la guía R2 y el robot con **los mismos tópicos y marcos que los ESP32**, para
probar `mision`, `brazo_ik` y la visión sin hardware. Se arma por etapas:

| Etapa | Qué | Estado |
|---|---|---|
| 1 | Mundo (hilera, obstáculos, GPS de la FIUNA) + base diferencial con IMU y GPS | **hecha** |
| 2 | Brazo (J1-J3 como cadena serie equivalente al cuatro barras) + pinza, respondiendo a `brazo_ik` | **hecha** |
| 3 | Cámaras estéreo + cadena de visión (o posición exacta de Gazebo si YOLO no ve limones sintéticos) | — |
| 4 | Ultrasonidos, bumpers y un nodo que imite `/base/estado` y `/brazo/estado`; `mision` completa | — |

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

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select simulacion && source install/setup.bash
ros2 launch simulacion sim.launch.py                 # gui:=false: solo el servidor (más liviano)
ros2 run teleop_twist_keyboard teleop_twist_keyboard  # otra terminal: i/j/l/, para mover

# brazo (otra terminal): armar y mandar un punto en brazo_base
ros2 topic pub --once /brazo/comando std_msgs/msg/String "{data: armar}"
ros2 topic pub --once /brazo/objetivo geometry_msgs/msg/PointStamped \
  "{header: {frame_id: brazo_base}, point: {x: 0.40, y: 0.25, z: 0.30}}"
ros2 topic pub --once /pinza/cierre std_msgs/msg/Float32 "{data: 100}"
```

Si Gazebo queda colgado después de cortar (pasa al matar solo el proceso del launch, no con Ctrl+C en la terminal):
`pkill -9 -f "[g]z sim"`. Varios servidores a la vez publican en los mismos tópicos y todo se vuelve errático.

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-28 | Notebook, sin ventana, etapa 2: arranca en reposo (muñeca en (0,368; 0; 0,091) m = ejemplo E4); `armar` + `/brazo/objetivo` (0,40; 0,25; 0,30) → `brazo_ik` q = (32,0°; 59,3°; −45,1°) → llega en ~3 s con "llego" en las 3 y la muñeca **exacta** en el objetivo (TF); pinza cerrada y girada 45° (dedos a ≤ 1 mm). Factor de tiempo real 0,6-0,7 con el brazo. 25 pruebas `colcon test` | OK |
| 2026-09-28 | Notebook (i5 de 4 hilos, Intel HD 5500), sin ventana: `/odom` 24,9 Hz, `/imu/data_raw` 49,8 Hz, `/gps/fix` 1,0 Hz con lat −25,3320 lon −57,5190; `/cmd_vel` 0,2 m/s por 6 s → x = 1,16 m (con la rampa); factor de tiempo real 1,0 | OK |
