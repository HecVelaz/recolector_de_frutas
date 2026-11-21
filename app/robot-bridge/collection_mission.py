"""Recolección con los transportes del puente ROS (21/11: cero relativo al limón más cercano).

El cero del Móvil es su pose cuando el operador pide «Calcular cero»: se mide el limón más cercano con el estéreo y se
guarda junto con la odometría de ese instante. «Iniciar recolección» acerca el Móvil hasta dejar ese limón en
LEMON_STOP_MM respecto de J1 (sin cambiar el rumbo ni retroceder), cosecha como punta.cosechar y vuelve al cero
desandando el mismo camino.
"""

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
from vision_3d import with_displacement

MAX_LEMONS = 5
MEASURE_SECONDS = 8.     # 21/11: 5 -> 8 s (con el v4 y la disparidad a ~1-2 Hz llegan menos posiciones)
MV_TIMEOUT = 90.         # TIMEOUT_MV de recolectar.py
MV_RETRIES = 2           # punta.ejecutar: cortes por atraso con carga
RETRY_ON = ('no quedan firmes', 'no sigue la trayectoria', 'se mueve al revés')
# 21/11: plegando para la canasta J3 quedó en 78,4 (pedido 80; cerca del punto muerto del cuatro barras está dura) y el
# mv siguiente cortó por "sin cuentas" porque J3 no subía esos 1,6°. Si una articulación ya está a menos de esto de su
# destino, se reintenta una vez dejándola donde está (con el encoder suelto de verdad la diferencia sería mayor)
STUCK_NEAR_DEG = 2.
ORIGIN_SECONDS = 3.      # medición del limón para el cero
# Dónde queda el limón respecto de J1 al llegar (mm; x a la derecha, y adelante). Con punta.planear_agarre_tol desde el
# reposo hay agarre a la canasta con el limón 6 cm más arriba o más abajo, y queda a ~89 cm de la cámara (21/11)
LEMON_STOP_MM = (-550., 150.)
ZONE_M, ZONE_DEG = .04, 5.
# Al llegar a la parada se sabe dónde tiene que estar el limón del cero: solo vale uno a menos de esto de ahí. El
# estéreo a veces mide el follaje delante del limón (21/11: el mismo limón a 42 y a 77 cm, alternando); ese punto
# fantasma queda descartado y el brazo no va a buscarlo al aire
EXPECTED_RADIUS_MM = 120.   # mientras actúa el brazo, el Móvil quieto a menos de esto de donde llegó
REVERSE_M_S = .06            # solo al volver al cero desandando el camino (atrás no hay sensores)


class ArmRejected(RuntimeError):
    """El firmware del brazo cortó o rechazó un movimiento (texto de /brazo/respuesta)."""


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
        self._planners = None

    @property
    def active(self):
        return self.task is not None and not self.task.done()

    def update(self, state, message):
        event = {'state': state, 'message': message, 'timestamp': datetime.now(timezone.utc).isoformat()}
        self.status = event
        self.events.append(event)

    def snapshot(self):
        return dict(self.status, active=self.active, events=self.events[-8:])

    def start(self, operator, origin, lemons=1, to_basket=True):
        if not 1 <= lemons <= MAX_LEMONS or (lemons > 1 and not to_basket):
            raise HTTPException(422, f'Pedí de 1 a {MAX_LEMONS} limones; más de uno solo yendo a la canasta')
        self.control.tick()
        if self.active or self.control.owner is not None:
            raise HTTPException(409, 'Detené el mando antes de iniciar la recolección')
        if not origin or origin.get('kind') != 'lemon':
            raise HTTPException(409, 'Calculá primero el cero del Móvil con el limón a la vista')
        start = self.control.snapshot()
        arm = start.get('arm_state')
        if not self.control.arm_ready(arm) or max(abs(a - b) for a, b in zip(arm_angles(arm), (3, 17, 4))) > 3:
            raise HTTPException(409, 'Hacé el homing y dejá el brazo en reposo')
        odom = source_value(start, 'odom')
        if not odom:
            raise HTTPException(409, 'Falta odometría reciente')
        delta = with_displacement(origin, odom)['displacement']
        if math.hypot(delta['x_m'], delta['y_m']) > .035 or abs(delta['yaw_deg']) > 4:
            raise HTTPException(409, 'El Móvil se movió desde el cero: volvé a calcularlo con el limón a la vista')
        if self.stereo.snapshot()['status'] == 'waiting':
            raise HTTPException(409, 'Esperá a que la visión estéreo reciba profundidad')
        self.owner, self.operator = f'mision-{uuid4()}', operator
        self.deadline = monotonic() + 1.25
        # Navegación y un agarre ~3 min; cada limón más, ida y vuelta a la canasta con su medición (~2 min)
        self.run_until = monotonic() + 180. + 120. * (lemons - 1)
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('BUSCANDO', 'Planeando el acercamiento al limón más cercano.')
        self.task = asyncio.create_task(self.run(self.owner, origin, lemons, to_basket))
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
        try:
            self.control.mission_velocity(owner, linear, angular)
        except HTTPException as error:
            raise RuntimeError(base_refusal(self.control.snapshot(), linear) or error.detail) from error
        if self.zone is not None and not stopped_near(self.zone, source_value(self.control.snapshot(), 'odom')):
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
            if kind == 'recto':   # value < 0: atrás (solo al desandar el camino), más despacio
                measured = math.hypot(sample['x_m'] - first['x_m'], sample['y_m'] - first['y_m'])
                remaining = abs(value) / 1000 - measured
                if remaining <= 0:
                    break
                top = .10 if value > 0 else REVERSE_M_S
                self.cycle(owner, math.copysign(min(top, max(.03, remaining)), value))
            else:
                measured = sample['gyro_yaw_rad'] - first['gyro_yaw_rad']
                remaining = math.radians(abs(value)) - math.copysign(1., value) * measured
                if remaining <= 0:
                    break
                self.cycle(owner, angular=math.copysign(min(.5, max(.12, 1.5 * remaining)), value))
            await asyncio.sleep(.05)
        else:
            raise RuntimeError('El Móvil no completó el movimiento en el tiempo permitido')
        await self.settle(owner, 1.)

    async def in_thread(self, owner, function, *args):
        """Cálculo largo (planificadores de punta.py) sin dejar de mandar el cero a la base (watchdog de 300 ms)."""
        work = asyncio.create_task(asyncio.to_thread(function, *args))
        while not work.done():
            self.cycle(owner)
            await asyncio.sleep(.05)
        return work.result()

    async def measure_frames(self, owner, seconds=MEASURE_SECONDS):
        """Las imágenes de /limon/todos de `seconds` s: [[(x, y, z) mm, ...], ...], marco `camera`."""
        return await self.collect_frames(seconds, lambda: self.cycle(owner))

    async def collect_frames(self, seconds, tick):
        frames, previous = [], monotonic()
        until = previous + seconds
        while monotonic() < until:
            tick()
            stamp, frame_id, points = self.stereo.target_frame()
            if stamp is not None and stamp > previous:
                if points and frame_id != 'camera':
                    raise RuntimeError(f'/limon/todos viene en {frame_id}; la calibración es para camera')
                frames.append([tuple(p[axis] * 1000 for axis in ('x_m', 'y_m', 'z_m')) for p in points])
                previous = stamp
            await asyncio.sleep(.05)
        return frames

    def planners(self):
        """(ir_a_parada, punta, tf cámara -> brazo), cargados una sola vez."""
        if self._planners is None:
            navigation, grasp = self.load_planners()
            self._planners = navigation, grasp, grasp.cargar_tf_agarre()
        return self._planners

    async def measure_origin(self, still):
        """Para «Calcular cero»: el limón más cercano a J1 (mm, marco del brazo, con las correcciones de punta) y
        cuántos limones estables se ven. still() False en cualquier momento corta (el Móvil tiene que estar quieto)."""
        _, grasp, tf = await asyncio.to_thread(self.planners)

        def tick():
            if not still():
                raise ValueError('Mantené quieto el Móvil y soltá los mandos para fijar el cero.')

        groups = group_lemons(await self.collect_frames(ORIGIN_SECONDS, tick), grasp.AGRUPAR_MM, grasp.MIN_POSICIONES)
        lemons = [grasp.limon_de_cara(tf, face, n, spread) for face, n, spread in groups
                  if spread <= grasp.DISPERSION_MAX]
        if not lemons:
            raise ValueError('No veo un limón estable: dejá el limonero a la vista de la cámara izquierda (40-95 cm).')
        return min(lemons, key=lambda lemon: math.hypot(lemon[0], lemon[1])), len(lemons)

    async def measure_lemons(self, owner, original, tf, near=None):
        """Como punta.medir_limones: agrupa los limones de todas las imágenes y da sus puntos de agarre (mm, marco del
        brazo) con las correcciones de punta.limon_de_cara (z de la visión, adelante, izquierda, arriba y ajuste fino).
        near: dónde tiene que estar el limón (mm, marco del brazo). Entonces solo vale el que está a menos de
        EXPECTED_RADIUS_MM de ahí, y alcanza con punta.MIN_POSICIONES posiciones aunque haya lecturas repartidas."""
        groups = group_lemons(await self.measure_frames(owner), original.AGRUPAR_MM, original.MIN_POSICIONES,
                              min_fraction=0. if near is not None else .3)
        lemons = [original.limon_de_cara(tf, face, n, spread) for face, n, spread in groups
                  if spread <= original.DISPERSION_MAX]
        if near is not None:
            lemons = [lemon for lemon in lemons if math.dist(lemon, near) <= EXPECTED_RADIUS_MM]
        return lemons

    async def arm_instruction(self, owner, command, expected, timeout):
        self.cycle(owner)
        started = monotonic()
        self.control.arm.send(command)
        while monotonic() - started < timeout:
            self.cycle(owner)
            received, answer = self.control.arm.home_feedback()
            if received is not None and received >= started:
                if answer == 'park_failed':
                    raise ArmRejected(self.control.arm.home_detail or 'El brazo rechazó un movimiento')
                if answer == expected:
                    return
            await asyncio.sleep(.05)
        raise ArmRejected(f'El brazo no confirmó «{command}» en {timeout:.0f} s')

    async def move(self, owner, q, passing=False):
        """Como punta.ejecutar con un punto: mv (o mvp de paso) y, si corta por atraso con carga, repetir desde donde
        quedó hasta MV_RETRIES veces. Los cortes de seguridad (franja, caja, plegado) no se repiten."""
        nudged = False
        for attempt in range(MV_RETRIES + 1):
            command = f"{'mvp' if passing else 'mv'} {q[0]:.2f} {q[1]:.2f} {q[2]:.2f}"
            try:
                await self.arm_instruction(owner, command, 'parked', MV_TIMEOUT)
                return
            except ArmRejected as error:
                if 'sin cuentas' in str(error) and not nudged:
                    now = arm_angles(self.control.snapshot().get('arm_state'))
                    # La trabada es la que tenía que moverse un poco (0,3-2°): las que ya llegaron no cuentan y si
                    # la que no llega está lejos, el corte es de verdad
                    short = [.3 < abs(a - b) < STUCK_NEAR_DEG for a, b in zip(now, q)]
                    if any(short):
                        q = tuple(a if stuck else b for a, b, stuck in zip(now, q, short))
                        nudged = True
                        await self.settle(owner, .5)
                        continue
                if attempt == MV_RETRIES or not any(text in str(error) for text in RETRY_ON):
                    raise
            await self.settle(owner, .5)

    async def run_task(self, owner, original, steps):
        """Como punta.correr_tarea: comandos sueltos, servos esperando SERVO_LLEGO y tramos de mv; los tramos de
        punta.DE_PASO van con mvp y los de punta.CON_CARGA a la velocidad de carga."""
        for name, part in steps:
            self.cycle(owner)
            if name == 'cmd':
                self.control.arm.send(part)
                await self.settle(owner, .2)
                continue
            if name == 'servo':
                self.update('INTERVINIENDO', 'Ajustando la pinza' if part.startswith('pz') else 'Girando la muñeca')
                await self.arm_instruction(owner, part, 'servo_ready', 8.)
                await self.settle(owner, .4)
                continue
            self.update('INTERVINIENDO', name[:1].upper() + name[1:])
            loaded = name in original.CON_CARGA
            if loaded:
                self.control.arm.send(original.VEL_CARGA)
                await self.settle(owner, .2)
            try:
                passing, last_passing = original.DE_PASO.get(name, (False, False))
                for index, q in enumerate(part):
                    await self.move(owner, q, passing and (index < len(part) - 1 or last_passing))
            finally:
                if loaded:
                    self.control.arm.send(original.VEL_NORMAL)

    async def recover_to_basket(self, owner, original):
        """Como punta.recuperar_a_canasta: lo que tenga la pinza a la canasta, si el camino entra en el modelo."""
        s = arm_angles(self.control.snapshot().get('arm_state'))
        path = await self.in_thread(owner, basket_path, original, s)   # el modelo tarda: sin trabar el lazo de la base
        if path is None:
            return False
        self.update('RECUPERACION', 'Llevando lo que tiene la pinza a la canasta.')
        for index, q in enumerate(path):
            await self.move(owner, q, passing=True)
        await self.arm_instruction(owner, 'pz a', 'servo_ready', 8.)
        await self.arm_instruction(owner, 'mn 0', 'servo_ready', 8.)
        return True

    async def harvest(self, owner, original, tf, count, to_basket, expected=None):
        """Como punta.cosechar: mide todos los limones, agarra el más cercano con plan, lo deja en la canasta y vuelve a
        medir desde ahí (confirma que ya no está en el árbol; hasta punta.MAX_INTENTOS por limón). Al final, al reposo.
        Sin canasta: uno solo y queda en la pinza. expected: dónde tiene que estar el primer limón (al llegar a la
        parada); la primera medición solo acepta ese. Devuelve cuántos dejó."""
        done, pending, attempts, discarded = 0, None, 0, []
        near = expected
        while True:
            self.update('BUSCANDO', f'Midiendo los limones con estéreo ({done} de {count} en la canasta).')
            lemons = await self.measure_lemons(owner, original, tf, near)
            if near is not None and not lemons:
                raise RuntimeError('No encuentro el limón donde debería estar al llegar (a menos de '
                                   f'{EXPECTED_RADIUS_MM / 10:.0f} cm de la posición esperada). Revisá que se vea '
                                   'completo y que no lo tapen hojas; volvé a calcular el cero.')
            near = None
            if pending is not None:
                still = [lemon for lemon in lemons if math.dist(lemon, pending) < original.VERIFICAR_MM]
                if still:
                    attempts += 1
                    if attempts >= original.MAX_INTENTOS:
                        discarded.append(still[0])
                        attempts = 0
                else:
                    done += 1
                    attempts = 0
                pending = None
            if done >= count:
                break
            candidates = sorted((lemon for lemon in lemons
                                 if not any(math.dist(lemon, d) < original.VERIFICAR_MM for d in discarded)),
                                key=lambda lemon: math.hypot(lemon[0], lemon[1]))
            if not candidates:
                if done == 0 and not lemons:
                    raise RuntimeError('No hay suficientes posiciones 3D estables de un limón')
                break
            s = arm_angles(self.control.snapshot().get('arm_state'))
            before = []
            if s[0] > original.k.Q1_LIM[1]:   # en la canasta: primero de paso a DESPLEGAR
                before, s = [('desplegar', [original.DESPLEGAR])], original.DESPLEGAR
            plan = reasons = None
            for lemon in candidates:
                plan, reasons = await self.in_thread(owner, original.planear_agarre_tol, s, lemon, to_basket)
                if plan is not None:
                    break
                discarded.append(lemon)
            if plan is None:
                if done == 0:
                    raise RuntimeError('Ningún limón tiene plan de agarre: ' + '; '.join(reasons or []))
                break
            try:
                await self.run_task(owner, original, before + plan)
            except ArmRejected:
                if not to_basket or not await self.recover_to_basket(owner, original):
                    raise
            if not to_basket:
                return 1
            pending = lemon
        s = arm_angles(self.control.snapshot().get('arm_state'))
        folded = s[1] >= original.SOLTAR_Q2_MIN_PY and s[2] >= 78.
        path = ([original.DESPLEGAR, (100., 46.7, 50.)] if folded else []) + [original.REPOSO]
        self.update('INTERVINIENDO', 'Brazo al reposo')
        for index, q in enumerate(path):
            await self.move(owner, q, passing=index < len(path) - 1)
        return done

    async def run(self, owner, origin, lemons=1, to_basket=True):
        stage = 'planificación del acercamiento'
        recorder = None
        try:
            planners = asyncio.create_task(asyncio.to_thread(self.planners))
            while not planners.done():
                if monotonic() >= self.deadline:
                    raise RuntimeError('Se perdió la supervisión de Arturito')
                await asyncio.sleep(.05)
            navigation, grasp, tf = planners.result()
            lemon = origin['lemon_in_arm']
            steps = navigation.planear((lemon['x_mm'], lemon['y_mm']), 0., LEMON_STOP_MM, orientar=False)
            if any(kind == 'recto' and not 0 < value <= navigation.MAX_RECTO for kind, value in steps):
                raise RuntimeError('Reubicá el Móvil: el acercamiento es largo o requiere retroceder')
            if monotonic() >= self.deadline:
                raise RuntimeError('Se perdió la supervisión de Arturito')
            recorder = await self.start_recording()
            await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            stage = 'acercamiento'
            self.update('NAVEGANDO', 'Acercándose al limón: ' + navigation.texto(steps))
            for kind, value in steps:
                await self.drive_step(owner, kind, value)
            await self.settle(owner, 1.)
            self.zone = source_value(self.control.snapshot(), 'odom')
            if self.zone is None:
                raise RuntimeError('Falta odometría reciente al llegar')
            self.cycle(owner)
            stage = 'cosecha'
            expected = (LEMON_STOP_MM[0], LEMON_STOP_MM[1], lemon['z_mm'])
            done = await self.harvest(owner, grasp, tf, lemons, to_basket, expected)
            self.zone = None
            stage = 'regreso al cero'
            back = [(kind, -value) for kind, value in reversed(steps)]
            self.update('NAVEGANDO', 'Volviendo al cero: ' + navigation.texto(back))
            for kind, value in back:
                await self.drive_step(owner, kind, value)
            await self.settle(owner, 1.)
            delta = with_displacement(origin, source_value(self.control.snapshot(), 'odom'))['displacement']
            error = '' if delta is None else (f' (a {math.hypot(delta["x_m"], delta["y_m"]) * 100:.1f} cm y '
                                              f'{abs(delta["yaw_deg"]):.0f}° del cero, según la odometría)')
            picked = ('el limón quedó en la pinza' if not to_basket else
                      f'{done} de {lemons} en la canasta' + ('' if done == lemons else
                                                             '; no quedan más limones con plan de agarre a la vista'))
            self.update('FINALIZADO', f'Recolección terminada: {picked}. El Móvil volvió al cero{error}.')
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
        punta.cargar_ajuste()   # como "agarrar" / "cosechar" en punta.py: el ajuste fino de resultados/ajuste_agarre.json
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


def base_refusal(snapshot, linear):
    """Por qué la base no aceptó el movimiento, en palabras del operador (o None si no se sabe)."""
    fields = (snapshot.get('base_state') or '').split()
    def distance(key):
        value = source_value(snapshot, key) if snapshot.get('sources') else None
        return f' a {value["meters"] * 100:.0f} cm' if isinstance(value, dict) and value.get('kind') == 'distance' else ''
    if linear > 0 and any(field.startswith('no_avanza') for field in fields):
        return f'Obstáculo adelante{distance("range_front")}: el Móvil no puede avanzar. Despejá el frente y volvé a calcular el cero.'
    if linear < 0 and 'no_retrocede' in fields:
        return 'El Móvil no puede retroceder (bloqueo atrás): revisá los bumpers y despejá detrás.'
    safety = next((field.split('=', 1)[1] for field in fields if field.startswith('seguridad=')), None)
    if safety not in (None, 'ok'):
        return f'La base frenó por seguridad ({safety}): {" ".join(fields[:3])}'
    if fields[:1] != ['ARMADA']:
        return f'La base dejó de estar armada ({" ".join(fields[:3]) or "sin estado"}).'
    return None


def basket_path(original, s):
    """Camino de punta.recuperar_a_canasta desde los ángulos s, o None si no entra en el modelo."""
    if s[0] > original.k.Q1_LIM[1]:
        return [original.CANASTA]
    up = (s[0],) + tuple(original.CAMINO_CANASTA[0][1:])
    path = [up] + list(original.CAMINO_CANASTA)
    if (original.con_zona(original.revisar_camino, s, up) + original.con_zona(original.revisar_camino, up, path[1])
            + original.con_zona(original.revisar_camino, path[1], path[2])):
        return None
    return path


def stopped_near(arrival, odom):
    """El Móvil quieto y a menos de ZONE_M / ZONE_DEG de la pose `arrival` (odometría) donde se detuvo."""
    if odom is None or abs(odom['linear_m_s']) > .005 or abs(odom['angular_rad_s']) > .02:
        return False
    turn = odom['yaw_rad'] - arrival['yaw_rad']
    return (math.hypot(odom['x_m'] - arrival['x_m'], odom['y_m'] - arrival['y_m']) <= ZONE_M
            and abs(math.degrees(math.atan2(math.sin(turn), math.cos(turn)))) <= ZONE_DEG)


def make_lemon_origin(lemon, seen, odom):
    """Cero del Móvil: el limón más cercano (mm, marco del brazo) y la odometría de ese instante."""
    x, y, z = (float(v) for v in lemon)
    return {'kind': 'lemon', 'lemon_in_arm': {'x_mm': x, 'y_mm': y, 'z_mm': z}, 'lemons_seen': int(seen),
            'distance_m': math.hypot(x, y) / 1000,
            'odom_origin': {key: odom[key] for key in ('x_m', 'y_m', 'yaw_rad')}}


def group_lemons(frames, join_mm, min_views, min_fraction=.3):
    """Igual que punta.Vision.medir_todos: cada posición va al grupo más cercano a menos de join_mm (si no, abre otro);
    quedan los grupos vistos en al menos max(min_views, 30 % de las imágenes). [(mediana mm, n, dispersión mm), ...]
    de más a menos visto."""
    import numpy as np
    groups = []   # [suma, puntos]
    for frame in frames:
        for point in frame:
            v = np.asarray(point, dtype=float)
            distances = [np.linalg.norm(v - total / len(points)) for total, points in groups]
            if distances and min(distances) < join_mm:
                group = groups[int(np.argmin(distances))]
                group[0] = group[0] + v
                group[1].append(v)
            else:
                groups.append([v.copy(), [v]])
    minimum = max(min_views, min_fraction * len(frames))
    result = []
    for _, points in groups:
        if len(points) < minimum:
            continue
        p = np.asarray(points)
        median = np.median(p, axis=0)
        result.append((median, len(p), float(np.median(np.linalg.norm(p - median, axis=1)))))
    result.sort(key=lambda r: -r[1])
    return result
