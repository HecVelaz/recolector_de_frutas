package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import py.edu.fiuna.arturito.model.DemoGpsRoute
import py.edu.fiuna.arturito.ui.MapSession
import py.edu.fiuna.arturito.ui.components.*
import java.util.Locale
import py.edu.fiuna.arturito.ui.GeofenceSession
import py.edu.fiuna.arturito.data.GeofenceStorage
import py.edu.fiuna.arturito.model.FencePoint

@Composable
fun MapScreen(session: MapSession, emergency: Boolean, fence: GeofenceSession, storage: GeofenceStorage) {
    var status by remember { mutableStateOf("Preparando mapa…") }
    var reload by remember { mutableIntStateOf(0) }
    var editor by remember { mutableStateOf(false) }
    var fitFence by remember { mutableIntStateOf(0) }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(if (editor) "Geocerca: puntos rojos · seleccionado violeta · mapa desplazable"
                else "Posición ficticia cerca de FIUNA · arrastrá y pellizcá para explorar", style = MaterialTheme.typography.bodySmall)
            Surface(Modifier.weight(1f).fillMaxWidth(), shape = MaterialTheme.shapes.medium) {
                key(reload) {
                    RobotMap(session.track.toList(), session.followRobot, session.centerRequest,
                        onStatus = { status = it }, modifier = Modifier.fillMaxSize(),
                        fence = fence.vertices.toList(), fenceClosed = fence.closed, selectedVertex = fence.selected,
                        editingFence = editor && fence.editing, onFenceTap = { lat, lon, hit ->
                            runCatching { fence.tap(FencePoint(lat, lon), hit) }.onFailure { fence.message = "Coordenada fuera del rango admitido." }
                        }, fitFenceRequest = fitFence)
                }
            }
            Text(status, style = MaterialTheme.typography.labelSmall)
            Text("Punto azul: robot simulado · línea gris: trayectoria. Cartografía: © OpenStreetMap contributors.",
                style = MaterialTheme.typography.bodySmall)
        }
        Column(Modifier.width(264.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ConsoleOption(selected = !editor, onClick = { editor = false; fence.editing = false; fence.selected = null }, label = { Text("GPS") })
                ConsoleOption(selected = editor, onClick = {
                    editor = true; session.playing = false; session.followRobot = false
                    if (fence.vertices.isNotEmpty()) fitFence++
                }, label = { Text("Geocerca") })
            }
            if (editor) GeofenceEditor(fence, storage,
                onEditing = { session.playing = false; session.followRobot = false },
                onCenter = { session.followRobot = false; fitFence++ })
            else {
            SectionCard("GPS del robot") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    InstrumentArt(Figure.Map, Modifier.size(39.dp))
                    StatusLight("Posición simulada", Signal.Notice)
                }
                Text(String.format(Locale.US, "Latitud: %.6f°\nLongitud: %.6f°", session.position.latitude, session.position.longitude))
                DetailRow("Muestras", "${session.track.size}")
                DetailRow("Distancia", String.format(Locale.US, "%.1f m", session.distanceMeters))
            }
            SectionCard("Recorrido de ejemplo") {
                Button(onClick = { session.playing = !session.playing },
                    enabled = !emergency && session.index < DemoGpsRoute.steps, modifier = Modifier.fillMaxWidth()) {
                    Text(if (session.playing) "Pausar recorrido" else "Simular recorrido")
                }
                OutlinedButton(onClick = { session.reset() }, modifier = Modifier.fillMaxWidth()) { Text("Reiniciar trayectoria") }
                OutlinedButton(onClick = { session.center() }, modifier = Modifier.fillMaxWidth()) { Text("Centrar robot") }
                CircleOption("Seguir robot", session.followRobot, { session.followRobot = it })
                Text(when {
                    emergency -> "Recorrido pausado por emergencia simulada."
                    session.index == DemoGpsRoute.steps -> "Recorrido finalizado. Reiniciá para repetirlo."
                    session.playing -> "Actualizando cada segundo. No mueve el robot."
                    else -> "Recorrido pausado."
                }, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { reload++ }) { Text("Recargar mapa") }
                Text("El mapa base necesita internet. No hay descarga de mapas sin conexión.", style = MaterialTheme.typography.bodySmall)
            }
            }
        }
    }
}
