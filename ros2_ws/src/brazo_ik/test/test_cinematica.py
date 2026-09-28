"""Pruebas de la cinemática portada de la E4 (sin ROS): colcon test o pytest."""

import math
import random

from brazo_ik.cinematica import (cinematica_directa, cinematica_inversa, config_valida, Q1_LIM, Q2_LIM,
                                 Q3_LIM)
from brazo_ik.cinematica import cinematica_directa as directa, muneca_desde_herramienta
from brazo_ik.nodo_ik import resolver


def test_ejemplo_numerico_de_la_e4():
    # E4 §9: P_d = (368.32, 0, 91.03) mm -> q = (0°, 45°, 0°), q3O = -113.516°
    sols, _ = cinematica_inversa(368.32, 0.0, 91.03)
    assert sols
    s = sols[0]
    assert math.degrees(s.q1) == 0.0
    assert abs(math.degrees(s.q2) - 45.0) < 0.01
    assert abs(math.degrees(s.q3) - 0.0) < 0.01
    assert abs(math.degrees(s.q30) - (-113.516)) < 0.01


def test_directa_inversa_directa():
    # Como la validación de la E4: miles de configuraciones válidas vuelven a su punto
    rng = random.Random(1)
    probadas = 0
    while probadas < 2000:
        q = [math.radians(rng.uniform(*lim)) for lim in (Q1_LIM, Q2_LIM, Q3_LIM)]
        fk = cinematica_directa(*q)
        if fk is None or not config_valida(*q, fk[2]):
            continue
        probadas += 1
        sols, motivos = cinematica_inversa(*fk[0])
        assert sols, motivos
        assert any(max(abs(a - b) for a, b in zip((s.q1, s.q2, s.q3), q)) < 1e-6 for s in sols)
        assert all(s.err < 1e-4 for s in sols)


def test_demasiado_lejos():
    sols, motivos = cinematica_inversa(900.0, 0.0, 150.0)
    assert not sols
    assert 'Demasiado lejos' in motivos[0]


def test_q1_fuera_de_rango():
    sols, motivos = cinematica_inversa(-100.0, 300.0, 150.0)  # ~108° de la base
    assert not sols
    assert any('q1' in m for m in motivos)


def test_resolver_en_metros():
    q, texto = resolver(0.36832, 0.0, 0.09103)
    assert q is not None and texto.startswith('ok')
    assert abs(math.degrees(q[1]) - 45.0) < 0.01
    q, texto = resolver(0.9, 0.0, 0.15)
    assert q is None and texto.startswith('inalcanzable')


def test_herramienta_horizontal():
    # TCP a 75 mm de la muñeca en horizontal, en la dirección de q1 (brazo tipo uArm)
    assert muneca_desde_herramienta(0.3, 0.4, 0.1, 0.0) == (0.3, 0.4, 0.1)
    m = muneca_desde_herramienta(0.3, 0.4, 0.1, 0.075)  # r = 0,5 -> 0,425
    assert all(abs(a - b) < 1e-12 for a, b in zip(m, (0.255, 0.34, 0.1)))
    assert muneca_desde_herramienta(0.05, 0.0, 0.1, 0.075) is None
    # con resolver: la muñeca que resulta queda 75 mm antes del TCP, a la misma altura y en la misma dirección
    q, texto = resolver(0.36832 + 0.075, 0.0, 0.09103, 0.075)
    assert q is not None and abs(math.degrees(q[1]) - 45.0) < 0.01, texto
    p = directa(q[0], q[1], q[2])[0]
    assert abs(p[0] - 368.32) < 1e-6 and abs(p[2] - 91.03) < 1e-6
