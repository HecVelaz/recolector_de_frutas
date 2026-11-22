"""Puerta de control pura: no importa ROS, no publica y empieza bloqueada."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite
import re
import time


class GateState(str, Enum):
    BLOCKED = 'blocked'
    READY = 'ready'
    ENABLED = 'enabled'
    ACTIVE = 'active'
    LATCHED_STOP = 'latched_stop'


class ControlMode(str, Enum):
    OBSERVATION = 'observation'
    MANUAL = 'manual'
    AUTONOMOUS = 'autonomous'


@dataclass(frozen=True)
class GateDecision:
    ready: bool
    reasons: tuple[str, ...]


REQUIRED = ('base', 'arm', 'battery', 'odom', 'bumpers', 'imu', 'range_front')
DEFAULT_MAX_AGE_MS = 500
# base: /base/estado llega a 2 Hz por micro-ROS best effort; 1100 ms tolera una muestra perdida (antes 650: cortaba)
# arm: /brazo/estado a 10 Hz; con la Pi cargada (planificador arrancando) hubo un hueco > 350 ms al abrir el mando
# de la recolección (21/11): 600 ms = 6 muestras
MAX_AGE_BY_SOURCE_MS = {'base': 1100, 'battery': 1250, 'arm': 600}


def watchdog_standby(state, *, armed=False, allow_released=False):
    fields = (state or '').split()
    modes = ('modo=parado', 'modo=libre') if allow_released else ('modo=parado',)
    return (len(fields) >= 4 and fields[0] == ('ARMADA' if armed else 'DESARMADA')
            and fields[1] in modes
            and fields[2:4] == ['seguridad=sin', 'comandos'])


def evaluate(snapshot, *, feature_enabled=False, authenticated=False,
             app_foreground=False, physical_ready=False,
             mode=ControlMode.MANUAL, allow_simulation=False, base_only=False,
             allow_standby=False, allow_armed_standby=False, allow_released_standby=False):
    """Evalúa solo evidencia; desconocido o contradictorio bloquea."""
    reasons = []
    if not feature_enabled:
        reasons.append('CONTROL_DISABLED')
    if not authenticated:
        reasons.append('NOT_AUTHENTICATED')
    if not app_foreground:
        reasons.append('APP_NOT_FOREGROUND')
    if not physical_ready:
        reasons.append('PHYSICAL_CHECK_PENDING')
    simulated = snapshot.get('simulated') and snapshot.get('source') == 'simulation'
    if not (allow_simulation and simulated) and (snapshot.get('simulated') or snapshot.get('source') != 'ros2'):
        reasons.append('NOT_REAL_ROS_SOURCE')
    if not snapshot.get('upstream_available'):
        reasons.append('ROS_UNAVAILABLE')
    if mode == ControlMode.AUTONOMOUS and not snapshot.get('geofence_enforced'):
        reasons.append('GEOFENCE_NOT_ENFORCED')

    sources = {x.get('key'): x for x in snapshot.get('sources', [])}
    for key in REQUIRED:
        if base_only and key == 'arm':
            continue
        value = sources.get(key)
        if not value or value.get('status') != 'fresh' or not isinstance(value.get('age_ms'), int):
            reasons.append(key.upper() + '_NOT_FRESH')
        elif value['age_ms'] > MAX_AGE_BY_SOURCE_MS.get(key, DEFAULT_MAX_AGE_MS):
            reasons.append(key.upper() + '_TOO_OLD')

    base = snapshot.get('base_state') or ''
    base_fields = base.split()
    standby = (allow_standby and watchdog_standby(base, allow_released=allow_released_standby)) or (
        allow_armed_standby and watchdog_standby(base, armed=True, allow_released=allow_released_standby))
    if 'seguridad=ok' not in base_fields and not standby:
        reasons.append('BASE_SAFETY_NOT_OK')
    for marker, code in (
        ('rueda_izq=ninguna', 'LEFT_WHEEL_FAULT'),
        ('rueda_der=ninguna', 'RIGHT_WHEEL_FAULT'),
    ):
        if marker not in base_fields:
            reasons.append(code)
    if 'imu=ok' not in base_fields:
        reasons.append('BASE_IMU_NOT_OK')
    if re.search(r'\b(SETA|VUELCO|BATERIA_BAJA)\b', base):
        reasons.append('BASE_CRITICAL_FLAG')
    if sources.get('bumpers', {}).get('value') != 0:
        reasons.append('BUMPER_ACTIVE_OR_UNKNOWN')
    battery = snapshot.get('battery_voltage')
    if not isinstance(battery, (int, float)) or not isfinite(battery) or battery < 10.5:
        reasons.append('BATTERY_TOO_LOW_OR_UNKNOWN')

    if not base_only:
        arm = snapshot.get('arm_state') or ''
        if not re.search(r'(?:^|;)c=111(?:;|$)', arm):
            reasons.append('ARM_NOT_HOMED')
        match = re.search(r'(?:^|;)e=([0-6]),([0-6]),([0-6])(?:;|$)', arm)
        if not match or any(int(x) in (1, 5, 6) for x in match.groups()):
            reasons.append('ARM_BUSY_OR_INVALID')
    return GateDecision(not reasons, tuple(dict.fromkeys(reasons)))


class ControlGate:
    """Máquina local de lease; no conoce transportes ni comandos del robot."""
    def __init__(self, clock=time.monotonic, lease_timeout=.25):
        self.clock, self.lease_timeout = clock, lease_timeout
        self.state, self.owner, self.deadline = GateState.BLOCKED, None, None

    def prepare(self, owner, decision):
        self.check()
        if self.owner is not None and owner != self.owner and self.state in (
                GateState.READY, GateState.ENABLED, GateState.ACTIVE):
            return False
        self.revoke(latched=False)
        if decision.ready and owner:
            self.state, self.owner = GateState.READY, owner
            return True
        return False

    def enable(self, owner):
        if self.state != GateState.READY or owner != self.owner:
            return False
        self.state, self.deadline = GateState.ENABLED, self.clock() + self.lease_timeout
        return True

    def heartbeat(self, owner, deadman=False):
        self.check()
        if owner != self.owner or self.state not in (GateState.ENABLED, GateState.ACTIVE):
            return False
        self.deadline = self.clock() + self.lease_timeout
        self.state = GateState.ACTIVE if deadman else GateState.ENABLED
        return True

    def check(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            self.revoke(latched=True)
        return self.state

    def revoke(self, latched=True):
        self.state = GateState.LATCHED_STOP if latched else GateState.BLOCKED
        self.owner, self.deadline = None, None

