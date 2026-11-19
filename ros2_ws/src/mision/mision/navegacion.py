"""Navegación de la demo con un banderín ArUco y una hilera de arbolitos (sin ROS, se prueba en test/).

    INICIO -> BUSCAR -> UBICAR -> IR_A_PARADA (árbol 1) -> COSECHAR -> AVANZAR -> COSECHAR ... (último árbol)
              lados=2: -> VUELTA_U (rodea el último árbol, antihorario) -> COSECHAR -> AVANZAR ... (árbol 1)
              -> CIERRE (a mirar el banderín) -> BUSCAR -> UBICAR -> FIN (error acumulado de la odometría)
              FALLA: el camino pasa J1 a menos de sep_min del banderín o de un tronco, no vio el banderín en 360°

- BUSCAR: mira t_buscar s quieto; si no ve el banderín, gira paso_buscar a la izquierda (giróscopo), hasta 360°.
- UBICAR: mediana de t_ubicar s de la pose del banderín -> banderín y árboles en `odom` (hilera: lo medido con cinta
  mirando la marca de frente, como 27-aruco-arbol/banderin.json de pruebas-esp32).
- Movimientos: girar hacia el destino (giróscopo), avanzar (ruedas, tramos <= tramo_max) y girar al rumbo final. El
  destino es una pose de la base; después de cada tramo vuelve a apuntar con la pose estimada.
- Parada (26-sim-alcance-arbolito): eje del árbol a parada[1] a la izquierda de J1 y parada[0] adelante; el robot
  siempre deja el árbol a su izquierda. La base solo se mueve con la misión en ESPERAR (brazo en reposo).

Marco odom (x, y, rumbo) de la base (centro del eje de tracción = centro de giro), unidades SI. Entradas: al_odom
(pose de OdometriaGiro: avance de /odom, rumbo del giróscopo), al_marca (pose del banderín en base_link),
al_estado_mision, al_estado_base y paso() periódico. Salidas por enviar(tipo, valor): 'cmd_vel' ((v, w)),
'comando_base' (str) y 'estado' (texto para /navegacion/estado).
"""

from dataclasses import dataclass
import json
import math
import statistics

INICIO, BUSCAR, UBICAR, IR_A_PARADA, COSECHAR, AVANZAR, VUELTA_U, CIERRE, FIN, FALLA = (
    'INICIO', 'BUSCAR', 'UBICAR', 'IR_A_PARADA', 'COSECHAR', 'AVANZAR', 'VUELTA_U', 'CIERRE', 'FIN', 'FALLA')


@dataclass
class ParNav:
    parada: tuple = (0.15, 0.70)  # m: eje del árbol respecto de J1 (adelante, izquierda); 26: tolera ±5 cm
    j1: tuple = (0.0, 0.11)       # m: J1 respecto del centro de giro (adelante, izquierda). urdf; real ~(0.005, 0.08) MEDIR
    yaw_camara: float = math.radians(86.2)  # cámara de navegación: 90° a la izquierda, 3,8° hacia adelante (13/11)
    sep_min: float = 0.45         # m: lo más cerca que puede pasar J1 del banderín o de un tronco
    tramo_max: float = 1.5        # m por recta (después frena y vuelve a apuntar)
    entrada: float = 1.0          # m antes del banderín (a lo largo de la hilera) para entrar a la línea de paradas
    paso_buscar: float = math.radians(30.0)
    t_buscar: float = 1.5         # s mirando en cada paso de BUSCAR
    t_ubicar: float = 3.0         # s de mediana en UBICAR
    min_vistas_buscar: int = 3
    min_vistas: int = 5
    t_quieto: float = 0.5         # s frenado antes de mirar o de dar por terminado un giro o un tramo
    t_cosechar: float = 6.0       # s con la misión en ESPERAR seguidos para dar por cosechado el árbol
    v_max: float = 0.10           # m/s (27: V_RECTO)
    v_min: float = 0.02
    w_max: float = 0.5            # rad/s (27: W_GIRO)
    w_min: float = 0.08
    k_v: float = 1.0              # 1/s
    k_w: float = 2.0              # 1/s: frenado proporcional cerca del objetivo (a 0,5 rad/s sin él se pasaba 6°)
    k_rumbo: float = 2.5          # 1/s: mantener el rumbo en las rectas
    tol_giro: float = math.radians(0.5)
    tol_recto: float = 0.005      # m
    min_recto: float = 0.02       # m: por debajo, no se mueve (solo orienta)
    atras_max: float = 0.30       # m: si el destino quedó atrás a menos de esto, retrocede en vez de dar la vuelta


# --- geometría (puntos (x, y) en m, ángulos en rad)

def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def suma(a, b, k=1.0):
    return (a[0] + k * b[0], a[1] + k * b[1])


def j1_de(pose, par):
    """Pose de la base (x, y, rumbo) -> J1 (x, y)."""
    return suma(pose[:2], rot(par.j1, pose[2]))


def pose_desde_j1(j1, rumbo, par):
    return (*suma(j1, rot(par.j1, rumbo), -1.0), rumbo)


def pose_parada(arbol, rumbo, par):
    """Pose de la base para cosechar `arbol` (x, y) mirando a `rumbo` (el árbol a la izquierda)."""
    return pose_desde_j1(suma(arbol, rot(par.parada, rumbo), -1.0), rumbo, par)


def arboles_en_odom(banderin, mira, hilera):
    """Banderín en (x, y) con la cara impresa mirando a `mira` -> ejes de los árboles. Mirando la marca de frente:
    derecha = la normal girada +90°, frente = la normal (hacia quien la mira)."""
    n = (math.cos(mira), math.sin(mira))
    d = rot(n, math.pi / 2)
    return [suma(suma(banderin, n, f), d, r) for r, f in hilera['arboles']]


def cargar_hilera(ruta, n=0):
    """JSON de la hilera (mm) -> {'id', 'lado', 'arboles': [(derecha, frente)]} en m; n > 0: solo los n primeros."""
    with open(ruta) as f:
        return leer_hilera(json.load(f), n)


def leer_hilera(j, n=0):
    arboles = [(a['derecha_mm'] / 1000.0, a['frente_mm'] / 1000.0) for a in j['arboles']]
    if n:
        if n > len(arboles):
            raise ValueError(f'la hilera tiene {len(arboles)} árboles y se pidieron {n}')
        arboles = arboles[:n]
    if not arboles:
        raise ValueError('la hilera no tiene árboles')
    return {'id': int(j.get('id', 0)), 'lado': j.get('lado_mm', 150.0) / 1000.0, 'arboles': arboles}


def hilera_recta(n, separacion=1.5, dist_banderin=1.5, id_=0, lado_mm=150.0):
    """La hilera de prueba (en mm, como el JSON): el banderín sobre la prolongación de la hilera, dist_banderin antes
    del árbol 1 y mirando hacia afuera (los árboles detrás de la marca)."""
    return {'id': id_, 'lado_mm': lado_mm,
            'arboles': [{'derecha_mm': 0.0, 'frente_mm': -1000.0 * (dist_banderin + k * separacion)}
                        for k in range(n)]}


def rumbo_ida(banderin, arboles):
    """Rumbo de la ida: del árbol 1 al 2 (con un solo árbol, del banderín al árbol)."""
    a, b = (arboles[0], arboles[1]) if len(arboles) > 1 else (banderin, arboles[0])
    return math.atan2(b[1] - a[1], b[0] - a[0])


def punto_banderin(banderin, rumbo_lado, psi_ida, par):
    """J1 sobre la línea de paradas de ese lado, `entrada` antes del banderín: para entrar a la hilera (ida) y para
    volver a mirar el banderín (cierre). La línea de J1 queda a parada[1] del banderín: pasa lejos."""
    u = (math.cos(psi_ida), math.sin(psi_ida))
    izq = (-math.sin(rumbo_lado), math.cos(rumbo_lado))
    return suma(suma(banderin, u, -par.entrada), izq, -par.parada[1])


def pose_mirador(banderin, rumbo_lado, psi_ida, par):
    """Pose para volver a ver el banderín: en punto_banderin, con la cámara apuntándolo."""
    j1 = punto_banderin(banderin, rumbo_lado, psi_ida, par)
    rumbo = math.atan2(banderin[1] - j1[1], banderin[0] - j1[0]) - par.yaw_camara
    return pose_desde_j1(j1, wrap(rumbo), par)


def camino_j1(desde, hasta, par, n=40):
    """Puntos de J1 en el movimiento ideal desde -> hasta (girar hacia el destino, avanzar, girar al rumbo final)."""
    x, y, th = desde
    pts = [j1_de(desde, par)]

    def girar(th, objetivo):
        dth = wrap(objetivo - th)
        pts.extend(j1_de((x, y, th + dth * k / n), par) for k in range(1, n + 1))
        return objetivo

    if math.hypot(hasta[0] - x, hasta[1] - y) >= par.min_recto:
        th = girar(th, math.atan2(hasta[1] - y, hasta[0] - x))
        pts.extend(j1_de((x + (hasta[0] - x) * k / n, y + (hasta[1] - y) * k / n, th), par) for k in range(1, n + 1))
        x, y = hasta[0], hasta[1]
    girar(th, hasta[2])
    return pts


def distancia_minima(puntos, obstaculos):
    return min(math.dist(p, o) for p in puntos for o in obstaculos)


def plan_hilera(pose, banderin, mira, hilera, lados, par):
    """(metas, aviso): metas = [(estado, árbol (1..n) o None, lado 'A'/'B' o None, pose de la base, cosechar)].
    aviso = None o por qué no se puede (J1 pasaría a menos de sep_min del banderín o de un tronco)."""
    if lados not in (1, 2):
        raise ValueError('lados tiene que ser 1 o 2')
    arboles = arboles_en_odom(banderin, mira, hilera)
    psi = rumbo_ida(banderin, arboles)
    vuelta = wrap(psi + math.pi)
    metas = [(AVANZAR, k + 1, 'A', pose_parada(a, psi, par), True) for k, a in enumerate(arboles)]
    metas[0] = (IR_A_PARADA,) + metas[0][1:]
    if lados == 2:
        ultimo = arboles[-1]
        metas.append((VUELTA_U, len(arboles), None, pose_parada(ultimo, wrap(psi + math.pi / 2), par), False))
        metas.append((VUELTA_U, len(arboles), 'B', pose_parada(ultimo, vuelta, par), True))
        metas += [(AVANZAR, k + 1, 'B', pose_parada(arboles[k], vuelta, par), True)
                  for k in range(len(arboles) - 2, -1, -1)]
    metas.append((CIERRE, None, None, pose_mirador(banderin, metas[-1][3][2], psi, par), False))
    obst = [banderin] + arboles

    def tramo_ok(a, b):
        return distancia_minima(camino_j1(a, b, par), obst) >= par.sep_min

    if not tramo_ok(pose, metas[0][3]):   # directo no: por la entrada, sobre la línea de paradas
        entrada = pose_desde_j1(punto_banderin(banderin, psi, psi, par), psi, par)
        metas.insert(0, (IR_A_PARADA, 1, None, entrada, False))
    previa = pose
    for estado, k, lado, meta, _ in metas:
        dmin = distancia_minima(camino_j1(previa, meta, par), obst)
        if dmin < par.sep_min:
            que = 'del banderín' if distancia_minima(camino_j1(previa, meta, par), [banderin]) < par.sep_min \
                else 'de un tronco'
            return metas, (f'{estado} (árbol {k}): J1 pasaría a {dmin * 100:.0f} cm {que} (mín. '
                           f'{par.sep_min * 100:.0f}): mover el robot, el banderín o corregir la hilera')
        previa = meta
    return metas, None


def mediana_marca(vistas):
    """[(x, y, mira)] -> (x, y, mira) mediana (la del ángulo, alrededor de la primera: están cerca entre sí)."""
    a0 = vistas[0][2]
    return (statistics.median(v[0] for v in vistas), statistics.median(v[1] for v in vistas),
            wrap(a0 + statistics.median(wrap(v[2] - a0) for v in vistas)))


def error_cierre(pose, banderin, mira, marca):
    """Pose estimada (odometría) contra la que da el banderín (guardado al ubicar, `marca` = (x, y, mira) en
    base_link ahora): (adelante, costado, rumbo) del error de la estimación, en el marco del robot."""
    th_m = wrap(mira - marca[2])
    base_m = suma(banderin, rot(marca[:2], th_m), -1.0)
    d = rot((pose[0] - base_m[0], pose[1] - base_m[1]), -pose[2])
    return d[0], d[1], wrap(pose[2] - th_m)


class Navegacion:

    def __init__(self, enviar, hilera, lados=2, par=None):
        self.enviar = enviar
        self.hilera = hilera
        self.lados = lados
        self.par = par or ParNav()
        self.estado = INICIO
        self.t0 = 0.0
        self.pose = None
        self.mision = 'INICIO'
        self.base_armada = False
        self.t_parado = None
        self.t_esperar = None      # desde cuándo la misión está en ESPERAR (COSECHAR)
        self.vistas = []           # (x, y, mira) del banderín en base_link
        self.t_mirar = None        # desde cuándo valen las vistas (robot quieto)
        self.giros = 0             # pasos de BUSCAR
        self.girando = None        # rumbo objetivo de un paso de BUSCAR
        self.metas = []
        self.meta = None
        self.fase = None           # 'apuntar' | 'recto' | 'orientar'
        self.recto = None          # (fin del tramo (x, y), sentido +1 adelante / -1 atrás)
        self.rumbo_buscar = None   # rumbo al empezar BUSCAR (los pasos son absolutos: no acumulan error)
        self.cerrando = False
        self.banderin = None       # (x, y) odom
        self.mira = None
        self.error = None          # (adelante, costado, rumbo) del cierre

    # --- entradas
    def al_odom(self, x, y, rumbo, t):
        self.pose = (x, y, rumbo)

    def al_estado_mision(self, estado, t):
        if estado != 'ESPERAR' or self.mision != 'ESPERAR':
            self.t_esperar = t if estado == 'ESPERAR' else None
        self.mision = estado

    def al_estado_base(self, texto, t):
        self.base_armada = texto.startswith('ARMADA')
        if 'SETA' in texto.split() and self.estado not in (FIN, FALLA):
            self._ir(FALLA, t, 'seta apretada')

    def al_marca(self, x, y, mira, t_img, t):
        """Pose del banderín en base_link (m, rad: hacia dónde sale la cara impresa) y hora de su imagen."""
        if self.estado in (BUSCAR, UBICAR) and self.t_mirar is not None and t_img >= self.t_mirar:
            self.vistas.append((x, y, mira))

    def base_quieta(self, t):
        """¿Puede cosechar la misión? En COSECHAR, con la base frenada hace más de t_quieto."""
        return self.estado == COSECHAR and self._quieto(t)

    # --- lógica
    def _ir(self, estado, t, motivo=''):
        self.estado, self.t0 = estado, t
        self.enviar('estado', estado + (f': {motivo}' if motivo else ''))

    def _quieto(self, t):
        return self.t_parado is not None and t - self.t_parado >= self.par.t_quieto

    def _frenar(self, t):
        if self.t_parado is None:
            self.t_parado = t
        self.enviar('cmd_vel', (0.0, 0.0))

    def _cmd(self, v, w):
        self.t_parado = None
        self.enviar('cmd_vel', (v, w))

    def _girar(self, objetivo, t):
        """Gira en el lugar hasta `objetivo` (rumbo del giróscopo); True cuando llegó y quedó quieto."""
        err = wrap(objetivo - self.pose[2])
        if abs(err) > self.par.tol_giro:
            w = max(self.par.w_min, min(self.par.w_max, self.par.k_w * abs(err)))
            self._cmd(0.0, math.copysign(w, err))
            return False
        self._frenar(t)
        return self._quieto(t)

    def _empezar_mirar(self, t):
        self.vistas, self.t_mirar = [], None

    def _mirar(self, t, segundos):
        """Frena y junta vistas `segundos` desde que quedó quieto; True cuando terminó la ventana."""
        self._frenar(t)
        if self.t_mirar is None:
            if self._quieto(t):
                self.t_mirar = t
            return False
        return t - self.t_mirar >= segundos

    def _siguiente_meta(self, t):
        if not self.metas:
            self.cerrando = True
            self.giros, self.girando = 0, None
            self._empezar_mirar(t)
            return self._ir(BUSCAR, t, 'cierre: mirando el banderín')
        self.meta = self.metas.pop(0)
        self.fase = 'apuntar'
        estado, k, lado, pose, _ = self.meta
        donde = f'árbol {k}, lado {lado}' if lado else (f'rodeando el árbol {k}' if estado == VUELTA_U else
                                                         'entrada' if estado == IR_A_PARADA else 'al banderín')
        self._ir(estado, t, f'{donde} -> ({pose[0]:.3f}, {pose[1]:.3f}) m, {math.degrees(pose[2]):.1f}°')

    def _mover(self, t):
        """Sigue la meta: apuntar -> recto (tramos) -> orientar. True al llegar."""
        x, y, th = self.pose
        gx, gy, gth = self.meta[3]
        p = self.par
        if self.fase == 'apuntar':
            d = math.hypot(gx - x, gy - y)
            if d < p.min_recto:
                self.fase = 'orientar'
                return False
            hacia, sentido = math.atan2(gy - y, gx - x), 1.0
            if abs(wrap(hacia - th)) > math.pi / 2 and d <= p.atras_max:   # quedó atrás y cerca: retroceder
                sentido = -1.0
            if self._girar(hacia if sentido > 0 else wrap(hacia + math.pi), t):
                largo = d / math.ceil(d / p.tramo_max)   # tramos iguales: sin un resto de 1 cm que no se haga
                self.fase = 'recto'
                self.recto = ((x + largo * math.cos(hacia), y + largo * math.sin(hacia)), sentido)
            return False
        if self.fase == 'recto':
            (ex, ey), sentido = self.recto
            dx, dy = ex - x, ey - y
            falta = sentido * (dx * math.cos(th) + dy * math.sin(th))   # lo que falta a lo largo del robot
            if falta <= p.tol_recto:
                self._frenar(t)
                if self._quieto(t):
                    self.fase = 'apuntar'
                return False
            # Rumbo hacia el fin del tramo (corrige el error de apuntar); en los últimos 10 cm, derecho
            rumbo = math.atan2(dy, dx) + (0.0 if sentido > 0 else math.pi) if math.hypot(dx, dy) > 0.10 else th
            v = sentido * max(p.v_min, min(p.v_max, p.k_v * falta))
            w = max(-p.w_max, min(p.w_max, p.k_rumbo * wrap(rumbo - th)))
            self._cmd(v, w)
            return False
        return self._girar(gth, t)

    def paso(self, t):
        if self.estado in (FIN, FALLA):
            return self._frenar(t)
        if self.pose is None:
            return self._frenar(t)
        if self.estado == INICIO:
            self._frenar(t)
            if not self.base_armada:
                if t - self.t0 >= 1.0:   # reintentar cada segundo hasta ver ARMADA
                    self.enviar('comando_base', 'armar')
                    self.t0 = t
                return
            if self.mision != 'ESPERAR':
                return
            self.giros, self.girando = 0, None
            self._empezar_mirar(t)
            return self._ir(BUSCAR, t, f'{len(self.hilera["arboles"])} árboles, {self.lados} lado(s)')
        if self.mision != 'ESPERAR' and self.estado != COSECHAR:
            return self._frenar(t)   # el brazo no está en reposo: la base no se mueve
        if self.estado == BUSCAR:
            return self._buscar(t)
        if self.estado == UBICAR:
            return self._ubicar(t)
        if self.estado == COSECHAR:
            self._frenar(t)
            if self.t_esperar is not None and self.mision == 'ESPERAR' and t - self.t_esperar >= self.par.t_cosechar \
                    and t - self.t0 >= self.par.t_cosechar:
                self._siguiente_meta(t)
            return
        if self._mover(t):   # IR_A_PARADA, AVANZAR, VUELTA_U, CIERRE
            estado, k, lado, _, cosechar = self.meta
            if cosechar:
                self.t_esperar = t if self.mision == 'ESPERAR' else None
                return self._ir(COSECHAR, t, f'árbol {k}, lado {lado}')
            self._siguiente_meta(t)

    def _buscar(self, t):
        p = self.par
        if self.girando is not None:
            if self._girar(self.girando, t):
                self.girando = None
                self._empezar_mirar(t)
            return
        if not self._mirar(t, p.t_buscar):
            return
        if len(self.vistas) >= p.min_vistas_buscar:
            self._empezar_mirar(t)
            return self._ir(UBICAR, t, f'banderín visto después de girar {math.degrees(self.giros * p.paso_buscar):.0f}°')
        self.enviar('estado', f'BUSCAR: paso {self.giros}, rumbo {math.degrees(self.pose[2]):+.1f}°, '
                              f'{len(self.vistas)} vistas')
        if self.giros * p.paso_buscar >= 2 * math.pi - 1e-6:
            return self._ir(FALLA, t, 'di la vuelta entera y no vi el banderín (¿a 0,9-4 m, de frente?)')
        if self.giros == 0:
            self.rumbo_buscar = self.pose[2]
        self.giros += 1
        self.girando = wrap(self.rumbo_buscar + self.giros * p.paso_buscar)

    def _ubicar(self, t):
        if not self._mirar(t, self.par.t_ubicar):
            return
        if len(self.vistas) < self.par.min_vistas:
            self.giros, self.girando = 0, None
            self._empezar_mirar(t)
            return self._ir(BUSCAR, t, f'solo {len(self.vistas)} vistas del banderín')
        mx, my, mmira = mediana_marca(self.vistas)
        x, y, th = self.pose
        if self.cerrando:
            self.error = error_cierre(self.pose, self.banderin, self.mira, (mx, my, mmira))
            a, c, r = self.error
            return self._ir(FIN, t, f'error de la odometría adelante {a * 100:+.1f} cm, costado {c * 100:+.1f} cm, '
                                    f'rumbo {math.degrees(r):+.1f}° ({len(self.vistas)} vistas)')
        self.banderin = suma((x, y), rot((mx, my), th))
        self.mira = wrap(th + mmira)
        self.metas, aviso = plan_hilera(self.pose, self.banderin, self.mira, self.hilera, self.lados, self.par)
        self.enviar('estado', f'UBICAR: banderín en ({self.banderin[0]:.3f}, {self.banderin[1]:.3f}) m mirando a '
                              f'{math.degrees(self.mira):.1f}° ({len(self.vistas)} vistas), {len(self.metas)} metas')
        if aviso:
            return self._ir(FALLA, t, aviso)
        self._siguiente_meta(t)
