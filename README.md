# Recolector de limones — "Arturito R2D2" (Grupo 2, 2026S2)

Robot móvil autónomo recolector de limones (FIUNA, Ingeniería Mecatrónica): Robótica I (brazo) y Robótica II
(robot móvil con ROS 2). Objetivo mínimo: **el robot se mueve, detecta el limón con YOLO, lo localiza con
estéreo y lo agarra** (ver `docs/ARQUITECTURA.md`).

## Estructura

```
recolector_de_frutas/
├── docs/                 documentación: consignas, entregas R1/R2, arquitectura, índice
│   ├── INDICE.md         qué hay en cada documento (empezar por acá)
│   └── ARQUITECTURA.md   arquitectura del objetivo mínimo, plan y decisiones abiertas
├── firmware/
│   ├── lib/              compartido: BTS7960, EncoderPCNT, HCSR04, MPU9250, UP501, ControlArticulacion,
│   │                     EnlaceMicroRos (conexión con el agente)
│   ├── brazo/            ESP32-WROOM-32D: J1-J3 en lazo cerrado + pinza (PlatformIO)
│   └── base/             ESP32-S3: tracción diferencial, odometría, sensores y seguridad (PlatformIO)
├── ros2_ws/src/
│   └── brazo_ik/         nodo ROS 2: cinemática inversa de la E4 (/brazo/objetivo -> /brazo/joint_cmd)
└── (próximamente) más paquetes ROS 2 (cámaras, YOLO, estéreo, misión)
```

| Parte | Placa | Estado |
|---|---|---|
| `firmware/brazo` | ESP32-WROOM-32D | Compila (serial y micro-ROS); 18 pruebas del control OK en la PC. **Sin probar en placa** |
| `firmware/base` | ESP32-S3 | Compila (serial y micro-ROS); 20 pruebas de la lógica OK en la PC. **Sin probar en placa** |
| `ros2_ws/src/brazo_ik` | Pi 5 / notebook (Ubuntu 24.04, ROS 2 Jazzy) | 9 pruebas OK; nodo probado en la notebook |
| resto de `ros2_ws` | Raspberry Pi 5 | Pendiente (cámaras, YOLO, estéreo, misión, seguridad) |

## Comandos

```bash
PIO=~/.platformio/penv/bin/pio
cd firmware/brazo
$PIO test -e native              # pruebas del control en la PC, sin placa (igual en firmware/base)
$PIO run -t upload -t monitor    # flashear (12 V de los motores APAGADOS) y abrir el monitor
$PIO run -e ros -t upload        # la versión micro-ROS (ver el README de cada firmware)

cd ../../ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && colcon test && colcon test-result --verbose
```

## Fuera de git (solo en local)

- Videos de evidencias (`*.mp4`, ≈500 MB): están en la lista de YouTube de la Entrega 1 de R2.
- Artículos y libro de referencia (material de terceros).
- `graphify-out/` (grafo de conocimiento generado con graphify).

## Relación con `~/pruebas-esp32`

Ese repo sigue siendo el de **pruebas de componentes de a uno** (IMU, GPS, motores en lazo abierto). Lo que va al
robot vive acá. Los drivers de `firmware/lib` se copiaron de ahí el 2026-09-27: los arreglos nuevos se hacen acá.
