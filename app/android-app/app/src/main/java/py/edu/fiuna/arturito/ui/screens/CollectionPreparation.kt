package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.Locale
import py.edu.fiuna.arturito.data.CollectionStatus
import py.edu.fiuna.arturito.data.NavigationOrigin
import py.edu.fiuna.arturito.data.StereoReading
import py.edu.fiuna.arturito.ui.components.DetailRow
import py.edu.fiuna.arturito.ui.components.SectionCard
import py.edu.fiuna.arturito.ui.components.Signal
import py.edu.fiuna.arturito.ui.components.StatusLight

@Composable
fun CollectionPreparation(origin: NavigationOrigin?, stereo: StereoReading?, armReady: Boolean,
    canCapture: Boolean, capturing: Boolean, onCapture: () -> Unit, onMap: () -> Unit,
    homingStatus: String?, mission: CollectionStatus?, missionRequested: Boolean, canStart: Boolean,
    onStart: () -> Unit, onStop: () -> Unit, homeControl: @Composable () -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionCard("Cero del robot", Modifier.weight(1f)) {
            Text("Dejá el Móvil quieto y mostrá el ArUco de 15 cm a la cámara izquierda.")
            Button(onClick = onCapture, enabled = canCapture) {
                Text(if (capturing) "Midiendo la marca…" else "Calcular cero del robot")
            }
            if (origin != null) {
                DetailRow("Marca", "ArUco ${origin.markerId} · ${cm(origin.distanceM)} cm")
                DetailRow("Posición inicial respecto a la marca",
                    "X ${cm(origin.atMarker.xM)} · Y ${cm(origin.atMarker.yM)} cm")
                DetailRow("Rumbo respecto a la marca", "${origin.atMarker.yawDegrees.toInt()}°")
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
        StereoTargets(stereo)
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
        if (missionRequested) Button(onClick = onStop) { Text("Detener recolección") }
        else Button(onClick = onStart, enabled = canStart) { Text("Iniciar recolección") }
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

private fun cm(meters: Double) = String.format(Locale.getDefault(), "%.1f", meters * 100)
