import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from bridge import create_app
from vision import CameraFrames


class VisionTest(unittest.TestCase):
    def test_frame_expires_or_is_removed_after_invalid_input(self):
        now = [2.0]
        frames = CameraFrames(clock=lambda: now[0])
        jpeg = b'\xff\xd8data\xff\xd9'
        frames.put('left', jpeg)
        self.assertEqual(frames.latest('left'), jpeg)
        now[0] += 1.6
        self.assertIsNone(frames.latest('left'))
        frames.put('left', jpeg)
        frames.put('left', b'bad')
        self.assertIsNone(frames.latest('left'))

    def test_jpeg_is_private_and_only_delivered_from_ros_observer(self):
        jpeg = b'\xff\xd8data\xff\xd9'

        class Reader:
            def __init__(self, store, *, node_name, camera_frames, stereo=None, marker_tools=None):
                camera_frames.put('left', jpeg)

            def close(self):
                pass

        headers = {'Authorization':'Bearer test'}
        with patch('ros_source.RosReader', Reader), TestClient(create_app(source='ros2', token='test')) as client:
            self.assertEqual(client.get('/api/v1/vision/left/frame').status_code, 401)
            frame = client.get('/api/v1/vision/left/frame', headers=headers)
            self.assertEqual(frame.content, jpeg)
            self.assertEqual(frame.headers['content-type'], 'image/jpeg')
            self.assertEqual(frame.headers['cache-control'], 'no-store')
            self.assertEqual(client.get('/api/v1/vision/right/frame', headers=headers).status_code, 204)
            self.assertEqual(client.get('/api/v1/vision/unknown/frame', headers=headers).status_code, 404)
        with TestClient(create_app(source='simulation', token='test')) as client:
            self.assertEqual(client.get('/api/v1/vision/left/frame', headers=headers).status_code, 204)


# ------------------------------------------------ vistas izquierda / central / derecha con los limones (20/11)
try:
    import cv2
    import numpy as np
    HAS_CV = True
except ImportError:
    HAS_CV = False

import vision

# P de la Pi (camera_info del 20/11): f 672,1, centro (425,5; 236,8), base 10,03 cm
P_LEFT = [672.126313, 0., 425.455894, 0., 0., 672.126313, 236.809729, 0., 0., 0., 1., 0.]
P_RIGHT = [672.126313, 0., 425.455894, -67.432454, 0., 672.126313, 236.809729, 0., 0., 0., 1., 0.]


class ViewsTest(unittest.TestCase):
    def test_projection_matches_the_stereo_disparity(self):
        lemon = {'x_m': -.123, 'y_m': -.002, 'z_m': .447}   # el limón que veía el localizador
        ul, vl, radius = vision.project(lemon, P_LEFT)
        ur, vr, _ = vision.project(lemon, P_RIGHT)
        self.assertAlmostEqual(vl, vr)
        self.assertAlmostEqual(ul - ur, 672.126313 * .10032705 / .447, places=0)   # disparidad = f·B/Z
        self.assertAlmostEqual(radius, 672.126313 * .025 / .447)
        self.assertIsNone(vision.project({'x_m': 0., 'y_m': 0., 'z_m': 0.}, P_LEFT))

    @unittest.skipUnless(HAS_CV, 'opencv')
    def test_marks_lemons(self):
        image = np.zeros((480, 640, 3), np.uint8)
        lemon = {'x_m': -.123, 'y_m': -.002, 'z_m': .447}
        vision.draw_lemons(cv2, image, [lemon], P_LEFT)
        u, v, radius = (round(x) for x in vision.project(lemon, P_LEFT))
        self.assertTrue((image[v, u - radius] == vision.MARK_COLOR).all())     # el borde del círculo
        jpeg = vision.encode(cv2, image)
        self.assertTrue(jpeg.startswith(b'\xff\xd8') and jpeg.endswith(b'\xff\xd9'))

    @unittest.skipUnless(HAS_CV, 'opencv')
    def test_converts_ros_images(self):
        from types import SimpleNamespace
        bgra = SimpleNamespace(encoding='bgra8', width=2, height=1, step=8, data=bytes([1, 2, 3, 255, 4, 5, 6, 255]))
        self.assertEqual(vision.image_to_bgr(cv2, np, bgra).tolist(), [[[1, 2, 3], [4, 5, 6]]])
        self.assertIsNone(vision.image_to_bgr(cv2, np, SimpleNamespace(encoding='16UC1', width=1, height=1, step=2,
                                                                       data=b'00')))

    @unittest.skipUnless(HAS_CV, 'opencv')
    def test_draws_yolo_boxes(self):
        image = np.zeros((480, 640, 3), np.uint8)
        vision.draw_boxes(cv2, image, [(200., 240., 40., 50., 'limon', .87)])
        self.assertTrue((image[240, 180] == (255, 120, 0)).all())   # borde izquierdo de la caja
        self.assertTrue((image[240, 200] == 0).all())               # adentro queda la imagen


class OnDemandTest(unittest.TestCase):
    def test_views_are_built_only_while_requested(self):
        now = [10.]
        frames = CameraFrames(clock=lambda: now[0])
        self.assertFalse(frames.wanted('center'))           # nadie la pidió todavía
        self.assertIsNone(frames.latest('center'))          # el primer pedido devuelve 204 y la activa
        self.assertTrue(frames.wanted('center'))
        self.assertFalse(frames.wanted('left'))
        now[0] += 3.1
        self.assertFalse(frames.wanted('center'))           # 3 s sin pedidos: se deja de armar
