package py.edu.fiuna.arturito.model

import kotlin.math.*

/** Coordenadas WGS84 del robot. No representa la ubicación de la tablet. */
data class GpsFix(val latitude: Double, val longitude: Double, val timestampMillis: Long,
                  val simulated: Boolean = true) {
    init {
        require(latitude.isFinite() && latitude in -90.0..90.0)
        require(longitude.isFinite() && longitude in -180.0..180.0)
        require(timestampMillis >= 0)
    }

    fun distanceTo(other: GpsFix): Double {
        val latitudeDelta = Math.toRadians(other.latitude - latitude)
        val longitudeDelta = Math.toRadians(other.longitude - longitude)
        val a = sin(latitudeDelta / 2).pow(2) + cos(Math.toRadians(latitude)) *
            cos(Math.toRadians(other.latitude)) * sin(longitudeDelta / 2).pow(2)
        return 6_371_000.0 * 2 * asin(sqrt(a.coerceIn(0.0, 1.0)))
    }
}

/** Circuito ficticio, cerca de FIUNA. No constituye una ruta autorizada para el robot. */
object DemoGpsRoute {
    private val corners = listOf(
        -25.3307 to -57.5156, -25.3307 to -57.5146,
        -25.3313 to -57.5146, -25.3313 to -57.5156, -25.3307 to -57.5156,
    )
    const val steps = 120
    fun point(index: Int, now: Long): GpsFix {
        val step = index.coerceIn(0, steps)
        val leg = (step / 30).coerceAtMost(3)
        val fraction = (step - leg * 30) / 30.0
        val a = corners[leg]
        val b = corners[leg + 1]
        return GpsFix(a.first + (b.first - a.first) * fraction,
            a.second + (b.second - a.second) * fraction, now)
    }
}
