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
import statistics
import sys
import types
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException

from physical_control import OpenManual
from vision_3d import with_displacement

MAX_LEMONS = 5
PICK_TRIES = 2          # 25/11: agarres por limón (un corte del brazo o el limón todavía en el árbol)
MEASURE_SECONDS = 8.     # 21/11: 5 -> 8 s (con el v4 y la disparidad a ~1-2 Hz llegan menos posiciones)
MV_TIMEOUT = 90.         # TIMEOUT_MV de recolectar.py
MV_RETRIES = 2           # punta.ejecutar: cortes por atraso con carga
# 25/11: J1 se trabó dos veces ("sin cuentas", batería a 10,9 V) yendo frente al limón y cortó la misión: también se
# repite desde donde quedó (la tercera vez llegaba)
RETRY_ON = ('no quedan firmes', 'no sigue la trayectoria', 'se mueve al revés', 'sin cuentas')
# 21/11: plegando para la canasta J3 quedó en 78,4 (pedido 80; cerca del punto muerto del cuatro barras está dura) y el
# mv siguiente cortó por "sin cuentas" porque J3 no subía esos 1,6°. Si una articulación ya está a menos de esto de su
# destino, se reintenta una vez dejándola donde está (con el encoder suelto de verdad la diferencia sería mayor)
STUCK_NEAR_DEG = 2.
# 21/11 (2.ª vez): J3 llegó a 79,96 y, al girar J1 hacia la canasta, el firmware igual la cortó por "sin cuentas" (con
# destino 80 intentaba corregir 0,04° en la zona dura). Con J1 pasada J1_MAX_NORMAL el brazo tiene que estar plegado
# (config.h SOLTAR_*): si J2 y J3 ya están dentro de esa zona, se quedan donde están y solo gira J1
J1_MAX_NORMAL, FOLDED_Q2, FOLDED_Q3_MIN = 118., (42.3, 50.7), 78.3
# 25/11, en el robot: después de soltar J2 quedó en 53,9° (fuera de la zona plegada); con J1 afuera de la canasta el
# brazo quedó 17° fuera de la franja y el firmware rechazaba todo mv ("volver adentro con j"). J3 a UNFOLD_J3 primero:
# adentro de la franja para J2 entre ~51° y ~75° (con J2 en 53,9°: J3 de 29,8° a 61,9°).
UNFOLD_J3 = 55.
# 25/11: desde la canasta (J1 130°) J1 no despega con "mv": corta "sin cuentas" a los 150 ms (firmware 20, CFG_J1) aun
# con 45 % de despegue (9 cortes seguidos); con el joystick (sin ese corte) sale bien. Para salir de la canasta, J1 va
# con "jv" (J1_JOG_AXIS, ~11 °/s) hasta su destino y el "mv" termina J2/J3; si no avanza en J1_JOG_STALL_S, sigue el mv
J1_JOG_AXIS, J1_JOG_STALL_S, J1_JOG_MAX_S = .9, 2., 8.
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
# modelo de punta, 1 mm de z son ~1,43 mm reales). 23/11: ajustado en el robot (ver GRASP_RAISE_MM)
GRASP_RAISE_MM = 32.5   # 23/11, usuario: 20 -> 7,5 -> -2,5 (cerraba alto) -> 12,5 (con -2,5, 1,5 cm bajo) -> 32,5 (+2 cm)
RETURN_SECONDS = 90.
# Rodear el árbol (25/11, pedido del usuario): 26-sim-alcance-arbolito da 4 paradas cada 90° alrededor del tronco para
# el 100 % del arbolito (~31 % desde una). Antihorario visto de arriba: el árbol siempre a la izquierda (lado del
# brazo). El tronco sale del primer escaneo; al terminar vuelve a donde hizo ese escaneo.
TREE_STOPS = 4   # máximo; la app elige 1-4 (25/11, usuario: poco espacio) y siempre vuelve al inicio
TRUNK_STOP_MM = (-700., 150.)   # parada de 26-sim: tronco 70 cm a la izquierda de J1 y 15 adelante (tolera ±5 cm)
CANOPY_MM = 120.                # limones a 10-14 cm del tronco (arbolito medido el 13/11)
# Obstáculos en Rodear árbol (25/11, pedido del usuario; el Recolector y la Recolección no cambian). Avanzando, con
# algo a menos de OBSTACLE_M al frente el Móvil espera quieto (el firmware frena a 0,20 m y si se insiste la sesión
# desarma la base); despejado en OBSTACLE_WAIT_S era alguien que pasaba y sigue. Si no, es un objeto: se guarda en el
# marco odom y ese salto alrededor del árbol se hace por un círculo DETOUR_RIGHT_MM más afuera (a la derecha: lejos del
# árbol); ningún camino pasa con el centro de giro a menos de OBSTACLE_CLEAR_MM de un objeto guardado. Sin camino: se
# saltea la parada.
OBSTACLE_M = .35
OBSTACLE_WAIT_S = 5.
SENSOR_AHEAD_MM = 360.      # MEDIR: HC-SR04 del frente delante del centro de giro (tapa en T de 40 cm)
OBSTACLE_RADIUS_MM = 150.   # supuesto: el sensor ve la cara de adelante, no el ancho
DETOUR_RIGHT_MM = (500., 800.)
HOP_DEG = 45.               # saltos alrededor del árbol (la recta de un salto queda cerca del círculo)
OBSTACLE_CLEAR_MM = 450.    # ~20 cm de medio ancho del Móvil + el radio supuesto + 10 cm
# Distancia a la maceta en cada parada (25/11, usuario): TFmini-S al costado izquierdo (/range/lidar_izq). Medido por el
# usuario: maceta redonda de 29,5-30 cm; lidar 19,1 cm adelante de J1 y 13 cm a la izquierda: lee D - 27,3 cm (D: J1 ->
# eje del árbol; la parada de 26-sim, D 70, da 42,7). 26-sim con 4 paradas: 41-44 cm -> 100 %, 40 -> 98 %, 38 -> 94 %.
# Fuera de LIDAR_BAND_M se corre de costado hasta el centro; fuera de LIDAR_TRUST_M no pega en la maceta.
LIDAR_BAND_M = (.40, .44)
LIDAR_TRUST_M = (.25, .60)
TRUNK_CLEAR_MM = 550.       # centro de giro al tronco (en la parada, 79,5 cm): ~20 cm de medio ancho + copa + margen
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
NO_LEMON_S = 4.        # con profundidad y ningún limón ubicado durante esto: no hay limones a la vista
VISION_READY_S = 40.   # espera de un par estéreo nuevo (la visión recién prendida tarda ~15 s)   # brazo al reposo y regreso al cero, aunque se haya agotado el tiempo de la recolección
HEIGHT_CM = (33, 64)   # alcance en altura (21/11: 33 cm medido con cosechar; ~64 cm con plan de punta.py sin los +2 cm): solo para explicar un acercamiento sin plan


class ArmRejected(RuntimeError):
    """El firmware del brazo cortó o rechazó un movimiento (texto de /brazo/respuesta)."""


class Blocked(RuntimeError):
    """Rodear árbol: el frente siguió bloqueado OBSTACLE_WAIT_S. point: el objeto (x, y m, marco odom)."""

    def __init__(self, message, point):
        super().__init__(message)
        self.point = point


class StopUnreachable(RuntimeError):
    """Rodear árbol: no hay camino a la parada (objetos o tronco): se saltea."""


class CollectionMission:
    def __init__(self, control, stereo, data_dir, tools):
        self.control, self.stereo = control, stereo
        self.data_dir, self.tools = Path(data_dir), Path(tools)
        self.task = self.owner = self.operator = None
        self.zone = None
        self.deadline = 0.
        self.run_until = 0.
        self.avoid, self.obstacles = False, []   # Rodear árbol: esperar y esquivar objetos (marco odom, m)
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

    def start_scan(self, operator, lemons=1, seconds=SCAN_SECONDS, around=False, stops=TREE_STOPS):
        """Modo Recolector: cosechar TODOS los limones del escaneo (lemons se ignora, 23/11); si hace falta, reubicando el
        Móvil (no hace falta cero)."""
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
        self.run_until = monotonic() + 180.   # hasta el escaneo; después, según cuántos limones vio (23/11)
        self.stop_requested = False
        self.zone = None
        self.events = []
        self.update('BUSCANDO', f'Modo Recolector: escaneo de {seconds:.0f} s con el Móvil quieto.')
        self.task = asyncio.create_task(self.run_scan(self.owner, lemons, seconds, around, stops))
        return self.snapshot()

    async def scan_frames(self, owner, seconds):
        """Las imágenes de /limon/todos durante `seconds` s contados desde la primera nueva (el primer par estéreo
        procesado después de empezar; hasta VISION_READY_S de espera: la visión puede estar arrancando). None si llega
        profundidad pero ningún limón ubicado en NO_LEMON_S: el localizador solo publica /limon/todos con alguno."""
        self.demand_vision()
        first, waited, searching = None, monotonic() + VISION_READY_S, None
        start_stamp = self.stereo.target_frame()[0]
        while first is None:
            if monotonic() >= waited:
                raise RuntimeError('La visión estéreo no entrega pares nuevos: revisá las cámaras')
            self.cycle(owner)
            stamp = self.stereo.target_frame()[0]
            if stamp is not None and (start_stamp is None or stamp > start_stamp):
                first = stamp
            elif self.stereo.snapshot()['status'] == 'searching':
                # 25/11, en el robot: con el limón fuera de la zona con profundidad (o ya arrancado) no llegaba nada y
                # a los 40 s cortaba toda la misión como si fueran las cámaras
                searching = searching or monotonic()
                if monotonic() - searching >= NO_LEMON_S:
                    return None
            else:
                searching = None
            await asyncio.sleep(.05)
        return await self.measure_frames(owner, seconds)

    async def run_scan(self, owner, count, seconds, around=False, stops=TREE_STOPS):
        """Modo Recolector: detener la base -> escanear -> guardar las posiciones en el marco de la odometría ->
        de a uno (primero los de la zona buena): reubicarse si hace falta, medir (corrige las posiciones guardadas de
        los que ve) y cosechar (harvest_stop) -> brazo al reposo. Sin verificar con la visión después (pedido del
        usuario, 21/11). La visión queda prendida (23/11). around (25/11): `stops` paradas (1-4) alrededor del árbol, cada
        una con su escaneo, y al final de vuelta a donde hizo el primero."""
        self.stage = 'preparación'
        recorder, paused, results = None, False, []
        try:
            navigation, grasp, tf = await asyncio.to_thread(self.planners)
            recorder = await self.start_recording()
            await self.control.open(owner, OpenManual(mode='combined', operator_present=True), autonomous=True)
            first = source_value(self.control.snapshot(), 'odom')
            if first is None:
                raise RuntimeError('Falta odometría para recordar dónde están los limones')
            first = dict(first)   # la pose del primer escaneo: una copia (se vuelve ahí al final)
            trunk_world, trunk_start, done, total, notes = None, None, 0, 0, []
            self.avoid, self.obstacles = around, []
            stops = max(1, min(TREE_STOPS, int(stops)))
            for stop in range(stops if around else 1):
                name = f'Parada {stop + 1} de {stops}: ' if around else ''
                if stop:
                    self.stage = f'paso a la parada {stop + 1}'
                    try:
                        await self.go_to_stop(owner, navigation, trunk_world, first['yaw_rad'] + stop * math.pi / 2,
                                              TRUNK_STOP_MM, f'Yendo a la parada {stop + 1} de {stops}')
                    except StopUnreachable as error:   # pedido del usuario: la tarea sigue con la siguiente
                        notes.append(f'parada {stop + 1} salteada: {error}')
                        continue
                if around:
                    self.stage = 'distancia a la maceta'
                    note = await self.lidar_trim(owner, name)
                    if note:
                        notes.append(note)
                    if not stop:   # el primer escaneo se hace (y se vuelve) desde acá
                        first = dict(source_value(self.control.snapshot(), 'odom') or first)
                self.stage = 'escaneo'
                if around:
                    self.update('BUSCANDO', f'{name}escaneo de {seconds:.0f} s con el Móvil quieto.')
                frames = await self.scan_frames(owner, seconds) or []
                groups = group_lemons(frames, grasp.AGRUPAR_MM, ORIGIN_MIN_VIEWS)
                targets = sorted((raised(grasp.limon_de_cara(tf, face, n, spread)) for face, n, spread in groups
                                  if spread <= grasp.DISPERSION_MAX), key=lambda l: math.hypot(l[0], l[1]))
                if around and trunk_world is None:   # pedido del usuario: el tronco, del primer escaneo
                    trunk_start = estimate_trunk(targets)
                    if trunk_start is None:
                        trunk_start = TRUNK_STOP_MM
                        notes.append('tronco supuesto en la parada (70 cm a la izquierda de J1)')
                    trunk_world = arm_to_world((*trunk_start, 0.), first)[:2]
                    self.update('BUSCANDO', f'Tronco a {trunk_start[0] / -10:.0f} cm a la izquierda de J1 y '
                                f'{trunk_start[1] / 10:.0f} cm adelante.')
                if not targets:
                    if not around:
                        self.update('FINALIZADO', f'Escaneo de {seconds:.0f} s sin limones estables: no se cosecha '
                                    'en esta parada.')
                        return
                    notes.append(f'parada {stop + 1}: sin limones')   # pedido del usuario: pasa a la siguiente
                    continue
                before = len(results)
                done += await self.harvest_stop(owner, navigation, grasp, tf, targets, results, name)
                total += len(targets)
                if around:
                    results[before:] = [(l, f'P{stop + 1} {r}') for l, r in results[before:]]
            if around:   # pedido del usuario: termina donde hizo el primer escaneo
                self.stage = 'regreso al lugar del primer escaneo'
                # con las 4 paradas completa la vuelta; con menos, vuelve por donde vino (no hay más espacio). Si los
                # objetos guardados cierran todo (un contacto de frente se guarda pegado al frente y puede quedar mal
                # ubicado), se olvidan y se intenta otra vez: uno real se vuelve a detectar al acercarse
                for attempt in range(2):
                    try:
                        await self.go_to_stop(owner, navigation, trunk_world, first['yaw_rad'], trunk_start,
                                              'Volviendo al lugar del primer escaneo', ccw=stops == TREE_STOPS)
                        break
                    except StopUnreachable as error:
                        if attempt:
                            notes.append(f'no volvió al lugar del primer escaneo: {error}')
                        self.obstacles = []
            self.stage = 'regreso del brazo al reposo'
            await self.arm_to_rest(owner, grasp)
            # Pedido del usuario (21/11): sin volver a prender la visión para verificar; se informa lo ejecutado
            detail = '; '.join([f'{math.hypot(l[0], l[1]) / 10:.0f} cm: {r}' for l, r in results] + notes)
            where = f' en {stops} parada(s) alrededor del árbol' if around else ' del escaneo'
            self.update('FINALIZADO', f'Modo Recolector: {done} de {total} limón(es){where} en la canasta. {detail}')
        except asyncio.CancelledError:
            self.update('INACTIVO', 'Modo Recolector detenido por el operador.')
        except (RuntimeError, HTTPException, ValueError, OSError, ImportError) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            self.update('RECUPERACION', f'El modo Recolector se detuvo durante {self.stage}. {detail}')
        except Exception:
            logging.exception('Falló el modo Recolector')
            self.update('RECUPERACION', 'Falló el modo Recolector. Consultá el registro de la Raspberry Pi.')
        finally:
            self.avoid = False
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

    async def harvest_stop(self, owner, navigation, grasp, tf, targets, results, name=''):
        """Modo Recolector en una parada: cosecha `targets` (mm, marco del brazo, desde la pose de ahora) de a
        uno, reubicando el Móvil si hace falta. Devuelve cuántos dejó en la canasta."""
        # 23/11, pedido del usuario: cosechar TODOS los del escaneo. Se guardan en el marco de la odometría (no
        # cambia al mover la base) y antes de cada uno se pasan al marco del brazo desde la pose de ese momento
        start = source_value(self.control.snapshot(), 'odom')
        if start is None:
            raise RuntimeError('Falta odometría para recordar dónde están los limones')
        remaining = [arm_to_world(lemon, start) for lemon in targets]
        tries = [0] * len(remaining)
        # 25/11, usuario: "hecho" no aseguraba que el limón quedó en la pinza. Después de cada agarre se mide otra vez
        # ese limón (el brazo en la canasta, fuera de la vista): si sigue en el árbol, otro intento (PICK_TRIES en total)
        verify = None
        self.run_until = monotonic() + 120. + 160. * len(targets)
        self.update('BUSCANDO', f'{name}lista guardada: {len(targets)} limón(es); se cosechan todos, de a uno.')
        done = 0
        while remaining:
            odom = source_value(self.control.snapshot(), 'odom')
            if odom is None:
                raise RuntimeError('Falta odometría reciente')
            here = [world_to_arm(point, odom) for point in remaining]
            # primero los que ya están en la zona buena (sin mover la base); si no, el más cercano
            ready = [i for i, lemon in enumerate(here) if in_zone(lemon)] or range(len(here))
            index = verify if verify is not None else min(ready, key=lambda i: math.hypot(here[i][0], here[i][1]))
            number = len(targets) - len(remaining) + 1
            if verify is None and not in_zone(here[index]):
                self.stage = 'planificación de la reubicación'
                # 25/11: desde la canasta el Móvil anda con el brazo ahí (no al reposo: 16 s) y despliega recién
                # al agarrar (pick_here). En DESPLEGAR tapaba la cámara izquierda al medir: 40 s sin pares, cortó
                folded = arm_angles(self.control.snapshot().get('arm_state'))[0] > grasp.k.Q1_LIM[1]
                found = await self.reposition(owner, navigation, grasp, here[index], True,
                                              grasp.DESPLEGAR if folded else grasp.REPOSO)
                if found is not None:
                    steps = found[0]
                    self.stage = 'reubicación del Móvil'
                    if not folded:
                        await self.arm_to_rest(owner, grasp)
                    self.update('NAVEGANDO', f'{name}reubicando el Móvil para el limón {number} de {len(targets)}: '
                                + navigation.texto(steps))
                    try:
                        for kind, value in steps:
                            await self.drive_step(owner, kind, value)
                    except Blocked as blocked:   # solo en Rodear árbol (avoid): ese limón se saltea
                        self.obstacles.append(blocked.point)
                        results.append((here[index], f'salteado: {blocked} al reubicarse'))
                        remaining.pop(index)
                        retried.pop(index)
                        continue
                    await self.settle(owner, 1.)
            self.stage = 'medición'
            self.zone = source_value(self.control.snapshot(), 'odom')
            if self.zone is None:
                raise RuntimeError('Falta odometría reciente al llegar')
            self.update('BUSCANDO', f'{name}' + (f'¿quedó el limón {number} en el árbol? Midiendo con estéreo.'
                        if verify is not None else f'midiendo el limón {number} de {len(targets)} con estéreo.'))
            visible = await self.scan_frames(owner, 0.) is not None   # pares nuevos, desde acá
            expected = world_to_arm(remaining[index], self.zone)

            def steady(frames):
                """25/11: la medición corta apenas el limón buscado tiene lecturas firmes (~2-3 s); si se hamaca
                (lo tocó la herramienta) sigue hasta MEASURE_SECONDS.
                ponytail: la dispersión es de toda la ventana; si se hamacó al principio puede no bajar."""
                return any(spread <= grasp.DISPERSION_MAX and math.dist(
                    raised(grasp.limon_de_cara(tf, face, n, spread))[:2], expected[:2]) <= EXPECTED_RADIUS_MM
                    for face, n, spread in group_lemons(frames, grasp.AGRUPAR_MM, grasp.MIN_POSICIONES))

            measured = await self.measure_lemons(owner, grasp, tf, enough=steady) if visible else []
            here = refresh_positions(remaining, measured, self.zone)
            lemon = here[index]
            if verify is not None and math.dist(lemon, picked_at) >= grasp.VERIFICAR_MM:
                remaining[index] = remaining[index][:3] + (False,)   # el que se ve es otro (como punta.cosechar)
            if not remaining[index][3]:   # 25/11, usuario: si no se ve (se movió o cayó), no se agarra
                if verify is not None:   # ya no está en el árbol: lo arrancó
                    results[-1] = (results[-1][0], results[-1][1] + (' (verificado'
                                   + (', al 2.º intento)' if tries[index] > 1 else ')')))
                else:
                    results.append((lemon, 'salteado: no se vio al medir (se movió, se cayó o quedó tapado)'))
                remaining.pop(index)
                tries.pop(index)
                self.zone, verify = None, None
                continue
            if verify is not None:   # sigue en el árbol: no quedó en la pinza
                verify = None
                done -= 1
                if tries[index] >= PICK_TRIES:
                    results[-1] = (results[-1][0], f'falló: sigue en el árbol después de {tries[index]} intentos')
                    remaining.pop(index)
                    tries.pop(index)
                    self.zone = None
                    continue
                results.pop()
                self.update('BUSCANDO', f'{name}el limón {number} sigue en el árbol: otro intento.')
                self.run_until += 150.
            self.stage = 'cosecha'
            tries[index] += 1
            picked_at = lemon[:3]
            picked = await self.pick_here(owner, grasp, lemon[:3], results)
            done += picked
            self.zone = None
            if picked:
                verify = index
                continue
            # 25/11: J1 no despegó de la canasta (6 cortes "sin cuentas", batería a 10,8 V) y se perdió un limón
            # a 59 cm; el brazo se recuperó solo. Un corte del brazo es pasajero: ese limón, una vez más
            if not picked and results[-1][1].startswith('falló') and tries[index] < PICK_TRIES:
                results[-1] = (results[-1][0], results[-1][1] + ' (se reintentó)')
                self.run_until += 150.
                continue
            remaining.pop(index)
            tries.pop(index)
        return done

    async def go_to_stop(self, owner, navigation, trunk_world, heading, stop, label, ccw=True):
        """Rodear el árbol (25/11): ir alrededor del tronco por el círculo de la parada hasta quedar con el tronco en
        `stop` (mm, marco de J1) y rumbo `heading` (rad, odometría), en saltos de HOP_DEG (girar -> recto -> girar con
        ir_a_parada.planear; giros con el giróscopo). ccw: antihorario (el árbol a la izquierda); False: volver por donde
        vino (horario; los saltos intermedios miran hacia donde va, con el árbol a la derecha). Un salto que pasa cerca
        de un objeto guardado o del tronco, o que queda bloqueado, se hace por un círculo DETOUR_RIGHT_MM más afuera
        (con un paso al costado hacia afuera si hace falta) si el ultrasonido de ese lado lo deja; el salto siguiente
        vuelve al círculo. Nunca en marcha atrás (hop_plan). StopUnreachable si ninguno anda."""
        odom = source_value(self.control.snapshot(), 'odom')
        if odom is None:
            raise RuntimeError('Falta odometría para ir a la parada')
        start = odom['yaw_rad']
        total = math.atan2(math.sin(heading - start), math.cos(heading - start))
        if ccw and total < -1e-6:
            total += 2 * math.pi
        elif not ccw and total > 1e-6:
            total -= 2 * math.pi
        hops = max(1, math.ceil(abs(math.degrees(total)) / HOP_DEG - 1e-6))
        hop, exact = 1, False
        while hop <= hops:
            back = not ccw and hop < hops   # el salto termina mirando en sentido horario: el árbol a la derecha
            # sin desvío; por un círculo más afuera; y lo mismo con un paso al costado antes (frenado frente a un
            # objeto, ir en diagonal al círculo de afuera pasa muy cerca de él)
            options = [(0., False)] + ([] if exact else [(o, s) for o in DETOUR_RIGHT_MM for s in (False, True)])
            for offset, aside in options:
                self.run_until = max(self.run_until, monotonic() + 90.)
                snapshot = self.control.snapshot()
                odom = source_value(snapshot, 'odom')
                if odom is None:
                    raise RuntimeError('Falta odometría para ir a la parada')
                # hacia afuera del árbol desde donde está ahora: a la derecha si el tronco le queda a la izquierda
                outward = -1. if world_to_arm((*trunk_world, 0.), odom)[0] < ROTATION_CENTER_MM[0] else 1.
                side = front_distance(snapshot, 'range_right' if outward < 0 else 'range_left')
                if offset and side is not None and side * 1000 < offset:
                    continue   # hacia afuera hay algo más cerca: ese círculo no
                legs, pose = [], odom
                if aside:
                    legs.append((odom, [('giro', 90. * outward), ('recto', offset)]))
                    yaw = odom['yaw_rad']
                    pose = {'x_m': odom['x_m'] - outward * offset / 1000 * math.sin(yaw),
                            'y_m': odom['y_m'] + outward * offset / 1000 * math.cos(yaw),
                            'yaw_rad': yaw + outward * math.pi / 2}
                spot = (stop[0] - offset, stop[1])
                if back:   # la misma parada con el Móvil girado 180° sobre su centro de giro
                    spot = (2 * ROTATION_CENTER_MM[0] - spot[0], 2 * ROTATION_CENTER_MM[1] - spot[1])
                legs += self.hop_plan(navigation, trunk_world, pose,
                                      start + total * hop / hops + (math.pi if back else 0.), spot)
                if any(center_clearance(steps, world_to_arm((*trunk_world, 0.), at)[:2]) < TRUNK_CLEAR_MM or any(
                           center_clearance(steps, world_to_arm((*point, 0.), at)[:2]) < OBSTACLE_CLEAR_MM
                           for point in self.obstacles) for at, steps in legs):
                    continue
                steps = [step for _, leg in legs for step in leg]
                self.update('NAVEGANDO', f'{label}' + (f' ({offset / 10:.0f} cm más afuera por un objeto)'
                                                       if offset else '') + f': {navigation.texto(steps)}')
                try:
                    for kind, value in steps:
                        await self.drive_step(owner, kind, value)
                    break
                except Blocked as blocked:
                    self.obstacles.append(blocked.point)
            else:
                if exact:
                    return   # se queda en la parada de más afuera (la reubicación de cada limón lo compensa)
                raise StopUnreachable('sin camino libre')
            # el último salto quedó en el círculo de afuera: uno más hasta la parada exacta (25/11, usuario: siempre
            # vuelve al inicio)
            if hop == hops and offset and not exact:
                exact = True
                continue
            hop += 1

    async def lidar_trim(self, owner, name):
        """Rodear árbol (25/11): deja la maceta a LIDAR_BAND_M del TFmini-S (al medio) con un paso al costado: girar
        90° -> recto -> volver a girar (nunca atrás; el árbol a la izquierda). Sin una lectura confiable no se mueve.
        Devuelve una nota para el informe o None si ya estaba bien."""
        readings = []
        for _ in range(5):
            meters = front_distance(self.control.snapshot(), 'range_lidar_left')
            if meters is not None and math.isfinite(meters):
                readings.append(meters)
            await self.settle(owner, .1)   # quieto, pero mandando: sin consignas el control corta la recolección
        if len(readings) < 3:
            return f'{name}sin lectura del lidar, sin corregir la distancia'
        meters = statistics.median(readings)
        if not LIDAR_TRUST_M[0] <= meters <= LIDAR_TRUST_M[1]:
            return f'{name}lidar a {meters * 100:.0f} cm (no parece la maceta), sin corregir'
        if LIDAR_BAND_M[0] <= meters <= LIDAR_BAND_M[1]:
            return None
        shift = (meters - sum(LIDAR_BAND_M) / 2) * 1000   # mm; > 0: lejos, hacia el árbol (a la izquierda)
        turn = math.copysign(90., shift)
        self.update('NAVEGANDO', f'{name}maceta a {meters * 100:.0f} cm: me corro {abs(shift) / 10:.0f} cm '
                    + ('hacia el árbol.' if shift > 0 else 'hacia afuera.'))
        await self.drive_step(owner, 'giro', turn)
        try:
            await self.drive_step(owner, 'recto', abs(shift))
        except Blocked as blocked:
            self.obstacles.append(blocked.point)
            await self.drive_step(owner, 'giro', -turn)
            return f'{name}lidar a {meters * 100:.0f} cm, no pudo corregir: {blocked}'
        await self.drive_step(owner, 'giro', -turn)
        return f'{name}lidar a {meters * 100:.0f} cm, corrido {abs(shift) / 10:.0f} cm'

    @staticmethod
    def hop_plan(navigation, trunk_world, pose, heading, stop):
        """[(pose, pasos)] para quedar con el tronco en `stop` (mm, marco de J1) y rumbo `heading` (rad, odom). Si
        ir_a_parada.planear pide marcha atrás (atrás no hay sensores), primero gira 180° en el lugar."""
        def plan(at):
            turn = heading - at['yaw_rad']
            return navigation.planear(world_to_arm((*trunk_world, 0.), at)[:2],
                                      math.degrees(math.atan2(math.sin(turn), math.cos(turn))), stop, orientar=True)
        steps = plan(pose)
        if not any(kind == 'recto' and value < 0 for kind, value in steps):
            return [(pose, steps)]
        turned = dict(pose, yaw_rad=pose['yaw_rad'] + math.pi)
        return [(pose, [('giro', 180.)]), (turned, plan(turned))]

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
            await self.recover(owner, grasp)
            return 0
        results.append((lemon, 'hecho'))
        return 1

    async def reposition(self, owner, navigation, original, target, to_basket, start=None):
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
            plan, _ = await self.grasp_plan(owner, original, start or original.REPOSO, expected, to_basket)
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
            # J1 sale de la canasta con el joystick (move); un mv a (100, J2, J3) plegado quedaba fuera de la franja
            path = [(100., 46.7, 50.), tuple(original.REPOSO)]
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
        limit, waiting = monotonic() + 24., None
        while monotonic() < limit:
            snapshot = self.control.snapshot()
            sample = source_value(snapshot, 'odom' if kind == 'recto' else 'imu')
            if not sample:
                raise RuntimeError('Se perdió la realimentación del Móvil')
            if self.avoid and kind == 'recto' and value > 0 and front_blocked(snapshot):
                front = front_distance(snapshot)
                where = f' a {front * 100:.0f} cm' if front not in (None, math.inf) else ''
                self.cycle(owner)   # quieto (avanzar contra el bloqueo desarma la base)
                if waiting is None:
                    waiting = monotonic()
                    self.update('NAVEGANDO', f'Obstáculo adelante{where}: esperando que se despeje.')
                elif monotonic() - waiting >= OBSTACLE_WAIT_S:
                    raise Blocked(f'Objeto adelante{where}', obstacle_point(sample, front))
                limit += .05
                await asyncio.sleep(.05)
                continue
            waiting = None
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

    async def measure_frames(self, owner, seconds=MEASURE_SECONDS, enough=None):
        """Las imágenes de /limon/todos de `seconds` s: [[(x, y, z) mm, ...], ...], marco `camera`. enough(frames):
        corta antes, apenas da True con las imágenes juntadas hasta ahí."""
        return await self.collect_frames(seconds, lambda: self.cycle(owner), enough)

    async def collect_frames(self, seconds, tick, enough=None):
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
                if enough is not None and enough(frames):
                    break
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

    async def measure_lemons(self, owner, original, tf, near=None, enough=None):
        """Como punta.medir_limones: agrupa los limones de todas las imágenes y da sus puntos de agarre (mm, marco del
        brazo) con las correcciones de punta.limon_de_cara (z de la visión, adelante, izquierda, arriba y ajuste fino).
        near: dónde tiene que estar el limón (mm, marco del brazo). Entonces alcanza con punta.MIN_POSICIONES
        posiciones aunque haya lecturas repartidas, y van primero los que están a menos de EXPECTED_RADIUS_MM de ahí;
        si no hay ninguno, todos (21/11, pedido del usuario: la profundidad del cero puede errar 10-25 cm; al llegar se
        cosecha lo que se mide ahí si el brazo tiene plan)."""
        frames = await (self.measure_frames(owner) if enough is None else self.measure_frames(owner, enough=enough))
        groups = group_lemons(frames, original.AGRUPAR_MM, original.MIN_POSICIONES,
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

    async def jog_j1_out(self, owner, target):
        """Sacar J1 de la canasta con el joystick ("jv", reenviado antes de los 300 ms del hombre muerto) hasta `target`
        (°); se corta si no avanza en J1_JOG_STALL_S. Siempre termina con "jv 0 0 0" (sostiene donde quedó)."""
        started = progress = monotonic()
        best = arm_angles(self.control.snapshot().get('arm_state'))[0]
        self.update('INTERVINIEND', 'Sacando J1 de la canasta')
        try:
            while monotonic() - started < J1_JOG_MAX_S and monotonic() - progress < J1_JOG_STALL_S:
                self.cycle(owner)
                q1 = arm_angles(self.control.snapshot().get('arm_state'))[0]
                if q1 <= target + 1.:
                    break
                if q1 < best - .3:
                    best, progress = q1, monotonic()
                self.control.arm.send(f'jv {-J1_JOG_AXIS:.2f} 0 0')
                await asyncio.sleep(.1)
        finally:
            self.control.arm.send('jv 0 0 0')
        await self.settle(owner, .6)

    async def unfold_j3(self, owner):
        """Plegado con J2 por encima de la zona y J1 afuera de la canasta (fuera de la franja): J3 a UNFOLD_J3 con "j",
        lo único que el firmware deja hacer ahí (volver adentro)."""
        self.update('INTERVINIENDO', 'Bajando J3 a la franja')
        self.control.arm.send(f'j 3 {UNFOLD_J3:.1f}')
        until = monotonic() + 15.
        while monotonic() < until:
            self.cycle(owner)
            if abs(arm_angles(self.control.snapshot().get('arm_state'))[2] - UNFOLD_J3) <= 1.5:
                await self.settle(owner, .4)
                return
            await asyncio.sleep(.05)
        raise ArmRejected(f'J3 no bajó a {UNFOLD_J3:.0f}° (fuera de la franja): bajala con el joystick y hacé el homing')

    async def move(self, owner, q, passing=False):
        """Como punta.ejecutar con un punto: mv (o mvp de paso) y, si corta por atraso con carga, repetir desde donde
        quedó hasta MV_RETRIES veces. Los cortes de seguridad (franja, caja, plegado) no se repiten. Saliendo de la
        canasta, J1 primero con el joystick (jog_j1_out)."""
        now = arm_angles(self.control.snapshot().get('arm_state'))
        if now[0] > J1_MAX_NORMAL and q[0] < now[0] - 2.:
            await self.jog_j1_out(owner, q[0])
            now = arm_angles(self.control.snapshot().get('arm_state'))
        if now[0] <= J1_MAX_NORMAL and now[1] > FOLDED_Q2[1] and now[2] >= FOLDED_Q3_MIN:
            await self.unfold_j3(owner)
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

    async def recover(self, owner, original):
        """Modo Recolector (25/11, pedido del usuario: la demo no se corta por un limón): tras un agarre fallido, con
        algo en la pinza a la canasta y si no al reposo; si un intento corta, espera y prueba el otro. Solo si ninguno
        llega (el brazo necesita a alguien) sigue el error y se detiene."""
        state = self.control.snapshot().get('arm_state') or ''
        try:
            holding = float(state.split('pz=', 1)[1].split(';')[0]) >= 1000   # abierta 500, agarre 1200
        except (IndexError, ValueError):
            holding = True
        tries = ([self.recover_to_basket] if holding else []) + [self.arm_to_rest, self.arm_to_rest]
        error = None
        for attempt in tries:
            try:
                if await attempt(owner, original):
                    return
            except ArmRejected as rejected:
                error = rejected
            await self.settle(owner, 1.)
        raise error or ArmRejected('El brazo no encontró un camino seguro al reposo')

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

    async def harvest(self, owner, original, tf, count, to_basket, expected=None, verify=True):
        """Como punta.cosechar: mide todos los limones, agarra el más cercano con plan, lo deja en la canasta y vuelve a
        medir desde ahí (confirma que ya no está en el árbol; hasta punta.MAX_INTENTOS por limón). Al final, al reposo.
        Sin canasta: uno solo y queda en la pinza. expected: dónde tiene que estar el primer limón (al llegar a la
        parada); la primera medición solo acepta ese. verify False (modo Recolector, 23/11): no vuelve a medir para
        confirmar que el limón ya no está (~8 s). Devuelve cuántos dejó."""
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
            if not verify:   # pedido del usuario (21/11): el Recolector no verifica con la visión
                done += 1
                if done >= count:
                    break
                continue
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
    # 25/11: debajo del puente (que manda la velocidad a la S3 cada 50 ms; con la Pi saturada se atrasaba y la S3
    # cortaba por "sin comandos") y encima de la visión (nice 10, scripts/vision.sh)
    os.nice(5)
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


ROTATION_CENTER_MM = (80., -5.)   # = ir_a_parada.CENTRO_GIRO: centro del eje de las ruedas en el marco de J1


def arm_to_world(lemon, odom):
    """Limón (mm, marco del brazo: x derecha, y adelante) -> (x, y en m del marco odom, z mm del modelo, visto). La
    odometría es la del centro de giro, con x adelante e y a la izquierda (base_link)."""
    forward = (lemon[1] - ROTATION_CENTER_MM[1]) / 1000
    left = -(lemon[0] - ROTATION_CENTER_MM[0]) / 1000
    c, s = math.cos(odom['yaw_rad']), math.sin(odom['yaw_rad'])
    return (odom['x_m'] + c * forward - s * left, odom['y_m'] + s * forward + c * left, lemon[2], True)


def world_to_arm(point, odom):
    """La inversa de arm_to_world: dónde queda en el marco del brazo desde la pose `odom` (x, y, z mm)."""
    dx, dy = point[0] - odom['x_m'], point[1] - odom['y_m']
    c, s = math.cos(odom['yaw_rad']), math.sin(odom['yaw_rad'])
    forward, left = c * dx + s * dy, -s * dx + c * dy
    return (-left * 1000 + ROTATION_CENTER_MM[0], forward * 1000 + ROTATION_CENTER_MM[1], point[2])


def refresh_positions(remaining, measured, odom):
    """Corrige en el lugar las posiciones guardadas (marco odom) con lo medido desde `odom` (mm, marco del brazo): a
    cada una, el limón medido más cercano a menos de EXPECTED_RADIUS_MM de donde se esperaba (el 4.º campo dice si se
    vio esta vez). Devuelve las posiciones en el marco del brazo."""
    predicted = [world_to_arm(point, odom) for point in remaining]
    # 25/11: cada medición, a un solo limón guardado (antes dos cercanos tomaban la misma y el 2.º iba a un lugar vacío)
    match = {}
    for d, i, j in sorted((math.dist(m[:2], p[:2]), i, j) for i, p in enumerate(predicted) for j, m in enumerate(measured)):
        if d <= EXPECTED_RADIUS_MM and i not in match and j not in match.values():
            match[i] = j
    here = []
    for i, point in enumerate(remaining):
        if i in match:
            near = measured[match[i]]
            remaining[i] = arm_to_world(near, odom)
            here.append(tuple(near[:3]))
        else:
            remaining[i] = point[:3] + (False,)
            here.append(predicted[i])
    return here


def front_distance(snapshot, key='range_front'):
    """m al ultrasonido `key`; inf sin nada al alcance; None sin dato fresco."""
    value = source_value(snapshot, key) if snapshot.get('sources') else None
    if not isinstance(value, dict):
        return None
    return value['meters'] if value.get('kind') == 'distance' else math.inf if value.get('kind') == 'out_of_range' else None


def front_blocked(snapshot):
    """Rodear árbol: no se puede avanzar (algo a menos de OBSTACLE_M, sin dato del frente o el firmware no deja)."""
    front = front_distance(snapshot)
    return (front is None or front < OBSTACLE_M
            or any(field.startswith('no_avanza') for field in (snapshot.get('base_state') or '').split()))


def obstacle_point(odom, front):
    """Dónde está el objeto (x, y m, odom): adelante del centro de giro, a lo que mide el frente + el sensor + el
    radio supuesto."""
    # el ultrasonido solo cuenta si ve algo cerca; si frenó el bumper (no_avanza) con el ultrasonido viendo más lejos
    # (25/11, simulación: el árbol detrás a 79 cm), el objeto está pegado al frente
    near = front if front is not None and front < OBSTACLE_M else 0.
    ahead = near + (SENSOR_AHEAD_MM + OBSTACLE_RADIUS_MM) / 1000
    return (odom['x_m'] + ahead * math.cos(odom['yaw_rad']), odom['y_m'] + ahead * math.sin(odom['yaw_rad']))


def center_clearance(steps, point):
    """mm: lo más cerca que pasa el centro de giro de `point` (mm, marco de J1) siguiendo los pasos."""
    heading, cx, cy = 0., *ROTATION_CENTER_MM
    best = math.dist((cx, cy), point)
    for kind, value in steps:
        if kind == 'giro':
            heading += math.radians(value)
            continue
        for k in range(1, 41):
            best = min(best, math.dist((cx - value * k / 40 * math.sin(heading), cy + value * k / 40 * math.cos(heading)),
                                       point))
        cx, cy = cx - value * math.sin(heading), cy + value * math.cos(heading)
    return best


def estimate_trunk(lemons):
    """Rodear el árbol (25/11, pedido del usuario): el tronco (x, y mm, marco del brazo) desde los limones del primer
    escaneo: el centro de los que ve, CANOPY_MM más lejos en la dirección desde J1. None si no da creíble (a la
    izquierda de J1 y a 45-120 cm).
    ponytail: supone que ve la cara de la copa que mira al robot; con limones de los dos lados el centro sale corto."""
    if not lemons:
        return None
    cx, cy = (sum(lemon[k] for lemon in lemons) / len(lemons) for k in (0, 1))
    r = math.hypot(cx, cy)
    trunk = (cx + CANOPY_MM * cx / r, cy + CANOPY_MM * cy / r)
    return trunk if trunk[0] < 0 and 450. <= math.hypot(*trunk) <= 1200. else None


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
