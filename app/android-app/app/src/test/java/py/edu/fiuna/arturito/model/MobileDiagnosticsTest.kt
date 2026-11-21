package py.edu.fiuna.arturito.model

import org.junit.Assert.*
import org.junit.Test

class MobileDiagnosticsTest {
    @Test
    fun separatesMultiwordConditionsAndFormatsCounters() {
        val report = "DESARMADA modo=parado seguridad=EMERGENCIA (seta) SETA no_avanza(frente_sin_eco) " +
            "imu=SIN_DATOS rueda_izq=fuera de limites rueda_der=encoder (saltos) " +
            "imu_rec=2 enlace: pings_fallidos=14 cortes=3"
        val rows = mobileDiagnosticRows(report).toMap()
        assertEquals("Detenido", rows["Modo de tracción"])
        assertEquals("Parada de emergencia", rows["Seguridad"])
        assertTrue(rows.getValue("Avisos de tracción").contains("Sensor frontal sin eco"))
        assertEquals("Fuera de límites", rows["Rueda izquierda"])
        assertEquals("Lectura irregular del encoder", rows["Rueda derecha"])
        assertEquals("2", rows["Recuperaciones de IMU"])
        assertEquals("14", rows["Comprobaciones de enlace fallidas"])
        assertEquals("3", rows["Cortes de comunicación"])
        assertFalse(rows.values.any { it.contains("DESARMADA") })
    }

    @Test
    fun waitingForMovementOrdersDoesNotImplyAMissingImu() {
        val rows = mobileDiagnosticRows("ARMADA modo=libre seguridad=sin comandos imu=ok").toMap()
        assertEquals("A la espera de una orden", rows["Seguridad"])
        assertEquals("Lectura válida", rows["IMU"])
        assertTrue(mobileDiagnosticRows(null).isEmpty())
    }
}
