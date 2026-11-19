"""Nodo camara_info_sim: camera_info ideal para las cámaras estéreo de Gazebo.

Gazebo publica un camera_info por cámara sin la separación entre ellas, y stereo_image_proc la saca de la P de la
derecha (Tx = -f * B). Este nodo publica /left/camera_info y /right/camera_info con el mismo header que cada imagen
(/left/image_rect, /right/image_rect): pinhole sin distorsión, R = I (ya rectificadas). Parámetros f y tx: por
defecto la calibración v1; la cámara de navegación del mástil (camara:=nav) es f = 672,126 y tx = -67,432
(vision_estereo/config/calibracion_mastil).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

F = 1076.537901     # px, calibración v1 (vision_estereo/config/calibracion)
TX = -106.854141    # -f * B: B = 99,26 mm
ANCHO, ALTO = 640, 480


def info(tx, f=F):
    cx, cy = ANCHO / 2, ALTO / 2
    m = CameraInfo(width=ANCHO, height=ALTO, distortion_model='plumb_bob', d=[0.0] * 5)
    m.k = [f, 0.0, cx, 0.0, f, cy, 0.0, 0.0, 1.0]
    m.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    m.p = [f, 0.0, cx, tx, 0.0, f, cy, 0.0, 0.0, 0.0, 1.0, 0.0]
    return m


class CamaraInfoSim(Node):

    def __init__(self):
        super().__init__('camara_info_sim')
        f = self.declare_parameter('f', F).value
        for lado, tx in (('left', 0.0), ('right', self.declare_parameter('tx', TX).value)):
            pub = self.create_publisher(CameraInfo, f'/{lado}/camera_info', 10)
            plantilla = info(tx, f)
            self.create_subscription(Image, f'/{lado}/image_rect',
                                     lambda img, pub=pub, m=plantilla: self.publicar(img, pub, m), 10)

    @staticmethod
    def publicar(img, pub, m):
        m.header = img.header
        pub.publish(m)


def main(args=None):
    rclpy.init(args=args)
    nodo = CamaraInfoSim()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
