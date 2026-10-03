"""Cinemática directa e inversa del brazo (mecanismo de cuatro barras), portada de la Entrega 4 de R1.

Mismo algoritmo y convenciones que el notebook de la E4 (Entrega4.md), sin numpy ni gráficos:

    q1 : giro de la base alrededor de Z (0 = eje +X del brazo = frente del robot; antihorario visto desde arriba).
         Su rango (Q1_LIM) pasa de 180° (atrás): los q1 se expresan dentro de Q1_LIM, no en (-180°, 180°]
    q2 : barra verde l2 medida desde la horizontal, del lado de la muñeca
    q3 : actuador de la barra roja l3,0; su ángulo absoluto es 90° - q3
    gamma4 = q2 + q3 - 90°        (ángulo del cuatro barras en la base)
    q3O = alpha4 - beta4          (antebrazo l3 respecto de la prolongación de l2; dependiente)

El punto que se posiciona es la muñeca P3. El brazo es tipo uArm / Dobot Magician: un paralelogramo mantiene la
herramienta siempre horizontal, apuntando hacia afuera en la dirección de q1 (E1). Por eso el punto de agarre (TCP)
está a una distancia horizontal fija de la muñeca y muneca_desde_herramienta() pasa de uno al otro.
Longitudes en mm, ángulos en radianes (límites en grados).
Los límites deben coincidir con firmware/brazo/include/brazo_config.h.
"""

from dataclasses import dataclass
import math

# Geometría (E4) [mm]
H1 = 150.00   # altura del hombro
L2 = 350.22   # barra verde
L3 = 329.51   # barra azul (articulación superior B -> muñeca P3)
L4 = 338.00   # barra amarilla (acoplador)
L30 = 40.00   # balancín de entrada (rojo)
L31 = 40.00   # balancín de salida (tramo corto del azul)

# Límites [°]
# J1: -45/+135 desde el costado izquierdo (q1 = 90°, el cero del banco de pruebas-esp32/10, 2026-10-02). Igual que
# brazo_config.h y el urdf
Q1_LIM = (45.0, 225.0)
Q2_LIM = (-25.0, 135.0)
Q3_LIM = (-50.0, 50.0)
GAMMA4_LIM = (-180.0, 0.0)  # rama física: la roja no cruza la verde
MU_MIN = 15.0               # ángulo de transmisión mínimo [°] (lejos de los puntos muertos)

TOL_POS = 1e-4  # mm: una solución se acepta si la cinemática directa vuelve al objetivo


@dataclass
class Solucion:
    q1: float      # rad
    q2: float
    q3: float
    q30: float     # antebrazo (dependiente)
    gamma4: float
    mu: float      # ángulo de transmisión
    p: tuple       # (x, y, z) de la muñeca por cinemática directa [mm]
    err: float     # mm


def muneca_desde_herramienta(x, y, z, largo):
    """Punto de agarre (TCP) -> muñeca P3: la herramienta es horizontal y apunta en la dirección de q1, así que el TCP
    está `largo` más afuera que la muñeca en el mismo plano vertical que el eje de J1. Mismas unidades que la entrada.
    Con el TCP a menos de `largo` del eje de J1 no hay solución: devuelve None."""
    r = math.hypot(x, y)
    if largo == 0.0:
        return x, y, z
    if r <= largo:
        return None
    k = (r - largo) / r
    return x * k, y * k, z


def norm_ang(a):
    return math.atan2(math.sin(a), math.cos(a))


def q1_en_rango(q1):
    """Lleva un ángulo de la base al intervalo que empieza en Q1_LIM[0] (+-360°): atan2 da (-180°, 180°] y el rango de
    J1 pasa por 180°."""
    a = q1
    while math.degrees(a) < Q1_LIM[0] - 1e-9:
        a += 2 * math.pi
    while math.degrees(a) >= Q1_LIM[0] + 360.0 - 1e-9:
        a -= 2 * math.pi
    return a


def en_rango(q_rad, lim):
    return lim[0] - 1e-9 <= math.degrees(q_rad) <= lim[1] + 1e-9


def cuatro_barras_directo(gamma4):
    """gamma4 -> (q3O, mu). None si el mecanismo no cierra."""
    lado = math.sqrt(L2**2 + L30**2 - 2 * L2 * L30 * math.cos(gamma4))
    c = (lado**2 + L31**2 - L4**2) / (2 * L31 * lado)
    if abs(c) > 1:
        return None
    alpha4 = math.atan2(L30 * math.sin(gamma4), L2 - L30 * math.cos(gamma4))
    beta4 = math.acos(c)
    mu = math.acos(max(-1.0, min(1.0, (L31**2 + L4**2 - lado**2) / (2 * L31 * L4))))
    return alpha4 - beta4, mu


def cuatro_barras_inverso(q30):
    """q3O -> lista de gamma4 candidatos: -(delta ± epsilon)."""
    psi = -q30
    e = math.sqrt(L2**2 + L31**2 - 2 * L2 * L31 * math.cos(psi))
    c = (e**2 + L30**2 - L4**2) / (2 * L30 * e)
    if abs(c) > 1:
        return []
    delta = math.atan2(L31 * math.sin(psi), L2 - L31 * math.cos(psi))
    eps = math.acos(c)
    return [-(delta + eps), -(delta - eps)]


def cinematica_directa(q1, q2, q3):
    """(q1, q2, q3) [rad] -> ((x, y, z) [mm], q3O, mu). None si el cuatro barras no cierra."""
    res = cuatro_barras_directo(q2 + q3 - math.pi / 2)
    if res is None:
        return None
    q30, mu = res
    th = q2 + q30
    r = L2 * math.cos(q2) + L3 * math.cos(th)
    p = (r * math.cos(q1), r * math.sin(q1), H1 + L2 * math.sin(q2) + L3 * math.sin(th))
    return p, q30, mu


def config_valida(q1, q2, q3, mu):
    gamma4 = norm_ang(q2 + q3 - math.pi / 2)
    return (en_rango(q1, Q1_LIM) and en_rango(q2, Q2_LIM) and en_rango(q3, Q3_LIM)
            and en_rango(gamma4, GAMMA4_LIM) and MU_MIN <= math.degrees(mu) <= 180 - MU_MIN)


def _dist(a, b):
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def cinematica_inversa(x, y, z):
    """Objetivo de la muñeca (x, y, z) [mm] -> (soluciones, motivos).

    soluciones: lista de Solucion válidas (límites, rama física, ángulo de transmisión), ordenadas por |q3|.
    motivos: por qué se descartó cada candidato (útil si no hay soluciones).
    """
    soluciones, motivos = [], []
    r = math.hypot(x, y)
    zp = z - H1
    dist = math.hypot(r, zp)

    # Paso 1: q1
    q1 = q1_en_rango(math.atan2(y, x)) if r > 1e-10 else math.radians(90.0)
    if not en_rango(q1, Q1_LIM):
        motivos.append(f'q1 = {math.degrees(q1):.1f}° fuera de [{Q1_LIM[0]:.0f}°, {Q1_LIM[1]:.0f}°]')

    # Paso 2: q3O (codo de la cadena equivalente l2-l3)
    c30 = (r**2 + zp**2 - L2**2 - L3**2) / (2 * L2 * L3)
    if c30 > 1 + 1e-9:
        return [], [f'Demasiado lejos: distancia al hombro {dist:.1f} mm > l2 + l3 = {L2 + L3:.1f} mm']
    if c30 < -1 - 1e-9:
        return [], [f'Demasiado cerca: distancia al hombro {dist:.1f} mm < |l2 - l3| = {abs(L2 - L3):.1f} mm']
    q30_abs = math.acos(max(-1.0, min(1.0, c30)))

    for q30 in (-q30_abs, q30_abs):
        rama = f'rama q3O = {math.degrees(q30):+.1f}°'
        # Paso 3: q2
        q2 = norm_ang(math.atan2(zp, r) - math.atan2(L3 * math.sin(q30), L2 + L3 * math.cos(q30)))
        if not en_rango(q2, Q2_LIM):
            motivos.append(f'{rama}: q2 = {math.degrees(q2):.1f}° fuera de [{Q2_LIM[0]:.0f}°, {Q2_LIM[1]:.0f}°]')
            continue
        # Paso 4: invertir el cuatro barras
        gammas = cuatro_barras_inverso(q30)
        if not gammas:
            motivos.append(f'{rama}: el cuatro barras no puede dar ese q3O')
            continue
        for gamma4 in gammas:
            # Paso 5: q3
            q3 = norm_ang(gamma4 - q2 + math.pi / 2)
            # Paso 6: verificación con la directa
            fk = cinematica_directa(q1, q2, q3)
            if fk is None or _dist(fk[0], (x, y, z)) > TOL_POS:
                continue  # pertenece a la otra rama de ensamble
            p, q30_fk, mu = fk
            if not en_rango(q3, Q3_LIM):
                motivos.append(f'{rama}: q3 = {math.degrees(q3):.1f}° fuera de [{Q3_LIM[0]:.0f}°, {Q3_LIM[1]:.0f}°]')
            elif not en_rango(norm_ang(gamma4), GAMMA4_LIM):
                motivos.append(f'{rama}: γ4 = {math.degrees(gamma4):.1f}° (la roja cruzaría la verde)')
            elif not (MU_MIN <= math.degrees(mu) <= 180 - MU_MIN):
                motivos.append(f'{rama}: ángulo de transmisión {math.degrees(mu):.1f}° (cerca de punto muerto)')
            elif en_rango(q1, Q1_LIM):
                soluciones.append(Solucion(q1, q2, q3, q30_fk, gamma4, mu, p, _dist(p, (x, y, z))))
    soluciones.sort(key=lambda s: abs(s.q3))
    return soluciones, (motivos or ['Sin solución con los límites actuales'])
