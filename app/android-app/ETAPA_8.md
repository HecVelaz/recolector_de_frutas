# Etapa 8 — comunicación con Raspberry Pi

**Actualización 19/11/2026:** ver [PRIORIDAD_1.md](PRIORIDAD_1.md) para el estado vigente:
app 0.4.1, observador ROS directo, fuentes con antigüedad y alarmas separadas. GPS pospuesto.
Las secciones siguientes conservan la verificación anterior de la versión 0.4.0.

Autorizada el 19/11/2026. **Comunicación con la Pi verificada**; la recepción de lecturas
reales de sensores sigue pendiente de que las fuentes ROS las entreguen.

## Implementación

- Versión 0.4.0 (código 4), actualiza 0.3.0 y conserva su geocerca privada.
- Pantalla Conexión: dirección, clave, conectar y volver a simulación local.
- HTTP para enviar la geocerca de planificación; WebSocket para telemetría.
- Reconexión con espera progresiva y detección de ausencia de mensajes a los 5 segundos.
- Lecturas desconocidas `null`, origen visible y separación de recorridos simulados y recibidos.
- Cuando se selecciona el puente, Control, Misión y Estado muestran observación: no envían órdenes.
- Mapa recibido separado del demostrador; sin coordenadas válidas no muestra una posición ficticia.
- Segundo plano cierra el socket; al regresar se reconecta. Al reiniciar comienza en simulación local.
- Configuración privada y backup desactivado. HTTP sin TLS limitado a las IP de prueba de la Pi,
  loopback y localhost; otras direcciones requieren HTTPS o revisar la configuración explícita.

El puente está en `../robot-bridge`, aislado de los repositorios del robot, en el puerto 8001.
Contrato completo: `../robot-bridge/API_V1.md`. No modifica `web_estado.py` ni su puerto 8000.
La recepción de una geocerca no la aplica a ROS ni habilita una misión; esa integración corresponde a la etapa 9.

## Evidencia y límites actuales

- Confirmados por HTTP el servicio existente y su OpenAPI: solo `GET /estado`, resultado `estado:null`.
- Código del servicio proporcionado por el usuario desde SSH: lee `/base/estado` de tipo String.
- Puente probado por HTTP y WebSocket sobre sockets locales tanto con simulación como leyendo la Pi real.
- El servicio antiguo no informa antigüedad de su mensaje. La app lo advierte: no puede confirmar frescura de la base.
- GPS, batería y alarmas estructuradas reales todavía no están expuestos por ese servicio.

Compilación `assembleDebug`, análisis `lintDebug` y 20 pruebas Android: correctos.
Lint: 0 errores, 5 advertencias (las 4 anteriores y sugerencia de extensión KTX para preferencias).
Puente: 6 pruebas correctas; el cliente de pruebas informa una advertencia de deprecación
por httpx/Starlette, sin fallos. Pruebas adicionales HTTP/WebSocket por socket correctas
para simulación y lectura del servicio real de la Pi.

APK instalado y versión 0.4.0 confirmada en Xiaomi bce2c06f.

## Pruebas en la Xiaomi, 19/11/2026

- Geocerca privada recuperada después de actualizar: cuatro vértices, nombre y coordenadas conservados.
- Conexión WebSocket con el puente simulado ejecutado en la notebook mediante `adb reverse`,
  dirección temporal `http://127.0.0.1:8001`. La interfaz distingue «PUENTE SIMULADO».
- Mapa: coordenadas recibidas generan marcador y trayectoria, junto al polígono local conservado.
- Corte del proceso del puente: la interfaz invalida las lecturas y muestra «SIN DATOS RECIENTES».
- Reinicio del proceso: reconexión automática confirmada visualmente, sin pulsar Conectar otra vez.
- Envío desde el botón de la app: GET posterior confirma que el GeoJSON recibido coincide exactamente,
  incluido nombre UTF-8 y precisión de coordenadas. Área del puente 732,066937646 m²;
  `applied_to_robot:false`. Este archivo de prueba está en la notebook, no en ROS.
- Modo `estado` por puerto local 8002, usando la notebook como intermediario hacia la Pi:
  la app muestra origen ROS, servicio disponible y lecturas desconocidas como «sin datos».
- Regreso desde segundo plano: se abre una nueva conexión WebSocket y se recuperan lecturas.

Evidencias en `evidencias/etapa8-*.png`, `etapa8-geocerca-conservada.geojson` y
`etapa8-geocerca-recibida.json`. La configuración temporal de pruebas se cargó mediante
datos privados de la app; la edición manual del formulario todavía no está verificada.

## Despliegue en la Pi

El usuario completó la instalación aislada y arrancó `run_pi.py --source estado`:
PID 6799, puerto 8001. No se modificó el servicio anterior del puerto 8000.
Desde la notebook se verificaron `/health`, telemetría HTTP autenticada y WebSocket directo
con mensajes sucesivos correctos. Sin clave, la telemetría devuelve HTTP 401.
La clave quedó guardada únicamente en las preferencias privadas de la app; no se incluye aquí.

La Xiaomi ya tiene configurada `http://192.168.1.159:8001`, pero la primera prueba directa
no pudo alcanzar la Pi: su Wi-Fi tenía IP `172.16.237.191/19`, y la Pi está en la red 192.168.1.x.
El usuario conectó la tablet a LabEquiposMedicos: IP 192.168.1.107/24.
La app se reconectó directamente a la Pi y mostró «Conectado» y servicio de origen disponible.
Se retiraron las redirecciones USB de los puertos 8001 y 8002 y se confirmó que seguía conectada.
Los servidores temporales de la notebook se detuvieron; el proceso de la Pi se conserva.

Desde el botón de la Xiaomi se envió la geocerca al puente de la Pi. GET autenticado posterior
confirmó coincidencia exacta con el archivo privado de la app: coordenadas, nombre y área
732,066937646 m². Respuesta `applied_to_robot:false`; evidencia
`evidencias/etapa8-geocerca-en-pi.json` y `etapa8-geocerca-pi-confirmada.png`.
También se conserva `etapa8-wifi-directo.png` como evidencia de la conexión directa.

HTTP, WebSocket, autenticación, reconexión y transferencia de geocerca quedaron verificados.
Límite pendiente de integración ROS: el servicio heredado sigue respondiendo `estado:null`;
no hay fuente real disponible para GPS, batería ni alarmas estructuradas en esa API.
Por tanto no se declara verificada la telemetría física ni el estado de seguridad del robot.
La edición manual del formulario tampoco se verificó en esta sesión.

Para mantener la prueba, dejar abierta la sesión SSH que ejecuta el puente. No se configuró
arranque automático. El control real, misiones y aplicación de geocercas corresponden a la
etapa 9, que no está iniciada ni autorizada.
