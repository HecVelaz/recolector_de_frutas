package py.edu.fiuna.arturito.data

import android.content.Context
import android.util.AtomicFile
import py.edu.fiuna.arturito.model.FenceDocument
import py.edu.fiuna.arturito.model.GeofenceGeoJson
import java.io.File

class GeofenceStorage(private val context: Context) {
    private val file by lazy { AtomicFile(File(context.filesDir, "operation-boundary.geojson")) }
    fun load(): FenceDocument? {
        if (!file.baseFile.exists()) return null
        return GeofenceGeoJson.decode(file.openRead().bufferedReader(Charsets.UTF_8).use { it.readText() })
    }
    fun save(document: FenceDocument) {
        val bytes = GeofenceGeoJson.encode(document).toByteArray(Charsets.UTF_8)
        val stream = file.startWrite()
        try { stream.write(bytes); file.finishWrite(stream) }
        catch (error: Exception) { file.failWrite(stream); throw error }
    }
}
