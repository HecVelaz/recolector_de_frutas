"""Nodo limones_sim: la "visión" y el agarre de los limones cosechables en Gazebo.

Visión: publica /limon/posicion (geometry_msgs/PointStamped) como el localizador_node real: marco `camera` (óptico
de la cámara izquierda), superficie del limón visible y hora de la "imagen", ~3 Hz. Solo los limones que la cadena
real podría localizar: dentro de la imagen (640x480, f = 1076,5 px, calibración v1), a 0,40-0,95 m y con u >= 271 px
(más a la izquierda el BM no tiene disparidad: min 112 + rango 160); el más cercano. Así `mision` corre igual que con
las cámaras reales.

Agarre: cuando los dedos cierran (/joint_states) con la muñeca a menos de `dist_agarre` del centro de un limón, lo
engancha a la pinza (/sim/limon_N/agarrar, DetachableJoint); cuando abren, lo suelta y lo da por cosechado (no se
vuelve a "ver").

Los limones cosechables están en config/limones_cosechables.xml y este nodo los hace aparecer a los 4 s, con el
brazo ya quieto en el reposo: los enganches arrancan enganchados y, si los limones estuvieran desde el principio, el
brazo se los llevaba al ir al reposo. Después los suelta. Sus posiciones son las del archivo (no se mueven hasta que
se agarran) y la del robot sale de `odom`: la base arranca en el origen del mundo, así que odom = mundo salvo
patinamiento.
"""

import math
from pathlib import Path
import subprocess
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


T_APARECER = 4.0  # s de simulación: el brazo ya llegó al reposo
T_SOLTAR = 5.0    # s soltando los enganches después de que aparecen


def leer_limones(archivo):
    """Modelos limon_N del archivo -> {N: (x, y, z)} [m]."""
    limones = {}
    for m in ET.parse(archivo).getroot().iter('model'):
        nombre = m.get('name', '')
        if nombre.startswith('limon_') and nombre[6:].isdigit():
            limones[int(nombre[6:])] = tuple(float(v) for v in m.find('pose').text.split()[:3])
    return limones


def pedido_crear(archivo):
    """Modelos del archivo -> pedido gz.msgs.EntityFactory_V (formato texto) para /world/hilera/create_multiple."""
    pedidos = []
    for m in ET.parse(archivo).getroot().iter('model'):
        sdf = "<sdf version='1.9'>" + ET.tostring(m, encoding='unicode').replace('"', "'").replace('\n', ' ') + '</sdf>'
        pedidos.append('{sdf: "' + sdf + '"}')
    return 'data: [' + ', '.join(pedidos) + ']'


F, CX, CY, ANCHO, ALTO = 1076.537901, 320.0, 240.0, 640, 480  # como camara_info_sim
U_MIN = 271  # min_disparity + disparity_range - 1 del disparity_node: a la izquierda de esto no hay disparidad


def visible(p, z_min, z_max, u_min=U_MIN):
    """Punto en el marco óptico (x derecha, y abajo, z adelante): ¿lo podría localizar el estéreo?"""
    x, y, z = p
    if not z_min <= z <= z_max:
        return False
    u, v = CX + F * x / z, CY + F * y / z
    return u_min <= u < ANCHO and 0 <= v < ALTO


def superficie(p, radio):
    """Centro -> superficie visible desde la cámara (lo que da el estéreo), acercándolo `radio` sobre el rayo."""
    d = math.sqrt(sum(c * c for c in p))
    return tuple(c * (1.0 - radio / d) for c in p)


class LimonesSim(Node):

    def __init__(self):
        super().__init__('limones_sim')
        archivo = str(Path(get_package_share_directory('simulacion')) / 'config' / 'limones_cosechables.xml')
        self.archivo = self.declare_parameter('archivo', archivo).value
        self.limones = leer_limones(self.archivo)
        self.radio = self.declare_parameter('radio_limon', 0.03).value
        self.z_min = self.declare_parameter('z_min', 0.40).value
        self.z_max = self.declare_parameter('z_max', 0.95).value
        self.dist_agarre = self.declare_parameter('dist_agarre', 0.03).value  # m, muñeca -> centro del limón
        # false: /limon/posicion lo da la cadena real (cámaras de Gazebo + YOLO); acá queda solo el agarre
        self.publicar_vision = self.declare_parameter('publicar_vision', True).value
        self.enganchado = None
        self.cosechados = set()
        self.t_arranque = None
        self.aparecieron = False

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
        t = (ahora - self.t_arranque).nanoseconds * 1e-9
        if t < T_APARECER:
            return
        if not self.aparecieron:
            r = subprocess.run(['gz', 'service', '-s', '/world/hilera/create_multiple', '--reqtype',
                                'gz.msgs.EntityFactory_V', '--reptype', 'gz.msgs.Boolean', '--timeout', '5000',
                                '--req', pedido_crear(self.archivo)], capture_output=True, text=True)
            self.aparecieron = True
            self.get_logger().info(f'limones cosechables agregados: {r.stdout.strip() or r.stderr.strip()}')
            return
        if t < T_APARECER + T_SOLTAR:
            # Los enganches se enganchan solos cuando aparece el limón: soltarlos (si ya estaba suelto, no hace nada)
            for pub in self.pub_soltar.values():
                pub.publish(Empty())
            return
        if not self.publicar_vision:
            return
        vistos = []
        for n, p in self.limones.items():
            if n == self.enganchado or n in self.cosechados:
                continue
            c = self.en_marco(p, 'camera')
            if c is not None and visible(c, self.z_min, self.z_max):
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
