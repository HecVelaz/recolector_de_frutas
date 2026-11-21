"""Lecturas del localizador estéreo y cero local vinculado al ArUco original."""

from math import atan2, cos, degrees, hypot, isfinite, radians, sin
from threading import Lock
from time import monotonic


class StereoReadings:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.lock = Lock()
        self.disparity_at = self.points_at = None
        self.frame_id = None
        self.points = []

    def disparity(self):
        with self.lock:
            self.disparity_at = self.clock()

    def positions(self, frame_id, positions):
        points = [{'x_m': x, 'y_m': y, 'z_m': z} for x, y, z in positions
                  if all(map(isfinite, (x, y, z))) and z > 0][:20]
        with self.lock:
            self.frame_id, self.points_at, self.points = frame_id, self.clock(), points

    def snapshot(self):
        with self.lock:
            now = self.clock()
            depth = self.disparity_at is not None and now - self.disparity_at <= 2.5
            fresh = depth and self.points_at is not None and now - self.points_at <= 2.
            points = self.points if fresh else []
            return {'status': 'located' if points else 'searching' if depth else 'waiting',
                    'frame_id': self.frame_id if fresh else None, 'lemons': list(points)}

    def target_sample(self):
        with self.lock:
            point = self.points[0] if self.points and self.frame_id == 'camera' else None
            return self.points_at, point


# Centro de giro medido respecto de J1 en ir_a_parada.py [m].
BASE_CENTER = (.080, -.005)


def make_origin(mark, odom):
    marker_id, position_mm, normal_deg, views = mark
    x, y, z = (float(i) / 1000 for i in position_mm)
    normal = radians(float(normal_deg))
    dx, dy = BASE_CENTER[0] - x, BASE_CENTER[1] - y
    # En el plano, +X de la marca sale de su cara impresa y +Y gira 90°.
    x_at_mark = cos(normal) * dx + sin(normal) * dy
    y_at_mark = -sin(normal) * dx + cos(normal) * dy
    yaw_at_mark = atan2(sin(radians(90) - normal), cos(radians(90) - normal))
    return {'marker_id': int(marker_id), 'samples': int(views), 'distance_m': hypot(dx, dy),
            'at_marker': {'x_m': x_at_mark, 'y_m': y_at_mark, 'yaw_deg': degrees(yaw_at_mark)},
            'marker_in_arm': {'x_m': x, 'y_m': y, 'z_m': z, 'normal_deg': float(normal_deg)},
            'odom_origin': {key: odom[key] for key in ('x_m', 'y_m', 'yaw_rad')}}


def with_displacement(origin, odom):
    if origin is None:
        return None
    result = dict(origin, displacement=None)
    if odom is not None:
        start = origin['odom_origin']
        dx, dy = odom['x_m'] - start['x_m'], odom['y_m'] - start['y_m']
        heading = start['yaw_rad']
        turn = odom['yaw_rad'] - heading
        result['displacement'] = {'x_m': cos(heading) * dx + sin(heading) * dy,
                                  'y_m': -sin(heading) * dx + cos(heading) * dy,
                                  'yaw_deg': degrees(atan2(sin(turn), cos(turn)))}
    return result
