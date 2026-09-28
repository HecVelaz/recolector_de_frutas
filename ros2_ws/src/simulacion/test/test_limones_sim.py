"""Visión simulada de limones_sim (sin ROS): colcon test o pytest."""

import math
from pathlib import Path

from simulacion.limones_sim import leer_limones, superficie, visible

MUNDO = Path(__file__).resolve().parents[1] / 'worlds' / 'hilera.sdf'


def test_lee_los_12_limones_cosechables_del_mundo():
    limones = leer_limones(MUNDO)  # los limon_fijo_* de la fila derecha no cuentan
    assert sorted(limones) == list(range(1, 13))
    for x, y, z in limones.values():
        assert 0.4 < y < 0.6 and 0.20 <= z <= 0.50  # fila izquierda, lado del pasillo, esfera de trabajo de R1


def test_lo_que_el_estereo_podria_localizar():
    assert visible((0.0, 0.0, 0.6), 0.40, 0.95)             # centro de la imagen
    assert not visible((0.0, 0.0, 0.3), 0.40, 0.95)         # demasiado cerca para la disparidad
    assert not visible((0.0, 0.0, 1.2), 0.40, 0.95)         # demasiado lejos
    assert not visible((0.25, 0.0, 0.6), 0.40, 0.95)        # u = 769: fuera de la imagen
    assert not visible((0.0, 0.2, 0.6), 0.40, 0.95)         # v = 599: fuera de la imagen
    assert not visible((-0.05, 0.0, 0.6), 0.40, 0.95)       # u = 230: franja ciega del BM (u < 271)
    assert visible((-0.02, 0.0, 0.6), 0.40, 0.95)           # u = 284


def test_superficie_y_centro_son_inversos():
    # mision suma el radio sobre el rayo (centro_desde_superficie): tiene que volver al centro
    c = (0.1, -0.05, 0.6)
    s = superficie(c, 0.03)
    d = math.dist(s, (0, 0, 0))
    assert math.isclose(math.dist(c, (0, 0, 0)) - d, 0.03)
    assert all(math.isclose(ci, si * (1 + 0.03 / d)) for ci, si in zip(c, s))
