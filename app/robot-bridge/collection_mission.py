"""Una recolección de la demo original, con los transportes del puente ROS."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import signal
import sys
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException

from physical_control import OpenManual
from vision_3d import BASE_CENTER, with_displacement


class CollectionMission:
    def __init__(self, control, stereo, data_dir, tools):
        self.control, self.stereo = control, stereo
        self.data_dir, self.tools = Path(data_dir), Path(tools)
        self.task = self.owner = self.operator = None
        self.zone = None
        self.deadline = 0.
        self.run_until = 0.
        self.stop_requested = False
        self.events = []
        self.status = {'state': 'INACTIVO', 'message': 'Prepará el cero del Móvil y el reposo del brazo.'}

    @property
    def active(self):
        return self.task is not None and not self.task.done()

    def update(self, state, message):
        event = {'state': state, 'message': message, 'timestamp': datetime.now(timezone.utc).isoformat()}
        self.status = event
        self.events.append(event)

    def snapshot(self):
        return dict(self.status, active=self.active, events=self.events[-8:])

    def start(self, operator, origin):
        self.control.tick()
        if self.active or self.control.owner is not None:
            raise HTTPException(409, 'Detené el mando antes de iniciar la recolección')
        if not origin:
            raise HTTPException(409, 'Calculá primero el cero del Móvil con el ArUco')
        if origin['marker_id'] not in (0, 1, 2, 3):
            raise HTTPException(409, 'Para la demo usá una de las marcas del arbolito, ID 0 a 3')
        start = self.control.snapshot()
        arm = start.get('arm_state')
        if not self.control.arm_ready(arm) or max(abs(a - b) for a, b in zip(arm_angles(arm), (3, 17, 4))) > 3:
            raise HTTPException(409, 'Hacé el homing y dejá el brazo en reposo')
        odom = source_value(start, 'odom')
        if not odom:
            raise HTTPException(409, 'Falta odometría reciente')
        delta = with_displacement(origin, odom)['displacement']
        resume = math.hypot(delta['x_m'], delta['y_m']) > .035 or abs(delta['yaw_deg']) > 4
        if self.stereo.snapshot()['status'] == 'waiting':
            raise HTTPException(409, 'Esperá a que la visión estéreo reciba profundidad')
        self.owner, self.operator = f'mision-{uuid4()}', operator
        self.deadline = monotonic() + 1.25
        self.run_until = monotonic() + 180.
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('BUSCANDO', 'Validando la parada del arbolito con la calibración original.')
        self.task = asyncio.create_task(self.run(self.owner, origin, resume))
        return self.snapshot()

    def heartbeat(self, operator):
        if self.active and self.operator == operator:
            self.deadline = monotonic() + 1.25
        return self.snapshot()

    async def stop(self, operator=None):
        if self.active and (operator is None or self.operator == operator):
            if not self.stop_requested and self.status['state'] not in ('FINALIZADO', 'RECUPERACION', 'INACTIVO'):
                self.stop_requested = True
                self.task.cancel()
            try:
                await asyncio.shield(self.task)
            except asyncio.CancelledError:
                self.update('INACTIVO', 'Recolección detenida antes de comenzar.')
        return self.snapshot()

    def cycle(self, owner, linear=0., angular=0.):
        if monotonic() >= self.run_until:
            raise RuntimeError('La recolección superó el tiempo permitido')
        if monotonic() >= self.deadline:
            raise RuntimeError('Se perdió la supervisión de Arturito')
        self.control.mission_velocity(owner, linear, angular)
        if self.zone is not None:
            origin, trunk = self.zone
            if not stopped_in_zone(origin, trunk, source_value(self.control.snapshot(), 'odom')):
                raise RuntimeError('El Móvil salió de la zona de agarre o dejó de estar detenido')

    async def settle(self, owner, seconds):
        until = monotonic() + seconds
        while monotonic() < until:
            self.cycle(owner)
            await asyncio.sleep(.05)

    async def drive_step(self, owner, kind, value):
        initial = self.control.snapshot()
        first = source_value(initial, 'odom' if kind == 'recto' else 'imu')
        if not first:
            raise RuntimeError('Falta realimentación para el movimiento')
        limit = monotonic() + 24.
        while monotonic() < limit:
            sample = source_value(self.control.snapshot(), 'odom' if kind == 'recto' else 'imu')
            if not sample:
                raise RuntimeError('Se perdió la realimentación del Móvil')
            if kind == 'recto':
                measured = math.hypot(sample['x_m'] - first['x_m'], sample['y_m'] - first['y_m'])
                remaining = value / 1000 - measured
                if remaining <= 0:
                    break
                self.cycle(owner, min(.10, max(.03, remaining)))
            else:
                measured = sample['gyro_yaw_rad'] - first['gyro_yaw_rad']
                remaining = math.radians(abs(value)) - math.copysign(1., value) * measured
                if remaining <= 0:
                    break
                self.cycle(owner, angular=math.copysign(min(.5, max(.12, 1.5 * remaining)), value))
            await asyncio.sleep(.05)
        else:
            raise RuntimeError('El Móvil no llegó a la parada en el tiempo permitido')
        await self.settle(owner, 1.)

    async def measure_lemon(self, owner):
        points, previous = [], monotonic()
        until = previous + 5.
        while monotonic() < until:
            self.cycle(owner)
            stamp, point = self.stereo.target_sample()
            if stamp is not None and stamp > previous:
                if point:
                    points.append(tuple(point[axis] * 1000 for axis in ('x_m', 'y_m', 'z_m')))
                previous = stamp
            await asyncio.sleep(.05)
        return points

    async def arm_instruction(self, owner, command, expected, timeout):
        self.cycle(owner)
        started = monotonic()
        self.control.arm.send(command)
        while monotonic() - started < timeout:
            self.cycle(owner)
            received, answer = self.control.arm.home_feedback()
            if received is not None and received >= started:
                if answer == 'park_failed':
                    raise RuntimeError(self.control.arm.home_detail or 'El brazo rechazó un movimiento')
                if answer == expected:
                    return
            await asyncio.sleep(.05)
        raise RuntimeError('El brazo no confirmó el movimiento')

    async def run(self, owner, origin, resume):
        stage = 'validación del recorrido'
        recorder = None
        try:
            planners = asyncio.create_task(asyncio.to_thread(self.load_planners))
            while not planners.done():
                if monotonic() >= self.deadline:
                    raise RuntimeError('Se perdió la supervisión de Arturito')
                await asyncio.sleep(.05)
            navigation, grasp = planners.result()
            mark = origin['marker_in_arm']
            pos = [mark[axis] * 1000 for axis in ('x_m', 'y_m', 'z_m')]
            trunk = navigation.tronco_desde(pos, mark['normal_deg'], 165.)
            if resume:
                if not stopped_in_zone(origin, trunk, source_value(self.control.snapshot(), 'odom')):
                    raise RuntimeError('El Móvil se movió fuera de la parada. Volvé a medir el ArUco.')
                steps = []
            else:
                steps = navigation.planear(trunk, mark['normal_deg'], (-700., 150.))
            if any(kind == 'recto' and not 0 < value <= navigation.MAX_RECTO for kind, value in steps):
                raise RuntimeError('Reubicá el Móvil: el recorrido calculado es largo o requiere retroceder')
            if monotonic() >= self.deadline:
                raise RuntimeError('Se perdió la supervisión de Arturito')
            recorder = await self.start_recording()
            await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            stage = 'aproximación'
            self.update('NAVEGANDO', navigation.texto(steps))
            for kind, value in steps:
                await self.drive_step(owner, kind, value)
            await self.settle(owner, 1.)
            self.zone = (origin, trunk)
            self.cycle(owner)
            stage = 'localización del limón'
            self.update('BUSCANDO', 'Midiendo la posición estable del limón con estéreo.')
            samples = await self.measure_lemon(owner)
            angles = arm_angles(self.control.snapshot().get('arm_state'))
            planning = asyncio.create_task(asyncio.to_thread(grasp_plan, grasp, samples, angles))
            while not planning.done():
                self.cycle(owner)
                await asyncio.sleep(.05)
            plan = planning.result()
            for stage, step in plan:
                self.update('INTERVINIENDO', stage if stage != 'servo' else 'Ajustando la pinza')
                if stage == 'servo':
                    await self.arm_instruction(owner, step, 'servo_ready', 8.)
                    await self.settle(owner, .4)
                else:
                    for q in step:
                        command = 'mv ' + ' '.join(f'{joint:.2f}' for joint in q)
                        await self.arm_instruction(owner, command, 'parked', 30.)
            self.update('FINALIZADO', 'Recolección terminada. El limón quedó en la pinza.')
        except asyncio.CancelledError:
            self.update('INACTIVO', 'Recolección detenida por el operador.')
        except (RuntimeError, HTTPException, ValueError, OSError, ImportError) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            self.update('RECUPERACION', f'La recolección se detuvo durante {stage}. {detail}')
        except Exception:
            logging.exception('Falló la recolección')
            self.update('RECUPERACION', 'Falló la recolección. Consultá el registro de la Raspberry Pi.')
        finally:
            self.zone = None
            try:
                if self.control.owner == owner:
                    self.control.stop()
            finally:
                if recorder is not None:
                    await self.stop_recording(recorder)
                self.save_log()

    def load_planners(self):
        for path in (self.tools, self.tools.parent.parent / '20-brazo-coordinado/tools'):
            if not path.is_dir():
                raise RuntimeError('Faltan las herramientas originales y su calibración en la Raspberry Pi')
            if str(path) not in sys.path:
                sys.path.append(str(path))
        import ir_a_parada
        import punta
        return ir_a_parada, punta

    def save_log(self):
        try:
            path = self.data_dir / 'missions'
            path.mkdir(parents=True, exist_ok=True)
            (path / f'{self.owner}.json').write_text(json.dumps(self.events, ensure_ascii=False), encoding='utf-8')
        except OSError:
            logging.exception('No se guardó el registro de recolección')

    async def start_recording(self):
        directory = self.data_dir / 'missions'
        directory.mkdir(parents=True, exist_ok=True)
        topics = ('/odom', '/imu/data_raw', '/cmd_vel', '/base/estado', '/brazo/estado',
                  '/brazo/respuesta', '/battery', '/bumpers', '/range/frente',
                  '/yolo/detecciones', '/limon/posicion', '/limon/todos')
        return await asyncio.create_subprocess_exec(
            'ros2', 'bag', 'record', '-s', 'sqlite3', '-o', str(directory / self.owner),
            '--disable-keyboard-controls', '--node-name', 'arturito_registro_mision', '--topics', *topics,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)

    async def stop_recording(self, recorder):
        if recorder.returncode is None:
            try:
                recorder.send_signal(signal.SIGINT)
                await asyncio.wait_for(recorder.wait(), 4.)
            except ProcessLookupError:
                pass
            except asyncio.TimeoutError:
                recorder.terminate()
                await recorder.wait()


def source_value(snapshot, key):
    return next((item['value'] for item in snapshot['sources'] if item['key'] == key
                 and item['status'] == 'fresh' and item['age_ms'] <= 500), None)


def arm_angles(state):
    try:
        angles = tuple(float(x) for x in state.split('q=', 1)[1].split(';')[0].split(','))
    except (AttributeError, IndexError, ValueError) as error:
        raise HTTPException(409, 'Los ángulos del brazo no están disponibles') from error
    if len(angles) != 3 or not all(map(math.isfinite, angles)):
        raise HTTPException(409, 'Los ángulos del brazo no son válidos')
    return angles


def stopped_in_zone(origin, trunk_mm, odom):
    if (odom is None or abs(odom['linear_m_s']) > .005 or abs(odom['angular_rad_s']) > .02):
        return False
    relative = with_displacement(origin, odom)['displacement']
    yaw = math.radians(relative['yaw_deg'])
    cx, cy = BASE_CENTER
    x = trunk_mm[0] / 1000 - cx + relative['y_m']
    y = trunk_mm[1] / 1000 - cy - relative['x_m']
    # La navegación original expresa x a la derecha y y hacia adelante.
    tree_x = math.cos(yaw) * x + math.sin(yaw) * y + cx
    tree_y = -math.sin(yaw) * x + math.cos(yaw) * y + cy
    return math.hypot(tree_x + .70, tree_y - .15) <= .13


def grasp_plan(original, samples, angles):
    import numpy as np
    if len(samples) < original.MIN_POSICIONES:
        raise RuntimeError('No hay suficientes posiciones 3D del limón')
    points = np.asarray(samples, dtype=float)
    face = np.median(points, axis=0)
    if np.median(np.linalg.norm(points - face, axis=1)) > original.DISPERSION_MAX:
        raise RuntimeError('La posición del limón es inestable')
    rotation, translation = original.cargar_tf_agarre()
    x, y, z = original.ajc.camara_a_cinematica(rotation, translation, face, original.RADIO_LIMON)
    plan, details = original.planear_agarre(angles, (round(x), round(y), round(z + original.AGARRAR_DZ)))
    if plan is None:
        raise RuntimeError('; '.join(details))
    return plan
