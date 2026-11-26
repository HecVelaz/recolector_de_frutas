package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import py.edu.fiuna.arturito.data.BridgeConnection
import py.edu.fiuna.arturito.data.SensorReading
import py.edu.fiuna.arturito.model.ArmReadings
import py.edu.fiuna.arturito.model.SensorAlert
import py.edu.fiuna.arturito.model.SensorLook
import py.edu.fiuna.arturito.model.sensorLooks
import py.edu.fiuna.arturito.model.mobileDiagnosticRows
import py.edu.fiuna.arturito.model.mobileWording
import py.edu.fiuna.arturito.ui.components.*
import java.util.Locale

private fun SensorReading?.signal(connected: Boolean) =
    if (!connected) Signal.Off else if (this?.status == "fresh") Signal.Ready else Signal.Fault

@Composable
fun ConnectionLights(bridge: BridgeConnection, modifier: Modifier = Modifier) {
    val data = bridge.telemetry
    val linked = bridge.connected && data != null
    val links = listOf(
        Triple("Puente", Figure.Bridge, if (linked) "Conectado" to Signal.Ready else "Sin enlace" to Signal.Off),
        Triple("ROS 2", Figure.Ros, if (data?.source == "ros2" && data.upstreamAvailable) "En línea" to Signal.Ready
            else "Sin confirmar" to if (linked) Signal.Fault else Signal.Off),
        Triple("Móvil", Figure.Drive, data.sourcesLight("base", linked)),
        Triple("Brazo", Figure.Arm, data.sourcesLight("arm", linked)),
    )
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
        for ((label, icon, state) in links) {
            Surface(Modifier.weight(1f), shape = MaterialTheme.shapes.large,
                color = Color.Black, contentColor = Color.White) {
                Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        InstrumentArt(icon, Modifier.size(27.dp), Color.White)
                        Text(label, style = MaterialTheme.typography.titleSmall)
                    }
                    StatusLight(state.first, state.second)
                }
            }
        }
    }
}

private fun py.edu.fiuna.arturito.data.BridgeTelemetry?.sourcesLight(key: String, linked: Boolean): Pair<String, Signal> {
    val reading = this?.sources?.find { it.key == key }
    return (when (reading?.status) {
        "fresh" -> "En línea"
        "stale" -> "Datos vencidos"
        "invalid" -> "Dato inválido"
        else -> "Sin mensajes"
    }) to reading.signal(linked)
}

@Composable
private fun SensorAlertsCard(looks: Map<SensorAlert, SensorLook>, sound: Boolean, onSound: (Boolean) -> Unit) {
    SectionCard("Sensores del Móvil") {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            RobotSensorDiagram(looks, Modifier.weight(1.3f).height(320.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically) {
                    Text(if (sound) "Sonidos de alerta activados" else "Sonidos de alerta silenciados",
                        style = MaterialTheme.typography.titleSmall)
                    Switch(sound, onSound)
                }
                val active = looks.filterValues { it == SensorLook.ACTIVE }.keys.sortedBy { it.ordinal }
                when {
                    looks.values.all { it == SensorLook.NO_DATA } -> StatusLight("Sin lecturas de los sensores", Signal.Off)
                    active.isEmpty() -> StatusLight("Ningún sensor activo", Signal.Ready)
                    else -> for (alert in active) StatusLight(alert.label, if (alert.group <= 1) Signal.Fault else Signal.Notice)
                }
                val missing = looks.filterValues { it == SensorLook.NO_DATA }.keys
                if (missing.isNotEmpty() && missing.size < looks.size)
                    Text("Sin dato (en gris): " + missing.sortedBy { it.ordinal }.joinToString { it.short },
                        style = MaterialTheme.typography.bodySmall)
                Text("Solo avisa: la detención por seta, vuelco, bumpers y el ultrasonido frontal la hace el " +
                    "controlador del robot, con o sin la app.", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun RobotDashboard(bridge: BridgeConnection, alertSound: Boolean = true, onAlertSound: (Boolean) -> Unit = {}) {
    val data = bridge.telemetry
    val battery = data?.batteryVoltage
    val mobileRows = mobileDiagnosticRows(data?.baseState)
    val arm = ArmReadings.decode(data?.armState)
    val alarms = data?.alarmDetails.orEmpty()
    var details by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ConnectionLights(bridge)
        SensorAlertsCard(sensorLooks(data), alertSound, onAlertSound)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SectionCard("Alimentación", Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    InstrumentArt(Figure.Battery, Modifier.size(45.dp))
                    Text(battery?.let { String.format(Locale.getDefault(), "%.2f V", it) } ?: "— V",
                        style = MaterialTheme.typography.headlineMedium)
                }
                StatusLight(when {
                    battery == null -> "Sin lectura"
                    battery < 10.5 -> "Tensión baja"
                    else -> "Tensión disponible"
                }, when {
                    battery == null -> if (bridge.connected) Signal.Fault else Signal.Off
                    battery < 10.5 -> Signal.Fault
                    else -> Signal.Ready
                })
            }
            SectionCard("Tracción", Modifier.weight(1f)) {
                val speed = data?.measuredLinearMps
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    InstrumentArt(Figure.Drive, Modifier.size(45.dp))
                    Text(speed?.let { String.format(Locale.getDefault(), "%.1f cm/s", it * 100) } ?: "— cm/s",
                        style = MaterialTheme.typography.headlineMedium)
                }
                StatusLight(if (speed == null) "Sin odometría" else "Velocidad medida",
                    if (speed != null) Signal.Ready else if (bridge.connected) Signal.Fault else Signal.Off)
            }
            SectionCard("Brazo y pinza", Modifier.weight(1f)) {
                InstrumentArt(Figure.Arm, Modifier.size(45.dp))
                val ready = data?.manualArmReady ?: (arm?.joints?.all { it.zeroKnown } == true)
                StatusLight(when {
                    arm == null -> "Sin lectura"
                    ready -> "Referencia lista"
                    else -> "Homing pendiente"
                }, if (!bridge.connected) Signal.Off else if (ready) Signal.Ready else Signal.Fault)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SectionCard("Sensores de distancia", Modifier.weight(1f)) {
                val ranges = listOf("Frente" to "range_front", "Izquierda" to "range_left", "Derecha" to "range_right",
                    "LiDAR izquierdo" to "range_lidar_left")
                val readings = data?.sources.orEmpty().associateBy { it.key }
                for ((label, id) in ranges) {
                    val reading = readings[id]
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically) {
                        Text(label)
                        val value = reading?.value?.asJsonObject
                        val range = when (value?.get("kind")?.asString) {
                            "distance" -> String.format(Locale.getDefault(), "%.0f cm", value.get("meters").asDouble * 100)
                            "out_of_range" -> "Fuera de alcance"
                            else -> reading?.statusLabel ?: "Sin lectura"
                        }
                        StatusLight(range, reading.signal(bridge.connected))
                    }
                }
                HorizontalDivider()
                val bumper = readings["bumpers"]?.value?.asInt
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically) {
                    Text("Bumpers")
                    StatusLight(when (bumper) {
                        null -> "Sin lectura"
                        0 -> "Sin contacto"
                        else -> "Contacto"
                    }, when {
                        !bridge.connected -> Signal.Off
                        bumper == 0 -> Signal.Ready
                        else -> Signal.Fault
                    })
                }
            }
            SectionCard("Alertas", Modifier.weight(1f)) {
                if (data == null) {
                    StatusLight("Telemetría pausada", Signal.Off)
                } else if (alarms.isEmpty()) {
                    StatusLight("Sin alertas reportadas", Signal.Ready)
                } else for (alarm in alarms) {
                    StatusLight(mobileWording(alarm.message), if (alarm.severity == "critical") Signal.Fault else Signal.Notice)
                }
            }
        }
        OutlinedButton(onClick = { details = !details }) { Text(if (details) "Ocultar lecturas técnicas" else "Ver lecturas técnicas") }
        if (details) {
            SectionCard("Lecturas del Móvil") {
                if (mobileRows.isEmpty()) Text("Sin lecturas recientes del controlador.")
                for ((label, value) in mobileRows) DetailRow(label, value)
            }
            SectionCard("Articulaciones y servos") {
                if (arm == null) Text("Sin lecturas recientes del brazo.")
                arm?.joints?.forEachIndexed { i, joint ->
                    DetailRow("J${i + 1}", String.format(Locale.getDefault(), "%.1f° · %s · final de carrera %s",
                        joint.angleDegrees, joint.state.label, if (joint.limitActive) "activo" else "libre"))
                }
                if (arm != null) {
                    DetailRow("Pinza", arm.gripperPulseUs?.let { "$it µs" } ?: "Sin pulso")
                    DetailRow("Muñeca", arm.wristPulseUs?.let { "$it µs" } ?: "Sin pulso")
                }
            }
            SectionCard("Datos de los sensores") {
                for (reading in data?.sources.orEmpty()) {
                    if (reading.key == "base" || reading.key == "arm") continue
                    HorizontalDivider()
                    DetailRow(reading.label, reading.statusLabel)
                    Text(sensorValue(reading), style = MaterialTheme.typography.bodySmall)
                    reading.reason?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
            }
        }
    }
}

@Composable
fun LiveMissionScreen(onMap: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        IllustratedPlaceholder(Figure.Mission, "Planificar recolección",
            "Prepará el área de trabajo en el mapa. El robot sigue disponible para mando manual.",
            Modifier.weight(1.15f).fillMaxHeight()) {
            Button(onClick = onMap) { Text("Abrir mapa de trabajo") }
        }
        SectionCard("Preparación de la misión", Modifier.weight(1f).fillMaxHeight()) {
            StatusLight("Autonomía no habilitada", Signal.Off)
            DetailRow("Área de trabajo", "Se configura en Mapa")
            DetailRow("Posición del robot", "Requiere localización validada")
            DetailRow("Modo actual", "Mando manual")
        }
    }
}
