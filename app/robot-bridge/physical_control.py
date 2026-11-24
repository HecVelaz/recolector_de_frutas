"""Control manual coordinado en el puente local de Arturito."""

import asyncio
import logging
import re
import time
from threading import Lock
from time import monotonic
from typing import Literal

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from base_session import BaseSession, BaseSessionState
from control_gate import MAX_AGE_BY_SOURCE_MS, evaluate, trusted_client
from ros_base_output import MAX_ANGULAR_RAD_S, MAX_MANUAL_DUTY_PERCENT, MAX_PHYSICAL_LINEAR_M_S


Mode = Literal['base', 'arm', 'combined', 'homing']
ArmMotion = Literal['j1+', 'j1-', 'j2+', 'j2-', 'j3+', 'j3-']
BaseMotion = Literal['forward', 'backward', 'left', 'right']
ServoMotion = Literal['gripper_open', 'gripper_close', 'wrist_left', 'wrist_center', 'wrist_right']

LINEAR_LIMIT, TURN_LIMIT = MAX_PHYSICAL_LINEAR_M_S, MAX_ANGULAR_RAD_S   # giro como teleop.html (antes 0,15)
BASE_MOTIONS = {'forward': (LINEAR_LIMIT, 0.), 'backward': (-LINEAR_LIMIT, 0.),
                'left': (0., TURN_LIMIT), 'right': (0., -TURN_LIMIT)}
DRIVE_LIMITS = {'linear_m_s': LINEAR_LIMIT, 'angular_rad_s': TURN_LIMIT}
ARM_AXIS_LIMIT = 1.0   # rad/s a fondo y al 100 %: igual que teleop.html (que arranca al 60 %)
ARM_MOTIONS = {'j1+': (1, 0, 0), 'j1-': (-1, 0, 0), 'j2+': (0, 1, 0), 'j2-': (0, -1, 0),
               'j3+': (0, 0, 1), 'j3-': (0, 0, -1)}


def joint_velocity(values, scale):
    return 'jv ' + ' '.join(f'{axis * scale:.4f}' for axis in values) if any(values) else None
SERVOS = {'gripper_open': 'pz a', 'gripper_close': 'pz c', 'wrist_left': 'mn a',
          'wrist_center': 'mn 0', 'wrist_right': 'mn b'}
LEASE = .22
# Homing (21/11): lo hace el firmware a 1,5-5 °/s; con la Pi cargada un aviso de la app a veces tardaba > 0,22 s y
# cortaba el homing ya terminado. Soltar el botón lo sigue cortando, como mucho 1 s después
HOME_LEASE = 1.0
SESSION_LEASE = 3.0
BASE_STOP_TIMEOUT = 1.5
HOME_TIMEOUT = 120
PARK_TIMEOUT = 30
PARK_COMMAND = 'mv 3 17 4'
# Homing rechazado por el firmware con el cero ya conocido (20/11): el brazo frenado se asienta abajo (J2 2,2°, J3 2,9°),
# fuera de la franja del cuatro barras (con J2 < 3,4° J3 puede llegar a ~1°), o J2 quedó más arriba de 25°. Como pide el
# firmware, primero "j 2 <grados>" (también valida la franja) y otra vez "h". Un solo intento por homing
HOME_RECOVERY_TIMEOUT = 20   # 23/11: 10 -> 20 (el reposo coordinado tarda más que un j 2)
HOME_RECOVERY_TOLERANCE = .7
ANGLES = re.compile(r'(?:^|;)q=(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)(?:;|$)')


def home_recovery(detail, state):
    """(orden, destino de J2) para volver a intentar el homing tras el rechazo `detail` del firmware, o None."""
    angles = ANGLES.search(state or '')
    if not isinstance(detail, str) or angles is None:
        return None
    q3 = float(angles.group(3))
    if 'fuera de la franja' in detail:
        # Borde de arriba de la franja: J3 <= ~J2 desde J2 5,8° (config.h FRANJA_ARRIBA), con 1° de margen
        target = round(min(20., max(6., q3 + 2.)), 1)
        return f'j 2 {target:.1f}', target
    if 'Bajarla antes' in detail:
        # 23/11: con J3 en 24,7° J2 no podía bajar sola a 10° (la franja la deja >= ~J3): el reposo coordinado del
        # firmware baja las dos sin salir de la franja (J2 17°, J3 4°)
        return PARK_COMMAND, 17.
    return None
JOINT_STATES = re.compile(r'(?:^|;)e=([0-6]),([0-6]),([0-6])(?:;|$)')
ARM_HOLD_CORRECTION_S = 2.0   # quieto: cuánto puede durar el estado 1 (corrección del sostén)
ARM_SETTLE_S = 1.0   # margen tras 'jv 0 0 0' para que las articulaciones queden quietas
REFERENCED = re.compile(r'(?:^|;)c=111(?:;|$)')


class OpenManual(BaseModel):
    mode: Mode
    operator_present: Literal[True]
    wheels_off_ground: bool = False


class DriveAxes(BaseModel):
    forward: float = Field(ge=-1, le=1)
    turn: float = Field(ge=-1, le=1)

    def velocity(self):
        # Combinar giro y avance sin superar el esfuerzo de un mando a fondo.
        scale = max(1, abs(self.forward) + abs(self.turn))
        return LINEAR_LIMIT * self.forward / scale, TURN_LIMIT * self.turn / scale


class ArmAxes(BaseModel):
    swivel: float = Field(ge=-1, le=1)
    shoulder: float = Field(ge=-1, le=1)
    elbow: float = Field(ge=-1, le=1)

    def command(self, scale=ARM_AXIS_LIMIT * .6):
        return joint_velocity((self.swivel, self.shoulder, self.elbow), scale)


class ManualInput(BaseModel):
    sequence: int | None = Field(default=None, ge=1, le=2**63 - 1, strict=True)
    motion: BaseMotion | ArmMotion | Literal['home'] | None = None
    servo: ServoMotion | None = None
    arm_motion: ArmMotion | None = None
    drive: DriveAxes | None = None
    joints: ArmAxes | None = None
    gripper_open_percent: int | None = Field(default=None, ge=0, le=100, strict=True)
    wrist_degrees: int | None = Field(default=None, ge=-90, le=90, strict=True)
    gripper_speed_dps: int | None = Field(default=None, ge=5, le=360, strict=True)   # rampa de la pinza (pz w)
    wrist_speed_dps: int | None = Field(default=None, ge=5, le=360, strict=True)     # rampa del giro (mn w)
    speed_percent: int = Field(default=100, ge=0, le=100, strict=True)
    duty_percent: int | None = Field(default=None, ge=5, le=MAX_MANUAL_DUTY_PERCENT, strict=True)
    arm_speed_percent: int = Field(default=60, ge=10, le=100, strict=True)   # velocidad del brazo, como teleop.html

    def arm_command(self, name):
        scale = ARM_AXIS_LIMIT * self.arm_speed_percent / 100
        if self.joints:
            return self.joints.command(scale)
        return joint_velocity(ARM_MOTIONS[name], scale) if name in ARM_MOTIONS else None

    def is_neutral(self):
        """Sin movimiento continuo (ruedas ni articulaciones). Los servos van a posiciones o velocidades fijas: no cuentan
        (23/11: tras un corte de 0,22 s se espera una entrada neutra, y la app reenvía la pinza hasta que salga: con la
        pinza contada como movimiento quedaban esperándose y la pinza no respondía más)."""
        return not (self.motion or self.arm_motion or (self.drive and any(self.drive.velocity()))
                    or (self.joints and self.joints.command()))

    def servo_command(self):
        targets = (self.servo, self.gripper_open_percent, self.wrist_degrees, self.gripper_speed_dps,
                   self.wrist_speed_dps)
        if sum(target is not None for target in targets) > 1:
            raise HTTPException(409, 'Ajustá un servo a la vez')
        if self.gripper_speed_dps is not None:
            return f'pz w {self.gripper_speed_dps}'
        if self.wrist_speed_dps is not None:
            return f'mn w {self.wrist_speed_dps}'
        if self.gripper_open_percent is not None:
            return f'pz {round(1250 - 7.5 * self.gripper_open_percent)}'
        if self.wrist_degrees is not None:
            slope = 640 if self.wrist_degrees >= 0 else 650
            return f'mn {round(1500 - slope * self.wrist_degrees / 90)}'
        return SERVOS.get(self.servo)


class RosArmLink:
    def __init__(self, node):
        from std_msgs.msg import String

        self.node = node
        self.message = String
        self.publisher = node.create_publisher(String, '/brazo/comando', 1)
        self._lock = Lock()
        self._home_feedback = (None, None)
        self.home_detail = None
        self.home_error = None
        self.subscription = node.create_subscription(String, '/brazo/respuesta', self._read_reply, 10)

    def _read_reply(self, message):
        result, detail = None, None
        for line in message.data.splitlines():
            text = line.strip()
            if text.startswith(('HOMING,', '>> Homing listo:')):
                result = 'completed'
            elif text.startswith(('HOMING_ERROR,', '>> Homing CORTADO:', 'Homing:')):
                result = 'failed'
                detail = text.removeprefix('HOMING_ERROR,')
            elif text.startswith(('LLEGO,', 'PASO,')):   # PASO: fin de un mvp (de paso), como en punta.ejecutar
                result, detail = 'parked', text
            elif text.startswith('SERVO_LLEGO,'):
                result, detail = 'servo_ready', text
            elif text.startswith(('MV_ERROR,', 'Fuera de', 'J2 y J3 fuera', '>> El camino recto sale',
                                  'J1 sin cero', 'J2 sin cero', 'J3 sin cero', 'Hardware sin',
                                  'J1 pasada', 'Sobre la caja', '>> PLEGADO', 'Uso:')):
                result, detail = 'park_failed', text.removeprefix('MV_ERROR,')
            elif result == 'failed' and re.match(r'^>> J[123] CORTADA:', text) and 'cancelado' not in text:
                detail = text.removeprefix('>> ')
        if result:
            with self._lock:
                self._home_feedback = (monotonic(), result)
                self.home_error = detail
                self.home_detail = detail

    def home_feedback(self):
        with self._lock:
            return self._home_feedback

    def exclusive(self):
        return self.node.count_publishers('/brazo/comando') == 1 and self.node.count_subscribers('/brazo/comando') == 1

    def send(self, command):
        self.publisher.publish(self.message(data=command))


class PhysicalControl:
    def __init__(self, snapshot, base, arm, clock=monotonic, home_marker=None):
        self.snapshot, self.base, self.arm, self.clock = snapshot, base, arm, clock
        self.owner = self.mode = self.deadline = self.input_deadline = self.trial = self.motion = None
        self.awaiting_neutral = False
        self.last_sequence = None
        self.last_stop = (None, None)
        self.arm_settling_until = 0
        self.arm_correcting_since = None
        self.home_started = self.home_completed = self.park_started = None
        self.home_recovery = None      # (inicio, destino de J2) mientras J2 vuelve a la franja
        self.home_retried = False
        self.bench = False
        self.autonomous = False
        self.home_marker = home_marker
        self.home_unverified = home_marker is not None and home_marker.exists()
        self.arm_motion = None
        self.using_duty = False

    def arm_ready(self, state):
        return not self.home_unverified and bool(REFERENCED.search(state or ''))

    def blockers(self, mode, *, starting=False, evidence=None):
        evidence = evidence if evidence is not None else self.snapshot()
        base_state = evidence.get('base_state')
        fields = (base_state or '').split()
        drive = mode in ('base', 'combined')
        decision = evaluate(evidence, feature_enabled=True, authenticated=True, app_foreground=True,
                            physical_ready=True, base_only=True, allow_standby=starting or not drive,
                            allow_armed_standby=starting, allow_released_standby=starting)
        reasons = list(decision.reasons)
        # Solo brazo: una reconexión de la S3 (su suscripción a /cmd_vel desaparece un instante) no corta el brazo (23/11)
        if (drive and not self.base.exclusive()) or not self.arm.exclusive():
            reasons.append('Hay otro mando ROS activo o falta un controlador')
        if starting and fields[:1] not in (['ARMADA'], ['DESARMADA']):
            reasons.append('Estado del Móvil desconocido')
        if drive and not starting and fields[:1] != ['ARMADA']:
            reasons.append('Se perdió el mando del Móvil')
        if mode != 'base':
            if not drive and not starting and not BaseSession.stopped_base(base_state, False):
                reasons.append('El Móvil dejó de estar detenido')
            sources = {item['key']: item for item in evidence.get('sources', [])}
            arm = sources.get('arm', {})
            age = arm.get('age_ms')
            text = evidence.get('arm_state') or ''
            if arm.get('status') != 'fresh' or not isinstance(age, int) or age > MAX_AGE_BY_SOURCE_MS['arm']:
                reasons.append('Estado del brazo vencido')
            if self.arm_motion and not self.arm_ready(text):
                reasons.append('El brazo perdió su referencia')
            if self.autonomous and not self.arm_ready(text):
                reasons.append('El brazo perdió su referencia durante la recolección')
            states = JOINT_STATES.search(text)
            # Al soltar, el firmware frena pasando por 1 (y 2) hasta 0,6 s antes de quedar en 4 (medido 23/11)
            allowed = '012345' if self.arm_motion or self.clock() < self.arm_settling_until else '0234'
            if mode == 'homing' and self.home_started is not None:
                # 23/11: la recuperación puede ir al reposo coordinado (mv: estado 5), como el reposo final
                allowed = ('012345' if self.park_started is not None or self.home_recovery is not None
                           else '012346')
            if self.autonomous:
                allowed = '012345'
            # Quieto, "1 yendo" es la corrección del sostén cuando algo corre la articulación (al manejar la base en
            # combinado, 23/11): vale hasta ARM_HOLD_CORRECTION_S; más tiempo es una articulación que no vuelve.
            correcting = bool(states) and '1' in states.groups() and '1' not in allowed
            if not correcting:
                self.arm_correcting_since = None
            elif self.arm_correcting_since is None:
                self.arm_correcting_since = self.clock()
            if correcting and self.clock() - self.arm_correcting_since <= ARM_HOLD_CORRECTION_S:
                allowed += '1'
            if not states or any(state not in allowed for state in states.groups()):
                reasons.append('Brazo ocupado o en estado inválido')
        return reasons

    def base_feedback(self, starting=False, *, safe=None):
        state, received_at = self.base.feedback()
        if safe is None:
            safe = not self.blockers(self.mode, starting=starting)
        return dict(safe=safe, session_alive=self.owner is not None, base_state=state, received_at=received_at)

    async def prepare_base(self, owner):
        requested_at = None
        while self.owner == owner:
            checked_at = self.clock()
            evidence = self.snapshot()
            reasons = self.blockers(self.mode, starting=True, evidence=evidence)
            if reasons:
                raise HTTPException(409, reasons)
            state, received_at = self.base.feedback()
            odom = next(source for source in evidence['sources'] if source['key'] == 'odom')
            motion = odom['value'] or {}
            linear, angular = motion.get('linear_m_s'), motion.get('angular_rad_s')
            max_state_age = MAX_AGE_BY_SOURCE_MS['base'] / 1000
            odom_received_at = checked_at - (odom['age_ms'] + 1) / 1000
            confirmed = requested_at is None or (
                received_at is not None and min(received_at, odom_received_at) > requested_at)
            if (BaseSession.stopped_base(evidence['base_state'], False)
                    and BaseSession.stopped_base(state, False)
                    and received_at is not None and 0 <= self.clock() - received_at <= max_state_age
                    and isinstance(linear, (int, float)) and abs(linear) <= .005
                    and isinstance(angular, (int, float)) and abs(angular) <= .02
                    and confirmed):
                return state
            if requested_at is None:
                requested_at = self.clock()
                # El firmware detiene el Móvil al procesar este comando.
                self.base.request_disarm()
            elif self.clock() >= requested_at + BASE_STOP_TIMEOUT:
                raise HTTPException(409, 'El Móvil no confirmó la detención')
            await asyncio.sleep(.02)
        raise HTTPException(409, 'Se canceló la habilitación del mando')

    def stop(self, reason=None):
        mode, trial = self.mode, self.trial
        using_duty, autonomous = self.using_duty, self.autonomous
        interrupt_home = mode == 'homing' and self.home_started is not None and not self.home_completed
        if self.owner is not None and reason is not None:
            self.last_stop = (self.owner, reason)
            logging.getLogger(__name__).info('Mando detenido: %s', reason)
            arm_state = (self.snapshot() or {}).get('arm_state')   # 23/11: para diagnosticar cortes del brazo
            print(f'{time.strftime("%H:%M:%S")} mando detenido ({mode}): {reason} | brazo: {arm_state}', flush=True)
        self.owner = self.mode = self.deadline = self.input_deadline = self.trial = self.motion = None
        self.awaiting_neutral = False
        self.last_sequence = None
        self.arm_settling_until = 0
        self.arm_correcting_since = None
        self.home_started = self.home_completed = self.park_started = None
        self.home_recovery = None
        self.home_retried = False
        self.bench = False
        self.autonomous = False
        self.arm_motion = None
        self.using_duty = False
        try:
            if trial is not None:
                try:
                    if using_duty:
                        self.base.stop_duty()
                finally:
                    trial.stop()
        finally:
            if autonomous:
                self.arm.send('s')
            elif mode in ('arm', 'combined'):
                self.arm.send('jv 0 0 0')
            if interrupt_home:
                self.arm.send('s')

    def tick(self):
        if self.deadline is None:
            return
        now = self.clock()
        if now >= self.deadline:
            self.stop('Se perdió el enlace de mando. Volvé a habilitarlo cuando se conecte.')
            return
        reasons = self.blockers(self.mode)
        if reasons:
            self.stop(reasons)
            return
        if self.input_deadline is not None and now >= self.input_deadline:
            if self.autonomous:
                self.stop('Se interrumpió el control de la recolección')
                return
            if self.mode == 'homing':
                self.stop('Homing interrumpido por falta de comunicación. Volvé a iniciarlo.')
                return
            if self.trial is not None:
                self.drive_base(0., 0., 0, None)
            self.drive_arm(None, None)
            self.awaiting_neutral = True
            self.input_deadline = None
        if self.mode in ('base', 'combined'):
            self.trial.update(**self.base_feedback(safe=True))
            if self.trial.state != BaseSessionState.ARMED:
                self.stop('El controlador del Móvil dejó de confirmar que el mando está disponible.')

    async def open(self, owner, body, *, autonomous=False):
        self.tick()
        if self.owner is not None:
            raise HTTPException(409, 'Ya hay una sesión de mando')
        reasons = self.blockers(body.mode, starting=True)
        if reasons:
            raise HTTPException(409, reasons)
        self.owner, self.mode = owner, body.mode
        self.bench = body.wheels_off_ground
        self.autonomous = autonomous
        self.last_stop = (None, None)
        try:
            state = await self.prepare_base(owner)
            if body.mode in ('base', 'combined'):
                trial = self.trial = self.base.new_session()
                if not trial.begin(safe=True, base_state=state):
                    raise HTTPException(409, 'El controlador no está listo para habilitar el mando')
                while self.owner == owner and trial.state in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO):
                    await asyncio.sleep(.02)
                    if self.owner == owner:
                        trial.update(**self.base_feedback(starting=True))
                if self.owner != owner or trial.state != BaseSessionState.ARMED:
                    why = '; '.join(self.blockers(body.mode, starting=True)) or (self.base.feedback()[0] or 'sin estado')[:70]
                    raise HTTPException(409, f'El Móvil no confirmó el mando a velocidad cero ({why})')
            elif body.mode == 'arm':
                self.arm.send('jv 0 0 0')
        except BaseException:
            if self.owner == owner:
                self.stop()
            raise
        now = self.clock()
        self.deadline = now + SESSION_LEASE
        self.input_deadline = now + self.lease()

    def lease(self):
        return HOME_LEASE if self.mode == 'homing' else LEASE

    def mission_velocity(self, owner, linear, angular):
        self.tick()
        if not self.autonomous or owner != self.owner:
            prior, reason = self.last_stop
            raise RuntimeError(', '.join(reason) if prior == owner and isinstance(reason, list)
                               else reason if prior == owner and reason else 'Mando de recolección cerrado')
        self.drive_base(linear, angular, 100, None)
        now = self.clock()
        self.input_deadline = now + LEASE
        self.deadline = now + SESSION_LEASE

    def drive_base(self, linear, angular, speed, duty):
        active = bool(linear or angular) and (bool(speed) or duty is not None)
        if not active:
            if self.using_duty:
                self.base.stop_duty()
                self.using_duty = False
            if self.motion:
                self.trial.send_zero()
                self.trial.velocity_deadline = None
        else:
            factor = speed / 100
            if duty is None:
                if self.using_duty:
                    self.base.stop_duty()
                    self.using_duty = False
                output = None
            else:
                forward, turn = linear / LINEAR_LIMIT, angular / TURN_LIMIT
                left, right = forward - turn, forward + turn
                peak = max(1, abs(left), abs(right))
                output = lambda: self.base.send_duty(round(left * duty / peak),
                                                     round(right * duty / peak))
                self.using_duty = True
            if not self.trial.velocity(linear * factor, angular * factor, deadman=True,
                                       valid_for=LEASE, apply_output=output, **self.base_feedback()):
                raise HTTPException(409, 'La base rechazó el movimiento')
        self.motion = active

    def drive_arm(self, command, servo):
        if command and not self.arm_ready(self.snapshot().get('arm_state')):
            raise HTTPException(409, 'La pinza está disponible. Las articulaciones requieren completar el homing')
        if self.arm_motion and not command:
            self.arm.send('jv 0 0 0')
            self.arm_settling_until = self.clock() + ARM_SETTLE_S
            self.arm_motion = None
            if servo:
                # Priorizar la parada. El mando puede reenviar el servo en la próxima entrada.
                return False
        elif servo:
            # El firmware procesa los servos por separado. Una muestra del joystick
            # se omite para no sobrescribir el servo en la cola ROS de profundidad 1.
            self.arm.send(servo)
        elif command:
            self.arm.send(command)
        self.arm_motion = command
        return bool(servo)

    def input(self, owner, body):
        input_started_at = self.clock()
        self.tick()
        if owner != self.owner or self.deadline is None:
            previous_owner, reason = self.last_stop
            raise HTTPException(409, reason if owner == previous_owner else 'El mando está cerrado. Volvé a habilitarlo.')
        if self.autonomous:
            raise HTTPException(409, 'La sesión corresponde a una recolección')
        if self.last_sequence is not None and (body.sequence is None or body.sequence <= self.last_sequence):
            return 'ignored', False
        self.last_sequence = body.sequence
        if self.awaiting_neutral:
            if not body.is_neutral():
                return 'paused', False
            self.awaiting_neutral = False
        try:
            servo_sent = False
            servo = body.servo_command()
            if body.duty_percent is not None and not self.bench:
                raise HTTPException(409, 'El mando PWM solo está disponible en banco')
            if (body.drive and body.motion) or (body.joints and body.arm_motion):
                raise HTTPException(409, 'Usá una sola entrada por mando')
            if self.mode in ('base', 'combined'):
                if (body.motion and body.motion not in BASE_MOTIONS) or (
                        self.mode == 'base' and (servo or body.arm_motion or body.joints)):
                    raise HTTPException(409, 'Mando incompatible con la sesión de base')
                arm_command = body.arm_command(body.arm_motion)
                if arm_command and not self.arm_ready(self.snapshot().get('arm_state')):
                    raise HTTPException(409, 'Las articulaciones requieren completar el homing')
                linear, angular = body.drive.velocity() if body.drive else BASE_MOTIONS.get(body.motion, (0., 0.))
                self.drive_base(linear, angular, body.speed_percent, body.duty_percent)
                if self.mode == 'combined':
                    servo_sent = self.drive_arm(arm_command, servo)
            elif self.mode == 'homing':
                if body.motion != 'home' or servo or body.arm_motion or body.drive or body.joints:
                    raise HTTPException(409, 'Mantené presionado Hacer homing para continuar')
                if self.home_started is None:
                    self.home_unverified = True
                    if self.home_marker is not None:
                        self.home_marker.touch()
                    self.home_started = self.clock()
                    self.arm.send('h')
                elif self.home_recovery is not None:
                    started, target = self.home_recovery
                    received_at, reply = self.arm.home_feedback()
                    if received_at is not None and received_at >= started and reply in ('park_failed', 'failed'):
                        raise HTTPException(409, self.arm.home_detail or 'El brazo rechazó volver a la franja')
                    angles = ANGLES.search(self.snapshot().get('arm_state') or '')
                    joints = JOINT_STATES.search(self.snapshot().get('arm_state') or '')
                    if (angles and joints and joints.group(2) in '234'
                            and abs(float(angles.group(2)) - target) <= HOME_RECOVERY_TOLERANCE):
                        self.home_recovery = None
                        self.home_started = self.clock()
                        self.arm.send('h')
                    elif self.clock() - started >= HOME_RECOVERY_TIMEOUT:
                        raise HTTPException(409, f'J2 no llegó a {target:.1f}° para reintentar el homing')
                else:
                    received_at, reply = self.arm.home_feedback()
                    if self.park_started is not None:
                        if self.clock() - self.park_started >= PARK_TIMEOUT:
                            raise HTTPException(409, 'El brazo no confirmó la llegada al reposo')
                        if received_at is not None and received_at >= self.park_started:
                            if reply == 'park_failed':
                                raise HTTPException(409, self.arm.home_detail or 'El brazo rechazó el reposo')
                            if reply == 'parked':
                                self.home_completed = True
                                self.stop()
                                return 'completed', False
                    elif self.clock() - self.home_started >= HOME_TIMEOUT:
                        raise HTTPException(409, 'El homing superó el tiempo permitido')
                    elif received_at is not None and received_at >= self.home_started:
                        if reply == 'failed':
                            detail = self.arm.home_error
                            recovery = None if self.home_retried else home_recovery(
                                detail, self.snapshot().get('arm_state'))
                            if recovery is not None:
                                command, target = recovery
                                self.home_retried = True
                                self.home_recovery = (self.clock(), target)
                                self.arm.send(command)
                                self.deadline = input_started_at + SESSION_LEASE
                                self.input_deadline = input_started_at + self.lease()
                                return 'active', False
                            raise HTTPException(409, detail if isinstance(detail, str) and detail else 'El controlador interrumpió el homing')
                        state = self.snapshot().get('arm_state') or ''
                        joints = JOINT_STATES.search(state)
                        if reply == 'completed' and REFERENCED.search(state) and joints and all(
                                joint in '0234' for joint in joints.groups()):
                            if self.home_marker is not None:
                                self.home_marker.unlink(missing_ok=True)
                            self.home_unverified = False
                            self.park_started = self.clock()
                            self.arm.send(PARK_COMMAND)
            else:
                if body.drive or (body.motion and (body.joints or body.motion not in ARM_MOTIONS)):
                    raise HTTPException(409, 'Mando incompatible con la sesión de brazo')
                command = body.arm_command(body.arm_motion or body.motion)
                servo_sent = self.drive_arm(command, servo)
            self.deadline = input_started_at + SESSION_LEASE
            self.input_deadline = input_started_at + self.lease()
            return 'active', servo_sent
        except BaseException:
            self.stop()
            raise


def mount_physical_control(app, runtime, authorize):
    def session(request):
        if not trusted_client(request):
            raise HTTPException(403, 'El mando físico requiere el túnel local o Tailscale')
        authorize(request.headers)
        owner = request.headers.get('x-arturito-client', '')
        if not re.fullmatch('[a-f0-9-]{36}', owner):
            raise HTTPException(400, 'Identificador de sesión inválido')
        controller = runtime()
        if controller is None:
            raise HTTPException(503, 'Mando físico no disponible')
        return controller, owner

    @app.post('/api/v1/physical/session')
    async def open_session(body: OpenManual, request: Request):
        controller, owner = session(request)
        await controller.open(owner, body)
        return {'active': True}

    @app.post('/api/v1/physical/input')
    async def control_input(body: ManualInput, request: Request):
        controller, owner = session(request)
        try:
            status, servo_sent = controller.input(owner, body)
        except HTTPException as error:   # 21/11: el motivo en bridge.log (la app solo muestra el último)
            print(f'{time.strftime("%H:%M:%S")} mando rechazado ({controller.mode}): {error.detail}', flush=True)
            raise
        return {'active': status == 'active', 'paused': status == 'paused',
                'homing_completed': status == 'completed', 'servo_sent': servo_sent,
                'homing_parking': controller.park_started is not None}

    @app.delete('/api/v1/physical/session')
    async def close_session(request: Request):
        controller, owner = session(request)
        if controller.owner == owner:
            controller.stop()
        return {'active': False}
