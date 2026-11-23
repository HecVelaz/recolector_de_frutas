package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import py.edu.fiuna.arturito.data.BridgeConnection
import py.edu.fiuna.arturito.data.SensorReading
import java.util.Locale
import py.edu.fiuna.arturito.ui.components.*

@Composable
fun ConnectionScreen(bridge: BridgeConnection, enabled: Boolean, address: String, token: String,
    onAddress: (String) -> Unit, onToken: (String) -> Unit, onConnect: () -> Unit,
    onDisconnect: () -> Unit) {
    val connected = enabled && bridge.connected
    val colors = MaterialTheme.colorScheme
    val accessInk = if (connected) Color.White else colors.onSurface
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ConnectionLights(bridge)
        SectionCard("Acceso al robot", colors = CardDefaults.cardColors(
            containerColor = if (connected) Color(0xFF135639) else colors.surface, contentColor = accessInk)) {
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                InstrumentArt(Figure.Link, Modifier.size(48.dp), ink = accessInk)
                Column(Modifier.weight(1f)) {
                    Text(if (enabled) bridge.status else "Conexión pausada", style = MaterialTheme.typography.titleMedium)
                    Text(if (enabled) "Para cambiar la dirección: Desconectar" else "Tablet → Raspberry Pi por Tailscale (o túnel USB)",
                        color = if (connected) accessInk.copy(alpha = .84f) else colors.onSurfaceVariant)
                }
                if (enabled) {
                    OutlinedButton(onClick = onDisconnect,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = accessInk),
                        border = BorderStroke(1.dp, if (connected) Color.White.copy(alpha = .72f) else colors.outline)) {
                        Text("Desconectar")
                    }
                }
            }
            if (!enabled) {
                OutlinedTextField(address, onAddress, label = { Text("Dirección del puente") },
                    placeholder = { Text("http://100.116.96.71:18006") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth())
                OutlinedTextField(token, onToken, label = { Text("Clave de conexión") }, singleLine = true,
                    visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                Button(onClick = onConnect, enabled = address.isNotBlank()) { Text("Conectar al robot") }
            }
        }
    }
}

@Composable
fun ControlPreparationScreen(bridge: BridgeConnection, onPrepare: (Boolean) -> Unit,
    onConfirm: () -> Unit, onStop: () -> Unit, heldDirection: py.edu.fiuna.arturito.model.ManualDirection?,
    onHeld: (py.edu.fiuna.arturito.model.ManualDirection, Boolean) -> Unit) {
    var physicalReady by remember { mutableStateOf(false) }
    val telemetry = bridge.telemetry
    val gate = bridge.controlStatus ?: telemetry?.controlGate
    val simulated = telemetry?.simulatedBaseOutput != null
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionCard("Preparar control · ensayo sin potencia") {
            Badge("NO ENVÍA COMANDOS AL ROBOT", warning = true)
            Text("Esta versión prueba autenticación, condiciones, propietario exclusivo, confirmación y parada. La salida ROS está ausente.")
            DetailRow("Puente", if (bridge.connected) "Conectado" else "No conectado")
            DetailRow("Origen", when {
                simulated -> "Simulación del móvil"
                telemetry?.source == "ros2" -> "ROS 2 real"
                else -> "No apto"
            })
            DetailRow("Móvil", telemetry?.sources?.find { it.key == "base" }?.statusLabel ?: "Sin confirmar")
            DetailRow("Brazo", telemetry?.sources?.find { it.key == "arm" }?.statusLabel ?: "Sin confirmar")
            DetailRow("Batería", telemetry?.batteryVoltage?.let { "$it V" } ?: "Sin datos")
            CircleOption("Confirmo que la potencia de los motores está desconectada", physicalReady,
                { physicalReady = it })
            Button(onClick = { onPrepare(physicalReady) },
                enabled = bridge.connected && telemetry?.controlDryRun == true && physicalReady) {
                Text("Preparar sesión")
            }
            OutlinedButton(onClick = onConfirm, enabled = bridge.connected && gate?.state == "ready") {
                Text("Confirmar sesión")
            }
            Button(onClick = onStop, colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.error, contentColor = MaterialTheme.colorScheme.onError)) {
                Text("PARAR Y BLOQUEAR")
            }
        }
        if (simulated) {
            SectionCard("Mando simulado del móvil") {
                Text("Mantené presionada una flecha para mover el móvil.")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    for (direction in py.edu.fiuna.arturito.model.ManualDirection.entries) {
                        DirectionButton(direction, bridge.connected && gate?.state in listOf("enabled", "active") &&
                            (heldDirection == null || direction == heldDirection), onHeld)
                    }
                }
                val velocity = gate?.simulatedBaseOutput ?: telemetry?.simulatedBaseOutput
                DetailRow("Velocidad simulada", "${velocity?.linear ?: 0.0} m/s")
                DetailRow("Giro simulado", "${velocity?.angular ?: 0.0} rad/s")
            }
        }
        SectionCard("Resultado de la puerta") {
            DetailRow("Estado", gate?.state ?: "Sin evaluar")
            DetailRow("Listo", if (gate?.ready == true) "Sí" else "No")
            DetailRow("Modo", if (telemetry?.controlDryRun == true) "Ensayo en seco" else "Deshabilitado")
            if (gate?.reasons?.isNotEmpty() == true) {
                Text("Bloqueos detectados:", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                gate.reasons.forEach { Text("• ${controlReason(it)}") }
            }
            Text("Una desconexión, la app en segundo plano o 250 ms sin heartbeat revocan la sesión. Nunca se reanuda automáticamente.")
        }
    }
}

private fun controlReason(code: String) = when (code) {
    "CONTROL_DISABLED" -> "Ensayo de control deshabilitado en el puente"
    "APP_NOT_FOREGROUND" -> "La app no está en primer plano"
    "PHYSICAL_CHECK_PENDING" -> "Falta confirmar la condición física"
    "NOT_REAL_ROS_SOURCE" -> "El origen no es ROS 2 real"
    "ROS_UNAVAILABLE" -> "ROS 2 no está disponible"
    "BATTERY_TOO_LOW_OR_UNKNOWN" -> "Batería insuficiente o desconocida"
    "ARM_NOT_HOMED" -> "Brazo sin cero confirmado"
    "ARM_BUSY_OR_INVALID" -> "Brazo ocupado o en estado inválido"
    "REQUEST_FAILED" -> "No se pudo completar la solicitud"
    else -> code.replace('_', ' ').lowercase().replaceFirstChar { it.uppercase() }
}

internal fun sensorValue(reading: SensorReading): String {
    val value = reading.value ?: return "Sin valor vigente"
    fun number(n: Double) = String.format(Locale.getDefault(), "%.2f", n)
    return when (reading.key) {
        "battery" -> "${number(value.asDouble)} V · sin porcentaje estimado"
        "bumpers" -> "Máscara de contactos: ${value.asInt} (0 = ninguno)"
        "arm" -> value.asString
        "imu" -> {
            val a = value.asJsonObject.getAsJsonArray("acceleration_m_s2").joinToString(", ") { number(it.asDouble) }
            val w = value.asJsonObject.getAsJsonArray("angular_velocity_rad_s").joinToString(", ") { number(it.asDouble) }
            "Aceleración XYZ: $a m/s²\nVelocidad angular XYZ: $w rad/s"
        }
        "odom" -> value.asJsonObject.let { "x: ${number(it.get("x_m").asDouble)} m · y: ${number(it.get("y_m").asDouble)} m\nVelocidad: ${number(it.get("linear_m_s").asDouble)} m/s · giro: ${number(it.get("angular_rad_s").asDouble)} rad/s" }
        else -> if (reading.key.startsWith("range_")) value.asJsonObject.let {
            if (it.get("kind").asString == "out_of_range") "Ningún eco dentro del alcance de medición"
            else "${number(it.get("meters").asDouble)} m"
        } else value.toString()
    }
}
