package py.edu.fiuna.arturito.ui

import androidx.compose.runtime.*
import py.edu.fiuna.arturito.model.*

data class FenceSnapshot(val points: List<FencePoint>, val closed: Boolean, val name: String)

class GeofenceSession {
    val vertices = mutableStateListOf<FencePoint>()
    var closed by mutableStateOf(false)
        private set
    var name by mutableStateOf("Zona de operación")
    var editing by mutableStateOf(false)
    var selected by mutableStateOf<Int?>(null)
    var message by mutableStateOf("Activá Editar puntos y tocá el mapa para comenzar.")
    var savedJson by mutableStateOf<String?>(null)
        private set
    private val undo = mutableStateListOf<FenceSnapshot>()
    val canUndo: Boolean get() = undo.isNotEmpty()
    val validation: FenceValidation get() = GeofenceGeometry.validate(vertices)
    val canSave: Boolean get() = closed && validation.valid && name.isNotBlank() && name.length <= 40
    val savedMatches: Boolean get() = canSave && savedJson == GeofenceGeoJson.encode(document())
    private fun snapshot() = FenceSnapshot(vertices.toList(), closed, name)
    private fun rememberChange() { undo.add(snapshot()); if (undo.size > 64) undo.removeAt(0) }
    fun document() = FenceDocument(name, vertices.toList())

    fun tap(point: FencePoint, hit: Int?) {
        if (!editing) return
        if (hit != null && hit in vertices.indices) { selected = hit; message = "Punto ${hit + 1}: tocá su nueva ubicación o eliminá el punto."; return }
        val selection = selected
        if (closed && selection == null) { message = "Seleccioná un vértice para moverlo, o abrí el polígono para agregar puntos."; return }
        val candidate = vertices.toMutableList()
        if (selection != null && selection in candidate.indices) candidate[selection] = point else candidate.add(point)
        val check = GeofenceGeometry.validate(candidate, closed)
        if (!check.valid) { message = check.error.orEmpty(); return }
        rememberChange(); vertices.clear(); vertices.addAll(candidate); selected = null
        message = if (selection != null) "Punto movido. Guardá para conservar los cambios." else "Punto ${vertices.size} agregado."
    }
    fun close() {
        val check = validation
        if (!check.valid) { message = check.error.orEmpty(); return }
        rememberChange(); closed = true; selected = null; editing = false
        message = "Polígono válido. Guardalo o exportalo en GeoJSON."
    }
    fun reopen() { rememberChange(); closed = false; editing = true; selected = null; message = "Polígono abierto para agregar puntos." }
    fun deleteSelected() {
        val index = selected ?: return
        if (index !in vertices.indices) return
        val candidate = vertices.toMutableList().also { it.removeAt(index) }
        val remainsClosed = closed && candidate.size >= 3
        val check = GeofenceGeometry.validate(candidate, remainsClosed)
        if (!check.valid) { message = check.error.orEmpty(); return }
        rememberChange(); vertices.clear(); vertices.addAll(candidate); closed = remainsClosed; selected = null
        message = "Punto eliminado."
    }
    fun undo() {
        if (undo.isEmpty()) return
        val previous = undo.removeAt(undo.lastIndex)
        vertices.clear(); vertices.addAll(previous.points); closed = previous.closed; name = previous.name; selected = null
        message = "Último cambio deshecho."
    }
    fun clear() { rememberChange(); vertices.clear(); closed = false; selected = null; message = "Borrador vacío. La copia guardada se conserva hasta guardar otra." }
    fun load(document: FenceDocument, initial: Boolean = false) {
        require(GeofenceGeometry.validate(document.vertices).valid)
        if (!initial) rememberChange()
        vertices.clear(); vertices.addAll(document.vertices); name = document.name; closed = true; editing = false; selected = null
        savedJson = GeofenceGeoJson.encode(document); message = "Geocerca guardada cargada. Sin enviar al robot."
    }
    fun markSaved() { savedJson = GeofenceGeoJson.encode(document()); message = "Guardado local. Sin enviar al robot." }
}
