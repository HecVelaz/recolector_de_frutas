import asyncio
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from collection_mission import CollectionMission, stopped_in_zone


class CollectionMissionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.control = Mock()
        self.control.owner = None
        self.control.arm_ready.return_value = True
        self.control.open = AsyncMock()
        self.stereo = Mock()
        self.stereo.snapshot.return_value = {'status': 'located'}
        self.mission = CollectionMission(self.control, self.stereo, self.temp.name, self.temp.name)
        self.odom = {'x_m': 0., 'y_m': 0., 'yaw_rad': 0.}
        self.origin = {'marker_id': 0, 'odom_origin': dict(self.odom),
                       'marker_in_arm': {'x_m': -1., 'y_m': 0., 'z_m': 0., 'normal_deg': 0.}}
        self.control.snapshot.return_value = {
            'arm_state': 'q=3,17,4;e=3,3,3;c=111',
            'sources': [{'key': 'odom', 'status': 'fresh', 'age_ms': 10, 'value': self.odom}],
        }

    async def test_requires_a_current_origin_and_a_referenced_arm(self):
        with self.assertRaisesRegex(HTTPException, 'ArUco'):
            self.mission.start('operator', None)
        self.control.arm_ready.return_value = False
        with self.assertRaisesRegex(HTTPException, 'homing'):
            self.mission.start('operator', self.origin)
        self.control.open.assert_not_called()

    async def test_retry_from_outside_the_work_zone_is_rejected(self):
        self.odom.update(x_m=.4, linear_m_s=0., angular_rad_s=0.)
        navigation = Mock()
        navigation.tronco_desde.return_value = (-700., 150.)
        with patch.object(self.mission, 'load_planners', return_value=(navigation, Mock())):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.assertIn('fuera de la parada', self.mission.status['message'])
        self.control.open.assert_not_called()

    def test_actuator_requires_stationary_odometry_inside_local_work_zone(self):
        parked = dict(self.odom, x_m=.2, linear_m_s=0., angular_rad_s=0.)
        self.assertTrue(stopped_in_zone(self.origin, (-700., 350.), parked))
        self.assertFalse(stopped_in_zone(self.origin, (-400., 350.), parked))
        self.assertFalse(stopped_in_zone(self.origin, (-700., 350.), dict(parked, linear_m_s=.02)))
        turned = dict(self.odom, yaw_rad=math.pi / 2, linear_m_s=0., angular_rad_s=0.)
        self.assertTrue(stopped_in_zone(self.origin, (-75., -785.), turned))

    async def test_plan_rejects_reverse_before_enabling_the_robot(self):
        navigation = Mock(MAX_RECTO=1500)
        navigation.planear.return_value = [('recto', -100.)]
        with patch.object(self.mission, 'load_planners', return_value=(navigation, Mock())):
            self.assertTrue(self.mission.start('operator', self.origin)['active'])
            await self.mission.task
        self.assertEqual(self.mission.status['state'], 'RECUPERACION')
        self.control.open.assert_not_called()
        self.assertEqual(len(list((Path(self.temp.name) / 'missions').glob('*.json'))), 1)

    async def test_stop_releases_owned_control_during_collection(self):
        navigation = Mock(MAX_RECTO=1500)
        navigation.planear.return_value = []
        navigation.texto.return_value = 'El Móvil ya está en la parada'

        async def open_robot(owner, body, *, autonomous):
            self.assertTrue(autonomous)
            self.control.owner = owner

        self.control.open.side_effect = open_robot
        started = asyncio.Event()

        async def settle(*args):
            started.set()
            await asyncio.sleep(5)

        with (patch.object(self.mission, 'load_planners', return_value=(navigation, Mock())),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None)),
              patch.object(self.mission, 'settle', side_effect=settle)):
            self.mission.start('operator', self.origin)
            await asyncio.wait_for(started.wait(), 2)
            await self.mission.stop('otro-cliente')
            self.assertTrue(self.mission.active)
            await self.mission.stop('operator')
        self.control.stop.assert_called_once()
        self.assertEqual(self.mission.status['state'], 'INACTIVO')


# ---------------------------------------------------------------- agarre con punta.py (20/11, Héctor + Claude Code)
import importlib
import os
import re
import sys
from time import monotonic
from types import SimpleNamespace

from collection_mission import ArmRejected, group_lemons

try:
    import numpy  # noqa: F401  (en la Pi viene del sistema)
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

PUNTA_DIR = Path(os.environ.get('ARTURITO_PUNTA_DIR',
                                Path.home() / 'Documentos/pruebas-esp32/20-brazo-coordinado/tools'))
COMMAND = re.compile(r'^(mvp?) (-?\d+\.\d\d) (-?\d+\.\d\d) (-?\d+\.\d\d)$')


class FakeArm:
    """Responde como el firmware 20 por /brazo/respuesta: LLEGO/PASO a mv/mvp, SERVO_LLEGO a pz/mn.
    failures: lista de textos de MV_ERROR para los próximos mv (uno por mv)."""

    def __init__(self, failures=()):
        self.sent, self.failures = [], list(failures)
        self.feedback, self.home_detail = (None, None), None

    def send(self, command):
        self.sent.append(command)
        now = monotonic()
        if command.startswith(('mv ', 'mvp ')):
            if self.failures:
                self.feedback, self.home_detail = (now, 'park_failed'), self.failures.pop(0)
            else:
                self.feedback, self.home_detail = (now, 'parked'), None
        elif re.match(r'^(pz|mn) (?!w )', command):
            self.feedback = (now, 'servo_ready')

    def home_feedback(self):
        return self.feedback


class GraspTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.control = Mock()
        self.control.arm = FakeArm()
        self.angles = [3., 17., 4.]
        self.control.snapshot.side_effect = lambda: {'arm_state': 'q={},{},{};e=3,3,3;c=111'.format(*self.angles),
                                                     'sources': []}
        self.mission = CollectionMission(self.control, Mock(), self.temp.name, self.temp.name)
        self.mission.deadline = self.mission.run_until = monotonic() + 600
        self.mission.settle = AsyncMock()
        self.original = SimpleNamespace(
            CON_CARGA=('entrar de frente', 'tirar'), DE_PASO={'tirar': (True, True), 'ir frente al limón': (True, False)},
            VEL_CARGA='vel 0.5 4 0.5', VEL_NORMAL='vel 1 4 0.5')

    async def test_task_follows_correr_tarea(self):
        steps = [('cmd', 'pz w 0'), ('servo', 'pz a'), ('ir frente al limón', [(10, 20, 30), (11, 21, 31)]),
                 ('entrar de frente', [(12, 22, 32)]), ('servo', 'pz 1200'), ('tirar', [(13, 23, 33)])]
        await self.mission.run_task('mision', self.original, steps)
        self.assertEqual(self.control.arm.sent, [
            'pz w 0', 'pz a', 'mvp 10.00 20.00 30.00', 'mv 11.00 21.00 31.00',
            'vel 0.5 4 0.5', 'mv 12.00 22.00 32.00', 'vel 1 4 0.5', 'pz 1200',
            'vel 0.5 4 0.5', 'mvp 13.00 23.00 33.00', 'vel 1 4 0.5'])

    async def test_retries_only_lag_cuts_and_restores_speed(self):
        self.control.arm = FakeArm(['no quedan firmes', 'no sigue la trayectoria (más de 10° de error, de paso)'])
        await self.mission.run_task('mision', self.original, [('tirar', [(1, 2, 3)])])
        self.assertEqual(self.control.arm.sent.count('mvp 1.00 2.00 3.00'), 3)
        self.control.arm = FakeArm(['Fuera de la franja'])
        with self.assertRaises(ArmRejected):
            await self.mission.run_task('mision', self.original, [('tirar', [(1, 2, 3)])])
        self.assertEqual(self.control.arm.sent, ['vel 0.5 4 0.5', 'mvp 1.00 2.00 3.00', 'vel 1 4 0.5'])

    def test_arm_link_reads_pass_points_and_safety_rejections(self):
        from physical_control import RosArmLink
        from threading import Lock
        link = object.__new__(RosArmLink)
        link._lock, link._home_feedback = Lock(), (None, None)
        link._read_reply(SimpleNamespace(data='PASO,1234,3.000,17.000,4.000'))
        self.assertEqual(link.home_feedback()[1], 'parked')
        link._read_reply(SimpleNamespace(data='J1 pasada 118° solo con el brazo plegado'))
        self.assertEqual(link.home_feedback()[1], 'park_failed')

    @unittest.skipUnless(HAS_NUMPY, 'numpy')
    def test_groups_lemons_like_punta(self):
        frames = [[(100, 0, 500), (300, 0, 600)] for _ in range(9)] + [[(102, 1, 501)], [(900, 0, 900)]]
        groups = group_lemons(frames, 35., 3)
        self.assertEqual([n for _, n, _ in groups], [10, 9])
        self.assertLess(abs(groups[0][0][0] - 100), 2)

    @unittest.skipUnless(HAS_NUMPY, 'numpy')
    async def test_harvest_confirms_the_lemon_left_and_returns_to_rest(self):
        lemon = (-550., 100., 100.)
        original = SimpleNamespace(
            **vars(self.original), VERIFICAR_MM=60., MAX_INTENTOS=2, k=SimpleNamespace(Q1_LIM=(0, 115)),
            DESPLEGAR=(100., 46.7, 80.), REPOSO=(3., 17., 4.), SOLTAR_Q2_MIN_PY=42.)
        measures = [[lemon], []]   # antes de agarrar lo ve; después, desde la canasta, ya no

        async def measure(*args):
            return measures.pop(0)

        def plan(s, target, to_basket):
            self.assertTrue(to_basket)
            return [('a la canasta', [(130., 46.7, 80.)]), ('servo', 'pz a')], []

        original.planear_agarre_tol = plan
        self.mission.measure_lemons = measure
        sent = self.control.arm.sent
        arm = self.control.arm

        def send(command):   # al llegar a la canasta, la telemetría muestra el brazo plegado
            FakeArm.send(arm, command)
            if command.startswith('mv 130.00'):
                self.angles[:] = [130., 46.7, 80.]

        arm.send = send
        done = await self.mission.harvest('mision', original, None, 1, True)
        self.assertEqual(done, 1)
        self.assertEqual(sent[-3:], ['mvp 100.00 46.70 80.00', 'mvp 100.00 46.70 50.00', 'mv 3.00 17.00 4.00'])

    @unittest.skipUnless(HAS_NUMPY and (PUNTA_DIR / 'punta.py').is_file(), 'falta punta.py de pruebas-esp32')
    async def test_real_punta_plan_reaches_the_firmware_as_valid_commands(self):
        """Con el punta.py actual: el plan de agarre a la canasta sale como mv/mvp bien formados, vel y servos."""
        sys.path.insert(0, str(PUNTA_DIR))
        self.addCleanup(sys.path.remove, str(PUNTA_DIR))
        punta = importlib.import_module('punta')
        plan, reasons = punta.planear_agarre_tol(punta.REPOSO, punta.TAREA_A, True)
        self.assertIsNotNone(plan, reasons)
        await self.mission.run_task('mision', punta, plan)
        sent = self.control.arm.sent
        for command in sent:
            self.assertTrue(COMMAND.match(command) or command in (punta.VEL_CARGA, punta.VEL_NORMAL)
                            or re.match(r'^(pz|mn) (w )?-?\w+$', command), command)
        self.assertIn('mvp', {c.split()[0] for c in sent})
        self.assertEqual(sent[-1], 'pz a')   # soltó en la canasta
