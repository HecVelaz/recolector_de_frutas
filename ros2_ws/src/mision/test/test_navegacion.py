"""Pruebas de la navegación con el banderín (sin ROS): colcon test o pytest."""

import json
import math
from pathlib import Path

import pytest

from mision.navegacion import (arboles_en_odom, BUSCAR, camino_j1, CIERRE, COSECHAR, distancia_minima,
                               error_cierre, FALLA, FIN, hilera_recta, IR_A_PARADA, j1_de, leer_hilera, cargar_hilera,
                               Navegacion, ParNav, plan_hilera, rot, VUELTA_U, wrap)

PAR = ParNav()
BANDERIN, MIRA = (0.0, 0.0), math.pi   # mirando hacia -x: la hilera sigue por +x, detrás de la marca


def hilera(n):
    return leer_hilera(hilera_recta(n))


def arbol_en_robot(pose, arbol):
    """Eje del árbol respecto de J1, en el marco del robot (adelante, izquierda)."""
    j1 = j1_de(pose, PAR)
    return rot((arbol[0] - j1[0], arbol[1] - j1[1]), -pose[2])


def test_arboles_desde_el_banderin():
    # Mirando la marca de frente (desde -x): la derecha es -y; frente negativo = detrás de la marca (+x)
    h = leer_hilera({'arboles': [{'derecha_mm': 300, 'frente_mm': -1500}]})
    (x, y), = arboles_en_odom(BANDERIN, MIRA, h)
    assert x == pytest.approx(1.5) and y == pytest.approx(-0.3)
    assert [a[0] for a in arboles_en_odom(BANDERIN, MIRA, hilera(3))] == pytest.approx([1.5, 3.0, 4.5])


def test_config_del_repo():
    j = json.loads((Path(__file__).parent.parent / 'config' / 'hilera_arboles.json').read_text())
    assert j['id'] == 0 and len(j['arboles']) == 3
    h = cargar_hilera(Path(__file__).parent.parent / 'config' / 'hilera_arboles.json', 2)
    assert len(h['arboles']) == 2 and h['lado'] == pytest.approx(0.150)
    with pytest.raises(ValueError):
        leer_hilera(j, 4)


@pytest.mark.parametrize('n', [2, 3])
@pytest.mark.parametrize('lados', [1, 2])
def test_plan_de_paradas(n, lados):
    metas, aviso = plan_hilera((-2.0, 0.5, 0.3), BANDERIN, MIRA, hilera(n), lados, PAR)
    assert aviso is None
    arboles = arboles_en_odom(BANDERIN, MIRA, hilera(n))
    paradas = [(k, lado, pose) for _, k, lado, pose, cosechar in metas if cosechar]
    esperado = [(k, 'A') for k in range(1, n + 1)] + ([(k, 'B') for k in range(n, 0, -1)] if lados == 2 else [])
    assert [(k, lado) for k, lado, _ in paradas] == esperado
    for k, lado, pose in paradas:
        # El árbol a 70 cm a la izquierda de J1 y 15 cm adelante, el robot a lo largo de la hilera
        assert arbol_en_robot(pose, arboles[k - 1]) == pytest.approx(PAR.parada, abs=1e-9)
        assert abs(wrap(pose[2] - (0.0 if lado == 'A' else math.pi))) < 1e-9
    assert metas[-1][0] == CIERRE
    # Todo el camino ideal, desde la pose inicial, a >= 45 cm del banderín y de los troncos
    previa = (-2.0, 0.5, 0.3)
    for _, _, _, pose, _ in metas:
        assert distancia_minima(camino_j1(previa, pose, PAR), [BANDERIN] + arboles) >= PAR.sep_min
        previa = pose


def test_vuelta_en_u():
    metas, _ = plan_hilera((-2.0, 0.5, 0.3), BANDERIN, MIRA, hilera(3), 2, PAR)
    u = [m for m in metas if m[0] == VUELTA_U]
    assert len(u) == 2 and u[0][2] is None and u[1][2] == 'B'
    # Antihorario visto de arriba: de mirar a +x pasa a +y y después a -x, siempre con el árbol 3 a la izquierda
    assert [round(math.degrees(m[3][2])) % 360 for m in u] == [90, 180]
    for m in u:
        assert arbol_en_robot(m[3], (4.5, 0.0)) == pytest.approx(PAR.parada, abs=1e-9)
    # Las paradas del lado B quedan del otro lado de la hilera (+y)
    assert all(m[3][1] > 0 for m in metas if m[2] == 'B')
    assert all(m[3][1] < 0 for m in metas if m[2] == 'A')


def test_entrada_cuando_el_camino_directo_pasa_por_el_banderin():
    # De frente a la marca, sobre la línea de la hilera: ir directo a la parada 1 pasaría por encima del banderín
    metas, aviso = plan_hilera((-2.0, 0.0, 0.0), BANDERIN, MIRA, hilera(2), 1, PAR)
    assert aviso is None and metas[0][0] == IR_A_PARADA and metas[0][4] is False and metas[1][1:3] == (1, 'A')


def test_rechaza_si_pasa_a_menos_de_45_cm():
    # El árbol 3 entre el 1 y el 2, sobre la línea de J1 de la ida (70 cm a la derecha de la hilera): se lo llevaría
    h = leer_hilera({'arboles': [{'derecha_mm': 0, 'frente_mm': -1500}, {'derecha_mm': 0, 'frente_mm': -3000},
                                 {'derecha_mm': 700, 'frente_mm': -2250}]})
    _, aviso = plan_hilera((-2.0, 0.5, 0.3), BANDERIN, MIRA, h, 1, PAR)
    assert aviso is not None and 'tronco' in aviso
    # El banderín 30 cm al costado de la hilera, entre los árboles 1 y 2: la ida pasa a < 45 cm
    h = leer_hilera({'arboles': [{'derecha_mm': -400, 'frente_mm': 750}, {'derecha_mm': -400, 'frente_mm': -750}]})
    _, aviso = plan_hilera((-2.0, -2.0, 0.0), BANDERIN, MIRA, h, 1, PAR)
    assert aviso is not None and 'banderín' in aviso


def test_error_cierre():
    # El robot cree estar en (1, 0, 0) pero está 3 cm más adelante y girado 2°: el banderín lo dice
    real = (1.03, 0.0, math.radians(2.0))
    b, mira = (3.0, 1.0), math.pi
    marca_rel = rot((b[0] - real[0], b[1] - real[1]), -real[2])
    a, c, r = error_cierre((1.0, 0.0, 0.0), b, mira, (*marca_rel, wrap(mira - real[2])))
    assert a == pytest.approx(-0.03, abs=1e-9) and c == pytest.approx(0.0, abs=1e-9)
    assert math.degrees(r) == pytest.approx(-2.0)


# --- FSM completa contra un robot cinemático ideal: la cámara ve el banderín si está a 0,9-4 m, dentro de ±25° de
# donde mira (yaw_camara) y de frente (la cara impresa hacia la cámara, ±60°)

class Robot:
    def __init__(self, pose, banderin=BANDERIN, mira=MIRA):
        self.pose = list(pose)
        self.b, self.mira = banderin, mira
        self.cmd = (0.0, 0.0)
        self.estados = []

    def enviar(self, tipo, valor):
        if tipo == 'cmd_vel':
            self.cmd = valor
        elif tipo == 'estado':
            self.estados.append(valor)

    def mover(self, dt):
        v, w = self.cmd
        self.pose[0] += v * math.cos(self.pose[2]) * dt
        self.pose[1] += v * math.sin(self.pose[2]) * dt
        self.pose[2] = wrap(self.pose[2] + w * dt)

    def marca(self):
        x, y, th = self.pose
        rel = rot((self.b[0] - x, self.b[1] - y), -th)
        d = math.hypot(*rel)
        rumbo = math.atan2(rel[1], rel[0])
        de_frente = abs(wrap(self.mira - math.atan2(y - self.b[1], x - self.b[0]))) < math.radians(60)
        if 0.9 <= d <= 4.0 and abs(wrap(rumbo - PAR.yaw_camara)) < math.radians(25) and de_frente:
            return (*rel, wrap(self.mira - th))
        return None


def correr(pose0, n, lados, cosechar=None, t_max=1500.0):
    r = Robot(pose0)
    nav = Navegacion(r.enviar, hilera(n), lados)
    arboles = arboles_en_odom(BANDERIN, MIRA, hilera(n))
    paradas = []
    dt, t = 0.05, 0.0
    mision = 'ESPERAR'
    nav.al_estado_base('ARMADA modo=libre seguridad=ok', 0.0)
    while t < t_max and nav.estado not in (FIN, FALLA):
        t += dt
        r.mover(dt)
        nav.al_odom(*r.pose, t)
        m = r.marca()
        if m:
            nav.al_marca(*m, t, t)
        if cosechar:
            mision = cosechar(nav, t)
        nav.al_estado_mision(mision, t)
        antes = nav.estado
        nav.paso(t)
        if nav.estado == COSECHAR and antes != COSECHAR:
            _, k, lado, _, _ = nav.meta
            paradas.append((k, lado, arbol_en_robot(r.pose, arboles[k - 1]), r.pose[2]))
    return nav, r, paradas


@pytest.mark.parametrize('pose0', [(-2.0, 0.5, 0.3), (-1.0, -1.5, 2.0), (-2.5, -1.2, -2.5)])
def test_fsm_recorrido_completo(pose0):
    nav, r, paradas = correr(pose0, 3, 2)
    assert nav.estado == FIN, r.estados[-3:]
    assert [(k, lado) for k, lado, _, _ in paradas] == [(1, 'A'), (2, 'A'), (3, 'A'), (3, 'B'), (2, 'B'), (1, 'B')]
    for k, lado, rel, rumbo in paradas:
        assert rel == pytest.approx(PAR.parada, abs=PAR.min_recto)   # por debajo de min_recto no se mueve
        assert abs(wrap(rumbo - (0.0 if lado == 'A' else math.pi))) < math.radians(1.0)
    # odometría ideal: el cierre no encuentra error
    assert max(abs(e) for e in nav.error[:2]) < 0.005 and abs(nav.error[2]) < math.radians(0.5)


def test_fsm_un_lado_dos_arboles():
    nav, r, paradas = correr((-2.0, 0.5, 0.3), 2, 1)
    assert nav.estado == FIN and [(k, lado) for k, lado, _, _ in paradas] == [(1, 'A'), (2, 'A')]


def test_fsm_espera_a_la_mision():
    # En cada parada la misión cosecha un limón (sale de ESPERAR 10 s): la base no se mueve mientras tanto
    cosechas = {}

    def cosechar(nav, t):
        if nav.estado == COSECHAR and nav.base_quieta(t):
            k = (nav.meta[1], nav.meta[2])
            cosechas.setdefault(k, t)
            return 'APROXIMAR' if t - cosechas[k] < 10.0 else 'ESPERAR'
        return 'ESPERAR'

    nav, r, paradas = correr((-2.0, 0.5, 0.3), 2, 1, cosechar)
    assert nav.estado == FIN and len(cosechas) == 2


def test_fsm_no_ve_el_banderin():
    r = Robot((-2.0, 0.5, 0.3), banderin=(50.0, 50.0))
    nav = Navegacion(r.enviar, hilera(2), 2)
    nav.al_estado_base('ARMADA', 0.0)
    t = 0.0
    while t < 200 and nav.estado != FALLA:
        t += 0.05
        r.mover(0.05)
        nav.al_odom(*r.pose, t)
        nav.al_estado_mision('ESPERAR', t)
        nav.paso(t)
    assert nav.estado == FALLA and nav.giros == 12
    assert abs(wrap(r.pose[2] - 0.3)) < math.radians(2)   # dio la vuelta entera


def test_fsm_no_mueve_la_base_sin_la_mision_en_esperar():
    r = Robot((-2.0, 0.5, 0.3))
    nav = Navegacion(r.enviar, hilera(2), 2)
    nav.al_estado_base('ARMADA', 0.0)
    nav.al_odom(*r.pose, 0.0)
    nav.al_estado_mision('ESPERAR', 0.0)
    nav.paso(0.1)
    assert nav.estado == BUSCAR
    nav.al_estado_mision('APROXIMAR', 0.2)
    for k in range(100):
        nav.paso(0.3 + k * 0.05)
        assert r.cmd == (0.0, 0.0)


def test_fsm_seta():
    r = Robot((-2.0, 0.5, 0.3))
    nav = Navegacion(r.enviar, hilera(2), 2)
    nav.al_estado_base('ARMADA', 0.0)
    nav.al_estado_base('DESARMADA modo=libre seguridad=ok SETA', 1.0)
    assert nav.estado == FALLA
    nav.paso(1.1)
    assert r.cmd == (0.0, 0.0)


def test_fsm_arma_la_base():
    salidas = []
    nav = Navegacion(lambda t, v: salidas.append((t, v)), hilera(2), 2)
    nav.al_odom(0.0, 0.0, 0.0, 0.0)
    nav.paso(1.0)
    assert ('comando_base', 'armar') in salidas and nav.estado != BUSCAR
