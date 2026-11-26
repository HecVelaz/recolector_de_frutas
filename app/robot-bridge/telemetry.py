"""Estado de recepción y alarmas. No importa ROS y admite reloj de prueba."""
import copy
import math
import re
import threading
import time

TOPICS = {
    'base': ('/base/estado', 'Base'), 'arm': ('/brazo/estado', 'Brazo y servos'),
    'battery': ('/battery', 'Batería'), 'imu': ('/imu/data_raw', 'IMU'),
    'odom': ('/odom', 'Odometría de ruedas'), 'bumpers': ('/bumpers', 'Bumpers'),
    'range_front': ('/range/frente', 'Distancia frontal'),
    'range_left': ('/range/izq', 'Distancia izquierda'),
    'range_right': ('/range/der', 'Distancia derecha'),
    'range_lidar_left': ('/range/lidar_izq', 'LiDAR izquierdo (TFmini-S)'),
}


class TelemetryStore:
    def __init__(self, clock=time.monotonic, stale_after=3):
        self.clock, self.stale_after = clock, stale_after
        self.lock = threading.Lock()
        self.samples = {}

    def put(self, key, value, valid=True, reason=None):
        if key not in TOPICS:
            raise KeyError(key)
        with self.lock:
            self.samples[key] = (copy.deepcopy(value), self.clock(), valid, reason)

    def snapshot(self):
        with self.lock:
            samples = copy.deepcopy(self.samples)
        now = self.clock()
        sources = []
        for key, (topic, label) in TOPICS.items():
            sample = samples.get(key)
            age = max(0, round((now-sample[1])*1000)) if sample else None
            state = 'waiting' if sample is None else 'stale' if age > self.stale_after*1000 else 'fresh' if sample[2] else 'invalid'
            sources.append({'key':key, 'topic':topic, 'label':label, 'status':state, 'age_ms':age,
                            'value':sample[0] if state == 'fresh' else None,
                            'reason':sample[3] if sample else 'Todavía no se recibieron mensajes'})
        indexed = {s['key']:s for s in sources}
        # Presencia de placa: evidencia de mensajes de su estado; no deducirla del servidor web.
        boards = {key: {'status':indexed[key]['status'], 'age_ms':indexed[key]['age_ms']}
                  for key in ('base', 'arm')}
        alarms = []

        def alarm(code, severity, message, source):
            alarms.append({'code':code, 'severity':severity, 'message':message, 'source':source})

        for s in sources:
            if s['status'] != 'fresh':
                alarm(s['key'].upper() + '_' + s['status'].upper(), 'warning',
                      s['label'] + ': ' + {'waiting':'sin mensajes', 'stale':'datos vencidos', 'invalid':'medición inválida'}[s['status']], s['key'])
        base = indexed['base']['value'] or ''
        if re.search(r'\bSETA\b', base) or 'EMERGENCIA (seta)' in base:
            alarm('SETA', 'critical', 'Seta de emergencia informada por la base', 'base')
        if 'BATERIA_BAJA' in base:
            alarm('BATERIA_BAJA', 'warning', 'La base informa batería baja', 'base')
        if 'imu=SIN_DATOS' in base:
            alarm('IMU_SIN_DATOS', 'warning', 'La base informa IMU sin datos válidos', 'base')
        if 'no_avanza' in base or 'no_retrocede' in base:
            alarm('MOVIMIENTO_BLOQUEADO', 'warning', 'La base informa una dirección bloqueada', 'base')
        for side in ('izq', 'der'):
            match = re.search(r'rueda_' + side + r'=([^ ]+)', base)
            if match and match[1] != 'ninguna':
                alarm('RUEDA_' + side.upper(), 'critical', 'Falla de rueda ' + side + ': ' + match[1], 'base')
        safety = re.search(r'seguridad=(.*?)(?= SETA| BATERIA_BAJA| no_avanza| no_retrocede| imu=|$)', base)
        if safety and safety[1].strip().lower() != 'ok':
            alarm('SEGURIDAD_BASE', 'critical', 'Seguridad de la base: ' + safety[1].strip(), 'base')
        mask = indexed['bumpers']['value']
        if mask is not None and mask:
            # Se conserva máscara: su asignación física depende del firmware instalado.
            alarm('CONTACTO_BUMPER', 'critical', 'Contacto de bumper; máscara ' + str(mask), 'bumpers')
        alarms.sort(key=lambda a: {'critical':0, 'warning':1, 'info':2}[a['severity']])
        return {'sources':sources, 'boards':boards, 'alarm_details':alarms,
                'alarms':[a['message'] for a in alarms],
                'base_state':indexed['base']['value'], 'arm_state':indexed['arm']['value'],
                'battery_voltage':round(indexed['battery']['value'], 2) if indexed['battery']['value'] is not None else None,
                'base_freshness_known':True}


def finite_vector(values):
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def range_value(value, minimum, maximum):
    if value == math.inf:
        return {'kind':'out_of_range', 'meters':None}, True, None
    if math.isfinite(value) and minimum <= value <= maximum:
        return {'kind':'distance', 'meters':value}, True, None
    return None, False, 'Sin eco o distancia inválida'
