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
    def test_marks_lemons_and_colors_depth(self):
        image = np.zeros((480, 640, 3), np.uint8)
        lemon = {'x_m': -.123, 'y_m': -.002, 'z_m': .447}
        vision.draw_lemons(cv2, image, [lemon], P_LEFT)
        u, v, radius = (round(x) for x in vision.project(lemon, P_LEFT))
        self.assertTrue((image[v, u - radius] == vision.MARK_COLOR).all())     # el borde del círculo
        disparity = np.full((480, 640), np.nan, np.float32)
        disparity[:, :320] = 175.   # cerca
        disparity[:, 320:400] = 75.  # lejos
        depth = vision.depth_view(cv2, np, disparity, 70., 181.)
        self.assertTrue((depth[:, 400:] == 0).all())                  # sin dato: negro
        near, far = depth[0, 0].astype(int), depth[0, 350].astype(int)
        self.assertGreater(near[2], near[0])                          # cerca: rojo > azul
        self.assertGreater(far[0], far[2])                            # lejos: azul > rojo
        jpeg = vision.encode(cv2, depth)
        self.assertTrue(jpeg.startswith(b'\xff\xd8') and jpeg.endswith(b'\xff\xd9'))

    @unittest.skipUnless(HAS_CV, 'opencv')
    def test_converts_ros_images(self):
        from types import SimpleNamespace
        bgra = SimpleNamespace(encoding='bgra8', width=2, height=1, step=8, data=bytes([1, 2, 3, 255, 4, 5, 6, 255]))
        self.assertEqual(vision.image_to_bgr(cv2, np, bgra).tolist(), [[[1, 2, 3], [4, 5, 6]]])
        self.assertIsNone(vision.image_to_bgr(cv2, np, SimpleNamespace(encoding='16UC1', width=1, height=1, step=2,
                                                                       data=b'00')))
        values = np.array([[70., 181.]], '<f4')
        message = SimpleNamespace(image=SimpleNamespace(encoding='32FC1', width=2, height=1, step=8,
                                                        is_bigendian=0, data=values.tobytes()))
        self.assertEqual(vision.disparity_to_array(np, message).tolist(), [[70., 181.]])
