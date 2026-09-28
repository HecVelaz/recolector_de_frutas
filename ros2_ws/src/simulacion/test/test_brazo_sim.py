"""Conversión actuador <-> cadena serie equivalente del cuatro barras (sin ROS): colcon test o pytest."""

import math
import random

from brazo_ik.cinematica import cinematica_directa, config_valida, L2, L3, H1
from simulacion.brazo_sim import acercar, actuador_a_serie, serie_a_actuador


def test_ejemplo_e4():
    # q = (0°, 45°, 0°) -> q3O = -113,516° (E4 §9)
    assert abs(math.degrees(actuador_a_serie(math.radians(45), 0.0)) + 113.516) < 0.01


def test_ida_y_vuelta_y_misma_muneca():
    random.seed(1)
    n = 0
    while n < 500:
        q2, q3 = math.radians(random.uniform(-25, 135)), math.radians(random.uniform(-50, 50))
        q3o = actuador_a_serie(q2, q3)
        if q3o is None or not config_valida(0.0, q2, q3, cinematica_directa(0.0, q2, q3)[2]):
            continue
        n += 1
        # q3_prev a 0,5° (en 20 ms J3 se mueve como mucho 0,4°): cerca del pliegue del cuatro barras (q3O ≈ -131,7°)
        # hay dos q3 a ~2,5° que dan el mismo q3O, y solo la continuidad las distingue
        # En la franja del pliegue (q3O < -130°) el q3 informado queda ambiguo en ~2,5°; la pose no (depende de q3O)
        if q3o > math.radians(-130):
            assert abs(serie_a_actuador(q2, q3o, q3 + math.radians(0.5)) - q3) < 1e-9
        # la cadena serie de Gazebo (l2 y l3 con q2 y q2 + q3O) pone la muñeca donde la directa de la E4
        th = q2 + q3o
        x = L2 * math.cos(q2) + L3 * math.cos(th)
        z = H1 + L2 * math.sin(q2) + L3 * math.sin(th)
        p = cinematica_directa(0.0, q2, q3)[0]
        assert abs(x - p[0]) < 1e-6 and abs(z - p[2]) < 1e-6  # mm


def test_acercar_respeta_el_paso():
    assert acercar(0.0, 1.0, 0.1) == 0.1
    assert acercar(0.95, 1.0, 0.1) == 1.0
    assert acercar(0.0, -1.0, 0.1) == -0.1
