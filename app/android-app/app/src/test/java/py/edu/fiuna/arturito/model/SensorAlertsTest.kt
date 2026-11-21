package py.edu.fiuna.arturito.model

import com.google.gson.JsonParser
import org.junit.Assert.*
import org.junit.Test
import py.edu.fiuna.arturito.data.BridgeTelemetry
import py.edu.fiuna.arturito.data.SensorReading

class SensorAlertsTest {
    private fun reading(key: String, json: String?, status: String = "fresh") =
        SensorReading(key, key, "/$key", status, 0, json?.let { JsonParser.parseString(it) }, null)

    private fun telemetry(vararg sources: SensorReading) =
        BridgeTelemetry(false, "ros2", true, null, null, null, null, sources.toList())

    private fun range(m: Double) = """{"kind":"distance","meters":$m}"""
    private val level = """{"acceleration_m_s2":[0.0,0.0,9.81]}"""
    private val quiet = arrayOf(
        reading("base", "\"ARMADA modo=v/w seguridad=ok imu=ok\""), reading("bumpers", "0"), reading("imu", level),
        reading("range_front", range(.5)), reading("range_left", """{"kind":"out_of_range","meters":null}"""),
        reading("range_right", range(.21)))

    private fun looks(vararg changed: SensorReading) =
        sensorLooks(telemetry(*(quiet.filter { q -> changed.none { it.key == q.key } } + changed).toTypedArray()))

    private fun active(vararg alerts: SensorAlert) =
        SensorAlert.entries.associateWith { if (it in alerts) SensorLook.ACTIVE else SensorLook.NORMAL }

    @Test fun quietRobotHasNoAlertsAndDisconnectedHasNoData() {
        assertTrue(looks().values.all { it == SensorLook.NORMAL })
        assertTrue(sensorLooks(null).values.all { it == SensorLook.NO_DATA })
        assertEquals(SensorLook.NO_DATA, looks(reading("range_front", null, "stale"))[SensorAlert.US_CENTRAL])
    }

    @Test fun thresholdsAndBumperBits() {
        assertEquals(SensorLook.ACTIVE, looks(reading("range_front", range(.20)))[SensorAlert.US_CENTRAL])
        assertEquals(SensorLook.NORMAL, looks(reading("range_front", range(.201)))[SensorAlert.US_CENTRAL])
        val bumpers = looks(reading("bumpers", "6"))   // bit 1 izq, bit 2 der
        assertEquals(SensorLook.NORMAL, bumpers[SensorAlert.BUMPER_FRENTE])
        assertEquals(SensorLook.ACTIVE, bumpers[SensorAlert.BUMPER_IZQ])
        assertEquals(SensorLook.ACTIVE, bumpers[SensorAlert.BUMPER_DER])
        assertEquals(SensorLook.ACTIVE, looks(reading("base", "\"DESARMADA modo=parado seguridad=EMERGENCIA (seta) SETA imu=ok\""))[SensorAlert.SETA])
    }

    @Test fun imuByTiltOrFirmwareRollover() {
        assertEquals(24.0, tiltDegrees(listOf(0.0, Math.sin(Math.toRadians(24.0)), Math.cos(Math.toRadians(24.0))))!!, 1e-9)
        val tilted = """{"acceleration_m_s2":[0.0,${Math.sin(Math.toRadians(26.0))},${Math.cos(Math.toRadians(26.0))}]}"""
        assertEquals(SensorLook.ACTIVE, looks(reading("imu", tilted))[SensorAlert.IMU])
        assertEquals(SensorLook.ACTIVE, looks(reading("base", "\"DESARMADA modo=parado seguridad=VUELCO imu=ok\""))[SensorAlert.IMU])
    }

    @Test fun soundsOnlyOnActivationExceptRepeatingRanges() {
        val tracker = AlertSoundTracker(repeatMillis = 1500)
        assertNull(tracker.update(active(), 0))
        assertEquals(SensorAlert.BUMPER_IZQ, tracker.update(active(SensorAlert.BUMPER_IZQ), 100))
        assertNull(tracker.update(active(SensorAlert.BUMPER_IZQ), 5000))           // un bumper no se repite
        assertNull(tracker.update(active(), 5100))
        assertEquals(SensorAlert.US_IZQ, tracker.update(active(SensorAlert.US_IZQ), 6000))
        assertNull(tracker.update(active(SensorAlert.US_IZQ), 7000))
        assertEquals(SensorAlert.US_IZQ, tracker.update(active(SensorAlert.US_IZQ), 7500))  // repite cada 1,5 s
    }

    @Test fun priorityWinsAndSilencesLowerAlerts() {
        val tracker = AlertSoundTracker(repeatMillis = 1500)
        assertEquals(SensorAlert.SETA, tracker.update(active(SensorAlert.SETA, SensorAlert.IMU, SensorAlert.US_CENTRAL), 0))
        assertNull(tracker.update(active(SensorAlert.SETA, SensorAlert.IMU, SensorAlert.US_CENTRAL), 3000))
        // Se suelta la seta: el ultrasonido, que sigue activo, vuelve a sonar; la IMU (sin repetición) no.
        assertNull(tracker.update(active(SensorAlert.IMU, SensorAlert.US_CENTRAL), 3100))
        assertEquals(SensorAlert.US_CENTRAL, tracker.update(active(SensorAlert.US_CENTRAL), 3200))
        // Dos ultrasonidos activos se alternan.
        assertEquals(SensorAlert.US_IZQ, tracker.update(active(SensorAlert.US_CENTRAL, SensorAlert.US_IZQ), 3300))
        assertEquals(SensorAlert.US_CENTRAL, tracker.update(active(SensorAlert.US_CENTRAL, SensorAlert.US_IZQ), 4800))
        assertEquals(SensorAlert.US_IZQ, tracker.update(active(SensorAlert.US_CENTRAL, SensorAlert.US_IZQ), 6300))
    }
}
