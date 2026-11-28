"""Aviso acústico (H8 de la guía R2): buzzer pasivo MH-FMD en el GPIO 27 de la Pi 5.

El módulo trae un PNP y se activa por nivel BAJO: callado = pin en ALTO (en `/boot/firmware/config.txt`,
`gpio=27=op,dh` lo deja en alto desde el arranque). VCC a 3,3 V, nunca a 5 V (el PNP no se apagaría).

Escucha `/base/estado` (texto de la S3), `/bumpers` (bits frente, izq., der.) y `/brazo/estado` (texto de la WROOM).
`/buzzer/aviso` (String con el nombre de un sonido) deja que otro nodo o el puente pida uno (p. ej. 'mision').
Suena solo en los cambios: con la seta apretada desde el encendido no queda pitando.
"""

import re
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String, UInt8

# (frecuencia Hz, duración ms); 0 Hz = silencio. Arriba de ~650 Hz porque más abajo el buzzer suena débil (Keepon).
SONIDOS = {
    'listo': [(1319, 120)],
    'armada': [(1760, 80), (0, 60), (1760, 80)],
    'homing': [(1319, 90), (1760, 140)],
    'mision': [(1319, 90), (1568, 90), (1760, 160)],
    'fin': [(1760, 90), (1319, 160)],
    'bateria': [(880, 500), (0, 150), (880, 500)],
    'emergencia': [(1760, 180), (1175, 180)] * 5,
    'enlace': [(880, 150), (0, 100)] * 4,
}

ENLACE_S = 3.0   # sin /base/estado ni /brazo/estado durante este tiempo = enlace perdido (llegan a 2 y 10 Hz)


class Avisos:
    """Lógica sin ROS ni GPIO: recibe los mensajes y devuelve qué sonidos tocar (pruebas en test_buzzer.py)."""

    def __init__(self):
        self.prev = {}        # última condición vista de cada cosa; ausente = todavía no se vio (no suena)
        self.ultimo = {}      # hora del último mensaje de 'base' y 'brazo'

    def _cambio(self, clave, valor, sonido_si, sonido_no=None):
        anterior = self.prev.get(clave)
        self.prev[clave] = valor
        if anterior is None or anterior == valor:
            return []
        return [sonido_si] if valor else ([sonido_no] if sonido_no else [])

    def base(self, texto, ahora):
        self.ultimo['base'] = ahora
        s = self._cambio('enlace_base', True, 'listo')
        campos = texto.split()
        s += self._cambio('armada', bool(campos) and campos[0] == 'ARMADA', 'armada')
        s += self._cambio('emergencia_base', bool(re.search(r'\b(SETA|VUELCO)\b', texto)), 'emergencia')
        s += self._cambio('bateria', 'BATERIA_BAJA' in campos, 'bateria')
        return s

    def bumpers(self, bits):
        return self._cambio('bumper', bits != 0, 'emergencia')

    def brazo(self, texto, ahora):
        self.ultimo['brazo'] = ahora
        s = self._cambio('enlace_brazo', True, 'listo')
        return s + self._cambio('cero', bool(re.search(r'(?:^|;)c=111(?:;|$)', texto)), 'homing')

    def vigilar(self, ahora):
        s = []
        for parte, t in self.ultimo.items():
            s += self._cambio('enlace_' + parte, ahora - t < ENLACE_S, 'listo', 'enlace')
        return s


class Buzzer:
    """lgpio con PWM por software. Sin lgpio (notebook, simulación) no suena: solo deja el aviso en el log."""

    def __init__(self, gpio, activo_bajo, log):
        self.gpio, self.callado, self.h = gpio, 1 if activo_bajo else 0, None
        try:
            import lgpio
        except ImportError:
            log.warn('sin python3-lgpio: el buzzer no suena (sudo apt install python3-lgpio)')
            return
        for chip in range(5):   # el RP1 de la Pi 5 es gpiochip4 o gpiochip0 según el kernel
            try:
                h = lgpio.gpiochip_open(chip)
            except lgpio.error:
                continue
            if 'rp1' in lgpio.gpio_get_chip_info(h)[3].lower():
                self.lg, self.h = lgpio, h
                lgpio.gpio_claim_output(h, gpio, self.callado)
                log.info(f'buzzer en gpiochip{chip}, GPIO {gpio}')
                return
            lgpio.gpiochip_close(h)
        log.warn('no encontré el gpiochip del RP1: el buzzer no suena')

    def tono(self, hz):
        if self.h is None:
            return
        if hz > 0:
            self.lg.tx_pwm(self.h, self.gpio, hz, 50)   # cuadrada al 50 %: invertirla no cambia nada
        else:
            # Callado = PWM fijo al 100 % (activo en bajo) o al 0 %. Cortar el PWM y escribir el pin no sirve: el hilo
            # de lgpio deja el último nivel en bajo (probado en la Pi el 27/11); frecuencia 0 da 'bad PWM micros'.
            self.lg.tx_pwm(self.h, self.gpio, 1000, 100 * self.callado)

    def cerrar(self):
        if self.h is not None:
            self.tono(0)
            self.lg.gpiochip_close(self.h)


class NodoBuzzer(Node):
    def __init__(self):
        super().__init__('nodo_buzzer')
        gpio = self.declare_parameter('gpio', 27).value
        activo_bajo = self.declare_parameter('activo_bajo', True).value
        self.buzzer = Buzzer(gpio, activo_bajo, self.get_logger())
        self.avisos = Avisos()
        self.cola, self.fin_nota = [], 0.0
        self.create_subscription(String, '/base/estado', lambda m: self.tocar(self.avisos.base(m.data, time.monotonic())), 10)
        self.create_subscription(UInt8, '/bumpers', lambda m: self.tocar(self.avisos.bumpers(m.data)), 10)
        self.create_subscription(String, '/brazo/estado', lambda m: self.tocar(self.avisos.brazo(m.data, time.monotonic())), 10)
        self.create_subscription(String, '/buzzer/aviso', lambda m: self.tocar([m.data.strip()]), 10)
        self.create_timer(0.01, self.paso)
        self.create_timer(0.5, lambda: self.tocar(self.avisos.vigilar(time.monotonic())))
        self.tocar(['listo'])

    def tocar(self, nombres):
        for n in nombres:
            if n not in SONIDOS:
                self.get_logger().warn(f'sonido desconocido: {n!r}')
                continue
            self.get_logger().info(f'aviso: {n}')
            if n in ('emergencia', 'enlace'):   # las alarmas pasan adelante de lo que estaba sonando
                self.cola, self.fin_nota = [], 0.0
            self.cola += SONIDOS[n] + [(0, 80)]

    def paso(self):
        ahora = time.monotonic()
        if ahora < self.fin_nota:
            return
        if not self.cola:
            if self.fin_nota:
                self.buzzer.tono(0)
                self.fin_nota = 0.0
            return
        hz, ms = self.cola.pop(0)
        self.buzzer.tono(hz)
        self.fin_nota = ahora + ms / 1000


def main():
    rclpy.init()
    nodo = NodoBuzzer()
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        nodo.buzzer.cerrar()
        nodo.destroy_node()
        rclpy.try_shutdown()
