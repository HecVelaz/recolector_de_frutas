"""Máquina de estados de la misión mínima (sin ROS, se prueba en test/): detectar -> localizar quieto -> agarrar.

    INICIO -> ESPERAR -> APROXIMAR -> AGARRAR -> RETIRAR -> SOLTAR -> ESPERAR ...
                              \\____________ FALLA (detiene el brazo y se queda ahí) ___/

Entradas (con el tiempo t en s): al_limon() con el centro del limón ya en el marco del brazo [m] y el tiempo de su
imagen, al_estado_brazo() con el texto de /brazo/estado, al_ik() con el de /brazo/ik_estado, al_joint_cmd() con los
ángulos que calculó brazo_ik, al_joints() con /brazo/joint_states y paso() periódico.
"Llegó" = posición medida igual a la que calculó brazo_ik para ESTE objetivo, quieta, y el firmware dice llego: un
estado viejo no alcanza (la posición de un movimiento anterior no coincide con el objetivo nuevo).
Salidas por enviar(tipo, valor): 'comando' (str a /brazo/comando), 'objetivo' ((x, y, z) m a /brazo/objetivo),
'cierre' (% a /pinza/cierre), 'estado' (texto para /mision/estado) y 'fuera_de_alcance' ((x, y, z) m del limón que
vio quieto y no alcanza: el recorrido autónomo se arrima). Con el recorrido, `base_quieta` dice si se puede mirar.
"""

from dataclasses import dataclass
import math
import re

from brazo_ik.cinematica import cinematica_inversa, muneca_desde_herramienta

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
    tol_q: float = 0.0175        # rad (1°) entre la posición medida y la de brazo_ik (el firmware frena a 0,5°)
    tol_v: float = 0.02          # rad/s para considerarlo quieto
    cierre: float = 100.0        # % de cierre para agarrar (MEDIR con un limón: sin aplastarlo)
    # m, TCP donde lleva y suelta el limón: q = (75°, 110°, -30°), el reposo de la simulación (no tapa las cámaras ni
    # toca el mástil). El de antes, al frente (q1 = 0°), quedó fuera del rango de J1 (45..225°)
    reposo: tuple = (0.06789, 0.25336, 0.35960)
    largo_herramienta: float = 0.0  # m, muñeca -> TCP en horizontal: el mismo que brazo_ik (MEDIR en el real)


def centro_desde_superficie(p, radio):
    """Punto de la superficie visto desde la cámara (marco de la cámara) -> centro, alejándolo `radio` sobre el rayo."""
    d = math.sqrt(sum(c * c for c in p))
    return tuple(c * (1.0 + radio / d) for c in p) if d > 0 else tuple(p)


def alcanzable(p, largo_herramienta=0.0):
    """¿brazo_ik resuelve este TCP? (misma cuenta que el nodo: TCP -> muñeca -> cinemática inversa)."""
    m = muneca_desde_herramienta(*p, largo_herramienta)
    return m is not None and bool(cinematica_inversa(m[0] * 1000.0, m[1] * 1000.0, m[2] * 1000.0)[0])


def leer_estado_brazo(texto):
    """Texto de /brazo/estado -> (armado, llegaron las 3, fallas distintas de 'ninguna' o articulaciones sin cero)."""
    fallas = [f for f in re.findall(r'falla=(.*?)(?: llego)?;', texto) if f != 'ninguna']
    if texto.count(' cero ') < 3:
        fallas.append('sin cero')
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
        self.q_obj = None         # ángulos de brazo_ik para el objetivo vigente [rad]
        self.q, self.v = None, None  # /brazo/joint_states
        self.base_quieta = True   # False mientras el recorrido mueve la base: el estéreo necesita el robot quieto

    def _ir(self, estado, t, motivo=''):
        self.estado, self.t0 = estado, t
        self.enviar('estado', estado + (f': {motivo}' if motivo else ''))

    def _fallar(self, t, motivo):
        self.enviar('comando', 's')  # detener J1-J3; la pinza queda como está para no soltar el limón
        self._ir(FALLA, t, motivo)

    def _fresco(self, t):
        return self.t_brazo is not None and t - self.t_brazo <= self.par.t_estado_max

    def _mover(self, p, estado, t):
        self.q_obj = None
        self.enviar('objetivo', p)
        self._ir(estado, t, 'objetivo ({:.3f}, {:.3f}, {:.3f}) m'.format(*p))

    def al_estado_brazo(self, texto, t):
        self.brazo, self.t_brazo = leer_estado_brazo(texto), t
        armado, _, fallas = self.brazo
        # En el callback y no en paso(): un estado bueno posterior no tiene que tapar la falla
        if self.estado in (APROXIMAR, AGARRAR, RETIRAR, SOLTAR) and (fallas or not armado):
            self._fallar(t, 'brazo ' + (', '.join(fallas) if fallas else 'desarmado'))

    def al_joint_cmd(self, q, t):
        if self.estado in (APROXIMAR, RETIRAR) and self.q_obj is None:
            self.q_obj = list(q)

    def al_joints(self, q, v, t):
        self.q, self.v = list(q), list(v)

    def _llego(self):
        return (self.q_obj is not None and self.q is not None and self.brazo[1]
                and all(abs(a - b) <= self.par.tol_q for a, b in zip(self.q, self.q_obj))
                and all(abs(w) <= self.par.tol_v for w in self.v))

    def al_ik(self, texto, t):
        if self.estado in (APROXIMAR, RETIRAR) and texto.startswith('inalcanzable'):
            self._fallar(t, texto)

    def al_limon(self, p, t_img, t):
        """p: centro en el marco del brazo; t_img: tiempo de la imagen (ventana de muestras); t: ahora."""
        armado, llego, fallas = self.brazo
        if self.estado != ESPERAR or not self._fresco(t) or not armado or not llego or fallas or not self.base_quieta:
            # sin brazo listo y quieto no se junta nada (p. ej. tras reconectar queda desarmado)
            self.muestras = []
            return
        n = self.par.n_muestras
        self.muestras = [(tm, pm) for tm, pm in self.muestras if t_img - tm <= self.par.ventana]
        self.muestras = (self.muestras[-(n - 1):] if n > 1 else []) + [(t_img, p)]
        if len(self.muestras) < self.par.n_muestras:
            return
        prom = tuple(sum(pm[k] for _, pm in self.muestras) / len(self.muestras) for k in range(3))
        if any(math.dist(pm, prom) > self.par.tol_muestras for _, pm in self.muestras):
            return  # todavía se mueve (o el estéreo salta): seguir juntando
        self.muestras = []
        if not alcanzable(prom, self.par.largo_herramienta):
            self.enviar('estado', 'ESPERAR: limón fuera de alcance en ({:.3f}, {:.3f}, {:.3f}) m'.format(*prom))
            self.enviar('fuera_de_alcance', prom)
            return
        self._mover(prom, APROXIMAR, t)

    def paso(self, t):
        armado = self.brazo[0]
        if self.estado == FALLA:
            return
        if self.estado == INICIO:
            if not self._fresco(t):
                return
            if not armado:
                if t - self.t0 >= 1.0:  # reintentar cada segundo hasta ver ARMADO
                    self.enviar('comando', 'armar')
                    self.t0 = t
                return
            self.enviar('cierre', 0.0)
            self._ir(ESPERAR, t)
            return
        if self.estado != ESPERAR and not self._fresco(t):
            return self._fallar(t, 'sin /brazo/estado')
        if self.estado in (APROXIMAR, RETIRAR):
            if self._llego():
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
