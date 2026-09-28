"""Visión simulada de limones_sim (sin ROS): colcon test o pytest."""

import math
from pathlib import Path

from simulacion.limones_sim import leer_limones, superficie, visible

MUNDO = Path(__file__).resolve().parents[1] / 'worlds' / 'hilera.sdf'


def test_lee_los_4_limones_cosechables_del_mundo():
    limones = leer_limones(MUNDO)
    assert sorted(limones) == [1, 2, 3, 4]
    for x, y, z in limones.values():
        assert 0.4 < y < 0.55 and 0.20 <= z <= 0.50  # fila izquierda, lado del pasillo, esfera de trabajo de R1


def test_campo_visual_y_ventana():
    h, v = math.radians(33), math.radians(25)
    assert visible((0.0, 0.0, 0.6), h, v, 0.40, 0.95)
    assert not visible((0.0, 0.0, 0.3), h, v, 0.40, 0.95)   # demasiado cerca para la disparidad
    assert not visible((0.0, 0.0, 1.2), h, v, 0.40, 0.95)   # demasiado lejos
    assert not visible((0.25, 0.0, 0.6), h, v, 0.40, 0.95)  # 22,6° a la derecha: fuera de los 16,5°
    assert not visible((0.0, 0.2, 0.6), h, v, 0.40, 0.95)   # 18,4° abajo: fuera de los 12,5°


def test_superficie_y_centro_son_inversos():
    # mision suma el radio sobre el rayo (centro_desde_superficie): tiene que volver al centro
    c = (0.1, -0.05, 0.6)
    s = superficie(c, 0.03)
    d = math.dist(s, (0, 0, 0))
    assert math.isclose(math.dist(c, (0, 0, 0)) - d, 0.03)
    assert all(math.isclose(ci, si * (1 + 0.03 / d)) for ci, si in zip(c, s))
