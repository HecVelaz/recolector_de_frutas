"""Nodo base_sim: hace en Gazebo lo que firmware/base hace con micro-ROS, con los mismos tópicos y textos.

Entra  /cmd_vel       geometry_msgs/Twist   solo ARMADA; watchdog de 300 ms como con micro-ROS (`wd` 50..1000)
       /base/comando  std_msgs/String       armar, desarmar, s (detener), r (rearmar), wd <ms>,
                                            seta / soltar_seta (solo en la simulación: probar la emergencia)
       /imu/data_raw  sensor_msgs/Imu       de Gazebo (con orientación): roll y pitch para el vuelco
       gz /sim/us_*       LaserScan         HC-SR04 como gpu_lidar de 5 rayos en ~15°: el eco más cercano
       /joint_states  sensor_msgs/JointState  planchas de los bumpers (con resorte): apretado = hundida > 3 mm
Sale   /sim/cmd_vel (-> DiffDrive, con la rampa de CFG_DIF), /range/frente|izq|der (10 Hz), /bumpers (10 Hz),
       /battery (1 Hz, 38 V fijos), /base/estado (2 Hz, formato del firmware), /base/respuesta

La seguridad es la de lib/BaseLogica/SeguridadBase.cpp (misma prioridad y mismos umbrales de base_config.h).
"""

import math

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, Imu, JointState, Range
from std_msgs.msg import String, UInt8

from simulacion.limones_sim import rutas_gz

DIST_PARADA, DIST_LENTA = 0.20, 0.50  # m (CFG_SEG)
INCL_MAX = 25.0                       # grados de roll o pitch
V_MAX = 0.25                          # m/s, tope de avance lejos de obstáculos
IMU_MAX = 0.2                         # s sin IMU -> no se mueve
US = ('frente', 'izq', 'der')
BUMPERS = ('frente', 'izq', 'der')    # bits 0..2 de /bumpers
HUNDIDO = -0.003                      # m: con la plancha más adentro, el final de carrera la da por apretada
TS = 0.02                             # 50 Hz


class Seguridad:
    """SeguridadBase.cpp en Python. filtrar() -> (puede, v, w); estado: ok, EMERGENCIA (seta), VUELCO, ..."""

    def __init__(self, wd_ms=300):
        self.wd_ms = wd_ms
        self.estado = 'ok'
        self.bloq_adelante = self.frente_sin_dato = False

    def filtrar(self, bumper, dist_frente, seta, roll, pitch, ms_sin_cmd, imu_valida, v, w):
        nivelada = abs(roll) < INCL_MAX and abs(pitch) < INCL_MAX
        # Enclavados: primero la seta, después el vuelco
        if seta:
            self.estado = 'EMERGENCIA (seta)'
        elif self.estado != 'EMERGENCIA (seta)' and imu_valida and not nivelada:
            self.estado = 'VUELCO'
        self.bloq_adelante = self.frente_sin_dato = False
        if self.estado in ('EMERGENCIA (seta)', 'VUELCO'):
            return False, 0.0, 0.0
        if not imu_valida:
            self.estado = 'IMU sin datos'
            return False, 0.0, 0.0
        if self.wd_ms > 0 and ms_sin_cmd > self.wd_ms:
            self.estado = 'sin comandos'
            return False, 0.0, 0.0
        self.estado = 'ok'
        # Contacto: frente no avanza; cualquiera, sin giro (un giro puede seguir apretando contra el objeto)
        if any(bumper):
            w = 0.0
        self.bloq_adelante = bumper[0]
        if math.isnan(dist_frente):
            self.frente_sin_dato = self.bloq_adelante = True
        elif dist_frente <= DIST_PARADA:
            self.bloq_adelante = True
        elif dist_frente < DIST_LENTA:
            v = min(v, V_MAX * (dist_frente - DIST_PARADA) / (DIST_LENTA - DIST_PARADA))
        if self.bloq_adelante and v > 0.0:
            v = 0.0
        return True, v, w

    def rearmar(self, seta, roll, pitch, imu_valida):
        if seta or not imu_valida or not (abs(roll) < INCL_MAX and abs(pitch) < INCL_MAX):
            return False
        self.estado = 'ok'
        return True


def eco_mas_cercano(rangos, r_min=0.02, r_max=4.0):
    """Rayos del gpu_lidar -> lo que mide un HC-SR04: el eco más cercano, +Inf si nada al alcance (REP-117)."""
    validos = [r for r in rangos if r_min <= r <= r_max]
    return min(validos) if validos else math.inf


class BaseSim(Node):

    def __init__(self):
        super().__init__('base_sim')
        self.seg = Seguridad()
        self.armado = False
        self.modo = 'libre'           # como el firmware al arrancar
        self.cmd = (0.0, 0.0)
        self.t_cmd = None
        self.seta = False
        self.roll = self.pitch = 0.0
        self.t_imu = None
        self.dist = [math.nan] * 3    # sin eco hasta la primera medición: no avanza
        self.bumper = [False] * 3
        self.tick = 0

        rutas_gz()
        from gz.msgs10.laserscan_pb2 import LaserScan
        from gz.transport13 import Node as NodoGz
        self.gz = NodoGz()  # los callbacks corren en hilos de gz-transport: solo guardan el último valor
        for k, n in enumerate(US):
            self.gz.subscribe(LaserScan, f'/sim/us_{n}', lambda m, k=k: self.dist.__setitem__(k, eco_mas_cercano(m.ranges)))

        self.pub_cmd = self.create_publisher(Twist, '/sim/cmd_vel', 10)
        self.pub_rango = [self.create_publisher(Range, f'/range/{n}', 10) for n in US]
        self.pub_bumpers = self.create_publisher(UInt8, '/bumpers', 10)
        self.pub_bateria = self.create_publisher(BatteryState, '/battery', 10)
        self.pub_estado = self.create_publisher(String, '/base/estado', 10)
        self.pub_resp = self.create_publisher(String, '/base/respuesta', 10)
        self.create_subscription(Twist, '/cmd_vel', self.al_cmd, 10)
        self.create_subscription(String, '/base/comando', self.al_comando, 10)
        self.create_subscription(Imu, '/imu/data_raw', self.al_imu, 10)
        self.create_subscription(JointState, '/joint_states', self.al_joints, 10)
        self.create_timer(TS, self.paso)

    def t(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def responder(self, texto):
        self.pub_resp.publish(String(data=texto))
        self.get_logger().info(texto)

    def al_cmd(self, m):
        if not self.armado:
            return self.responder(">> Base DESARMADA: enviar 'armar' por /base/comando para habilitar /cmd_vel.")
        self.cmd, self.t_cmd, self.modo = (m.linear.x, m.angular.z), self.t(), 'v/w'

    def al_imu(self, m):
        x, y, z, w = m.orientation.x, m.orientation.y, m.orientation.z, m.orientation.w
        self.roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
        self.pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
        self.t_imu = self.t()

    def al_joints(self, m):
        d = dict(zip(m.name, m.position))
        for k, n in enumerate(BUMPERS):
            if f'bumper_{n}_joint' in d:
                self.bumper[k] = d[f'bumper_{n}_joint'] < HUNDIDO

    def imu_valida(self):
        return self.t_imu is not None and self.t() - self.t_imu <= IMU_MAX

    def al_comando(self, m):
        partes = m.data.split()
        c = partes[0] if partes else ''
        if c == 'armar':
            self.armado = True
            self.responder('>> Base ARMADA: se acepta /cmd_vel.')
        elif c in ('desarmar', 's'):
            if c == 'desarmar':
                self.armado = False
            if self.modo != 'libre':
                self.modo = 'parado'
            self.responder('>> Base DESARMADA.' if c == 'desarmar' else '>> Detenida.')
        elif c == 'r':
            ok = self.seg.rearmar(self.seta, self.roll, self.pitch, self.imu_valida())
            self.responder('>> Rearmado.' if ok else
                           '>> No se puede rearmar: seta apretada, base no nivelada o IMU sin datos.')
        elif c == 'wd' and len(partes) == 2 and partes[1].isdigit() and 50 <= int(partes[1]) <= 1000:
            self.seg.wd_ms = int(partes[1])
            self.responder(f'>> Watchdog de comandos: {self.seg.wd_ms} ms.')
        elif c in ('seta', 'soltar_seta'):
            self.seta = c == 'seta'
            self.responder('>> Seta ' + ('APRETADA (simulada).' if self.seta else 'suelta (simulada): r para rearmar.'))
        else:
            self.responder(f'>> "{m.data}" no está en la simulación (armar, desarmar, s, r, wd <ms>, seta, soltar_seta)')

    def paso(self):
        ahora = self.t()
        v, w = self.cmd if self.modo == 'v/w' else (0.0, 0.0)
        ms_sin_cmd = (ahora - self.t_cmd) * 1000 if self.t_cmd is not None else math.inf
        _, v, w = self.seg.filtrar(self.bumper, self.dist[0], self.seta, self.roll, self.pitch, ms_sin_cmd,
                                   self.imu_valida(), v, w)
        # Vencido el watchdog, el comando viejo se anula: no vuelve solo cuando llega otro mensaje
        if self.seg.estado == 'sin comandos' and self.modo != 'libre':
            self.modo = 'parado'
        cmd = Twist()
        cmd.linear.x, cmd.angular.z = v, w
        self.pub_cmd.publish(cmd)

        self.tick += 1
        stamp = self.get_clock().now().to_msg()
        if self.tick % 5 == 0:  # 10 Hz
            for k, n in enumerate(US):
                r = Range(radiation_type=Range.ULTRASOUND, field_of_view=0.26, min_range=0.02, max_range=4.0,
                          range=self.dist[k])
                r.header.stamp, r.header.frame_id = stamp, f'us_{n}'
                self.pub_rango[k].publish(r)
            self.pub_bumpers.publish(UInt8(data=sum(1 << k for k, b in enumerate(self.bumper) if b)))
        if self.tick % 50 == 0:  # 1 Hz
            b = BatteryState(voltage=11.8, present=True)  # LiPo 3S
            b.header.stamp = stamp
            self.pub_bateria.publish(b)
        if self.tick % 25 == 0:  # 2 Hz
            s = self.seg
            self.pub_estado.publish(String(data=(
                f'{"ARMADA" if self.armado else "DESARMADA"} modo={self.modo} seguridad={s.estado}'
                f'{" SETA" if self.seta else ""}{" no_avanza" if s.bloq_adelante else ""}'
                f'{"(frente_sin_eco)" if s.frente_sin_dato else ""} imu={"ok" if self.imu_valida() else "SIN_DATOS"}'
                ' rueda_izq=ninguna rueda_der=ninguna enlace: pings_fallidos=0 cortes=0')))


def main(args=None):
    rclpy.init(args=args)
    nodo = BaseSim()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
