# Etapa 4 · Primera interfaz

Panel nativo para tablet horizontal. No utiliza red ni se conecta con ROS 2 o motores.

## Qué se agregó

- Navegación lateral: Control, Misión y Estado; Atrás vuelve a Control.
- Control: cuatro flechas por pulsación mantenida, botón Parar, estado y resumen de datos de ejemplo.
- Misión: selección de dos escenarios de demostración, inicio, cancelación y progreso automático (unos 20 segundos).
- Estados: INACTIVO, TELEOP, NAVEGANDO, BUSCANDO, INTERVINIENDO, RECUPERACION, FINALIZADO y EMERGENCIA.
- Estado: batería, comunicaciones, sensores, actuadores, alarma simulada y últimos 30 eventos de la sesión.
- Emergencia simulada visible en las tres pantallas; interrumpe la demostración y requiere restablecer desde Estado.
- Al pasar la app a segundo plano se detiene la simulación; al cambiar de pantalla se libera el movimiento manual.
- La misión bloquea los controles manuales. Los dos escenarios usan la misma secuencia de estados de demostración; no son planificadores de tareas reales.

El indicador SIMULACIÓN permanece visible. Batería y diagnóstico son ejemplos fijos. El progreso es un temporizador de interfaz, no mide una misión real. Los eventos son locales en memoria; no son rosbags ni un registro persistente.

## Archivos

- `model/RobotState.kt`: estados y escenarios de ejemplo.
- `ui/RobotApp.kt`: navegación y comportamiento de la simulación.
- `ui/screens/ConsoleScreens.kt`: tres pantallas.
- `ui/components/ConsoleComponents.kt`: tarjetas, etiquetas, filas y controles reutilizables.
- `MainActivity.kt`: abre el nuevo panel. La bienvenida de etapa 2 se conservó.

Rutas relativas a `app/src/main/java/py/edu/fiuna/arturito/`.

No se agregaron dependencias. Se reutilizan Compose y Material 3; el ciclo de vida ya está disponible mediante las dependencias existentes.

## Cómo revisar en Android Studio

1. Abrir `RobotApp.kt` (Ctrl+Shift+N y buscar el nombre).
2. Seleccionar Design o Split arriba a la derecha.
3. Actualizar la vista previa si indica Out of date. Se muestran Control, Misión y Estado en formato tablet 1280 × 800 dp.
4. En el menú de tres puntos de Control, elegir **Start Interactive Mode**. Esta opción prueba la interfaz dentro del IDE; no instala en la tablet.
5. Entrar en Misión e iniciar la simulación. El porcentaje aumenta hasta Finalizado.
6. Durante otra misión, pulsar Cancelar: vuelve a Inactivo y el porcentaje deja de avanzar.
7. Pulsar Emergencia simulada: pasa a Estado, indica EMERGENCIA y muestra la alarma. Restablecer devuelve a Inactivo sin reanudar la misión.
8. Volver a Control y mantener una flecha: indica TELEOP; al soltar vuelve a Inactivo. Parar detiene la simulación.

La prueba táctil, multitáctil, segundo plano y cambios de orientación en la Xiaomi corresponde a la etapa 5. La interfaz muestra una indicación para girar la tablet cuando la ventana es demasiado estrecha.

## Verificaciones

- ADB detectó la Xiaomi Pad 5 como dispositivo autorizado.
- `compilar.ps1`: assembleDebug y lintDebug, BUILD SUCCESSFUL, sin errores; permanecen las cuatro advertencias de configuración ya documentadas.
- Las tres vistas previas renderizan con indicador Up-to-date.
- Vista interactiva: navegación, inicio y avance de misión, ciclo completo a FINALIZADO (100 %), cancelación a INACTIVO (57 %), alarma de emergencia y restablecimiento comprobados.

La etapa 5 (instalar y probar en la tablet) requiere confirmación de esta etapa y autorización explícita.
