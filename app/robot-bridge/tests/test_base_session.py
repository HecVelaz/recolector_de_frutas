import unittest

from base_session import BaseSession, BaseSessionState


class BaseSessionTest(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.events = []
        self.session = BaseSession(self, clock=lambda: self.now,
            request_arm=lambda: self.events.append('arm'),
            request_disarm=lambda: self.events.append('disarm'))

    def send(self, linear, angular):
        self.events.append((linear, angular))

    def stop(self):
        self.send(0, 0)

    def feedback(self, state='ARMADA modo=parado seguridad=ok', **overrides):
        return dict({'safe':True, 'session_alive':True, 'base_state':state, 'received_at':self.now}, **overrides)

    def begin(self):
        self.assertTrue(self.session.begin(safe=True, base_state='DESARMADA modo=parado'))
        self.assertEqual(self.events, [(0, 0), 'arm'])

    def acknowledge(self):
        self.now += 0.125
        self.session.update(**self.feedback('ARMADA modo=parado seguridad=sin comandos'))
        self.assertEqual(self.session.state, BaseSessionState.VERIFYING_ZERO)
        self.now += 0.04
        self.session.update(**self.feedback('ARMADA modo=v/w seguridad=ok'))
        self.assertEqual(self.session.state, BaseSessionState.ARMED)

    def test_waits_for_new_armed_confirmation(self):
        self.assertFalse(self.session.begin(safe=False, base_state='DESARMADA modo=parado'))
        self.assertFalse(self.session.begin(safe=True, base_state='DESARMADA modo=libre'))
        self.begin()
        self.assertFalse(self.session.velocity(.1, 0, deadman=True, **self.feedback()))
        self.assertEqual(self.session.state, BaseSessionState.ARMING)
        self.acknowledge()
        self.assertTrue(self.session.velocity(.1, 0, deadman=True, **self.feedback()))
        self.assertEqual(self.events[-1], (.1, 0))

    def test_zero_requires_fresh_ok_before_movement(self):
        self.begin()
        self.now += 0.125
        self.session.update(**self.feedback('ARMADA modo=parado seguridad=sin comandos'))
        self.assertEqual(self.events, [(0, 0), 'arm', (0, 0)])
        self.assertFalse(self.session.velocity(.1, 0, deadman=True, **self.feedback()))
        self.now += 0.04
        self.session.update(**self.feedback('ARMADA modo=parado seguridad=sin comandos'))
        self.assertFalse(self.session.velocity(.1, 0, deadman=True,
            **self.feedback('ARMADA modo=parado seguridad=sin comandos')))
        self.session.update(**self.feedback())
        self.assertEqual(self.session.state, BaseSessionState.ARMED)

    def test_arming_timeout_ignores_late_confirmation(self):
        self.begin()
        self.now += 2.0
        self.session.update(**self.feedback())
        self.assertEqual(self.session.state, BaseSessionState.STOPPED)
        self.assertEqual(self.events, [(0, 0), 'arm', (0, 0), 'disarm'])

    def test_fault_release_and_timeout_latch_until_new_session(self):
        for cause in ('sensor', 'lease', 'firmware', 'release', 'velocity_timeout', 'invalid'):
            with self.subTest(cause=cause):
                self.setUp()
                self.begin()
                self.acknowledge()
                self.assertTrue(self.session.velocity(.1, 0, deadman=True, **self.feedback()))
                if cause == 'sensor':
                    self.session.update(**self.feedback(safe=False))
                elif cause == 'lease':
                    self.session.update(**self.feedback(session_alive=False))
                elif cause == 'firmware':
                    self.session.update(**self.feedback('DESARMADA modo=parado'))
                elif cause == 'release':
                    self.assertFalse(self.session.velocity(0, 0, deadman=False, **self.feedback()))
                elif cause == 'invalid':
                    self.assertFalse(self.session.velocity(float('nan'), 0, deadman=True, **self.feedback()))
                else:
                    self.now += .25
                    self.session.update(**self.feedback())
                self.assertEqual(self.events[-2:], [(0, 0), 'disarm'])
                self.session.update(**self.feedback())
                self.assertFalse(self.session.velocity(.1, 0, deadman=True, **self.feedback()))
                self.assertEqual(self.session.state, BaseSessionState.STOPPED)

    def test_directional_block_stops_before_nonzero_output(self):
        self.begin()
        self.acknowledge()
        self.assertFalse(self.session.velocity(.1, 0, deadman=True,
            **self.feedback('ARMADA modo=parado seguridad=ok no_avanza(frente_sin_eco)')))
        self.assertEqual(self.events, [(0, 0), 'arm', (0, 0), (0, 0), 'disarm'])
