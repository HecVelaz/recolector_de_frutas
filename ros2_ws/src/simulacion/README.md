# simulacion — Arturito en Gazebo Harmonic

Hilera de limoneros de la opción B de la guía R2 y el robot con **los mismos tópicos y marcos que los ESP32**, para
probar `mision`, `brazo_ik` y la visión sin hardware. Se arma por etapas:

| Etapa | Qué | Estado |
|---|---|---|
| 1 | Mundo (hilera, obstáculos, GPS de la FIUNA) + base diferencial con IMU y GPS | **hecha** |
| 2 | Brazo (J1-J3 como cadena serie equivalente al cuatro barras) + pinza, respondiendo a `brazo_ik` | — |
| 3 | Cámaras estéreo + cadena de visión (o posición exacta de Gazebo si YOLO no ve limones sintéticos) | — |
| 4 | Ultrasonidos, bumpers y un nodo que imite `/base/estado` y `/brazo/estado`; `mision` completa | — |

## Mundo (`worlds/hilera.sdf`)

- Pasillo a lo largo de +x, robot en el origen, **4 limoneros por lado** en x = 1,5 / 3 / 4,5 / 6 m, y = ±0,95 m.
- Limonero (`models/limonero`): maqueta estática, tronco de 0,6 m y copa de r = 0,35 m a 0,85 m, 10 limones verdes
  entre ~0,6 y 1,1 m de altura (2 hundidos en la copa: oclusión parcial).
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

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select simulacion && source install/setup.bash
ros2 launch simulacion sim.launch.py                 # gui:=false: solo el servidor (más liviano)
ros2 run teleop_twist_keyboard teleop_twist_keyboard  # otra terminal: i/j/l/, para mover
```

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-28 | Notebook (i5 de 4 hilos, Intel HD 5500), sin ventana: `/odom` 24,9 Hz, `/imu/data_raw` 49,8 Hz, `/gps/fix` 1,0 Hz con lat −25,3320 lon −57,5190; `/cmd_vel` 0,2 m/s por 6 s → x = 1,16 m (con la rampa); factor de tiempo real 1,0 | OK |
