"""Pruebas de la máquina de estados (sin ROS): colcon test o pytest."""

import math

from mision.fsm import (AGARRAR, APROXIMAR, centro_desde_superficie, ESPERAR, FALLA, leer_estado_brazo, Mision,
                        Parametros, RETIRAR, SOLTAR)

# Al costado izquierdo, del lado de la fila: J1 va de 45° a 225° (q1 = 0 al frente quedó fuera de rango)
LIMON = (0.05, 0.45, 0.25)  # m, alcanzable
LEJOS = (0.0, 2.0, 0.25)
Q_REPOSO = [1.571, 0.785, 0.0]  # rad, donde está el brazo al empezar
Q_LIMON = [1.46, 0.9, -0.5]     # lo que "calcula" brazo_ik para LIMON
QUIETO = [0.0, 0.0, 0.0]


def estado_brazo(armado=True, llego=True, falla='ninguna', cero='cero'):
    j = ''.join(f'J{i} posicion {cero if i == 3 else "cero"} u=0% falla={falla if i == 2 else "ninguna"}'
                f'{" llego" if llego else ""}; ' for i in (1, 2, 3))
    return f'{"ARMADO" if armado else "DESARMADO"}; {j}enlace: pings_fallidos=0 cortes=0'


class Registro:
    def __init__(self):
        self.salidas = []

    def __call__(self, tipo, valor):
        self.salidas.append((tipo, valor))

    def de(self, tipo):
        return [v for t, v in self.salidas if t == tipo]


def lista(par=None):
    """Misión en ESPERAR con el brazo armado y quieto en Q_REPOSO."""
    r = Registro()
    m = Mision(r, par)
    m.al_joints(Q_REPOSO, QUIETO, 0.0)
    m.al_estado_brazo(estado_brazo(armado=False), 0.0)
    m.paso(1.0)
    assert r.de('comando') == ['armar']
    m.al_estado_brazo(estado_brazo(), 1.2)
    m.paso(1.3)
    assert m.estado == ESPERAR and r.de('cierre') == [0.0]
    return m, r


def ver_limon(m, p, t0, n=5):
    for k in range(n):
        m.al_limon(p, t0 + 0.3 * k, t0 + 0.3 * k)


def mover_y_llegar(m, q, t):
    """brazo_ik responde con q; el brazo se mueve y llega."""
    m.al_joint_cmd(q, t)
    m.al_estado_brazo(estado_brazo(llego=False), t)
    m.al_joints([a / 2 for a in q], [0.3, 0.3, 0.3], t)
    m.paso(t)
    m.al_joints(q, QUIETO, t + 1)
    m.al_estado_brazo(estado_brazo(), t + 1)
    m.paso(t + 1)


def test_leer_estado_brazo():
    assert leer_estado_brazo(estado_brazo()) == (True, True, [])
    assert leer_estado_brazo(estado_brazo(armado=False, llego=False)) == (False, False, [])
    assert leer_estado_brazo(estado_brazo(falla='fuera de limites')) == (True, True, ['fuera de limites'])
    assert leer_estado_brazo(estado_brazo(cero='SIN_CERO')) == (True, True, ['sin cero'])


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
    mover_y_llegar(m, Q_LIMON, 4.0)
    assert m.estado == AGARRAR and r.de('cierre')[-1] == 100.0
    m.paso(6.6)
    assert m.estado == RETIRAR and r.de('objetivo')[-1] == m.par.reposo
    mover_y_llegar(m, Q_REPOSO, 7.0)
    assert m.estado == SOLTAR and r.de('cierre')[-1] == 0.0
    m.al_estado_brazo(estado_brazo(), 9.6)
    m.paso(9.6)
    assert m.estado == ESPERAR
    assert 's' not in r.de('comando')


def test_estados_viejos_de_un_movimiento_anterior_no_cierran():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_joint_cmd(Q_LIMON, 3.3)
    # pareja "no llegó -> llegó" atrasada, pero el brazo todavía en reposo: no es este objetivo
    m.al_estado_brazo(estado_brazo(llego=False), 3.4)
    m.al_estado_brazo(estado_brazo(), 3.5)
    m.paso(3.5)
    assert m.estado == APROXIMAR and r.de('cierre') == [0.0]


def test_objetivo_ya_alcanzado_no_da_timeout():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_joint_cmd(Q_REPOSO, 3.3)  # el objetivo coincide con donde está: nunca se ve "no llegó"
    m.al_estado_brazo(estado_brazo(), 3.5)
    m.paso(3.5)
    assert m.estado == AGARRAR


def test_falla_tapada_por_un_estado_bueno_igual_detiene():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_estado_brazo(estado_brazo(llego=False, falla='atasco'), 3.4)
    m.al_estado_brazo(estado_brazo(), 3.5)  # llega antes del próximo paso()
    m.paso(3.5)
    assert m.estado == FALLA and r.de('comando')[-1] == 's' and r.de('cierre') == [0.0]


def test_estado_del_brazo_vencido_no_manda_objetivos():
    m, r = lista()
    ver_limon(m, LIMON, 10.0)  # último /brazo/estado en 1,2 s
    assert m.estado == ESPERAR and not r.de('objetivo')


def test_brazo_sin_cero_o_moviendose_no_junta_muestras():
    for estado in (estado_brazo(cero='SIN_CERO'), estado_brazo(llego=False)):
        m, r = lista()
        m.al_estado_brazo(estado, 1.9)
        ver_limon(m, LIMON, 2.0)
        assert m.estado == ESPERAR and not r.de('objetivo')


def test_una_sola_muestra_no_promedia_con_la_anterior():
    m, r = lista(Parametros(n_muestras=1))
    m.al_limon(LEJOS, 2.0, 2.0)
    assert m.estado == ESPERAR
    m.al_limon(LIMON, 2.3, 2.3)
    assert m.estado == APROXIMAR and r.de('objetivo') == [LIMON]


def test_muestras_que_no_coinciden_no_disparan():
    m, r = lista()
    for k in range(10):
        t = 2.0 + 0.3 * k
        m.al_limon((LIMON[0] + (0.05 if k % 2 else 0.0), LIMON[1], LIMON[2]), t, t)
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


def test_seta_desarma_el_brazo_y_no_lo_rearma():
    m, r = lista()
    ver_limon(m, LIMON, 2.0)
    m.al_estado_base('ARMADA modo=vel seguridad=PARADA SETA imu=ok', 3.5)
    assert m.estado == FALLA and r.de('comando')[-1] == 'desarmar'
    m.al_estado_brazo(estado_brazo(armado=False), 4.0)
    m.paso(5.0)
    assert 'armar' not in r.de('comando')[1:]  # el único 'armar' es el del arranque


def test_seta_en_inicio_no_deja_armar():
    r = Registro()
    m = Mision(r, None)
    m.al_estado_brazo(estado_brazo(armado=False), 0.0)
    m.al_estado_base('DESARMADA modo=vel seguridad=PARADA SETA imu=ok', 0.5)
    m.paso(1.0)
    assert m.estado == FALLA and 'armar' not in r.de('comando')


def test_estado_de_base_sin_seta_no_hace_nada():
    m, r = lista()
    m.al_estado_base('ARMADA modo=vel seguridad=OK imu=ok', 1.5)
    assert m.estado == ESPERAR and r.de('comando') == ['armar']
