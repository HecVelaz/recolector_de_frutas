package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.geometry.Offset
import py.edu.fiuna.arturito.model.*
import py.edu.fiuna.arturito.ui.components.*

@Composable
fun ControlScreen(state: RobotState, direction: ManualDirection?, running: Boolean,
                  onHeld: (ManualDirection, Boolean) -> Unit, onStop: () -> Unit, onMission: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        SectionCard("Movimiento manual", Modifier.weight(1.25f).fillMaxHeight()) {
            Text("Arrastrá el joystick para simular el avance o el giro. Soltalo para detenerte.",
                style = MaterialTheme.typography.bodyMedium)
            Column(Modifier.weight(1f).fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp, Alignment.CenterVertically)) {
                val enabled = !running && state != RobotState.EMERGENCIA
                var last by remember { mutableStateOf<ManualDirection?>(null) }
                Joystick("Joystick de simulación", enabled, Modifier.size(170.dp)) { point ->
                    val next = when {
                        point == Offset.Zero -> null
                        kotlin.math.abs(point.y) >= kotlin.math.abs(point.x) ->
                            if (point.y < 0) ManualDirection.FORWARD else ManualDirection.BACKWARD
                        point.x < 0 -> ManualDirection.LEFT
                        else -> ManualDirection.RIGHT
                    }
                    if (next != last) {
                        last?.let { onHeld(it, false) }
                        next?.let { onHeld(it, true) }
                        last = next
                    }
                }
                Button(onClick = onStop) { Text("Parar") }
            }
            StatusLight(direction?.label ?: "Movimiento detenido", if (direction == null) Signal.Off else Signal.Ready)
            if (running) Text("La misión tiene el control. Cancelala para usar las flechas.", color = MaterialTheme.colorScheme.primary)
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SectionCard("Resumen del robot") {
                DetailRow("Estado", state.label)
                DetailRow("Batería de ejemplo", "82 % · 11,8 V")
                DetailRow("Velocidad simulada", if (direction != null) "0,15 m/s máx." else "0,00 m/s")
                DetailRow("Comunicaciones", "Sin enlace real")
            }
            SectionCard("Recolección autónoma") {
                Text("Elegí una misión y observá sus etapas con datos de ejemplo.")
                Button(onClick = onMission, modifier = Modifier.fillMaxWidth()) { Text("Ir a misión") }
            }
            SectionCard("Entorno de prueba") {
                InstrumentArt(Figure.Drive, Modifier.size(50.dp))
                StatusLight("Simulación", Signal.Notice)
                Text("Los botones modifican únicamente esta interfaz. No hay órdenes hacia motores ni ROS 2.",
                    style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
fun MissionScreen(state: RobotState, selectedMission: Int, progress: Float, running: Boolean,
                  onSelect: (Int) -> Unit, onStart: () -> Unit, onCancel: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        SectionCard("Seleccionar misión", Modifier.weight(1f).fillMaxHeight()) {
            demoMissions.forEachIndexed { index, name ->
                OutlinedCard(onClick = { onSelect(index) }, enabled = !running && state != RobotState.EMERGENCIA,
                    modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = selectedMission == index, onClick = null)
                        Column {
                            Text(name, fontWeight = FontWeight.Medium)
                            Text(if (index == 0) "Aproximación, búsqueda y agarre" else "Recorrido de inspección de ejemplo",
                                style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            Spacer(Modifier.weight(1f))
            Button(onClick = onStart, enabled = !running && state != RobotState.EMERGENCIA,
                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) { Text("Iniciar simulación") }
            OutlinedButton(onClick = onCancel, enabled = running,
                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) { Text("Cancelar misión") }
        }
        SectionCard("Progreso de la misión", Modifier.weight(1.2f).fillMaxHeight()) {
            Row(horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically) {
                InstrumentArt(Figure.Mission, Modifier.size(42.dp))
                StatusLight(state.label, if (running) Signal.Ready else Signal.Off)
            }
            Text("${(progress * 100).toInt()} %", style = MaterialTheme.typography.displaySmall)
            LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
            Text(demoMissions[selectedMission], style = MaterialTheme.typography.titleMedium)
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf("Navegar a la zona", "Buscar el objetivo", "Recoger la fruta", "Volver a la posición inicial")
                    .forEachIndexed { index, label ->
                        StatusLight(label, if (running && index == (progress * 4).toInt()) Signal.Ready else Signal.Off)
                    }
            }
            Text(when {
                state == RobotState.EMERGENCIA -> "Simulación interrumpida por emergencia. Restablecé desde Estado."
                state == RobotState.FINALIZADO -> "Misión de ejemplo finalizada. Podés iniciar otra simulación."
                running -> "Secuencia automática de demostración · sin conexión al robot."
                else -> "Seleccioná una misión y pulsá Iniciar simulación."
            }, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun StatusScreen(state: RobotState, events: List<String>, onReset: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SectionCard("Diagnóstico · datos simulados") {
                DetailRow("Batería", "82 % · 11,8 V")
                StatusLight("Raspberry Pi sin enlace", Signal.Off)
                StatusLight("ESP32 del móvil y del brazo sin enlace", Signal.Off)
                DetailRow("Sensores de distancia", "Ejemplo: libres")
                DetailRow("IMU / encoders", "Ejemplo: disponibles")
                DetailRow("Brazo / pinza", "Ejemplo: en reposo")
                DetailRow("GPS", "Sin datos reales")
            }
            SectionCard("Alarmas") {
                Badge(if (state == RobotState.EMERGENCIA) "EMERGENCIA SIMULADA" else "Sin alarmas simuladas",
                    warning = state == RobotState.EMERGENCIA)
                Text("La seguridad física depende del robot. Esta pantalla solo demuestra estados.",
                    style = MaterialTheme.typography.bodyMedium)
                if (state == RobotState.EMERGENCIA) {
                    Button(onClick = onReset) { Text("Restablecer simulación") }
                }
            }
        }
        SectionCard("Eventos de esta sesión", Modifier.weight(1f).fillMaxHeight()) {
            Text("Registro local de demostración; se borra al cerrar la aplicación.", style = MaterialTheme.typography.bodySmall)
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                events.asReversed().forEach { Text("• $it", style = MaterialTheme.typography.bodyMedium) }
            }
        }
    }
}
