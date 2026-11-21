"""Ensayo de la API de Arturito con un receptor ROS 2 y sin hardware."""

import os
from threading import Lock, Thread
from time import monotonic, sleep
from uuid import uuid4

import rclpy
from fastapi.testclient import TestClient
from geometry_msgs.msg import Twist
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

from bridge import create_app
from floor_geofence import FloorGeofence, FloorPose
from ros_base_link import RosBaseLink

PARKED = 'DESARMADA modo=parado seguridad=sin comandos'
ARMED_WAITING = 'ARMADA modo=parado seguridad=sin comandos'
OK = 'ARMADA modo=v/w seguridad=ok'
BASE_FIELDS = ' imu=ok rueda_izq=ninguna rueda_der=ninguna'


class TestLink:
    def __init__(self, node, *, bench_pulse=False):
        prefix = '/arturito_test/trial_' + uuid4().hex
        self.lock = Lock()
        self.state = PARKED
        self.allow_ack = True
        self.send_feedback = True
        self.events = []
        self.link = RosBaseLink(node, velocity_topic=prefix + '/velocity',
                                request_topic=prefix + '/request', feedback_topic=prefix + '/status',
                                bench_pulse=bench_pulse)
        node.create_subscription(Twist, prefix + '/velocity', self.receive_velocity, 10)
        node.create_subscription(String, prefix + '/request', self.receive_request, 10)
        self._status = node.create_publisher(String, prefix + '/status', 10)
        node.create_timer(0.04, self.publish_status)

    def receive_velocity(self, message):
        with self.lock:
            velocity = (message.linear.x, message.angular.z)
            self.events.append(('velocity', *velocity))
            if self.state == ARMED_WAITING and velocity == (0.0, 0.0):
                self.state = OK

    def receive_request(self, message):
        with self.lock:
            self.events.append(message.data)
            if message.data == 'desarmar':
                self.state = PARKED
            elif self.allow_ack:
                self.state = ARMED_WAITING

    def feedback(self):
        return self.link.feedback()

    def publish_status(self):
        with self.lock:
            if self.send_feedback:
                self._status.publish(String(data=self.state + BASE_FIELDS))

    def new_session(self):
        return self.link.new_session()

    def configure(self, *, allow_ack=True, state=None, send_feedback=True):
        with self.lock:
            self.allow_ack = allow_ack
            self.send_feedback = send_feedback
            if state is not None:
                self.state = state

    def observed(self):
        with self.lock:
            return list(self.events)


def wait_for(predicate):
    deadline = monotonic() + 4
    while not predicate():
        if monotonic() >= deadline:
            raise AssertionError('El receptor no observó el resultado esperado')
        sleep(0.01)


def verify_pulse_profile(link):
    headers = {'Authorization':'Bearer qa', 'X-Arturito-Client':'pulse-test'}
    app = create_app(source='simulation', token='qa', control_dry_run=True,
                     simulate_base_output=True, isolated_base_link=link, isolated_pulse_test=True)
    with TestClient(app) as client:
        def post(action, **body):
            return client.post('/api/v1/control/' + action, headers=headers, json=body)

        pulse = dict(linear_m_s=0.04, duration_ms=120, deadman=True)
        for end in ('deadline', 'release', 'alarm'):
            link.configure()
            wait_for(lambda: link.feedback()[0] == PARKED + BASE_FIELDS)
            assert post('prepare', app_foreground=True, physical_ready=True).json()['state'] == 'ready'
            assert post('bench/pulse', **pulse).status_code == 409
            assert post('confirm').json()['state'] == 'enabled'
            assert post('manual/base', linear_m_s=0.04, angular_rad_s=0, deadman=True).status_code == 409
            assert post('bench/pulse', **dict(pulse, duration_ms=201)).status_code == 422
            assert post('bench/pulse', **dict(pulse, linear_m_s=0.051)).status_code == 422
            offset = len(link.observed())
            response = post('bench/pulse', **pulse)
            assert response.status_code == 200 and not response.json()['robot_command_sent']
            assert post('bench/pulse', **pulse).status_code == 409
            movement = ('velocity', 0.04, 0.0)
            wait_for(lambda: movement in link.observed()[offset:])
            if end == 'release':
                assert post('heartbeat', deadman=False).json()['state'] == 'latched_stop'
            elif end == 'alarm':
                link.configure(state='ARMADA modo=v/w seguridad=EMERGENCIA')
            wait_for(lambda: 'desarmar' in link.observed()[offset:])
            wait_for(lambda: ('velocity', 0.0, 0.0) in link.observed()[offset:])
            assert client.get('/health').json()['control_gate'] == 'latched_stop'
            events = link.observed()[offset:]
            assert events.count(movement) == 1
            assert ('velocity', 0.0, 0.0) in events[events.index(movement) + 1:]
            assert post('bench/pulse', **pulse).status_code == 409
    print('Pulso aislado: único, con límites validados y parada por plazo, suelta o alarma.')


def verify_floor_guard(link):
    headers = {'Authorization':'Bearer qa', 'X-Arturito-Client':'floor-test'}
    pose_x = 1.0
    localization = False

    def read_pose():
        return FloorPose(pose_x, 1.0, 0.0, 'lab_map', 'mark-a', monotonic(), 0.02, 0.02) if localization else None

    guard = FloorGeofence([(0, 0), (2, 0), (2, 2), (0, 2)], frame_id='lab_map', anchor_id='mark-a',
                          robot_radius_m=0.25, stop_reserve_m=0.05, max_position_error_m=0.08,
                          max_yaw_error_rad=0.1, max_pose_age_s=0.2, pose_reader=read_pose)
    app = create_app(source='simulation', token='qa', control_dry_run=True, simulate_base_output=True,
                     isolated_base_link=link, isolated_pulse_test=True, isolated_floor_guard=guard)
    with TestClient(app) as client:
        def post(action, **body):
            return client.post('/api/v1/control/' + action, headers=headers, json=body)

        def prepare():
            wait_for(lambda: link.feedback()[0] == PARKED + BASE_FIELDS)
            return post('prepare', app_foreground=True, physical_ready=True).json()

        def pulse():
            return post('bench/pulse', linear_m_s=0.04, duration_ms=120, deadman=True)

        blocked = prepare()
        assert blocked['state'] == 'blocked' and 'FLOOR_POSE_UNAVAILABLE' in blocked['reasons']
        assert not link.observed()
        localization = True
        pose_x = 1.677
        assert prepare()['state'] == 'ready'
        assert post('confirm').json()['state'] == 'enabled'
        denied = pulse()
        assert denied.status_code == 409 and denied.json()['detail']['reason'] == 'FLOOR_CLEARANCE_INSUFFICIENT'
        wait_for(lambda: 'desarmar' in link.observed())
        assert not any(isinstance(event, tuple) and event[1:] != (0.0, 0.0) for event in link.observed())

        pose_x = 1.0
        assert prepare()['state'] == 'ready'
        assert post('confirm').json()['state'] == 'enabled'
        assert pulse().status_code == 200
        wait_for(lambda: ('velocity', 0.04, 0.0) in link.observed())
        offset = len(link.observed())
        localization = False
        wait_for(lambda: ('velocity', 0.0, 0.0) in link.observed()[offset:] and 'desarmar' in link.observed()[offset:])
        telemetry = client.get('/api/v1/telemetry', headers=headers).json()
        assert telemetry['control_gate']['state'] == 'latched_stop'
        assert not telemetry['geofence_enforced'] and not telemetry['commands_enabled']
    print('Piso simulado: sin pose o margen insuficiente bloquea; pérdida de pose envía cero y desarma.')


def main():
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ.pop('ROS_STATIC_PEERS', None)
    context = Context()
    rclpy.init(args=[], context=context, domain_id=118)
    node = rclpy.create_node('arturito_prueba_api', context=context)
    executor = SingleThreadedExecutor(context=context)
    link = TestLink(node)
    executor.add_node(node)
    thread = Thread(target=executor.spin)
    thread.start()
    try:
        headers = {'Authorization':'Bearer qa', 'X-Arturito-Client':'tablet-test'}
        app = create_app(source='simulation', token='qa', control_dry_run=True,
                         simulate_base_output=True, isolated_base_link=link)
        with TestClient(app) as client:
            def post(action, **body):
                return client.post('/api/v1/control/' + action, headers=headers, json=body)

            def prepare():
                wait_for(lambda: link.feedback()[0] == PARKED + BASE_FIELDS)
                assert post('prepare', app_foreground=True, physical_ready=True).json()['state'] == 'ready'

            def command():
                return post('manual/base', linear_m_s=0.1, angular_rad_s=0, deadman=True)

            def verify_stop(offset):
                wait_for(lambda: 'desarmar' in link.observed()[offset:])
                wait_for(lambda: ('velocity', 0.0, 0.0) in link.observed()[offset:])
                assert client.get('/health').json()['control_gate'] == 'latched_stop'
                assert command().status_code == 409

            link.configure(allow_ack=False)
            prepare()
            assert command().status_code == 409
            assert post('confirm').status_code == 409
            verify_stop(0)
            wait_for(lambda: link.observed().count(('velocity', 0.0, 0.0)) == 2)
            assert ('velocity', 0.1, 0.0) not in link.observed()

            for interruption in ('release', 'link_timeout', 'alarm', 'feedback_timeout'):
                link.configure()
                prepare()
                assert post('confirm').json()['state'] == 'enabled'
                offset = len(link.observed())
                response = command().json()
                assert response['simulated_base_output']['linear_m_s'] == 0.1
                assert not response['robot_command_sent']
                wait_for(lambda: ('velocity', 0.1, 0.0) in link.observed()[offset:])
                offset = len(link.observed())
                if interruption == 'release':
                    assert post('heartbeat', deadman=False).json()['state'] == 'latched_stop'
                elif interruption == 'alarm':
                    link.configure(state='ARMADA modo=parado seguridad=EMERGENCIA')
                elif interruption == 'feedback_timeout':
                    link.configure(send_feedback=False)
                    deadline = monotonic() + 2
                    while command().status_code == 200:
                        assert monotonic() < deadline
                        sleep(0.08)
                verify_stop(offset)
            print('API y ROS aislado: armado sin confirmación bloqueado; suelta, pérdida de enlace, alarma y telemetría vencida detienen y desarman.')
        verify_pulse_profile(TestLink(node, bench_pulse=True))
        verify_floor_guard(TestLink(node, bench_pulse=True))
    finally:
        executor.shutdown()
        thread.join(timeout=3)
        node.destroy_node()
        rclpy.shutdown(context=context)


if __name__ == '__main__':
    main()
