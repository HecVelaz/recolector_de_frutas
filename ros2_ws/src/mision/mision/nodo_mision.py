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
Con autonomo:=true además recorre la hilera solo (recorrido.py):
Suscribe  /odom nav_msgs/Odometry (avance), /imu/data_raw sensor_msgs/Imu (rumbo), /range/frente|izq|der sensor_msgs/Range, /bumpers std_msgs/UInt8,
          /base/estado std_msgs/String, /yolo/detecciones vision_msgs/Detection2DArray (clase `clase_limon`)
Publica   /cmd_vel geometry_msgs/Twist (10 Hz, siempre: el watchdog de la base es de 300 ms), /base/comando (armar),
          /recorrido/estado std_msgs/String
Al cerrarse (Ctrl+C o ros2 launch) manda `s` al brazo y a la base: si no, seguirían hacia el último objetivo.
"""

import math
import time

from geometry_msgs.msg import PointStamped, Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from sensor_msgs.msg import Imu, JointState, Range
from std_msgs.msg import Float32, String, UInt8
from vision_msgs.msg import Detection2DArray
import tf2_geometry_msgs  # noqa: F401  (registra PointStamped en tf2)
from tf2_ros import Buffer, TransformException, TransformListener

from mision.fsm import centro_desde_superficie, Mision, Parametros
from mision.recorrido import OdometriaGiro, ParRecorrido, Recorrido


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
        self.recorrido = None
        if self.declare_parameter('autonomo', False).value:
            base_r = ParRecorrido(largo_herramienta=par.largo_herramienta)
            par_r = ParRecorrido(**{k: self.declare_parameter(k, v).value for k, v in vars(base_r).items()
                                    if k != 'largo_herramienta'}, largo_herramienta=par.largo_herramienta)
            self.pubs.update({
                'cmd_vel': self.create_publisher(Twist, '/cmd_vel', 10),
                'comando_base': self.create_publisher(String, '/base/comando', 10),
                'estado_recorrido': self.create_publisher(String, '/recorrido/estado', 10),
            })
            self.recorrido = Recorrido(self.enviar_recorrido, par_r)
            self.rangos = [None] * 3
            self.odo = OdometriaGiro()
            self.create_subscription(Odometry, '/odom', self.al_odom, 10)
            self.create_subscription(Imu, '/imu/data_raw',
                                     lambda m: self.odo.al_giro(m.angular_velocity.z,
                                                                Time.from_msg(m.header.stamp).nanoseconds * 1e-9), 50)
            for k, n in enumerate(('frente', 'izq', 'der')):
                self.create_subscription(Range, f'/range/{n}', lambda m, k=k: self.al_rango(k, m), 10)
            self.create_subscription(UInt8, '/bumpers', lambda m: self.recorrido.al_bumpers(m.data, self.t()), 10)
            self.create_subscription(String, '/base/estado',
                                     lambda m: self.recorrido.al_estado_base(m.data, self.t()), 10)
            self.clase_limon = self.declare_parameter('clase_limon', 'limon').value
            self.create_subscription(Detection2DArray, '/yolo/detecciones', self.al_detecciones, 10)
        self.create_timer(0.1, self.paso)
        self.get_logger().info(f'mision lista (marco {self.marco}{", recorrido autónomo" if self.recorrido else ""})'
                               ': esperando /brazo/estado')

    def paso(self):
        t = self.t()
        if self.recorrido:
            self.recorrido.al_estado_mision(self.mision.estado, t)
            self.recorrido.paso(t)
            self.mision.base_quieta = self.recorrido.base_quieta(t)
        self.mision.paso(t)

    def al_odom(self, m):
        p, q = m.pose.pose.position, m.pose.pose.orientation
        self.odo.al_odom(p.x, p.y, math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
        self.recorrido.al_odom(self.odo.x, self.odo.y, self.odo.rumbo, self.t())

    def al_detecciones(self, m):
        cajas = [(d.bbox.center.position.x, d.bbox.size_x) for d in m.detections
                 if d.results and d.results[0].hypothesis.class_id == self.clase_limon]
        self.recorrido.al_detecciones(cajas, self.t())

    def al_rango(self, k, m):
        self.rangos[k] = m.range
        self.recorrido.al_rangos(self.rangos, self.t())

    def enviar_recorrido(self, tipo, valor):
        if tipo == 'cmd_vel':
            msg = Twist()
            msg.linear.x, msg.angular.z = float(valor[0]), float(valor[1])
            self.pubs['cmd_vel'].publish(msg)
        elif tipo == 'comando_base':
            self.pubs['comando_base'].publish(String(data=valor))
        else:
            self.pubs['estado_recorrido'].publish(String(data=valor))
            self.get_logger().info('recorrido: ' + valor)

    def t(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def enviar(self, tipo, valor):
        if tipo == 'fuera_de_alcance':
            if self.recorrido:
                self.recorrido.al_fuera_de_alcance(valor, self.t())
            return
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
        if nodo.recorrido:
            nodo.enviar_recorrido('cmd_vel', (0.0, 0.0))
            nodo.pubs['comando_base'].publish(String(data='s'))
        time.sleep(0.3)  # que DDS lo entregue antes de destruir el publicador
        nodo.get_logger().info('mision cerrada: brazo detenido')
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
