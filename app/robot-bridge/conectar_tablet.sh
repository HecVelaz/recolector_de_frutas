#!/usr/bin/env bash
# Desde la notebook, con la tablet por USB: arranca todo en la Pi (arrancar_pi.sh, no repite lo que ya corre) y
# deja el túnel tablet → notebook → Pi 127.0.0.1:18006. Si se corta (Pi reiniciada, cable desenchufado), reintenta solo.
# Uso: bash app/robot-bridge/conectar_tablet.sh     (Ctrl+C para cortar)
PI=r2d2@100.116.96.71
ADB=~/Android/Sdk/platform-tools/adb
SSH_OPTS=(-o ConnectTimeout=5 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o ExitOnForwardFailure=yes)
pkill -f "ssh -N .*-L 127.0.0.1:18006" 2>/dev/null   # túnel viejo de otra terminal
# adb reverse se pierde al desenchufar la tablet: lo reaplico cada 3 s (es idempotente)
( while true; do "$ADB" wait-for-device reverse tcp:18006 tcp:18006 > /dev/null 2>&1; sleep 3; done ) &
ADB_LOOP=$!; trap 'kill $ADB_LOOP' EXIT

while true; do
  if ssh "${SSH_OPTS[@]}" "$PI" 'bash ~/arturito-bridge-0.9.0/arrancar_pi.sh'; then
    echo "túnel abierto: en la app, Conectar al puente ($(date +%H:%M:%S))"
    ssh -N "${SSH_OPTS[@]}" -L 127.0.0.1:18006:127.0.0.1:18006 "$PI"
    echo "túnel cortado ($(date +%H:%M:%S)); reintento"
  else
    echo "no llego a la Pi; reintento en 5 s"
  fi
  sleep 5
done
