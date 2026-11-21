"""Puente de observación y perfiles explícitos de control."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
import time

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from base_session import BaseSessionState
from control_gate import (DEFAULT_MAX_AGE_MS, MAX_AGE_BY_SOURCE_MS, REQUIRED, ControlGate, ControlMode,
                          GateDecision, GateState, evaluate as evaluate_control)
from geometry import validate
from ros_base_output import MAX_ANGULAR_RAD_S, MAX_BENCH_PULSE_M_S, MAX_LINEAR_M_S
from telemetry import TelemetryStore
from vision import CAMERAS, CameraFrames
from vision_3d import StereoReadings, make_origin, with_displacement


class PrepareRequest(BaseModel):
    app_foreground: bool = False
    physical_ready: bool = False
    mode: ControlMode = ControlMode.MANUAL
    arm_physically_isolated: bool = False
    wheels_off_ground: bool = False


class HeartbeatRequest(BaseModel):
    deadman: bool = False


class BaseManualRequest(BaseModel):
    linear_m_s: float = Field(ge=-MAX_LINEAR_M_S, le=MAX_LINEAR_M_S)
    angular_rad_s: float = Field(ge=-MAX_ANGULAR_RAD_S, le=MAX_ANGULAR_RAD_S)
    deadman: bool


class ArmManualRequest(BaseModel):
    j1_deg: float = Field(ge=-118, le=118)
    j2_deg: float = Field(ge=-90, le=90)
    j3_deg: float = Field(ge=-90, le=90)
    deadman: bool


class BenchPulseRequest(BaseModel):
    linear_m_s: float = Field(gt=0, le=MAX_BENCH_PULSE_M_S)
    duration_ms: int = Field(ge=40, le=200, strict=True)
    deadman: bool


class CollectionRequest(BaseModel):
    operator_present: bool
    lemons: int = Field(1, ge=1, le=5, strict=True)   # limones por parada (recolectar.py --limones)
    to_basket: bool = True                           # False: uno solo y queda en la pinza (--sin-soltar)


def create_app(source=None, data_dir=None, token=None, estado_url=None, control_dry_run=None,
               *, simulate_base_output=False, isolated_base_link=None, base_zero_test=False,
               isolated_pulse_test=False, base_pulse_test=False, isolated_floor_guard=None,
               physical_manual=False):
    source = source or os.getenv('ARTURITO_SOURCE', 'simulation')
    if source not in ('simulation', 'estado', 'ros2'):
        raise ValueError('ARTURITO_SOURCE debe ser simulation, estado o ros2')
    token = token if token is not None else os.getenv('ARTURITO_TOKEN', '')
    data_dir = Path(data_dir or os.getenv('ARTURITO_DATA_DIR', 'data'))
    estado_url = estado_url or os.getenv('ARTURITO_ESTADO_URL', 'http://127.0.0.1:8000/estado')
    latest = {'value': None, 'available': False}
    store = TelemetryStore()
    camera_frames = CameraFrames()
    stereo = StereoReadings()
    restore = os.getenv('ARTURITO_RESTORE_ORIGIN_JSON') if physical_manual else None
    navigation_origin = json.loads(restore) if restore else None
    origin_capture = asyncio.Lock()
    reader = None
    gate = ControlGate()
    control_dry_run = (os.getenv('ARTURITO_CONTROL_DRY_RUN', '0') == '1'
                       if control_dry_run is None else bool(control_dry_run))
    if simulate_base_output and (source != 'simulation' or not control_dry_run):
        raise ValueError('La salida simulada requiere un ensayo aislado con origen simulation')
    if isolated_base_link is not None and not simulate_base_output:
        raise ValueError('El enlace de prueba de base requiere salida simulada')
    bench_test = base_zero_test or base_pulse_test
    if physical_manual and (source != 'ros2' or not token or bench_test or control_dry_run):
        raise ValueError('El mando físico requiere ROS real, autenticación y un perfil exclusivo')
    physical_controller = None
    collection = None
    if base_zero_test and base_pulse_test:
        raise ValueError('Seleccioná un solo perfil de banco')
    if bench_test and (source != 'ros2' or not token or control_dry_run):
        raise ValueError('La prueba de banco requiere ROS real y una clave')
    if isolated_pulse_test and (isolated_base_link is None or not token):
        raise ValueError('La prueba de pulso requiere un enlace ROS aislado y autenticación')
    if isolated_floor_guard is not None and not (source == 'simulation' and isolated_pulse_test):
        raise ValueError('La comprobación de piso solo se admite con pulso y ROS aislados')
    base_link = isolated_base_link
    simulated_base_command = None
    base_trial = None

    def base_output(state):
        nonlocal simulated_base_command
        if simulated_base_command is not None:
            linear, angular, deadline = simulated_base_command
            if state == GateState.ACTIVE and gate.clock() < deadline:
                return {'linear_m_s':linear, 'angular_rad_s':angular}
            simulated_base_command = None
        return {'linear_m_s':0.0, 'angular_rad_s':0.0}

    async def poll():
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            while True:
                try:
                    response = await client.get(estado_url)
                    response.raise_for_status()
                    value = response.json()['estado']
                    if value is not None and not isinstance(value, str):
                        raise ValueError('estado no es texto')
                    latest.update(value=value, available=True)
                except (httpx.HTTPError, ValueError, KeyError):
                    latest.update(value=None, available=False)
                await asyncio.sleep(1)

    def stop_trial():
        if base_trial is not None and base_trial.state in (BaseSessionState.ARMING,
                                                          BaseSessionState.VERIFYING_ZERO, BaseSessionState.ARMED):
            base_trial.stop()
            return True
        return False

    def compatible_base():
        return not bench_test or base_link is not None and base_link.exclusive()

    def floor_reason(linear=0.0, duration=0.0):
        return isolated_floor_guard.check(linear, duration) if isolated_floor_guard is not None else None

    def with_floor_check(decision):
        reason = floor_reason()
        return GateDecision(False, decision.reasons + (reason,)) if reason else decision

    def trial_feedback(session_alive):
        text, received_at = base_link.feedback()
        evidence = dict(snapshot(), base_state=text)
        handshaking = base_trial.state in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO)
        decision = evaluate_control(evidence, feature_enabled=True, authenticated=True,
                                    app_foreground=True, physical_ready=True, allow_simulation=simulate_base_output,
                                    base_only=bench_test, allow_standby=base_trial.state != BaseSessionState.ARMED,
                                    allow_armed_standby=handshaking)
        stationary = True
        if bench_test and base_trial.velocity_deadline is None:
            odom = next((item['value'] for item in evidence['sources'] if item['key'] == 'odom'), None)
            stationary = (odom is not None and abs(odom['linear_m_s']) <= 0.005
                          and abs(odom['angular_rad_s']) <= 0.02)
        current_linear = current_duration = 0.0
        if simulated_base_command is not None:
            current_linear, _, deadline = simulated_base_command
            current_duration = max(0.0, deadline - gate.clock())
        return dict(safe=decision.ready and compatible_base() and stationary
                         and floor_reason(current_linear, current_duration) is None,
                    session_alive=session_alive, base_state=text, received_at=received_at)

    async def monitor_trial():
        while True:
            if base_trial is not None and base_trial.state == BaseSessionState.ARMED:
                state = gate.check()
                base_trial.update(**trial_feedback(state in (GateState.ENABLED, GateState.ACTIVE)))
                if base_trial.state == BaseSessionState.STOPPED:
                    gate.revoke(latched=True)
            await asyncio.sleep(0.02)

    async def monitor_physical():
        while True:
            try:
                physical_controller.tick()
            except Exception:
                logging.exception('Se perdió el control físico')
                try:
                    physical_controller.stop()
                except Exception:
                    logging.exception('Falló la publicación de parada; quedan los watchdogs del firmware')
            await asyncio.sleep(0.02)

    @asynccontextmanager
    async def lifespan(app):
        nonlocal reader, base_link, physical_controller, collection
        if source == 'ros2':
            from ros_source import RosReader
            reader = RosReader(store, node_name='arturito_banco_base' if bench_test else 'arturito_observador',
                               camera_frames=None if bench_test else camera_frames,
                               stereo=None if bench_test else stereo,
                               marker_tools=Path(os.environ.get('ARTURITO_MARKER_TOOLS') or
                                                 Path.home() / 'scripts/27-aruco-arbol/tools') if physical_manual else None)
            if bench_test:
                from ros_base_link import RosBaseLink
                base_link = (RosBaseLink.for_robot_pulse(reader.node) if base_pulse_test
                             else RosBaseLink.for_robot(reader.node))
            if physical_manual:
                from collection_mission import CollectionMission
                from physical_control import PhysicalControl, RosArmLink
                from ros_base_link import RosBaseLink
                physical_controller = PhysicalControl(snapshot, RosBaseLink.for_manual_control(reader.node),
                                                      RosArmLink(reader.node),
                                                      home_marker=data_dir / 'arm-homing-pending')
                marker_tools = os.environ.get('ARTURITO_MARKER_TOOLS') or Path.home() / 'scripts/27-aruco-arbol/tools'
                collection = CollectionMission(physical_controller, stereo, data_dir, marker_tools)
        task = asyncio.create_task(poll()) if source == 'estado' else None
        trial_monitor = asyncio.create_task(monitor_trial()) if base_link is not None else None
        physical_monitor = asyncio.create_task(monitor_physical()) if physical_controller is not None else None
        try:
            yield
        finally:
            if collection is not None:
                await collection.stop()
            if physical_monitor:
                physical_monitor.cancel()
                try:
                    await physical_monitor
                except asyncio.CancelledError:
                    pass
                try:
                    physical_controller.stop()
                except Exception:
                    logging.exception('Falló la parada al cerrar el puente')
            if trial_monitor:
                trial_monitor.cancel()
                try:
                    await trial_monitor
                except asyncio.CancelledError:
                    pass
                stop_trial()
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            if reader:
                reader.close()

    app = FastAPI(title='Arturito · control seguro en seco', version='1.1', lifespan=lifespan)

    def authorize(headers):
        if token and not hmac.compare_digest(headers.get('authorization', ''), f'Bearer {token}'):
            raise HTTPException(401, 'Clave de conexión incorrecta')

    if physical_manual:
        from physical_control import DRIVE_LIMITS, mount_physical_control
        mount_physical_control(app, lambda: physical_controller, authorize)

    def current_odometry(limit_ms=500):
        return next((s['value'] for s in store.snapshot()['sources']
                     if s['key'] == 'odom' and s['status'] == 'fresh' and s['age_ms'] <= limit_ms), None)

    if physical_manual:
        def mission_operator(request):
            authorize(request.headers)
            operator = request.headers.get('x-arturito-client', '')
            if request.client is None or request.client.host != '127.0.0.1' or not re.fullmatch('[a-f0-9-]{36}', operator):
                raise HTTPException(403, 'La recolección requiere el túnel local y una sesión válida')
            if collection is None:
                raise HTTPException(503, 'La recolección no está disponible')
            return operator

        @app.post('/api/v1/mission/session')
        async def start_mission(body: CollectionRequest, request: Request):
            operator = mission_operator(request)
            if not body.operator_present or origin_capture.locked():
                raise HTTPException(409, 'Confirmá la supervisión local y esperá a que termine la medición')
            return collection.start(operator, navigation_origin, body.lemons, body.to_basket)

        @app.post('/api/v1/mission/heartbeat')
        async def mission_heartbeat(request: Request):
            return collection.heartbeat(mission_operator(request))

        @app.delete('/api/v1/mission/session')
        async def stop_mission(request: Request):
            return await collection.stop(mission_operator(request))

        @app.post('/api/v1/navigation/origin')
        async def capture_origin(request: Request):
            nonlocal navigation_origin
            authorize(request.headers)
            if reader is None or not reader.available or collection is None:
                raise HTTPException(503, 'La visión estéreo y las herramientas de recolección deben estar disponibles')
            if origin_capture.locked():
                raise HTTPException(409, 'Ya se está midiendo el limón')
            if collection.active:
                raise HTTPException(409, 'Detené la recolección antes de volver a calcular el cero')

            def stationary_pose():
                odom = current_odometry(250)
                if (physical_controller is None or physical_controller.owner is not None or odom is None
                        or abs(odom['linear_m_s']) > .005 or abs(odom['angular_rad_s']) > .02):
                    return None
                return odom

            async with origin_capture:
                if stationary_pose() is None:
                    raise HTTPException(409, 'Mantené el Móvil quieto y soltá los mandos para fijar el cero')
                # 21/11: el cero es la pose actual respecto del limón más cercano (ya no la marca ArUco)
                try:
                    lemon, seen = await collection.measure_origin(lambda: stationary_pose() is not None)
                except (ValueError, RuntimeError, ImportError, OSError) as error:
                    raise HTTPException(409, str(error)) from error
                odom = stationary_pose()
                if odom is None:
                    raise HTTPException(409, 'No se pudo confirmar que el Móvil está quieto')
                from collection_mission import make_lemon_origin
                navigation_origin = make_lemon_origin(lemon, seen, odom)
                return with_displacement(navigation_origin, odom)

    def snapshot():
        now = int(time.time()*1000)
        simulated = source == 'simulation'
        angle = time.monotonic()/30
        result = {'schema_version':1, 'timestamp_ms':now, 'source':source, 'simulated':simulated,
                'upstream_available':True if simulated else latest['available'],
                # El servicio antiguo no informa antigüedad del mensaje: no inventarla.
                'base_state': 'DESARMADA · ejemplo' if simulated else latest['value'],
                'base_freshness_known':simulated,
                'gps':{'latitude':-25.3307 + .0002*math.sin(angle), 'longitude':-57.5156 + .0002*math.cos(angle),
                       'timestamp_ms':now, 'simulated':True} if simulated else None,
                'battery_voltage':11.8 if simulated else None,
                'alarms':[] if simulated else None,
                'commands_enabled':base_pulse_test or physical_manual, 'geofence_enforced':False}
        if physical_manual:
            result['physical_manual'] = 'supervised_manual'
            result['manual_analog'] = True
            result['manual_servo_positions'] = True
            result['manual_drive_limits'] = DRIVE_LIMITS
        if source == 'ros2':
            result.update(store.snapshot())
            result['stereo'] = stereo.snapshot()
            if navigation_origin is not None:
                odom = next((s['value'] for s in result['sources']
                             if s['key'] == 'odom' and s['status'] == 'fresh' and s['age_ms'] <= 500), None)
                result['navigation_origin'] = with_displacement(navigation_origin, odom)
            if physical_controller is not None:
                result['manual_arm_ready'] = physical_controller.arm_ready(result['arm_state'])
            if collection is not None:
                result['collection'] = collection.snapshot()
            result['upstream_available'] = reader is not None and reader.available
            if not result['upstream_available']:
                message = 'El lector ROS no está disponible; no se puede confirmar el estado del robot'
                result['alarms'].append(message)
                result['alarm_details'].append({'code':'ROS_UNAVAILABLE', 'severity':'critical', 'message':message, 'source':'ros2'})
        if simulate_base_output:
            result.update(
                base_state='DESARMADA modo=parado seguridad=ok imu=ok rueda_izq=ninguna rueda_der=ninguna',
                arm_state='q=0,0,0;e=3,3,3;c=111;fc=000;pz=-1;mn=-1',
                sources=[{'key':key, 'label':key, 'topic':'simulado', 'status':'fresh',
                          'age_ms':0, 'value':0 if key == 'bumpers' else None} for key in REQUIRED],
            )
        decision = evaluate_control(result, feature_enabled=control_dry_run, authenticated=True,
                                    app_foreground=False, physical_ready=False,
                                    mode=ControlMode.MANUAL, allow_simulation=simulate_base_output)
        state = gate.check()
        if simulate_base_output:
            result['simulated_base_output'] = base_output(state)
        result['control_gate'] = {'state':state.value, 'ready':decision.ready,
                                  'max_age_ms':DEFAULT_MAX_AGE_MS,
                                  'max_age_by_source_ms':MAX_AGE_BY_SOURCE_MS,
                                  'reasons':list(decision.reasons)}
        result['control_dry_run'] = control_dry_run
        result['base_zero_test'] = base_zero_test
        result['base_pulse_test'] = base_pulse_test
        result['isolated_pulse_test'] = isolated_pulse_test
        if isolated_floor_guard is not None:
            reason = floor_reason()
            result['floor_simulation'] = {'allowed_at_rest':reason is None, 'reason':reason}
        return result

    @app.get('/health')
    async def health():
        return {'service':'arturito-bridge', 'schema_version':1, 'source':source,
                'commands_enabled':base_pulse_test or physical_manual, 'control_dry_run':control_dry_run,
                'control_gate':gate.check().value, 'base_zero_test':base_zero_test, 'base_pulse_test':base_pulse_test}

    def owner(request: Request):
        if bench_test and (request.client is None or request.client.host != '127.0.0.1'):
            raise HTTPException(403, 'La prueba de banco acepta control solamente desde loopback')
        value = request.headers.get('x-arturito-client', '').strip()
        if not value or len(value) > 100:
            raise HTTPException(400, 'Falta identificador de la sesión de control')
        return value

    def gate_response(decision=None, *, sent=False):
        state = gate.check()
        result = {'state':state.value, 'owner':gate.owner,
                'ready':bool(decision and decision.ready),
                'reasons':list(decision.reasons) if decision else [],
                'dry_run':not bench_test, 'commands_enabled':base_pulse_test,
                'robot_command_sent':bench_test and sent}
        if simulate_base_output:
            result['simulated_base_output'] = base_output(state)
        return result

    def recheck_session(request):
        current_owner = owner(request)
        state = gate.check()
        if gate.owner != current_owner or state not in (GateState.READY, GateState.ENABLED, GateState.ACTIVE):
            raise HTTPException(409, 'La sesión no está vigente o pertenece a otro operador')
        decision = evaluate_control(snapshot(), feature_enabled=control_dry_run or bench_test, authenticated=True,
                                    app_foreground=True, physical_ready=True, mode=ControlMode.MANUAL,
                                    allow_simulation=simulate_base_output, base_only=bench_test,
                                    allow_standby=state == GateState.READY)
        decision = with_floor_check(decision)
        if not decision.ready or not compatible_base():
            gate.revoke(latched=True)
            stop_trial()
            base_output(GateState.LATCHED_STOP)
            raise HTTPException(409, detail={'message':'Se perdieron condiciones del ensayo',
                                            'reasons':list(decision.reasons)})
        return current_owner

    @app.post('/api/v1/control/prepare')
    async def prepare_control(body: PrepareRequest, request: Request):
        authorize(request.headers)
        if not (control_dry_run or bench_test):
            raise HTTPException(409, 'El ensayo de control está deshabilitado')
        if bench_test and not body.arm_physically_isolated:
            raise HTTPException(409, 'Se requiere confirmar el aislamiento físico del brazo')
        if base_pulse_test and not body.wheels_off_ground:
            raise HTTPException(409, 'Se requiere confirmar el soporte y las ruedas elevadas')
        if body.mode != ControlMode.MANUAL:
            raise HTTPException(409, 'El ensayo solo admite modo manual')
        current_owner = owner(request)
        if base_trial is not None and base_trial.state in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO):
            raise HTTPException(409, 'Confirmación de armado en curso')
        decision = evaluate_control(snapshot(), feature_enabled=True, authenticated=True,
                                    app_foreground=body.app_foreground,
                                    physical_ready=body.physical_ready, mode=body.mode,
                                    allow_simulation=simulate_base_output, base_only=bench_test,
                                    allow_standby=base_link is not None)
        decision = with_floor_check(decision)
        if not compatible_base():
            raise HTTPException(409, 'Hay otro publicador o no se detecta la base')
        if not gate.prepare(current_owner, decision) and gate.owner is not None:
            raise HTTPException(409, 'La sesión pertenece a otro operador')
        stop_trial()
        return gate_response(decision)

    @app.post('/api/v1/control/confirm')
    async def confirm_control(request: Request):
        nonlocal base_trial
        authorize(request.headers)
        current_owner = recheck_session(request)
        if gate.state != GateState.READY:
            raise HTTPException(409, 'La sesión no está lista o pertenece a otro operador')
        if base_link is not None:
            if base_trial is not None and base_trial.state in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO):
                raise HTTPException(409, 'Confirmación de armado en curso')
            trial = base_link.new_session()
            base_trial = trial
            feedback = trial_feedback(True)
            received_at = feedback['received_at']
            fresh = received_at is not None and 0 <= base_trial.clock() - received_at <= MAX_AGE_BY_SOURCE_MS['base'] / 1000
            if not trial.begin(safe=feedback['safe'] and fresh, base_state=feedback['base_state']):
                gate.revoke(latched=True)
                raise HTTPException(409, 'La base de prueba no está desarmada y parada')
            try:
                while trial.state in (BaseSessionState.ARMING, BaseSessionState.VERIFYING_ZERO):
                    await asyncio.sleep(0.01)
                    trial.update(**trial_feedback(base_trial is trial and gate.owner == current_owner
                                                  and gate.state == GateState.READY))
                if base_trial is not trial or trial.state != BaseSessionState.ARMED:
                    raise HTTPException(409, 'La base de prueba no confirmó el armado')
            except BaseException:
                if base_trial is trial:
                    stop_trial()
                    gate.revoke(latched=True)
                raise
        if not gate.enable(current_owner):
            stop_trial()
            raise HTTPException(409, 'La sesión no está lista o pertenece a otro operador')
        return gate_response(sent=base_link is not None)

    @app.post('/api/v1/control/heartbeat')
    async def heartbeat(body: HeartbeatRequest, request: Request):
        authorize(request.headers)
        if not gate.heartbeat(recheck_session(request), body.deadman):
            raise HTTPException(409, 'La sesión no está habilitada')
        if base_zero_test and not body.deadman:
            gate.revoke(latched=True)
            return gate_response(sent=stop_trial())
        if base_trial is not None and not body.deadman and base_trial.velocity_deadline is not None:
            stop_trial()
            gate.revoke(latched=True)
        return gate_response()

    def accept_dry_manual(request, deadman):
        current_owner = recheck_session(request)
        if not gate.heartbeat(current_owner, deadman=deadman) or not deadman:
            if not deadman and base_trial is not None and base_trial.velocity_deadline is not None:
                stop_trial()
                gate.revoke(latched=True)
            base_output(gate.state)
            raise HTTPException(409, 'Hombre muerto o sesión habilitada requeridos')

    @app.post('/api/v1/control/manual/base')
    async def manual_base(body: BaseManualRequest, request: Request):
        nonlocal simulated_base_command
        authorize(request.headers)
        if base_zero_test:
            raise HTTPException(409, 'La prueba de cero no admite órdenes de movimiento')
        if isolated_pulse_test or base_pulse_test:
            raise HTTPException(409, 'El ensayo solo admite un pulso delimitado')
        accept_dry_manual(request, body.deadman)
        if base_link is not None:
            if base_trial is None or not base_trial.velocity(body.linear_m_s, body.angular_rad_s,
                    deadman=body.deadman, **trial_feedback(True)):
                stop_trial()
                gate.revoke(latched=True)
                raise HTTPException(409, 'La base de prueba no acepta movimiento')
        if simulate_base_output:
            simulated_base_command = (body.linear_m_s, body.angular_rad_s, gate.deadline)
        return gate_response()

    if isolated_pulse_test or base_pulse_test:
        @app.post('/api/v1/control/bench/pulse')
        async def bench_pulse(body: BenchPulseRequest, request: Request):
            nonlocal simulated_base_command
            authorize(request.headers)
            current_owner = recheck_session(request)
            if gate.state != GateState.ENABLED or base_trial is None or base_trial.velocity_deadline is not None:
                raise HTTPException(409, 'Se requiere una sesión nueva y armada')
            duration = body.duration_ms / 1000
            reason = floor_reason(body.linear_m_s, duration)
            if reason:
                gate.revoke(latched=True)
                stop_trial()
                raise HTTPException(409, detail={'reason':reason})
            if not body.deadman or not gate.heartbeat(current_owner, deadman=True):
                gate.revoke(latched=True)
                stop_trial()
                raise HTTPException(409, 'Se requiere mantener el mando presionado')
            if not base_trial.velocity(body.linear_m_s, 0.0, deadman=True,
                                      valid_for=duration, **trial_feedback(True)):
                gate.revoke(latched=True)
                stop_trial()
                raise HTTPException(409, 'La base de prueba rechazó el pulso')
            if simulate_base_output:
                simulated_base_command = (body.linear_m_s, 0.0, base_trial.velocity_deadline)
            return gate_response(sent=True)

    @app.post('/api/v1/control/manual/arm')
    async def manual_arm(body: ArmManualRequest, request: Request):
        authorize(request.headers)
        if base_link is not None or bench_test:
            raise HTTPException(409, 'El ensayo integrado solo incluye la base')
        accept_dry_manual(request, body.deadman)
        return gate_response()

    @app.post('/api/v1/control/stop')
    async def stop_control(request: Request):
        authorize(request.headers)
        if bench_test:
            owner(request)
        gate.revoke(latched=True)
        return gate_response(sent=stop_trial())

    @app.delete('/api/v1/control/session')
    async def release_control(request: Request):
        authorize(request.headers)
        requested = owner(request)
        if gate.owner not in (None, requested):
            raise HTTPException(409, 'La sesión pertenece a otro operador')
        gate.revoke(latched=False)
        return gate_response(sent=stop_trial())

    @app.get('/api/v1/telemetry')
    async def telemetry(request: Request):
        authorize(request.headers)
        return snapshot()

    @app.get('/api/v1/vision/{camera}/frame')
    async def camera_frame(camera: str, request: Request):
        if not token:
            raise HTTPException(403, 'La cámara requiere autenticación')
        authorize(request.headers)
        if camera not in CAMERAS:
            raise HTTPException(404, 'Cámara desconocida')
        frame = camera_frames.latest(camera) if source == 'ros2' and not bench_test else None
        headers = {'Cache-Control': 'no-store'}
        if frame is None:
            return Response(status_code=204, headers=headers)
        return Response(frame, media_type='image/jpeg', headers=headers)

    @app.websocket('/api/v1/telemetry')
    async def stream(ws: WebSocket):
        try:
            authorize(ws.headers)
        except HTTPException:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            while True:
                await ws.send_json(snapshot())
                await asyncio.sleep(1)
        except (WebSocketDisconnect, OSError):
            pass

    fence_path = data_dir / 'operation-boundary.geojson'

    @app.get('/api/v1/geofence')
    async def get_fence(request: Request):
        authorize(request.headers)
        if not fence_path.exists():
            return {'geofence':None, 'applied_to_robot':False}
        try:
            fence, area = validate(json.loads(fence_path.read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError):
            raise HTTPException(500, 'No se pudo recuperar la geocerca guardada')
        return {'geofence':fence, 'area_m2':area, 'applied_to_robot':False}

    @app.put('/api/v1/geofence')
    async def put_fence(request: Request):
        authorize(request.headers)
        # Limitar también peticiones sin Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 64000:
                raise HTTPException(413, 'GeoJSON demasiado grande')
        try:
            fence, area = validate(json.loads(body))
        except (ValueError, TypeError, KeyError, IndexError):
            raise HTTPException(422, 'Geocerca inválida: revisar nombre, anillo y cruces')
        data_dir.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=data_dir, delete=False) as out:
                temporary = Path(out.name)
                json.dump(fence, out, ensure_ascii=False, allow_nan=False)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, fence_path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return {'accepted':True, 'geofence':fence, 'area_m2':area, 'applied_to_robot':False}

    return app


app = create_app()
