package py.edu.fiuna.arturito.data

import com.google.gson.JsonParser
import org.junit.Assert.*
import org.junit.Test

/** 21/11: el cero del Móvil es su pose respecto del limón más cercano (lo que manda el puente). */
class NavigationOriginTest {
    @Test fun decodesTheLemonOriginFromTheBridge() {
        val json = """{"kind":"lemon","lemon_in_arm":{"x_mm":-575.0,"y_mm":290.0,"z_mm":128.0},"lemons_seen":2,
            "distance_m":0.644,"odom_origin":{"x_m":0.0,"y_m":0.0,"yaw_rad":0.0},
            "displacement":{"x_m":0.01,"y_m":-0.02,"yaw_deg":1.5}}"""
        val origin = JsonParser.parseString(json).asJsonObject.decodeNavigationOrigin()
        assertEquals(-575.0, origin.lemonXmm, 1e-9)
        assertEquals(290.0, origin.lemonYmm, 1e-9)
        assertEquals(2, origin.lemonsSeen)
        assertEquals(0.644, origin.distanceM, 1e-9)
        assertEquals(0.439, origin.lemonHeightM, 1e-3)   // 256 + 1,43·128 mm del piso
        assertEquals(1.5, checkNotNull(origin.displacement).yawDegrees, 1e-9)
        assertTrue(origin.hasLemon)
    }

    @Test fun decodesAZeroWithoutLemon() {   // 21/11: la recolección lo busca girando
        val json = """{"kind":"pose","lemon_in_arm":null,"lemons_seen":0,"distance_m":0.0,
            "odom_origin":{"x_m":0.0,"y_m":0.0,"yaw_rad":0.0},"displacement":null}"""
        val origin = JsonParser.parseString(json).asJsonObject.decodeNavigationOrigin()
        assertFalse(origin.hasLemon)
        assertEquals(0, origin.lemonsSeen)
        assertNull(origin.displacement)
    }
}
