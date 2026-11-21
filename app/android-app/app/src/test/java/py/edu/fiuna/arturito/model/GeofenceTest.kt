package py.edu.fiuna.arturito.model

import org.junit.Assert.*
import org.junit.Test
import org.maplibre.geojson.Feature
import org.maplibre.geojson.Polygon

class GeofenceTest {
    private fun p(x: Double, y: Double) = FencePoint(y / 111_195.0, x / 111_195.0)
    private val square = listOf(p(0.0, 0.0), p(20.0, 0.0), p(20.0, 20.0), p(0.0, 20.0))

    @Test fun validAreaIsMeasuredInSquareMetersInEitherDirection() {
        assertEquals(400.0, GeofenceGeometry.validate(square).areaSquareMeters, 0.1)
        assertTrue(GeofenceGeometry.validate(square.reversed()).valid)
    }
    @Test fun rejectsBowTieAndOpenCrossing() {
        val bowTie = listOf(square[0], square[2], square[3], square[1])
        assertFalse(GeofenceGeometry.validate(bowTie).valid)
        assertFalse(GeofenceGeometry.validate(bowTie, closed = false).valid)
    }
    @Test fun rejectsClosingEdgeCrossing() {
        val points = listOf(p(0.0, 0.0), p(20.0, 0.0), p(0.0, 20.0), p(20.0, 20.0))
        assertTrue(GeofenceGeometry.validate(points, closed = false).valid)
        assertFalse(GeofenceGeometry.validate(points).valid)
    }
    @Test fun rejectsDuplicatesAndOverlappingAdjacentEdges() {
        assertFalse(GeofenceGeometry.validate(square + square.first()).valid)
        assertFalse(GeofenceGeometry.validate(listOf(p(0.0, 0.0), p(20.0, 0.0), p(10.0, 0.0)), closed = false).valid)
    }
    @Test fun rejectsCollinearTinyAndExcessiveAreas() {
        assertFalse(GeofenceGeometry.validate(listOf(p(0.0, 0.0), p(10.0, 0.0), p(20.0, 0.0))).valid)
        assertFalse(GeofenceGeometry.validate(listOf(p(0.0, 0.0), p(0.5, 0.0), p(0.0, 0.5))).valid)
        assertFalse(GeofenceGeometry.validate(listOf(p(0.0, 0.0), p(6000.0, 0.0), p(0.0, 20.0))).valid)
    }
    @Test fun geoJsonClosesRingAndUsesLongitudeLatitude() {
        val json = GeofenceGeoJson.encode(FenceDocument("Zona 1", square))
        val ring = (Feature.fromJson(json).geometry() as Polygon).coordinates().single()
        assertEquals(5, ring.size)
        assertEquals(ring.first(), ring.last())
        assertEquals(square[1].longitude, ring[1].longitude(), 0.0)
        assertEquals(square[1].latitude, ring[1].latitude(), 0.0)
        assertEquals(FenceDocument("Zona 1", square), GeofenceGeoJson.decode(json))
    }
    @Test fun normalizesWindingAndRejectsMalformedDocuments() {
        val document = GeofenceGeoJson.decode(GeofenceGeoJson.encode(FenceDocument("Zona 1", square.reversed())))
        assertEquals(square.toSet(), document.vertices.toSet())
        assertThrows(Exception::class.java) { GeofenceGeoJson.decode("{}") }
        assertThrows(Exception::class.java) { GeofenceGeoJson.decode("""{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[0,0],[0.001,0],[0.001,0.001],[0,0.001]]]}}""") }
        assertThrows(IllegalArgumentException::class.java) { GeofenceGeoJson.encode(FenceDocument(" ", square)) }
    }
}
