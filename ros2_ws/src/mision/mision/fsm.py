"""Máquina de estados de la misión mínima (sin ROS, se prueba en test/): detectar -> localizar quieto -> agarrar.

    INICIO -> ESPERAR -> APROXIMAR -> AGARRAR -> RETIRAR -> SOLTAR -> ESPERAR ...
                              \\____________ FALLA (detiene el brazo y se queda ahí) ___/

Entradas (con el tiempo t en s): al_limon() con el centro del limón ya en el marco del brazo [m], al_estado_brazo()
con el texto de /brazo/estado, al_ik() con el de /brazo/ik_estado, y paso() periódico.
Salidas por enviar(tipo, valor): 'comando' (str a /brazo/comando), 'objetivo' ((x, y, z) m a /brazo/objetivo),
'cierre' (% a /pinza/cierre) y 'estado' (texto para /mision/estado).
"""

from dataclasses import dataclass
import math
import re

from brazo_ik.cinematica import cinematica_inversa

INICIO, ESPERAR, APROXIMAR, AGARRAR, RETIRAR, SOLTAR, FALLA = (
    'INICIO', 'ESPERAR', 'APROXIMAR', 'AGARRAR', 'RETIRAR', 'SOLTAR', 'FALLA')


@dataclass
class Parametros:
    n_muestras: int = 5          # posiciones seguidas que tienen que coincidir (el localizador da ~2-4 Hz)
    tol_muestras: float = 0.02   # m: cada muestra a menos de esto del promedio
    ventana: float = 3.0         # s: las muestras más viejas se descartan
    t_mov_max: float = 20.0      # s para llegar a un objetivo (J2/J3 con sin fin son lentos: MEDIR)
    t_pinza: float = 1.5         # s para cerrar o abrir la pinza
    t_estado_max: float = 2.0    # s sin /brazo/estado (sale a 2 Hz) -> enlace caído
    cierre: float = 100.0        # % de cierre para agarrar (MEDIR con un limón: sin aplastarlo)
    reposo: tuple = (0.36832, 0.0, 0.09103)  # m, donde lleva y suelta el limón (ejemplo E4: q = 0°, 45°, 0°)


def centro_desde_superficie(p, radio):
    """Punto de la superficie visto desde la cámara (marco de la cámara) -> centro, alejándolo `radio` sobre el rayo."""
    d = math.sqrt(sum(c * c for c in p))
    return tuple(c * (1.0 + radio / d) for c in p) if d > 0 else tuple(p)


def alcanzable(p):
    return bool(cinematica_inversa(p[0] * 1000.0, p[1] * 1000.0, p[2] * 1000.0)[0])


def leer_estado_brazo(texto):
    """Texto de /brazo/estado -> (armado, llegaron las 3, fallas distintas de 'ninguna')."""
    fallas = [f for f in re.findall(r'falla=(.*?)(?: llego)?;', texto) if f != 'ninguna']
    return texto.startswith('ARMADO'), texto.count(' llego;') == 3, fallas


class Mision:

    def __init__(self, enviar, par=None):
        self.enviar = enviar
        self.par = par or Parametros()
        self.estado = INICIO
        self.t0 = 0.0             # entrada al estado actual
        self.muestras = []        # (t, p)
        self.brazo = (False, False, [])
        self.t_brazo = None       # último /brazo/estado
        self.se_movio = False     # vio al brazo sin "llego" después de mandarle el objetivo
        self.objetivo = None

    def _ir(self, estado, t, motivo=''):
        self.estado, self.t0 = estado, t
        self.enviar('estado', estado + (f': {motivo}' if motivo else ''))

    def _fallar(self, t, motivo):
        self.enviar('comando', 's')  # detener J1-J3; la pinza queda como está para no soltar el limón
        self._ir(FALLA, t, motivo)

    def _mover(self, p, estado, t):
        self.se_movio = False
        self.enviar('objetivo', p)
        self._ir(estado, t, 'objetivo ({:.3f}, {:.3f}, {:.3f}) m'.format(*p))

    def al_estado_brazo(self, texto, t):
        self.brazo, self.t_brazo = leer_estado_brazo(texto), t
        if not self.brazo[1]:
            self.se_movio = True

    def al_ik(self, texto, t):
        if self.estado in (APROXIMAR, RETIRAR) and texto.startswith('inalcanzable'):
            self._fallar(t, texto)

    def al_limon(self, p, t):
        armado, _, fallas = self.brazo
        if self.estado != ESPERAR or not armado or fallas:
            return  # sin brazo listo no se manda nada (p. ej. tras reconectar queda desarmado)
        self.muestras = [(tm, pm) for tm, pm in self.muestras if t - tm <= self.par.ventana][-(self.par.n_muestras - 1):]
        self.muestras.append((t, p))
        if len(self.muestras) < self.par.n_muestras:
            return
        prom = tuple(sum(pm[k] for _, pm in self.muestras) / len(self.muestras) for k in range(3))
        if any(math.dist(pm, prom) > self.par.tol_muestras for _, pm in self.muestras):
            return  # todavía se mueve (o el estéreo salta): seguir juntando
        self.muestras = []
        if not alcanzable(prom):
            self.enviar('estado', 'ESPERAR: limón fuera de alcance en ({:.3f}, {:.3f}, {:.3f}) m'.format(*prom))
            return
        self.objetivo = prom
        self._mover(prom, APROXIMAR, t)

    def paso(self, t):
        armado, llego, fallas = self.brazo
        if self.estado == FALLA:
            return
        if self.estado == INICIO:
            if self.t_brazo is None:
                return
            if not armado:
                if t - self.t0 >= 1.0:  # reintentar cada segundo hasta ver ARMADO
                    self.enviar('comando', 'armar')
                    self.t0 = t
                return
            self.enviar('cierre', 0.0)
            self._ir(ESPERAR, t)
            return
        if self.estado != ESPERAR and t - self.t_brazo > self.par.t_estado_max:
            return self._fallar(t, 'sin /brazo/estado')
        if self.estado != ESPERAR and (fallas or not armado):
            return self._fallar(t, 'brazo ' + (', '.join(fallas) if fallas else 'desarmado'))
        if self.estado in (APROXIMAR, RETIRAR):
            if self.se_movio and llego:
                if self.estado == APROXIMAR:
                    self.enviar('cierre', self.par.cierre)
                    self._ir(AGARRAR, t)
                else:
                    self.enviar('cierre', 0.0)
                    self._ir(SOLTAR, t)
            elif t - self.t0 > self.par.t_mov_max:
                self._fallar(t, f'no llegó en {self.par.t_mov_max:.0f} s')
        elif self.estado == AGARRAR and t - self.t0 >= self.par.t_pinza:
            self._mover(self.par.reposo, RETIRAR, t)
        elif self.estado == SOLTAR and t - self.t0 >= self.par.t_pinza:
            self.muestras = []
            self._ir(ESPERAR, t)
