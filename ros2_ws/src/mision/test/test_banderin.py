"""Pose del banderín con solvePnP (sin ROS): una marca dibujada con una cámara conocida."""

import cv2
import numpy as np
import pytest

from mision.nodo_banderin import pose_marca


def test_pose_de_una_marca_sintetica():
    # Cámara de navegación (f = 672 px) y la marca de 150 mm de frente a 2 m, girada 20° alrededor de la vertical
    f, lado, z = 672.0, 0.150, 2.0
    K = np.array([[f, 0, 320], [0, f, 240], [0, 0, 1.0]])
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marca = cv2.copyMakeBorder(cv2.aruco.drawMarker(d, 0, 240), 80, 80, 80, 80, cv2.BORDER_CONSTANT, value=255)
    a = np.radians(20.0)
    R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    h = 0.125   # mitad de la tabla de 250 mm (marca + margen), y abajo en la imagen
    esq3 = np.array([[-h, -h, 0], [h, -h, 0], [h, h, 0], [-h, h, 0]]) @ R.T + [0.1, 0.05, z]
    esq2 = (esq3 @ K.T)[:, :2] / (esq3 @ K.T)[:, 2:]
    borde = [[-0.5, -0.5], [399.5, -0.5], [399.5, 399.5], [-0.5, 399.5]]   # bordes de los píxeles (centros enteros)
    H = cv2.getPerspectiveTransform(np.float32(borde), np.float32(esq2 - 0.5))
    img = cv2.warpPerspective(marca, H, (640, 480), borderValue=128)
    esq, ids, _ = cv2.aruco.detectMarkers(img, d)
    assert ids is not None and list(ids.ravel()) == [0]
    pos, normal = pose_marca(esq[0], K, lado)
    assert pos == pytest.approx([0.1, 0.05, z], abs=0.02)
    # La normal sale de la cara hacia la cámara: -z de la cámara girada 20°. Con ~50 px de marca, IPPE erra el
    # rumbo unos grados (por eso la navegación usa la mediana de 3 s y se acerca a la parada por la línea de paradas)
    assert np.degrees(np.arccos(np.dot(normal, -R[:, 2]))) < 5.0
