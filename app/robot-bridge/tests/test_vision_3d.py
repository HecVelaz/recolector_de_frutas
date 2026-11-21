import math
import unittest

from vision_3d import StereoReadings, make_origin, with_displacement


class VisionTest(unittest.TestCase):
    def test_expired_positions_and_disparity(self):
        now = 0.
        readings = StereoReadings(clock=lambda: now)
        self.assertEqual(readings.snapshot()['status'], 'waiting')
        readings.disparity()
        self.assertEqual(readings.snapshot()['status'], 'searching')
        readings.positions('camera', [(0.1, 0.05, 0.65), (0, 0, float('nan')), (0, 0, -1)])
        self.assertEqual(readings.snapshot()['lemons'], [{'x_m': .1, 'y_m': .05, 'z_m': .65}])
        now += 2.3
        self.assertEqual(readings.snapshot()['status'], 'searching')
        now += .3
        self.assertEqual(readings.snapshot()['status'], 'waiting')

    def test_origin_uses_robot_center_and_tracks_signed_displacement(self):
        origin = make_origin((0, (-920, -5, 220), 0, 7), {'x_m': 3., 'y_m': 4., 'yaw_rad': math.pi / 2})
        self.assertAlmostEqual(origin['distance_m'], 1.)
        self.assertEqual(origin['at_marker'], {'x_m': 1., 'y_m': 0., 'yaw_deg': 90.})
        result = with_displacement(origin, {'x_m': 3., 'y_m': 5., 'yaw_rad': math.pi / 2})
        self.assertAlmostEqual(result['displacement']['x_m'], 1.)
        self.assertAlmostEqual(result['displacement']['y_m'], 0.)
