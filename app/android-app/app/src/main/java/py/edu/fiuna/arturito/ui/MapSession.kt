package py.edu.fiuna.arturito.ui

import androidx.compose.runtime.*
import py.edu.fiuna.arturito.model.DemoGpsRoute
import py.edu.fiuna.arturito.model.GpsFix

/** Estado en memoria compartido entre pantallas; en esta etapa recibe solo datos de ejemplo. */
class MapSession {
    var playing by mutableStateOf(false)
    var index by mutableIntStateOf(0)
        private set
    var centerRequest by mutableIntStateOf(0)
        private set
    var followRobot by mutableStateOf(true)
    val track = mutableStateListOf(DemoGpsRoute.point(0, System.currentTimeMillis()))
    val position: GpsFix get() = track.last()
    val distanceMeters: Double get() = track.zipWithNext().sumOf { (a, b) -> a.distanceTo(b) }

    fun tick() {
        if (!playing || index >= DemoGpsRoute.steps) { playing = false; return }
        index++
        accept(DemoGpsRoute.point(index, System.currentTimeMillis()))
        if (index == DemoGpsRoute.steps) playing = false
    }

    /** Punto de entrada para datos GPS futuros: valida orden temporal y limita la memoria. */
    fun accept(fix: GpsFix) {
        if (fix.timestampMillis < position.timestampMillis) return
        track.add(fix)
        if (track.size > 600) track.removeAt(0)
    }

    fun center() { centerRequest++; followRobot = true }
    fun reset() {
        playing = false; index = 0
        track.clear(); track.add(DemoGpsRoute.point(0, System.currentTimeMillis()))
        center()
    }
}
