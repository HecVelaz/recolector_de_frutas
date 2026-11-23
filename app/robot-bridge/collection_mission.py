"""Recolección con los transportes del puente ROS (21/11: cero relativo al limón más cercano).

El cero del Móvil es su pose cuando el operador pide «Calcular cero»: se mide el limón más cercano con el estéreo y se
guarda junto con la odometría de ese instante. «Iniciar recolección» acerca el Móvil hasta dejar ese limón en
LEMON_STOP_MM respecto de J1 (sin cambiar el rumbo ni retroceder), cosecha como punta.cosechar y vuelve al cero
desandando el mismo camino.
"""

import asyncio
import concurrent.futures
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import multiprocessing
import signal
import sys
import types
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
# 21/11 (2.ª vez): J3 llegó a 79,96 y, al girar J1 hacia la canasta, el firmware igual la cortó por "sin cuentas" (con
# destino 80 intentaba corregir 0,04° en la zona dura). Con J1 pasada J1_MAX_NORMAL el brazo tiene que estar plegado
# (config.h SOLTAR_*): si J2 y J3 ya están dentro de esa zona, se quedan donde están y solo gira J1
J1_MAX_NORMAL, FOLDED_Q2, FOLDED_Q3_MIN = 118., (42.3, 50.7), 78.3
ORIGIN_SECONDS = 3.8      # medición del limón para el cero (21/11: 3 s juntaba a veces 2 lecturas con la estéreo a ~1 Hz; la app corta «Calcular cero» a los 4,5 s: con 4,5 el pedido tardaba 4,53 s)
# 21/11: el cero solo sirve para planear el acercamiento; al llegar, la cosecha vuelve a medir con el criterio estricto
# de punta (MIN_POSICIONES, DISPERSION_MAX) y a menos de EXPECTED_RADIUS_MM. Por eso acá alcanza con menos (un limón a
# ~95 cm de la cámara daba 2 lecturas en 3 s y no se podía fijar el cero sin acercar el robot a mano).
ORIGIN_MIN_VIEWS, ORIGIN_SPREAD_MM = 2, 30.
# 21/11: cero sin limón a la vista -> la recolección lo busca girando sobre el lugar a estos rumbos (° respecto del
# cero, + a la izquierda), quieta y midiendo en cada uno como el cero; si no ve ninguno vuelve al rumbo del cero
SEARCH_HEADINGS_DEG = (15., 25., -15., -25.)
# Dónde queda el limón respecto de J1 al llegar (mm; x a la derecha, y adelante). Con punta.planear_agarre_tol desde el
# reposo hay agarre a la canasta con el limón 6 cm más arriba o más abajo, y queda a ~89 cm de la cámara (21/11)
LEMON_STOP_MM = (-575., 170.)   # parada fija de respaldo, a 60 cm (23/11; 21/11: -500, 150; a 57 cm sin el ajuste fino
                                # la pinza quedó 3 cm corta)
# Pedido del usuario (23/11; antes 50-55 cm): cosechar con el limón a ~60 cm de J1, para que la pinza baje a su altura
# lejos de las ramas y entre horizontal ~15 cm (la punta no se recoge a menos de ~44 cm: entrada = r - 44 cm). Si ya
# está en REACH_MM y tiene plan, la base no se mueve; si no, se acerca en su dirección hasta dejarlo a STOP_RADIUS_MM.
# Más cerca que REACH_MM (nunca retrocede): se cosecha sin moverse si hay plan, con entrada corta (lo de antes)
STOP_RADIUS_MM, REACH_MM = 600., (580., 630.)
CLOSE_MM = 500.   # 21/11: punta.py necesita r > ~500 para entrar de frente
MIN_BEARING_DEG = 8.   # J1 no baja de 3°: con el limón a 3° o más adelante de J1 hay agarre a 13-21 cm de z (21/11)
ZONE_M, ZONE_DEG = .04, 5.
# Al llegar a la parada se sabe dónde tiene que estar el limón del cero: solo vale uno a menos de esto de ahí. El
# estéreo a veces mide el follaje delante del limón (21/11: el mismo limón a 42 y a 77 cm, alternando); ese punto
# fantasma queda descartado y el brazo no va a buscarlo al aire
EXPECTED_RADIUS_MM = 120.   # mientras actúa el brazo, el Móvil quieto a menos de esto de donde llegó
REVERSE_M_S = .06            # al volver al cero desandando el camino y al reubicarse en el Recolector (atrás no hay sensores)
# Modo Recolector (23/11, pedido del usuario): si un limón no está en la zona buena, el Móvil se reubica para dejarlo a
# STOP_RADIUS_MM y entre estos ángulos adelante de J1, con la orientación final libre y marcha atrás de hasta
# MAX_REVERSE_MM (atrás no hay sensores)
REPOSITION_BEARINGS_DEG = (15., 35.)
MAX_REVERSE_MM = 200.
REPOSITION_PLANS = 4   # paradas a probar con el planificador del brazo (cada plan puede tardar ~6-30 s)
# Pedido del usuario (21/11): la pinza cerró justo debajo del limón; el punto de agarre sube GRASP_RAISE_MM reales (en el
# modelo de punta, 1 mm de z son ~1,43 mm reales). 23/11: de 2 cm a 0,75 y a -0,25 (cerraba alto)
GRASP_RAISE_MM = -2.5   # 23/11, usuario: con 20 cerraba 1-1,5 cm alto; con 7,5, 1 cm más abajo todavía
RETURN_SECONDS = 90.
# Modo Recolector (21/11): base quieta, escaneo de SCAN_SECONDS desde el primer par estéreo, visión pausada mientras
# el brazo cosecha la lista guardada. Se pausa el procesamiento (rectificación, disparidad, YOLO y localizador:
# ~1,9 núcleos de la Pi), no las cámaras: un SIGSTOP a camera_ros puede dejar colgada la cámara de libcamera.
SCAN_SECONDS = 3.
# Visión a pedido (21/11): se apaga y se prende entera (cámaras, estéreo y YOLO, el grupo de start_limon.sh). Un
# SIGSTOP a la rectificación dejaba a la cámara izquierda sin publicar (Fast DDS por memoria compartida), por eso no
# se congela: se apaga. Arrancar tarda ~15 s: margen de VISION_DEMAND_S sin pedido antes de apagarla.
VISION_DEMAND_S = 30.
VISION_ON_DEMAND = True    # interruptor general de la visión a pedido
VISION_STOP = ['pkill', '-TERM', '-f', 'start_limon.sh']
VISION_START = ['bash', str(Path.home() / 'scripts/vision.sh')]
VISION_ALIVE = 'camera_ros/lib/camera_ros/camera_node'   # mientras quede alguno, no se puede volver a arrancar
VISION_READY_S = 40.   # espera de un par estéreo nuevo (la visión recién prendida tarda ~15 s)   # brazo al reposo y regreso al cero, aunque se haya agotado el tiempo de la recolección
HEIGHT_CM = (33, 64)   # alcance en altura (21/11: 33 cm medido con cosechar; ~64 cm con plan de punta.py sin los +2 cm): solo para explicar un acercamiento sin plan


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
        self.status = {'state': 'INACTIVO', 'message': 'Sin recolección en curso.'}
        self._planners = None
        # Visión a pedido (21/11): la app la pide mientras está en Recolector, Recolección o en la pestaña Visión;
        # sin pedido (ni misión activa) se pausa. vision_hold: pausada a propósito (cosecha del modo Recolector).
        self.vision_demand_until = monotonic() + VISION_DEMAND_S   # al arrancar, la dejada por arrancar_pi.sh
        self.vision_hold = False
        self.vision_paused = None
        self._pool = None

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
        if not origin or 'lemon_in_arm' not in origin:   # sin cero o un cero ArUco viejo
            raise HTTPException(409, 'Calculá primero el cero del Móvil')
        if origin.get('used'):
            raise HTTPException(409, 'El limón de este cero ya se cosechó: calculá el cero de nuevo')
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
        # 21/11: 180 -> 360 s: con un limón alto cada plan de punta.py tarda ~30 s en la Pi (y a veces dos por parada)
        self.run_until = monotonic() + 360. + 120. * (lemons - 1) + (60. if origin['lemon_in_arm'] is None else 0.)
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('BUSCANDO', 'Planeando el acercamiento al limón más cercano.')
        self.task = asyncio.create_task(self.run(self.owner, origin, lemons, to_basket))
        return self.snapshot()

    def start_return(self, operator, origin):
        """«Volver al cero»: el brazo al reposo (si tiene referencia) y el Móvil al cero por la odometría."""
        self.control.tick()
        if self.active or self.control.owner is not None:
            raise HTTPException(409, 'Detené el mando antes de volver al cero')
        if not origin:
            raise HTTPException(409, 'No hay un cero guardado: calculalo primero')
        start = self.control.snapshot()
        if not self.control.arm_ready(start.get('arm_state')):
            raise HTTPException(409, 'El brazo no tiene referencia: hacé el homing antes de mover el Móvil')
        if not source_value(start, 'odom'):
            raise HTTPException(409, 'Falta odometría reciente')
        self.owner, self.operator = f'regreso-{uuid4()}', operator
        self.deadline = monotonic() + 1.25
        self.run_until = monotonic() + 150.
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('NAVEGANDO', 'Volviendo al reposo y al cero.')
        self.task = asyncio.create_task(self.run_return(self.owner, origin))
        return self.snapshot()

    def start_scan(self, operator, lemons=1, seconds=SCAN_SECONDS):
        """Modo Recolector: cosechar la lista del escaneo; si hace falta, reubicando el Móvil (no hace falta cero)."""
        self.control.tick()
        if self.active or self.control.owner is not None:
            raise HTTPException(409, 'Detené el mando antes de iniciar el modo Recolector')
        start = self.control.snapshot()
        arm = start.get('arm_state')
        if not self.control.arm_ready(arm) or max(abs(a - b) for a, b in zip(arm_angles(arm), (3, 17, 4))) > 3:
            raise HTTPException(409, 'Hacé el homing y dejá el brazo en reposo')
        if self.stereo.snapshot()['status'] == 'waiting':
            raise HTTPException(409, 'Esperá a que la visión estéreo reciba profundidad')
        self.owner, self.operator = f'recolector-{uuid4()}', operator
        self.deadline = monotonic() + 1.25
        self.run_until = monotonic() + 180. + 150. * lemons   # 23/11: + reubicarse y volver a prender la visión
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('BUSCANDO', f'Modo Recolector: escaneo de {seconds:.0f} s con el Móvil quieto.')
        self.task = asyncio.create_task(self.run_scan(self.owner, lemons, seconds))
        return self.snapshot()

    async def scan_frames(self, owner, seconds):
        """Las imágenes de /limon/todos durante `seconds` s contados desde la primera nueva (el primer par estéreo
        procesado después de empezar; hasta VISION_READY_S de espera: la visión puede estar arrancando)."""
        self.demand_vision()
        first, waited = None, monotonic() + VISION_READY_S
        start_stamp = self.stereo.target_frame()[0]
        while first is None:
            if monotonic() >= waited:
                raise RuntimeError('La visión estéreo no entrega pares nuevos: revisá las cámaras')
            self.cycle(owner)
            stamp = self.stereo.target_frame()[0]
            if stamp is not None and (start_stamp is None or stamp > start_stamp):
                first = stamp
            await asyncio.sleep(.05)
        return await self.measure_frames(owner, seconds)

    async def run_scan(self, owner, count, seconds):
        """Modo Recolector: detener la base -> escanear -> guardar las coordenadas -> apagar la visión -> cosechar la
        lista de a uno -> brazo al reposo (sin verificar con la visión: pedido del usuario, 21/11)."""
        stage, recorder, paused, results = 'preparación', None, False, []
        try:
            navigation, grasp, tf = await asyncio.to_thread(self.planners)
            recorder = await self.start_recording()
            await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            stage = 'escaneo'
            frames = await self.scan_frames(owner, seconds)
            groups = group_lemons(frames, grasp.AGRUPAR_MM, ORIGIN_MIN_VIEWS)
            targets = sorted((raised(grasp.limon_de_cara(tf, face, n, spread)) for face, n, spread in groups
                              if spread <= grasp.DISPERSION_MAX), key=lambda l: math.hypot(l[0], l[1]))
            if not targets:
                self.update('FINALIZADO', f'Escaneo de {seconds:.0f} s sin limones estables: no se cosecha en esta parada.')
                return
            pending = [lemon for lemon in targets if not in_zone(lemon)]
            # La visión se apaga para que el brazo planee más rápido, salvo que haga falta reubicarse: prenderla en
            # medio de la misión cargó la Pi y venció el mando (23/11); queda prendida, como en la Recolección
            if pending:
                self.update('BUSCANDO', f'Lista guardada: {len(targets)} limón(es); cosechando de a uno.')
            else:
                self.update('BUSCANDO', f'Lista guardada: {len(targets)} limón(es). Visión pausada; cosechando de a uno.')
                self.vision_hold = paused = True
                self.sync_vision()
            stage = 'cosecha'
            done = 0
            # 1) Los que ya están en la zona buena, sin mover la base (entrada horizontal larga)
            for lemon in (lemon for lemon in targets if in_zone(lemon)):
                if done >= count:
                    break
                done += await self.pick_here(owner, grasp, lemon, results)
            # 2) El resto, del más cercano: reubicar el Móvil para dejarlo en la zona buena, medir de nuevo y cosechar
            #    desde ahí (23/11, pedido del usuario). Si no se puede, desde acá como antes (entrada corta) o se saltea
            for lemon in pending:
                if done >= count:
                    break
                stage = 'planificación de la reubicación'
                found = await self.reposition(owner, navigation, grasp, lemon, True)
                if found is None:
                    stage = 'cosecha'
                    done += await self.pick_here(owner, grasp, lemon, results)
                    continue
                steps, expected = found
                stage = 'reubicación del Móvil'
                await self.arm_to_rest(owner, grasp)
                self.update('NAVEGANDO', 'Reubicando el Móvil para el limón: ' + navigation.texto(steps))
                for kind, value in steps:
                    await self.drive_step(owner, kind, value)
                await self.settle(owner, 1.)
                self.zone = source_value(self.control.snapshot(), 'odom')
                if self.zone is None:
                    raise RuntimeError('Falta odometría reciente al llegar')
                stage = 'cosecha tras reubicarse'
                await self.scan_frames(owner, 0.)   # espera a que la visión entregue pares nuevos
                try:
                    got = await self.harvest(owner, grasp, tf, count - done, True, expected)
                    results.append((lemon, f'reubicado: {got} en la canasta'))
                    done += got
                except ArmRejected:
                    raise
                except RuntimeError as error:
                    results.append((lemon, f'reubicado, sin cosecha: {error}'[:120]))
                self.zone = None
                break   # el resto de la lista quedó en el marco de antes de moverse
            stage = 'regreso del brazo al reposo'
            await self.arm_to_rest(owner, grasp)
            # Pedido del usuario (21/11): sin volver a prender la visión para verificar; se informa lo ejecutado
            detail = '; '.join(f'{math.hypot(l[0], l[1]) / 10:.0f} cm: {r}' for l, r in results)
            self.update('FINALIZADO', f'Modo Recolector: {done} agarre(s) completo(s) de {len(targets)} limón(es) en la '
                        f'lista. {detail}')
        except asyncio.CancelledError:
            self.update('INACTIVO', 'Modo Recolector detenido por el operador.')
        except (RuntimeError, HTTPException, ValueError, OSError, ImportError) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            self.update('RECUPERACION', f'El modo Recolector se detuvo durante {stage}. {detail}')
        except Exception:
            logging.exception('Falló el modo Recolector')
            self.update('RECUPERACION', 'Falló el modo Recolector. Consultá el registro de la Raspberry Pi.')
        finally:
            if paused:
                self.vision_hold = False
                self.sync_vision()
            try:
                if self.control.owner == owner:
                    self.control.stop()
            finally:
                if recorder is not None:
                    await self.stop_recording(recorder)
                self.save_log()

    def demand_vision(self):
        """La app necesita la visión (la pide cada ~2 s): vale VISION_DEMAND_S."""
        self.vision_demand_until = monotonic() + VISION_DEMAND_S
        self.sync_vision()
        return {'vision_paused': bool(self.vision_paused)}

    def sync_vision(self):
        """Pausa o reanuda la visión según el pedido de la app, la misión activa y vision_hold (solo si cambia)."""
        if not VISION_ON_DEMAND:
            return
        paused = self.vision_hold or not (self.active or monotonic() < self.vision_demand_until)
        if paused != self.vision_paused and self.set_vision_paused(paused):
            self.vision_paused = paused

    def set_vision_paused(self, paused):
        """Apaga (TERM al grupo de start_limon.sh) o prende (scripts/vision.sh) la visión entera, sin esperar. False si
        todavía no se puede prender (quedan procesos del apagado anterior): sync_vision lo reintenta."""
        import subprocess
        if paused:
            subprocess.run(VISION_STOP, capture_output=True, timeout=5)
            return True
        if subprocess.run(['pgrep', '-f', VISION_ALIVE], capture_output=True).returncode == 0 and self.vision_paused:
            return False   # se está apagando: esperar a que termine antes de lanzarla de nuevo
        subprocess.run(VISION_START, capture_output=True, timeout=10)
        return True

    async def run_return(self, owner, origin):
        try:
            planners = asyncio.create_task(asyncio.to_thread(self.planners))
            while not planners.done():
                if monotonic() >= self.deadline:
                    raise RuntimeError('Se perdió la supervisión de Arturito')
                await asyncio.sleep(.05)
            navigation, grasp, _ = planners.result()
            await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            await self.return_home(owner, navigation, grasp, origin)
            self.update('FINALIZADO', 'El brazo está en reposo y el Móvil volvió al cero' + self.home_error(origin) + '.')
        except asyncio.CancelledError:
            self.update('INACTIVO', 'Regreso al cero detenido por el operador.')
        except (RuntimeError, HTTPException, ValueError, OSError, ImportError) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            self.update('RECUPERACION', f'No se pudo volver al cero. {detail}')
        except Exception:
            logging.exception('Falló el regreso al cero')
            self.update('RECUPERACION', 'Falló el regreso al cero. Consultá el registro de la Raspberry Pi.')
        finally:
            if self.control.owner == owner:
                self.control.stop()
            self.save_log()

    async def approach(self, owner, navigation, original, target, to_basket):
        """(pasos de la base, dónde va a quedar el limón respecto de J1) para cosechar `target` (mm, marco del brazo)
        con el limón a ~60 cm: sin moverse si ya está en REACH_MM (o más cerca) y tiene plan; si no, acercándose en su dirección
        hasta STOP_RADIUS_MM, o a la parada fija. Nunca retrocede. owner None: todavía sin el mando de la base."""
        angles = arm_angles(self.control.snapshot().get('arm_state'))
        r = math.hypot(target[0], target[1])
        if CLOSE_MM <= r <= REACH_MM[1]:   # en REACH_MM, o más cerca (no se retrocede): sin moverse si hay plan
            plan, _ = await self.grasp_plan(owner, original, angles, target, to_basket)
            if plan is not None:
                return [], target
        # 21/11: con el limón justo a la izquierda de J1 (y ≈ -2 cm) la parada en su dirección pedía J1 = 1,4° (mín. 3°)
        # y no había agarre: probar también a la misma distancia pero con el limón al menos MIN_BEARING_DEG adelante
        bearing = max(math.atan2(target[1], -target[0]), math.radians(MIN_BEARING_DEG))
        ahead = (-STOP_RADIUS_MM * math.cos(bearing), STOP_RADIUS_MM * math.sin(bearing))
        for stop in ((target[0] * STOP_RADIUS_MM / r, target[1] * STOP_RADIUS_MM / r), ahead, LEMON_STOP_MM):
            steps = navigation.planear(target[:2], 0., stop, orientar=False)
            if any(kind == 'recto' and not 0 < value <= navigation.MAX_RECTO for kind, value in steps):
                continue
            expected = (stop[0], stop[1], target[2]) if steps else target
            plan, _ = await self.grasp_plan(owner, original, original.REPOSO, expected, to_basket)
            if plan is not None:
                return steps, expected
        height = (256 + 1.43 * target[2]) / 10   # cm del piso (z del modelo de punta)
        if not HEIGHT_CM[0] <= height <= HEIGHT_CM[1]:
            raise RuntimeError(f'El limón está a ~{height:.0f} cm del piso y el brazo agarra de {HEIGHT_CM[0]} a '
                               f'{HEIGHT_CM[1]} cm: acercarse no lo arregla. Bajá o subí ese limón, o sacalo de la vista.')
        raise RuntimeError('Reubicá el Móvil: no hay un acercamiento sin retroceder que deje el limón a ~60 cm '
                           'con plan de agarre')

    async def pick_here(self, owner, grasp, lemon, results):
        """Modo Recolector: cosechar `lemon` sin mover la base (brazo desde donde está). 1 si quedó en la canasta."""
        s = arm_angles(self.control.snapshot().get('arm_state'))
        before = []
        if s[0] > grasp.k.Q1_LIM[1]:   # en la canasta: primero de paso a DESPLEGAR
            before, s = [('desplegar', [grasp.DESPLEGAR])], grasp.DESPLEGAR
        # 21/11: un limón casi justo a la izquierda de J1 pedía J1 < 3° y el firmware cortó la cosecha
        if math.degrees(math.atan2(lemon[1], -lemon[0])) < MIN_BEARING_DEG:
            results.append((lemon, f'salteado: a menos de {MIN_BEARING_DEG:.0f}° adelante de J1 y sin reubicación'))
            return 0
        plan, reasons = await self.grasp_plan(owner, grasp, s, lemon, True)
        if plan is None:
            results.append((lemon, 'sin plan: ' + '; '.join(reasons or [])[:80]))
            return 0
        try:
            await self.run_task(owner, grasp, before + plan)
        except ArmRejected as error:
            results.append((lemon, f'falló: {error}'))
            if not await self.recover_to_basket(owner, grasp) and not await self.arm_to_rest(owner, grasp):
                raise
            return 0
        results.append((lemon, 'hecho'))
        return 1

    async def reposition(self, owner, navigation, original, target, to_basket):
        """Modo Recolector (23/11): (pasos, dónde va a quedar el limón) para dejarlo a STOP_RADIUS_MM (±20 mm) y entre
        REPOSITION_BEARINGS_DEG adelante de J1, con plan de agarre desde el reposo. La orientación final del Móvil es
        libre (J1 no está en el centro de giro: a veces alcanza con girar): de todas las combinaciones, la que menos
        mueve el robot (giros en grados + 2 por cm recto; la marcha atrás, hasta MAX_REVERSE_MM, cuesta 60 más;
        fuera de STOP_RADIUS_MM exacto, 25 más).
        None si no hay."""
        low, high = REPOSITION_BEARINGS_DEG
        options = []
        for radius in (STOP_RADIUS_MM, STOP_RADIUS_MM - 20., STOP_RADIUS_MM + 20.):
            for bearing in range(int(low), int(high) + 1, 5):
                # 23/11: el mando de la misión vence a los 0,22 s; la búsqueda entera lo hizo vencer en la Pi
                if owner is not None:
                    self.cycle(owner)
                await asyncio.sleep(0)
                stop = (-radius * math.cos(math.radians(bearing)), radius * math.sin(math.radians(bearing)))
                best = None
                for heading in range(-120, 121, 5):
                    steps = navigation.planear(target[:2], float(heading), stop, orientar=True)
                    if any(kind == 'recto' and not -MAX_REVERSE_MM <= value <= navigation.MAX_RECTO
                           for kind, value in steps):
                        continue
                    cost = (sum(abs(v) for k, v in steps if k == 'giro') + sum(abs(v) for k, v in steps if k == 'recto')
                            / 5 + (60. if any(k == 'recto' and v < 0 for k, v in steps) else 0.))
                    if best is None or cost < best[0]:
                        best = (cost, steps)
                if best is not None:   # a STOP_RADIUS_MM exacto la entrada horizontal es más larga: se prefiere
                    extra = 0. if radius == STOP_RADIUS_MM else 25.
                    options.append((best[0] + extra, len(options), best[1], (stop[0], stop[1], target[2])))
        for _, _, steps, expected in sorted(options)[:REPOSITION_PLANS]:
            plan, _ = await self.grasp_plan(owner, original, original.REPOSO, expected, to_basket)
            if plan is not None:
                return steps, expected
        return None

    async def grasp_plan(self, owner, original, s, lemon, to_basket):
        """punta.planear_agarre_tol con el agarre GRASP_RAISE_MM más arriba (como lo da raised); si no hay plan, a la
        altura medida (21/11: un limón a ~64 cm del piso tenía plan, pero 2 cm más arriba el camino a la canasta
        sacaba a J2/J3 de la franja). Los motivos que devuelve son los del primer intento."""
        plan, reasons = await self.plan(owner, original, 'planear_agarre_tol', s, lemon, to_basket)
        if plan is None:
            lower = (lemon[0], lemon[1], lemon[2] - GRASP_RAISE_MM / 1.43)
            plan, _ = await self.plan(owner, original, 'planear_agarre_tol', s, lower, to_basket)
        return plan, reasons

    async def arm_to_rest(self, owner, original):
        """El brazo al reposo desde donde quedó. Plegado (canasta), como el final de punta.cosechar pero sin volver a
        pedirle a J3 la zona dura de 80°; si no, con punta.planear_q. False si no hay un camino seguro."""
        s = arm_angles(self.control.snapshot().get('arm_state'))
        if max(abs(a - b) for a, b in zip(s, original.REPOSO)) <= 3.:
            return True
        if s[1] >= original.SOLTAR_Q2_MIN_PY and s[2] >= 78.:
            path = ([(100., s[1], s[2])] if s[0] > 100.5 else []) + [(100., 46.7, 50.), tuple(original.REPOSO)]
        else:
            path, _ = await self.plan(owner, original, 'rest_plan', s)
            if path is None:
                return False
        self.update('NAVEGANDO', 'Brazo al reposo')
        for index, q in enumerate(path):
            await self.move(owner, q, passing=index < len(path) - 1)
        return True

    async def return_home(self, owner, navigation, original, origin):
        """Brazo al reposo y Móvil al cero desandando por la odometría (girar, retroceder recto, girar)."""
        # 21/11: volver es lo seguro: siempre con tiempo propio, aunque la recolección haya agotado el suyo
        self.run_until = max(self.run_until, monotonic() + RETURN_SECONDS)
        if not await self.arm_to_rest(owner, original):
            raise RuntimeError('No hay un camino seguro del brazo al reposo: hacé el homing antes de mover el Móvil.')
        odom = source_value(self.control.snapshot(), 'odom')
        if odom is None:
            raise RuntimeError('Falta odometría reciente para volver al cero')
        steps = home_steps(origin, odom)
        self.update('NAVEGANDO', 'Volviendo al cero: ' + (navigation.texto(steps) or 'ya está en el cero'))
        for kind, value in steps:
            await self.drive_step(owner, kind, value)
        await self.settle(owner, 1.)

    def home_error(self, origin):
        delta = with_displacement(origin, source_value(self.control.snapshot(), 'odom'))['displacement']
        return '' if delta is None else (f' (a {math.hypot(delta["x_m"], delta["y_m"]) * 100:.1f} cm y '
                                         f'{abs(delta["yaw_deg"]):.0f}° del cero, según la odometría)')

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

    def pool(self):
        """Un proceso aparte para los planificadores de punta.py (21/11): en un hilo acaparaban el intérprete del puente
        y el estado de la base "envejecía" más de 650 ms aunque llegaba bien, y la sesión se cortaba."""
        if self._pool is None:
            paths = [str(self.tools), str(self.tools.parent.parent / '20-brazo-coordinado/tools')]
            self._pool = concurrent.futures.ProcessPoolExecutor(
                1, mp_context=multiprocessing.get_context('spawn'), initializer=_planner_init, initargs=(paths,))
        return self._pool

    def warm(self):
        """Arranca el proceso de los planificadores (y carga punta.py) antes de que haga falta."""
        return self.pool().submit(_planner_call, 'ping')

    def close(self):
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)

    async def plan(self, owner, original, name, *args):
        """Planificador de punta.py (planear_agarre_tol, basket_path, rest_plan) en el proceso aparte, renovando mientras
        tanto la orden a la base (owner) o solo controlando la supervisión (owner None). Con planificadores simulados
        (pruebas), en un hilo."""
        if isinstance(original, types.ModuleType):
            work = asyncio.get_running_loop().run_in_executor(self.pool(), _planner_call, name, *args)
        else:
            function = {'basket_path': lambda *a: basket_path(original, *a),
                        'rest_plan': lambda q: original.con_margen(original.MARGEN_SALIDA_CARGA, original.planear_q,
                                                                   q, original.REPOSO)}.get(name) or getattr(original, name)
            work = asyncio.ensure_future(asyncio.to_thread(function, *args))
        while not work.done():
            if owner is not None:
                self.cycle(owner)
            elif monotonic() >= self.deadline:
                raise RuntimeError('Se perdió la supervisión de Arturito')
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

        return nearest_rough(await self.collect_frames(ORIGIN_SECONDS, tick), grasp, tf)

    async def search(self, owner, grasp, tf):
        """Cero sin limón (21/11): gira sobre el lugar a SEARCH_HEADINGS_DEG y en cada rumbo mide como el cero. Devuelve
        el limón más cercano (mm, marco del brazo en el rumbo actual); si no ve ninguno, vuelve al rumbo del cero."""
        heading = 0.
        for target in SEARCH_HEADINGS_DEG:
            side = 'izquierda' if target > 0 else 'derecha'
            self.update('BUSCANDO', f'Sin limón a la vista: girando {abs(target):.0f}° a la {side} del cero para buscarlo.')
            await self.drive_step(owner, 'giro', target - heading)
            heading = target
            lemon, _ = nearest_rough(await self.measure_frames(owner, ORIGIN_SECONDS + 1.), grasp, tf)
            if lemon is not None:
                return lemon
        await self.drive_step(owner, 'giro', -heading)
        limit = max(abs(h) for h in SEARCH_HEADINGS_DEG)
        raise RuntimeError(f'No encontré limones girando ±{limit:.0f}°: acercá el Móvil al limonero y calculá el cero de nuevo')

    async def measure_lemons(self, owner, original, tf, near=None):
        """Como punta.medir_limones: agrupa los limones de todas las imágenes y da sus puntos de agarre (mm, marco del
        brazo) con las correcciones de punta.limon_de_cara (z de la visión, adelante, izquierda, arriba y ajuste fino).
        near: dónde tiene que estar el limón (mm, marco del brazo). Entonces alcanza con punta.MIN_POSICIONES
        posiciones aunque haya lecturas repartidas, y van primero los que están a menos de EXPECTED_RADIUS_MM de ahí;
        si no hay ninguno, todos (21/11, pedido del usuario: la profundidad del cero puede errar 10-25 cm; al llegar se
        cosecha lo que se mide ahí si el brazo tiene plan)."""
        groups = group_lemons(await self.measure_frames(owner), original.AGRUPAR_MM, original.MIN_POSICIONES,
                              min_fraction=0. if near is not None else .3)
        lemons = [raised(original.limon_de_cara(tf, face, n, spread)) for face, n, spread in groups
                  if spread <= original.DISPERSION_MAX]
        if near is not None:
            close = [lemon for lemon in lemons if math.dist(lemon, near) <= EXPECTED_RADIUS_MM]
            if lemons and not close:
                miss = min(math.dist(lemon, near) for lemon in lemons) / 10
                self.update('BUSCANDO', f'El limón estaba a {miss:.0f} cm de donde se esperaba: se cosecha según la '
                            'medición de acá, si el brazo llega.')
            return close or lemons
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
        now = arm_angles(self.control.snapshot().get('arm_state'))
        if q[0] > J1_MAX_NORMAL and FOLDED_Q2[0] <= now[1] <= FOLDED_Q2[1] and now[2] >= FOLDED_Q3_MIN:
            q = (q[0], now[1], now[2])
        nudged = False
        for attempt in range(MV_RETRIES + 1):
            command = f"{'mvp' if passing else 'mv'} {q[0]:.2f} {q[1]:.2f} {q[2]:.2f}"
            try:
                await self.arm_instruction(owner, command, 'parked', MV_TIMEOUT)
                return
            except ArmRejected as error:
                if 'sin cuentas' in str(error) and not nudged:
                    now = arm_angles(self.control.snapshot().get('arm_state'))
                    # Las que están a menos de STUCK_NEAR_DEG de su destino se quedan donde están y se reintenta una
                    # vez lo que falta (si la que no llega está lejos y trabada de verdad, vuelve a cortar)
                    near = [abs(a - b) < STUCK_NEAR_DEG for a, b in zip(now, q)]
                    if any(near) and not all(near):
                        q = tuple(a if close else b for a, b, close in zip(now, q, near))
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
        path = await self.plan(owner, original, 'basket_path', s)   # el modelo tarda: sin trabar el lazo de la base
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
                plan, reasons = await self.grasp_plan(owner, original, s, lemon, to_basket)
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
            if lemon is None:   # 21/11: el cero no vio limón -> buscarlo girando (hace falta el mando de la base)
                recorder = await self.start_recording()
                await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
                stage = 'búsqueda del limón'
                target = await self.search(owner, grasp, tf)
                stage = 'planificación del acercamiento'
                self.update('BUSCANDO', 'Limón encontrado: planeando el acercamiento.')
                steps, expected = await self.approach(owner, navigation, grasp, target, to_basket)
            else:
                target = (lemon['x_mm'], lemon['y_mm'], lemon['z_mm'])
                steps, expected = await self.approach(None, navigation, grasp, target, to_basket)
                if monotonic() >= self.deadline:
                    raise RuntimeError('Se perdió la supervisión de Arturito')
                recorder = await self.start_recording()
                await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            done = 0
            while True:
                stage = 'acercamiento'
                self.update('NAVEGANDO', ('Acercándose al limón: ' + navigation.texto(steps)) if steps
                            else 'El limón se alcanza desde acá: el Móvil no se mueve.')
                for kind, value in steps:
                    await self.drive_step(owner, kind, value)
                await self.settle(owner, 1.)
                self.zone = source_value(self.control.snapshot(), 'odom')
                if self.zone is None:
                    raise RuntimeError('Falta odometría reciente al llegar')
                self.cycle(owner)
                stage = 'cosecha'
                try:
                    picked_now = await self.harvest(owner, grasp, tf, 1, to_basket, expected)
                except RuntimeError as error:
                    # Del segundo en adelante, un limón sin plan o que no está donde se esperaba no es una falla:
                    # se termina con lo cosechado y se vuelve al cero (los cortes del brazo siguen siendo fallas)
                    if not done or isinstance(error, ArmRejected):
                        raise
                    self.update('BUSCANDO', f'El siguiente limón no se puede cosechar desde acá: {error}')
                    picked_now = 0
                done += picked_now
                if done:
                    origin['used'] = True   # ese limón ya no está: para recolectar de nuevo, otro cero
                self.zone = None
                if done >= lemons or not to_basket or not picked_now:
                    break
                # Pedido del usuario (21/11): el siguiente limón, medido desde acá (el brazo quedó en reposo)
                stage = 'búsqueda del siguiente limón'
                self.update('BUSCANDO', f'Buscando el siguiente limón ({done} de {lemons} en la canasta).')
                remaining = await self.measure_lemons(owner, grasp, tf)
                if not remaining:
                    break
                target = min(remaining, key=lambda l: math.hypot(l[0], l[1]))
                try:
                    steps, expected = await self.approach(owner, navigation, grasp, target, to_basket)
                except RuntimeError as error:
                    self.update('BUSCANDO', f'El siguiente limón no se puede cosechar desde acá: {error}')
                    break
            self.zone = None
            stage = 'regreso al cero'
            await self.return_home(owner, navigation, grasp, origin)
            error = self.home_error(origin)
            picked = ('el limón quedó en la pinza' if not to_basket else
                      f'{done} de {lemons} en la canasta' + ('' if done == lemons else
                                                             '; el siguiente no se puede cosechar desde acá'))
            self.update('FINALIZADO', f'Recolección terminada: {picked}. El Móvil volvió al cero{error}.')
        except asyncio.CancelledError:
            self.update('INACTIVO', 'Recolección detenida por el operador.')
        except (RuntimeError, HTTPException, ValueError, OSError, ImportError) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            self.update('RECUPERACION', f'La recolección se detuvo durante {stage}. {detail}')
            # Pedido del usuario (21/11): si falla la cosecha y la misión conserva el mando, volver igual al cero
            if stage == 'cosecha' and self.control.owner == owner:
                self.zone = None
                try:
                    await self.return_home(owner, navigation, grasp, origin)
                    self.update('RECUPERACION', f'La recolección se detuvo durante cosecha ({detail}). El brazo '
                                f'volvió al reposo y el Móvil al cero{self.home_error(origin)}.')
                except asyncio.CancelledError:
                    self.update('INACTIVO', 'Regreso al cero detenido por el operador.')
                except (RuntimeError, HTTPException, ValueError) as second:
                    reason = second.detail if isinstance(second, HTTPException) else str(second)
                    self.update('RECUPERACION', f'La recolección se detuvo durante cosecha ({detail}) y no pudo '
                                f'volver al cero: {reason}')
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


def _planner_init(paths):
    """En el proceso de los planificadores: punta.py e ir_a_parada.py de las herramientas originales."""
    import contextlib
    import io
    for path in paths:
        if path not in sys.path:
            sys.path.append(path)
    with contextlib.redirect_stdout(io.StringIO()):
        import punta  # noqa: F401


def _planner_call(name, *args):
    """En el proceso de los planificadores. Los resultados son listas de tuplas y textos (se pueden enviar)."""
    import contextlib
    import io
    import punta
    with contextlib.redirect_stdout(io.StringIO()):
        if name == 'ping':
            return True
        if name == 'basket_path':
            return basket_path(punta, *args)
        if name == 'rest_plan':
            return punta.con_margen(punta.MARGEN_SALIDA_CARGA, punta.planear_q, args[0], punta.REPOSO)
        return getattr(punta, name)(*args)


def in_zone(lemon):
    """El limón (mm, marco del brazo) ya está donde se cosecha sin mover la base: REACH_MM y MIN_BEARING_DEG."""
    return (REACH_MM[0] <= math.hypot(lemon[0], lemon[1]) <= REACH_MM[1]
            and math.degrees(math.atan2(lemon[1], -lemon[0])) >= MIN_BEARING_DEG)


def raised(lemon):
    """Punto de agarre GRASP_RAISE_MM (reales) más arriba."""
    x, y, z = lemon
    return x, y, z + GRASP_RAISE_MM / 1.43


def home_steps(origin, odom):
    """Pasos para volver al cero desde la odometría actual: mirar en la dirección en que se vino, retroceder recto
    hasta el cero y recuperar el rumbo del cero (desanda un acercamiento girar - avanzar - girar)."""
    start = origin['odom_origin']
    dx, dy = odom['x_m'] - start['x_m'], odom['y_m'] - start['y_m']
    def wrap_deg(angle):
        return math.degrees(math.atan2(math.sin(angle), math.cos(angle)))
    steps = []
    if math.hypot(dx, dy) > .03:
        travel = math.atan2(dy, dx)
        steps += [('giro', wrap_deg(travel - odom['yaw_rad'])), ('recto', -math.hypot(dx, dy) * 1000),
                  ('giro', wrap_deg(start['yaw_rad'] - travel))]
    else:
        steps.append(('giro', wrap_deg(start['yaw_rad'] - odom['yaw_rad'])))
    return [(kind, value) for kind, value in steps if kind == 'recto' or abs(value) >= 1.5]


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
    """Cero del Móvil: el limón más cercano (mm, marco del brazo) y la odometría de ese instante. lemon None (21/11):
    solo la pose (kind 'pose'); la recolección busca el limón girando."""
    pose = {key: odom[key] for key in ('x_m', 'y_m', 'yaw_rad')}
    if lemon is None:
        return {'kind': 'pose', 'lemon_in_arm': None, 'lemons_seen': 0, 'distance_m': 0., 'odom_origin': pose}
    x, y, z = (float(v) for v in lemon)
    return {'kind': 'lemon', 'lemon_in_arm': {'x_mm': x, 'y_mm': y, 'z_mm': z}, 'lemons_seen': int(seen),
            'distance_m': math.hypot(x, y) / 1000, 'odom_origin': pose}


def nearest_rough(frames, grasp, tf):
    """(limón más cercano a J1 o None, cuántos se ven) con el criterio flojo del cero (ORIGIN_MIN_VIEWS, ORIGIN_SPREAD_MM)."""
    groups = group_lemons(frames, grasp.AGRUPAR_MM, ORIGIN_MIN_VIEWS)
    lemons = [raised(grasp.limon_de_cara(tf, face, n, spread)) for face, n, spread in groups if spread <= ORIGIN_SPREAD_MM]
    if not lemons:
        return None, 0
    # 21/11: primero los que están a la altura que agarra el brazo (un limón a 63 cm del piso, el más cercano, no tenía plan)
    reachable = [lemon for lemon in lemons if HEIGHT_CM[0] <= (256 + 1.43 * lemon[2]) / 10 <= HEIGHT_CM[1]]
    return min(reachable or lemons, key=lambda lemon: math.hypot(lemon[0], lemon[1])), len(lemons)


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
