"""Pruebas del recorrido autónomo (sin ROS): colcon test o pytest."""

import math

from mision.fsm import alcanzable
from mision.recorrido import (ARRIMAR, AVANZAR, BLOQUEADO, desplazamiento_para_alcanzar, ESQUIVAR, FIN,
                              lado_para_esquivar, limon_atras, limon_util, MIRAR, obstaculo_en_el_camino, ParRecorrido, PASAR,
                              OdometriaGiro, Recorrido, VOLVER)

PAR = ParRecorrido()
LIBRE = (math.inf, math.inf, math.inf)


class Registro:
    def __init__(self):
        self.salidas = []

    def __call__(self, tipo, valor):
        self.salidas.append((tipo, valor))

    def de(self, tipo):
        return [v for t, v in self.salidas if t == tipo]


def mirando(x=0.0, rangos=LIBRE):
    """Recorrido en MIRAR con la base armada y la misión en ESPERAR."""
    r = Registro()
    rec = Recorrido(r)
    rec.al_odom(x, 0.0, 0.0, 0.0)
    rec.al_rangos(rangos, 0.0)
    rec.al_estado_mision('ESPERAR', 0.0)
    rec.paso(1.0)
    assert r.de('comando_base') == ['armar'] and rec.estado != MIRAR
    rec.al_estado_base('ARMADA modo=libre seguridad=ok', 1.1)
    rec.paso(1.2)
    assert rec.estado == MIRAR
    return rec, r


LIMON_UTIL = [(400.0, 1076.5 * 0.06 / 0.70)]   # caja de YOLO: a la derecha de u = 271, a 0,70 m
LIMON_LEJOS = [(400.0, 1076.5 * 0.06 / 1.50)]  # a 1,5 m: el estéreo no lo localiza
LIMON_CIEGO = [(150.0, 1076.5 * 0.06 / 0.70)]  # u < 271: sin disparidad


def test_limon_util():
    assert limon_util(LIMON_UTIL, PAR)
    assert not limon_util(LIMON_LEJOS, PAR) and not limon_util(LIMON_CIEGO, PAR) and not limon_util([], PAR)


def test_avanza_de_corrido_y_frena_al_ver_un_limon():
    rec, r = mirando()
    assert rec.base_quieta(1.8)              # frenada desde el arranque
    rec.paso(1.2 + PAR.t_quieto + PAR.t_sin_limon + 0.1)   # sin limones a la vista: sigue enseguida
    assert rec.estado == AVANZAR
    rec.paso(2.5)
    v, w = r.de('cmd_vel')[-1]
    assert abs(v - PAR.v_crucero) < 1e-9 and abs(w) < 1e-9 and not rec.base_quieta(2.5)
    rec.al_detecciones(LIMON_LEJOS, 2.6)
    rec.paso(2.6)
    assert rec.estado == AVANZAR             # lejos: no frena
    rec.al_odom(0.5, 0.0, 0.0, 3.0)
    rec.al_detecciones(LIMON_UTIL, 3.0)
    rec.paso(3.0)
    assert rec.estado == MIRAR and r.de('cmd_vel')[-1] == (0.0, 0.0)
    assert not rec.base_quieta(3.2) and rec.base_quieta(3.0 + PAR.t_quieto)   # recién frenada: todavía no mira
    # Con el limón a la vista espera t_mirar; si la misión no hace nada, sigue y no vuelve a frenar por él enseguida
    rec.paso(5.0)                            # hueco de 2 s entre detecciones: igual espera
    assert rec.estado == MIRAR
    rec.al_detecciones(LIMON_UTIL, 6.1)
    rec.paso(6.1)
    assert rec.estado == AVANZAR and abs(rec.x_ignorar - (0.5 + PAR.ignorar)) < 1e-9
    rec.al_detecciones(LIMON_UTIL, 6.3)
    rec.paso(6.3)
    assert rec.estado == AVANZAR


def test_no_se_mueve_mientras_la_mision_trabaja():
    rec, r = mirando()
    rec.al_estado_mision('APROXIMAR', 2.0)
    for t in (2.0, 5.0, 9.0):
        rec.paso(t)
    assert rec.estado == MIRAR and r.de('cmd_vel')[-1] == (0.0, 0.0)


def test_se_arrima_a_un_limon_fuera_de_alcance():
    p = (0.70, 0.40, 0.10)                  # limón 0,70 m adelante del brazo: fuera de alcance
    assert not alcanzable(p)
    dx = desplazamiento_para_alcanzar(p)
    assert dx is not None and dx > 0 and alcanzable((p[0] - dx, p[1], p[2]))
    assert desplazamiento_para_alcanzar((0.0, 1.5, 0.1)) is None   # demasiado lejos a un costado
    rec, r = mirando()
    rec.al_fuera_de_alcance(p, 1.3)
    rec.paso(1.4)
    assert rec.estado == ARRIMAR and abs(rec.x_obj - dx) < 1e-9


def test_fin_de_la_hilera():
    rec, _ = mirando(x=PAR.x_fin + 0.01)
    rec.paso(1.2 + PAR.t_mirar + 0.1)
    assert rec.estado == FIN


def test_obstaculo_en_el_camino_y_lado():
    # Eco del sensor izquierdo a 0,40 m: cae dentro del ancho del robot
    libre, y_min, y_max = obstaculo_en_el_camino((math.inf, 0.40, math.inf), PAR)
    assert 0.39 < libre < 0.41 and y_min < 0.25 < y_max
    # Otro obstáculo 1,5 m más adelante (eco del central) no suma al ancho del primero
    assert obstaculo_en_el_camino((1.95, 0.40, math.inf), PAR)[1] > 0.15
    # Balde a la derecha: el centro del haz cae apenas afuera del ancho, pero el cono no
    assert obstaculo_en_el_camino((math.inf, math.inf, 0.55), PAR)[0] < 1.0
    # Un árbol a un costado (fuera del ancho) no cuenta
    assert obstaculo_en_el_camino((math.inf, math.inf, 3.0), PAR)[0] == math.inf
    assert lado_para_esquivar(0.12, 0.40, PAR) == -1      # obstáculo a la izquierda: por la derecha
    assert lado_para_esquivar(-0.40, -0.12, PAR) == 1
    assert lado_para_esquivar(-0.10, 0.10, PAR) is None   # en el medio: no entra por ningún lado


def test_esquiva_pasa_y_vuelve_al_centro():
    rec, r = mirando(rangos=(math.inf, 0.30, math.inf))
    rec.paso(1.2 + PAR.t_mirar + 0.1)
    assert rec.estado == ESQUIVAR and rec.y_ref == -PAR.y_esquive
    rec.al_rangos(LIBRE, 5.0)
    rec.paso(5.0)
    assert r.de('cmd_vel')[-1][1] < 0          # gira a la derecha
    rec.al_odom(0.3, -PAR.y_esquive, 0.0, 6.0)
    rec.paso(6.0)
    assert rec.estado == PASAR
    rec.al_odom(rec.x_pasar + 0.01, -PAR.y_esquive, 0.0, 9.0)
    rec.paso(9.0)
    assert rec.estado == VOLVER
    rec.al_odom(rec.x_pasar + 0.3, 0.0, 0.15, 12.0)   # en el centro pero torcido: sigue enderezándose
    rec.paso(12.0)
    assert rec.estado == VOLVER
    rec.al_odom(rec.x_pasar + 0.35, 0.0, 0.0, 13.0)
    rec.paso(13.0)
    assert rec.estado == MIRAR


def test_bumper_y_obstaculo_sin_lugar_bloquean():
    rec, r = mirando(rangos=(0.30, math.inf, math.inf))   # justo en el medio
    rec.paso(1.2 + PAR.t_mirar + 0.1)
    assert rec.estado == BLOQUEADO
    rec, r = mirando()
    rec.paso(1.2 + PAR.t_mirar + 0.1)
    assert rec.estado == AVANZAR
    rec.al_bumpers(1, 4.6)
    rec.paso(4.6)
    assert rec.estado == BLOQUEADO and r.de('cmd_vel')[-1] == (0.0, 0.0)


def test_odometria_giro_rumbo_del_giroscopo():
    o = OdometriaGiro()
    o.al_odom(0.0, 0.0, 0.0)
    for k in range(51):                       # 1 s a 0,5 rad/s: rumbo 0,5 rad por el giróscopo
        o.al_giro(0.5, k * 0.02)
    o.al_odom(0.0, 0.0, 0.8)                  # las ruedas patinaron: dicen 0,8 rad, no se usa
    assert abs(o.rumbo - 0.5) < 1e-9
    o.al_odom(0.1 * math.cos(0.8), 0.1 * math.sin(0.8), 0.8)   # avanzó 0,1 m
    assert abs(o.x - 0.1 * math.cos(0.5)) < 1e-9 and abs(o.y - 0.1 * math.sin(0.5)) < 1e-9
    o.al_odom(0.0, 0.0, 0.8)                  # retrocedió 0,1 m
    assert abs(o.x) < 1e-9 and abs(o.y) < 1e-9


def test_retrocede_por_un_limon_que_quedo_atras_con_tope():
    assert limon_atras(LIMON_CIEGO, PAR) and not limon_atras(LIMON_UTIL, PAR)
    rec, r = mirando(x=2.0)
    rec.x_libre_atras = 1.0
    t = 2.0
    destinos = []
    for _ in range(6):                        # el limón sigue en la zona ciega: retrocede de a paso_atras
        rec.al_detecciones(LIMON_CIEGO, t)
        rec.paso(t + PAR.t_quieto + PAR.t_sin_limon + 0.1)
        if rec.estado != ARRIMAR:
            break
        destinos.append(round(rec.x_obj, 2))
        rec.al_odom(rec.x_obj, 0.0, 0.0, t + 1)
        rec.paso(t + 1)
        rec.al_estado_mision('ESPERAR', t + 1)
        t += 2
    assert destinos == [1.9, 1.8, 1.7]        # max_arrimes = 3 (y atras_max = 0,40 no se pasa)
    assert rec.estado == AVANZAR
