"""Prueba de transporte en un dominio ROS separado con un receptor de prueba."""

import os
from time import monotonic
from uuid import uuid4

import rclpy
from geometry_msgs.msg import Twist
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

from base_session import BaseSession, BaseSessionState
from ros_base_output import RosBaseVelocityOutput


def wait_for(executor, predicate):
    deadline = monotonic() + 5
    while not predicate():
        if monotonic() >= deadline:
            raise RuntimeError('Se agotó la espera del receptor de prueba')
        executor.spin_once(timeout_sec=0.05)


def main():
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ.pop('ROS_STATIC_PEERS', None)
    context = Context()
    rclpy.init(args=[], context=context, domain_id=118)
    executor = SingleThreadedExecutor(context=context)
    node = rclpy.create_node('arturito_prueba_salida', context=context)
    executor.add_node(node)
    try:
        topic = '/arturito_test/velocity_' + uuid4().hex
        received = []
        node.create_subscription(Twist, topic, received.append, 10)
        output = RosBaseVelocityOutput(node, topic=topic)
        wait_for(executor, lambda: node.count_publishers(topic) == 1 and node.count_subscribers(topic) == 1)
        output.send(0.1, -0.2)
        wait_for(executor, lambda: len(received) == 1)
        message = received.pop()
        assert (message.linear.x, message.angular.z) == (0.1, -0.2)
        assert (message.linear.y, message.linear.z, message.angular.x, message.angular.y) == (0.0,) * 4
        for linear, angular in ((float('nan'), 0), (0, float('inf')), (0.151, 0), (0, -1.001)):
            try:
                output.send(linear, angular)
            except ValueError:
                continue
            raise AssertionError('Se aceptó una velocidad inválida')
        output.stop()
        wait_for(executor, lambda: len(received) >= 1)
        assert received == [Twist()]
        received.clear()

        command_topic = topic + '_state_request'
        requests = []
        node.create_subscription(String, command_topic, lambda message: requests.append(message.data), 10)
        publisher = node.create_publisher(String, command_topic, 10)
        wait_for(executor, lambda: publisher.get_subscription_count() == 1)
        session = BaseSession(output,
            request_arm=lambda: publisher.publish(String(data='armar')),
            request_disarm=lambda: publisher.publish(String(data='desarmar')))
        assert session.begin(safe=True, base_state='DESARMADA modo=parado')
        wait_for(executor, lambda: len(requests) == 1 and len(received) == 1)
        assert requests == ['armar'] and received == [Twist()]
        feedback = dict(safe=True, session_alive=True, base_state='ARMADA modo=parado seguridad=sin comandos', received_at=monotonic())
        session.update(**feedback)
        wait_for(executor, lambda: len(received) == 2)
        assert received[-1] == Twist()
        feedback.update(base_state='ARMADA modo=parado seguridad=ok', received_at=monotonic())
        session.update(**feedback)
        assert session.velocity(0.1, -0.2, deadman=True, **feedback)
        wait_for(executor, lambda: len(received) == 3)
        assert (received[-1].linear.x, received[-1].angular.z) == (0.1, -0.2)
        session.update(**dict(feedback, safe=False))
        wait_for(executor, lambda: len(requests) == 2 and len(received) == 4)
        assert requests == ['armar', 'desarmar'] and received[-1] == Twist()
        assert session.state == BaseSessionState.STOPPED
        print('ROS 2 aislado: armado, velocidad y parada con desarmado verificados.')
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown(context=context)


if __name__ == '__main__':
    main()
