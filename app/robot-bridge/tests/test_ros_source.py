"""El observador convierte Range del TFmini-S sin necesitar ROS ni hardware."""
import math
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ros_source import RosReader
from telemetry import TelemetryStore


class LidarSubscriptionTest(unittest.TestCase):
    def test_topic_and_invalid_sample_reach_the_dashboard_source(self):
        node = MagicMock()
        ros = MagicMock()
        ros.create_node.return_value = node
        range_type = type('Range', (), {})
        modules = {
            'rclpy': ros,
            'rclpy.context': SimpleNamespace(Context=MagicMock()),
            'rclpy.executors': SimpleNamespace(SingleThreadedExecutor=MagicMock()),
            'rclpy.qos': SimpleNamespace(qos_profile_sensor_data=object()),
            'rclpy.signals': SimpleNamespace(SignalHandlerOptions=SimpleNamespace(NO=0)),
            'sensor_msgs': SimpleNamespace(),
            'sensor_msgs.msg': SimpleNamespace(BatteryState=object, Image=object, Imu=object, Range=range_type),
            'nav_msgs': SimpleNamespace(),
            'nav_msgs.msg': SimpleNamespace(Odometry=object),
            'std_msgs': SimpleNamespace(),
            'std_msgs.msg': SimpleNamespace(String=object, UInt8=object),
        }
        store = TelemetryStore()
        with patch.dict(sys.modules, modules), patch('ros_source.threading.Thread'):
            RosReader(store)
        calls = [c for c in node.create_subscription.call_args_list if c.args[1] == '/range/lidar_izq']
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0].args[0], range_type)
        callback = calls[0].args[2]
        callback(SimpleNamespace(range=.62, min_range=.1, max_range=12.))
        def source():
            return next(s for s in store.snapshot()['sources'] if s['key'] == 'range_lidar_left')
        self.assertEqual(source()['value']['meters'], .62)
        self.assertEqual(source()['status'], 'fresh')
        callback(SimpleNamespace(range=math.nan, min_range=.1, max_range=12.))
        self.assertIsNone(source()['value'])
        self.assertEqual(source()['status'], 'invalid')
        self.assertIn('LiDAR', source()['reason'])


class UltrasonicHoldTest(unittest.TestCase):
    def test_a_single_echo_miss_keeps_the_last_good_front_reading(self):
        # 25/11, en el robot: una muestra sin eco del frente cortaba Rodear árbol (RANGE_FRONT_NOT_FRESH)
        node, ros = MagicMock(), MagicMock()
        ros.create_node.return_value = node
        range_type = type('Range', (), {})
        modules = {
            'rclpy': ros,
            'rclpy.context': SimpleNamespace(Context=MagicMock()),
            'rclpy.executors': SimpleNamespace(SingleThreadedExecutor=MagicMock()),
            'rclpy.qos': SimpleNamespace(qos_profile_sensor_data=object()),
            'rclpy.signals': SimpleNamespace(SignalHandlerOptions=SimpleNamespace(NO=0)),
            'sensor_msgs': SimpleNamespace(),
            'sensor_msgs.msg': SimpleNamespace(BatteryState=object, Image=object, Imu=object, Range=range_type),
            'nav_msgs': SimpleNamespace(),
            'nav_msgs.msg': SimpleNamespace(Odometry=object),
            'std_msgs': SimpleNamespace(),
            'std_msgs.msg': SimpleNamespace(String=object, UInt8=object),
        }
        store = TelemetryStore()
        with patch.dict(sys.modules, modules), patch('ros_source.threading.Thread'):
            RosReader(store)
        front = next(c.args[2] for c in node.create_subscription.call_args_list if c.args[1] == '/range/frente')
        lidar = next(c.args[2] for c in node.create_subscription.call_args_list if c.args[1] == '/range/lidar_izq')

        def source(key):
            return next(s for s in store.snapshot()['sources'] if s['key'] == key)
        with patch('ros_source.monotonic', return_value=10.):
            front(SimpleNamespace(range=1.2, min_range=.02, max_range=4.))
            lidar(SimpleNamespace(range=.3, min_range=.1, max_range=12.))
        with patch('ros_source.monotonic', return_value=10.3):
            front(SimpleNamespace(range=math.nan, min_range=.02, max_range=4.))
            lidar(SimpleNamespace(range=math.nan, min_range=.1, max_range=12.))
        self.assertEqual(source('range_front')['value']['meters'], 1.2)   # la última buena
        self.assertEqual(source('range_lidar_left')['status'], 'invalid')   # el lidar no: ya tiene su vigencia
        with patch('ros_source.monotonic', return_value=10.6):
            front(SimpleNamespace(range=math.nan, min_range=.02, max_range=4.))
        self.assertEqual(source('range_front')['status'], 'invalid')   # más de 0,5 s sin una buena
