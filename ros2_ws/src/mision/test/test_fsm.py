"""Pruebas de la máquina de estados (sin ROS): colcon test o pytest."""

import math

from mision.fsm import (AGARRAR, APROXIMAR, centro_desde_superficie, ESPERAR, FALLA, leer_estado_brazo, Mision,
                        RETIRAR, SOLTAR)

LIMON = (0.45, 0.05, 0.25)  # m, alcanzable
LEJOS = (2.0, 0.0, 0.25)


def estado_brazo(armado=True, llego=True, falla='ninguna'):
    j = ''.join(f'J{i} posicion cero u=0% falla={falla if i == 2 else "ninguna"}{" llego" if llego else ""}; '
                for i in (1, 2, 3))
    return f'{"ARMADO" if armado else "DESARMADO"}; {j}enlace: pings_fallidos=0 cortes=0'


class Registro:
    def __init__(self):
        self.salidas = []

    def __call__(self, tipo, valor):
        self.salidas.append((tipo, valor))

    def de(self, tipo):
        return [v for t, v in self.salidas if t == tipo]


def lista():
    """Misión en ESPERAR con el brazo armado y quieto."""
    r = Registro()
    m = Mision(r)
    m.al_estado_brazo(estado_brazo(armado=False), 0.0)
    m.paso(1.0)
    assert r.de('comando') == ['armar']
    m.al_estado_brazo(estado_brazo(), 1.2)
    m.paso(1.3)
    assert m.estado == ESPERAR and r.de('cierre') == [0.0]
    return m, r


def ver_limon(m, p, t0, n=5):
    for k in range(n):
        m.al_limon(p, t0 + 0.3 * k)


def mover_y_llegar(m, t):
    m.al_estado_brazo(estado_brazo(llego=False), t)
    m.paso(t)
    m.al_estado_brazo(estado_brazo(), t + 1)
    m.paso(t + 1)


def test_leer_estado_brazo():
    assert leer_estado_brazo(estado_brazo()) == (True, True, [])
    assert leer_estado_brazo(estado_brazo(armado=False, llego=False)) == (False, False, [])
    assert leer_estado_brazo(estado_brazo(falla='fuera de limites')) == (True, True, ['fuera de limites'])


def test_centro_desde_superficie():
    c = centro_desde_superficie((0.0, 0.3, 0.4), 0.03)  # a 0,5 m sobre el rayo
    assert math.isclose(math.dist(c, (0, 0, 0)), 0.53)
    assert math.isclose(c[1] / c[2], 0.75)


def test_ciclo_completo():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    assert m.estado == APROXIMAR and r.de('objetivo') == [LIMON]
    m.al_estado_brazo(estado_brazo(), 3.3)  # "llego" viejo, de antes de moverse: no cuenta
    m.paso(3.3)
    assert m.estado == APROXIMAR
    mover_y_llegar(m, 4.0)
    assert m.estado == AGARRAR and r.de('cierre')[-1] == 100.0
    m.paso(6.6)
    assert m.estado == RETIRAR and r.de('objetivo')[-1] == m.par.reposo
    mover_y_llegar(m, 7.0)
    assert m.estado == SOLTAR and r.de('cierre')[-1] == 0.0
    m.al_estado_brazo(estado_brazo(), 9.6)
    m.paso(9.6)
    assert m.estado == ESPERAR
    assert 's' not in r.de('comando')


def test_muestras_que_no_coinciden_no_disparan():
    m, r = lista()
    for k in range(10):
        m.al_limon((LIMON[0] + (0.05 if k % 2 else 0.0), LIMON[1], LIMON[2]), 2.0 + 0.3 * k)
    assert m.estado == ESPERAR and not r.de('objetivo')


def test_muestras_viejas_se_descartan():
    m, r = lista()
    ver_limon(m, LIMON, 2.0, n=4)
    ver_limon(m, LIMON, 10.0, n=1)  # la quinta llega mucho después: no alcanza
    assert m.estado == ESPERAR


def test_fuera_de_alcance_sigue_esperando():
    m, r = lista()
    ver_limon(m, LEJOS, 2.0)
    assert m.estado == ESPERAR and not r.de('objetivo')
    assert 'fuera de alcance' in r.de('estado')[-1]


def test_desarmado_no_manda_objetivos():
    m, r = lista()
    m.al_estado_brazo(estado_brazo(armado=False), 1.5)
    ver_limon(m, LIMON, 2.0)
    assert m.estado == ESPERAR and not r.de('objetivo')


def test_falla_del_brazo_detiene():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_estado_brazo(estado_brazo(llego=False, falla='atasco'), 3.5)
    m.paso(3.5)
    assert m.estado == FALLA and r.de('comando')[-1] == 's'
    ver_limon(m, LIMON, 5.0)  # en FALLA no hace nada más
    m.paso(6.0)
    assert m.estado == FALLA and len(r.de('objetivo')) == 1


def test_sin_estado_del_brazo_detiene():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.paso(5.0)  # último /brazo/estado en 1,2 s
    assert m.estado == FALLA and 'sin /brazo/estado' in r.de('estado')[-1]


def test_no_llega_a_tiempo():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    for t in range(4, 30):
        m.al_estado_brazo(estado_brazo(llego=False), t)
        m.paso(t)
    assert m.estado == FALLA and 'no llegó' in r.de('estado')[-1]


def test_ik_inalcanzable_detiene():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_ik('inalcanzable: marco "camera" distinto de "brazo_base"', 3.3)
    assert m.estado == FALLA
