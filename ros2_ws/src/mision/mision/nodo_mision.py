"""Nodo mision: conecta la máquina de estados (fsm.py) con los tópicos y la TF cámara -> brazo.

Suscribe  /limon/posicion  geometry_msgs/PointStamped  superficie del limón [m], marco de la cámara (visión)
          /brazo/estado    std_msgs/String             armado, "llego" y fallas (firmware, 2 Hz)
          /brazo/ik_estado std_msgs/String             "ok ..." o "inalcanzable: ..." (brazo_ik)
          /brazo/joint_cmd sensor_msgs/JointState      ángulos que calculó brazo_ik para el objetivo [rad]
          /brazo/joint_states sensor_msgs/JointState   ángulos y velocidades medidos (firmware, 20 Hz)
Publica   /brazo/objetivo  geometry_msgs/PointStamped  centro del limón [m], marco `marco_brazo` (-> brazo_ik)
          /brazo/comando   std_msgs/String             armar, s
          /pinza/cierre    std_msgs/Float32            0 = abierta, 100 = cerrada
          /mision/estado   std_msgs/String             estado y motivo de cada cambio
Al cerrarse (Ctrl+C o ros2 launch) manda `s` al brazo: si no, seguiría hacia el último objetivo.
"""

import time

from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Float32, String
import tf2_geometry_msgs  # noqa: F401  (registra PointStamped en tf2)
from tf2_ros import Buffer, TransformException, TransformListener

from mision.fsm import centro_desde_superficie, Mision, Parametros


class NodoMision(Node):

    def __init__(self):
        super().__init__('mision')
        self.marco = self.declare_parameter('marco_brazo', 'brazo_base').value
        self.radio = self.declare_parameter('radio_limon', 0.03).value  # m: la visión da la superficie
        self.edad_max = self.declare_parameter('edad_max_imagen', 1.0).value  # s: detecciones más viejas se ignoran
        self.t_img_prev = None
        base = Parametros()
        par = Parametros(**{k: self.declare_parameter(k, v).value for k, v in vars(base).items() if k != 'reposo'})
        par.reposo = tuple(self.declare_parameter('reposo', list(base.reposo)).value)

        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf, self)
        self.pubs = {
            'comando': self.create_publisher(String, '/brazo/comando', 10),
            'objetivo': self.create_publisher(PointStamped, '/brazo/objetivo', 10),
            'cierre': self.create_publisher(Float32, '/pinza/cierre', 10),
            'estado': self.create_publisher(String, '/mision/estado', 10),
        }
        self.mision = Mision(self.enviar, par)
        self.create_subscription(PointStamped, '/limon/posicion', self.al_limon, 10)
        self.create_subscription(String, '/brazo/estado', lambda m: self.mision.al_estado_brazo(m.data, self.t()), 10)
        self.create_subscription(String, '/brazo/ik_estado', lambda m: self.mision.al_ik(m.data, self.t()), 10)
        self.create_subscription(JointState, '/brazo/joint_cmd',
                                 lambda m: self.mision.al_joint_cmd(self.ordenar(m.name, m.position), self.t()), 10)
        self.create_subscription(JointState, '/brazo/joint_states', self.al_joints, 10)
        self.create_timer(0.1, lambda: self.mision.paso(self.t()))
        self.get_logger().info(f'mision lista (marco {self.marco}): esperando /brazo/estado')

    def t(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def enviar(self, tipo, valor):
        if tipo == 'objetivo':
            msg = PointStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.marco
            msg.point.x, msg.point.y, msg.point.z = valor
        elif tipo == 'cierre':
            msg = Float32(data=float(valor))
        else:
            msg = String(data=valor)
            if tipo == 'estado':
                self.get_logger().info(valor)
        self.pubs[tipo].publish(msg)

    @staticmethod
    def ordenar(nombres, valores):
        """Valores en el orden j1, j2, j3 (o tal cual si vienen sin nombres, como acepta el firmware)."""
        if not nombres:
            return list(valores)
        d = dict(zip(nombres, valores))
        return [d.get(j, float('nan')) for j in ('j1', 'j2', 'j3')]

    def al_joints(self, m):
        self.mision.al_joints(self.ordenar(m.name, m.position), self.ordenar(m.name, m.velocity), self.t())

    def al_limon(self, msg):
        # Detecciones viejas (encoladas) o repetidas no cuentan como muestras nuevas
        t_img, t = Time.from_msg(msg.header.stamp).nanoseconds * 1e-9, self.t()
        if not -0.2 <= t - t_img <= self.edad_max or (self.t_img_prev is not None and t_img <= self.t_img_prev):
            self.get_logger().warn(f'/limon/posicion descartada: imagen de hace {t - t_img:.2f} s o repetida',
                                   throttle_duration_sec=5.0)
            return
        self.t_img_prev = t_img
        c = centro_desde_superficie((msg.point.x, msg.point.y, msg.point.z), self.radio)
        msg.point.x, msg.point.y, msg.point.z = c
        try:
            # TF estática: vale la última (no esperar la del stamp de la imagen)
            tr = self.tf.lookup_transform(self.marco, msg.header.frame_id, Time())
        except TransformException as e:
            self.get_logger().warn(f'sin TF {msg.header.frame_id} -> {self.marco}: {e}', throttle_duration_sec=5.0)
            return
        p = tf2_geometry_msgs.do_transform_point(msg, tr).point
        self.mision.al_limon((p.x, p.y, p.z), t_img, t)


def main(args=None):
    # Sin el manejador de señales de rclpy, para que el contexto siga vivo y se pueda mandar `s` al cerrar
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    nodo = NodoMision()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.enviar('comando', 's')  # detener J1-J3; la pinza queda como está
        time.sleep(0.3)  # que DDS lo entregue antes de destruir el publicador
        nodo.get_logger().info('mision cerrada: brazo detenido')
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
