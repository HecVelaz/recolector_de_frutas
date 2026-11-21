package py.edu.fiuna.arturito.model

import py.edu.fiuna.arturito.data.BridgeTelemetry
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot

/** Alertas de la pestaña Estado (21/11). Solo avisan: la detención la hace el firmware de la S3, no la app.
 * El orden es la prioridad (seta > IMU > bumpers > ultrasonidos); `group` agrupa los de igual prioridad. */
enum class SensorAlert(val group: Int, val repeats: Boolean, val label: String, val short: String) {
    SETA(0, false, "Seta de emergencia", "seta"),
    IMU(1, false, "IMU: inclinación mayor a 25°", "IMU"),
    BUMPER_IZQ(2, false, "Bumper izquierdo", "bumper izq."),
    BUMPER_FRENTE(2, false, "Bumper frontal", "bumper frontal"),
    BUMPER_DER(2, false, "Bumper derecho", "bumper der."),
    US_IZQ(3, true, "Ultrasonido izquierdo a 20 cm o menos", "ultrasonido izq."),
    US_CENTRAL(3, true, "Ultrasonido central a 20 cm o menos", "ultrasonido central"),
    US_DER(3, true, "Ultrasonido derecho a 20 cm o menos", "ultrasonido der."),
}

enum class SensorLook { NORMAL, ACTIVE, NO_DATA }

const val RANGE_ALERT_M = .20      // = distancia de parada al frente del firmware (CFG_SEG)
const val TILT_ALERT_DEG = 25.0    // = vuelco del firmware (CFG_SEG)

/** Roll y pitch como en firmware/base/src/main.cpp; devuelve el mayor en grados. */
fun tiltDegrees(a: List<Double>): Double? {
    if (a.size != 3 || a.any { !it.isFinite() }) return null
    val roll = Math.toDegrees(atan2(a[1], a[2]))
    val pitch = Math.toDegrees(atan2(-a[0], hypot(a[1], a[2])))
    return maxOf(abs(roll), abs(pitch))
}

fun sensorLooks(data: BridgeTelemetry?): Map<SensorAlert, SensorLook> {
    val fresh = data?.sources.orEmpty().filter { it.status == "fresh" && it.value != null }.associateBy { it.key }
    fun look(known: Boolean, active: Boolean) =
        if (!known) SensorLook.NO_DATA else if (active) SensorLook.ACTIVE else SensorLook.NORMAL
    fun range(key: String) = runCatching {
        val value = fresh.getValue(key).value!!.asJsonObject
        look(true, value.get("kind").asString == "distance" && value.get("meters").asDouble <= RANGE_ALERT_M)
    }.getOrDefault(SensorLook.NO_DATA)
    val base = runCatching { fresh["base"]?.value?.asString }.getOrNull()
    val mask = runCatching { fresh["bumpers"]?.value?.asInt }.getOrNull()
    val tilt = runCatching {
        tiltDegrees(fresh["imu"]!!.value!!.asJsonObject.getAsJsonArray("acceleration_m_s2").map { it.asDouble })
    }.getOrNull()
    // ponytail: inclinación de una sola muestra (sin filtro); un golpe andando puede dar un aviso corto.
    // El vuelco real lo marca el firmware (filtrado y enclavado hasta `r`) con seguridad=VUELCO.
    val vuelco = base?.contains("seguridad=VUELCO") == true
    fun bumper(bit: Int) = look(mask != null, mask != null && mask and (1 shl bit) != 0)  // bit 0 frente, 1 izq, 2 der
    return mapOf(
        SensorAlert.SETA to look(base != null, base != null &&
            (Regex("""\bSETA\b""").containsMatchIn(base) || "EMERGENCIA (seta)" in base)),
        SensorAlert.IMU to look(base != null || tilt != null, vuelco || (tilt ?: 0.0) > TILT_ALERT_DEG),
        SensorAlert.BUMPER_IZQ to bumper(1),
        SensorAlert.BUMPER_FRENTE to bumper(0),
        SensorAlert.BUMPER_DER to bumper(2),
        SensorAlert.US_IZQ to range("range_left"),
        SensorAlert.US_CENTRAL to range("range_front"),
        SensorAlert.US_DER to range("range_right"),
    )
}

/** Decide qué sonido tocar; se llama seguido (~4 Hz) aunque la telemetría llegue a 1 Hz.
 * Suena al pasar a activo; solo los ultrasonidos se repiten mientras sigan activos. Un sonido por vez: gana el de
 * mayor prioridad y, mientras haya uno activo de mayor prioridad, los de menor no suenan. */
class AlertSoundTracker(private val repeatMillis: Long = 1500) {
    private val active = mutableSetOf<SensorAlert>()
    private val lastPlayed = mutableMapOf<SensorAlert, Long>()
    private var lastAny = Long.MIN_VALUE / 2

    fun update(looks: Map<SensorAlert, SensorLook>, nowMillis: Long): SensorAlert? {
        val current = looks.filterValues { it == SensorLook.ACTIVE }.keys
        val started = current - active
        active.clear(); active += current
        lastPlayed.keys.retainAll(current)
        val top = current.minOfOrNull { it.group } ?: return null
        val repeatDue = nowMillis - lastAny >= repeatMillis
        val due = current.filter { it.group == top && (it in started ||
            it.repeats && repeatDue && nowMillis - (lastPlayed[it] ?: Long.MIN_VALUE / 2) >= repeatMillis) }
        // Entre los de igual prioridad, el que hace más que no suena (así se alternan dos ultrasonidos).
        val pick = due.minWithOrNull(compareBy({ lastPlayed[it] ?: Long.MIN_VALUE }, { it.ordinal })) ?: return null
        lastPlayed[pick] = nowMillis; lastAny = nowMillis
        return pick
    }
}
