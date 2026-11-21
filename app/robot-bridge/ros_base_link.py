"""Transporte ROS de una sesión de base, independiente del puente de observación."""

from threading import Lock
from time import monotonic

from base_session import BaseSession
from ros_base_output import MAX_LINEAR_M_S, MAX_MANUAL_DUTY_PERCENT, MAX_PHYSICAL_LINEAR_M_S, RosBaseVelocityOutput


class RosBaseLink:
    def __init__(self, node, *, velocity_topic, request_topic, feedback_topic,
                 clock=monotonic, zero_only=False, bench_pulse=False, linear_limit=MAX_LINEAR_M_S):
        from rclpy.qos import qos_profile_sensor_data
        from std_msgs.msg import String

        self._clock = clock
        self._lock = Lock()
        self._feedback = (None, None)
        self._output = RosBaseVelocityOutput(node, topic=velocity_topic, zero_only=zero_only,
                                             bench_pulse=bench_pulse, linear_limit=linear_limit)
        self._node = node
        self._velocity_topic = velocity_topic
        self._request_topic = request_topic
        self._request_type = String
        self._requests = node.create_publisher(String, request_topic, 1)
        self._subscription = node.create_subscription(String, feedback_topic, self._receive, qos_profile_sensor_data)

    @classmethod
    def for_robot(cls, node):
        return cls(node, velocity_topic='/cmd_vel', request_topic='/base/comando',
                   feedback_topic='/base/estado', zero_only=True)

    @classmethod
    def for_robot_pulse(cls, node):
        return cls(node, velocity_topic='/cmd_vel', request_topic='/base/comando',
                   feedback_topic='/base/estado', bench_pulse=True)

    @classmethod
    def for_manual_control(cls, node):
        return cls(node, velocity_topic='/cmd_vel', request_topic='/base/comando',
                   feedback_topic='/base/estado', linear_limit=MAX_PHYSICAL_LINEAR_M_S)

    def _receive(self, message):
        with self._lock:
            self._feedback = (message.data, self._clock())

    def feedback(self):
        with self._lock:
            return self._feedback

    def exclusive(self):
        return all(self._node.count_publishers(topic) == 1 and self._node.count_subscribers(topic) >= 1
                   for topic in (self._velocity_topic, self._request_topic))

    def send_duty(self, left, right):
        if not all(isinstance(value, int) and abs(value) <= MAX_MANUAL_DUTY_PERCENT for value in (left, right)):
            raise ValueError('Duty fuera del límite de banco')
        self._requests.publish(self._request_type(data=f'd {left} {right}'))

    def stop_duty(self):
        self._requests.publish(self._request_type(data='s'))

    def request_disarm(self):
        self._requests.publish(self._request_type(data='desarmar'))

    def new_session(self):
        return BaseSession(self._output,
            request_arm=lambda: self._requests.publish(self._request_type(data='armar')),
            request_disarm=self.request_disarm,
            clock=self._clock, linear_limit=self._output.linear_limit)
