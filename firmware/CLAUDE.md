# CLAUDE.md — firmware (ESP32-S3 base y ESP32-WROOM-32D brazo)

Complementa el `CLAUDE.md` de la raíz. Estado de cada placa: `docs/ESTADO.md`; pines y cableado: `docs/CONEXIONES.md`.

## PlatformIO
- Usar `~/.platformio/penv/bin/pio`. Un proyecto por placa: `firmware/base/` y `firmware/brazo/`.
- Pines **solo** en `include/pins.h` de cada placa. Pines de la S3 vigentes = los de `bb9263d` (no volver a los v0.8).
- Drivers compartidos en `firmware/lib/` (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, EncoderPCNT, HCSR04,
  MPU9250, UP501), enlazados con `symlink://../lib/X`.
- Lógica sin Arduino, con pruebas `pio test -e native`. Antes de un commit: `pio test` y `pio run` **sin warnings**.
- Hook local (`.claude/hooks/tests_firmware.sh`): al editar `firmware/` corre `pio test -e native` en la placa
  afectada (en las dos si es `lib/`).
- Env de prueba de la S3 `ros_motores` (sin IMU ni distancia al frente; tope de `d` 25 %): **nunca en el piso**.
  `serial_motores` tiene `log` (para `scripts/escalon_tau.py`).

## Flasheo
- **Apagar los 12 V antes de flashear o resetear.** Un hook pide confirmarlo antes de `pio ... -t upload` o `esptool`.
- Desde la Pi: `/pi-sync` (rsync, `colcon build` y flasheo). Binarios en `~/firmware/<base|brazo|hola>`, esptool en
  `~/venvs/esptool`.
- S3: flashear con reset por watchdog (ya en `platformio.ini`); abrir el puerto con DTR/RTS bajos la deja en modo
  descarga. Usar `/dev/serial/by-id/`: el puerto pasa de ACM0 a ACM1.
- Si la S3 no abre sesión, está en modo descarga:
  `~/venvs/esptool/bin/esptool --port <S3> --before no_reset --after watchdog-reset read-mac`
  (sin `--before no_reset` la deja en modo descarga).
- `OSError: [Errno 71] Protocol error`: el USB quedó trabado; 12 V apagados, desenchufar y enchufar el USB de la S3.

## micro-ROS
- Cada sesión arranca **desarmada**: `armar` por `/<parte>/comando` (un nodo que siga publicando no mueve el robot al
  reconectar). Con el robot real, no dejar agentes corriendo con el brazo armado si no se usa.
- Agentes en la Pi (`~/microros_ws`):
  `micro_ros_agent serial --dev /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` (brazo, a **115200**: a 921600 el
  CH340 pierde datos) y `.../usb-Espressif_USB_JTAG_serial_debug_unit_*-if00` (base).
- Por ssh, `pkill -f` con un patrón anclado (`"^/home/r2d2/microros_ws.*Espressif"`): si no, coincide con el propio
  comando y corta la sesión.
- Ping del enlace a 100 ms (a 20 ms daba cortes falsos); contadores `enlace: pings_fallidos cortes` en `/<parte>/estado`.
- Cualquier nodo de ROS 2 en la misma LAN que la Pi ve y comanda los ESP32 (dominio 0): la simulación va aislada con
  `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.
- Lazos cerrados y seguridad en cada ESP32 (seta, vuelco, bumpers, distancia, watchdog): la Pi solo manda consignas.
