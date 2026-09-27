# brazo_ik — cinemática inversa del brazo (ROS 2 Jazzy)

Porta la cinemática inversa de la **Entrega 4 de R1** (mecanismo de cuatro barras no paralelogramo) a un nodo
ROS 2. Mismo algoritmo, convenciones y filtros que el notebook (límites articulares, rama física γ4 ∈ (−180°, 0°),
ángulo de transmisión 15°–165°, verificación con la directa), sin numpy ni gráficos.

| Archivo | Qué tiene |
|---|---|
| `brazo_ik/cinematica.py` | Directa e inversa, **sin ROS**: la puede importar también `mision_fsm` para saber si un limón es alcanzable |
| `brazo_ik/nodo_ik.py` | Nodo `brazo_ik` |
| `test/test_cinematica.py` | Ejemplo numérico de la E4, 2000 idas y vueltas directa→inversa→directa, casos inalcanzables |

## Tópicos

| Tópico | Tipo | Sentido | Unidades |
|---|---|---|---|
| `/brazo/objetivo` | `geometry_msgs/PointStamped` | entra | m, marco `brazo_base` (parámetro `marco`) |
| `/brazo/joint_cmd` | `sensor_msgs/JointState` (`j1`, `j2`, `j3`) | sale, solo si es alcanzable | rad |
| `/brazo/ik_estado` | `std_msgs/String` | sale siempre | `ok q=[…]°` o `inalcanzable: <motivos>` |

- El punto es la **muñeca P3**, no la punta de la pinza (ver "Limitación" en la E4: con 3 GDL de posición la
  orientación de la herramienta no se elige).
- Un objetivo en otro marco se rechaza: la transformación cámara → brazo la hace `stereo_3d`.
- El firmware del brazo trabaja en grados: convierte su capa micro-ROS (pendiente).
- La geometría y los límites están en `cinematica.py` y **deben coincidir** con
  `firmware/brazo/include/brazo_config.h`.

## Uso

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
colcon test --packages-select brazo_ik && colcon test-result --verbose

ros2 run brazo_ik nodo_ik
# en otra terminal (ejemplo de la E4: debe dar q = 0°, 45°, 0°)
ros2 topic echo /brazo/ik_estado --field data
ros2 topic pub --once /brazo/objetivo geometry_msgs/msg/PointStamped \
  "{header: {frame_id: brazo_base}, point: {x: 0.36832, y: 0.0, z: 0.09103}}"
```

## Resultados

| Fecha | Prueba | Resultado |
|---|---|---|
| 2026-09-27 | `colcon test` (5 pruebas) | OK |
| 2026-09-27 | Nodo en la notebook: ejemplo E4 → q = (0.00°, 45.00°, 0.00°), err 5e-13 mm; punto lejano, q1 = 108° y marco equivocado → rechazados con su motivo | OK |
