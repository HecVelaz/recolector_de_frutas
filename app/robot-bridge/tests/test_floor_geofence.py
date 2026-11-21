from dataclasses import replace
import unittest

from floor_geofence import FloorGeofence, FloorPose


class FloorGeofenceTest(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.pose = FloorPose(1.0, 1.0, 0.0, 'lab_map', 'mark-a', self.now, 0.02, 0.02)
        self.guard = self.make_guard([(0, 0), (2, 0), (2, 2), (0, 2)])

    def make_guard(self, vertices, frame_id='lab_map'):
        return FloorGeofence(vertices, frame_id=frame_id, anchor_id='mark-a',
            robot_radius_m=0.25, stop_reserve_m=0.05, max_position_error_m=0.08,
            max_yaw_error_rad=0.1, max_pose_age_s=0.2,
            pose_reader=lambda: self.pose, clock=lambda: self.now)

    def test_clearance_accounts_for_robot_pose_error_and_stop(self):
        self.assertIsNone(self.guard.check(0.04, 0.12))
        self.pose = replace(self.pose, x_m=1.677)
        self.assertIsNone(self.guard.check())
        self.assertEqual(self.guard.check(0.04, 0.12), 'FLOOR_CLEARANCE_INSUFFICIENT')
        self.pose = replace(self.pose, x_m=2.0)
        self.assertEqual(self.guard.check(), 'FLOOR_OUTSIDE')

    def test_rejects_missing_stale_wrong_reference_or_uncertain_pose(self):
        nominal = self.pose
        for pose, reason in (
            (None, 'FLOOR_POSE_UNAVAILABLE'),
            (replace(nominal, received_at=9), 'FLOOR_POSE_STALE'),
            (replace(nominal, received_at=11), 'FLOOR_POSE_STALE'),
            (replace(nominal, frame_id='odom'), 'FLOOR_REFERENCE_MISMATCH'),
            (replace(nominal, anchor_id='reset'), 'FLOOR_REFERENCE_MISMATCH'),
            (replace(nominal, position_error_m=0.09), 'FLOOR_POSE_UNCERTAIN'),
            (replace(nominal, yaw_error_rad=0.2), 'FLOOR_POSE_UNCERTAIN'),
            (replace(nominal, x_m=float('nan')), 'FLOOR_POSE_OR_COMMAND_INVALID'),
        ):
            with self.subTest(reason=reason):
                self.pose = pose
                self.assertEqual(self.guard.check(), reason)

    def test_blocks_crossing_a_concave_boundary_with_both_endpoints_inside(self):
        guard = self.make_guard([(0, 0), (4, 0), (4, 4), (3, 4), (3, 1), (1, 1), (1, 4), (0, 4)])
        self.pose = replace(self.pose, x_m=0.5, y_m=3)
        self.assertIsNone(guard.check())
        self.assertEqual(guard.check(0.5, 6), 'FLOOR_PATH_CROSSES_BOUNDARY')

    def test_cannot_treat_unanchored_odometry_as_a_lab_frame(self):
        with self.assertRaises(ValueError):
            self.make_guard([(0, 0), (2, 0), (2, 2), (0, 2)], frame_id='odom')
