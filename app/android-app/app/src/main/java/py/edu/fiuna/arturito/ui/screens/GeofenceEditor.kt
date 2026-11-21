package py.edu.fiuna.arturito.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import py.edu.fiuna.arturito.data.GeofenceStorage
import py.edu.fiuna.arturito.model.GeofenceGeoJson
import py.edu.fiuna.arturito.ui.GeofenceSession
import py.edu.fiuna.arturito.ui.components.*
import java.util.Locale

@Composable
fun GeofenceEditor(session: GeofenceSession, storage: GeofenceStorage,
                   onEditing: () -> Unit, onCenter: () -> Unit) {
    val context = LocalContext.current
    var confirmation by remember { mutableStateOf<String?>(null) }
    var preview by remember { mutableStateOf(false) }
    var pendingExport by rememberSaveable { mutableStateOf<String?>(null) }
    val export = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/geo+json")) { uri ->
        val payload = pendingExport
        pendingExport = null
        if (uri != null && payload != null) {
            runCatching {
                context.contentResolver.openOutputStream(uri, "wt")?.bufferedWriter(Charsets.UTF_8)?.use { it.write(payload) }
                    ?: error("No se pudo abrir el archivo.")
            }.onSuccess { session.message = "GeoJSON exportado. Sin enviar al robot." }
                .onFailure { session.message = "No se pudo exportar: ${it.localizedMessage}" }
        } else session.message = "Exportación cancelada."
    }
    fun save() {
        runCatching { storage.save(session.document()) }.onSuccess { session.markSaved() }
            .onFailure { session.message = "No se pudo guardar: ${it.localizedMessage}" }
    }
    fun load() {
        runCatching { storage.load() }.onSuccess { doc ->
            if (doc == null) session.message = "Todavía no hay una geocerca guardada."
            else { session.load(doc); onCenter() }
        }.onFailure { session.message = "No se pudo cargar la geocerca. El borrador se conserva." }
    }

    SectionCard("Geocerca de operación") {
        Badge(if (session.closed && session.validation.valid) "POLÍGONO VÁLIDO" else "BORRADOR ABIERTO", warning = !session.closed)
        Text("Área visual de planificación. No es una protección de seguridad validada.", style = MaterialTheme.typography.bodySmall)
        OutlinedTextField(value = session.name, onValueChange = { session.name = it.take(40) },
            label = { Text("Nombre del área") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(checked = session.editing, onCheckedChange = {
                session.editing = it; session.selected = null
                if (it) onEditing()
            })
            Text("Editar puntos", Modifier.padding(start = 8.dp))
        }
        Text(if (session.selected != null) "Tocá el mapa para mover P${session.selected!! + 1}."
            else if (session.closed) "Tocá un vértice para seleccionarlo."
            else "Tocá el mapa para agregar puntos en orden.", style = MaterialTheme.typography.bodySmall)
        Text(session.message, style = MaterialTheme.typography.bodyMedium)
        DetailRow("Vértices", "${session.vertices.size} / 64")
        if (session.closed) DetailRow("Área aproximada", String.format(Locale.US, "%.1f m²", session.validation.areaSquareMeters))
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedButton(onClick = { session.undo() }, enabled = session.canUndo, modifier = Modifier.weight(1f)) { Text("Deshacer") }
            OutlinedButton(onClick = { confirmation = "clear" }, enabled = session.vertices.isNotEmpty(), modifier = Modifier.weight(1f)) { Text("Vaciar") }
        }
        if (session.closed) OutlinedButton(onClick = { session.reopen(); onEditing() }, modifier = Modifier.fillMaxWidth()) { Text("Abrir para agregar puntos") }
        else Button(onClick = { session.close() }, enabled = session.vertices.size >= 3,
            modifier = Modifier.fillMaxWidth()) { Text("Cerrar polígono") }
        if (session.selected != null) {
            OutlinedButton(onClick = { session.selected = null }, modifier = Modifier.fillMaxWidth()) { Text("Cancelar selección") }
            OutlinedButton(onClick = { session.deleteSelected() }, modifier = Modifier.fillMaxWidth()) { Text("Eliminar punto seleccionado") }
        }
        OutlinedButton(onClick = onCenter, enabled = session.vertices.isNotEmpty(), modifier = Modifier.fillMaxWidth()) { Text("Ver toda la geocerca") }
        HorizontalDivider()
        Button(onClick = {
            if (session.savedJson != null && !session.savedMatches) confirmation = "save" else save()
        }, enabled = session.canSave, modifier = Modifier.fillMaxWidth()) { Text("Guardar geocerca") }
        OutlinedButton(onClick = {
            if (session.vertices.isNotEmpty() && !session.savedMatches) confirmation = "load" else load()
        }, modifier = Modifier.fillMaxWidth()) { Text("Cargar guardada") }
        OutlinedButton(onClick = {
            pendingExport = GeofenceGeoJson.encode(session.document())
            export.launch("arturito-geocerca.geojson")
        }, enabled = session.canSave, modifier = Modifier.fillMaxWidth()) { Text("Exportar GeoJSON") }
        TextButton(onClick = { preview = true }, enabled = session.canSave) { Text("Ver GeoJSON para envío futuro") }
        Text(if (session.savedMatches) "Guardado local · sin enviar al robot" else "Cambios locales sin guardar · sin enviar al robot",
            style = MaterialTheme.typography.labelSmall)
        session.vertices.forEachIndexed { index, point ->
            OutlinedButton(onClick = {
                session.selected = index; session.editing = true; onEditing()
                session.message = "P${index + 1} seleccionado. Tocá su nueva ubicación en el mapa."
            }, modifier = Modifier.fillMaxWidth()) {
                Text(String.format(Locale.US, "%sP%d  %.6f, %.6f", if (session.selected == index) "● " else "", index + 1, point.latitude, point.longitude),
                    style = MaterialTheme.typography.labelSmall)
            }
        }
    }
    if (confirmation != null) AlertDialog(onDismissRequest = { confirmation = null },
        title = { Text(when (confirmation) { "clear" -> "¿Vaciar el borrador?"; "load" -> "¿Cargar la copia guardada?"; else -> "¿Reemplazar la copia guardada?" }) },
        text = { Text(if (confirmation == "clear") "La copia guardada se conserva. Podés deshacer el cambio."
            else if (confirmation == "load") "El borrador actual se reemplaza. Podés deshacer la carga."
            else "Se guardará el polígono actual en el almacenamiento local de la app.") },
        confirmButton = { TextButton(onClick = {
            when (confirmation) { "clear" -> session.clear(); "load" -> load(); else -> save() }; confirmation = null
        }) { Text("Confirmar") } },
        dismissButton = { TextButton(onClick = { confirmation = null }) { Text("Cancelar") } })
    if (preview) AlertDialog(onDismissRequest = { preview = false }, title = { Text("GeoJSON · sin enviar") },
        text = { Box(Modifier.heightIn(max = 360.dp).verticalScroll(rememberScrollState())) {
            Text(GeofenceGeoJson.encode(session.document()), style = MaterialTheme.typography.bodySmall)
        } },
        confirmButton = { TextButton(onClick = { preview = false }) { Text("Cerrar") } })
}
