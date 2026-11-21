"""Secuencia de armado de base para ensayos con transportes inyectados."""

from enum import Enum
from math import isfinite
from time import monotonic

from control_gate import MAX_AGE_BY_SOURCE_MS
from ros_base_output import MAX_ANGULAR_RAD_S, MAX_LINEAR_M_S

# Con /base/estado a 2 Hz, 1 s eran 2 muestras y perder una cortaba el armado (21/11): 2 s son 4
CONFIRM_S = 2.0


class BaseSessionState(str, Enum):
    DISARMED = 'disarmed'
    ARMING = 'arming'
    VERIFYING_ZERO = 'verifying_zero'
    ARMED = 'armed'
    STOPPED = 'latched_stop'


class BaseSession:
    def __init__(self, velocity_output, *, request_arm, request_disarm, clock=monotonic, linear_limit=MAX_LINEAR_M_S):
        self.output = velocity_output
        self.request_arm = request_arm
        self.request_disarm = request_disarm
        self.clock = clock
        self.linear_limit = linear_limit
        self.state = BaseSessionState.DISARMED
        self.arm_requested_at = None
        self.velocity_deadline = None
        self.first_zero_at = None
        self.last_zero_at = None

    @staticmethod
    def stopped_base(state_text, arming):
        fields = (state_text or '').split()
        state = 'ARMADA' if arming else 'DESARMADA'
        return fields[:2] == [state, 'modo=parado']

    def begin(self, *, safe, base_state):
        if self.state != BaseSessionState.DISARMED or not safe or not self.stopped_base(base_state, False):
            return False
        self.output.stop()
        self.arm_requested_at = self.clock()
        self.state = BaseSessionState.ARMING
        try:
            self.request_arm()
        except Exception:
            self.stop()
            raise
        return True

    def update(self, *, safe, session_alive, base_state, received_at):
        if self.state not in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO, BaseSessionState.ARMED):
            return
        now = self.clock()
        max_base_age = MAX_AGE_BY_SOURCE_MS['base'] / 1000
        if not safe or not session_alive or received_at is None or not 0 <= now - received_at <= max_base_age:
            self.stop()
            return
        if self.state == BaseSessionState.ARMING:
            if now >= self.arm_requested_at + CONFIRM_S:
                self.stop()
            elif self.arm_requested_at < received_at and self.stopped_base(base_state, True):
                self.send_zero()
                self.first_zero_at = self.last_zero_at
                self.state = BaseSessionState.VERIFYING_ZERO
            return
        fields = (base_state or '').split()
        if fields[:1] != ['ARMADA']:
            self.stop()
        elif self.state == BaseSessionState.VERIFYING_ZERO:
            if now >= self.first_zero_at + CONFIRM_S:
                self.stop()
            elif (received_at > self.first_zero_at
                  and fields[1:3] in (['modo=parado', 'seguridad=ok'], ['modo=v/w', 'seguridad=ok'])):
                self.state = BaseSessionState.ARMED
            elif now >= self.last_zero_at + 0.08:
                self.send_zero()
        elif 'seguridad=ok' not in fields:
            self.stop()
        elif self.velocity_deadline is not None and now >= self.velocity_deadline:
            self.stop()
        elif self.velocity_deadline is None and now >= self.last_zero_at + 0.08:
            self.send_zero()

    def send_zero(self):
        try:
            self.output.stop()
        except Exception:
            self.stop()
            raise
        self.last_zero_at = self.clock()

    def velocity(self, linear, angular, *, deadman, safe, session_alive, base_state, received_at,
                 valid_for=0.25, apply_output=None):
        self.update(safe=safe, session_alive=session_alive, base_state=base_state, received_at=received_at)
        if self.state != BaseSessionState.ARMED:
            return False
        if not deadman:
            self.stop()
            return False
        if (not isfinite(linear) or not -self.linear_limit <= linear <= self.linear_limit
                or not isfinite(angular) or not -MAX_ANGULAR_RAD_S <= angular <= MAX_ANGULAR_RAD_S
                or not 0 < valid_for <= 0.25):
            self.stop()
            return False
        fields = base_state.split()
        if ((linear > 0 and any(field.startswith('no_avanza') for field in fields))
                or (linear < 0 and 'no_retrocede' in fields)):
            self.stop()
            return False
        self.velocity_deadline = self.clock() + valid_for
        try:
            if apply_output is None:
                self.output.send(linear, angular)
            else:
                apply_output()
        except Exception:
            self.stop()
            raise
        return True

    def stop(self):
        if self.state == BaseSessionState.STOPPED:
            return
        self.state = BaseSessionState.STOPPED
        self.velocity_deadline = None
        try:
            self.output.stop()
        finally:
            self.request_disarm()
