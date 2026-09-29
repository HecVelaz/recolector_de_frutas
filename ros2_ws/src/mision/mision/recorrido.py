"""Recorrido autónomo de la hilera (sin ROS, se prueba en test/): la base avanza de corrido por el centro del
pasillo y frena cuando YOLO ve un limón en la zona que puede localizar el estéreo (que necesita el robot quieto);
ahí deja mirar a la misión; si la misión ve un limón fuera de alcance, se arrima lo justo; si algo ocupa el pasillo,
lo esquiva por el lado libre con los 3 HC-SR04 del frente y vuelve al centro.

    INICIO -> MIRAR -> AVANZAR (hasta ver un limón útil) -> MIRAR ...                    -> FIN (x >= x_fin)
              MIRAR -> ARRIMAR (limón fuera de alcance) -> MIRAR
              MIRAR -> ESQUIVAR (correrse al costado) -> PASAR -> VOLVER (al centro) -> MIRAR
              BLOQUEADO: no se puede esquivar, bumper apretado o la misión en falla (frena y reintenta)

La base solo se mueve con la misión en ESPERAR (brazo en reposo). Posición por odometría: el robot arranca en el
centro del pasillo mirando a lo largo (odom y = 0 es el centro). Unidades SI, marco odom y marco del robot
(x adelante, y a la izquierda). Entradas: al_odom, al_rangos, al_bumpers, al_estado_base, al_estado_mision,
al_fuera_de_alcance, al_detecciones y paso() periódico. Salidas por enviar(tipo, valor): 'cmd_vel' ((v, w)), 'comando_base' (str)
y 'estado' (texto para /recorrido/estado).
"""

from dataclasses import dataclass
import math

from mision.fsm import alcanzable

INICIO, MIRAR, AVANZAR, ARRIMAR, ESQUIVAR, PASAR, VOLVER, BLOQUEADO, FIN = (
    'INICIO', 'MIRAR', 'AVANZAR', 'ARRIMAR', 'ESQUIVAR', 'PASAR', 'VOLVER', 'BLOQUEADO', 'FIN')

# HC-SR04 (x, y, ángulo) en el marco del robot: frente, izquierda, derecha (urdf de la simulación: MEDIR en el real)
SENSORES = ((0.323, 0.0, 0.0), (0.323, 0.15, math.radians(15)), (0.323, -0.15, math.radians(-15)))


@dataclass
class ParRecorrido:
    v_crucero: float = 0.10     # m/s buscando limones
    v_max: float = 0.12         # m/s
    v_lenta: float = 0.08       # m/s al esquivar
    t_quieto: float = 0.5       # s frenado antes de dejar mirar (el estéreo necesita el robot quieto)
    t_mirar: float = 3.0        # s quieto con un limón a la vista sin novedades de la misión (5 muestras a ~3 Hz)
    t_sin_limon: float = 0.5    # s quieto sin ningún limón útil a la vista antes de seguir
    ignorar: float = 0.15       # m sin frenar por limones después de mirar sin resultado
    paso_atras: float = 0.10    # m para retroceder hacia un limón que quedó atrás (en la zona ciega de la imagen)
    atras_max: float = 0.40     # m que puede retroceder por tramo (atrás no hay sensores)
    # Zona útil del estéreo en la imagen izquierda (calibración v1): u >= 271 px y 0,40-0,95 m, con la distancia
    # estimada por el ancho de la caja de YOLO
    f_px: float = 1076.5
    u_min: float = 271.0
    z_min: float = 0.40
    z_max: float = 0.95
    diametro_limon: float = 0.06
    x_fin: float = 7.3          # m: fin de la hilera
    frente: float = 0.315       # m del eje de tracción al frente de la caja
    atras: float = 0.085        # m del eje a la cola
    medio_ancho: float = 0.2225  # m, de centro a borde de rueda
    margen: float = 0.05        # m de aire a cada lado al pasar
    y_esquive: float = 0.25     # m: carril para esquivar (más afuera, las copas: a 0,48 m del centro)
    d_libre: float = 0.30       # m libres delante de la caja para avanzar o arrimarse (la base frena sola a 0,20);
                                # si no, se esquiva desde ahí
    largo_obst: float = 0.30    # m: largo máximo supuesto de un obstáculo (el ultrasonido solo ve su cara)
    k_y: float = 6.0            # 1/m: rumbo = atan(k_y * error lateral)
    rumbo_max: float = 1.0      # rad: cerrado, para correrse y volver en poco avance (con 0,6 volver al centro
                                # llevaba 0,7 m y pasaba los limones del árbol siguiente sin mirar)
    k_rumbo: float = 2.5        # 1/s
    w_max: float = 1.0          # rad/s (límite de la base)
    tol_x: float = 0.01         # m
    tol_y: float = 0.03         # m
    tol_rumbo: float = 0.05     # rad: al terminar un corrimiento, derecho (la cámara mira de costado: torcida unos
                                # grados, el limón siguiente quedaba fuera de la zona útil de la imagen)
    max_arrimes: int = 3        # arrimes seguidos sin cosechar antes de seguir de largo
    largo_herramienta: float = 0.0  # el de brazo_ik


MEDIO_CONO = math.radians(7.5)  # HC-SR04: el eco puede venir de cualquier punto del cono


def obstaculo_en_el_camino(rangos, par):
    """(frente, izq, der) [m] -> (distancia libre delante de la caja, y mínima, y máxima) de los ecos que caen
    dentro del ancho del robot más el margen, o (inf, None, None). Las y abarcan todo el cono de cada eco (peor
    caso) y solo de los ecos del obstáculo más cercano (hasta largo_obst detrás del primero: uno más lejos no suma a
    su ancho). Los ecos fuera del camino (árboles, copas) no cuentan."""
    ecos = []
    for (sx, sy, a), r in zip(SENSORES, rangos):
        if r is None or not math.isfinite(r):
            continue
        hx, hy, m = sx + r * math.cos(a), sy + r * math.sin(a), r * math.tan(MEDIO_CONO)
        # Cuenta si cualquier parte del cono cae en el camino: con el centro del haz afuera, el balde chocaba el costado
        if abs(hy) - m <= par.medio_ancho + par.margen:
            ecos.append((hx - par.frente, hy, m))
    if not ecos:
        return math.inf, None, None
    libre = min(e[0] for e in ecos)
    cerca = [e for e in ecos if e[0] <= libre + par.largo_obst]
    return libre, min(hy - m for _, hy, m in cerca), max(hy + m for _, hy, m in cerca)


def lado_para_esquivar(y_min, y_max, par):
    """Obstáculo entre y_min e y_max -> +1 (por la izquierda), -1 (por la derecha) o None si no hay lugar en el
    carril de esquive (y = ±y_esquive). Con lugar a los dos lados, el de más aire."""
    aire = {-1: y_min - (-par.y_esquive + par.medio_ancho), 1: (par.y_esquive - par.medio_ancho) - y_max}
    lado = max(aire, key=aire.get)
    return lado if aire[lado] >= par.margen else None


def limon_util(cajas, par):
    """Cajas de YOLO [(u, ancho) px] -> ¿alguna en la zona que puede localizar el estéreo?"""
    return any(u >= par.u_min and w > 0 and par.z_min <= par.f_px * par.diametro_limon / w <= par.z_max
               for u, w in cajas)


def limon_atras(cajas, par):
    """¿Alguna caja en la zona ciega del estéreo (u < u_min: con la cámara mirando de costado, un limón que ya quedó
    atrás) a una distancia a la que se podría alcanzar?"""
    return any(u < par.u_min and w > 0 and par.z_min <= par.f_px * par.diametro_limon / w <= par.z_max + 0.2
               for u, w in cajas)


def desplazamiento_para_alcanzar(p, largo_herramienta=0.0, margen=0.02, d_max=0.6):
    """Limón p (marco del brazo) -> cuánto avanzar [m] (negativo = retroceder) para alcanzarlo con margen, el menor
    posible (así sigue a la vista); None si no se alcanza moviéndose a lo largo del pasillo."""
    cands = [k / 100 for k in range(-round(d_max * 100), round(d_max * 100) + 1)]
    ok = [dx for dx in cands
          if all(alcanzable((p[0] - dx + e, p[1], p[2]), largo_herramienta) for e in (-margen, 0.0, margen))]
    return min(ok, key=abs) if ok else None


class OdometriaGiro:
    """Pose para el recorrido: el avance lo dan las ruedas (/odom) y el rumbo, el giróscopo (/imu, z). En un giro
    fuerte las ruedas patinan y su rumbo se desvía (simulación: tras esquivar la caja, 10 cm de error lateral y el
    robot corrido sin enterarse); el giróscopo no patina. En el real, calibrar su sesgo en reposo (`cal` de la base)."""

    def __init__(self):
        self.x = self.y = self.rumbo = 0.0
        self.t_giro = None
        self.odom_prev = None

    def al_giro(self, wz, t):
        if self.t_giro is not None and 0.0 < t - self.t_giro < 0.5:
            self.rumbo = math.atan2(math.sin(self.rumbo + wz * (t - self.t_giro)),
                                    math.cos(self.rumbo + wz * (t - self.t_giro)))
        self.t_giro = t

    def al_odom(self, x, y, rumbo_odom):
        """Pose de /odom: se usa solo cuánto avanzó (con signo, a lo largo de su propio rumbo)."""
        if self.odom_prev is not None:
            px, py, pr = self.odom_prev
            ds = (x - px) * math.cos(pr) + (y - py) * math.sin(pr)
            self.x += ds * math.cos(self.rumbo)
            self.y += ds * math.sin(self.rumbo)
        self.odom_prev = (x, y, rumbo_odom)


class Recorrido:

    def __init__(self, enviar, par=None):
        self.enviar = enviar
        self.par = par or ParRecorrido()
        self.estado = INICIO
        self.t0 = 0.0
        self.pose = None            # (x, y, rumbo) odom
        self.rangos = (None, None, None)
        self.bumpers = 0
        self.base_armada = False
        self.mision = 'INICIO'
        self.x_obj = 0.0
        self.y_ref = 0.0
        self.x_pasar = 0.0
        self.arrimes = 0
        self.dx_pendiente = None
        self.t_parado = None        # desde cuándo la base está frenada
        self.t_visto = None         # última detección útil de YOLO
        self.x_ignorar = -math.inf  # hasta dónde no frenar por limones (ya se miró ahí)
        self.t_atras = None         # última caja de un limón que quedó atrás
        self.x_libre_atras = 0.0    # hasta dónde se sabe libre para retroceder (el arranque o el fin del último esquive)
        self.x_atras = -math.inf    # dónde empezó a retroceder en este tramo (hasta atras_max desde ahí)

    # --- entradas
    def al_odom(self, x, y, rumbo, t):
        self.pose = (x, y, rumbo)

    def al_rangos(self, rangos, t):
        self.rangos = tuple(rangos)

    def al_bumpers(self, bits, t):
        self.bumpers = bits

    def al_estado_base(self, texto, t):
        self.base_armada = texto.startswith('ARMADA')

    def al_estado_mision(self, estado, t):
        """Estado de la máquina de la misión (Mision.estado)."""
        self.mision = estado
        if estado in ('AGARRAR', 'SOLTAR'):
            self.arrimes = 0  # cosechó: los arrimes vuelven a contar desde cero

    def al_detecciones(self, cajas, t):
        """Cajas de YOLO [(u, ancho) px] de la imagen izquierda (salen también en movimiento)."""
        if limon_util(cajas, self.par):
            self.t_visto = t
        if limon_atras(cajas, self.par):
            self.t_atras = t

    def _visto(self, t):
        return self.t_visto is not None and t - self.t_visto <= 0.5

    def al_fuera_de_alcance(self, p, t):
        """La misión vio quieto un limón (marco del brazo) que no alcanza."""
        if self.estado == MIRAR:
            self.dx_pendiente = desplazamiento_para_alcanzar(p, self.par.largo_herramienta)
            if self.dx_pendiente is None:
                self.enviar('estado', 'MIRAR: limón inalcanzable desde el pasillo, sigo')

    def base_quieta(self, t):
        """¿Puede mirar la misión? Base frenada hace más de t_quieto."""
        return self.estado == MIRAR and self.t_parado is not None and t - self.t_parado >= self.par.t_quieto

    # --- lógica
    def _ir(self, estado, t, motivo=''):
        self.estado, self.t0 = estado, t
        self.enviar('estado', estado + (f': {motivo}' if motivo else ''))

    def _frenar(self, t):
        if self.t_parado is None:
            self.t_parado = t
        self.enviar('cmd_vel', (0.0, 0.0))

    def _conducir(self, v, y_ref):
        """Avanza a v siguiendo la recta y = y_ref (rumbo a lo largo del pasillo)."""
        self.t_parado = None
        _, y, rumbo = self.pose
        rumbo_ref = math.copysign(1.0, v) * max(-self.par.rumbo_max,
                                                min(self.par.rumbo_max, math.atan(self.par.k_y * (y_ref - y))))
        err = math.atan2(math.sin(rumbo_ref - rumbo), math.cos(rumbo_ref - rumbo))
        w = max(-self.par.w_max, min(self.par.w_max, self.par.k_rumbo * err))
        self.enviar('cmd_vel', (v, w))

    def _hacia_x(self, x_obj, y_ref, v_max):
        """Hacia x_obj por la recta y_ref; True al llegar."""
        falta = x_obj - self.pose[0]
        if abs(falta) <= self.par.tol_x:
            return True
        v = math.copysign(max(0.03, min(v_max, 1.5 * abs(falta))), falta)
        self._conducir(v, y_ref)
        return False

    def _libre(self):
        return obstaculo_en_el_camino(self.rangos, self.par)

    def paso(self, t):
        if self.estado == FIN:
            return self._frenar(t)
        if self.estado == INICIO:
            self._frenar(t)
            if self.pose is None:
                return
            if not self.base_armada:
                if t - self.t0 >= 1.0:  # reintentar cada segundo hasta ver ARMADA
                    self.enviar('comando_base', 'armar')
                    self.t0 = t
                return
            return self._ir(MIRAR, t)
        if self.mision == 'FALLA' and self.estado != BLOQUEADO:
            self._frenar(t)
            return self._ir(BLOQUEADO, t, 'misión en FALLA')
        # La base solo se mueve con el brazo en reposo
        if self.mision != 'ESPERAR':
            self._frenar(t)
            if self.estado != MIRAR:
                self._ir(MIRAR, t, 'la misión está trabajando')
            self.t0 = t
            return
        if self.bumpers and self.estado not in (MIRAR, BLOQUEADO):
            self._frenar(t)
            return self._ir(BLOQUEADO, t, f'bumper apretado ({self.bumpers})')

        x, y, rumbo = self.pose
        libre, y_min, y_max = self._libre()
        p = self.par
        if self.estado == MIRAR:
            self._frenar(t)
            if self.dx_pendiente is not None:
                dx, self.dx_pendiente = self.dx_pendiente, None
                if self.arrimes >= p.max_arrimes:
                    self.enviar('estado', f'MIRAR: {self.arrimes} arrimes sin cosechar, sigo')
                elif dx > 0 and libre - dx < p.d_libre:
                    self.enviar('estado', 'MIRAR: no me puedo arrimar, obstáculo adelante')
                else:
                    self.arrimes += 1
                    self.x_obj = x + dx
                    return self._ir(ARRIMAR, t, f'{dx:+.2f} m hasta x = {self.x_obj:.2f}')
            if not self.base_quieta(t):
                return
            # Con un limón útil visto desde que frenó se le da tiempo a la misión; sin ninguno, se sigue enseguida.
            # "Desde que frenó" y no "en el último instante": un hueco entre detecciones lo hacía seguir de largo
            visto = self.t_visto is not None and self.t_visto >= self.t0 - 0.5
            if t - self.t0 < (p.t_mirar if visto else p.t_quieto + p.t_sin_limon):
                return
            if visto:
                self.x_ignorar = x + p.ignorar
            # Un limón que quedó atrás (p. ej. al volver de un esquive): retroceder hasta verlo en la zona útil
            atras = self.t_atras is not None and self.t_atras >= self.t0 - 0.5
            if atras and not visto and self.arrimes < p.max_arrimes:
                if x > self.x_atras + 0.5:   # tramo nuevo: desde acá se cuentan los atras_max
                    self.x_atras = x
                destino = x - p.paso_atras
                if destino >= max(self.x_libre_atras, self.x_atras - p.atras_max):
                    self.arrimes += 1
                    self.x_obj = destino
                    return self._ir(ARRIMAR, t, f'limón atrás: retrocedo a x = {destino:.2f}')
            if x >= p.x_fin:
                return self._ir(FIN, t, f'fin de la hilera en x = {x:.2f} m')
            if libre >= p.d_libre + 0.05:
                self.arrimes = 0
                return self._ir(AVANZAR, t)
            lado = lado_para_esquivar(y_min, y_max, p)
            donde = f'obstáculo a {libre:.2f} m, y de {y_min:+.2f} a {y_max:+.2f}'
            if lado is None:
                return self._ir(BLOQUEADO, t, donde + ': no hay lugar para esquivarlo')
            self.y_ref = lado * p.y_esquive
            self.x_pasar = x + p.frente + libre + p.largo_obst + p.atras + 0.10
            return self._ir(ESQUIVAR, t, donde + f': paso por {"la izquierda" if lado > 0 else "la derecha"}')
        if self.estado == AVANZAR:
            if libre < p.d_libre:
                self._frenar(t)
                return self._ir(MIRAR, t, f'obstáculo a {libre:.2f} m')
            if self._visto(t) and x > self.x_ignorar:
                self._frenar(t)
                return self._ir(MIRAR, t, 'limón a la vista')
            if x >= p.x_fin:
                self._frenar(t)
                return self._ir(MIRAR, t)
            return self._conducir(p.v_crucero, 0.0)
        if self.estado == ARRIMAR:
            if self.x_obj > x and libre < p.d_libre - 0.05:
                self._frenar(t)
                return self._ir(MIRAR, t, 'obstáculo al arrimarme')
            if self._hacia_x(self.x_obj, 0.0, p.v_max):
                self._frenar(t)
                return self._ir(MIRAR, t)
            return
        if self.estado in (ESQUIVAR, PASAR, VOLVER):
            if libre < 0.12:
                self._frenar(t)
                return self._ir(BLOQUEADO, t, f'obstáculo a {libre:.2f} m al esquivar')
            if self.estado == ESQUIVAR:
                self._conducir(p.v_lenta, self.y_ref)
                if abs(y - self.y_ref) <= p.tol_y and abs(rumbo) <= p.tol_rumbo:
                    self._ir(PASAR, t, f'hasta x = {self.x_pasar:.2f}')
            elif self.estado == PASAR:
                self._conducir(p.v_max, self.y_ref)
                if x >= self.x_pasar:
                    self.x_libre_atras = self.x_pasar - 0.10
                    self._ir(VOLVER, t)
            else:
                self._conducir(p.v_lenta, 0.0)
                if abs(y) <= p.tol_y and abs(rumbo) <= p.tol_rumbo:
                    self._frenar(t)
                    self._ir(MIRAR, t)
            return
        if self.estado == BLOQUEADO:
            self._frenar(t)
            if t - self.t0 >= 3.0 and self.mision != 'FALLA' and not self.bumpers:
                self._ir(MIRAR, t, 'reintento')
