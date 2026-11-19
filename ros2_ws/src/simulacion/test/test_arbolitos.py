"""Mundo de los arbolitos y registro de la navegación (sin ROS): colcon test o pytest."""

import math
from pathlib import Path

import pytest

from mision.navegacion import hilera_recta, ParNav, pose_parada
from simulacion.limones_sim import leer_limones, nombre_mundo
from simulacion.mundo_arbolitos import generar
from simulacion.registro_nav import error_parada, leer_arboles

MUNDO = Path(__file__).resolve().parents[1] / 'worlds' / 'arbolitos.sdf'


def test_el_mundo_del_repo_es_el_generado():
    texto = MUNDO.read_text()
    assert texto == generar(hilera_recta(3), texto.split('mundo_arbolitos.py (')[1].split('):')[0])


@pytest.mark.parametrize('n', [2, 3])
def test_arboles_y_limones(n, tmp_path):
    (tmp_path / 'm.sdf').write_text(generar(hilera_recta(n, 1.5)))
    assert nombre_mundo(tmp_path / 'm.sdf') == 'arbolitos'
    arboles = leer_arboles(tmp_path / 'm.sdf')
    assert arboles == {k: pytest.approx((1.5 * k, 0.0)) for k in range(1, n + 1)}
    limones = leer_limones(tmp_path / 'm.sdf')
    assert len(limones) == 8 * n
    for num, (x, y, z) in limones.items():
        ax, ay = arboles[num // 10]
        assert math.hypot(x - ax, y - ay) == pytest.approx(0.12, abs=0.002) and 0.32 <= z <= 0.52


def test_error_parada():
    par = ParNav()
    pose = pose_parada((3.0, 0.0), math.pi, par)   # lado B del árbol 2, exacta
    assert error_parada(pose, (3.0, 0.0), math.pi, par.j1, par.parada) == pytest.approx((0, 0, 0), abs=1e-12)
    # Lado B (mira a -x): 2 cm más adelante (x - 0,02) -> el árbol queda 2 cm más atrás de lo pedido
    x, y, th = pose
    assert error_parada((x - 0.02, y, th), (3.0, 0.0), math.pi, par.j1, par.parada) == \
        pytest.approx((-0.02, 0.0, 0.0), abs=1e-12)
    assert math.degrees(error_parada((x, y, th + math.radians(1.0)), (3.0, 0.0), math.pi, par.j1,
                                     par.parada)[2]) == pytest.approx(1.0)
