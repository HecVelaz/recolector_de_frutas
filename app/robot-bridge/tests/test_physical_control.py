import asyncio
import unittest
from unittest.mock import Mock, patch
from pydantic import ValidationError

from fastapi import HTTPException

from base_session import BaseSession, BaseSessionState
from physical_control import ArmAxes, DriveAxes, HOME_LEASE, LEASE, LINEAR_LIMIT, PARK_COMMAND, SESSION_LEASE, TURN_LIMIT, ManualInput, OpenManual, PhysicalControl


class PhysicalControlTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = 10
        self.base, self.arm = Mock(), Mock()
        self.base.exclusive.return_value = self.arm.exclusive.return_value = True
        self.evidence = {
            'source': 'ros2', 'upstream_available': True, 'battery_voltage': 11.2,
            'base_state': 'DESARMADA modo=parado seguridad=sin comandos rueda_izq=ninguna rueda_der=ninguna imu=ok',
            'arm_state': 'q=0,0,0;e=3,3,3;c=111;fc=000;pz=-1;mn=-1',
            'sources': [{'key': key, 'status': 'fresh', 'age_ms': 3, 'value': 0}
                        for key in ('base', 'arm', 'battery', 'odom', 'bumpers', 'imu', 'range_front')],
        }
        self.odom = next(source for source in self.evidence['sources'] if source['key'] == 'odom')
        self.odom['value'] = {'linear_m_s': 0., 'angular_rad_s': 0.}
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        self.control = PhysicalControl(lambda: self.evidence, self.base, self.arm, clock=lambda: self.now)

    def set_base_state(self, status):
        state = status + ' rueda_izq=ninguna rueda_der=ninguna imu=ok'
        self.evidence['base_state'] = state
        self.base.feedback.return_value = (state, self.now)

    async def test_manual_prepares_mobile_and_verifies_zero_before_enabling(self):
        output, request_arm = Mock(), Mock()
        self.base.new_session.return_value = BaseSession(
            output, request_arm=request_arm, request_disarm=self.base.request_disarm, clock=lambda: self.now)
        for initial in ('DESARMADA modo=libre seguridad=sin comandos', 'ARMADA modo=v/w seguridad=ok'):
            with self.subTest(initial=initial):
                self.set_base_state(initial)
                self.odom['value']['linear_m_s'] = 0.
                stages = iter(('old_odom', 'moving', 'stationary', 'armed', 'zero'))

                async def sample(_):
                    self.now += .1
                    stage = next(stages)
                    if stage in ('old_odom', 'moving', 'stationary'):
                        self.base.request_disarm.assert_called_once()
                        request_arm.assert_not_called()
                        self.set_base_state('DESARMADA modo=parado seguridad=sin comandos')
                        self.odom.update(age_ms=120 if stage == 'old_odom' else 3)
                        self.odom['value']['linear_m_s'] = .04 if stage == 'moving' else 0.
                    elif stage == 'armed':
                        request_arm.assert_called_once()
                        self.set_base_state('ARMADA modo=parado seguridad=sin comandos')
                    else:
                        self.assertEqual(output.stop.call_count, 2)
                        self.set_base_state('ARMADA modo=v/w seguridad=ok')

                with patch('physical_control.asyncio.sleep', side_effect=sample):
                    await self.control.open('owner', OpenManual(mode='base', operator_present=True, wheels_off_ground=True))
                self.assertEqual(self.control.trial.state, BaseSessionState.ARMED)
                output.send.assert_not_called()
                self.control.stop()
                output.reset_mock()
                request_arm.reset_mock()
                self.base.request_disarm.reset_mock()
                self.base.new_session.return_value = BaseSession(
                    output, request_arm=request_arm, request_disarm=self.base.request_disarm, clock=lambda: self.now)

    async def test_manual_refuses_an_alarm_and_a_stop_without_confirmation(self):
        body = OpenManual(mode='combined', operator_present=True, wheels_off_ground=True)
        self.set_base_state('DESARMADA modo=libre seguridad=EMERGENCIA (seta) SETA')
        with self.assertRaises(HTTPException) as alarm:
            await self.control.open('owner', body)
        self.assertIn('BASE_CRITICAL_FLAG', alarm.exception.detail)
        self.base.request_disarm.assert_not_called()
        self.arm.send.assert_not_called()

        self.set_base_state('ARMADA modo=v/w seguridad=ok')

        async def sample(_):
            self.now += .25
            self.set_base_state('ARMADA modo=v/w seguridad=ok')

        with patch('physical_control.asyncio.sleep', side_effect=sample):
            with self.assertRaisesRegex(HTTPException, 'no confirmó la detención'):
                await self.control.open('owner', body)
        self.base.request_disarm.assert_called_once()
        self.base.new_session.assert_not_called()
        self.assertIsNone(self.control.owner)

    async def test_arm_release_and_timeout(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        self.control.input('owner', ManualInput(motion='j2-'))
        self.arm.send.assert_called_with('jv 0.0000 -0.6000 0.0000')
        self.control.input('owner', ManualInput())
        self.arm.send.assert_called_with('jv 0 0 0')
        self.control.input('owner', ManualInput(servo='gripper_open'))
        self.arm.send.assert_called_with('pz a')
        self.now += LEASE + .01
        self.assertEqual(self.control.input('owner', ManualInput(motion='j2-')), ('paused', False))
        self.assertEqual(self.control.owner, 'owner')
        self.arm.send.assert_called_with('pz a')
        self.now += SESSION_LEASE
        with self.assertRaisesRegex(HTTPException, 'Se perdió el enlace de mando'):
            self.control.input('owner', ManualInput())

    async def test_arm_speed_percent_scales_joints_and_buttons(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        self.control.input('owner', ManualInput(motion='j1+', arm_speed_percent=100))
        self.arm.send.assert_called_with('jv 1.0000 0.0000 0.0000')
        self.control.input('owner', ManualInput(joints=ArmAxes(swivel=0, shoulder=-1, elbow=.5), arm_speed_percent=20))
        self.arm.send.assert_called_with('jv 0.0000 -0.2000 0.1000')

    async def test_base_reconnect_does_not_stop_arm_only_session(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        self.base.exclusive.return_value = False
        self.assertNotIn('Hay otro mando ROS activo o falta un controlador', self.control.blockers('arm'))
        self.assertIn('Hay otro mando ROS activo o falta un controlador', self.control.blockers('combined'))

    def test_servo_speed_commands(self):
        self.assertEqual(ManualInput(gripper_speed_dps=90).servo_command(), 'pz w 90')
        self.assertEqual(ManualInput(wrist_speed_dps=30).servo_command(), 'mn w 30')
        self.assertFalse(ManualInput(wrist_speed_dps=30).is_neutral())
        with self.assertRaises(HTTPException):
            ManualInput(gripper_speed_dps=90, wrist_degrees=10).servo_command()

    async def test_arm_braking_state_is_valid_only_while_settling(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        self.control.input('owner', ManualInput(motion='j2-'))
        self.evidence['arm_state'] = 'q=3,17,9;e=4,1,4;c=111;fc=000;pz=-1;mn=-1'   # frenando, medido 23/11
        self.assertNotIn('Brazo ocupado o en estado inválido', self.control.blockers('arm'))
        self.control.input('owner', ManualInput())
        self.now += .6
        self.assertNotIn('Brazo ocupado o en estado inválido', self.control.blockers('arm'))
        self.now += .5
        self.assertIn('Brazo ocupado o en estado inválido', self.control.blockers('arm'))

    async def test_brief_input_gap_stops_both_axes_and_keeps_the_session(self):
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        await self.control.open('owner', OpenManual(mode='combined', operator_present=True, wheels_off_ground=True))
        drive = DriveAxes(forward=1, turn=0)
        self.set_base_state('ARMADA modo=v/w seguridad=ok')
        for sequence in range(1, 1201):
            if sequence % 100 == 0:
                await asyncio.sleep(0)
            self.now += .08
            self.set_base_state('ARMADA modo=v/w seguridad=ok')
            self.control.input('owner', ManualInput(sequence=sequence, drive=drive, arm_motion='j1+'))

        self.now += LEASE + .01
        self.set_base_state('ARMADA modo=v/w seguridad=ok')
        self.control.tick()
        trial.send_zero.assert_called_once()
        self.arm.send.assert_called_with('jv 0 0 0')
        trial.stop.assert_not_called()
        trial.velocity.reset_mock()
        self.arm.send.reset_mock()
        self.assertEqual(self.control.input('owner', ManualInput(sequence=1202, drive=drive)), ('paused', False))
        self.assertEqual(self.control.input('owner', ManualInput(sequence=1203)), ('active', False))
        self.assertEqual(self.control.input('owner', ManualInput(sequence=1201, drive=drive)), ('ignored', False))
        self.assertEqual(self.control.input('owner', ManualInput(drive=drive)), ('ignored', False))
        trial.velocity.assert_not_called()
        self.arm.send.assert_not_called()
        self.control.input('owner', ManualInput(sequence=1204, drive=drive))
        self.assertEqual(trial.velocity.call_args.args, (LINEAR_LIMIT, 0.))

    async def test_telemetry_failure_revokes_control_with_the_specific_reason(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        self.set_base_state('DESARMADA modo=parado seguridad=EMERGENCIA (seta) SETA')
        self.control.tick()
        with self.assertRaises(HTTPException) as failure:
            self.control.input('owner', ManualInput())
        self.assertIn('BASE_CRITICAL_FLAG', failure.exception.detail)
        self.assertIsNone(self.control.owner)

    async def test_manual_floor_does_not_require_wheels_elevated_but_blocks_direct_pwm(self):
        self.evidence['arm_state'] = self.evidence['arm_state'].replace('c=111', 'c=000')
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        await self.control.open('owner', OpenManual(mode='base', operator_present=True))
        self.set_base_state('ARMADA modo=v/w seguridad=ok')
        self.control.input('owner', ManualInput(motion='forward'))
        self.assertEqual(trial.velocity.call_args.args, (.25, 0.))
        with self.assertRaises(HTTPException):
            self.control.input('owner', ManualInput(motion='forward', duty_percent=20))
        self.arm.send.assert_not_called()
        self.base.send_duty.assert_not_called()
        self.set_base_state('DESARMADA modo=parado seguridad=sin comandos')
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        with self.assertRaises(HTTPException):
            self.control.input('owner', ManualInput(arm_motion='j1+'))
        self.arm.send.assert_called_with('jv 0 0 0')

    async def test_homing_can_start_without_zero_and_stops_on_release(self):
        self.evidence['arm_state'] = self.evidence['arm_state'].replace('c=111', 'c=000')
        await self.control.open('owner', OpenManual(mode='homing', operator_present=True))
        self.arm.send.assert_not_called()
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.send.assert_called_once_with('h')
        with self.assertRaises(HTTPException):
            self.control.input('owner', ManualInput())
        self.arm.send.assert_called_with('s')
        self.assertTrue(self.control.home_unverified)

    async def test_homing_requires_a_new_success_reply_and_confirmed_joints(self):
        await self.control.open('owner', OpenManual(mode='homing', operator_present=True))
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.home_feedback.return_value = (self.now - 1, 'completed')
        self.assertEqual(self.control.input('owner', ManualInput(motion='home')), ('active', False))
        self.arm.home_feedback.return_value = (self.now + .01, 'completed')
        self.assertEqual(self.control.input('owner', ManualInput(motion='home')), ('active', False))
        self.arm.send.assert_called_with(PARK_COMMAND)
        self.assertIsNotNone(self.control.park_started)
        self.arm.home_feedback.return_value = (self.now + .02, 'parked')
        self.assertEqual(self.control.input('owner', ManualInput(motion='home')), ('completed', False))
        self.assertEqual([call.args[0] for call in self.arm.send.call_args_list], ['h', PARK_COMMAND])
        self.assertFalse(self.control.home_unverified)
        await self.control.open('different-owner', OpenManual(mode='arm', operator_present=True))

    async def test_homing_outside_the_band_raises_j2_and_retries_once(self):
        # 20/11: el brazo frenado quedó en J2 2,2° y J3 2,9° con el cero conocido; el firmware rechaza "h"
        self.evidence['arm_state'] = 'q=1.13,2.23,2.91;e=4,4,4;c=111;fc=000;pz=500;mn=1500'
        self.arm.home_error = self.arm.home_detail = ('Homing: J2 y J3 fuera de la franja (2.05° afuera): '
                                                      'volver adentro con "j" antes.')
        await self.control.open('owner', OpenManual(mode='homing', operator_present=True))
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.home_feedback.return_value = (self.now + .01, 'failed')
        self.now += .05
        self.assertEqual(self.control.input('owner', ManualInput(motion='home')), ('active', False))
        self.arm.send.assert_called_with('j 2 6.0')
        self.now += .05
        self.evidence['arm_state'] = 'q=1.13,4.10,2.91;e=4,1,4;c=111;fc=000;pz=500;mn=1500'   # subiendo
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.send.assert_called_with('j 2 6.0')
        self.now += .05
        self.evidence['arm_state'] = 'q=1.13,5.95,2.91;e=4,3,4;c=111;fc=000;pz=500;mn=1500'   # llegó
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.send.assert_called_with('h')
        self.now += .05
        self.control.input('owner', ManualInput(motion='home'))   # la respuesta vieja ("failed") no cuenta
        self.assertIsNotNone(self.control.owner)
        self.evidence['arm_state'] = 'q=3,6,3;e=3,3,3;c=111;fc=000;pz=500;mn=1500'
        self.arm.home_feedback.return_value = (self.now + .01, 'completed')
        self.now += .05
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.send.assert_called_with(PARK_COMMAND)
        self.arm.home_feedback.return_value = (self.now + .01, 'parked')
        self.now += .05
        self.assertEqual(self.control.input('owner', ManualInput(motion='home')), ('completed', False))
        self.assertEqual([c.args[0] for c in self.arm.send.call_args_list], ['h', 'j 2 6.0', 'h', PARK_COMMAND])

    async def test_homing_retry_stops_if_the_firmware_rejects_it_again(self):
        self.evidence['arm_state'] = 'q=1.13,2.23,2.91;e=4,4,4;c=111;fc=000;pz=500;mn=1500'
        self.arm.home_error = self.arm.home_detail = 'Homing: J2 y J3 fuera de la franja (2.05° afuera)'
        await self.control.open('owner', OpenManual(mode='homing', operator_present=True))
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.home_feedback.return_value = (self.now + .01, 'failed')
        self.now += .05
        self.control.input('owner', ManualInput(motion='home'))
        self.arm.home_detail = 'Fuera de rango: J2 puede ir de +4.4° a +5.0°'
        self.arm.home_feedback.return_value = (self.now + .01, 'park_failed')
        self.now += .05
        with self.assertRaisesRegex(HTTPException, 'Fuera de rango'):
            self.control.input('owner', ManualInput(motion='home'))
        self.arm.send.assert_called_with('s')
        self.assertIsNone(self.control.owner)

    async def test_homing_heartbeat_loss_interrupts_firmware(self):
        await self.control.open('owner', OpenManual(mode='homing', operator_present=True))
        self.control.input('owner', ManualInput(motion='home'))
        self.now += LEASE + .01   # un aviso atrasado (Pi cargada) no corta el homing
        self.control.tick()
        self.assertEqual('owner', self.control.owner)
        self.now += HOME_LEASE
        self.control.tick()
        self.arm.send.assert_called_with('s')
        self.assertIsNone(self.control.owner)

    async def test_base_release_and_competing_publisher(self):
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        await self.control.open('owner', OpenManual(mode='base', operator_present=True, wheels_off_ground=True))
        self.evidence['base_state'] = self.evidence['base_state'].replace(
            'DESARMADA modo=parado seguridad=sin comandos', 'ARMADA modo=parado seguridad=ok')
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        self.control.input('owner', ManualInput(motion='backward', speed_percent=50))
        self.assertEqual(trial.velocity.call_args.args, (-LINEAR_LIMIT / 2, 0.))
        self.control.input('owner', ManualInput(motion='left', speed_percent=100))
        self.assertEqual(trial.velocity.call_args.args, (0., TURN_LIMIT))
        self.control.input('owner', ManualInput())
        trial.send_zero.assert_called_once()
        self.base.exclusive.return_value = False
        trial.update.side_effect = lambda **feedback: setattr(trial, 'state', BaseSessionState.STOPPED)
        self.control.tick()
        self.assertIsNone(self.control.owner)
        trial.stop.assert_called_once()

    async def test_combined_duty_and_gripper_with_unreferenced_joints(self):
        self.evidence['arm_state'] = self.evidence['arm_state'].replace('c=111', 'c=000')
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        await self.control.open('owner', OpenManual(mode='combined', operator_present=True, wheels_off_ground=True))
        self.evidence['base_state'] = self.evidence['base_state'].replace(
            'DESARMADA modo=parado seguridad=sin comandos', 'ARMADA modo=parado seguridad=ok')
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        trial.velocity.side_effect = lambda *args, **kw: (kw['apply_output'](), True)[1]
        self.assertEqual(self.control.input('owner', ManualInput(motion='left', servo='gripper_open',
                                                               duty_percent=12)), ('active', True))
        self.base.send_duty.assert_called_once_with(-12, 12)
        self.arm.send.assert_called_once_with('pz a')
        self.control.input('owner', ManualInput())
        self.base.stop_duty.assert_called_once()
        trial.send_zero.assert_called_once()

        trial.velocity.side_effect = lambda *args, **kw: (kw['apply_output'](), True)[1]
        self.control.input('owner', ManualInput(drive=DriveAxes(forward=1, turn=0), duty_percent=25))
        self.base.send_duty.assert_called_with(25, 25)
        with self.assertRaises(ValidationError):
            ManualInput(duty_percent=26)

    async def test_combined_base_and_referenced_joint_keep_independent_motion(self):
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        await self.control.open('owner', OpenManual(mode='combined', operator_present=True, wheels_off_ground=True))
        self.evidence['base_state'] = self.evidence['base_state'].replace(
            'DESARMADA modo=parado seguridad=sin comandos', 'ARMADA modo=parado seguridad=ok')
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        self.control.input('owner', ManualInput(motion='forward', arm_motion='j1+'))
        self.assertEqual(trial.velocity.call_args.args, (LINEAR_LIMIT, 0.))
        self.arm.send.assert_called_with('jv 0.6000 0.0000 0.0000')
        self.control.input('owner', ManualInput(motion='forward'))
        self.arm.send.assert_called_with('jv 0 0 0')
        trial.send_zero.assert_not_called()

    async def test_joysticks_mix_axes_and_release_independently(self):
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        await self.control.open('owner', OpenManual(mode='combined', operator_present=True, wheels_off_ground=True))
        self.evidence['base_state'] = self.evidence['base_state'].replace(
            'DESARMADA modo=parado seguridad=sin comandos', 'ARMADA modo=parado seguridad=ok')
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        axes = DriveAxes(forward=1, turn=-1)
        reach = ArmAxes(swivel=0, elbow=.8, shoulder=-.5)
        self.control.input('owner', ManualInput(drive=axes, joints=reach))
        self.assertEqual(trial.velocity.call_args.args, (LINEAR_LIMIT / 2, -TURN_LIMIT / 2))
        self.arm.send.assert_called_with('jv 0.0000 -0.3000 0.4800')
        self.control.input('owner', ManualInput(joints=reach))
        trial.send_zero.assert_called_once()
        self.arm.send.assert_called_with('jv 0.0000 -0.3000 0.4800')
        self.control.input('owner', ManualInput())
        self.arm.send.assert_called_with('jv 0 0 0')

    async def test_servo_positions_respect_calibrated_endpoints(self):
        await self.control.open('owner', OpenManual(mode='arm', operator_present=True))
        for body, command in (
            (ManualInput(gripper_open_percent=0), 'pz 1250'),
            (ManualInput(gripper_open_percent=40), 'pz 950'),
            (ManualInput(gripper_open_percent=100), 'pz 500'),
            (ManualInput(wrist_degrees=-90), 'mn 2150'),
            (ManualInput(wrist_degrees=0), 'mn 1500'),
            (ManualInput(wrist_degrees=90), 'mn 860'),
        ):
            self.assertEqual(('active', True), self.control.input('owner', body))
            self.arm.send.assert_called_with(command)
        with self.assertRaises(ValidationError):
            ManualInput(wrist_degrees=91)

    async def test_zero_speed_cancels_the_motion_even_with_deflected_joystick(self):
        trial = self.base.new_session.return_value
        trial.state = BaseSessionState.ARMED
        self.base.feedback.return_value = (self.evidence['base_state'], self.now)
        await self.control.open('owner', OpenManual(mode='base', operator_present=True, wheels_off_ground=True))
        self.evidence['base_state'] = self.evidence['base_state'].replace(
            'DESARMADA modo=parado seguridad=sin comandos', 'ARMADA modo=parado seguridad=ok')
        drive = DriveAxes(forward=1, turn=0)
        self.control.input('owner', ManualInput(drive=drive))
        self.control.input('owner', ManualInput(drive=drive, speed_percent=0))
        trial.velocity.assert_called_once()
        trial.send_zero.assert_called_once()
