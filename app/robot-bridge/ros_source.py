"""Suscripciones ROS 2 de observación. No crea publicadores, clientes ni comandos."""
import math
import threading
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from time import monotonic, sleep
from telemetry import finite_vector, range_value
from vision import CAMERAS


class RosReader:
    def __init__(self, store, *, node_name='arturito_observador', camera_frames=None, stereo=None, marker_tools=None):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import qos_profile_sensor_data
        from rclpy.signals import SignalHandlerOptions
        from sensor_msgs.msg import BatteryState, Image, Imu, Range
        from nav_msgs.msg import Odometry
        from std_msgs.msg import String, UInt8
        self.rclpy = rclpy
        self.context = Context()
        rclpy.init(args=[], context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.node = rclpy.create_node(node_name, context=self.context,
                                     enable_rosout=False, start_parameter_services=False)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.error = None
        self.stopped = threading.Event()
        self.marker = None

        def subscribe(kind, topic, callback):
            self.node.create_subscription(kind, topic, callback, qos_profile_sensor_data)

        subscribe(String, '/base/estado', lambda m: store.put('base', m.data[:4096], bool(m.data.strip()), 'Texto de estado vacío' if not m.data.strip() else None))
        subscribe(String, '/brazo/estado', lambda m: store.put('arm', m.data[:4096], bool(m.data.strip()), 'Texto de estado vacío' if not m.data.strip() else None))
        subscribe(BatteryState, '/battery', lambda m: store.put('battery', float(m.voltage) if math.isfinite(m.voltage) else None,
                  math.isfinite(m.voltage) and m.voltage >= 0, 'Tensión no válida' if not math.isfinite(m.voltage) or m.voltage < 0 else None))
        subscribe(UInt8, '/bumpers', lambda m: store.put('bumpers', int(m.data)))

        def imu(m):
            a = [m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z]
            w = [m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z]
            valid = finite_vector(a+w) and m.linear_acceleration_covariance[0] != -1 and m.angular_velocity_covariance[0] != -1
            stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
            previous = getattr(self, '_imu_stamp', None)
            if valid and previous is not None and 0 < stamp - previous < .5:
                self._gyro_yaw += w[2] * (stamp - previous)
            self._imu_stamp = stamp if valid else None
            store.put('imu', {'acceleration_m_s2':a, 'angular_velocity_rad_s':w, 'frame_id':m.header.frame_id,
                              'gyro_yaw_rad': self._gyro_yaw} if valid else None,
                      valid, None if valid else 'IMU sin medición utilizable')

        def odom(m):
            q = m.pose.pose.orientation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            values = [m.pose.pose.position.x, m.pose.pose.position.y, m.twist.twist.linear.x, m.twist.twist.angular.z, yaw]
            valid = finite_vector(values)
            store.put('odom', dict(zip(('x_m','y_m','linear_m_s','angular_rad_s','yaw_rad'), values), frame_id=m.header.frame_id,
                                  child_frame_id=m.child_frame_id) if valid else None, valid, None if valid else 'Odometría no finita')

        def distance(key):
            def callback(m):
                value, valid, reason = range_value(m.range, m.min_range, m.max_range)
                store.put(key, value, valid, reason)
            return callback

        self._gyro_yaw = 0.
        self._imu_stamp = None
        subscribe(Imu, '/imu/data_raw', imu)
        subscribe(Odometry, '/odom', odom)
        for key, suffix in [('range_front','frente'),('range_left','izq'),('range_right','der')]:
            subscribe(Range, '/range/'+suffix, distance(key))
        if camera_frames is not None:
            try:
                import cv2
                import numpy as np
            except ImportError:
                pass
            else:
                from sensor_msgs.msg import CameraInfo
                from stereo_msgs.msg import DisparityImage
                import vision
                projection = {'left': None, 'right': None}   # matriz P de cada cámara rectificada
                last_conversion = {key: -math.inf for key in CAMERAS}

                def lemons():
                    if stereo is None:
                        return []
                    seen = stereo.snapshot()
                    return seen['lemons'] if seen['frame_id'] == 'camera' else []

                def due(key):
                    now = camera_frames.clock()
                    if now - last_conversion[key] < .25:   # ~4 imágenes por segundo por vista
                        return False
                    last_conversion[key] = now
                    return True

                def show(key, picture, p):
                    try:
                        camera_frames.put(key, b'' if picture is None else
                                          vision.encode(cv2, vision.draw_lemons(cv2, picture, lemons(), p)))
                    except cv2.error:
                        camera_frames.put(key, b'')

                def info(key):
                    def callback(m):
                        p = [float(v) for v in m.p]
                        projection[key] = p if len(p) == 12 and p[0] > 0 and p[10] == 1 else None
                    return callback

                def camera(key):
                    def callback(image):
                        if due(key):
                            show(key, vision.image_to_bgr(cv2, np, image), projection[key if key == 'right' else 'left'])
                    return callback

                def depth(message):
                    if not due('center'):
                        return
                    disparity = vision.disparity_to_array(np, message)
                    picture = None if disparity is None else vision.depth_view(
                        cv2, np, disparity, message.min_disparity, message.max_disparity)
                    show('center', picture, projection['left'])

                subscribe(CameraInfo, '/left/camera_info', info('left'))
                subscribe(CameraInfo, '/right/camera_info', info('right'))
                subscribe(Image, CAMERAS['left'], camera('left'))
                subscribe(Image, CAMERAS['right'], camera('right'))
                subscribe(DisparityImage, CAMERAS['center'], depth)
        if stereo is not None:
            from geometry_msgs.msg import PoseArray
            from stereo_msgs.msg import DisparityImage
            subscribe(DisparityImage, '/disparity', lambda m: stereo.disparity())
            subscribe(PoseArray, '/limon/todos', lambda m: stereo.positions(
                m.header.frame_id, ((pose.position.x, pose.position.y, pose.position.z) for pose in m.poses)))
        if marker_tools is not None:
            path = Path(marker_tools) / 'marcas.py'
            if path.is_file():
                spec = spec_from_file_location('arturito_marcas_original', path)
                module = module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    self.marker = module.Marcas(self.node)
                except (ImportError, OSError, AttributeError, ValueError) as error:
                    self.node.get_logger().error(f'No se pudo cargar la calibración ArUco: {error}')
        self.thread = threading.Thread(target=self._run, name='arturito-ros-observer', daemon=True)
        self.thread.start()

    def measure_marker(self, still):
        def wait(seconds):
            until = monotonic() + seconds
            while monotonic() < until:
                if not still():
                    raise ValueError('Mantené quieto el Móvil y soltá los mandos para fijar el cero.')
                sleep(.05)

        try:
            return self.marker.medir(wait, seg=3., minimo=5)
        finally:
            self.marker.juntar = False

    @property
    def available(self):
        return self.thread.is_alive() and self.error is None

    def _run(self):
        try:
            while not self.stopped.is_set() and self.context.ok():
                self.executor.spin_once(timeout_sec=.2)
        except Exception as error:
            self.error = type(error).__name__

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise RuntimeError('El observador ROS no terminó')
        self.executor.shutdown(timeout_sec=1)
        self.node.destroy_node()
        self.rclpy.shutdown(context=self.context)
