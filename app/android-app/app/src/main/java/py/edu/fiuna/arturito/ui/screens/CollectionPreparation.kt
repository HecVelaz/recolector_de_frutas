package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.Locale
import py.edu.fiuna.arturito.data.CollectionStatus
import py.edu.fiuna.arturito.data.NavigationOrigin
import py.edu.fiuna.arturito.data.RobotCamera
import py.edu.fiuna.arturito.data.StereoReading
import py.edu.fiuna.arturito.ui.components.DetailRow
import py.edu.fiuna.arturito.ui.components.SectionCard
import py.edu.fiuna.arturito.ui.components.Signal
import py.edu.fiuna.arturito.ui.components.StatusLight

@Composable
fun CollectionPreparation(origin: NavigationOrigin?, stereo: StereoReading?, armReady: Boolean,
    canCapture: Boolean, capturing: Boolean, onCapture: () -> Unit, onMap: () -> Unit,
    homingStatus: String?, mission: CollectionStatus?, missionRequested: Boolean, canStart: Boolean,
    onStart: () -> Unit, onStop: () -> Unit, lemons: Int = 1, onLemons: (Int) -> Unit = {},
    address: String = "", token: String = "", video: Boolean = false,
    canReturn: Boolean = false, onReturn: () -> Unit = {},
    homeControl: @Composable () -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionCard("Cero del robot", Modifier.weight(1f)) {
            Text("Dejá el Móvil quieto con el limonero a la vista de la cámara izquierda (a 40–95 cm). " +
                "El cero es la posición actual respecto del limón más cercano.")
            Button(onClick = onCapture, enabled = canCapture) {
                Text(if (capturing) "Midiendo el limón…" else "Calcular cero con el limón")
            }
            if (origin?.used == true) StatusLight("Ese limón ya se cosechó: calculá un cero nuevo", Signal.Notice)
            if (origin?.hasLemon == false) StatusLight("Sin limón a la vista: al iniciar lo busca girando ±25°", Signal.Notice)
            if (origin != null) {
                if (origin.hasLemon) {
                    DetailRow("Limón más cercano", "a ${cm(origin.distanceM)} cm del brazo")
                    DetailRow("Respecto del brazo",
                        "${cm(-origin.lemonXmm / 1000)} cm a la izquierda · ${cm(origin.lemonYmm / 1000)} cm adelante")
                    DetailRow("Altura del limón", "~${cm(origin.lemonHeightM)} cm del piso")
                    DetailRow("Limones a la vista", "${origin.lemonsSeen}")
                }
                origin.displacement?.let { delta ->
                    DetailRow("Desplazamiento desde cero", "X ${cm(delta.xM)} · Y ${cm(delta.yM)} cm")
                }
            }
        }
        SectionCard("Brazo", Modifier.weight(1f)) {
            StatusLight(homingStatus ?: if (armReady) "Ceros confirmados" else "Buscar finales de carrera",
                if (armReady && homingStatus == null) Signal.Ready else Signal.Notice)
            homeControl()
            Text("El homing fija el cero de J1, J2 y J3. El brazo termina recogido en reposo.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
    SectionCard("Visión estéreo", Modifier.fillMaxWidth(), compact = true) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1.4f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                CameraFeed(address, token, RobotCamera.CENTER, video, Modifier.fillMaxWidth().aspectRatio(4f / 3f))
                Text(RobotCamera.CENTER.description, style = MaterialTheme.typography.bodySmall)
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                StereoTargets(stereo)
            }
        }
    }
    SectionCard("Recolección del arbolito", Modifier.fillMaxWidth(), compact = true) {
        mission?.let { status ->
            DetailRow("Estado", when (status.state) {
                "BUSCANDO" -> "Buscando"
                "NAVEGANDO" -> "Navegando"
                "INTERVINIENDO" -> "Recogiendo"
                "RECUPERACION" -> "Requiere revisión"
                "FINALIZADO" -> "Finalizado"
                else -> "Inactivo"
            })
            Text(status.message)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Limones a la canasta")
            OutlinedButton(onClick = { onLemons(lemons - 1) }, enabled = !missionRequested && lemons > 1) { Text("−") }
            Text("$lemons", style = MaterialTheme.typography.titleMedium)
            OutlinedButton(onClick = { onLemons(lemons + 1) }, enabled = !missionRequested && lemons < MAX_LEMONS) { Text("+") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (missionRequested) Button(onClick = onStop) { Text("Detener") }
            else {
                Button(onClick = onStart, enabled = canStart) { Text("Iniciar recolección") }
                OutlinedButton(onClick = onReturn, enabled = canReturn) { Text("Volver al cero") }
            }
        }
    }
    Button(onClick = onMap) { Text("Abrir mapa de trabajo") }
}

@Composable
fun StereoTargets(stereo: StereoReading?) {
    val targets = stereo?.lemons.orEmpty()
    StatusLight(when (stereo?.status) {
        "located" -> "Limones localizados · ${targets.size}"
        "searching" -> "Estéreo activo · buscando limones"
        else -> "Sin profundidad reciente"
    }, if (stereo?.status in listOf("located", "searching")) Signal.Ready else Signal.Off)
    if (targets.isNotEmpty()) {
        Text("Coordenadas respecto a la cámara izquierda", style = MaterialTheme.typography.bodySmall)
        targets.take(4).forEachIndexed { index, point ->
            DetailRow("Limón ${index + 1}", "X ${cm(point.xM)} · Y ${cm(point.yM)} · Z ${cm(point.zM)} cm")
        }
    }
}

/** Igual que MAX_LEMONS del puente (collection_mission.py). */
private const val MAX_LEMONS = 5

private fun cm(meters: Double) = String.format(Locale.getDefault(), "%.1f", meters * 100)
