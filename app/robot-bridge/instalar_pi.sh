#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-lock.txt
echo 'Instalación aislada completada. Para leer el estado existente:'
echo 'source /opt/ros/jazzy/setup.bash'
echo '.venv/bin/python run_pi.py --source ros2'
