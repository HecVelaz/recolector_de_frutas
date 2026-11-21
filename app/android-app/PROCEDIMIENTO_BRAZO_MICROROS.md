# Procedimiento preparado — brazo micro-ROS

Fecha: 19/11/2026. Etapa 8, prioridad 1.

Este documento describe la instalación y la comprobación inicial del firmware micro-ROS del brazo.
La instalación y la comprobación sin potencia se ejecutaron correctamente el 19/11/2026. No autoriza
movimientos, homing, armado ni etapa 9.

## Artefactos verificados

Directorio de la Pi: `/home/r2d2/arturito-build/20261119/artifacts`.

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `bootloader.bin` | 17.536 | `3d234a7471f67b013686dabd4dee7c1fa915c9928463616a94bc9297acf1abf8` |
| `partitions.bin` | 3.072 | `148b959cbff1c38aa8e1d5c0ba9d612c54997b945e56a63f41223eef650653a1` |
| `boot_app0.bin` | 8.192 | `f94c5d786a7a8fab06ac5d10e33bf37711a6697636dc037559ea19cc410a17f0` |
| `firmware.bin` micro-ROS candidato | 417.776 | `1bb3c63c87f667b9e1b1c42bc92624948d029f6718010c93efe37e46149958a4` |

Respaldo completo previo: `../respaldo_wroom_pre_microros_20261119.bin`, 4.194.304 bytes,
SHA-256 `37312156ec27b3161eed75b1d2cd1cac18b0f14ca7dbcf668d308a85e28f1862`.
También hay una copia local bajo `.codex-build/brazo-microros-20261119-artifacts/`.

La aplicación que estaba realmente en la WROOM se identificó por comparación exacta con
`~/firmware/brazo20_20261119/firmware.bin` (SHA-256
`c1d876ac71d7d08204c8e1022c67d48127be6fd86183fe33d4b035cc12d9a02c`).

## Puerta de seguridad antes de instalar

Se debe detener el procedimiento si alguna condición no se cumple:

1. Autorización específica para flashear recibida.
2. Alimentación de 12 V físicamente desconectada; Pi y ESP32 solo por USB.
3. Robot inmóvil y brazo apoyado de forma estable.
4. Seta accionada.
5. WROOM presente mediante
   `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` y puerto sin usuarios.
6. Hash del respaldo y de los cuatro artefactos coincidente con la tabla anterior.
7. Ningún agente o monitor del brazo abierto. El agente de la base no necesita detenerse.

## Instalación ejecutada

Desde la Pi, después de cumplir la puerta de seguridad:

```bash
E=~/venvs/esptool/bin/esptool
W=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
cd ~/arturito-build/20261119/artifacts

$E --chip esp32 --port "$W" --baud 230400 write-flash -z \
  0x1000 bootloader.bin \
  0x8000 partitions.bin \
  0xe000 boot_app0.bin \
  0x10000 firmware.bin
```

No se utilizó `pio run -t upload`: los binarios y desplazamientos fueron verificados y el comando
anterior deja explícito qué se escribió. Los 12 V permanecieron desconectados después de grabar.

## Comprobación inicial sin potencia

1. Iniciar solo el agente del brazo, aislado al host local:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros/microros_ws/install/setup.bash
ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  ros2 run micro_ros_agent micro_ros_agent serial \
  --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 -v3
```

2. En otra sesión con el mismo entorno, comprobar sin publicar comandos:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic info /brazo/estado --verbose
timeout 10s ros2 topic echo /brazo/estado std_msgs/msg/String --once
ros2 topic info /brazo/respuesta --verbose
ros2 topic info /brazo/comando --verbose
```

Resultado mínimo esperado: publicador real en `/brazo/estado`, mensajes a aproximadamente 10 Hz y
suscripción en `/brazo/comando`. No enviar `armar`, `h`, `s`, `z`, `mv`, `j`, `jv`, `pz` ni `mn`.
Con 12 V desconectados no se valida movimiento; solamente transporte micro-ROS y telemetría.

3. Mantener el puente 0.4.1 en modo `ros2`. La app debe pasar el brazo de «sin mensajes» a reciente
y mostrar el texto recibido. Verificar pérdida y recuperación deteniendo únicamente el agente del
brazo, no el puente ni el agente de la base.

## Reversión preparada

Si la WROOM no establece micro-ROS o el estado no tiene el formato esperado, mantener los 12 V
desconectados, detener el agente del brazo y restaurar la imagen completa:

```bash
E=~/venvs/esptool/bin/esptool
W=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
$E --chip esp32 --port "$W" --baud 230400 write-flash 0x0 \
  ~/arturito-build/20261119/respaldo_wroom_pre_microros_20261119.bin
```

Después se debe comprobar por UART que reaparece el banner de la variante serie del 19/11. Abrir el
puerto reinicia la WROOM, por lo que los 12 V deben permanecer desconectados durante esa comprobación.

## Prueba con potencia — fuera de este procedimiento

Encender 12 V, homing, servos y cualquier movimiento pertenecen a una prueba física posterior. Exigen
un plan de poses seguras, límites, persona junto a la seta y una autorización independiente. No forman
parte de la comprobación de etapa 8 descrita aquí.
