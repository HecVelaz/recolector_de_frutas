# Etapa 9 · pasos 1 a 7

Implementación preparada el 19/11/2026 exclusivamente para ensayo sin potencia.

## Completado

- Pantalla de preparación con condiciones, confirmación física y motivos de bloqueo.
- Autenticación existente más identificador único de cliente y lease exclusivo.
- Estados `blocked`, `ready`, `enabled`, `active` y `latched_stop`.
- Confirmación explícita; una reconexión nunca recupera una sesión anterior.
- Heartbeat cada 150 ms y vencimiento a los 250 ms.
- Parada y liberación al salir de primer plano o desconectar la app.
- Contratos tipados y limitados para base y brazo, con hombre muerto obligatorio.
- Ensayos automatizados de condiciones, límites, propietario y vencimiento.

## Barrera física y de software

El puente de esta entrega no importa ningún publicador ROS ni posee una capa actuadora. Todas las
respuestas de la API de control declaran `dry_run=true`, `commands_enabled=false` y
`robot_command_sent=false`. Los comandos tipados solo se validan; nunca se transmiten.

Arturito 0.5.0 está instalado en la Xiaomi. Tras recuperar conectividad, el puente 0.5.0 quedó
instalado en una carpeta nueva y activo con `ARTURITO_CONTROL_DRY_RUN=1`. También se recuperaron los
agentes de base y brazo después del reinicio de la Pi, sin reiniciar placas ni publicar comandos.

## Pendiente antes del paso 8

1. Validar físicamente los límites provisionales antes de control con energía.
2. El paso 8 requiere otra autorización antes de conectar potencia.

La prueba integrada confirmó preparación `blocked`, confirmación HTTP 409, límite inválido HTTP 422,
parada `latched_stop`, revocación al enviar la app a segundo plano y cero comandos enviados. Evidencias:
`evidencias/etapa9-conexion.png`, `evidencias/etapa9-control-bloqueado.png` y
`evidencias/etapa9-preparacion-bloqueada.png`.

Después del reinicio de la Pi, la ESP32-S3 permaneció sin sesión micro-ROS. Con la potencia
desconectada se detuvo exclusivamente su agente, se aplicó el reinicio por watchdog documentado y se
reinició el agente. La base recuperó `/base/estado`, batería, odometría y bumpers. Informó 0,03 V,
`SETA`, `BATERIA_BAJA` e IMU sin datos; el brazo permaneció reciente con `c=000`. Estas condiciones
mantuvieron correctamente la puerta en `blocked`. No se publicó ningún comando.

## Pruebas de la base y diagnóstico con potencia desconectada

El ensayo estático con la seta accionada registró entre 0,00 y 0,03 V en el punto de
medición situado después de la seta. La base se mantuvo desarmada. Después se
desconectó la batería de los motores.

Con la batería desconectada se probó en la Pi una sesión de base en un dominio ROS
aislado. Un receptor de prueba recibió velocidad cero, la solicitud de armado,
una velocidad después de una confirmación simulada y, al perder una condición,
velocidad cero y la solicitud de desarmado. Las 27 pruebas locales pasaron. La
sesión de prueba permanece separada del puente operativo.

La base real transmite estado, batería, odometría y bumpers. El publicador de
IMU existe, pero no entregó muestras durante la observación. El rango frontal
publicó `NaN`. Según la aclaración del operador, los sensores del montaje real se
alimentan de la batería. Falta verificar su lectura con alimentación. El brazo
sigue publicando `c=000`.

Se midieron intervalos de 999–1100 ms para batería y de 493–606 ms para estado de
base. El puente aplica 1250 ms a batería, 650 ms a estado de base y 500 ms a las
demás fuentes obligatorias. Los 28 ensayos locales y en la Pi pasaron. El puente
operativo quedó en modo ensayo y con la puerta bloqueada.

## Mando de base en la Xiaomi

Arturito 0.5.1 muestra el mando únicamente cuando el puente anuncia la salida simulada.
El ensayo se hizo por USB con un puente local, datos sintéticos y la batería de los
motores desconectada. En la Xiaomi se preparó y confirmó la sesión. Al mantener
presionada la flecha de avance se midió 0,1 m/s en el simulador. Al soltarla o salir
de la app, la velocidad volvió a cero. Al cortar el enlace y cerrar las conexiones
activas durante otra pulsación, se midió cero y la sesión quedó en `latched_stop`.
Pasaron 29 pruebas del puente, las pruebas Android y lint.

## Recorrido completo de Xiaomi a ROS

La Xiaomi se conectó por USB y túnel SSH a un puente temporal en la Pi, en
loopback y en un dominio ROS aislado. Tras una confirmación de armado del
receptor de prueba, la pulsación produjo 0,1 m/s en ROS. El receptor recibió
velocidad cero y desarmado al soltar, simular una alarma, perder la telemetría
o cortar el enlace. Al restablecer el enlace, la velocidad siguió en cero y
la sesión quedó enclavada.

La revisión pasiva del robot encontró suscriptores de la base en `/cmd_vel` y
`/base/comando`, sin publicadores en esos dos tópicos. La base seguía en
`EMERGENCIA (seta)`, el brazo en `c=000` y el puente operativo en modo ensayo.
La prueba de movimiento físico queda pendiente de integrar la salida con el
robot supervisado, resolver esos bloqueos y verificar el estado al energizar.

## Adaptador de la base real

El adaptador preparado en `robot-bridge/ros_base_link.py` tiene una configuración
explícita para `/cmd_vel`, `/base/comando` y `/base/estado`. Se validó el mismo
adaptador con tópicos de prueba en un dominio ROS aislado. Pasaron 31 pruebas
locales. El adaptador permanece fuera del proceso operativo de observación.

El firmware distingue el rearme de seguridad (`r`) del armado ROS (`armar`).
El segundo solo cambia la aceptación de comandos de velocidad. Antes de una
prueba física hay que confirmar el rearme de seguridad y recibir
`DESARMADA modo=parado seguridad=ok` con IMU válida. La última comprobación sin
potencia encontró emergencia enclavada y brazo sin cero (`c=000`).

## Perfil de banco a velocidad cero

El rearme presencial confirmó `DESARMADA modo=parado seguridad=sin comandos`.
La espera del watchdog se acepta únicamente como estado de preparación de una
base desarmada y parada. Durante la transición se espera un reporte nuevo de
`ARMADA`, se envía velocidad cero y solo se completa la confirmación cuando
llega un reporte posterior con `ARMADA` y `seguridad=ok`. El firmware real
informa `modo=v/w` al recibir cero. El perfil de banco exige además odometría
reciente con velocidad lineal ≤ 0,005 m/s y angular ≤ 0,02 rad/s en magnitud.

El puente tiene un perfil separado, autenticado y limitado a loopback para
integrar el adaptador real en un ensayo de banco. Rechaza la preparación si hay
otro publicador en los tópicos de control o no se detecta la base. El perfil
requiere que el responsable confirme el aislamiento físico del brazo en cada
preparación. En ese perfil el cero del brazo no es un requisito, las órdenes al
brazo se rechazan y el puente no crea publicadores de control del brazo. La API y
el publicador de base bloquean velocidades distintas de cero.

Se validaron 33 pruebas locales y en la Pi, y dos ensayos ROS con receptores
aislados. El perfil de banco quedó preparado en una carpeta separada. El puente
operativo de observación quedó activo y bloqueado. El operador confirmó el
aislamiento físico del brazo. En el primer ensayo con la base real, el puente
rechazó la confirmación y la base terminó desarmada. La corrección para
`modo=v/w` se validó en ROS aislado y se cargó con el selector en OFF.

La repetición con la base real y el bus a 11,12 V pasó en dos sesiones. En
ambas se confirmó `ARMADA modo=v/w seguridad=ok`. El observador ROS recibió
15 mensajes de velocidad cero en la prueba de suelta y 17 en la de vencimiento
de latido. La odometría lineal y angular marcó cero en ambas y la base regresó
a `DESARMADA modo=parado`. La primera prueba con velocidad distinta de cero
queda pendiente.

## Perfil de movimiento limitado en banco

El perfil de banco para ruedas elevadas quedó preparado y validado con un
receptor ROS aislado. La API y el publicador restringen el avance a un solo
pulso por armado, sin giro ni retroceso. El software limita el pulso a
0,05 m/s y 200 ms. Se comprobó velocidad cero y desarmado al vencer el plazo,
soltar el mando o informar una alarma. El perfil exige confirmación del
soporte, ruedas elevadas y aislamiento físico del brazo.

Pasaron 35 pruebas locales y en la Pi. El perfil de movimiento quedó preparado en
una carpeta persistente separada. El 20/11/2026 se ejecutó un único pulso
aprobado en banco, de 0,04 m/s y 120 ms solicitados. El observador ROS midió
137,1 ms entre el mensaje de avance y el de velocidad cero. La odometría
alcanzó 0,0283 m/s en magnitud y volvió a cero lineal y angular. La base
terminó desarmada y parada, con la sesión enclavada y sin nuevos cortes de
enlace durante el ensayo. El puente habitual continúa en observación.

La serie de repetibilidad con ruedas elevadas usó los mismos 0,04 m/s y
120 ms solicitados. ROS registró 125,7, 134,3 y 136,4 ms hasta la orden de
cero (variación de 10,7 ms entre el mínimo y el máximo). La odometría lineal
y angular terminó en cero en los tres ensayos. La base quedó desarmada y
parada en cada caso y no se registraron nuevos cortes de enlace durante la
serie. El perfil de banco se cerró al terminar.

## Preparación para el piso con el selector en OFF

La revisión de ROS en la Pi encontró la odometría de la base en `odom` y el
tópico de IMU. Durante la revisión no apareció un publicador de pose vinculado
a una referencia fija del laboratorio. La odometría de ruedas y el giróscopo
no acreditan por sí solos la posición dentro de la geocerca física.

El ensayo aislado usa un polígono en metros y una pose con marco fijo, origen
identificado, edad y errores máximos declarados. Antes de aceptar el avance
se comprueba el recorrido recto completo, incluido el margen por tamaño del
robot, incertidumbre de pose y reserva de frenado. Los ensayos en la Pi
verificaron rechazo por ausencia de pose o falta de margen y velocidad cero
con desarmado al perder localización durante el pulso. Pasaron 40 pruebas
locales y en la Pi. El control real continúa deshabilitado y la geocerca
guardada por la app continúa sin aplicarse al robot.

Pendiente en el laboratorio con el selector en OFF: medir la zona, elegir y
marcar la referencia fija, y definir cómo se obtendrá una pose real en ese
marco. Los márgenes simulados son valores de prueba y requieren validación
para el montaje real.

Los ensayos con alimentación deberán registrar primero sensores, odometría y
pose real con la base desarmada. Antes de un movimiento en el piso, el
controlador debe aplicar la geocerca medida y se deben comprobar el bloqueo
por pérdida de posición y el margen de parada. La función de simulación no
publica en los tópicos de movimiento del robot real.
