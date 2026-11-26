import json
import math
import unittest
from telemetry import TelemetryStore, range_value


class TelemetryTest(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.store = TelemetryStore(clock=lambda:self.now)

    def test_unchanged_value_is_fresh_only_when_a_new_message_arrives(self):
        self.store.put('base', 'DESARMADA modo=libre seguridad=ok imu=ok')
        self.now += 2
        self.store.put('base', 'DESARMADA modo=libre seguridad=ok imu=ok')
        self.now += 2
        self.assertEqual(self.store.snapshot()['boards']['base']['status'], 'fresh')
        self.now += 2
        data = self.store.snapshot()
        self.assertEqual(data['boards']['base']['status'], 'stale')
        self.assertIsNone(data['base_state'])
        self.assertTrue(any(a['code']=='BASE_STALE' for a in data['alarm_details']))

    def test_missing_hardware_does_not_become_connected(self):
        self.store.put('battery', 11.72)
        data = self.store.snapshot()
        self.assertEqual(data['battery_voltage'], 11.72)
        self.assertEqual(data['boards']['base']['status'], 'waiting')
        self.assertEqual(data['boards']['arm']['status'], 'waiting')
        self.assertTrue(data['alarm_details'])

    def test_invalid_message_has_receipt_age_but_no_current_value(self):
        self.store.put('range_front', None, False, 'Sin eco')
        source = next(s for s in self.store.snapshot()['sources'] if s['key']=='range_front')
        self.assertEqual(source['status'], 'invalid')
        self.assertEqual(source['age_ms'], 0)
        self.assertIsNone(source['value'])
        self.now += 4
        self.assertEqual(next(s for s in self.store.snapshot()['sources'] if s['key']=='range_front')['status'], 'stale')

    def test_real_flags_are_separated_and_not_sticky(self):
        self.store.put('base', 'DESARMADA modo=libre seguridad=EMERGENCIA (seta) SETA BATERIA_BAJA imu=SIN_DATOS rueda_izq=encoder rueda_der=ninguna')
        codes={a['code'] for a in self.store.snapshot()['alarm_details']}
        self.assertTrue({'SETA','BATERIA_BAJA','IMU_SIN_DATOS','RUEDA_IZQ','SEGURIDAD_BASE'} <= codes)
        self.assertEqual(self.store.snapshot()['alarm_details'][0]['severity'], 'critical')
        self.store.put('base','DESARMADA modo=libre seguridad=ok imu=ok rueda_izq=ninguna rueda_der=ninguna')
        self.assertFalse({'SETA','BATERIA_BAJA','IMU_SIN_DATOS','RUEDA_IZQ','SEGURIDAD_BASE'} & {a['code'] for a in self.store.snapshot()['alarm_details']})

    def test_sensor_values_expire_independently(self):
        self.store.put('battery', 12.0)
        self.store.put('arm','q=0,0,0;e=0,0,0;pz=-1;mn=-1')
        self.now += 4
        self.store.put('base', 'DESARMADA seguridad=ok imu=ok')
        data=self.store.snapshot()
        self.assertIsNone(data['battery_voltage'])
        self.assertIsNone(data['arm_state'])
        self.assertIsNotNone(data['base_state'])
        self.assertEqual(data['boards']['arm']['status'],'stale')

    def test_lidar_missing_invalid_and_disconnected_never_show_old_distance(self):
        def lidar():
            return next(s for s in self.store.snapshot()['sources'] if s['key'] == 'range_lidar_left')
        self.assertEqual(lidar()['status'], 'waiting')
        self.assertEqual(lidar()['topic'], '/range/lidar_izq')
        self.store.put('range_lidar_left', *range_value(.73, .1, 12))
        self.assertEqual(lidar()['value'], {'kind': 'distance', 'meters': .73})
        self.store.put('range_lidar_left', *range_value(math.nan, .1, 12))
        self.assertEqual(lidar()['status'], 'invalid')
        self.assertIsNone(lidar()['value'])
        self.store.put('range_lidar_left', *range_value(.60, .1, 12))
        self.now += 4
        self.store.put('range_left', *range_value(.30, .02, 4))
        self.assertEqual(lidar()['status'], 'stale')
        self.assertIsNone(lidar()['value'])
        json.dumps(self.store.snapshot(), allow_nan=False)

    def test_range_nonfinite_values_are_explicit_and_json_safe(self):
        value,valid,reason=range_value(math.inf,.02,4)
        self.assertTrue(valid)
        self.assertEqual(value['kind'],'out_of_range')
        for x in (math.nan,-math.inf,-1,5):
            value,valid,reason=range_value(x,.02,4)
            self.assertFalse(valid)
            self.store.put('range_front',value,valid,reason)
            json.dumps(self.store.snapshot(),allow_nan=False)
        self.assertEqual(range_value(.5,.02,4)[0]['meters'],.5)


if __name__=='__main__': unittest.main()
