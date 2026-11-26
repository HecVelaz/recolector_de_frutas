import asyncio
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from collection_mission import (GRASP_RAISE_MM, LEMON_STOP_MM, STOP_RADIUS_MM, REVERSE_M_S, CollectionMission, home_steps,
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

    async def test_with_depth_but_no_lemon_located_the_scan_is_empty_not_a_camera_failure(self):
        # 25/11, en el robot: el localizador no publica /limon/todos sin limones; a los 40 s cortaba toda la misión
        self.mission.deadline = self.mission.run_until = float('inf')
        self.stereo.target_frame.return_value = (None, None, [])
        self.stereo.snapshot.return_value = {'status': 'searching'}
        with patch('collection_mission.NO_LEMON_S', .1), patch('collection_mission.VISION_READY_S', 5.):
            self.assertIsNone(await self.mission.scan_frames('o', 0.))
        self.stereo.snapshot.return_value = {'status': 'waiting'}   # sin profundidad: sí son las cámaras
        with patch('collection_mission.VISION_READY_S', .2), self.assertRaisesRegex(RuntimeError, 'cámaras'):
            await self.mission.scan_frames('o', 0.)

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
            r = math.hypot(-575., 290.)   # a 64 cm: se acerca en su dirección hasta dejarlo a STOP_RADIUS_MM de J1
            self.assertAlmostEqual(expected[0], -575. * STOP_RADIUS_MM / r)
            self.assertAlmostEqual(expected[1], 290. * STOP_RADIUS_MM / r)
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
        high, low_far = (-575., 342., 300.), (-600., 300., 120.)   # ~69 cm (más cerca) y ~43 cm del piso
        lemon, seen = nearest_rough([[high, low_far]] * 3, grasp, None)
        self.assertEqual(seen, 2)
        self.assertEqual([round(v) for v in lemon[:2]], [-600, 300])

    async def test_a_high_lemon_is_planned_without_the_extra_raise(self):
        # 21/11: a ~64 cm del piso hay plan a la altura medida, no 2 cm más arriba
        self.navigation.planear.return_value = [('recto', 130.)]
        self.origin = make_lemon_origin((-575., 342., 272.), 1, self.odom)   # z ya con los +2 cm: 272 + 14
        with (self.planners(feasible=lambda target: target[2] < 280), patch.object(self.mission, 'drive_step', new=AsyncMock()),
              patch.object(self.mission, 'harvest', new=AsyncMock(return_value=1)),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])

    async def recolector_run(self, views, count=2, extra=(), around=False, stops=4, misses=0):
        """Modo Recolector: views = lo que ve la visión en cada medición, en orden (el escaneo primero; la última se
        repite). scan_frames(owner, 0.) solo espera pares nuevos: no consume una vista. Un limón agarrado deja de verse,
        salvo los primeros `misses` agarres (la pinza no lo arrancó)."""
        gone, miss = set(), [misses]
        events, planned = [], []
        grasp = Mock(AGRUPAR_MM=35., DISPERSION_MAX=10., VERIFICAR_MM=40., REPOSO=(3., 17., 4.), MIN_POSICIONES=2,
                     DESPLEGAR=(100., 46.7, 80.))
        grasp.k.Q1_LIM = (0., 118.)   # J1 > 118: en la canasta
        grasp.limon_de_cara.side_effect = lambda tf, face, n, spread: tuple(face)
        grasp.planear_agarre_tol.side_effect = lambda s, target, basket: (
            ([('servo', 'pz a')], []) if target[0] > -700 else (None, ['lejos']))
        views = list(views)

        async def measure(owner, seconds=8., enough=None):
            if seconds == 0.:
                return []
            events.append(('mide', paused[0]))
            frames = views.pop(0) if len(views) > 1 else views[0]
            frames = [[f for f in frame if (round(f[0]), round(f[1])) not in gone] for frame in frames]
            if enough is not None:   # corta apenas alcanza, como collect_frames
                frames = next((frames[:k] for k in range(1, len(frames) + 1) if enough(frames[:k])), frames)
                events.append(('imagenes', len(frames)))
            return frames

        arm = self.control.snapshot.return_value

        async def task(owner, original, steps):
            if steps[0][0] == 'desplegar' and len(steps) == 1:   # 25/11: desplegar para andar, sin agarre
                events.append(('despliega', paused[0]))
                arm['arm_state'] = 'q=100,46.7,80;e=3,3,3;c=111'
                return
            events.append(('agarra', paused[0]))
            planned.append(self.grasp_target)
            if miss[0]:
                miss[0] -= 1
            else:
                gone.add(self.grasp_target)
            arm['arm_state'] = 'q=130,46.7,80;e=3,3,3;c=111'   # suelta en la canasta

        paused = [False]

        def pause(value):
            paused[0] = value
            events.append(('pausa' if value else 'reanuda', value))
            return True

        for extra_patch in extra:   # patches propios de cada prueba (drive_step, ...)
            extra_patch.start()
            self.addCleanup(extra_patch.stop)
        original_plan = self.mission.grasp_plan

        async def grasp_plan(owner, original, s, lemon, basket):
            self.grasp_target = tuple(round(v) for v in lemon[:2])
            return await original_plan(owner, original, s, lemon, basket)

        with (patch.object(self.mission, 'planners', return_value=(self.navigation, grasp, None)),
              patch.object(self.mission, 'scan_frames', side_effect=measure),
              patch.object(self.mission, 'measure_frames', side_effect=measure),
              patch.object(self.mission, 'run_task', side_effect=task),
              patch.object(self.mission, 'grasp_plan', side_effect=grasp_plan),
              patch.object(self.mission, 'arm_to_rest', new=AsyncMock(return_value=True)),
              patch.object(self.mission, 'set_vision_paused', side_effect=pause),
              patch.object(self.mission, 'settle', new=AsyncMock()),
              patch.object(self.mission, 'start_recording', new=AsyncMock(return_value=None))):
            self.mission.start_scan('operator', count, 3., around, stops)
            await self.mission.task
        return events, planned

    @patch('collection_mission.VISION_ON_DEMAND', True)
    async def test_recolector_tries_every_scanned_lemon_without_moving_when_it_cannot_reposition(self):
        near, far_ok, unreachable = (-500., 150., 128.), (-560., 200., 140.), (-750., 300., 130.)
        beside = (-480., 40., 130.)   # a ~5° de J1: el firmware pediría J1 < 3°
        self.navigation.planear.return_value = [('giro', 20.), ('recto', -500.)]   # reubicarse: marcha atrás de más
        events, planned = await self.recolector_run([[[near, far_ok, unreachable, beside]] * 3], count=1)
        self.assertEqual(planned, [(-560, 200), (-500, 150)])   # primero el de la zona buena; sin reubicación, desde acá
        self.assertFalse(any(e == 'pausa' for e, _ in events))   # 23/11: la visión queda prendida
        for call in self.control.mission_velocity.call_args_list:   # la base no se mueve
            self.assertEqual(call.args[1:], (0., 0.))
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])
        self.assertIn('2 de 4 limón(es) del escaneo', self.mission.status['message'])   # count=1 no limita: todos
        self.assertIn('salteado', self.mission.status['message'])
        self.assertIn('sin plan', self.mission.status['message'])

    async def test_recolector_repositions_with_the_arm_in_the_basket_and_skips_a_lemon_lost_from_view(self):
        a, b, c = (-560., 200., 140.), (-480., 40., 130.), (-450., 300., 130.)   # a en la zona buena; b y c no
        self.navigation.planear.return_value = [('giro', 12.)]

        drive = AsyncMock()   # la odometría no cambia: lo guardado se mide en el mismo lugar
        views = [[[a, b, c]] * 3,   # escaneo
                 [[a]] * 3,         # al medir para a (b y c tapados)
                 [[]] * 3,          # para b: no se ve (se movió o cayó) -> se saltea
                 [[c]] * 3]         # para c: sí -> se agarra
        events, planned = await self.recolector_run(views, count=1, extra=(
            patch.object(self.mission, 'drive_step', new=drive),))
        self.assertEqual(planned, [(-560, 200), (-450, 300)], self.mission.status['message'])   # a y c; b no
        self.assertEqual(drive.call_count, 2)       # se reubicó para b y para c
        names = [e for e, _ in events]
        self.assertNotIn('despliega', names)   # 25/11: anda con el brazo en la canasta (en DESPLEGAR tapaba la cámara)
        self.assertIn(('imagenes', 2), events)      # cortó con 2 de 3 imágenes (MIN_POSICIONES 2 en la prueba)
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', self.mission.status['message'])
        self.assertIn('salteado: no se vio', self.mission.status['message'])
        self.assertNotIn('sin verlo', self.mission.status['message'])

    async def test_going_around_the_tree_lemons_beyond_the_trunk_are_skipped(self):
        # 25/11, usuario: en cada parada la pinza no pasa del tronco (tronco a 52 cm de J1 con la franja 20-30 cm)
        from collection_mission import TRUNK_STOP_MM
        near, beyond = (-560., 200., 140.), (-650., 250., 140.)
        self.navigation.planear.return_value = [('giro', 0.)]   # la vuelta al primer escaneo
        self.assertGreater(near[0], TRUNK_STOP_MM[0] - 100)
        with patch('collection_mission.estimate_trunk', return_value=(-600., 150.)):
            events, planned = await self.recolector_run([[[near, beyond]] * 3], count=1, around=True, stops=1,
                                                        extra=(patch.object(self.mission, 'drive_step', new=AsyncMock()),))
        self.assertEqual(planned, [(-560, 200)], self.mission.status['message'])
        self.assertIn('1 limón(es) del otro lado del tronco: salteados', self.mission.status['message'])

    async def test_recolector_first_puts_the_pot_in_the_lidar_band_without_stops(self):
        # 26/11, usuario: el Recolector mueve la base, sin paradas, y se ubica con el lidar respecto a la maceta
        snapshot = self.control.snapshot.return_value
        snapshot['sources'].append({'key': 'range_lidar_left', 'status': 'fresh', 'age_ms': 10,
                                    'value': {'kind': 'distance', 'meters': .40}})
        a = (-560., 200., 140.)
        drive = AsyncMock()
        events, planned = await self.recolector_run([[[a]] * 3], count=1, extra=(
            patch.object(self.mission, 'drive_step', new=drive),))
        got = [(c.args[1], round(c.args[2], 6)) for c in drive.await_args_list]
        self.assertEqual(got[:3], [('giro', 90.), ('recto', 70.), ('giro', -90.)], self.mission.status['message'])
        self.assertEqual(planned, [(-560, 200)], self.mission.status['message'])
        self.assertIn('lidar a 40 cm, corrido 7 cm', self.mission.status['message'])
        self.assertNotIn('parada', self.mission.status['message'].lower())

    async def test_going_around_the_tree_lemons_too_far_from_j1_are_skipped(self):
        # 26/11, usuario: en Rodear árbol solo lo que se alcanza de enfrente (uno a 95 cm de la cámara iba a buscarse)
        near, far = (-560., 200., 140.), (-560., 400., 140.)   # 59 y 69 cm de J1, los dos de este lado del tronco
        self.navigation.planear.return_value = [('giro', 0.)]
        with patch('collection_mission.estimate_trunk', return_value=(-900., 150.)):
            events, planned = await self.recolector_run([[[near, far]] * 3], count=1, around=True, stops=1,
                                                        extra=(patch.object(self.mission, 'drive_step', new=AsyncMock()),))
        self.assertEqual(planned, [(-560, 200)], self.mission.status['message'])
        self.assertIn('1 limón(es) a más de 63 cm de J1: salteados', self.mission.status['message'])

    async def test_after_each_pick_it_checks_the_lemon_left_the_tree_and_tries_once_more(self):
        # 25/11, usuario: "hecho" no aseguraba el limón en la pinza; se mide otra vez y, si sigue ahí, otro intento
        a = (-560., 200., 140.)
        events, planned = await self.recolector_run([[[a]] * 3], count=1, misses=1)
        self.assertEqual(planned, [(-560, 200)] * 2)
        message = self.mission.status['message']
        self.assertIn('1 de 1', message)
        self.assertIn('hecho (verificado, al 2.º intento)', message)
    async def test_a_lemon_still_on_the_tree_after_two_picks_fails_without_a_third(self):
        a = (-560., 200., 140.)
        events, planned = await self.recolector_run([[[a]] * 3], count=1, misses=2)
        self.assertEqual(len(planned), 2)
        self.assertIn('0 de 1', self.mission.status['message'])
        self.assertIn('sigue en el árbol después de 2 intentos', self.mission.status['message'])

    async def test_a_failed_pick_goes_on_with_the_next_lemon(self):
        # 25/11: con la pinza vacía, al reposo (no a la canasta); si el primer intento corta, prueba de nuevo y sigue
        from collection_mission import ArmRejected
        grasp = Mock(REPOSO=(3., 17., 4.))
        grasp.k.Q1_LIM = (0., 118.)
        self.control.snapshot.return_value['arm_state'] = 'q=17,18,18;e=4,4,4;c=111;fc=000;pz=500;mn=-1'
        rest = AsyncMock(side_effect=[ArmRejected('saldría de la franja'), True])
        with (patch.object(self.mission, 'grasp_plan', new=AsyncMock(return_value=([('ir', [(20., 17., 4.)])], []))),
              patch.object(self.mission, 'run_task', new=AsyncMock(side_effect=ArmRejected('sin cuentas'))),
              patch.object(self.mission, 'recover_to_basket', new=AsyncMock()) as basket,
              patch.object(self.mission, 'arm_to_rest', new=rest),
              patch.object(self.mission, 'settle', new=AsyncMock())):
            results = []
            self.assertEqual(await self.mission.pick_here('o', grasp, (-560., 200., 140.), results), 0)
        basket.assert_not_called()
        self.assertEqual(rest.await_count, 2)
        self.assertIn('falló', results[0][1])

    async def test_recolector_tries_a_lemon_once_more_after_an_arm_cut(self):
        a = (-560., 200., 140.)
        cuts = ['sin cuentas']
        original = self.mission.pick_here

        async def pick(owner, grasp, lemon, results):
            if cuts:
                results.append((lemon, 'falló: ' + cuts.pop()))
                return 0
            return await original(owner, grasp, lemon, results)

        events, planned = await self.recolector_run([[[a]] * 3], count=1, extra=(
            patch.object(self.mission, 'pick_here', side_effect=pick),))
        self.assertEqual(planned, [(-560, 200)], self.mission.status['message'])   # el segundo intento lo agarra
        self.assertIn('1 de 1', self.mission.status['message'])
        self.assertIn('se reintentó', self.mission.status['message'])

    @patch('collection_mission.ARC_AROUND_TREE', False)   # los saltos (el respaldo del arco)
    async def test_recolector_goes_around_the_tree_and_back_to_the_first_scan(self):
        # 25/11, usuario: 4 paradas antihorario; una sin limones pasa a la siguiente; al final, al primer escaneo
        a = (-560., 200., 140.)   # en la zona buena: se cosecha sin reubicarse
        self.navigation.SEP_TRONCO = 450.
        self.navigation.distancia_minima.return_value = 480.
        self.navigation.planear.return_value = [('giro', 45.)]
        drive = AsyncMock()
        events, planned = await self.recolector_run([[[a]] * 3, [[a]] * 3, [[]] * 3], count=1, around=True, extra=(
            patch.object(self.mission, 'drive_step', new=drive),))
        self.assertEqual(planned, [(-560, 200)], self.mission.status['message'])
        # en saltos de 45° alrededor del árbol, antihorario (la odometría simulada no cambia: cada salto se mide desde
        # el inicio); con las 4 completa la vuelta
        turns = [round(c.args[1]) for c in self.navigation.planear.call_args_list]
        self.assertEqual(turns, [45, 90, 45, 90, 135, 180, 45, 90, 135, 180, -135, -90, 0])
        self.assertEqual(drive.await_count, 13)
        message = self.mission.status['message']
        self.assertEqual(self.mission.status['state'], 'FINALIZADO', message)
        self.assertIn('1 de 1 limón(es) en 4 parada(s) alrededor del árbol', message)
        self.assertIn('parada 2: sin limones', message)

    async def test_going_around_it_waits_for_an_object_ahead_and_never_pushes_against_it(self):
        from collection_mission import SENSOR_AHEAD_MM, OBSTACLE_RADIUS_MM, Blocked
        self.mission.avoid = True
        self.mission.deadline = self.mission.run_until = float('inf')
        snapshot = self.control.snapshot.return_value
        snapshot['base_state'] = 'ARMADA modo=v/w seguridad=ok'
        snapshot['sources'].append({'key': 'range_front', 'status': 'fresh', 'age_ms': 10,
                                    'value': {'kind': 'distance', 'meters': .2}})
        with (patch('collection_mission.OBSTACLE_WAIT_S', .1), patch.object(self.mission, 'settle', new=AsyncMock())):
            with self.assertRaises(Blocked) as caught:
                await self.mission.drive_step('o', 'recto', 500.)
        self.assertTrue(all(c.args[1] == 0. for c in self.control.mission_velocity.call_args_list))   # quieto
        self.assertAlmostEqual(caught.exception.point[0], .2 + (SENSOR_AHEAD_MM + OBSTACLE_RADIUS_MM) / 1000)
        self.assertIn('esperando que se despeje', self.mission.events[0]['message'])

    async def test_at_each_stop_the_lidar_leaves_the_pot_between_30_and_36_cm(self):
        # 25/11, usuario: franja 20-30 cm (antes 40-44); 26/11: 30-36 (el ajuste fino, con 33). Corrige al medio con un
        # paso al costado, nunca marcha atrás
        self.mission.deadline = self.mission.run_until = float('inf')
        snapshot = self.control.snapshot.return_value
        lidar = {'key': 'range_lidar_left', 'status': 'fresh', 'age_ms': 10, 'value': None}
        snapshot['sources'].append(lidar)
        for meters, steps in ((.40, [('giro', 90.), ('recto', 70.), ('giro', -90.)]),
                              (.20, [('giro', -90.), ('recto', 130.), ('giro', 90.)]),
                              (.33, []), (.80, []), (None, [])):
            lidar['value'] = None if meters is None else {'kind': 'distance', 'meters': meters}
            drive = AsyncMock()
            with patch.object(self.mission, 'drive_step', new=drive):
                note = await self.mission.lidar_trim('o', '')
            got = [(c.args[1], round(c.args[2], 6)) for c in drive.await_args_list]
            self.assertEqual(got, steps, (meters, note))
            self.assertEqual(note is None, meters == .33, note)
            # 25/11, en el robot: leyendo sin mandar consignas, el control cortaba la recolección a los ~0,5 s
            self.assertGreaterEqual(self.control.mission_velocity.call_count, 5)
            self.control.mission_velocity.reset_mock()

    async def test_between_stops_it_goes_in_an_arc_around_the_trunk_and_stops_at_the_next(self):
        # 26/11, usuario: girar en círculo alrededor del árbol y parar igual en cada parada (90°)
        from collection_mission import TRUNK_STOP_MM, arm_to_world, world_to_arm
        pose = {'x_m': 0., 'y_m': 0., 'yaw_rad': 0.}
        trunk = arm_to_world((*TRUNK_STOP_MM, 0.), pose)[:2]
        dt = .05

        def snapshot():
            return {'sources': [{'key': 'odom', 'status': 'fresh', 'age_ms': 1, 'value': dict(pose)},
                                {'key': 'imu', 'status': 'fresh', 'age_ms': 1, 'value': {'gyro_yaw_rad': pose['yaw_rad']}}]}

        def velocity(owner, linear=0., angular=0.):   # la base: avanza y gira lo pedido (dt por consigna)
            pose['yaw_rad'] += angular * dt
            pose['x_m'] += linear * dt * math.cos(pose['yaw_rad'])
            pose['y_m'] += linear * dt * math.sin(pose['yaw_rad'])

        async def turn(owner, kind, value):
            pose['yaw_rad'] += math.radians(value)

        self.control.snapshot.side_effect = snapshot
        self.control.mission_velocity.side_effect = velocity
        self.mission.deadline = self.mission.run_until = float('inf')
        with (patch.object(self.mission, 'drive_step', side_effect=turn), patch.object(self.mission, 'settle', new=AsyncMock()),
              patch('collection_mission.asyncio.sleep', new=AsyncMock())):
            await self.mission.go_to_stop('o', self.navigation, trunk, math.pi / 2, TRUNK_STOP_MM, 'Parada 2')
        self.navigation.planear.assert_not_called()   # sin saltos
        self.assertAlmostEqual(math.degrees(pose['yaw_rad']), 90., delta=1.)
        here = world_to_arm((*trunk, 0.), pose)
        self.assertLess(math.dist(here[:2], TRUNK_STOP_MM), 30., here)   # el tronco otra vez donde va en la parada
        self.assertIn('arco de 90°', self.mission.status['message'])
        self.assertTrue(all(c.args[1] == .08 for c in self.control.mission_velocity.call_args_list if c.args[1]))

    @patch('collection_mission.ARC_AROUND_TREE', False)   # los saltos (el respaldo del arco)
    async def test_with_two_stops_it_comes_back_the_way_it_went_facing_forward(self):
        # 25/11, usuario: poco espacio, 2 paradas; vuelve por donde vino (horario), nunca en marcha atrás
        a = (-560., 200., 140.)
        self.navigation.planear.return_value = [('giro', 45.)]

        async def turn(owner, kind, value):   # cada salto simulado gira 45° (la odometría acompaña)
            self.odom['yaw_rad'] += math.radians(value)

        events, planned = await self.recolector_run([[[a]] * 3, [[a]] * 3, [[]] * 3], count=1, around=True, stops=2,
                                                    extra=(patch.object(self.mission, 'drive_step', side_effect=turn),))
        calls = self.navigation.planear.call_args_list
        self.assertEqual([round(c.args[1]) for c in calls], [45, 45, 135, -135])   # ida 90° y vuelta 90° (4 saltos)
        from collection_mission import ROTATION_CENTER_MM, TRUNK_STOP_MM
        start = calls[3].args[2]   # el último salto deja el tronco como en el primer escaneo
        self.assertEqual(calls[0].args[2], TRUNK_STOP_MM)
        mirrored = calls[2].args[2]   # salto intermedio de la vuelta: la misma parada girado 180° (tronco a la derecha)
        self.assertAlmostEqual(mirrored[0], 2 * ROTATION_CENTER_MM[0] - start[0])
        self.assertAlmostEqual(mirrored[1], 2 * ROTATION_CENTER_MM[1] - start[1])
        self.assertGreater(mirrored[0], 0)
        self.assertEqual(round(math.degrees(self.odom['yaw_rad'])), 180)   # (con giros simulados fijos de 45°)
        self.assertIn('en 2 parada(s) alrededor del árbol', self.mission.status['message'])

    def test_the_trunk_is_estimated_behind_the_lemons(self):
        from collection_mission import CANOPY_MM, estimate_trunk
        trunk = estimate_trunk([(-560., 200., 140.), (-600., 120., 150.)])
        centre = (-580., 160.)
        self.assertAlmostEqual(math.dist(trunk, centre), CANOPY_MM)
        self.assertGreater(math.hypot(*trunk), math.hypot(*centre))   # más lejos de J1 que los limones
        self.assertIsNone(estimate_trunk([(300., 400., 100.)]))       # a la derecha: no es el árbol
        self.assertIsNone(estimate_trunk([]))

    def test_lemon_positions_survive_moving_the_base(self):
        from collection_mission import arm_to_world, refresh_positions, world_to_arm
        start, moved = dict(self.odom), dict(self.odom, x_m=.1, yaw_rad=math.radians(20))
        lemon = (-540., 180., 120.)
        point = arm_to_world(lemon, start)
        self.assertEqual([round(v, 6) for v in world_to_arm(point, start)], list(lemon))
        seen_now = world_to_arm(point, moved)
        remaining = [point]
        nudged = (seen_now[0] + 30., seen_now[1], seen_now[2])   # medido 3 cm al costado: se corrige la guardada
        self.assertEqual(refresh_positions(remaining, [nudged], moved), [nudged])
        self.assertTrue(remaining[0][3])
        self.assertEqual(len(refresh_positions(remaining, [], moved)), 1)   # no se ve: queda la guardada
        self.assertFalse(remaining[0][3])
        # 25/11: dos guardados cerca de una sola medición: la toma el más cercano; el otro queda sin ver
        two = [arm_to_world((-540., 180., 120.), start), arm_to_world((-480., 180., 120.), start)]
        refresh_positions(two, [(-535., 180., 120.)], start)
        self.assertEqual([p[3] for p in two], [True, False])

    async def test_measurement_stops_as_soon_as_it_is_enough(self):
        from time import monotonic
        stamps = (monotonic() + k for k in range(1, 100))   # posteriores al arranque
        self.stereo.target_frame.side_effect = lambda: (next(stamps), 'camera', [{'x_m': .1, 'y_m': 0., 'z_m': .8}])
        frames = await self.mission.collect_frames(5., lambda: None, lambda f: len(f) >= 3)
        self.assertEqual(len(frames), 3)

    async def test_recolector_without_lemons_skips_the_harvest(self):
        events, planned = await self.recolector_run([[[]] * 3])
        self.assertEqual(planned, [])
        self.assertEqual([e for e, _ in events], ['mide'])
        self.assertIn('no se cosecha', self.mission.status['message'])

    @patch('collection_mission.VISION_ON_DEMAND', True)
    def test_vision_runs_only_on_demand_or_during_a_mission(self):
        calls = []
        self.mission.vision_demand_until = 0.
        with patch.object(self.mission, 'set_vision_paused', side_effect=lambda v: calls.append(v) or True), \
                patch('collection_mission.monotonic', side_effect=[0., 0., 1., 31., 31.]):
            self.mission.sync_vision()      # sin pedido: pausa
            self.mission.demand_vision()    # t=0: la app la pide -> reanuda
            self.mission.sync_vision()      # t=1: sigue pedida, no cambia
            self.mission.sync_vision()      # t=31: venció el pedido (30 s) -> se apaga
        self.assertEqual(calls, [True, False, True])

    async def test_a_lemon_too_high_says_so_instead_of_asking_to_move(self):
        # Limón a ~68 cm del piso (z 300): ninguna parada tiene plan; acercarse no sirve
        self.navigation.planear.return_value = [('recto', 80.)]
        self.origin = make_lemon_origin((-575., 342., 300.), 1, self.odom)
        with self.planners(feasible=lambda target: False):
            self.mission.start('operator', self.origin)
            await self.mission.task
        self.assertIn('~68 cm del piso', self.mission.status['message'])

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
        self.assertAlmostEqual(targets[1][0], second[0] * STOP_RADIUS_MM / r)   # el segundo, acercándose a STOP_RADIUS_MM
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

    def test_grasp_point_is_raised_grasp_raise_real_millimetres(self):
        from collection_mission import raised
        self.assertEqual(GRASP_RAISE_MM, 0.)   # 26/11: la altura la corrige el ajuste fino de punta.py
        self.assertAlmostEqual(raised((-550., 150., 100.))[2], 100. + GRASP_RAISE_MM / 1.43)

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
    failures: lista de textos de MV_ERROR para los próximos mv (uno por mv). angles: si se pasa, la lista de ángulos
    del estado simulado sigue a los mv que llegan y al joystick de J1."""

    def __init__(self, failures=(), angles=None):
        self.sent, self.failures, self.angles = [], list(failures), angles
        self.feedback, self.home_detail = (None, None), None

    def send(self, command):
        self.sent.append(command)
        now = monotonic()
        if self.angles is not None and command.startswith('jv -'):
            self.angles[0] -= 10.
        if command.startswith(('mv ', 'mvp ')):
            if self.failures:
                self.feedback, self.home_detail = (now, 'park_failed'), self.failures.pop(0)
            else:
                self.feedback, self.home_detail = (now, 'parked'), None
                if self.angles is not None:
                    self.angles[:] = [float(x) for x in command.split()[1:]]
        elif self.angles is not None and command.startswith('j '):
            joint, target = command.split()[1:]
            self.angles[int(joint) - 1] = float(target)
        elif re.match(r'^(pz|mn) (?!w )', command):
            self.feedback = (now, 'servo_ready')

    def home_feedback(self):
        return self.feedback


class GraspTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.control = Mock()
        self.angles = [3., 17., 4.]
        self.control.arm = FakeArm(angles=self.angles)   # 25/11: el estado sigue a los mv (salida de la canasta)
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
        # 25/11: J1 trabada (batería baja) se repite desde donde quedó; a la tercera vez corta
        self.control.arm = FakeArm(['sin cuentas del encoder', 'sin cuentas del encoder'])
        await self.mission.move('mision', (100., 46.7, 80.), passing=True)
        self.control.arm = FakeArm(['sin cuentas del encoder'] * 3)
        with self.assertRaises(ArmRejected):
            await self.mission.move('mision', (100., 46.7, 80.), passing=True)

    async def test_folded_with_j2_above_the_zone_lowers_j3_before_going_to_rest(self):
        # 25/11, en el robot: soltó con J2 en 53,9°; con J1 afuera de la canasta el firmware rechazaba todo mv
        self.angles[:] = [130., 53.85, 79.98]
        original = SimpleNamespace(REPOSO=(3., 17., 4.), SOLTAR_Q2_MIN_PY=42.)
        self.assertTrue(await self.mission.arm_to_rest('mision', original))
        sent = [c for c in self.control.arm.sent if not c.startswith('jv -')]
        self.assertEqual(sent, ['jv 0 0 0', 'j 3 55.0', 'mvp 100.00 46.70 50.00', 'mv 3.00 17.00 4.00'])
        # plegado dentro de la zona (lo normal): sin el j
        self.angles[:] = [130., 46.7, 80.]
        self.control.arm = FakeArm(angles=self.angles)
        await self.mission.arm_to_rest('mision', original)
        self.assertNotIn('j 3 55.0', self.control.arm.sent)

    async def test_leaving_the_basket_j1_goes_with_the_joystick_first(self):
        # 25/11: desde la canasta el mv cortaba "sin cuentas"; J1 sale con jv hasta el destino y el mv termina
        self.angles[:] = [130., 46.7, 80.]
        arm = FakeArm()
        sent = arm.send

        def send(command):
            sent(command)
            if command.startswith('jv -'):
                self.angles[0] -= 10.   # el joystick la mueve
        arm.send = send
        self.control.arm = arm
        await self.mission.move('mision', (100., 46.7, 80.), passing=True)
        jogs = [c for c in arm.sent if c.startswith('jv')]
        self.assertEqual(jogs[:3], ['jv -0.90 0 0'] * 3)
        self.assertEqual(jogs[-1], 'jv 0 0 0')
        self.assertEqual(arm.sent[-1], 'mvp 100.00 46.70 80.00')
        # sin canasta, como antes: solo el mv
        self.angles[:] = [60., 46.7, 80.]
        self.control.arm = FakeArm()
        await self.mission.move('mision', (30., 46.7, 80.))
        self.assertEqual(self.control.arm.sent, ['mv 30.00 46.70 80.00'])

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

    @unittest.skipUnless(HAS_NUMPY, 'numpy')
    async def test_harvest_without_verifying_in_the_recolector_measures_once_and_returns_to_rest(self):
        lemon = (-550., 100., 100.)
        original = SimpleNamespace(
            **vars(self.original), VERIFICAR_MM=60., MAX_INTENTOS=2, k=SimpleNamespace(Q1_LIM=(0, 115)),
            DESPLEGAR=(100., 46.7, 80.), REPOSO=(3., 17., 4.), SOLTAR_Q2_MIN_PY=42.)
        measures = [[lemon]]   # 23/11, Recolector: no vuelve a medir después de la canasta (una 2.ª medición fallaría)

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
        done = await self.mission.harvest('mision', original, None, 1, True, verify=False)
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
