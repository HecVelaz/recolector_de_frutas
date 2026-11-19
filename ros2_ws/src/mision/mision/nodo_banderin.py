"""Nodo banderin: pose del banderín ArUco en el marco de la base (portado de 27-aruco-arbol/tools/marcas.py).

Suscribe  /left/image_rect   sensor_msgs/Image       imagen rectificada izquierda (sin distorsión: K = P[:3, :3])
          /left/camera_info  sensor_msgs/CameraInfo
Publica   /banderin/pose     geometry_msgs/PoseStamped  en `marco` (base_link), con la hora de la imagen: posición
                             del centro de la marca [m] y orientación = solo el giro alrededor de z, hacia dónde sale
                             la cara impresa (0 = hacia +x de la base)

DICT_4X4_50, solo el ID `id` (0), cuadrado negro de `lado` m (0,150); solvePnP con IPPE_SQUARE. La TF cámara -> base
sale del árbol de TF (urdf en la simulación). Se publica una pose por imagen; la mediana la hace la navegación (robot
quieto: las exposiciones izq/der no están sincronizadas y en movimiento la marca sale corrida).
"""

import math

import cv2
from geometry_msgs.msg import PoseStamped
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener


def a_gris(msg):
    """sensor_msgs/Image -> imagen de grises (numpy), sin cv_bridge."""
    canales = {'mono8': 1, 'bgr8': 3, 'rgb8': 3, 'bgra8': 4, 'rgba8': 4}
    n = canales.get(msg.encoding)
    if n is None:
        raise ValueError(f'encoding {msg.encoding} no soportado')
    img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width * n]
    if n == 1:
        return np.ascontiguousarray(img)
    cod = {'bgr8': cv2.COLOR_BGR2GRAY, 'rgb8': cv2.COLOR_RGB2GRAY, 'bgra8': cv2.COLOR_BGRA2GRAY,
           'rgba8': cv2.COLOR_RGBA2GRAY}[msg.encoding]
    return cv2.cvtColor(np.ascontiguousarray(img.reshape(msg.height, msg.width, n)), cod)


def matriz(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def pose_marca(esquinas, K, lado):
    """Esquinas (4x2 px, orden de ArUco) -> (posición [m], normal de la cara impresa) en el marco de la cámara."""
    h = lado / 2
    obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], np.float64)
    ok, rvec, tvec = cv2.solvePnP(obj, esquinas.reshape(4, 2).astype(np.float64), K, None,
                                  flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if not ok:
        return None
    return tvec.ravel(), cv2.Rodrigues(rvec)[0][:, 2]   # z de la marca: sale de la cara impresa hacia la cámara


class NodoBanderin(Node):

    def __init__(self):
        super().__init__('banderin')
        self.id = self.declare_parameter('id', 0).value
        self.lado = self.declare_parameter('lado', 0.150).value
        self.marco = self.declare_parameter('marco', 'base_link').value
        self.K = None
        self.dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.par = cv2.aruco.DetectorParameters_create()
        self.par.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf, self)
        self.pub = self.create_publisher(PoseStamped, '/banderin/pose', 10)
        self.create_subscription(CameraInfo, '/left/camera_info', self.al_info, 1)
        self.create_subscription(Image, '/left/image_rect', self.al_img, 1)
        self.get_logger().info(f'banderin: ID {self.id}, {self.lado * 1000:.0f} mm -> /banderin/pose ({self.marco})')

    def al_info(self, m):
        self.K = np.array(m.p, float).reshape(3, 4)[:, :3].copy()

    def al_img(self, m):
        if self.K is None:
            return
        esq, ids, _ = cv2.aruco.detectMarkers(a_gris(m), self.dic, parameters=self.par)
        if ids is None or self.id not in ids.ravel():
            return
        r = pose_marca(esq[list(ids.ravel()).index(self.id)], self.K, self.lado)
        if r is None:
            return
        try:
            tr = self.tf.lookup_transform(self.marco, m.header.frame_id, Time()).transform   # TF estática
        except TransformException as e:
            self.get_logger().warn(f'sin TF {m.header.frame_id} -> {self.marco}: {e}', throttle_duration_sec=5.0)
            return
        q = tr.rotation
        R = matriz((q.x, q.y, q.z, q.w))
        pos = R @ r[0] + np.array([tr.translation.x, tr.translation.y, tr.translation.z])
        nor = R @ r[1]
        mira = math.atan2(nor[1], nor[0])
        msg = PoseStamped()
        msg.header.stamp, msg.header.frame_id = m.header.stamp, self.marco
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = (float(v) for v in pos)
        msg.pose.orientation.z, msg.pose.orientation.w = math.sin(mira / 2), math.cos(mira / 2)
        self.pub.publish(msg)
        self.get_logger().info(f'ID {self.id}: a {np.linalg.norm(r[0]):.2f} m, en ({pos[0]:.3f}, {pos[1]:.3f}) m, '
                               f'mira a {math.degrees(mira):+.1f}°', throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    nodo = NodoBanderin()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
