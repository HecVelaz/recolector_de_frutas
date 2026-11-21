"""Último JPEG por vista de cámara y dibujo de los limones. Independiente de las órdenes.

Vistas (20/11): izquierda = la imagen anotada por YOLO; central = la imagen normal (izquierda rectificada, la que
usa el estéreo y sobre la que corre YOLO, con sus cajas de /yolo/detecciones); derecha = la imagen rectificada derecha. En las tres se marcan los limones de /limon/todos
(metros, marco óptico `camera` de la izquierda rectificada) proyectados con la matriz P de cada cámara y su distancia.
"""

import threading
import time

CAMERAS = {
    'left': '/yolo/left/image_annotated',
    'center': '/left/image_rect',
    'right': '/right/image_rect',
}
MAX_JPEG_BYTES = 1_048_576
LEMON_RADIUS_M = .025          # limón de juguete de 5 cm (punta.RADIO_LIMON)
MARK_COLOR = (0, 255, 255)     # BGR: amarillo
JPEG_QUALITY = 70


class CameraFrames:
    """Último JPEG de cada vista. Las vistas se arman solo mientras alguien las pide (21/11): convertir y comprimir las
    tres todo el tiempo le quitaba ~media CPU de la Pi al detector y a la disparidad."""

    def __init__(self, *, clock=time.monotonic, stale_after=1.5, wanted_for=3.):
        self.clock = clock
        self.stale_after = stale_after
        self.wanted_for = wanted_for
        self.lock = threading.Lock()
        self.frames = {}
        self.requested = {}

    def wanted(self, key):
        """True si la vista se pidió en los últimos `wanted_for` s (si no, no vale la pena armarla)."""
        with self.lock:
            return self.clock() - self.requested.get(key, -float('inf')) <= self.wanted_for

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
            self.requested[key] = self.clock()
            item = self.frames.get(key)
            if item is None or self.clock() - item[0] > self.stale_after:
                return None
            return item[1]


def project(point, p):
    """(u, v, radio) en píxeles de un punto {x_m, y_m, z_m} con la matriz P (12 valores, fila por fila) de una cámara
    rectificada: u = (fx·X + Tx)/Z + cx, v = fy·Y/Z + cy. None si queda detrás de la cámara."""
    z = point['z_m']
    if not z > 0:
        return None
    fx, cx, tx, fy, cy = p[0], p[2], p[3], p[5], p[6]
    return (fx * point['x_m'] + tx) / z + cx, fy * point['y_m'] / z + cy, fx * LEMON_RADIUS_M / z


def draw_lemons(cv2, image, points, p):
    """Marca cada limón (círculo del tamaño del limón y su distancia en cm) sobre una imagen BGR de esa cámara."""
    if p is None:
        return image
    height, width = image.shape[:2]
    for point in points:
        projected = project(point, p)
        if projected is None:
            continue
        u, v, radius = projected
        if not (-radius <= u < width + radius and -radius <= v < height + radius):
            continue
        center, radius = (round(u), round(v)), max(6, round(radius))
        cv2.circle(image, center, radius + 2, (0, 0, 0), 4)
        cv2.circle(image, center, radius, MARK_COLOR, 2)
        label = f"{point['z_m'] * 100:.0f} cm"
        origin = (center[0] - radius, max(14, center[1] - radius - 6))
        cv2.putText(image, label, origin, cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(image, label, origin, cv2.FONT_HERSHEY_SIMPLEX, .55, MARK_COLOR, 1, cv2.LINE_AA)
    return image


def draw_boxes(cv2, image, boxes):
    """Cajas de YOLO [(u centro, v centro, ancho, alto, clase, confianza), ...] en píxeles de esa misma imagen."""
    for u, v, w, h, name, score in boxes:
        top_left = (round(u - w / 2), round(v - h / 2))
        bottom_right = (round(u + w / 2), round(v + h / 2))
        cv2.rectangle(image, top_left, bottom_right, (255, 120, 0), 2)
        label = f'{name} {score:.2f}'
        origin = (top_left[0], max(14, top_left[1] - 6))
        cv2.putText(image, label, origin, cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(image, label, origin, cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 120, 0), 1, cv2.LINE_AA)
    return image


def image_to_bgr(cv2, np, image):
    """sensor_msgs/Image (bgr8, rgb8, bgra8, rgba8, mono8) -> arreglo BGR, o None si no es una imagen válida."""
    channels = {'bgr8': 3, 'rgb8': 3, 'bgra8': 4, 'rgba8': 4, 'mono8': 1}.get(image.encoding)
    if (channels is None or not 0 < image.width <= 1920 or not 0 < image.height <= 1080
            or image.step < image.width * channels or len(image.data) != image.step * image.height):
        return None
    rows = np.frombuffer(image.data, dtype=np.uint8).reshape(image.height, image.step)
    pixels = rows[:, :image.width * channels].reshape(image.height, image.width, channels)
    conversion = {'rgb8': cv2.COLOR_RGB2BGR, 'bgra8': cv2.COLOR_BGRA2BGR, 'rgba8': cv2.COLOR_RGBA2BGR,
                  'mono8': cv2.COLOR_GRAY2BGR}.get(image.encoding)
    return cv2.cvtColor(pixels, conversion) if conversion is not None else pixels.copy()


def encode(cv2, image):
    success, jpeg = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return jpeg.tobytes() if success else b''
