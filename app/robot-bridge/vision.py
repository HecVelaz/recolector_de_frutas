"""Último JPEG recibido por cámara. Independiente de ROS y de las órdenes."""

import threading
import time

CAMERAS = {
    'left': '/left/image_raw/compressed',
    'right': '/right/image_raw/compressed',
    'detections': '/yolo/left/image_annotated',
}
MAX_JPEG_BYTES = 1_048_576


class CameraFrames:
    def __init__(self, *, clock=time.monotonic, stale_after=1.5):
        self.clock = clock
        self.stale_after = stale_after
        self.lock = threading.Lock()
        self.frames = {}

    def put(self, key, payload):
        if key not in CAMERAS:
            raise KeyError(key)
        jpeg = None
        if 4 < len(payload) <= MAX_JPEG_BYTES:
            content = bytes(payload)
            if content.startswith(b'\xff\xd8') and content.endswith(b'\xff\xd9'):
                jpeg = content
        with self.lock:
            self.frames[key] = (self.clock(), jpeg)

    def latest(self, key):
        with self.lock:
            item = self.frames.get(key)
            if item is None or self.clock() - item[0] > self.stale_after:
                return None
            return item[1]
