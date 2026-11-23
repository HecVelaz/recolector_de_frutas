#!/usr/bin/env bash
# Arranca en la Pi todo lo que usa la app Arturito, en segundo plano: agentes micro-ROS de la base (S3) y del brazo
# (WROOM), la visión (start_limon.sh con el v4, vía ~/scripts/vision.sh) y el puente en la IP de Tailscale :18006
# (mando supervisado; la tablet entra directo por Tailscale; sin Tailscale, 127.0.0.1). Lo que ya está corriendo no se vuelve a lanzar. No resetea placas ni mueve motores.
# Uso: bash ~/arturito-bridge-0.9.0/arrancar_pi.sh        Logs en ~/logs/ y bridge.log al lado de este script.
DIR="$(dirname "$(readlink -f "$0")")"
BRAZO=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
DATOS=~/arturito-bridge-0.4.0/data          # clave de la app, geocerca y registros de misiones
VENV=~/arturito-bridge-0.4.1/.venv          # entorno con FastAPI (y los paquetes ROS del sistema)
mkdir -p ~/logs
source /opt/ros/jazzy/setup.bash
source ~/microros_ws/install/local_setup.bash

# La S3 a veces arranca en BOOTLOADER al prender la Pi (23/11: aparece en el USB pero no corre el firmware; algo
# que abre el puerto al arrancar la manda ahí). Solo si está en bootloader (esptool sin reset solo conecta en ese
# caso) se la reinicia: en bootloader no controla los IBT-2, así que reiniciarla no agrega riesgo (OK del usuario).
s3_bootloader() {
  local S3; S3=$(ls /dev/serial/by-id/usb-Espressif_USB_JTAG* 2>/dev/null | head -1)
  [ -n "$S3" ] || return 1
  if timeout 25 ~/venvs/esptool/bin/esptool --port "$S3" --before no-reset --after watchdog-reset chip-id \
      >> ~/logs/s3_bootloader.log 2>&1; then
    echo "S3: estaba en bootloader, reiniciada $(date +%T)" | tee -a ~/logs/s3_bootloader.log; sleep 3
  fi
}
base_habla() { timeout 4 ros2 topic echo /base/estado --once > /dev/null 2>&1; }
agente_base_corre() { pgrep -f "[m]icro_ros_agent serial --dev /dev/serial/by-id/usb-Espressif" > /dev/null; }

export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
agente_base_corre || s3_bootloader
bash ~/scripts/agente_base.sh   # no arranca si ya hay algún agente: por eso va antes que el del brazo
for _ in $(seq 1 10); do base_habla && break; sleep 1; done
if ! base_habla && agente_base_corre; then   # segundo intento: quizás la mandó al bootloader el propio agente
  echo "base sin mensajes: reviso la S3 y relanzo su agente"
  pkill -f "[m]icro_ros_agent serial --dev /dev/serial/by-id/usb-Espressif"; sleep 2
  s3_bootloader
  S3=$(ls /dev/serial/by-id/usb-Espressif_USB_JTAG* 2>/dev/null | head -1)
  nohup setsid ros2 run micro_ros_agent micro_ros_agent serial --dev "$S3" > ~/logs/agente_base.log 2>&1 < /dev/null &
fi
if pgrep -f "micro_ros_agent serial --dev $BRAZO" > /dev/null; then
  echo "agente del brazo: ya corre"
elif [ -e "$BRAZO" ]; then
  nohup setsid ros2 run micro_ros_agent micro_ros_agent serial --dev "$BRAZO" > ~/logs/agente_brazo.log 2>&1 < /dev/null &
  echo "agente del brazo lanzado"
else
  echo "no veo la WROOM ($BRAZO)"
fi

bash ~/scripts/vision.sh

if pgrep -f "run_pi.py --source ros2 --physical-manual" > /dev/null; then
  echo "puente: ya corre"
else
  HOST=127.0.0.1   # al prender, Tailscale puede tardar: espero hasta 60 s su IP
  for _ in $(seq 1 30); do IP=$(tailscale ip -4 2>/dev/null) && [ -n "$IP" ] && HOST=$IP && break; sleep 2; done
  cd "$DIR" || exit 1
  unset ROS_STATIC_PEERS
  echo "=== puente arrancado $(date "+%F %T") ===" >> bridge.log   # se acumula: no pisar el registro de cortes
  ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST nohup setsid "$VENV/bin/python" run_pi.py --source ros2 --physical-manual \
    --host "$HOST" --port 18006 --data-dir "$DATOS" >> bridge.log 2>&1 < /dev/null &
  echo "puente lanzado en $HOST:18006 (log $DIR/bridge.log)"
fi

# Espera corta y resumen: placas y visión
for _ in $(seq 1 20); do timeout 3 ros2 topic echo /brazo/estado --once > /dev/null 2>&1 && break; sleep 1; done
printf "brazo: "; timeout 4 ros2 topic echo /brazo/estado --once --field data 2>/dev/null | head -1 || echo "sin mensajes"
printf "base:  "; timeout 4 ros2 topic echo /base/estado --once --field data 2>/dev/null | head -1 | cut -c1-70 || echo "sin mensajes"
LOG=$(ls -t ~/logs/start_limon_*.log 2>/dev/null | head -1)
for _ in $(seq 1 40); do grep -q "FPS" "$LOG" 2>/dev/null && break; sleep 2; done
printf "visión: "; grep "FPS" "$LOG" 2>/dev/null | tail -1 | sed 's/.*\]: //' || echo "todavía sin detector"
