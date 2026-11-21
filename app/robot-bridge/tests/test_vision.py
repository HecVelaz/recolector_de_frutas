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
