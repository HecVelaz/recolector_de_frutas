import json
from pathlib import Path
import tempfile
from time import monotonic
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from bridge import create_app
from base_session import BaseSession
from control_gate import ControlGate, GateDecision
from geometry import validate


def fence():
    return {'type':'Feature', 'properties':{'name':'Prueba'}, 'geometry':{'type':'Polygon',
            'coordinates':[[[-57.51,-25.33],[-57.509,-25.33],[-57.509,-25.329],[-57.51,-25.329],[-57.51,-25.33]]]}}


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app(data_dir=self.directory.name, source='simulation', token='test')
        self.client = TestClient(self.app)
        self.auth = {'Authorization':'Bearer test'}

    def test_auth_and_no_motion_routes(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/telemetry').status_code, 401)
        for route in ('/cmd_vel', '/api/v1/mission', '/api/v1/emergency', '/api/v1/command'):
            self.assertEqual(self.client.post(route, headers=self.auth).status_code, 404)
        self.assertEqual(self.client.post('/api/v1/control/bench/pulse', headers=self.auth).status_code, 404)
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/api/v1/telemetry'):
                pass

    def test_pulse_profile_requires_an_isolated_link(self):
        for profile in (
            dict(source='ros2', base_zero_test=True, control_dry_run=False),
            dict(source='simulation', control_dry_run=True, simulate_base_output=True),
        ):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                create_app(token='test', isolated_pulse_test=True, **profile)

    def test_floor_guard_cannot_attach_to_robot_profile(self):
        with self.assertRaises(ValueError):
            create_app(source='ros2', token='test', control_dry_run=False,
                       base_pulse_test=True, isolated_floor_guard=object())

    def test_zero_bench_requires_isolated_arm_and_never_accepts_motion(self):
        self.exercise_bench_profile(pulse=False)

    def test_motion_bench_requires_wheels_off_ground_and_accepts_only_one_pulse(self):
        self.exercise_bench_profile(pulse=True)

    def exercise_bench_profile(self, *, pulse):
        parked = 'DESARMADA modo=parado seguridad=sin comandos imu=ok rueda_izq=ninguna rueda_der=ninguna'
        events = []

        class Reader:
            available = True
            node = object()

            def __init__(self, store, **kwargs):
                self.store = store

            def close(self):
                pass

        class Link:
            state = parked
            graph_safe = True

            def feedback(self):
                for key, value in dict(base=self.state, battery=11.2, odom={'linear_m_s':0.0,'angular_rad_s':0.0}, bumpers=0,
                    imu={}, range_front={'kind':'distance','meters':0.5}).items():
                    reader.store.put(key, value)
                return self.state, monotonic()

            def exclusive(self):
                self.feedback()
                return self.graph_safe

            def stop(self):
                events.append('zero')
                armed_watchdog = 'ARMADA' + parked.removeprefix('DESARMADA')
                if self.state == armed_watchdog:
                    self.state = armed_watchdog.replace('modo=parado seguridad=sin comandos', 'modo=v/w seguridad=ok')

            def send(self, linear, angular):
                if not pulse:
                    raise AssertionError('El perfil de cero no debe aceptar movimiento')
                events.append((linear, angular))

            def arm(self):
                events.append('arm')
                self.state = 'ARMADA' + parked.removeprefix('DESARMADA')

            def disarm(self):
                events.append('disarm')
                self.state = parked

            def new_session(self):
                return BaseSession(self, request_arm=self.arm, request_disarm=self.disarm)

        link = Link()
        reader = None

        def make_reader(*args, **kwargs):
            nonlocal reader
            reader = Reader(*args, **kwargs)
            return reader

        headers = {**self.auth, 'X-Arturito-Client':'banco'}
        app = create_app(source='ros2', token='test', control_dry_run=False,
                         base_zero_test=not pulse, base_pulse_test=pulse)
        factory = 'for_robot_pulse' if pulse else 'for_robot'
        with patch('ros_source.RosReader', side_effect=make_reader), patch('ros_base_link.RosBaseLink.' + factory, return_value=link):
            with TestClient(app, client=('127.0.0.1', 50000)) as client:
                prefix = '/api/v1/control'
                body = {'app_foreground':True,'physical_ready':True}
                link.feedback()
                self.assertEqual(client.post(prefix + '/prepare', headers=headers, json=body).status_code, 409)
                body['arm_physically_isolated'] = True
                if pulse:
                    self.assertEqual(client.post(prefix + '/prepare', headers=headers, json=body).status_code, 409)
                    body['wheels_off_ground'] = True
                link.graph_safe = False
                self.assertEqual(client.post(prefix + '/prepare', headers=headers, json=body).status_code, 409)
                self.assertEqual(events, [])
                link.graph_safe = True
                self.assertEqual(client.post(prefix + '/prepare', headers=headers, json=body).json()['state'], 'ready')
                confirmed = client.post(prefix + '/confirm', headers=headers)
                self.assertEqual(confirmed.status_code, 200, confirmed.text)
                self.assertTrue(confirmed.json()['robot_command_sent'])
                self.assertEqual(events[:3], ['zero', 'arm', 'zero'])
                self.assertEqual(client.post(prefix + '/manual/base', headers=headers,
                    json={'linear_m_s':0.1,'angular_rad_s':0,'deadman':True}).status_code, 409)
                self.assertEqual(client.post(prefix + '/manual/arm', headers=headers,
                    json={'j1_deg':1,'j2_deg':0,'j3_deg':0,'deadman':True}).status_code, 409)
                pulse_request = dict(linear_m_s=0.04, duration_ms=180, deadman=True)
                if pulse:
                    response = client.post(prefix + '/bench/pulse', headers=headers, json=pulse_request)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertTrue(response.json()['robot_command_sent'])
                    self.assertEqual(client.post(prefix + '/bench/pulse', headers=headers, json=pulse_request).status_code, 409)
                    self.assertEqual(events.count((0.04, 0)), 1)
                else:
                    self.assertEqual(client.post(prefix + '/bench/pulse', headers=headers, json=pulse_request).status_code, 404)
                response = client.post(prefix + '/heartbeat', headers=headers, json={'deadman':False})
                self.assertEqual(response.json()['state'], 'latched_stop')
                self.assertEqual(events[-2:], ['zero', 'disarm'])
                self.assertEqual(client.get('/health').json()['commands_enabled'], pulse)

    def test_control_dry_run_is_explicit_and_never_sends_robot_command(self):
        headers = {**self.auth, 'X-Arturito-Client':'tablet-test'}
        disabled = self.client.post('/api/v1/control/prepare', headers=headers,
            json={'app_foreground':True, 'physical_ready':True, 'mode':'manual'})
        self.assertEqual(disabled.status_code, 409)

        dry = TestClient(create_app(source='simulation', data_dir=self.directory.name,
                                    token='test', control_dry_run=True))
        prepared = dry.post('/api/v1/control/prepare', headers=headers,
            json={'app_foreground':True, 'physical_ready':True, 'mode':'manual'})
        self.assertEqual(prepared.status_code, 200)
        self.assertEqual(prepared.json()['state'], 'blocked')
        self.assertIn('NOT_REAL_ROS_SOURCE', prepared.json()['reasons'])
        self.assertFalse(prepared.json()['robot_command_sent'])
        self.assertFalse(prepared.json()['commands_enabled'])
        self.assertEqual(dry.post('/api/v1/control/confirm', headers=headers).status_code, 409)
        stopped = dry.post('/api/v1/control/stop', headers=headers).json()
        self.assertEqual(stopped['state'], 'latched_stop')
        self.assertFalse(stopped['robot_command_sent'])
        invalid = dry.post('/api/v1/control/manual/base', headers=headers,
            json={'linear_m_s':1.0, 'angular_rad_s':0, 'deadman':True})
        self.assertEqual(invalid.status_code, 422)
        blocked = dry.post('/api/v1/control/manual/arm', headers=headers,
            json={'j1_deg':0, 'j2_deg':0, 'j3_deg':0, 'deadman':True})
        self.assertEqual(blocked.status_code, 409)

    def test_websocket_and_explicit_simulation(self):
        with self.client.websocket_connect('/api/v1/telemetry', headers=self.auth) as ws:
            data = ws.receive_json()
        self.assertTrue(data['simulated'])
        self.assertTrue(data['gps']['simulated'])
        self.assertFalse(data['commands_enabled'])
        self.assertFalse(data['geofence_enforced'])
        self.assertEqual(data['control_gate']['state'], 'blocked')
        self.assertFalse(data['control_gate']['ready'])
        self.assertIn('CONTROL_DISABLED', data['control_gate']['reasons'])

    def test_dry_session_latches_when_safety_evidence_is_lost(self):
        headers = {**self.auth, 'X-Arturito-Client':'tablet-test'}
        prefix = '/api/v1/control'
        for action, payload in (
            ('confirm', {}),
            ('heartbeat', {'deadman':True}),
            ('manual/base', {'linear_m_s':0.1, 'angular_rad_s':0, 'deadman':True}),
        ):
            with self.subTest(action=action), patch('bridge.evaluate_control') as evaluate:
                evaluate.return_value = GateDecision(True, ())
                app = create_app(source='simulation', token='test', control_dry_run=True)
                with TestClient(app) as client:
                    prepared = client.post(prefix + '/prepare', headers=headers,
                        json={'app_foreground':True, 'physical_ready':True})
                    self.assertEqual(prepared.json()['state'], 'ready')
                    if action != 'confirm':
                        self.assertEqual(client.post(prefix + '/confirm', headers=headers).status_code, 200)
                    evaluate.return_value = GateDecision(False, ('IMU_TOO_OLD',))
                    rejected = client.post(prefix + '/' + action, headers=headers, json=payload)
                    self.assertEqual(rejected.status_code, 409)
                    self.assertEqual(rejected.json()['detail']['reasons'], ['IMU_TOO_OLD'])
                    self.assertEqual(client.get('/health').json()['control_gate'], 'latched_stop')
                    evaluate.return_value = GateDecision(True, ())
                    self.assertEqual(client.post(prefix + '/heartbeat', headers=headers,
                        json={'deadman':True}).status_code, 409)

    def test_unknown_real_readings_are_not_simulated(self):
        client = TestClient(create_app(source='estado', data_dir=self.directory.name, token=''))
        data = client.get('/api/v1/telemetry').json()
        self.assertIsNone(data['gps'])
        self.assertIsNone(data['battery_voltage'])
        self.assertIsNone(data['base_state'])
        self.assertFalse(data['base_freshness_known'])
        self.assertFalse(data['simulated'])

    def test_simulated_base_stops_without_a_fresh_permitted_command(self):
        headers = {**self.auth, 'X-Arturito-Client':'tablet-test'}
        prefix = '/api/v1/control'
        zero = {'linear_m_s':0.0, 'angular_rad_s':0.0}
        velocity = {'linear_m_s':0.1, 'angular_rad_s':-0.2}
        for interruption in ('release_deadman', 'expire_lease', 'expire_command', 'sensor_loss', 'stop'):
            with self.subTest(interruption=interruption):
                now = [10.0]
                with patch('bridge.ControlGate', return_value=ControlGate(clock=lambda: now[0])), \
                        patch('bridge.evaluate_control', return_value=GateDecision(True, ())) as evaluate:
                    app = create_app(source='simulation', token='test', control_dry_run=True,
                                     simulate_base_output=True)
                    with TestClient(app) as client:
                        def post(action, **payload):
                            return client.post(prefix + '/' + action, headers=headers, json=payload)

                        self.assertEqual(post('prepare', app_foreground=True, physical_ready=True).json()['state'], 'ready')
                        self.assertEqual(post('confirm').json()['simulated_base_output'], zero)
                        command = post('manual/base', **velocity, deadman=True).json()
                        self.assertEqual(command['simulated_base_output'], velocity)
                        self.assertFalse(command['robot_command_sent'])

                        if interruption == 'release_deadman':
                            self.assertEqual(post('heartbeat', deadman=False).status_code, 200)
                            self.assertEqual(post('heartbeat', deadman=True).json()['simulated_base_output'], zero)
                        elif interruption == 'expire_lease':
                            now[0] += 0.25
                            self.assertEqual(post('heartbeat', deadman=True).status_code, 409)
                        elif interruption == 'expire_command':
                            now[0] += 0.125
                            self.assertEqual(post('heartbeat', deadman=True).status_code, 200)
                            now[0] += 0.125
                        elif interruption == 'sensor_loss':
                            evaluate.return_value = GateDecision(False, ('IMU_TOO_OLD',))
                            self.assertEqual(post('heartbeat', deadman=True).status_code, 409)
                        else:
                            self.assertEqual(post('stop').json()['state'], 'latched_stop')

                        observed = client.get('/api/v1/telemetry', headers=headers).json()
                        self.assertEqual(observed['simulated_base_output'], zero)
                        self.assertFalse(observed['commands_enabled'])

    def test_simulated_base_output_cannot_attach_to_real_sources(self):
        for source in ('ros2', 'estado'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                create_app(source=source, control_dry_run=True, simulate_base_output=True)
        self.assertNotIn('simulated_base_output', self.client.get('/api/v1/telemetry', headers=self.auth).json())

    def test_isolated_simulator_accepts_a_complete_session(self):
        headers = {**self.auth, 'X-Arturito-Client':'tablet-test'}
        with TestClient(create_app(source='simulation', token='test', control_dry_run=True,
                                   simulate_base_output=True)) as client:
            prefix = '/api/v1/control'
            self.assertEqual(client.post(prefix + '/prepare', headers=headers,
                json={'app_foreground':True, 'physical_ready':False}).json()['state'], 'blocked')
            self.assertEqual(client.post(prefix + '/prepare', headers=headers,
                json={'app_foreground':True, 'physical_ready':True}).json()['state'], 'ready')
            self.assertEqual(client.post(prefix + '/confirm', headers=headers).json()['state'], 'enabled')
            movement = client.post(prefix + '/manual/base', headers=headers,
                json={'linear_m_s':0.1, 'angular_rad_s':0, 'deadman':True}).json()
            self.assertFalse(movement['robot_command_sent'])
            self.assertEqual(movement['simulated_base_output']['linear_m_s'], 0.1)
            released = client.post(prefix + '/heartbeat', headers=headers, json={'deadman':False}).json()
            self.assertEqual(released['simulated_base_output']['linear_m_s'], 0)

    def test_save_reload_and_invalid_write_preserves_previous(self):
        result = self.client.put('/api/v1/geofence', json=fence(), headers=self.auth)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()['applied_to_robot'])
        previous = Path(self.directory.name, 'operation-boundary.geojson').read_bytes()
        invalid = fence()
        ring = invalid['geometry']['coordinates'][0]
        ring[1], ring[2] = ring[2], ring[1]
        self.assertEqual(self.client.put('/api/v1/geofence', json=invalid, headers=self.auth).status_code, 422)
        self.assertEqual(previous, Path(self.directory.name, 'operation-boundary.geojson').read_bytes())
        reloaded = TestClient(create_app(source='simulation', data_dir=self.directory.name, token='test'))
        self.assertEqual(reloaded.get('/api/v1/geofence', headers=self.auth).json()['geofence'], result.json()['geofence'])

    def test_size_limit_and_bad_coordinates(self):
        self.assertEqual(self.client.put('/api/v1/geofence', content=b'x'*64001, headers=self.auth).status_code, 413)
        for point in ([True, -25], [0, 90], [float('nan'), 0], [0], 'xx'):
            bad = fence()
            bad['geometry']['coordinates'][0][1] = point
            with self.assertRaises(ValueError):
                validate(bad)

    def test_geometry_orientation_precision_and_limits(self):
        original = fence()
        original['geometry']['coordinates'][0][1][0] = -57.50900001234567
        normalized, area = validate(original)
        self.assertGreater(area, 1)
        self.assertEqual(normalized['geometry']['coordinates'][0][1][0], -57.50900001234567)
        reversed_fence = fence()
        reversed_fence['geometry']['coordinates'][0].reverse()
        reversed_normalized, reversed_area = validate(reversed_fence)
        self.assertAlmostEqual(reversed_area, validate(fence())[1], places=2)
        self.assertEqual(set(map(tuple, reversed_normalized['geometry']['coordinates'][0])),
                         set(map(tuple, fence()['geometry']['coordinates'][0])))
        too_far = fence()
        too_far['geometry']['coordinates'][0][1][0] = -56
        with self.assertRaises(ValueError):
            validate(too_far)


if __name__ == '__main__':
    unittest.main()
