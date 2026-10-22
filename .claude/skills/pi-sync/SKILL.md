---
name: pi-sync
description: Sincroniza la Raspberry Pi del robot con el repo de la notebook - rsync del repo, recompilar los paquetes de ROS 2 que cambiaron y, si cambió el firmware, compilar y flashear el ESP32 (base S3 o brazo WROOM) desde la Pi. Usar con /pi-sync, "sincronizá la Pi", "actualizá la Pi", "flasheá la base/el brazo desde la Pi".
argument-hint: "[todo|repo|ros|base|brazo]"
---

# /pi-sync

Lleva a la Pi (`r2d2`, Ubuntu 24.04 + Jazzy) lo que hay en la notebook. Argumento: `todo` (por defecto),
`repo`, `ros`, `base` o `brazo`. Todo en castellano. Datos de `firmware/CLAUDE.md` y `docs/ESTADO.md`; si algo de acá no coincide con lo
que se ve en la Pi, **manda la Pi**: frenar, contarle al usuario y corregir esta skill.

## 0. Conexión
```bash
PI=r2d2@100.116.96.71          # Tailscale (r2d2-desktop)
ssh -o BatchMode=yes -o ConnectTimeout=5 $PI true || PI=r2d2@192.168.2.219   # LAN del lab
ssh -o BatchMode=yes -o ConnectTimeout=5 $PI true
```
Si ninguna responde: avisar ("la Pi no está accesible") y terminar. No seguir sin Pi.

## 1. Estado local
- `git status --short` y `git log --oneline -3`. Si hay cambios sin commit, preguntar si sincronizarlos igual.
- Si se va a flashear: `pio test -e native` y `pio run -e ros` en esa placa, sin errores ni warnings
  (`~/.platformio/penv/bin/pio`, desde `firmware/<base|brazo>`).

## 2. Repo (rsync, sin .git)
Primero en seco y mostrar qué cambia:
```bash
rsync -an --itemize-changes --exclude-from=- ./ $PI:recolector_de_frutas/ <<'EOF'
.git/
.claude/
graphify-out/
.pio/
ros2_ws/build/
ros2_ws/install/
ros2_ws/log/
__pycache__/
*.mp4
EOF
```
Sin `--delete` (en la Pi puede haber cosas que no están acá). Si la lista se ve bien, repetir sin `-n`.
Anotar qué carpetas cambiaron: `ros2_ws/src/<paquete>` → paso 3; `firmware/<placa>` → paso 4.

## 3. ROS 2 en la Pi
Los paquetes del repo (`brazo_ik`, `mision`) se compilan **en el repo de la Pi**, `~/recolector_de_frutas/ros2_ws`
(`~/ros/` tiene solo `camera_ws`, `microros_ws` y `yolo_ws`, verificado el 21/10). Compilar **solo los que cambiaron**:
```bash
ssh $PI 'cd ~/recolector_de_frutas/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-select <paquetes>'
```
No hace falta `colcon test` en la Pi (se corre en la notebook).

## 4. Firmware (solo si cambió `firmware/<placa>` o se pidió `base`/`brazo`)
1. Compilar en la notebook: `pio run -e ros` en `firmware/base` (S3) o `firmware/brazo` (WROOM).
2. Copiar los binarios a `~/firmware/<base|brazo>/` en la Pi:
   ```bash
   B=firmware/<placa>/.pio/build/ros
   rsync -a $B/bootloader.bin $B/partitions.bin $B/firmware.bin \
     ~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin \
     $PI:firmware/<placa>/
   ```
3. **Pedir al usuario que apague los 12 V** (selector WEG o seta) y esperar su confirmación. El hook del
   proyecto también lo pregunta: es esperado, no saltearlo.
4. Parar el agente micro-ROS de esa placa (si no, el puerto está ocupado):
   `ssh $PI 'pkill -f "^/home/r2d2/microros_ws.*<puerto>"'` (anclado con ^: si no, el patrón coincide con el propio
   comando de ssh y corta la sesión).
5. Flashear desde la Pi con `~/venvs/esptool/bin/esptool`, siempre por `/dev/serial/by-id/`:
   - **Base (S3)**, puerto `usb-Espressif_USB_JTAG_serial_debug_unit_*-if00`, con reset por watchdog:
     ```bash
     ~/venvs/esptool/bin/esptool --chip esp32s3 --port <S3> --after watchdog-reset write-flash \
       0x0 bootloader.bin 0x8000 partitions.bin 0xe000 boot_app0.bin 0x10000 firmware.bin
     ```
   - **Brazo (WROOM, CH340)**, puerto `usb-1a86_USB_Serial-if00-port0`, a 115200 si falla a más velocidad:
     ```bash
     ~/venvs/esptool/bin/esptool --chip esp32 --port <brazo> -b 460800 write-flash \
       0x1000 bootloader.bin 0x8000 partitions.bin 0xe000 boot_app0.bin 0x10000 firmware.bin
     ```
   (correr desde `~/firmware/<placa>`). Si la S3 queda en modo descarga:
   `esptool --port <S3> --before no_reset --after watchdog-reset read-mac`.
6. Levantar el agente otra vez (`~/microros_ws`, comandos en `firmware/CLAUDE.md`) y comprobar que la placa abre sesión y publica
   `/<parte>/estado` (`ros2 topic hz`). Recordar: arranca **desarmada**.

## 5. Cierre
Resumen corto: qué se sincronizó, qué paquetes se compilaron, qué placa se flasheó y con qué commit
(`git log -1 --format='%h %s'`). Si existe la memoria `pi-desactualizada` y quedó resuelto lo que pedía, borrarla.
Si algún comando o ruta de esta skill estaba mal, corregirla acá.
