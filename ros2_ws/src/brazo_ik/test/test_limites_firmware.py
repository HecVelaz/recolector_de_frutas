"""Los límites de cinematica.py y los de firmware/brazo/include/brazo_config.h tienen que ser los mismos.

Hasta el 18/10 solo lo pedía un comentario, y se desincronizaron (balancín de 40 mm en Python, γ₄ sin verificar en el
firmware). Lee los números del .h y los compara."""

import math
from pathlib import Path
import re

import pytest

from brazo_ik.cinematica import cuatro_barras_directo, GAMMA4_LIM, MU_MIN, Q1_LIM, Q2_LIM, Q3_LIM

CONFIG = Path(__file__).resolve().parents[4] / 'firmware' / 'brazo' / 'include' / 'brazo_config.h'


def _config():
    if not CONFIG.exists():
        pytest.skip(f'sin {CONFIG} (copia del paquete sin el firmware)')
    return re.sub(r'//[^\n]*', '', CONFIG.read_text(encoding='utf-8'))


def _num(texto):
    return float(texto.strip().rstrip('f'))


def test_limites_articulares_iguales():
    texto = _config()
    lims = {}
    for n, cuerpo in re.findall(r'\{\s*"J(\d)"\s*,(.*?)\}', texto, re.DOTALL):
        valores = [v for v in cuerpo.split(',') if v.strip()]
        # ConfigArticulacion: cuentasPorVuelta, relacion, rpmMax, qMin, qMax, ...
        lims[int(n)] = (_num(valores[3]), _num(valores[4]))
    assert lims == {1: Q1_LIM, 2: Q2_LIM, 3: Q3_LIM}


def test_rango_de_gamma4_igual_al_de_mu_min():
    texto = _config()
    g_min = _num(re.search(r'GAMMA4_MIN\s*=\s*([-\d.]+f?)', texto).group(1))
    g_max = _num(re.search(r'GAMMA4_MAX\s*=\s*([-\d.]+f?)', texto).group(1))
    # El rango donde el cuatro barras cierra con μ entre MU_MIN y 180° - MU_MIN, con la geometría de cinematica.py
    validos = []
    for d in range(int(GAMMA4_LIM[0] * 10), int(GAMMA4_LIM[1] * 10) + 1):
        r = cuatro_barras_directo(math.radians(d / 10))
        if r and MU_MIN <= math.degrees(r[1]) <= 180 - MU_MIN:
            validos.append(d / 10)
    # El firmware lo redondea al grado
    assert abs(min(validos) - g_min) < 0.5 and abs(max(validos) - g_max) < 0.5
