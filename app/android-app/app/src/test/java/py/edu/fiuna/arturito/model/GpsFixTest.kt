package py.edu.fiuna.arturito.model

import org.junit.Assert.*
import org.junit.Test

class GpsFixTest {
    @Test fun rejectsInvalidCoordinates() {
        listOf(91.0 to 0.0, 0.0 to 181.0, Double.NaN to 0.0, 0.0 to Double.POSITIVE_INFINITY).forEach { (lat, lon) ->
            assertThrows(IllegalArgumentException::class.java) { GpsFix(lat, lon, 0) }
        }
    }
    @Test fun distanceUsesMeters() {
        val origin = GpsFix(0.0, 0.0, 0)
        assertEquals(111.195, origin.distanceTo(GpsFix(0.0, 0.001, 1)), 0.1)
        assertEquals(0.0, origin.distanceTo(origin), 0.0)
        assertEquals(111.195, origin.distanceTo(GpsFix(0.001, 0.0, 1)), 0.1)
    }
    @Test fun routeClosesWithoutJumps() {
        val route = (0..DemoGpsRoute.steps).map { DemoGpsRoute.point(it, it.toLong()) }
        assertEquals(0.0, route.first().distanceTo(route.last()), 0.01)
        assertTrue(route.zipWithNext().all { (a, b) -> a.distanceTo(b) in 1.0..5.0 })
        assertTrue(route.all { it.simulated && it.latitude in -25.332..-25.330 && it.longitude in -57.517..-57.513 })
    }
}
