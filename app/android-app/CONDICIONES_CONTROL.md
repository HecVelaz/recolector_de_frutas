# Condiciones obligatorias para permitir control

Fecha: 19/11/2026. Preparación de seguridad previa a la etapa 9.

Este documento define la puerta de habilitación. No agrega publicadores, no habilita movimiento y no
autoriza pruebas físicas. La seguridad primaria sigue en el robot; la app nunca reemplaza la seta.

## Principio

El sistema empieza siempre en `BLOQUEADO`. Estar conectado al puente o recibir telemetría no habilita
control. Toda condición se evalúa continuamente y con criterio de **fallo seguro**: dato ausente,
inválido, vencido o contradictorio equivale a condición no cumplida.

La habilitación debe existir en tres capas:

1. **Firmware:** límites, seta, watchdog, obstáculos, franja y fallas locales.
2. **Puente:** único punto autorizado para publicar; lista cerrada de comandos, vigencia y sesión.
3. **App:** confirmación humana, hombre muerto, primer plano y presentación del motivo de bloqueo.

La app no publicará directamente en ROS. El puente actual 0.4.1 es solo de observación y debe seguir
con `commands_enabled=false` hasta implementar y probar estas reglas.

## Estados de la puerta

| Estado | Significado | Salidas permitidas |
|---|---|---|
| `BLOQUEADO` | Falta una condición o existe una alarma | Solo observar y solicitar parada/desarmado |
| `LISTO` | Todas las condiciones previas son verdaderas | Solicitar habilitación; todavía sin movimiento |
| `HABILITADO` | Usuario confirmó la sesión y los controladores respondieron | Movimiento solo con hombre muerto |
| `ACTIVO` | Hombre muerto presionado y comandos recientes | Comandos acotados a 10 Hz |
| `PARADA_ENCLAVADA` | Seta, vuelco, falla, pérdida de enlace o parada explícita | Solo parada, diagnóstico y rearme supervisado |

Cada nueva conexión, reinicio de app, cambio de Wi-Fi, reconexión ROS, cambio de modo o retorno desde
segundo plano vuelve a `BLOQUEADO`. Nunca se restaura movimiento automáticamente.

## Condiciones generales obligatorias

Todas deben cumplirse simultáneamente:

- App autenticada contra el puente correcto, en modo real y no simulado.
- App visible y en primer plano; pantalla activa y sesión de control explícita.
- Un solo operador posee un **lease de control** exclusivo. Una segunda app no puede publicar.
- Puente ROS disponible, con `commands_enabled=true` habilitado explícitamente en la Pi.
- Base y brazo identificados por sus tópicos esperados; no por descubrimiento genérico de la LAN.
- `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` para los agentes y el puente de este robot.
- Edad máxima por fuente en el puente: **650 ms** para estado de base, **1250 ms** para batería
  y **500 ms** para brazo y demás fuentes obligatorias. Los 3 s de la pantalla sirven para diagnóstico.
- Heartbeat app–puente y lease renovados como máximo cada **250 ms**.
- Seta física accesible y una persona junto al robot durante pruebas iniciales.
- Potencia, área despejada y configuración mecánica confirmadas mediante checklist humano.
- Ninguna alarma crítica activa y ningún dato requerido en espera, inválido o vencido.
- Modo manual y autónomo mutuamente excluyentes.

## Condiciones de la base

Para armar la base:

- `/base/estado`, `/battery`, `/odom`, `/bumpers`, `/imu/data_raw` y rangos requeridos recientes.
- Estado inicial `DESARMADA` y `modo=parado`.
- `seguridad=ok`, sin `SETA`, `VUELCO`, `BATERIA_BAJA`, `imu=SIN_DATOS`, fallas de ruedas ni bloqueos
  incompatibles con la dirección solicitada.
- Tensión real igual o mayor a **10,5 V**. Valores residuales con 12 V apagados no habilitan.
- `rueda_izq=ninguna` y `rueda_der=ninguna`.
- Máscara de bumpers igual a cero.
- IMU válida para movimiento en el piso.
- Para avanzar: rango frontal válido o `out_of_range`; `NaN`, vencido o sin eco bloquea avance.
- Para retroceder o girar, no debe existir el bloqueo direccional correspondiente.
- Primera prueba: ruedas elevadas y velocidad limitada al valor de puesta en marcha aprobado.

Secuencia de armado:

1. La app presenta cada condición y el usuario mantiene “Preparar control” durante 2 segundos.
2. El puente toma el lease, publica cero y comprueba que la base sigue parada.
3. El puente envía `armar` una sola vez por `/base/comando`.
4. Solo pasa a `HABILITADO` al recibir `/base/estado` reciente con `ARMADA`, `seguridad=ok` y
   `modo=parado`.

La base ya aporta una segunda barrera: cada sesión micro-ROS empieza desarmada, `/cmd_vel` queda
bloqueado hasta `armar`, y la pérdida del agente detiene y desarma. Su watchdog es de 300 ms.

## Condiciones del brazo

Para control ordinario del brazo:

- `/brazo/estado` reciente y con formato completo `q`, `e`, `c`, `fc`, `pz` y `mn`.
- Los tres ángulos son finitos y están dentro de los límites documentados.
- `c=111`: las tres articulaciones tienen cero real. Con `c=000`, como ahora, se bloquean `j`, `mv`,
  `jv`, pinza y muñeca desde la app.
- Ninguna articulación está en homing o movimiento previo (`e=1`, `e=5` o `e=6`) al iniciar otra orden.
- Franja del cuatro barras y protección de caja activas; no se permite exponer `fr 0`, `fb`, `z` ni
  `zq` en la app de operación.
- Finales de carrera coherentes con la pose y sin mensaje de atasco, cuentas invertidas, pérdida de
  encoder, exceso de error, franja o caja.
- Brazo apoyado/área despejada confirmados antes del primer homing o movimiento con potencia.

El firmware `20-brazo-coordinado` frena por límites, error de seguimiento, franja y caja, y detiene el
joystick después de 300 ms sin actualización. Sin embargo, **no tiene armado de sesión equivalente al
de la base**: acepta `/brazo/comando` al conectarse. Por eso, antes de etapa 9, el puente debe agregar
un armado lógico del brazo y una lista cerrada de comandos.

Homing no es control ordinario. Solo se permite en un modo de mantenimiento separado, con confirmación
local, persona junto a la seta, pose inicial abajo y recogida, velocidad propia del firmware y sin
ninguna otra orden simultánea.

## Hombre muerto y cadencia

- Movimiento solo mientras el usuario mantiene presionado el control de hombre muerto.
- La app envía referencia como máximo a 10 Hz; el puente descarta mensajes repetidos, atrasados o fuera
  de la sesión vigente.
- Al soltar, la app manda cero; el puente deja de publicar movimiento inmediatamente.
- Si no llega renovación en **250 ms**, el puente publica cero/parada y revoca la habilitación.
- El watchdog local de 300 ms queda como última barrera, no como mecanismo normal de parada.
- Cerrar la app, bloquear pantalla, cambiar de aplicación, perder Wi-Fi, WebSocket o ROS produce la
  misma transición a `PARADA_ENCLAVADA`.

## Acciones siempre permitidas

Aunque la puerta esté bloqueada, se permiten exclusivamente acciones que reduzcan riesgo:

- publicar cero/parada;
- `desarmar` la base;
- cancelar el lease;
- mostrar diagnóstico;
- solicitar una parada del brazo previamente definida y comprobada.

La parada remota no se presenta como “emergencia” equivalente a la seta. Si la red falla, la seta
física y las protecciones locales son las únicas barreras independientes.

## Geocerca y modos de operación

- La geocerca guardada en la app y aceptada por el puente todavía **no se aplica en el robot**.
- Con GPS/localización real pospuestos, se bloquean navegación autónoma y desplazamiento exterior.
- Una prueba de banco con ruedas elevadas puede usar un modo de puesta en marcha separado, sin afirmar
  que la geocerca está protegida.
- Para operación real sobre el piso se exigirá localización válida, geocerca vigente y confirmación
  `geofence_enforced=true` desde el controlador del robot.

## Causas de bloqueo inmediato

Cualquiera revoca el lease, manda parada de mejor esfuerzo y exige rearme manual:

- seta, vuelco o seguridad distinta de `ok`;
- batería baja o dato de batería inválido/vencido;
- bumper activo;
- falla de rueda, encoder o seguimiento;
- estado de base con edad mayor a 650 ms o brazo con edad mayor a 500 ms;
- puente, agente, WebSocket o Wi-Fi desconectado;
- app fuera de primer plano;
- cambio de modo manual/autónomo;
- comando desconocido, fuera de rango o con secuencia inválida;
- brazo fuera de franja/caja o sin cero para una orden que lo requiere;
- pérdida del lease o presencia de un segundo operador;
- para operación real, localización/geocerca no válidas.

## Requisitos antes de implementar la etapa 9

- Agregar al puente una máquina de estados y lease, sin aceptar texto ROS arbitrario.
- Añadir endpoints tipados para preparar, habilitar, renovar, parar y desarmar.
- Definir límites numéricos de velocidad por modo y validarlos también en la Pi.
- Añadir armado lógico por sesión para el brazo.
- Hacer que app y puente registren cada transición y motivo de bloqueo.
- Probar todo primero con publicadores simulados; después con 12 V apagados; finalmente con ruedas
  elevadas y autorización física específica.
- Verificar que cada pérdida de enlace produzca parada y que ninguna reconexión retome movimiento.

## Criterio de aceptación

Esta definición queda aceptada cuando una matriz de pruebas demuestra que cada condición faltante
mantiene `BLOQUEADO`, cada fallo durante `ACTIVO` produce parada en menos de 300 ms y ninguna
reconexión recupera control sin una nueva confirmación humana.

## Cierre de las definiciones pendientes

### Armado, desarmado y emergencia

- `DESARMADO`: estado inicial y posterior a toda conexión o fallo; se aceptan únicamente diagnóstico,
  parada y solicitud de armado.
- `ARMADO`: lease vigente y puerta completa; todavía no implica movimiento.
- `ACTIVO`: armado más hombre muerto presionado y comando válido reciente.
- `EMERGENCIA`: estado enclavado por seta, vuelco, falla crítica o parada humana. Ordena cero y
  desarmado de mejor esfuerzo. Solo sale mediante rearme humano después de desaparecer la causa.
- La app no llamará “emergencia” a una parada remota: la seta física conserva esa función.

### Límites y protecciones confirmados en código

- Base: watchdog de 300 ms, parada frontal a 0,20 m, reducción desde 0,50 m, vuelco a 25°, batería
  baja a 10,5 V, bumpers, seta NC y fallas de rueda.
- Brazo: límites articulares, margen de destino de 3°, franja J2/J3, protección de caja, finales de
  carrera, detección de atasco/cuentas/error de seguimiento y hombre muerto del joystick de 300 ms.
- J1 conserva un máximo provisional de 118° y debe medirse nuevamente con el soporte de visión actual.
- Las tablas de franja y caja están confirmadas como presentes en firmware, pero requieren validación
  física antes de operación. Por ello los límites quedan **confirmados en software, no certificados
  físicamente**.

### Exclusión manual/autónomo

- Solo existe un modo activo: `OBSERVACION`, `MANUAL` o `AUTONOMO`.
- Cambiar de modo revoca el lease, publica parada, desarma y exige confirmación nueva.
- `MANUAL` acepta únicamente hombre muerto; `AUTONOMO` rechaza joystick.
- `AUTONOMO` permanece bloqueado hasta disponer de localización real y geocerca aplicada en el robot.

### Lista inicial de comandos permitidos

El puente usará endpoints tipados; nunca aceptará texto ROS libre.

- Siempre: `stop`, `disarm`, `release_lease`.
- Base preparada: `prepare_base`, `arm_base`, `deadman_velocity(v,w)`, con límites numéricos.
- Brazo preparado: `prepare_arm`, `deadman_joints(j1,j2,j3)` y posiciones previamente validadas.
- Mantenimiento separado: `home_arm`, con confirmación local específica.
- Prohibidos desde la app normal: `z`, `zq`, `fr 0`, cambios de ganancias, PWM/duty directo y cualquier
  comando desconocido.
- Pinza y muñeca solo después de `c=111`, brazo detenido y sesión habilitada.

### Respuesta definida ante pérdida de comunicación

- App en segundo plano o WebSocket perdido: revocar lease inmediatamente y enviar parada.
- Sin heartbeat durante 250 ms: cero/parada; al superar 300 ms deben actuar también los watchdogs.
- Puente o ROS perdido: firmware local frena; base se desarma y el sistema queda enclavado.
- Telemetría obligatoria por encima de su límite por fuente: bloquear control y parar.
- Al recuperar cualquier enlace: solo `BLOQUEADO`; nunca reanudar el último comando.

## Estado de esta preparación

- [x] Condiciones obligatorias.
- [x] Estados de armado, desarmado y emergencia.
- [x] Inventario de límites y protecciones de software.
- [x] Exclusión manual/autónomo.
- [x] Contrato inicial de comandos permitidos.
- [x] Respuesta ante pérdidas de comunicación.
- [ ] Validación física de límites provisionales.
- [x] Evaluador y máquina de estados puros en el puente, deshabilitados por defecto.
- [x] Pruebas automatizadas de bloqueo, frescura, geocerca, lease y hombre muerto.
- [ ] Integración del flujo de preparación y confirmación en la app.
- [ ] Publicadores y endpoints tipados de control (requieren autorización de etapa 9).
- [ ] Pruebas físicas autorizadas con potencia.

La implementación actual solo agrega `control_gate` al diagnóstico. Informa siempre `blocked`,
mantiene `commands_enabled=false` y no crea rutas ni publicadores de movimiento.
