# Arturito · Android nativo

Aplicación Kotlin + Jetpack Compose. Panel simulado de Control, Misión y Estado en [ETAPA_4.md](ETAPA_4.md); mapa y GPS simulado en [ETAPA_6.md](ETAPA_6.md). Comunicación con el puente, en verificación: [ETAPA_8.md](ETAPA_8.md).

Editor de polígonos, guardado y exportación GeoJSON en [ETAPA_7.md](ETAPA_7.md).

Actualización 0.4.1: [telemetría real, vigencia de datos y alarmas](PRIORIDAD_1.md).

Preparación de etapa 9: [condiciones obligatorias para permitir control](CONDICIONES_CONTROL.md).

## Operación con Arturito 0.8.0

1. En **Conexión**, comprobá el enlace con la Raspberry Pi.
2. En **Control → Modo manual**, seleccioná Móvil, brazo o ambos. El puente
   anuncia la velocidad máxima de tracción. El deslizador de esta instalación
   llega a 25 cm/s.
3. Para usar los joysticks del brazo, completá el homing con el brazo abajo y
   recogido y mantené presionado hasta que informe reposo. Los ceros se fijan
   en los finales de carrera. Al retirarse de ellos queda en J1 3°, J2 6° y
   J3 3°. Después pasa a reposo en J1 3°, J2 17° y J3 4°.
4. En **Visión**, consultá los limones localizados. Las coordenadas XYZ se
   expresan en centímetros respecto a la cámara izquierda. Podés consultar
   las posiciones sin encender la vista de video.
5. En **Modo Recolección**, con el Móvil quieto y el ArUco de 15 cm completo
   en la cámara izquierda, pulsá **Calcular cero del robot**. Para la demo,
   usá la marca original fijada en la maceta. Calculá el cero de nuevo si
   reposicionás el robot antes de iniciar la recolección.
6. **Iniciar recolección** aproxima el Móvil a la parada del arbolito. El
   brazo recoge un limón con el Móvil detenido en esa zona y lo conserva
   en la pinza. **Detener recolección** interrumpe el ensayo. Los eventos y
   el rosbag se guardan en la Pi.

El control y la misión usan el túnel local y los nodos ROS 2 de la Pi.
[Contrato del puente y registro](../robot-bridge/API_V1.md).

## Configuración

- Identificador: `py.edu.fiuna.arturito`.
- Android mínimo: 8.0 (API 26). Compilación y destino: API 36.
- Android Gradle Plugin 9.0.1, Gradle 9.1.0 y Kotlin integrado 2.2.10.
- Compilador Compose 2.2.10 y BOM Compose 2025.08.01.
- Java de ejecución: JBR 25 incluido en Android Studio; bytecode Java/Kotlin 17.

Se fijaron versiones concretas para poder reproducir la compilación. AGP 9.0 admite API 36 y requiere Gradle 9.1.0; esta versión de Gradle admite Java 25.

## Dependencias

- `activity-compose`: conecta la actividad Android con Compose.
- Compose UI: dibuja la interfaz.
- Material 3: colores, textos y componentes visuales.
- `ui-tooling-preview` y `ui-tooling` (solo depuración): vista previa en Android Studio.
- BOM: mantiene compatibles entre sí las versiones de las bibliotecas Compose.

MapLibre y OkHttp se incorporaron en la etapa 6; HTTP/WebSocket con el puente se implementan en la etapa 8. JUnit se utiliza solo en pruebas. El control real y las misiones corresponden a la etapa 9.

## Abrir en Android Studio

1. En la bienvenida, pulsar **Open**. Con otro proyecto abierto: **File > Open**.
2. Seleccionar la carpeta `android-app`, no la carpeta de los proyectos del robot.
3. Si aparece una consulta de confianza, elegir **Trust Project** para este proyecto local.
4. Esperar la sincronización Gradle y la descarga inicial de dependencias.
5. En **File > Settings > Build, Execution, Deployment > Build Tools > Gradle**, usar el wrapper del proyecto y seleccionar como **Gradle JDK** el JBR de Android Studio (`C:\Program Files\Android\Android Studio\jbr`). Java 8 no sirve para compilar este proyecto.
6. Abrir `app/src/main/java/py/edu/fiuna/arturito/ui/RobotApp.kt` y seleccionar **Split** o **Design**. Pulsar **Build & Refresh** si aparece.

La vista previa horizontal muestra las pantallas Control, Misión y Estado. La antigua bienvenida sigue conservada en `WelcomeScreen.kt`. El mapa nativo se verifica al ejecutar la app en Android, no en la vista previa del IDE.

## Compilar desde PowerShell

Desde `android-app`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\compilar.ps1
```

El script selecciona el JDK para su proceso y ejecuta `assembleDebug` y `lintDebug`. No cambia las variables globales de Windows.

- APK: `app/build/outputs/apk/debug/app-debug.apk`.
- Informe de análisis: `app/build/reports/lint-results-debug.html`.
- SDK local: `local.properties` (ruta propia de cada computadora, excluida de git).

## Compilar en Linux (notebook de Héctor)

SDK de línea de comandos en `~/Android/Sdk` (sin Android Studio): `cmdline-tools/latest`, `platform-tools`
(`adb`), `platforms;android-36` y `build-tools;36.0.0`. Java: OpenJDK 21 del sistema. `local.properties` tiene
`sdk.dir=/home/hecvelaz/Android/Sdk`.

```sh
./gradlew :app:assembleDebug :app:testDebugUnitTest :app:lintDebug --console=plain
~/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk   # tablet por USB, depuración activada
```

## Estructura

- `MainActivity.kt`: entrada de la aplicación.
- `ui/screens/WelcomeScreen.kt`: pantalla inicial y vista previa horizontal.
- `ui/theme/Theme.kt`: tema Material 3.
- `res/values/strings.xml`: textos en castellano.
- `app/build.gradle.kts`: configuración Android y dependencias.
- `gradle/wrapper/`: versión reproducible de Gradle con comprobación SHA-256.

Las carpetas de modelos, comunicación y lógica se agregarán cuando tengan una implementación en la etapa correspondiente.

## Referencias oficiales

- https://developer.android.com/build/releases/agp-9-0-0-release-notes
- https://docs.gradle.org/current/userguide/compatibility.html
- https://developer.android.com/jetpack/androidx/releases/compose-kotlin
- https://developer.android.com/develop/ui/compose/bom

## Continuidad

Etapa 2 verificada: compilación, análisis estático, sincronización y vista previa horizontal en Android Studio. La etapa 3 requiere autorización explícita.

Verificado el 18/11/2026: `compilar.ps1` terminó con **BUILD SUCCESSFUL** (`assembleDebug` y `lintDebug`), usando el wrapper y el JBR de Android Studio. El informe registra 0 errores y 4 advertencias: API destino 36, versiones más recientes de Compose/Activity y reglas de copia de seguridad. Se mantienen las versiones fijadas y compatibles de esta base; las copias de seguridad están desactivadas y se declararon reglas para ambas generaciones de Android. No se ocultaron las advertencias. En el primer arranque se observó además un aviso de formato XML de metadatos del SDK, sin impedir la compilación.

Revisión en Android Studio: sincronización finalizada correctamente (registro `onSuccess`, 17:55; primera importación de 5 min 16 s). `WelcomeScreen.kt` abierto en modo dividido; vista previa «Tablet horizontal - WelcomePreview» renderizada con indicador **Up-to-date**, cuatro textos visibles y sin errores de renderizado. No se verificó aún la ejecución en dispositivo.
