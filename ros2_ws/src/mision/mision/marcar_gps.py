"""Marca un punto de la hilera con el GPS: con el robot quieto en el inicio (o el fin) de la hilera, promedia
/gps/fix durante `segundos` e imprime los parámetros para nodo_mision.

    ros2 run mision marcar_gps --ros-args -p segundos:=60.0 -p punto:=inicio
"""

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus

from mision.hilera_gps import promediar


class MarcarGps(Node):

    def __init__(self):
        super().__init__('marcar_gps')
        self.segundos = self.declare_parameter('segundos', 60.0).value
        self.punto = self.declare_parameter('punto', 'inicio').value
        self.fixes = []
        self.t0 = None
        self.create_subscription(NavSatFix, '/gps/fix', self.al_fix, 10)
        self.get_logger().info(f'promediando /gps/fix {self.segundos:.0f} s: no mover el robot')

    def al_fix(self, m):
        if m.status.status < NavSatStatus.STATUS_FIX or not math.isfinite(m.latitude):
            self.get_logger().info('sin fix todavía', throttle_duration_sec=10.0)
            return
        t = self.get_clock().now().nanoseconds * 1e-9
        self.t0 = self.t0 or t
        c = m.position_covariance
        self.fixes.append((m.latitude, m.longitude, math.sqrt(max(c[0], c[4]))))
        if t - self.t0 >= self.segundos:
            lat, lon, sigma = promediar(self.fixes)
            print(f'{len(self.fixes)} fixes, σ de cada uno ~{sigma * math.sqrt(len(self.fixes)):.1f} m')
            print(f'-p hilera_{self.punto}_lat:={lat:.7f} -p hilera_{self.punto}_lon:={lon:.7f}', flush=True)
            raise SystemExit


def main(args=None):
    rclpy.init(args=args)
    nodo = MarcarGps()
    try:
        rclpy.spin(nodo)
    except (SystemExit, KeyboardInterrupt):
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()
