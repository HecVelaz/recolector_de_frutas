package py.edu.fiuna.arturito.data

import org.junit.Assert.*
import org.junit.Test

class BridgeProtocolTest {
    private val unknown = """{"schema_version":1,"source":"estado","simulated":false,"upstream_available":true,"base_state":null,"battery_voltage":null,"gps":null,"commands_enabled":false,"geofence_enforced":false}"""

    @Test fun missingReadingsRemainUnknown() {
        val value = BridgeProtocol.decode(unknown)
        assertFalse(value.simulated)
        assertNull(value.gps)
        assertNull(value.baseState)
        assertNull(value.batteryVoltage)
        assertTrue(value.upstreamAvailable)
    }

    @Test fun rejectsIncompatibleOrUnsafeContract() {
        for (message in listOf(unknown.replace("\"schema_version\":1", "\"schema_version\":2"),
            unknown.replace("\"commands_enabled\":false", "\"commands_enabled\":true"),
            unknown.replace("\"simulated\":false", "\"simulated\":true"))) {
            assertThrows(IllegalArgumentException::class.java) { BridgeProtocol.decode(message) }
        }
    }

    @Test fun validatesGpsAndSeparatesSources() {
        val gps = """{"latitude":-25.33,"longitude":-57.51,"timestamp_ms":1234,"simulated":true}"""
        val example = unknown.replace("\"source\":\"estado\"", "\"source\":\"simulation\"")
            .replace("\"simulated\":false", "\"simulated\":true").replace("\"gps\":null", "\"gps\":$gps")
        assertTrue(BridgeProtocol.decode(example).gps!!.simulated)
        assertEquals(-25.33, BridgeProtocol.decode(example).gps!!.latitude, 0.0)
        assertThrows(IllegalArgumentException::class.java) { BridgeProtocol.decode(example.replace("-25.33", "91.0")) }
    }

    @Test fun rejectsEndpointCredentialsAndPaths() {
        assertEquals(8001, BridgeProtocol.endpoint("http://192.168.1.159:8001").port)
        for (address in listOf("http://user:pass@192.168.1.159", "http://192.168.1.159/estado", "http://192.168.1.159?key=secret")) {
            assertThrows(IllegalArgumentException::class.java) { BridgeProtocol.endpoint(address) }
        }
    }

    @Test fun decodesRealSourceAgesAndSeparateAlarms() {
        val payload = unknown.replace("\"source\":\"estado\"", "\"source\":\"ros2\"").dropLast(1) +
            """, "sources":[{"key":"battery","label":"Batería","topic":"/battery","status":"fresh","age_ms":120,"value":11.72,"reason":null}],"alarm_details":[{"code":"SETA","severity":"critical","message":"Seta activa"}]}"""
        val result = BridgeProtocol.decode(payload)
        assertEquals(120L, result.sources.single().ageMillis)
        assertEquals(11.72, result.sources.single().value!!.asDouble, 0.0)
        assertEquals("critical", result.alarmDetails.single().severity)
        assertNull(result.gps)
    }

    @Test fun rejectsExpiredReadingsPresentedAsCurrent() {
        val payload = unknown.dropLast(1) +
            """, "sources":[{"key":"battery","label":"Batería","topic":"/battery","status":"stale","age_ms":4000,"value":11.72,"reason":null}]}"""
        assertThrows(IllegalArgumentException::class.java) { BridgeProtocol.decode(payload) }
        val accepted = BridgeProtocol.decode(payload.replace("\"value\":11.72", "\"value\":null"))
        assertEquals("Vencido", accepted.sources.single().statusLabel)
        assertNull(accepted.sources.single().value)
    }

    @Test fun controlOnlyByLoopbackOrTailscale() {
        assertTrue(BridgeProtocol.controlHostAllowed("127.0.0.1"))
        assertTrue(BridgeProtocol.controlHostAllowed("100.116.96.71"))
        assertFalse(BridgeProtocol.controlHostAllowed("192.168.1.159"))
        assertFalse(BridgeProtocol.controlHostAllowed("100.200.1.1"))
    }
}
