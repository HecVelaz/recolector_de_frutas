# Etapa 7 · Geocerca

Versión 0.3.0. Edición local de un polígono de operación sobre MapLibre, con guardado y exportación GeoJSON. No envía datos al robot ni impide movimientos físicos.

## Crear el área

1. Abrir **Mapa → Geocerca**. El recorrido GPS de ejemplo se pausa y el seguimiento del robot se desactiva para no desplazar el mapa mientras se dibuja.
2. Escribir el nombre del área y activar **Editar puntos**.
3. Tocar al menos tres puntos del mapa, siguiendo el borde en orden. Los vértices son naranjas.
4. Pulsar **Cerrar polígono**. Solo un polígono válido muestra relleno y permite guardar/exportar.
5. Pulsar **Guardar geocerca**. Se guarda un único archivo local; si se modifica una copia anterior, se confirma su reemplazo.

## Corregir el área

- **Mover:** activar Editar puntos, tocar un vértice naranja (se vuelve violeta) y tocar su nueva posición. También puede seleccionarse P1, P2, etc. en la lista de coordenadas.
- **Eliminar un punto:** seleccionar el vértice y pulsar Eliminar punto seleccionado. Si quedan menos de tres, el polígono vuelve a borrador abierto.
- **Agregar a uno cerrado:** Abrir para agregar puntos. Los puntos nuevos se agregan al final de la secuencia; cerrar nuevamente antes de guardar.
- **Deshacer:** revierte hasta 64 cambios de geometría, incluidos cierre, apertura, borrado y carga.
- **Vaciar:** limpia solo el borrador, con confirmación; conserva la copia guardada.
- **Cargar guardada:** recupera la copia local y confirma antes de reemplazar un borrador distinto. La carga también puede deshacerse.
- **Ver toda la geocerca:** ajusta el encuadre al polígono.

La copia guardada se carga al iniciar la app. El borrador y el historial de deshacer son de la sesión; guardar antes de cerrar, girar o recrear la actividad evita perder cambios sin guardar.

## Validación

- 3 a 64 vértices para cerrar.
- Coordenadas finitas, longitud ±180° y latitud entre −85° y +85°.
- Separación mínima entre vértices: 25 cm.
- Sin cruces, contactos entre lados no adyacentes ni lados adyacentes superpuestos.
- Área mínima: 1 m².
- Radio local máximo: 5 km desde el primer punto. Se usa proyección local aproximada para medidas en metros; no es una herramienta de agrimensura.

Una adición o movimiento inválido se rechaza conservando el borrador anterior. Un cierre inválido mantiene el área abierta y muestra el motivo. Guardar y exportar permanecen deshabilitados hasta corregirlo.

## Archivo y preparación del envío

- **Guardar geocerca:** archivo privado `operation-boundary.geojson`, escrito mediante AtomicFile para no reemplazar la copia previa con un archivo parcial.
- **Exportar GeoJSON:** abre el selector de Android para elegir destino y nombre, sin permisos de acceso general al almacenamiento.
- **Ver GeoJSON para envío futuro:** muestra el contenido que podrá consumir la API; no hace una solicitud de red.
- Formato: Feature con Polygon de un único anillo, coordenadas `[longitud, latitud]`, cierre idéntico al primer punto y orientación exterior antihoraria.
- Propiedades: `name`, `schemaVersion: 1`, `purpose: "operation_boundary"`.
- Se conservan los Double originales en la serialización. El serializador geográfico del SDK redondea coordenadas y no se usa para guardar este límite.

El archivo no incluye un GPS de la tablet. La aceptación por el robot y cualquier medida de seguridad se implementarán y validarán en ROS 2 en las etapas siguientes.

## Implementación

- `model/Geofence.kt`: geometría, validación y contrato GeoJSON.
- `ui/GeofenceSession.kt`: borrador, selección e historial.
- `data/GeofenceStorage.kt`: persistencia local.
- `ui/screens/GeofenceEditor.kt`: controles, confirmaciones, vista JSON y exportación.
- `ui/components/RobotMap.kt`: callbacks de toque, capas de área, borde, vértices y selección.
- `ui/screens/MapScreen.kt`: alternancia GPS/Geocerca y encuadre.

No se agregaron dependencias: JSON utiliza Gson, ya incluido por MapLibre. La compilación usa un trabajador y heap de Gradle de 1 GB para reducir el consumo en esta PC; las pruebas usan 256 MB.

## Verificación

Compilar APK, ejecutar pruebas y Lint:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\compilar.ps1 -Pruebas
```

Pruebas específicas: área y orientación, cruces con área abierta y al cerrar, duplicados, superposición, degeneración, límites locales, GeoJSON de ida/vuelta, orden de ejes, normalización y archivos malformados; edición, eliminación, deshacer y estado de guardado.

18/11/2026: compilación de versión 0.3.0 y Lint correctos (0 errores, 4 advertencias de configuración). **16 pruebas aprobadas**, incluidas 10 específicas de geocerca y 6 de GPS/trayectoria. El APK se copió a Descargas de la Xiaomi como `Arturito-0.3.0.apk`.

Verificación en Xiaomi Pad 5: versión 0.3.0 instalada. Se conservó el borrador de cuatro puntos creado por el usuario; un intento de mover P4 cruzando lados fue rechazado sin modificarlo. Se cerró el polígono, se mostró relleno y área aproximada de **732,1 m²**, y se guardó localmente. El archivo privado se inspeccionó: anillo cerrado de cuatro vértices, orientación exterior antihoraria y coordenadas conservadas.

Se exportó con el selector de archivos de Android a `Descargas/arturito-geocerca.geojson` y se comparó su contenido con la copia privada: idénticos. Tras detener y volver a abrir la app, se recuperaron nombre, cuatro vértices, estado válido y área de 732,1 m². Se dejó abierta la geocerca guardada en la tablet. Las pruebas automatizadas cubren también movimientos válidos, eliminación y deshacer; estos últimos no se ejercitaron de nuevo en el dispositivo para conservar el área del usuario.

Evidencias en `evidencias/`: `etapa7-cruce-rechazado.png`, `etapa7-cerrado.png`, `etapa7-guardado.png`, `etapa7-final.png` y `etapa7-geocerca-guardada.geojson`.

Implementación y verificación completadas; pendiente de la confirmación del usuario. La etapa 8 requiere autorización explícita.

Referencias: [GeoJSON RFC 7946](https://www.rfc-editor.org/rfc/rfc7946.html), [toques en MapLibre Android](https://maplibre.org/maplibre-native/android/api/-map-libre%20-native%20-android/org.maplibre.android.maps/-map-libre-map/add-on-map-click-listener.html).
