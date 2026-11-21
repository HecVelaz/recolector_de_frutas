# API v1 — observación

## Cámaras

`GET /api/v1/vision/{camera}/frame` requiere el mismo token que la telemetría.
Los valores de `camera` son `left`, `right` y `detections`. La última vista muestra
la cámara izquierda anotada por el detector ROS. El puente devuelve `200` con
`image/jpeg` si hay un fotograma reciente, `204` si falta o caducó, y `404` para
un nombre inválido. Los fotogramas caducan después de 1,5 segundos.

La telemetría `stereo` indica si se recibe disparidad y publica los limones
recientes de `/limon/todos` en metros, en el marco óptico de la cámara
izquierda. `POST /api/v1/navigation/origin` mide el ArUco original de 15 cm
durante tres segundos con el Móvil quieto. Guarda el centro y rumbo del
Móvil respecto a la marca y usa la odometría de ese instante como cero de
desplazamiento. Medí de nuevo después de reiniciar el puente.

## Recolección del arbolito

Con el cero medido y el brazo en reposo, `POST /api/v1/mission/session`
con `operator_present: true` abre una recolección supervisada. Usa la
calibración y los planificadores de las carpetas originales
`~/scripts/27-aruco-arbol/tools` y `~/scripts/20-brazo-coordinado/tools`.
Se aproxima a una parada y cosecha como `punta.cosechar`: mide todos los limones de
`/limon/todos` durante 5 s, los agrupa y corrige con `punta.limon_de_cara` (z de la visión,
adelante, izquierda, arriba y ajuste fino), planea con `punta.planear_agarre_tol` el más
cercano, ejecuta el plan como `punta.correr_tarea` (comandos sueltos, servos, `mvp` en los
tramos de paso, velocidad de carga, hasta dos reintentos por atraso), lo deja en la canasta
y vuelve a medir para confirmarlo. Al final, al reposo. Cuerpo opcional: `lemons` (1–5,
por defecto 1) y `to_basket` (por defecto `true`; `false`: uno solo y queda en la pinza).
Si el brazo corta con un limón, intenta llevarlo a la canasta (`punta.recuperar_a_canasta`).
El brazo solo actúa con el Móvil detenido dentro de la zona local de la
parada, referida a la marca de la maceta.
El cliente mantiene `POST /api/v1/mission/heartbeat` y puede cancelar con
`DELETE /api/v1/mission/session`. La misión comparte el mando ROS con el
control manual y guarda los eventos y un rosbag en `data-dir/missions/`.

## Mando manual supervisado

El perfil `--physical-manual` usa ROS real y se inicia en un puerto distinto de
observación, en `127.0.0.1`, con descubrimiento ROS local. La tablet llega al
puente mediante el túnel SSH y ADB. La telemetría anuncia
`physical_manual: "supervised_manual"`. El perfil normal continúa en observación.

- `POST /api/v1/physical/session` abre una sesión `base`, `arm`, `combined` o `homing` con la
  confirmación del operador. El puente solicita la detención del Móvil si hace
  falta y la comprueba con odometría. Las sesiones que incluyen el mando del
  Móvil confirman el armado a velocidad cero. El homing conserva el Móvil detenido y se hace con el
  operador junto al corte físico. Mantener `motion: "home"` inicia y sostiene
  el ensayo. La API solo confirma el éxito con respuesta nueva del firmware y
  los tres ceros presentes en la telemetría del brazo. Después mueve el brazo
  al reposo `mv 3 17 4` y comprueba su llegada.
- Mientras el brazo tenga telemetría vigente y permanezca en un estado admisible,
  la pinza y la muñeca pueden manejarse con el homing pendiente. J1–J3 solo
  aceptan movimiento con referencia válida (`manual_arm_ready`).
- `POST /api/v1/physical/input` renueva la sesión y acepta uno de los mandos
  predefinidos. `speed_percent` de 0 a 100 ajusta el mando de la base hasta
  0,25 m/s en línea recta y 0,15 rad/s en giro. El PWM legado requiere una
  sesión de banco con ruedas elevadas. En `combined`, `motion` mueve la
  base, `arm_motion` una articulación y `servo` la pinza o la muñeca.
  Las consolas con joystick usan `drive: {forward, turn}` y
  `joints: {swivel, shoulder, elbow}`, con ejes de −1 a 1 y los mismos límites.
  Avance y giro se escalan juntos para mantener el límite cuando se combinan.
  El control del brazo admite el giro J1 y los ejes de hombro y codo del
  firmware. La telemetría anuncia esta capacidad con `manual_analog` y sus
  límites de velocidad y duty con `manual_drive_limits`.
  `gripper_open_percent` permite seleccionar la apertura de 0 a 100. 
  `wrist_degrees` acepta −90 a +90, con positivo horario y cero en el centro.
  Se acepta una consigna de servo por entrada y se respetan los pulsos de
  apertura, cierre y giro calibrados. El puente anuncia `manual_servo_positions`.
  Un cuerpo vacío detiene los mandos mantenidos. La pinza y la muñeca
  reciben posiciones predefinidas de una sola vez. Los servos conservan su
  consigna para mantener el agarre.
  En una sesión con `sequence`, cada entrada lleva un entero estrictamente
  creciente y el puente ignora entradas anteriores. Después de 220 ms sin
  entradas se detienen el Móvil y las articulaciones y la siguiente entrada de
  movimiento devuelve `paused: true` hasta recibir un mando neutro nuevo.
  La sesión continúa mientras recibe entradas válidas. Se cierra tras tres
  segundos sin ellas, ante un fallo de seguridad o con
  `DELETE /api/v1/physical/session`. El homing se cancela con `s` tras 220 ms
  sin entradas. El corte físico sigue siendo necesario si se pierde
  la comunicación con el controlador del brazo o se interrumpe el proceso de la Pi.

Las solicitudes usan el mismo token que la telemetría y un
`X-Arturito-Client` distinto por sesión. El perfil de recolección usa el
arbolito y la calibración local. La geocerca del mapa aún no gobierna la
recolección.

## Puerta de control (solo diagnóstico)

La telemetría incluye `control_gate` con `state`, `ready`, `max_age_ms` y `reasons`. En la versión
actual el estado es siempre `blocked`, `commands_enabled` sigue en `false` y no existen rutas de
movimiento. Este campo permite desarrollar y probar las condiciones sin ampliar la autoridad del
puente.

### Ensayo en seco de etapa 9

Con `ARTURITO_CONTROL_DRY_RUN=1` se habilitan rutas autenticadas de preparación, confirmación,
heartbeat, parada, liberación y comandos manuales tipados. Todas exigen `X-Arturito-Client`; una
sesión activa tiene un solo propietario. Los límites provisionales son ±0,15 m/s, ±0,5 rad/s, J1
±118° y J2/J3 ±90°. Los comandos manuales exigen hombre muerto.

Este modo no contiene un publicador ROS ni una capa actuadora. Toda respuesta declara
`dry_run=true`, `commands_enabled=false` y `robot_command_sent=false`. Por eso sirve para los pasos
1–7 sin potencia, pero no constituye control físico del robot.

Base: `http://<Pi>:8001`. JSON UTF-8. La clave se envía en la cabecera
`Authorization: Bearer <clave>` tanto en HTTP como en el handshake WebSocket.
No enviar claves por parámetros de URL. `/health` no requiere clave.

## Telemetría

`GET /api/v1/telemetry` y `WS /api/v1/telemetry` entregan el mismo objeto:

```json
{
  "schema_version": 1,
  "timestamp_ms": 1795101842439,
  "source": "estado",
  "simulated": false,
  "upstream_available": true,
  "base_state": null,
  "base_freshness_known": false,
  "gps": null,
  "battery_voltage": null,
  "alarms": null,
  "commands_enabled": false,
  "geofence_enforced": false
}
```

- `timestamp_ms`: instante del envío del puente, milisegundos Unix. **No** es el instante del último mensaje ROS.
- `source`: `simulation` o `estado`. `simulated` debe coincidir con ese origen.
- `upstream_available`: indica que el servicio de origen respondió; no confirma que la S3 esté conectada.
- `base_state`: texto `/base/estado`, o `null`. Se conserva sin deducir estados de misión ni garantías de seguridad.
- `base_freshness_known`: `false` para el servicio antiguo: este retiene el último texto sin timestamp.
- `gps`: `null`, o `{latitude, longitude, timestamp_ms, simulated}`. Coordenadas WGS84 en grados.
- `battery_voltage`: voltios o `null`. No se infiere porcentaje de una tensión.
- `alarms`: lista de textos o `null` si no hay fuente estructurada. `[]` significa ninguna informada.
- `commands_enabled`, `geofence_enforced`: siempre `false` en esta etapa.

WebSocket emite una instantánea cada segundo. La app invalida las lecturas si transcurren
5 segundos sin un mensaje válido, cancela el socket y reintenta a 1, 2, 4, 8 y hasta 15 segundos.
Una primera lectura válida reinicia la espera. Al quedar en segundo plano cierra la conexión;
al volver la reabre si seguía seleccionado el puente. Al reiniciar la app comienza en simulación local.
Cambiar de conexión borra el recorrido recibido anterior para no mezclar orígenes.

## Geocerca de planificación

`PUT /api/v1/geofence` recibe directamente una Feature GeoJSON (sin otro envoltorio),
como el archivo exportado por la app. Un Polygon sin huecos, un anillo cerrado, ejes
`[longitud, latitud]`, nombre 1–40 caracteres, 3–64 vértices únicos separados al menos
0,25 m; latitud ±85°, entorno local 5 km, área mínima 1 m²; sin cruces ni superposiciones.
El puente normaliza el sentido antihorario y conserva la precisión de las coordenadas.

Respuesta 200: `{accepted:true, geofence:<Feature>, area_m2:<número>, applied_to_robot:false}`.
`GET /api/v1/geofence` devuelve `{geofence:<Feature o null>, applied_to_robot:false}`
y, si existe, `area_m2`. Un envío inválido conserva el archivo anterior. Se usa reemplazo atómico.

Errores HTTP: 401 clave incorrecta, 413 más de 64.000 bytes, 422 geometría inválida,
500 fallo de almacenamiento. WebSocket rechaza antes de aceptar cuando la clave es incorrecta.
No hay rutas de velocidad, armado, emergencia, reset o misión.

## Integración existente verificada

19/11/2026: `/home/r2d2/web_estado.py` ejecutado por PID 4246, según la sesión SSH del usuario.
Suscripción `std_msgs/msg/String` a `/base/estado`, respuesta HTTP `/estado` en puerto 8000.
Desde la notebook: HTTP 200 con `{"estado":null}`. El adaptador `estado` consulta esa ruta
cada segundo, con timeout de 2 segundos, y marca el origen no disponible si falla.
No modifica ese archivo, sus agentes, firmware ni configuración ROS.

GPS, batería y alarmas estructuradas reales requieren ampliar las fuentes verificadas de ROS.
No se rellenan con ejemplos en modo `estado`. La conexión y la recepción de datos reales
son comprobaciones distintas.

## Extensión de diagnóstico 0.4.1 — fuente `ros2`

`--source ros2` agrega suscripciones directas de observación, sin GPS y sin publicadores
de comandos. El origen `estado` se conserva por compatibilidad. Ambos mantienen
`schema_version:1`; la nueva app admite los campos opcionales siguientes:

- `sources`: lista de `{key, topic, label, status, age_ms, value, reason}`.
- `status`: `waiting` (nunca recibido), `fresh` (reciente y válido), `invalid` (mensaje
  reciente con medición inválida), `stale` (más de 3 segundos sin recepción).
- `age_ms`: tiempo monotónico desde recepción en la Pi, no desde el reloj del sensor
  ni desde el envío WebSocket. Es `null` cuando no hubo mensajes. Un valor idéntico
  recibido de nuevo renueva su edad; consultar repetidamente un dato retenido no la renueva.
- `value`: solamente está presente como valor vigente en estado `fresh`; en los otros
  casos es `null`. Cada fuente vence independientemente de las demás.
- `boards`: evidencia de recepción de estado de base y brazo. Nunca se deduce la
  presencia de una placa del hecho de que HTTP o el lector ROS respondan.
- `arm_state`: texto vigente de `/brazo/estado`, o `null`.
- `alarm_details`: lista `{code, severity, message, source}`; gravedad `warning`,
  `critical` o `info`. La lista `alarms` conserva los mensajes para clientes anteriores.

| Fuente | Tipo ROS | Valor y unidades |
|---|---|---|
| `/base/estado` | std_msgs/String | Estado y diagnósticos del firmware, texto original |
| `/brazo/estado` | std_msgs/String | Articulaciones y servos, texto original del firmware |
| `/battery` | sensor_msgs/BatteryState | Voltios; resumen redondeado a 0,01 V, sin porcentaje inferido |
| `/imu/data_raw` | sensor_msgs/Imu | Aceleración XYZ m/s², velocidad angular XYZ rad/s, frame_id |
| `/odom` | nav_msgs/Odometry | x/y m, velocidad m/s, giro rad/s y marcos; no equivale a diagnóstico completo de encoders |
| `/bumpers` | std_msgs/UInt8 | Máscara de contactos; cero sin contacto. No se inventa la asignación física de bits |
| `/range/frente`, `/range/izq`, `/range/der` | sensor_msgs/Range | Metros o `out_of_range` para +Inf; NaN, -Inf y valores fuera de rango son inválidos |

Los estados de las ruedas se conservan en el texto y sus fallas se separan como alarmas.
Las alarmas activas se recalculan desde mensajes vigentes. Si vencen los datos, se informa
su pérdida en lugar de afirmar que una alarma física se despejó. No se infiere que el
robot sea seguro de una lista vacía. Un mensaje sin medición válida distingue transporte
funcionando de sensor utilizable.

Se usa `qos_profile_sensor_data` (lector best effort, volatilidad), compatible con los
publicadores reliable y best effort del firmware. El proceso se inicia con descubrimiento
`LOCALHOST` para observar los dispositivos conectados a esta Pi y evitar mezclar otros
robots de la red. No se publica hacia actuadores ni se cambian firmware o parámetros de seguridad.
