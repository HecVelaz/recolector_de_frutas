"""Seguridad de base_sim = SeguridadBase.cpp del firmware (sin ROS): colcon test o pytest."""

import math

from simulacion.base_sim import eco_mas_cercano, Seguridad

LIBRE = dict(bumper=[False] * 3, dist_frente=math.inf, seta=False, roll=0.0, pitch=0.0, ms_sin_cmd=0,
             imu_valida=True)


def filtrar(seg, v=0.2, w=0.5, **cambios):
    return seg.filtrar(**{**LIBRE, **cambios}, v=v, w=w)


def test_libre_pasa_tal_cual():
    assert filtrar(Seguridad()) == (True, 0.2, 0.5)


def test_distancia_al_frente():
    assert filtrar(Seguridad(), dist_frente=0.15) == (True, 0.0, 0.5)            # < 0,20: no avanza
    assert filtrar(Seguridad(), v=-0.2, dist_frente=0.15) == (True, -0.2, 0.5)   # retroceder sí
    _, v, _ = filtrar(Seguridad(), dist_frente=0.35)                            # tope lineal: 0,25 * 0,15 / 0,30
    assert abs(v - 0.125) < 1e-9
    seg = Seguridad()
    assert filtrar(seg, dist_frente=math.nan) == (True, 0.0, 0.5) and seg.frente_sin_dato  # sin eco: no avanza


def test_bumpers():
    assert filtrar(Seguridad(), bumper=[True, False, False]) == (True, 0.0, 0.0)  # frente: ni avanza ni gira
    assert filtrar(Seguridad(), v=-0.1, bumper=[True, False, False]) == (True, -0.1, 0.0)
    assert filtrar(Seguridad(), bumper=[False, True, False]) == (True, 0.2, 0.0)  # lateral: recto sí, giro no


def test_seta_y_vuelco_enclavados():
    seg = Seguridad()
    assert filtrar(seg, seta=True) == (False, 0.0, 0.0)
    assert filtrar(seg) == (False, 0.0, 0.0)            # seta suelta: sigue en EMERGENCIA hasta rearmar
    assert seg.rearmar(False, 0.0, 0.0, True) and filtrar(seg) == (True, 0.2, 0.5)
    assert filtrar(seg, roll=30.0) == (False, 0.0, 0.0) and seg.estado == 'VUELCO'
    assert not seg.rearmar(False, 30.0, 0.0, True)      # todavía volcada


def test_watchdog_e_imu():
    seg = Seguridad(wd_ms=300)
    assert filtrar(seg, ms_sin_cmd=301) == (False, 0.0, 0.0) and seg.estado == 'sin comandos'
    assert filtrar(seg, imu_valida=False) == (False, 0.0, 0.0) and seg.estado == 'IMU sin datos'


def test_eco_mas_cercano():
    assert eco_mas_cercano([math.inf, 1.2, 0.8, math.inf]) == 0.8
    assert eco_mas_cercano([math.inf] * 15) == math.inf
