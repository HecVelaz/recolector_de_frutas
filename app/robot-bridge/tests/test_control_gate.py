import unittest
from control_gate import ControlGate, ControlMode, GateState, evaluate


def real_snapshot():
    keys = ('base','arm','battery','odom','bumpers','imu','range_front')
    values = {k:None for k in keys}
    values['bumpers'] = 0
    return {
        'source':'ros2', 'simulated':False, 'upstream_available':True,
        'commands_enabled':False, 'geofence_enforced':False,
        'base_state':'DESARMADA modo=parado seguridad=ok imu=ok rueda_izq=ninguna rueda_der=ninguna',
        'arm_state':'q=0,0,0;e=3,3,3;c=111;fc=000;pz=-1;mn=-1',
        'battery_voltage':11.5,
        'sources':[{'key':k,'status':'fresh','age_ms':20,'value':values[k]} for k in keys],
    }


class EvaluateTest(unittest.TestCase):
    def good(self, **kw):
        defaults={'feature_enabled':True,'authenticated':True,'app_foreground':True,'physical_ready':True}
        defaults.update(kw)
        return evaluate(real_snapshot(), **defaults)

    def test_complete_evidence_is_ready(self):
        self.assertTrue(self.good().ready)

    def test_disabled_by_default(self):
        decision=evaluate(real_snapshot())
        self.assertFalse(decision.ready)
        self.assertIn('CONTROL_DISABLED',decision.reasons)

    def test_stale_low_battery_and_unhomed_block(self):
        data=real_snapshot(); data['sources'][0]['age_ms']=651
        data['battery_voltage']=9; data['arm_state']=data['arm_state'].replace('c=111','c=000')
        decision=evaluate(data,feature_enabled=True,authenticated=True,app_foreground=True,physical_ready=True)
        self.assertTrue({'BASE_TOO_OLD','BATTERY_TOO_LOW_OR_UNKNOWN','ARM_NOT_HOMED'} <= set(decision.reasons))

    def test_each_source_expires_at_its_own_limit(self):
        for key, limit in (('base', 650), ('battery', 1250), ('arm', 500), ('imu', 500), ('range_front', 500)):
            with self.subTest(source=key):
                data = real_snapshot()
                reading = next(item for item in data['sources'] if item['key'] == key)
                flags = dict(feature_enabled=True, authenticated=True, app_foreground=True, physical_ready=True)
                reading['age_ms'] = limit
                self.assertTrue(evaluate(data, **flags).ready)
                reading['age_ms'] += 1
                self.assertIn(key.upper() + '_TOO_OLD', evaluate(data, **flags).reasons)

    def test_autonomous_requires_enforced_geofence(self):
        decision=self.good(mode=ControlMode.AUTONOMOUS)
        self.assertIn('GEOFENCE_NOT_ENFORCED',decision.reasons)

    def test_invalid_voltage_and_contradictory_base_status_block(self):
        data = real_snapshot()
        data['battery_voltage'] = float('nan')
        data['base_state'] = data['base_state'].replace('seguridad=ok imu=ok', 'seguridad=okay imu=SIN_DATOS')
        decision = evaluate(data, feature_enabled=True, authenticated=True, app_foreground=True, physical_ready=True)
        self.assertTrue({'BASE_SAFETY_NOT_OK', 'BASE_IMU_NOT_OK', 'BATTERY_TOO_LOW_OR_UNKNOWN'} <= set(decision.reasons))


class LeaseTest(unittest.TestCase):
    def setUp(self): self.now=1.0; self.gate=ControlGate(lambda:self.now)

    def test_owner_deadman_and_timeout(self):
        self.assertTrue(self.gate.prepare('tablet',self._ok()))
        self.assertTrue(self.gate.enable('tablet'))
        self.assertFalse(self.gate.heartbeat('other',True))
        self.assertTrue(self.gate.heartbeat('tablet',True))
        self.assertEqual(self.gate.state,GateState.ACTIVE)
        self.now+=.251
        self.assertEqual(self.gate.check(),GateState.LATCHED_STOP)

    def test_failed_preparation_stays_blocked(self):
        self.assertFalse(self.gate.prepare('tablet',evaluate(real_snapshot())))
        self.assertEqual(self.gate.state,GateState.BLOCKED)

    def test_late_heartbeat_cannot_revive_session_without_prior_status_check(self):
        self.assertTrue(self.gate.prepare('tablet', self._ok()))
        self.assertTrue(self.gate.enable('tablet'))
        self.now += .25
        self.assertFalse(self.gate.heartbeat('tablet', True))
        self.assertEqual(self.gate.state, GateState.LATCHED_STOP)
        self.assertIsNone(self.gate.owner)

    def test_second_owner_cannot_replace_live_lease(self):
        self.assertTrue(self.gate.prepare('tablet-a',self._ok()))
        self.assertFalse(self.gate.prepare('tablet-b',self._ok()))
        self.assertEqual(self.gate.owner,'tablet-a')
        self.assertEqual(self.gate.state,GateState.READY)

    def _ok(self):
        return evaluate(real_snapshot(),feature_enabled=True,authenticated=True,app_foreground=True,physical_ready=True)


if __name__=='__main__': unittest.main()
