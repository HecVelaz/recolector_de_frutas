package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import py.edu.fiuna.arturito.data.BridgeConnection
import py.edu.fiuna.arturito.data.GeofenceStorage
import py.edu.fiuna.arturito.model.FencePoint
import py.edu.fiuna.arturito.model.GeofenceGeoJson
import py.edu.fiuna.arturito.ui.GeofenceSession
import py.edu.fiuna.arturito.ui.components.*

@Composable
fun BridgeMapScreen(bridge: BridgeConnection, fence: GeofenceSession, storage: GeofenceStorage,
    address: String, token: String) {
    var showMap by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    var fit by remember { mutableIntStateOf(0) }
    var reload by remember { mutableIntStateOf(0) }
    val scope = rememberCoroutineScope()
    val data = bridge.telemetry
    val live = bridge.connected && data?.gps != null && data.simulated.not()
    val track = if (live) bridge.track.toList() else emptyList()
    fun edit() {
        showMap = true
        editing = true
        if (fence.vertices.isNotEmpty()) fit++
    }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        if (showMap) {
            Column(Modifier.weight(1.4f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatusLight(if (live) "Posición recibida" else "GPS sin datos", if (live) Signal.Ready else Signal.Off)
                    if (editing) StatusLight("Edición de área", Signal.Notice)
                }
                key(reload) {
                    RobotMap(track, followRobot = live && !editing, centerRequest = 0, onStatus = { status = it },
                        modifier = Modifier.weight(1f).fillMaxWidth(), fence = fence.vertices.toList(),
                        fenceClosed = fence.closed, selectedVertex = fence.selected, editingFence = editing && fence.editing,
                        onFenceTap = { latitude, longitude, hit ->
                            runCatching { fence.tap(FencePoint(latitude, longitude), hit) }
                                .onFailure { fence.message = "Coordenada fuera del rango admitido." }
                        }, fitFenceRequest = fit)
                }
                Row {
                    Text(status, Modifier.weight(1f), style = MaterialTheme.typography.labelSmall)
                    TextButton(onClick = { reload++ }) { Text("Recargar mapa") }
                }
            }
        } else {
            IllustratedPlaceholder(Figure.Map, "Área de trabajo",
                if (live) "La Pi está enviando coordenadas del robot."
                else "Podés planificar la zona mientras el GPS está sin datos.",
                Modifier.weight(1.4f).fillMaxHeight()) {
                Button(onClick = { showMap = true }) { Text("Ver mapa") }
            }
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SectionCard("Límite de trabajo") {
                StatusLight(if (fence.canSave) "Área lista" else "Área por definir", if (fence.canSave) Signal.Ready else Signal.Off)
                Text("La geocerca se usa para planificación.")
                if (!editing) Button(onClick = { edit() }) { Text("Editar área") }
                if (editing) TextButton(onClick = { editing = false; fence.editing = false; fence.selected = null }) {
                    Text("Cerrar editor")
                }
                OutlinedButton(onClick = {
                    scope.launch { bridge.sendFence(address, token, GeofenceGeoJson.encode(fence.document())) }
                }, enabled = bridge.connected && fence.canSave && !bridge.sending) { Text("Enviar área a la Pi") }
                if (bridge.sendStatus.isNotBlank()) Text(bridge.sendStatus)
            }
            if (editing) GeofenceEditor(fence, storage, onEditing = {}, onCenter = { fit++ })
        }
    }
}
