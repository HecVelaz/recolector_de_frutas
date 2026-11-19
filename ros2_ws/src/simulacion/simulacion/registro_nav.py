"""Nodo registro_nav: mide la navegación con el banderín contra la pose VERDADERA de Gazebo (solo para medir: la
navegación usa /odom, /imu/data_raw y la marca) y lo guarda en resultados/nav_<fecha>.csv.

- En cada "COSECHAR: árbol k, lado X" de /navegacion/estado: dónde quedó el eje del árbol k respecto de J1 (pose real
  del robot y árbol del mundo) contra la parada (adelante, costado) y el rumbo contra el de la hilera (lado A: del
  árbol 1 al 2; lado B: al revés). Cumple si los dos están a <= tol (5 cm) y el rumbo a <= tol_rumbo (3°).
- /sim/cosechado (limones_sim): limones cosechados por árbol (limon_<10·árbol + j>, mundo_arbolitos).
- "FIN: error de la odometría ..." (cierre): el error acumulado que midió la navegación con el banderín.
El CSV se reescribe en cada evento (sirve aunque se corte la simulación).
"""

import csv
from datetime import datetime
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from simulacion.limones_sim import GazeboPoses, nombre_mundo

PARADA = re.compile(r'^COSECHAR: árbol (\d+), lado ([AB])')
CIERRE = re.compile(r'^FIN: error de la odometría adelante ([-+\d.]+) cm, costado ([-+\d.]+) cm, rumbo ([-+\d.]+)°')


def leer_arboles(archivo):
    """<include> arbolito_k del mundo -> {k: (x, y)}."""
    arboles = {}
    for inc in ET.parse(archivo).getroot().iter('include'):
        nombre = inc.findtext('name', '')
        if nombre.startswith('arbolito_'):
            arboles[int(nombre[9:])] = tuple(float(v) for v in inc.findtext('pose').split()[:2])
    return arboles


def error_parada(pose, arbol, rumbo_lado, j1, parada):
    """Pose real (x, y, rumbo) y eje del árbol -> (adelante, costado, rumbo) de la parada: + = el árbol quedó más
    adelante / más a la izquierda de lo pedido, el robot girado a la izquierda."""
    x, y, th = pose
    jx = x + j1[0] * math.cos(th) - j1[1] * math.sin(th)
    jy = y + j1[0] * math.sin(th) + j1[1] * math.cos(th)
    dx, dy = arbol[0] - jx, arbol[1] - jy
    adelante = dx * math.cos(th) + dy * math.sin(th)
    izquierda = -dx * math.sin(th) + dy * math.cos(th)
    return (adelante - parada[0], izquierda - parada[1],
            math.atan2(math.sin(th - rumbo_lado), math.cos(th - rumbo_lado)))


def carpeta_resultados():
    """src/simulacion/resultados del workspace (install/simulacion/share/simulacion -> ws), o ./resultados."""
    ws = Path(get_package_share_directory('simulacion')).parents[3]
    src = ws / 'src' / 'simulacion'
    return (src if src.is_dir() else Path.cwd()) / 'resultados'


class RegistroNav(Node):

    def __init__(self):
        super().__init__('registro_nav')
        mundo = self.declare_parameter('mundo', '').value
        self.j1 = tuple(self.declare_parameter('j1', [0.0, 0.11]).value)
        self.parada = tuple(self.declare_parameter('parada', [0.15, 0.70]).value)
        self.tol = self.declare_parameter('tol', 0.05).value
        self.tol_rumbo = math.radians(self.declare_parameter('tol_rumbo', 3.0).value)
        self.nota = self.declare_parameter('nota', '').value
        self.arboles = leer_arboles(mundo)
        a = [self.arboles[k] for k in sorted(self.arboles)]
        self.psi = math.atan2(a[1][1] - a[0][1], a[1][0] - a[0][0]) if len(a) > 1 else 0.0
        self.gz = GazeboPoses(nombre_mundo(mundo))
        carpeta = Path(self.declare_parameter('salida', str(carpeta_resultados())).value)
        carpeta.mkdir(parents=True, exist_ok=True)
        self.csv = carpeta / f'nav_{datetime.now():%Y%m%d_%H%M%S}.csv'
        self.filas, self.cosechados, self.inicio = [], {}, None
        self.create_subscription(String, '/navegacion/estado', self.al_estado, 10)
        self.create_subscription(String, '/sim/cosechado', self.al_cosechado, 10)
        self.create_timer(1.0, self.al_inicio)
        self.get_logger().info(f'registro_nav: {len(self.arboles)} árboles -> {self.csv}')

    def pose(self):
        if self.gz.robot is None:
            return None
        (x, y, _), (qx, qy, qz, qw) = self.gz.robot
        return x, y, math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))

    def al_inicio(self):
        if self.inicio is None and (p := self.pose()) is not None:
            self.inicio = p
            self.escribir()

    def al_cosechado(self, m):
        k = int(m.data.split('_')[1]) // 10
        self.cosechados[k] = self.cosechados.get(k, 0) + 1
        self.escribir()

    def al_estado(self, m):
        if (r := PARADA.match(m.data)) and (p := self.pose()) is not None:
            k, lado = int(r.group(1)), r.group(2)
            a, c, th = error_parada(p, self.arboles[k], self.psi + (0.0 if lado == 'A' else math.pi), self.j1,
                                    self.parada)
            ok = abs(a) <= self.tol and abs(c) <= self.tol and abs(th) <= self.tol_rumbo
            self.filas.append(['parada', k, lado, f'{a * 100:+.1f}', f'{c * 100:+.1f}', f'{math.degrees(th):+.2f}',
                               'si' if ok else 'NO', ''])
            self.get_logger().info(f'parada árbol {k} lado {lado}: adelante {a * 100:+.1f} cm, costado '
                                   f'{c * 100:+.1f} cm, rumbo {math.degrees(th):+.2f}° -> {"cumple" if ok else "NO"}')
        elif r := CIERRE.match(m.data):
            self.filas.append(['cierre', '', '', *r.groups(), '', ''])
        elif m.data.startswith('FALLA'):
            self.filas.append(['falla', '', '', '', '', '', '', m.data])
        else:
            return
        self.escribir()

    def escribir(self):
        with open(self.csv, 'w', newline='') as f:
            if self.inicio:
                x, y, th = self.inicio
                f.write(f'# pose inicial real ({x:.3f}, {y:.3f}) m, {math.degrees(th):.1f}°; {len(self.arboles)} '
                        f'árboles; {self.nota}\n')
            w = csv.writer(f)
            w.writerow(['tipo', 'arbol', 'lado', 'adelante_cm', 'costado_cm', 'rumbo_deg', 'cumple', 'limones'])
            w.writerows(self.filas)
            w.writerows(['cosecha', k, '', '', '', '', '', self.cosechados.get(k, 0)] for k in sorted(self.arboles))


def main(args=None):
    rclpy.init(args=args)
    nodo = RegistroNav()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
