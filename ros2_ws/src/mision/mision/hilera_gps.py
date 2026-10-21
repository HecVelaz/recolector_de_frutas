"""Hilera definida por GPS (guía R2, N1), sin ROS: dos puntos medidos con el GPS antes de la demo (inicio y fin de la
hilera) y, con cada fix, a qué distancia del inicio está el robot y dónde cae sobre la línea inicio -> fin.

El GPS (UP501, σ de 3 a 20 m) no alcanza para seguir el pasillo: eso lo hace el recorrido con odometría, giróscopo y
visión. Acá solo decide si el robot está en el inicio de la hilera para arrancar el recorrido autónomo, y da el
avance y el corrimiento lateral para el registro (rosbag) y el mapa de la app.
"""

from dataclasses import dataclass
import math

R_TIERRA = 6371000.0  # m


def a_local(lat0, lon0, lat, lon):
    """(este, norte) [m] de (lat, lon) respecto de (lat0, lon0), en grados. Plano tangente: sobra para una hilera."""
    este = math.radians(lon - lon0) * R_TIERRA * math.cos(math.radians(lat0))
    norte = math.radians(lat - lat0) * R_TIERRA
    return este, norte


def promediar(fixes):
    """[(lat, lon, σ)] -> (lat, lon, σ del promedio) o None: para marcar el inicio y el fin con el robot quieto.
    σ del promedio = σ medio / √n (optimista: los errores del GPS están correlacionados en el tiempo)."""
    if not fixes:
        return None
    n = len(fixes)
    return (sum(f[0] for f in fixes) / n, sum(f[1] for f in fixes) / n,
            sum(f[2] for f in fixes) / n / math.sqrt(n))


@dataclass
class ParHilera:
    inicio: tuple = (math.nan, math.nan)  # (lat, lon) en grados; nan = sin hilera definida
    fin: tuple = (math.nan, math.nan)
    radio_inicio: float = 10.0  # m: más cerca que esto del inicio cuenta como "en el inicio"
    sigma_max: float = 20.0     # m: con un fix peor no se decide nada (el 21/10, con 3 satélites, dio ~21 m)
    edad_max: float = 3.0       # s: el driver publica a 1 Hz


class HileraGps:

    def __init__(self, par=None):
        self.par = par or ParHilera()
        self.fix = None  # (lat, lon, σ, t)

    def definida(self):
        return all(math.isfinite(v) for v in self.par.inicio)

    def al_fix(self, lat, lon, sigma, t):
        """Fix válido (status >= 0) con su σ horizontal [m]."""
        self.fix = (lat, lon, sigma, t)

    def evaluar(self, t):
        """-> (en_inicio, texto para /hilera/estado)."""
        if self.fix is None or t - self.fix[3] > self.par.edad_max:
            return False, 'SIN_FIX'
        lat, lon, sigma, _ = self.fix
        e, n = a_local(*self.par.inicio, lat, lon)
        d = math.hypot(e, n)
        texto = f'd_inicio={d:.1f} m σ={sigma:.1f} m'
        if all(math.isfinite(v) for v in self.par.fin):
            fe, fn = a_local(*self.par.inicio, *self.par.fin)
            largo = math.hypot(fe, fn)
            if largo > 0:
                avance = (e * fe + n * fn) / largo
                lateral = (fe * n - fn * e) / largo  # + a la izquierda de inicio -> fin
                texto += f' avance={avance:.1f}/{largo:.1f} m lateral={lateral:+.1f} m'
        if not sigma <= self.par.sigma_max:
            return False, f'FIX_MALO {texto} (σ máx {self.par.sigma_max:.0f} m)'
        if d > self.par.radio_inicio:
            return False, f'LEJOS {texto} (radio {self.par.radio_inicio:.0f} m)'
        return True, f'EN_INICIO {texto}'
