import asyncio
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from collection_mission import (GRASP_RAISE_MM, LEMON_STOP_MM, REVERSE_M_S, CollectionMission, home_steps,
                                make_lemon_origin, stopped_near)


class CollectionMissionTest(unittest.IsolatedAsyncioTestCase):
    """21/11: cero relativo al limón más cercano; acercarse, cosechar y volver al cero desandando el camino."""

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
        self.odom = {'x_m': 0., 'y_m': 0., 'yaw_rad': 0., 'linear_m_s': 0., 'angular_rad_s': 0.}
        self.origin = make_lemon_origin((-575., 290., 128.), 1, self.odom)
        self.control.snapshot.return_value = {
            'arm_state': 'q=3,17,4;e=3,3,3;c=111',
            'sources': [{'key': 'odom', 'status': 'fresh', 'age_ms': 10, 'value': self.odom}],
        }
        self.navigation = Mock(MAX_RECTO=1500)
        self.navigation.texto.side_effect = lambda steps: str(steps)

    def planners(self, feasible=lambda target: True):
        grasp = Mock(REPOSO=(3., 17., 4.))
        grasp.planear_agarre_tol.side_effect = lambda s, target, basket: (
            ([('servo', 'pz a')], []) if feasible(target) else (None, ['lejos']))
        self.grasp = grasp
        return patch.object(self.mission, 'planners', return_value=(self.navigation, grasp, None))

    async def test_requires_a_lemon_origin_a_referenced_arm_and_no_motion_since(self):
        with self.assertRaisesRegex(HTTPException, 'cero'):
            self.mission.start('operator', None)
        with self.assertRaisesRegex(HTTPException, 'cero'):
            self.mission.start('operator', {'marker_id': 0, 'odom_origin': dict(self.odom)})   # cero ArUco viejo
        self.control.arm_ready.return_value = False
        with self.assertRaisesRegex(HTTPException, 'homing'):
            self.mission.start('operator', self.origin)
        self.control.arm_ready.return_value = True
        self.odom['x_m'] = .1
        with self.assertRaisesRegex(HTTPException, 'se movió desde el cero'):
            self.mission.start('operator', self.origin)
        self.control.open.assert_not_called()

    def test_origin_keeps_the_nearest_lemon_and_the_odometry(self):
        origin = make_lemon_origin((-575.4, 290., 128.), 3, dict(self.odom, x_m=.5, yaw_rad=.1))
        self.assertEqual(origin['kind'], 'lemon')
        self.assertEqual(origin['lemon_in_arm'], {'x_mm': -575.4, 'y_mm': 290., 'z_mm': 128.})
        self.assertEqual(origin['odom_origin'], {'x_m': .5, 'y_m': 0., 'yaw_rad': .1})
        self.assertAlmostEqual(origin['distance_m'], math.hypot(.5754, .29))

    async def test_measure_origin_picks_the_lemon_closest_to_j1(self):
        grasp = Mock(AGRUPAR_MM=35., MIN_POSICIONES=3, DISPERSION_MAX=10.)
        grasp.limon_de_cara.side_effect = lambda tf, face, n, spread: tuple(face)
        frames = [(float(k), 'camera', [{'x_m': -.7, 'y_m': .3, 'z_m': .2}, {'x_m': -.5, 'y_m': .2, 'z_m': .1}])
                  for k in range(1, 30)]
        self.stereo.target_frame.side_effect = frames + [frames[-1]] * 200
        with (patch.object(self.mission, 'planners', return_value=(None, grasp, None)),
              patch('collection_mission.ORIGIN_SECONDS', .3), patch('collection_mission.monotonic',
                                                                    side_effect=[0.] + [k * .01 for k in range(500)])):
            lemon, seen = await self.mission.measure_origin(lambda: True)
            with self.assertRaisesRegex(ValueError, 'quieto'):
                await self.mission.measure_origin(lambda: False)
        self.assertEqual(seen, 2)
        self.assertEqual([round(v) for v in lemon], [-500, 200, round(100 + GRASP_RAISE_MM / 1.43)])   # 2 cm más arriba

    async def test_measure_origin_accepts_two_rough_views(self):
        # 21/11: un limón lejos (~95 cm) da 2 lecturas con ~20 mm de diferencia: alcanza para el cero
        grasp = Mock(AGRUPAR_MM=35., MIN_POSICIONES=3, DISPERSION_MAX=10.)
        grasp.limon_de_cara.side_effect = lambda tf, face, n, spread: tuple(face)
        frames = [(1., 'camera', [{'x_m': -.7, 'y_m': .3, 'z_m': .2}]), (2., 'camera', [{'x_m': -.7, 'y_m': .3, 'z_m': .22}])]
        self.stereo.target_frame.side_effect = frames + [frames[-1]] * 200
        with (patch.object(self.mission, 'planners', return_value=(None, grasp, None)),
              patch('collection_mission.ORIGIN_SECONDS', .3), patch('collection_mission.monotonic',
                                                                    side_effect=[0.] + [k * .01 for k in range(500)])):
            lemon, seen = await self.mission.measure_origin(lambda: True)
        self.assertEqual(seen, 1)
        self.assertEqual(round(lemon[0]), -700)

    async def test_plan_rejects_reverse_before_enabling_the_robot(self):
        self.navigation.planear.return_value = [('recto', -100.)]
        with self.planners():
            self.assertTrue(self.mission.start('operator', self.origin)['active'])
            await self.mission.task
        self.assertEqual(self.mission.status['state'], 'RECUPERACION')
        self.assertEqual(self.navigation.planear.call_count, 3)   # su dirección, la de 8° adelante y la fija: todas retroceden
        self.control.open.assert_not_called()
        self.assertEqual(len(list((Path(self.temp.name) / 'missions').glob('*.json'))), 1)

    async def test_approaches_harvests_one_lemon_and_returns_to_zero_retracing_the_path(self):
        steps = [('giro', 10.), ('recto', 142.), ('giro', -10.)]
        self.navigation.planear.return_value = steps
        driven = []

        async def drive(owner, kind, value):
            driven.append((kind, value))

        async def harvest(owner, original, tf, count, to_basket, expected):
            self.assertIsNotNone(self.mission.zone)   # el brazo solo actúa con la zona de agarre fijada
            r = math.hypot(-575., 290.)   # a 64 cm: se acerca en su dirección hasta dejarlo a 53,5 cm de J1
            self.assertAlmostEqual(expected[0], -575. * 535. / r)
            self.assertAlmostEqual(expected[1], 290. * 535. / r)
            self.assertEqual(expected[2], 128.)
            return 1

        with (self.planners(), patch.object(self.mission, 'drive_step', side_effect=drive),
              patch.object(self.mission, 'harvest', side_effect=harvest),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.assertEqual(driven, steps)   # la odometría simulada no se mueve: ya está en el cero
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])
        self.assertIn('volvió al cero', self.mission.status['message'])
        self.assertIsNone(self.mission.zone)

    async def search_run(self, sightings):
        """Cero sin limón (21/11): la misión gira a los rumbos de búsqueda; sightings = lo que ve en cada uno."""
        driven = []

        async def drive(owner, kind, value):
            self.assertTrue(self.control.open.await_count)   # solo gira con el mando de la base abierto
            driven.append((kind, value))

        with (self.planners(), patch.object(self.mission, 'drive_step', side_effect=drive),
              patch.object(self.mission, 'harvest', new=AsyncMock(return_value=1)),
              patch.object(self.mission, 'measure_frames', new=AsyncMock(return_value=[])),
              patch('collection_mission.nearest_rough', side_effect=sightings),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', make_lemon_origin(None, 0, self.odom))
            await self.mission.task
        return driven

    async def test_without_a_lemon_in_the_zero_it_turns_to_find_one(self):
        driven = await self.search_run([(None, 0), ((-500., 150., 128.), 1)])   # lo ve a 25° a la izquierda
        self.assertEqual(driven, [('giro', 15.), ('giro', 10.)])   # a 52 cm: se cosecha sin acercarse
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])

    async def test_search_without_lemons_goes_back_to_the_zero_heading(self):
        driven = await self.search_run([(None, 0)] * 4)
        self.assertEqual([value for _, value in driven], [15., 10., -40., -10., 25.])
        self.assertEqual(self.mission.status['state'], 'RECUPERACION')
        self.assertIn('No encontré limones girando ±25°', self.mission.status['message'])

    def test_the_zero_prefers_a_lemon_at_a_reachable_height(self):
        from collection_mission import nearest_rough
        grasp = Mock(AGRUPAR_MM=35.)
        grasp.limon_de_cara.side_effect = lambda tf, face, n, spread: tuple(face)
        high, low_far = (-575., 342., 250.), (-600., 300., 120.)   # ~64 cm (más cerca) y ~43 cm del piso
        lemon, seen = nearest_rough([[high, low_far]] * 3, grasp, None)
        self.assertEqual(seen, 2)
        self.assertEqual([round(v) for v in lemon[:2]], [-600, 300])

    async def test_a_lemon_too_high_says_so_instead_of_asking_to_move(self):
        # 21/11: limón a ~63 cm del piso (z 272): ninguna parada tiene plan; acercarse no sirve
        self.navigation.planear.return_value = [('recto', 80.)]
        self.origin = make_lemon_origin((-575., 342., 272.), 1, self.odom)
        with self.planners(feasible=lambda target: False):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.assertIn('~64 cm del piso', self.mission.status['message'])

    async def test_a_lemon_already_in_reach_is_picked_without_moving_and_its_zero_is_used(self):
        driven, expectations = [], []

        async def drive(owner, kind, value):
            driven.append((kind, value))

        async def harvest(owner, original, tf, count, to_basket, expected):
            expectations.append(expected)
            return 1

        self.origin = make_lemon_origin((-500., 150., 128.), 1, self.odom)   # a 52 cm de J1: ya está para cosechar
        with (self.planners(), patch.object(self.mission, 'drive_step', side_effect=drive),
              patch.object(self.mission, 'harvest', side_effect=harvest),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.navigation.planear.assert_not_called()
        self.assertEqual(driven, [])
        self.assertEqual(expectations, [(-500., 150., 128.)])   # el limón del cero, donde está
        self.assertTrue(self.origin['used'])
        with self.assertRaisesRegex(HTTPException, 'ya se cosechó'):
            self.mission.start('operator', self.origin)

    async def test_two_lemons_are_harvested_one_after_the_other(self):
        # Pedido del usuario (21/11): cosechado el primero, medir desde ahí, acercarse al siguiente y cosecharlo
        self.origin = make_lemon_origin((-500., 150., 128.), 2, self.odom)
        second = (-700., 300., 140.)   # a 76 cm: hace falta acercarse
        self.navigation.planear.return_value = [('recto', 80.)]
        driven, targets = [], []

        async def drive(owner, kind, value):
            driven.append((kind, value))

        async def harvest(owner, original, tf, count, to_basket, expected):
            self.assertEqual(count, 1)
            targets.append(expected)
            return 1

        with (self.planners(), patch.object(self.mission, 'drive_step', side_effect=drive),
              patch.object(self.mission, 'harvest', side_effect=harvest),
              patch.object(self.mission, 'measure_lemons', new=AsyncMock(return_value=[second])),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin, lemons=2)
            await self.mission.task
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])
        self.assertIn('2 de 2 en la canasta', self.mission.status['message'])
        self.assertEqual(targets[0], (-500., 150., 128.))   # el primero sin moverse
        r = math.hypot(*second[:2])
        self.assertAlmostEqual(targets[1][0], second[0] * 535. / r)   # el segundo, acercándose a 53,5 cm
        self.assertEqual(driven, [('recto', 80.)])

    async def test_a_next_lemon_without_plan_ends_normally_and_goes_home(self):
        self.origin = make_lemon_origin((-520., 150., 128.), 2, self.odom)
        calls = []

        async def harvest(owner, original, tf, count, to_basket, expected):
            calls.append(expected)
            if len(calls) == 2:
                raise RuntimeError('Ningún limón tiene plan de agarre')
            return 1

        home = AsyncMock()
        with (self.planners(), patch.object(self.mission, 'drive_step', new=AsyncMock()),
              patch.object(self.mission, 'harvest', side_effect=harvest),
              patch.object(self.mission, 'measure_lemons', new=AsyncMock(return_value=[(-525., 140., 40.)])),
              patch.object(self.mission, 'return_home', new=home),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin, lemons=2)
            await self.mission.task
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])
        self.assertIn('1 de 2 en la canasta', self.mission.status['message'])
        home.assert_awaited_once()

    async def test_reverse_is_slow_and_forward_keeps_its_speed(self):
        self.mission.deadline = self.mission.run_until = float('inf')
        self.mission.settle = AsyncMock()
        sample = dict(self.odom)
        self.control.snapshot.side_effect = lambda: {'sources': [{'key': 'odom', 'status': 'fresh', 'age_ms': 1,
                                                                  'value': dict(sample)}]}
        speeds = []

        def velocity(owner, linear, angular):
            speeds.append(linear)
            sample['x_m'] += .05

        self.control.mission_velocity.side_effect = velocity
        await self.mission.drive_step('mision', 'recto', -200.)
        self.assertTrue(all(-REVERSE_M_S <= v < 0 for v in speeds))
        speeds.clear()
        sample['x_m'] = 0.
        await self.mission.drive_step('mision', 'recto', 300.)
        self.assertEqual(speeds[0], .10)

    async def test_a_blocked_base_explains_the_obstacle_ahead(self):
        self.mission.deadline = self.mission.run_until = float('inf')
        self.control.mission_velocity.side_effect = HTTPException(409, 'La base rechazó el movimiento')
        self.control.snapshot.return_value = {
            'base_state': 'ARMADA modo=v/w seguridad=ok no_avanza imu=ok',
            'sources': [{'key': 'range_front', 'status': 'fresh', 'age_ms': 30,
                         'value': {'kind': 'distance', 'meters': .175}}]}
        with self.assertRaisesRegex(RuntimeError, 'Obstáculo adelante a 18 cm'):
            self.mission.cycle('mision', .1)
        self.control.snapshot.return_value = {'base_state': 'DESARMADA modo=parado seguridad=SETA', 'sources': []}
        with self.assertRaisesRegex(RuntimeError, 'seguridad .SETA.'):
            self.mission.cycle('mision', .1)

    async def test_at_the_stop_only_the_expected_lemon_counts_not_the_foliage_in_front(self):
        # 21/11: ya en la parada el estéreo alternó el mismo limón a 77 cm y un punto del follaje a 42 cm
        grasp = Mock(AGRUPAR_MM=35., MIN_POSICIONES=3, DISPERSION_MAX=10.)
        grasp.limon_de_cara.side_effect = lambda tf, face, n, spread: tuple(face)
        real, phantom = (-548., 152., 130.), (-250., 60., 120.)
        frames = [[real] if k % 2 else [phantom] for k in range(8)]   # 4 y 4: ninguno llega al 30 % de 8 + ruido
        self.mission.measure_frames = AsyncMock(return_value=frames)
        expected = (LEMON_STOP_MM[0], LEMON_STOP_MM[1], 128.)
        found = await self.mission.measure_lemons('mision', grasp, None, near=expected)
        self.assertEqual([tuple(round(v) for v in lemon) for lemon in found],
                         [(-548, 152, round(130 + GRASP_RAISE_MM / 1.43))])   # el real, 2 cm más arriba
        # Sin ninguno donde se esperaba (21/11): lo medido ahí; el plan de agarre descarta lo que el brazo no alcanza
        self.mission.measure_frames = AsyncMock(return_value=[[phantom]] * 8)
        found = await self.mission.measure_lemons('mision', grasp, None, near=expected)
        self.assertEqual([round(v) for v in found[0][:2]], [-250, 60])
        self.assertIn('se cosecha según la medición de acá', self.mission.status['message'])

    def test_going_home_retraces_an_approach_from_the_odometry(self):
        # Acercamiento: girar 58° a la izquierda, avanzar 8 cm, girar 58° a la derecha (21/11)
        yaw = math.radians(58)
        arrived = dict(self.odom, x_m=.08 * math.cos(yaw), y_m=.08 * math.sin(yaw), yaw_rad=0.)
        steps = home_steps(self.origin, arrived)
        self.assertEqual([kind for kind, _ in steps], ['giro', 'recto', 'giro'])
        self.assertAlmostEqual(steps[0][1], 58.)
        self.assertAlmostEqual(steps[1][1], -80.)
        self.assertAlmostEqual(steps[2][1], -58.)
        self.assertEqual(home_steps(self.origin, dict(self.odom, yaw_rad=math.radians(.5))), [])
        self.assertEqual(home_steps(self.origin, dict(self.odom, yaw_rad=math.radians(-12))), [('giro', 12.)])

    async def test_a_failed_harvest_still_brings_the_arm_to_rest_and_the_base_home(self):
        self.navigation.planear.return_value = [('recto', 100.)]

        async def open_robot(owner, body, *, autonomous):
            self.control.owner = owner

        self.control.open.side_effect = open_robot

        async def harvest(*args):
            raise RuntimeError('MV_ERROR sin cuentas')

        home = AsyncMock()
        with (self.planners(), patch.object(self.mission, 'drive_step', new=AsyncMock()),
              patch.object(self.mission, 'harvest', side_effect=harvest),
              patch.object(self.mission, 'return_home', new=home),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin)
            await self.mission.task
        home.assert_awaited_once()
        self.assertEqual(self.mission.status['state'], 'RECUPERACION')
        self.assertIn('volvió al reposo y el Móvil al cero', self.mission.status['message'])

    async def test_return_requires_a_zero_and_a_referenced_arm(self):
        with self.assertRaisesRegex(HTTPException, 'cero'):
            self.mission.start_return('operator', None)
        self.control.arm_ready.return_value = False
        with self.assertRaisesRegex(HTTPException, 'homing'):
            self.mission.start_return('operator', self.origin)

    def test_grasp_point_is_raised_two_real_centimetres(self):
        from collection_mission import raised
        self.assertEqual(GRASP_RAISE_MM, 20.)
        self.assertAlmostEqual(raised((-550., 150., 100.))[2], 100. + 20. / 1.43)

    def test_arm_zone_requires_a_stationary_base_near_its_arrival(self):
        arrival = dict(self.odom, x_m=.2)
        self.assertTrue(stopped_near(arrival, dict(arrival, x_m=.23)))
        self.assertFalse(stopped_near(arrival, dict(arrival, x_m=.25)))
        self.assertFalse(stopped_near(arrival, dict(arrival, linear_m_s=.02)))
        self.assertFalse(stopped_near(arrival, dict(arrival, yaw_rad=math.radians(6))))
        self.assertFalse(stopped_near(arrival, None))

    async def test_stop_releases_owned_control_during_collection(self):
        self.navigation.planear.return_value = []

        async def open_robot(owner, body, *, autonomous):
            self.assertTrue(autonomous)
            self.control.owner = owner

        self.control.open.side_effect = open_robot
        started = asyncio.Event()

        async def settle(*args):
            started.set()
            await asyncio.sleep(5)

        with (self.planners(), patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None)),
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

    async def test_into_the_basket_only_j1_turns_when_the_arm_is_already_folded(self):
        # 21/11: J3 en 79,96 y J2 en 46,76; el mv a (130, 46,7, 80) cortaba J3 por "sin cuentas"
        self.angles[:] = [99.92, 46.76, 79.96]
        await self.mission.move('mision', (130., 46.7, 80.), passing=True)
        self.assertEqual(self.control.arm.sent, ['mvp 130.00 46.76 79.96'])
        self.angles[:] = [99.92, 46.76, 70.]   # sin plegar: el destino queda como está (el firmware lo rechaza)
        self.control.arm = FakeArm()
        await self.mission.move('mision', (130., 46.7, 80.), passing=True)
        self.assertEqual(self.control.arm.sent, ['mvp 130.00 46.70 80.00'])

    async def test_a_joint_stuck_near_its_target_is_left_there_once(self):
        self.angles[:] = [60., 46.79, 78.37]
        self.control.arm = FakeArm(['sin cuentas del encoder (¿suelto o trabada?)'])
        await self.mission.move('mision', (100., 46.7, 80.), passing=True)
        self.assertEqual(self.control.arm.sent, ['mvp 100.00 46.70 80.00', 'mvp 100.00 46.79 78.37'])
        self.control.arm = FakeArm(['sin cuentas del encoder', 'sin cuentas del encoder'])
        with self.assertRaises(ArmRejected):   # una sola vez
            await self.mission.move('mision', (100., 46.7, 80.), passing=True)

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


class PlannerProcessTest(unittest.IsolatedAsyncioTestCase):
    """21/11: los planificadores corren en otro proceso para no acaparar el intérprete del puente."""

    @unittest.skipUnless(HAS_NUMPY and (PUNTA_DIR / 'punta.py').is_file(), 'falta punta.py de pruebas-esp32')
    async def test_real_planners_run_in_their_own_process(self):
        tools = PUNTA_DIR.parent.parent / '27-aruco-arbol/tools'
        mission = CollectionMission(Mock(), Mock(), tempfile.mkdtemp(), tools)
        self.addCleanup(mission.close)
        mission.deadline = float('inf')
        sys.path.insert(0, str(PUNTA_DIR))
        self.addCleanup(sys.path.remove, str(PUNTA_DIR))
        punta = importlib.import_module('punta')
        await asyncio.wrap_future(mission.warm())
        plan, reasons = await mission.plan(None, punta, 'planear_agarre_tol', punta.REPOSO, punta.TAREA_A, True)
        self.assertIsNotNone(plan, reasons)
        local, _ = punta.planear_agarre_tol(punta.REPOSO, punta.TAREA_A, True)
        self.assertEqual(plan, local)
        self.assertIsNotNone(await mission.plan(None, punta, 'basket_path', (40., 30., 30.)))
        rest, _ = await mission.plan(None, punta, 'rest_plan', (40., 30., 30.))
        self.assertEqual(tuple(rest[-1]), tuple(punta.REPOSO))
