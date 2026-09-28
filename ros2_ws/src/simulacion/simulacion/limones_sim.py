"""Nodo limones_sim: la "visión" y el agarre de los limones cosechables en Gazebo.

Visión: publica /limon/posicion (geometry_msgs/PointStamped) como el localizador_node real: marco `camera` (óptico
de la cámara izquierda), superficie del limón visible y hora de la "imagen", ~3 Hz. Solo los limones dentro del campo
visual (33° x 25°: 640x480 con f = 1076 px, calibración v1) y de la ventana de disparidad de 0,40 a 0,95 m; el más
cercano. Así `mision` corre igual que con las cámaras reales.

Agarre: cuando los dedos cierran (/joint_states) con la muñeca a menos de `dist_agarre` del centro de un limón, lo
engancha a la pinza (/sim/limon_N/agarrar, DetachableJoint); cuando abren, lo suelta y lo da por cosechado (no se
vuelve a "ver").

Las posiciones de los limones salen del mundo (no se mueven hasta que se agarran) y la del robot, de `odom`: en la
simulación la base arranca en el origen del mundo, así que odom = mundo salvo patinamiento.
"""

import math
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty, String
import tf2_geometry_msgs  # noqa: F401  (registra PointStamped en tf2)
from tf2_ros import Buffer, TransformException, TransformListener


def leer_limones(mundo):
    """Modelos limon_N del mundo -> {N: (x, y, z)} [m]."""
    limones = {}
    for m in ET.parse(mundo).getroot().iter('model'):
        nombre = m.get('name', '')
        if nombre.startswith('limon_') and nombre[6:].isdigit():
            limones[int(nombre[6:])] = tuple(float(v) for v in m.find('pose').text.split()[:3])
    return limones


def visible(p, hfov, vfov, z_min, z_max):
    """Punto en el marco óptico (x derecha, y abajo, z adelante): ¿dentro del campo visual y de la ventana?"""
    x, y, z = p
    return (z_min <= z <= z_max and abs(math.atan2(x, z)) <= hfov / 2 and abs(math.atan2(y, z)) <= vfov / 2)


def superficie(p, radio):
    """Centro -> superficie visible desde la cámara (lo que da el estéreo), acercándolo `radio` sobre el rayo."""
    d = math.sqrt(sum(c * c for c in p))
    return tuple(c * (1.0 - radio / d) for c in p)


class LimonesSim(Node):

    def __init__(self):
        super().__init__('limones_sim')
        mundo = str(Path(get_package_share_directory('simulacion')) / 'worlds' / 'hilera.sdf')
        self.limones = leer_limones(self.declare_parameter('mundo', mundo).value)
        self.radio = self.declare_parameter('radio_limon', 0.03).value
        self.hfov = math.radians(self.declare_parameter('hfov_deg', 33.0).value)
        self.vfov = math.radians(self.declare_parameter('vfov_deg', 25.0).value)
        self.z_min = self.declare_parameter('z_min', 0.40).value
        self.z_max = self.declare_parameter('z_max', 0.95).value
        self.dist_agarre = self.declare_parameter('dist_agarre', 0.03).value  # m, muñeca -> centro del limón
        self.enganchado = None
        self.cosechados = set()
        self.t_arranque = None

        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf, self)
        self.pub_pos = self.create_publisher(PointStamped, '/limon/posicion', 10)
        self.pub_agarrar = {n: self.create_publisher(Empty, f'/sim/limon_{n}/agarrar', 10) for n in self.limones}
        self.pub_soltar = {n: self.create_publisher(Empty, f'/sim/limon_{n}/soltar', 10) for n in self.limones}
        for n in self.limones:
            self.create_subscription(String, f'/sim/limon_{n}/estado',
                                     lambda m, n=n: self.get_logger().info(f'limon_{n}: {m.data}'), 10)
        self.create_subscription(JointState, '/joint_states', self.al_joints, 10)
        self.create_timer(1.0 / 3.0, self.ver)
        self.get_logger().info(f'limones_sim: {len(self.limones)} limones cosechables')

    def en_marco(self, p, marco):
        """Punto (x, y, z) en odom -> marco del robot, o None sin TF."""
        msg = PointStamped()
        msg.header.frame_id = 'odom'
        msg.point.x, msg.point.y, msg.point.z = p
        try:
            q = self.tf.transform(msg, marco)
        except TransformException:
            return None
        return (q.point.x, q.point.y, q.point.z)

    def ver(self):
        ahora = self.get_clock().now()
        if self.t_arranque is None:
            self.t_arranque = ahora
        if (ahora - self.t_arranque).nanoseconds < 5e9:
            # El enganche puede arrancar enganchado: soltar todo al principio (si ya estaba suelto, no hace nada)
            for pub in self.pub_soltar.values():
                pub.publish(Empty())
            return
        vistos = []
        for n, p in self.limones.items():
            if n == self.enganchado or n in self.cosechados:
                continue
            c = self.en_marco(p, 'camera')
            if c is not None and visible(c, self.hfov, self.vfov, self.z_min, self.z_max):
                vistos.append(c)
        if vistos:
            s = superficie(min(vistos, key=lambda c: c[2]), self.radio)
            msg = PointStamped()
            msg.header.stamp = ahora.to_msg()
            msg.header.frame_id = 'camera'
            msg.point.x, msg.point.y, msg.point.z = s
            self.pub_pos.publish(msg)

    def al_joints(self, m):
        d = dict(zip(m.name, m.position))
        if 'dedo_izq_joint' not in d or 'dedo_der_joint' not in d:
            return
        apertura = (d['dedo_izq_joint'] + d['dedo_der_joint']) / 2
        if self.enganchado is None and apertura < 0.01:
            try:
                t = self.tf.lookup_transform('odom', 'pinza', Time()).transform.translation
            except TransformException:
                return
            for n, p in self.limones.items():
                if n not in self.cosechados and math.dist((t.x, t.y, t.z), p) <= self.dist_agarre:
                    self.pub_agarrar[n].publish(Empty())
                    self.enganchado = n
                    self.get_logger().info(f'limon_{n} agarrado (muñeca a {math.dist((t.x, t.y, t.z), p) * 100:.1f} cm)')
                    break
        elif self.enganchado is not None and apertura > 0.02:
            self.pub_soltar[self.enganchado].publish(Empty())
            self.get_logger().info(f'limon_{self.enganchado} soltado: cosechado')
            self.cosechados.add(self.enganchado)
            self.enganchado = None


def main(args=None):
    rclpy.init(args=args)
    nodo = LimonesSim()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
