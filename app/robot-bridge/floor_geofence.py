"""Protección geométrica para el ensayo aislado de avance recto en el piso."""

from dataclasses import dataclass
import math
import time

from geometry import intersects, validate_metric_polygon


@dataclass(frozen=True)
class FloorPose:
    x_m: float
    y_m: float
    yaw_rad: float
    frame_id: str
    anchor_id: str
    received_at: float
    position_error_m: float
    yaw_error_rad: float


def point_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    squared = dx * dx + dy * dy
    if not squared:
        return math.dist(point, a)
    fraction = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / squared
    fraction = min(1, max(0, fraction))
    return math.dist(point, (a[0] + fraction * dx, a[1] + fraction * dy))


class FloorGeofence:
    def __init__(self, vertices, *, frame_id, anchor_id, robot_radius_m, stop_reserve_m,
                 max_position_error_m, max_yaw_error_rad, max_pose_age_s, pose_reader, clock=time.monotonic):
        validate_metric_polygon(vertices)
        if not frame_id or frame_id in ('odom', 'base_link') or not anchor_id:
            raise ValueError('Se requiere un marco fijo de la zona y un origen identificado')
        bounds = (robot_radius_m, stop_reserve_m, max_position_error_m, max_yaw_error_rad, max_pose_age_s)
        if not all(math.isfinite(v) and v > 0 for v in bounds) or max_yaw_error_rad > math.pi:
            raise ValueError('Márgenes de seguridad inválidos')
        ring = tuple(map(tuple, vertices))
        self.edges = tuple(zip(ring, ring[1:] + ring[:1]))
        self.frame_id = frame_id
        self.anchor_id = anchor_id
        self.robot_radius_m = robot_radius_m
        self.stop_reserve_m = stop_reserve_m
        self.max_position_error_m = max_position_error_m
        self.max_yaw_error_rad = max_yaw_error_rad
        self.max_pose_age_s = max_pose_age_s
        self.pose_reader = pose_reader
        self.clock = clock

    def inside(self, point):
        x, y = point
        crossings = sum((a[1] > y) != (b[1] > y) and
                        x < a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
                        for a, b in self.edges)
        return crossings % 2 == 1

    def check(self, linear_m_s=0.0, duration_s=0.0):
        """Devuelve un motivo de bloqueo o None. La pose debe existir en el marco fijo."""
        try:
            pose = self.pose_reader()
        except Exception:
            return 'FLOOR_POSE_UNAVAILABLE'
        if not isinstance(pose, FloorPose):
            return 'FLOOR_POSE_UNAVAILABLE'
        if pose.frame_id != self.frame_id or pose.anchor_id != self.anchor_id:
            return 'FLOOR_REFERENCE_MISMATCH'
        values = (pose.x_m, pose.y_m, pose.yaw_rad, pose.received_at, pose.position_error_m, pose.yaw_error_rad,
                  linear_m_s, duration_s)
        if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
            return 'FLOOR_POSE_OR_COMMAND_INVALID'
        if not 0 <= self.clock() - pose.received_at <= self.max_pose_age_s:
            return 'FLOOR_POSE_STALE'
        if not (0 <= pose.position_error_m <= self.max_position_error_m
                and 0 <= pose.yaw_error_rad <= self.max_yaw_error_rad):
            return 'FLOOR_POSE_UNCERTAIN'
        if linear_m_s < 0 or duration_s < 0:
            return 'FLOOR_POSE_OR_COMMAND_INVALID'
        distance = linear_m_s * duration_s
        if not math.isfinite(distance):
            return 'FLOOR_POSE_OR_COMMAND_INVALID'
        start = pose.x_m, pose.y_m
        end = start[0] + distance * math.cos(pose.yaw_rad), start[1] + distance * math.sin(pose.yaw_rad)
        margin = (self.robot_radius_m + self.stop_reserve_m + pose.position_error_m
                  + 2 * distance * math.sin(pose.yaw_error_rad / 2))
        if not self.inside(start) or not self.inside(end):
            return 'FLOOR_OUTSIDE'
        for a, b in self.edges:
            if intersects(start, end, a, b):
                return 'FLOOR_PATH_CROSSES_BOUNDARY'
            if min(point_distance(start, a, b), point_distance(end, a, b),
                   point_distance(a, start, end), point_distance(b, start, end)) <= margin:
                return 'FLOOR_CLEARANCE_INSUFFICIENT'
        return None
