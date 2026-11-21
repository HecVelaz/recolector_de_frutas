# Prioridad 1 — telemetría, vigencia y alarmas (etapa 8)

19/11/2026. App **0.4.1, código 5**, instalada y comprobada en Xiaomi Pad 5.
GPS pospuesto expresamente. No se implementan órdenes de movimiento, homing, armado ni misiones.

## Checklist y alcance

- [x] Registrar edad de cada fuente con reloj monotónico al recibir su mensaje ROS.
- [x] Retirar valores vigentes al pasar 3 segundos sin recepción; distinguir espera, reciente, inválido y vencido.
- [x] Leer tensión real `/battery`, sin inferir porcentaje. Resumen a 0,01 V.
- [x] Leer IMU `/imu/data_raw`, validar valores y campos de disponibilidad, mostrar unidades SI.
- [x] Leer odometría `/odom` y fallas de ruedas informadas en `/base/estado`.
  **No se exponen cuentas crudas de encoder ni se certifica su calibración.**
- [x] Leer máscara `/bumpers` sin inventar asignaciones físicas de bits.
- [x] Leer `/range/frente`, `/range/izq` y `/range/der`, diferenciando distancia, +Inf y medición inválida.
- [x] Preparar lectura `/brazo/estado` y mostrar su ausencia sin confundirla con servicio desconectado.
- [ ] Verificar recepción real del brazo: su WROOM inicia una consola serie y no establece sesión micro-ROS.
- [x] Separar alarmas de seta, seguridad de base, batería baja, IMU sin datos, rueda con falla,
  contacto de bumper y fuentes ausentes/inválidas/vencidas. Ordenar críticas primero.
- [x] Distinguir conexión con puente, lector ROS disponible y recepción por fuente/placa.
- [x] Probar pérdida y recuperación de datos de base, y corte y recuperación del puente en la tablet.
- [x] Documentar fuentes, contrato, pruebas y limitaciones.

## Arquitectura y despliegue

La nueva fuente `ros2` de `robot-bridge` utiliza un nodo `arturito_observador` con suscripciones
best effort/volatile. No crea publicadores de comandos, servicios de actuación ni acciones.
La fuente antigua `estado` permanece compatible, pero no permite determinar edad de su texto.
La app 0.4.1 reconoce ambos contratos y mantiene guardada su geocerca y configuración.

Se detectaron tópicos de otros equipos en el descubrimiento SUBNET. El observador y los agentes
de esta prueba usan `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` para no mezclar robots de la LAN.
Esto no modifica el entorno de otros procesos ni el firmware.

Pi: `/home/r2d2/arturito-bridge-0.4.1`, entorno virtual con paquetes ROS del sistema accesibles.
El puente escucha en 8001. Reutiliza `/home/r2d2/arturito-bridge-0.4.0/data` para conservar
la clave y la geocerca existentes. La app se conecta directamente por Wi-Fi a 192.168.1.159.
El nuevo modo no necesita `web_estado.py` en 8000. No se configuró arranque automático.

Agente base: identificador USB estable
`/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_94:A9:90:30:24:24-if00`.
Log de esta sesión: `~/logs/arturito-etapa8-base.log`.
Puente: `~/arturito-bridge-0.4.1/bridge.log` (permisos 600).

Arranque manual del puente si se detiene (no iniciar otra instancia si el puerto está ocupado):

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arturito-bridge-0.4.1
ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST .venv/bin/python run_pi.py --source ros2 --data-dir ~/arturito-bridge-0.4.0/data
```

## Pruebas

- Android: `assembleDebug`, `lintDebug` y **22 pruebas unitarias** correctos.
  Lint conserva 0 errores y 5 advertencias de configuración/dependencias/KTX.
- Puente: **12 pruebas** correctas (HTTP/WS/auth/geocerca, reloj, vencimiento independiente,
  datos inválidos, alarmas que se actualizan y codificación JSON sin NaN/Inf).
- Pi real: fuente `ros2`, recepción de base, batería, odometría, bumpers y rangos.
  La IMU llegó a publicar al recuperarse su alimentación; posteriormente volvió a faltar.
- Pausa temporal del agente base de esta prueba, reanudado con `finally`: el puente siguió
  disponible, las fuentes vencieron y sus valores se retiraron; al reanudar regresaron a recientes.
- Pausa temporal del puente de observación, sin detener agentes: la tablet mostró
  «SIN DATOS RECIENTES» y retiró valores; reconexión posterior comprobada.
- Capturas `evidencias/prioridad1-*.png`. No se ordenaron movimientos ni se grabó firmware.

## Hallazgos físicos y pendiente de brazo

Se observaron batería ~11,2 V e IMU válida durante parte de la prueba. El usuario confirmó que
la potencia estaba encendida y luego la apagó para permitir revisar la WROOM. La tensión cayó
por debajo de 1 V y reaparecieron avisos de batería baja/IMU sin datos. No se concluye de esto
que los sensores estén averiados: su alimentación y funcionamiento físico requieren revisión.
Los tres rangos publicaron NaN durante la prueba: la app los muestra inválidos, no como camino libre.

Para la WROOM se siguió el pulso EN documentado en `~/scripts/25-teleop-pi/tools/lanzar.sh`,
con potencia apagada confirmada por el usuario. No hubo sesión micro-ROS.
Una lectura de arranque a 115200 mostró el programa de prueba 20 y la ayuda de comandos por
consola (`h`, `j`, `mv`, etc.). En el código local esa salida/ayuda por UART corresponde a la
variante sin `USAR_MICROROS`; la variante ROS redirige esa salida a `/brazo/respuesta`.
No se enviaron comandos de movimiento. Se intentaron únicamente las consultas `c`, `pz e`
y `mn e` con potencia apagada; al abrir el puerto la WROOM reinició y emitió la ayuda de
consola, sin responder con un estado periódico. Se detuvo el agente del brazo al comprobar que no
había protocolo micro-ROS. La WROOM conserva su firmware; la app informa «sin mensajes».

Resolver el firmware/interfaz del brazo requiere revisar esa variante y el respaldo de la
flash antes de cualquier cambio. No se flasheó ni se considera ese pendiente completado.
La prioridad 1 queda implementada para las fuentes disponibles y pendiente de recepción del brazo.
No se comenzó la prioridad 2 ni la etapa 9.

## Inspección de variantes del brazo (19/11/2026)

Se repitió la revisión de solo lectura antes de intervenir. El puente seguía activo en el puerto
8001 y el agente micro-ROS de la base utilizaba exclusivamente el identificador estable de la S3.
La WROOM aparecía como `/dev/ttyUSB0`, sin agente ni monitor que ocupase el puerto. La telemetría
indicaba base reciente en modo `parado`, tensión de 0,0 V, odometría nula y brazo en espera. Esto es
coherente con la potencia apagada, pero no sustituye una confirmación física antes de un futuro reset
o flasheo.

El historial de la Pi muestra que el 11/11 se grabó el conjunto
`~/firmware/brazo20_ros`, cuya aplicación micro-ROS publica `/brazo/estado`. El 18/11 se reemplazó la
flash completa de la WROOM por `~/firmware/brazo20_serie_20261118h.bin`. No hay otra escritura a la
WROOM registrada después. La ayuda y el banner observados por UART coinciden con esta última variante
serie. No se leyó nuevamente la flash porque `esptool` reiniciaría la placa; por eso la identidad se
considera respaldada por historial y salida de arranque, no por una comparación criptográfica actual.

La Pi conserva los siguientes elementos relevantes:

- `~/firmware/brazo20_ros/firmware.bin`, 417.712 bytes, SHA-256
  `c2419a3ce4aaf78c28115e138c46a0041a3c8fb2128d70de20acb4ccd2c4aae2`, fechado 11/11.
- `~/firmware/brazo20_serie_20261118h.bin`, imagen completa serie de 4 MiB, SHA-256
  `2332403f8db75accb2aa016deee7f9311d9a901127575060490867303d490db9`, fechada 18/11.
- `~/firmware/brazo20_serie_20261119.bin`, imagen serie posterior de 412.720 bytes, SHA-256
  `ce5c9450b91c81687fe3be875f0a553333c90828f403a327ca61094ea59a8d26`; no figura como grabada.
- Respaldos completos anteriores `respaldo_wroom_20261111.bin` y
  `respaldo_wroom_20261112.bin`.

El binario micro-ROS disponible es anterior a los cambios serie del 18 y 19/11. Por tanto, **no es
seguro reutilizarlo directamente**: podría retroceder límites, franja mecánica, servos o correcciones
del controlador. En la Pi tampoco está el proyecto fuente completo de `20`; `~/scripts/20-brazo-coordinado`
solo contiene herramientas y resultados. La copia local sí contiene el entorno `ros` con
`-DUSAR_MICROROS`, pero sus rutas relativas esperan un repositorio hermano llamado
`recolector_de_frutas`, mientras que en este workspace la copia está anidada bajo
`recolector_de_frutas-main/recolector_de_frutas-main`. No hay artefacto local `.pio` ya compilado.

El siguiente paso seguro es preparar, sin grabar, una compilación micro-ROS reproducible desde la
fuente más reciente, resolviendo las dependencias por una ruta de trabajo que no modifique las copias
originales. Después se compararán sus tópicos, límites y protecciones con la variante serie. Cualquier
respaldo actual o flasheo requerirá confirmación física de 12 V apagados y autorización específica.

### Compilación micro-ROS candidata

Se preparó una copia mínima y aislada del proyecto en la Pi, sin modificar las fuentes originales ni
abrir `/dev/ttyUSB0`. La construcción en Windows no es viable directamente con esta versión de
`micro_ros_platformio`: primero falla con rutas que contienen espacios o exceden el límite de Windows
y, aun usando una ruta corta, su script ejecuta comandos de shell Unix. Por eso se creó en la Pi un
entorno de usuario separado con PlatformIO Core 6.1.19.

La copia de trabajo fija `espressif32@7.0.1`; el `platformio.ini` original solamente decía
`espressif32` y en una instalación nueva resolvía 8.0.0. La versión fijada recupera el entorno usado
por el proyecto: Arduino ESP32 2.0.17 y toolchain Xtensa 8.4.0+2021r2-patch5. Esta fijación existe solo
en la copia de compilación.

`pio run -e ros` terminó correctamente, sin objetivo `upload`:

- RAM: 46.096 de 327.680 bytes (14,1 %).
- Programa: 417.405 de 1.310.720 bytes (31,8 %).
- `firmware.bin`: 417.776 bytes, SHA-256
  `1bb3c63c87f667b9e1b1c42bc92624948d029f6718010c93efe37e46149958a4`.
- El binario contiene `brazo/comando`, `brazo/estado` y `brazo/respuesta`, además del banner y las
  protecciones de la fuente reciente de `20-brazo-coordinado`.
- `bootloader.bin` y `partitions.bin` coinciden por hash con los conjuntos históricos de la WROOM.

Artefactos en la Pi: `~/arturito-build/20261119/artifacts/`. Copia local:
`.codex-build/brazo-microros-20261119-artifacts/`. El candidato **no fue flasheado ni probado en la
placa**. Después de compilar, el puente y el agente de la base seguían activos; la base continuaba en
modo `parado`, batería 0,0 V y el brazo seguía sin mensajes, como corresponde a la variante serie.

### Respaldo actual, comparación y procedimiento

Con los 12 V físicamente desconectados y `/dev/ttyUSB0` libre, se leyó la flash completa de la WROOM.
La lectura reinició la placa mediante RTS, pero no escribió datos. Respaldo:
`~/arturito-build/20261119/respaldo_wroom_pre_microros_20261119.bin`, 4.194.304 bytes, SHA-256
`37312156ec27b3161eed75b1d2cd1cac18b0f14ca7dbcf668d308a85e28f1862`. Se guardó además una copia
local junto a los artefactos candidatos.

La comparación por regiones confirmó:

- bootloader, particiones y `boot_app0` coinciden exactamente con los componentes conocidos;
- la aplicación actual coincide byte por byte con `~/firmware/brazo20_20261119/firmware.bin`, SHA-256
  `c1d876ac71d7d08204c8e1022c67d48127be6fd86183fe33d4b035cc12d9a02c`;
- no coincide con la variante serie del 18/11, el micro-ROS antiguo del 11/11 ni el candidato nuevo,
  como era esperable antes de instalarlo;
- los respaldos completos históricos del 11 y 12/11 son diferentes del estado actual.

El procedimiento de instalación, comprobación sin potencia y reversión quedó preparado en
`android-app/PROCEDIMIENTO_BRAZO_MICROROS.md`. En ese punto todavía no se había ejecutado
`write-flash`; la instalación posterior se registra a continuación.

### Instalación y comprobación del brazo micro-ROS

Con autorización específica y los 12 V todavía desconectados, se validaron nuevamente los hashes,
el respaldo, el puerto libre y la lectura de batería en 0,0 V. Se grabaron y verificaron mediante
`esptool` el bootloader, la tabla de particiones, `boot_app0` y el candidato micro-ROS en sus
desplazamientos documentados. Cada región pasó la verificación de escritura.

Se inició únicamente el agente del brazo en
`/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`, con descubrimiento `LOCALHOST`. ROS mostró el nodo
`/brazo`, un publicador real de `/brazo/estado`, un publicador de `/brazo/respuesta` y una suscripción
de `/brazo/comando`. Sin publicar comandos se recibió:

```text
q=0.00,0.00,0.00;e=0,0,0;c=000;fc=000;pz=-1;mn=-1
```

El puente mantuvo la fuente del brazo reciente con edades de decenas de milisegundos y la Xiaomi
mostró «Enlace Brazo (según mensajes): Reciente». Al pausar solo el agente durante 4,5 segundos, el
puente marcó el brazo vencido, retiró su valor y luego recuperó el estado reciente al reanudarlo.
Capturas: `evidencias/prioridad1-brazo-microros*.png`.

Tras esa interrupción, el firmware informó `e=4,4,4`: su reacción local ante pérdida de agente pasó
las tres articulaciones al estado de frenado. No fue consecuencia de publicar un comando y, con la
potencia físicamente desconectada, no produjo movimiento. La batería de la base terminó informando
1,86 V pese a los 12 V desconectados; se conserva como lectura residual/no válida, no como evidencia
de potencia habilitada.

No se enviaron mensajes a `/brazo/comando`, no se ejecutó homing, no se habilitaron motores y no se
encendieron los 12 V. El agente queda activo; log `~/logs/arturito-etapa8-brazo.log`. La recepción
real del brazo queda comprobada para la prioridad 1. La prueba física con potencia permanece fuera
de esta etapa y requiere otra autorización.

## Preparación posterior: condiciones para permitir control

Se definió la puerta de habilitación previa a etapa 9 en `android-app/CONDICIONES_CONTROL.md`. La
especificación separa `BLOQUEADO`, `LISTO`, `HABILITADO`, `ACTIVO` y `PARADA_ENCLAVADA`; exige
telemetría de control con edad máxima de 500 ms, lease exclusivo, app en primer plano, hombre muerto,
base armada por sesión y brazo con cero real. También documenta que el brazo aún carece de armado de
sesión propio y que la navegación real queda bloqueada mientras GPS/localización y aplicación de la
geocerca estén pospuestos.

Después se implementó en el puente el evaluador puro y la máquina de estados/lease, deshabilitados
por defecto. La telemetría expone únicamente el diagnóstico `control_gate=blocked`; no se agregaron
rutas ni publicadores de control y `commands_enabled` continúa en `false`. Las 18 pruebas del puente
verifican también el bloqueo por defecto, datos vencidos, batería baja, brazo sin cero, geocerca,
propietario del lease y vencimiento del hombre muerto. La integración en la app y cualquier control
físico permanecen pendientes de autorización de etapa 9.
