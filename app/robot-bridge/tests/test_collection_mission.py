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
