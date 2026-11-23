"""Transporte ROS 2 de velocidad para una base diferencial."""

from math import isfinite

MAX_LINEAR_M_S = 0.15
MAX_PHYSICAL_LINEAR_M_S = 0.25  # CFG_DIF.vMax del firmware de tracción.
MAX_ANGULAR_RAD_S = 1.0  # CFG_DIF.wMax del firmware de tracción (igual que teleop.html)
MAX_BENCH_PULSE_M_S = 0.05
MAX_MANUAL_DUTY_PERCENT = 25  # JOG_DUTY_MAX del firmware de tracción.
MIN_MANUAL_START_DUTY_PERCENT = 20  # Arranque observado con ruedas elevadas.


class RosBaseVelocityOutput:
    """Publica una muestra por llamada. El llamador controla la habilitación y el vencimiento."""

    def __init__(self, node, *, topic, zero_only=False, bench_pulse=False, linear_limit=MAX_LINEAR_M_S):
        from geometry_msgs.msg import Twist
        from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

        self._message_type = Twist
        self._zero_only = zero_only
        self._bench_pulse = bench_pulse
        self.linear_limit = linear_limit
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.VOLATILE)
        self._publisher = node.create_publisher(Twist, topic, qos)

    def send(self, linear_m_s: float, angular_rad_s: float) -> None:
        if self._zero_only and (linear_m_s != 0.0 or angular_rad_s != 0.0):
            raise ValueError('El transporte de banco solo permite velocidad cero')
        if self._bench_pulse and (not 0.0 <= linear_m_s <= MAX_BENCH_PULSE_M_S or angular_rad_s != 0.0):
            raise ValueError('El transporte de pulso solo admite avance lineal limitado')
        if not isfinite(linear_m_s) or not -self.linear_limit <= linear_m_s <= self.linear_limit:
            raise ValueError('Velocidad lineal fuera de límites')
        if not isfinite(angular_rad_s) or not -MAX_ANGULAR_RAD_S <= angular_rad_s <= MAX_ANGULAR_RAD_S:
            raise ValueError('Velocidad angular fuera de límites')
        message = self._message_type()
        message.linear.x = float(linear_m_s)
        message.angular.z = float(angular_rad_s)
        self._publisher.publish(message)

    def stop(self) -> None:
        self.send(0.0, 0.0)
