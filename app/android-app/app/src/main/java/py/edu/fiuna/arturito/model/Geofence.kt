package py.edu.fiuna.arturito.model

import kotlin.math.*
import org.maplibre.geojson.Feature
import org.maplibre.geojson.Polygon
import com.google.gson.JsonArray
import com.google.gson.JsonObject

data class FencePoint(val latitude: Double, val longitude: Double) {
    init {
        require(latitude.isFinite() && latitude in -85.0..85.0) { "Latitud fuera del rango local admitido." }
        require(longitude.isFinite() && longitude in -180.0..180.0) { "Longitud inválida." }
    }
}

data class FenceValidation(val error: String? = null, val areaSquareMeters: Double = 0.0) {
    val valid: Boolean get() = error == null
}

/** Geometría plana local en metros; limitada explícitamente a un entorno de 5 km. */
object GeofenceGeometry {
    const val maxVertices = 64
    private data class XY(val x: Double, val y: Double)
    private fun project(points: List<FencePoint>): List<XY> {
        val origin = points.first()
        return points.map { XY(Math.toRadians(it.longitude - origin.longitude) * 6_371_000 * cos(Math.toRadians(origin.latitude)),
            Math.toRadians(it.latitude - origin.latitude) * 6_371_000) }
    }
    private fun cross(a: XY, b: XY, c: XY) = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    private fun onSegment(a: XY, b: XY, p: XY) = abs(cross(a, b, p)) < 1e-6 &&
        p.x >= min(a.x, b.x) - 1e-6 && p.x <= max(a.x, b.x) + 1e-6 &&
        p.y >= min(a.y, b.y) - 1e-6 && p.y <= max(a.y, b.y) + 1e-6
    private fun intersects(a: XY, b: XY, c: XY, d: XY): Boolean {
        val abC = cross(a, b, c); val abD = cross(a, b, d)
        val cdA = cross(c, d, a); val cdB = cross(c, d, b)
        return ((abC > 0 && abD < 0 || abC < 0 && abD > 0) &&
            (cdA > 0 && cdB < 0 || cdA < 0 && cdB > 0)) ||
            onSegment(a, b, c) || onSegment(a, b, d) || onSegment(c, d, a) || onSegment(c, d, b)
    }
    private fun signedArea(points: List<XY>) = points.indices.sumOf { i ->
        val next = points[(i + 1) % points.size]
        points[i].x * next.y - next.x * points[i].y
    } / 2

    fun validate(points: List<FencePoint>, closed: Boolean = true): FenceValidation {
        if (points.size > maxVertices) return FenceValidation("Máximo $maxVertices vértices.")
        if (points.isEmpty()) return FenceValidation(if (closed) "Agregá al menos 3 puntos." else null)
        val xy = project(points)
        if (xy.any { hypot(it.x, it.y) > 5000 }) return FenceValidation("El área debe quedar a menos de 5 km del primer punto.")
        for (i in xy.indices) for (j in 0 until i) {
            if (hypot(xy[i].x - xy[j].x, xy[i].y - xy[j].y) < 0.25)
                return FenceValidation("Los puntos deben estar separados al menos 25 cm.")
        }
        val segments = if (closed) xy.size else xy.size - 1
        // Las aristas adyacentes pueden compartir extremo, pero no retroceder sobre sí mismas.
        val cornerIndices = if (closed) xy.indices.toList() else (1 until xy.size - 1).toList()
        for (i in cornerIndices) {
            if (xy.size < 3) break
            val a = xy[(i - 1 + xy.size) % xy.size]; val b = xy[i]; val c = xy[(i + 1) % xy.size]
            if (abs(cross(a, b, c)) < 1e-6 && (a.x - b.x) * (c.x - b.x) + (a.y - b.y) * (c.y - b.y) > 0)
                return FenceValidation("Dos lados se superponen. Cambiá el punto.")
        }
        for (i in 0 until segments) for (j in i + 1 until segments) {
            if (j == i + 1 || closed && i == 0 && j == segments - 1) continue
            if (intersects(xy[i], xy[(i + 1) % xy.size], xy[j], xy[(j + 1) % xy.size]))
                return FenceValidation("Los lados se cruzan o se tocan. Deshacé o mové un punto.")
        }
        if (closed && points.size < 3) return FenceValidation("Agregá al menos 3 puntos.")
        val area = if (points.size >= 3) abs(signedArea(xy)) else 0.0
        if (closed && area < 1.0) return FenceValidation("El polígono debe tener al menos 1 m².")
        return FenceValidation(areaSquareMeters = area)
    }

    fun counterClockwise(points: List<FencePoint>): List<FencePoint> {
        require(validate(points).valid)
        return if (signedArea(project(points)) < 0) points.reversed() else points
    }
}

data class FenceDocument(val name: String, val vertices: List<FencePoint>)

/** Contrato de archivo y futuro envío: Feature GeoJSON RFC 7946, anillo exterior CCW. */
object GeofenceGeoJson {
    fun encode(document: FenceDocument): String {
        require(document.name.isNotBlank() && document.name.length <= 40) { "El nombre debe tener entre 1 y 40 caracteres." }
        val validation = GeofenceGeometry.validate(document.vertices)
        require(validation.valid) { validation.error.orEmpty() }
        val normalized = GeofenceGeometry.counterClockwise(document.vertices)
        // El serializador geográfico del SDK redondea coordenadas. El árbol JSON
        // conserva los Double originales al guardar y volver a cargar el límite.
        val ring = JsonArray().apply {
            (normalized + normalized.first()).forEach { point ->
                add(JsonArray().apply { add(point.longitude); add(point.latitude) })
            }
        }
        return JsonObject().apply {
            addProperty("type", "Feature")
            add("properties", JsonObject().apply {
                addProperty("name", document.name.trim())
                addProperty("schemaVersion", 1)
                addProperty("purpose", "operation_boundary")
            })
            add("geometry", JsonObject().apply {
                addProperty("type", "Polygon")
                add("coordinates", JsonArray().apply { add(ring) })
            })
        }.toString()
    }

    fun decode(json: String): FenceDocument {
        require(json.length <= 64_000) { "Archivo demasiado grande." }
        val feature = Feature.fromJson(json)
        val polygon = feature.geometry() as? Polygon ?: error("Se esperaba un Feature Polygon.")
        require(polygon.coordinates().size == 1) { "Solo se admite un anillo, sin huecos." }
        val ring = polygon.coordinates().single()
        require(ring.size in 4..GeofenceGeometry.maxVertices + 1 && ring.first() == ring.last()) { "Anillo sin cerrar o cantidad de puntos inválida." }
        val points = ring.dropLast(1).map { FencePoint(it.latitude(), it.longitude()) }
        val name = feature.getStringProperty("name") ?: "Zona de operación"
        require(name.isNotBlank() && name.length <= 40) { "Nombre inválido." }
        val validation = GeofenceGeometry.validate(points)
        require(validation.valid) { validation.error.orEmpty() }
        return FenceDocument(name, points)
    }
}
