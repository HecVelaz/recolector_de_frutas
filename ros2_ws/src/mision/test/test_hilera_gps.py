"""Pruebas de la hilera definida por GPS (sin ROS): colcon test o pytest."""

import math

from mision.hilera_gps import a_local, HileraGps, ParHilera, promediar
from mision.recorrido import INICIO, MIRAR, Recorrido

# Primer fix del 21/10 en la FIUNA; el fin, 30 m al norte
INICIO_GPS = (-25.33147, -57.51654)
FIN_GPS = (INICIO_GPS[0] + math.degrees(30 / 6371000.0), INICIO_GPS[1])


def test_a_local():
    e, n = a_local(*INICIO_GPS, *FIN_GPS)
    assert abs(e) < 1e-6 and abs(n - 30) < 1e-6
    e, n = a_local(*INICIO_GPS, INICIO_GPS[0], INICIO_GPS[1] + 0.0001)
    assert abs(e - 10.05) < 0.05 and abs(n) < 1e-6  # 0,0001° de longitud a 25° S ~ 10 m


def test_promediar():
    assert promediar([]) is None
    lat, lon, s = promediar([(1.0, 2.0, 10.0), (3.0, 4.0, 10.0), (2.0, 3.0, 10.0), (2.0, 3.0, 10.0)])
    assert (lat, lon) == (2.0, 3.0) and s == 5.0


def test_en_inicio_lejos_fix_malo_y_viejo():
    h = HileraGps(ParHilera(inicio=INICIO_GPS, fin=FIN_GPS))
    assert h.definida() and not HileraGps().definida()
    assert h.evaluar(0.0) == (False, 'SIN_FIX')
    lat5 = INICIO_GPS[0] + math.degrees(5 / 6371000.0)
    h.al_fix(lat5, INICIO_GPS[1], 4.0, 10.0)  # 5 m hacia el fin
    ok, texto = h.evaluar(10.5)
    assert ok and texto.startswith('EN_INICIO') and 'avance=5.0/30.0 m' in texto and 'lateral=+0.0' in texto
    assert h.evaluar(14.0) == (False, 'SIN_FIX')  # más de 3 s sin fix
    h.al_fix(lat5, INICIO_GPS[1], 25.0, 20.0)
    assert h.evaluar(20.0)[1].startswith('FIX_MALO')
    h.al_fix(INICIO_GPS[0], INICIO_GPS[1] - 0.0002, 4.0, 30.0)  # ~20 m al oeste: a la izquierda yendo al norte
    ok, texto = h.evaluar(30.0)
    assert not ok and texto.startswith('LEJOS') and 'lateral=+20.1' in texto


def test_recorrido_no_arranca_sin_gps_y_despues_no_lo_mira():
    salidas = []
    rec = Recorrido(lambda tipo, valor: salidas.append((tipo, valor)))
    rec.al_odom(0.0, 0.0, 0.0, 0.0)
    rec.al_estado_mision('ESPERAR', 0.0)
    rec.al_gps(False, 0.0)
    rec.paso(2.0)
    assert rec.estado == INICIO and ('comando_base', 'armar') not in salidas  # ni siquiera arma la base
    rec.al_gps(True, 2.5)
    rec.paso(3.0)
    rec.al_estado_base('ARMADA modo=libre seguridad=ok', 3.1)
    rec.paso(3.2)
    assert rec.estado == MIRAR
    rec.al_gps(False, 3.3)  # ya en la hilera: el GPS no la frena
    rec.paso(3.4)
    assert rec.estado != INICIO
