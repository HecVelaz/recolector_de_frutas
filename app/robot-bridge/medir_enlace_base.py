#!/usr/bin/env python3
"""Cada 1 s: pings fallidos y cortes de la S3, CPU de la Pi, visión prendida y brazo moviéndose (23/11).
Para ver si los cortes del enlace micro-ROS de la base coinciden con la carga de la Pi.
Uso en la Pi: python3 medir_enlace_base.py [segundos]   Salida: ~/logs/enlace_base_<fecha>.csv"""
import re
import subprocess
import sys
import time
from pathlib import Path

import rclpy
from std_msgs.msg import String


def cpu():
    v = list(map(int, open('/proc/stat').readline().split()[1:]))
    return v[3] + v[4], sum(v)


rclpy.init()
node = rclpy.create_node('medir_enlace_base')
last = {'base': '', 'brazo': ''}
node.create_subscription(String, '/base/estado', lambda m: last.__setitem__('base', m.data), 10)
node.create_subscription(String, '/brazo/estado', lambda m: last.__setitem__('brazo', m.data), 10)
out = Path.home() / 'logs' / time.strftime('enlace_base_%Y%m%d_%H%M%S.csv')
duration = float(sys.argv[1]) if len(sys.argv) > 1 else 900
with open(out, 'w') as f:
    f.write('hora,pings_fallidos,cortes,cpu_pct,vision,brazo_mueve,base_modo\n')
    idle0, total0 = cpu()
    end, next_at = time.time() + duration, time.time() + 1
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=max(0.0, next_at - time.time()))
        if time.time() < next_at:
            continue
        next_at += 1
        idle, total = cpu()
        pct = 100 * (1 - (idle - idle0) / max(1, total - total0))
        idle0, total0 = idle, total
        link = re.search(r'pings_fallidos=(\d+) cortes=(\d+)', last['base'])
        joints = re.search(r'e=(\d),(\d),(\d)', last['brazo'])
        vision = subprocess.run(['pgrep', '-f', 'start_limon'], capture_output=True).returncode == 0
        mode = re.search(r'modo=(\S+)', last['base'])
        f.write(f"{time.strftime('%H:%M:%S')},{link[1] if link else ''},{link[2] if link else ''},{pct:.0f},"
                f"{int(vision)},{int(bool(joints) and '5' in joints.groups())},{mode[1] if mode else ''}\n")
        f.flush()
print(out)
