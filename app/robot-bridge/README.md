# Puente Arturito — etapa 8 (en desarrollo)

Actualización **0.4.1**: observador directo de batería, IMU, odometría, bumpers, distancias
y estado de base/brazo. GPS pospuesto por pedido del usuario. Ver contrato en API_V1.md.

Arranque en la Pi, después de `bash instalar_pi.sh`:

```sh
source /opt/ros/jazzy/setup.bash
ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST .venv/bin/python run_pi.py --source ros2 --data-dir ~/arturito-bridge-0.4.0/data
```

`--data-dir` reutiliza la clave y la geocerca existentes; no borra ni transforma esos archivos.
El entorno virtual usa `--system-site-packages` para encontrar `rclpy` y mensajes de ROS
instalados con Ubuntu. Las dependencias web quedan instaladas dentro del entorno virtual.
El observador funciona aunque falte una placa: informa fuentes sin mensajes, inválidas o vencidas.
El estado del brazo se conserva como texto del firmware; no se ejecuta homing ni armado.

Servicio independiente del `web_estado.py` existente. Puerto propuesto: **8001**.
No publica comandos ROS, no arma motores y no aplica geocercas al control del robot.
El puerto 8000 y los agentes existentes deben permanecer funcionando.

## Ejecución aislada

Python 3.12 o superior. Desde esta carpeta:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
ARTURITO_SOURCE=simulation .venv/bin/python -m uvicorn bridge:app --host 127.0.0.1 --port 8001
```

En Windows usar `.venv\Scripts\python.exe` y configurar las variables con PowerShell.
El modo predeterminado es simulación; no importa ROS ni accede a dispositivos.

Para leer exclusivamente el servicio existente, usar `ARTURITO_SOURCE=estado` y
`ARTURITO_ESTADO_URL=http://127.0.0.1:8000/estado` en la Pi. Un resultado `estado:null`
significa **sin datos**, nunca que los sensores estén funcionando o que sea seguro mover.

## Contrato v1

- `GET /health`: disponibilidad del puente y origen configurado.
- `GET /api/v1/telemetry`: instantánea; datos desconocidos se expresan con `null`.
- `WS /api/v1/telemetry`: instantáneas cada segundo. El cliente debe detectar cortes y reconectar.
- `GET /api/v1/geofence`: área recibida o `null`.
- `PUT /api/v1/geofence`: Feature GeoJSON Polygon, un anillo cerrado, 3–64 vértices.
  Valida geometría antes de escribir. Responde `applied_to_robot:false` explícitamente.

Las rutas `/api/v1` requieren cabecera `Authorization: Bearer <clave>` si se define
`ARTURITO_TOKEN`. Antes de escuchar en la red local es obligatorio definir esa variable;
usar HTTP solamente dentro de la red de prueba. No publicar este puerto en Internet.

La geocerca se conserva atómicamente en `data/operation-boundary.geojson`, separada del
software del robot. Recibirla no habilita una misión ni constituye una barrera de seguridad.
La integración de GPS y otros tópicos ROS queda pendiente de inspeccionar los servicios
que están ejecutándose en la Pi y confirmar sus tipos y disponibilidad.

Pruebas: `.venv/bin/python -m unittest discover -s tests -v`.

## Instalación en la Pi desde el paquete preparado

1. En **otra ventana PowerShell de la notebook**, copiar el ZIP con `scp` al usuario
   `r2d2@192.168.1.159`. La contraseña se escribe únicamente en esa ventana.
2. En **la ventana SSH ya conectada a la Pi**:

```sh
python3 -m zipfile -e ~/arturito-bridge-0.4.0.zip ~/arturito-bridge-0.4.0
cd ~/arturito-bridge-0.4.0
bash instalar_pi.sh
.venv/bin/python run_pi.py --source estado
```

Se crea un entorno virtual independiente; no modifica la instalación Python del servicio
existente. Si falta el módulo `venv`, detenerse y revisar el error antes de instalar paquetes
del sistema. El lanzador genera una clave privada en `data/.connection-token` y la muestra
para ingresarla en la app. No es la contraseña SSH. El proceso queda en primer plano:
mantener abierta esa sesión durante la prueba. No se instala todavía un servicio automático.

En la app: dirección `http://192.168.1.159:8001`, clave mostrada por el lanzador y **Conectar al puente**.
Si devuelve base «sin datos», la comunicación puede estar funcionando: el origen todavía
responde `estado:null`. GPS y batería reales requieren ampliar las fuentes verificadas.

Contrato detallado y límites: [API_V1.md](API_V1.md).

Referencias: https://fastapi.tiangolo.com/advanced/websockets/ y
https://uvicorn.dev/settings/.
