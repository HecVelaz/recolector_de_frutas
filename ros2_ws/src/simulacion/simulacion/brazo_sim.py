"""Nodo brazo_sim: hace en Gazebo lo que firmware/brazo hace con micro-ROS, con los mismos tópicos y textos.

Entra  /brazo/joint_cmd  sensor_msgs/JointState  j1, j2, j3 del actuador [rad]; todo o nada, solo ARMADO
       /brazo/comando    std_msgs/String         armar, desarmar, s (detener)
       /pinza/cierre     std_msgs/Float32        0 = abierta, 100 = cerrada (solo ARMADO)
       /pinza/giro       std_msgs/Float32        grados, -90..90 (solo ARMADO)
       /joint_states     sensor_msgs/JointState  de Gazebo: j1, j2, j3o (cadena serie equivalente), j4, dedos
Sale   /brazo/joint_states (20 Hz), /brazo/estado (2 Hz, formato del firmware), /brazo/respuesta
       /sim/j1, /sim/j2, /sim/j3o, /sim/j_nivel, /sim/j4, /sim/dedo_izq, /sim/dedo_der  std_msgs/Float64 ->
       JointController (j1, j2, j3o, j_nivel: velocidad [rad/s]) y JointPositionController (j4, dedos: posición).
       j_nivel = -(q2 + q3O) hace lo del paralelogramo del uArm: herramienta horizontal.

Como el firmware: consigna con perfil trapezoidal (30 °/s y 60 °/s² J1, 20 °/s y 40 °/s² J2/J3), "llego" a 0,5°, arranca
DESARMADO y con cero (en la simulación no hace falta el homing). El cuatro barras se convierte con cinematica.py.
"""

import math

from brazo_ik.cinematica import (cuatro_barras_directo, cuatro_barras_inverso, en_rango, GAMMA4_LIM, norm_ang,
                                 Q1_LIM, Q2_LIM, Q3_LIM)
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float32, Float64, String

VEL_MAX = [math.radians(v) for v in (30.0, 20.0, 20.0)]  # brazo_config.h: velMax
ACC_MAX = [math.radians(a) for a in (60.0, 40.0, 40.0)]  # brazo_config.h: accMax (sin rampa, la reacción movía la base)
TOL = math.radians(0.5)                                   # brazo_config.h: tolerancia de llegada
LIMITES = (Q1_LIM, Q2_LIM, Q3_LIM)
DEDO_ABIERTO = 0.045  # m, cada dedo (urdf)
TS = 0.02             # 50 Hz
# Reposo (= reposo de mision en sim.launch.py): las articulaciones aparecen en 0 y brazo_sim las lleva ahí; no tomar
# esa pose intermedia como consigna. Levantado y girado a la izquierda, del lado de la fila: J1 nunca cruza el mástil
# (adelante a la derecha) al ir a un limón y volver (girado a la derecha, a -75°, lo atravesaba). Buscado simulando
# los recorridos a los 12 limones: ninguno pasa a menos de 33 cm del mástil, y queda a 17 cm de la vista de las cámaras
REPOSO = [math.radians(75.0), math.radians(110.0), math.radians(-30.0)]
K_POS = 5.0  # 1/s: velocidad = la de la consigna + K_POS * error (K_POS * TS << 1: estable a 50 Hz)
V_LIM = 1.0  # rad/s, límite de las articulaciones en el urdf


def actuador_a_serie(q2, q3):
    """(q2, q3 del actuador) -> q3O del antebrazo, o None si el cuatro barras no cierra."""
    r = cuatro_barras_directo(q2 + q3 - math.pi / 2)
    return None if r is None else r[0]


def serie_a_actuador(q2, q3o, q3_prev=0.0):
    """(q2, q3O medidos) -> q3 del actuador: la solución en la rama física (γ4 en (-180°, 0°)) más cercana a q3_prev.

    Como en cinematica_inversa, se descarta el γ4 de la otra rama de ensamble (su directa no vuelve a q3O). Cerca del
    pliegue (γ4 ≈ -4,5°, q3O ≈ -131,7°, borde del espacio de trabajo) dos q3 a ~2,5° dan el mismo q3O: ahí decide la
    continuidad con q3_prev.
    """
    cands = []
    for g in cuatro_barras_inverso(q3o):
        r = cuatro_barras_directo(g)
        if en_rango(norm_ang(g), GAMMA4_LIM) and r is not None and abs(norm_ang(r[0] - q3o)) < 1e-6:
            cands.append(norm_ang(g - q2 + math.pi / 2))
    return min(cands, key=lambda q: abs(q - q3_prev)) if cands else float('nan')


def perfil(pos, vel, objetivo, v_max, a_max, dt):
    """Un paso de perfil trapezoidal hacia `objetivo`: acelera a a_max hasta v_max y frena a tiempo. -> (pos, vel)"""
    falta = objetivo - pos
    if abs(falta) < 1e-9 and abs(vel) <= a_max * dt:
        return objetivo, 0.0
    # velocidad deseada: la máxima que todavía deja frenar justo en el objetivo, en pasos de dt (versión discreta de
    # sqrt(2·a·d): con la continua llegaba a ~6°/s y cortaba a 0 de golpe)
    ad = a_max * dt
    v_des = math.copysign(min(v_max, abs(falta) / dt, ad * (math.sqrt(0.25 + 2 * abs(falta) / (ad * dt)) - 0.5)), falta)
    vel += max(-a_max * dt, min(a_max * dt, v_des - vel))
    pos += vel * dt
    if (objetivo - pos) * falta <= 0:  # se pasó: queda en el objetivo
        return objetivo, 0.0
    return pos, vel


class BrazoSim(Node):

    def __init__(self):
        super().__init__('brazo_sim')
        self.armado = False
        self.q = None          # actuador medido [j1, j2, j3] rad
        self.medido = {}       # articulaciones de Gazebo (j1, j2, j3o, j_nivel) rad
        self.previo = {}       # consigna del ciclo anterior, para su velocidad
        self.v = [0.0] * 3
        self.consigna = list(REPOSO)  # actuador, se acerca al objetivo a VEL_MAX
        self.objetivo = list(REPOSO)
        self.vel = [0.0] * 3          # velocidad de la consigna
        self.dedos = DEDO_ABIERTO  # m, cada dedo
        self.giro = 0.0            # rad (J4)
        self.tick = 0
        self.pub = {n: self.create_publisher(Float64, f'/sim/{n}', 10) for n in ('j1', 'j2', 'j3o', 'j_nivel', 'j4', 'dedo_izq', 'dedo_der')}
        self.pub_joints = self.create_publisher(JointState, '/brazo/joint_states', 10)
        self.pub_estado = self.create_publisher(String, '/brazo/estado', 10)
        self.pub_resp = self.create_publisher(String, '/brazo/respuesta', 10)
        self.create_subscription(JointState, '/joint_states', self.al_gazebo, 10)
        self.create_subscription(JointState, '/brazo/joint_cmd', self.al_cmd, 10)
        self.create_subscription(String, '/brazo/comando', self.al_comando, 10)
        self.create_subscription(Float32, '/pinza/cierre', self.al_cierre, 10)
        self.create_subscription(Float32, '/pinza/giro', self.al_giro, 10)
        self.create_timer(TS, self.paso)

    def responder(self, texto):
        self.pub_resp.publish(String(data=texto))
        self.get_logger().info(texto)

    def armado_o_avisar(self):
        if not self.armado:
            self.responder(">> Brazo DESARMADO: enviar 'armar' por /brazo/comando para habilitar movimientos.")
        return self.armado

    def al_gazebo(self, m):
        d = dict(zip(m.name, m.position))
        dv = dict(zip(m.name, m.velocity)) if m.velocity else {}
        if not all(j in d for j in ('j1', 'j2', 'j3o', 'j_nivel')):
            return
        self.medido = {j: d[j] for j in ('j1', 'j2', 'j3o', 'j_nivel')}
        q3_prev = self.q[2] if self.q else 0.0
        q = [d['j1'], d['j2'], serie_a_actuador(d['j2'], d['j3o'], q3_prev)]
        if self.q:
            self.v = [dv.get('j1', 0.0), dv.get('j2', 0.0), (q[2] - self.q[2]) / TS]  # aprox.: /joint_states ~50 Hz
        self.q = q

    def al_cmd(self, m):
        if not self.armado_o_avisar() or self.q is None:
            return
        if m.name:
            d = dict(zip(m.name, m.position))
            nuevo = [d.get(j, self.objetivo[i] if self.objetivo else self.q[i]) for i, j in enumerate(('j1', 'j2', 'j3'))]
        elif len(m.position) == 3:
            nuevo = list(m.position)
        else:
            return self.responder('>> joint_cmd rechazado: nombres j1..j3 o las 3 posiciones en orden')
        for i, (qi, lim) in enumerate(zip(nuevo, LIMITES)):
            if not (math.isfinite(qi) and en_rango(qi, lim)):
                return self.responder(f'>> joint_cmd rechazado: J{i + 1} fuera de [{lim[0]:.0f}°, {lim[1]:.0f}°]')
        if actuador_a_serie(nuevo[1], nuevo[2]) is None:
            return self.responder('>> joint_cmd rechazado: el cuatro barras no cierra con esos q2, q3')
        self.objetivo = nuevo

    def al_comando(self, m):
        c = m.data.strip()
        if c == 'armar':
            self.armado = True
            self.responder('>> Brazo ARMADO.')
        elif c == 'desarmar':
            self.armado = False
            if self.q:
                self.objetivo = list(self.q)
            self.responder('>> Brazo DESARMADO.')
        elif c == 's':
            if self.q:
                self.objetivo, self.consigna, self.vel = list(self.q), list(self.q), [0.0] * 3
            self.responder('>> Detenido.')
        else:
            self.responder(f'>> "{c}" no está en la simulación (solo armar, desarmar, s)')

    def al_cierre(self, m):
        if self.armado_o_avisar() and math.isfinite(m.data):
            self.dedos = DEDO_ABIERTO * (1.0 - min(max(m.data, 0.0), 100.0) / 100.0)

    def al_giro(self, m):
        if self.armado_o_avisar() and math.isfinite(m.data):
            self.giro = math.radians(min(max(m.data, -90.0), 90.0))

    def paso(self):
        if not self.medido:
            return
        # Al aparecer (articulaciones en 0) q3 no tiene sentido: la consigna sigue en el reposo y se llega igual
        if self.q is not None and math.isfinite(self.q[2]):
            for i in range(3):
                self.consigna[i], self.vel[i] = perfil(self.consigna[i], self.vel[i], self.objetivo[i], VEL_MAX[i],
                                                       ACC_MAX[i], TS)
        q3o = actuador_a_serie(self.consigna[1], self.consigna[2])
        # Todo en cada ciclo (como el PWM de los servos): un mensaje suelto al puente se puede perder
        for n, val in (('j1', self.consigna[0]), ('j2', self.consigna[1]), ('j3o', q3o),
                       ('j_nivel', -(self.consigna[1] + q3o))):
            v = (val - self.previo.get(n, val)) / TS + K_POS * (val - self.medido[n])
            self.previo[n] = val
            self.pub[n].publish(Float64(data=max(-V_LIM, min(V_LIM, v))))
        for n, val in (('j4', self.giro), ('dedo_izq', self.dedos), ('dedo_der', self.dedos)):
            self.pub[n].publish(Float64(data=val))
        if self.q is None or not math.isfinite(self.q[2]):
            return

        self.tick += 1
        if self.tick % 2 == 0:  # 25 Hz (el firmware: 20)
            js = JointState(name=['j1', 'j2', 'j3'], position=list(self.q), velocity=list(self.v))
            js.header.stamp = self.get_clock().now().to_msg()
            self.pub_joints.publish(js)
        if self.tick % 25 == 0:  # 2 Hz
            partes = ['ARMADO' if self.armado else 'DESARMADO']
            for i in range(3):
                llego = self.consigna[i] == self.objetivo[i] and abs(self.q[i] - self.objetivo[i]) <= TOL
                partes.append(f'J{i + 1} posicion cero u=0% falla=ninguna{" llego" if llego else ""}')
            self.pub_estado.publish(String(data='; '.join(partes) + '; enlace: pings_fallidos=0 cortes=0'))


def main(args=None):
    rclpy.init(args=args)
    nodo = BrazoSim()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
