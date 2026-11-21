# Etapa 6 · Mapa y GPS

Versión 0.2.0. Nueva pestaña **Mapa**, con MapLibre Native y una posición ficticia cerca de FIUNA. No recibe datos del robot ni lee la ubicación de la tablet.

## Uso

1. Instalar la actualización del APK y abrir Arturito en horizontal.
2. Entrar en Mapa con acceso a internet. Se debe ver la cartografía de OpenStreetMap y un punto azul.
3. Pulsar Simular recorrido: cada segundo cambia la coordenada y se dibuja una línea verde. El circuito dura unos dos minutos y su velocidad está acelerada para la demostración.
4. Pausar: se conservan el punto y el recorrido.
5. Desmarcar Seguir robot para explorar el mapa sin recentrado automático. Arrastrar y pellizcar para desplazar y cambiar el zoom.
6. Centrar robot vuelve a la última posición y reactiva el seguimiento.
7. Reiniciar trayectoria borra únicamente las muestras simuladas de esta sesión y vuelve al punto inicial.
8. La emergencia simulada y el paso a segundo plano pausan el recorrido. Navegar a otra pestaña conserva los puntos y suspende su generación hasta volver al mapa.

El mapa base requiere internet. El trazado y el marcador se calculan localmente; no se ofrece descarga de mapas sin conexión. Si el fondo queda vacío, revisar internet y usar Recargar mapa. «Capa GPS lista» confirma las capas locales, no la descarga de todas las teselas.

## Arquitectura y dependencias

- `model/GpsFix.kt`: coordenadas WGS84, marca temporal, origen simulado y distancia Haversine en metros.
- `ui/MapSession.kt`: posición, trayectoria, controles de simulación y punto de entrada `accept(GpsFix)` para una futura fuente GPS. Descarta marcas temporales antiguas y limita el historial a 600 muestras.
- `ui/components/RobotMap.kt`: MapView nativo dentro de AndroidView; GeoJsonSource, CircleLayer para el robot y LineLayer para la trayectoria. GeoJSON utiliza longitud antes de latitud.
- `ui/screens/MapScreen.kt`: mapa, coordenadas y controles.
- `assets/robot-map-style.json`: proveedor raster HTTPS de OpenStreetMap, con atribución.

MapLibre Native **13.7.1**: versión estable, minSdk 23, compileSdk mínimo 34 y Kotlin 2.2.10, compatibles con minSdk 26, compileSdk 36 y Kotlin 2.2.10 del proyecto. Se usa directamente; no se agrega un wrapper Compose.

OkHttp **4.12.0**: ya es dependencia interna de MapLibre. Se declara directamente para configurar el identificador User-Agent de la aplicación, conservando las políticas de caché del SDK. No implementa la API del robot.

JUnit **4.13.2**, solo pruebas: verifica coordenadas inválidas, unidades de distancia, continuidad del circuito, descarte temporal, pausa/reinicio y límite del historial.

Se agrega INTERNET y se conserva ACCESS_NETWORK_STATE, utilizado por el SDK para conectividad. Se eliminan explícitamente del manifiesto combinado los permisos de ubicación y estado Wi-Fi que trae MapLibre. No se solicita ubicación, no hay claves de servicios cartográficos y no se implementa geocerca ni comunicación ROS 2 en esta etapa.

## Compilar y verificar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\compilar.ps1 -Pruebas
```

El script usa el JBR instalado y normaliza las comillas de PATH únicamente en su proceso. Las pruebas usan un proceso Gradle nuevo para no heredar el java.library.path del daemon iniciado con el PATH defectuoso. No cambia variables globales de Windows.

En Android Studio, MapView se sustituye por un texto durante la vista previa: el renderizador nativo debe verificarse al ejecutar la app en Android.

## Fuentes

- [Inicio de MapLibre Android](https://maplibre.org/maplibre-native/android/examples/getting-started/)
- [Código y requisitos de la versión 13.7.1](https://github.com/maplibre/maplibre-native/blob/android-v13.7.1/platform/android/MapLibreAndroid/build.gradle.kts)
- [Política de teselas de OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/)

Se muestra atribución, se identifica la aplicación y no se agregan funciones de descarga masiva o precarga de áreas.

## Estado de verificación

18/11/2026: `compilar.ps1 -Pruebas` terminó con BUILD SUCCESSFUL; 6 pruebas (GpsFixTest y MapSessionTest) aprobadas, 0 fallas. Lint: 0 errores y 4 advertencias de configuración ya presentes. APK versión 0.2.0 generado en `app/build/outputs/apk/debug/app-debug.apk`.

Verificación nativa realizada en Xiaomi Pad 5: versión instalada 0.2.0 confirmada por ADB. El usuario confirmó la trayectoria verde. Inspección adicional por captura: cartografía OpenStreetMap cargada, marcador azul visible, coordenadas cambiantes, contador de muestras y distancia actualizados; 4 muestras y 10,1 m en la captura de prueba. Se inició y pausó el recorrido simulado mediante ADB. No se observaron cierres de esta aplicación en el registro de fallos consultado. Evidencias: `evidencias/etapa6-mapa-xiaomi.png` y `evidencias/etapa6-trayectoria-xiaomi.png`.

No se verificaron todavía todos los escenarios de pérdida de internet o recreación por orientación. La etapa 7 requiere autorización explícita.
