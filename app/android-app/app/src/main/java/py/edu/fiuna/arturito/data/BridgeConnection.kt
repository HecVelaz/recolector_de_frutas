package py.edu.fiuna.arturito.data

import androidx.compose.runtime.*
import com.google.gson.JsonParser
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import okhttp3.*
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import py.edu.fiuna.arturito.model.GpsFix
import java.util.concurrent.TimeUnit
import java.util.UUID

const val DEFAULT_MANUAL_LIMIT_MPS = .04

data class BridgeTelemetry(val simulated: Boolean, val source: String, val upstreamAvailable: Boolean,
    val baseState: String?, val batteryVoltage: Double?, val gps: GpsFix?, val alarms: List<String>?,
    val sources: List<SensorReading> = emptyList(), val alarmDetails: List<RobotAlarm> = emptyList(),
    val armState: String? = null, val controlGate: ControlGateStatus? = null,
    val controlDryRun: Boolean = false, val simulatedBaseOutput: SimulatedBaseOutput? = null,
    val physicalManual: Boolean = false, val manualArmReady: Boolean? = null, val manualAnalog: Boolean = false,
    val manualLimitMps: Double = DEFAULT_MANUAL_LIMIT_MPS, val servoPositions: Boolean = false,
    val stereo: StereoReading? = null, val navigationOrigin: NavigationOrigin? = null,
    val collection: CollectionStatus? = null) {
    val measuredLinearMps: Double?
        get() = sources.firstOrNull { it.key == "odom" && it.status == "fresh" }?.value?.asJsonObject
            ?.get("linear_m_s")?.asDouble?.takeIf { it.isFinite() }
}

data class Position3D(val xM: Double, val yM: Double, val zM: Double)
data class StereoReading(val status: String, val frameId: String?, val lemons: List<Position3D>)
data class LocalPose(val xM: Double, val yM: Double, val yawDegrees: Double)
data class CollectionStatus(val state: String, val message: String, val active: Boolean, val events: List<String>)
data class NavigationOrigin(val markerId: Int, val distanceM: Double, val atMarker: LocalPose,
    val displacement: LocalPose?)

internal fun JsonObject.decodeNavigationOrigin(): NavigationOrigin {
    fun JsonObject.pose() = LocalPose(get("x_m").asDouble, get("y_m").asDouble, get("yaw_deg").asDouble)
    return NavigationOrigin(get("marker_id").asInt, get("distance_m").asDouble,
        getAsJsonObject("at_marker").pose(), get("displacement")?.takeIf { it.isJsonObject }?.asJsonObject?.pose())
}

internal fun JsonObject.decodeCollectionStatus() = CollectionStatus(get("state").asString, get("message").asString,
    get("active").asBoolean, getAsJsonArray("events")?.map { it.asJsonObject.get("message").asString }.orEmpty())

data class SimulatedBaseOutput(val linear: Double, val angular: Double)

private fun JsonElement?.baseOutput(): SimulatedBaseOutput? = this
    ?.takeIf { it.isJsonObject }?.asJsonObject?.let {
        SimulatedBaseOutput(it.get("linear_m_s").asDouble, it.get("angular_rad_s").asDouble)
            .also { value -> require(value.linear.isFinite() && value.angular.isFinite()) }
    }

data class ControlGateStatus(val state: String, val ready: Boolean = false,
    val reasons: List<String> = emptyList(), val dryRun: Boolean = true,
    val robotCommandSent: Boolean = false, val simulatedBaseOutput: SimulatedBaseOutput? = null)

data class SensorReading(val key: String, val label: String, val topic: String, val status: String,
    val ageMillis: Long?, val value: JsonElement?, val reason: String?) {
    val statusLabel get() = when (status) { "fresh" -> "Reciente"; "stale" -> "Vencido"; "invalid" -> "Inválido"; else -> "Sin mensajes" }
}
data class RobotAlarm(val code: String, val severity: String, val message: String)

object BridgeProtocol {
    fun endpoint(value: String): HttpUrl {
        val url = value.trim().toHttpUrl()
        require(url.encodedPath == "/" && url.query == null && url.fragment == null &&
            url.username.isEmpty() && url.password.isEmpty()) { "Usá solamente http(s)://dirección:puerto" }
        return url
    }
    fun decode(json: String): BridgeTelemetry {
        require(json.length <= 64000) { "Mensaje demasiado grande" }
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version").asInt == 1) { "API incompatible" }
        val source = root.get("source").asString
        val simulated = root.get("simulated").asBoolean
        val physical = root.get("physical_manual")?.asString in listOf("supervised_bench", "supervised_manual")
        require(root.get("commands_enabled").asBoolean == physical && !root.get("geofence_enforced").asBoolean &&
            (!physical || source == "ros2" && !simulated)) { "Perfil de control incompatible" }
        require(source in listOf("simulation", "estado", "ros2") && simulated == (source == "simulation")) { "Origen incoherente" }
        val gps = root.get("gps").takeUnless { it == null || it.isJsonNull }?.asJsonObject?.let {
            require(it.get("simulated").asBoolean == simulated) { "Origen GPS incoherente" }
            GpsFix(it.get("latitude").asDouble, it.get("longitude").asDouble, it.get("timestamp_ms").asLong, simulated)
        }
        val battery = root.get("battery_voltage").takeUnless { it == null || it.isJsonNull }?.asDouble
        require(battery == null || battery.isFinite() && battery >= 0) { "Batería inválida" }
        val sensors = root.getAsJsonArray("sources")?.map { entry ->
            val item = entry.asJsonObject
            val status = item.get("status").asString
            require(status in listOf("waiting", "fresh", "stale", "invalid"))
            val age = item.get("age_ms").takeUnless { it == null || it.isJsonNull }?.asLong
            require(age == null || age >= 0)
            val value = item.get("value").takeUnless { it == null || it.isJsonNull }
            require(status == "fresh" || value == null) { "Una lectura vencida no debe tener valor vigente" }
            SensorReading(item.get("key").asString, item.get("label").asString, item.get("topic").asString,
                status, age, value, item.get("reason").takeUnless { it == null || it.isJsonNull }?.asString)
        }.orEmpty()
        val details = root.getAsJsonArray("alarm_details")?.map {
            val item = it.asJsonObject
            val severity = item.get("severity").asString
            require(severity in listOf("warning", "critical", "info"))
            RobotAlarm(item.get("code").asString, severity, item.get("message").asString)
        }.orEmpty()
        val gate = root.get("control_gate").takeUnless { it == null || it.isJsonNull }?.asJsonObject?.let {
            ControlGateStatus(it.get("state").asString, it.get("ready")?.asBoolean ?: false,
                it.getAsJsonArray("reasons")?.map { reason -> reason.asString }.orEmpty())
        }
        val dryRun = root.get("control_dry_run")?.asBoolean ?: false
        val output = root.get("simulated_base_output").baseOutput()
        require(output == null || simulated && dryRun) { "Salida simulada incoherente" }
        val manualLimit = root.getAsJsonObject("manual_drive_limits")?.get("linear_m_s")?.asDouble
            ?: DEFAULT_MANUAL_LIMIT_MPS
        require(manualLimit.isFinite() && manualLimit > 0)
        val stereo = root.getAsJsonObject("stereo")?.let {
            StereoReading(it.get("status").asString, it.get("frame_id")?.takeUnless { value -> value.isJsonNull }?.asString,
                it.getAsJsonArray("lemons").map { entry ->
                    val point = entry.asJsonObject
                    Position3D(point.get("x_m").asDouble, point.get("y_m").asDouble, point.get("z_m").asDouble)
                })
        }
        return BridgeTelemetry(simulated, source, root.get("upstream_available").asBoolean,
            root.get("base_state").takeUnless { it == null || it.isJsonNull }?.asString, battery, gps,
            root.get("alarms").takeUnless { it == null || it.isJsonNull }?.asJsonArray?.map { it.asString },
            sensors, details, root.get("arm_state").takeUnless { it == null || it.isJsonNull }?.asString,
            gate, dryRun, output, physical, root.get("manual_arm_ready")?.asBoolean,
            root.get("manual_analog")?.asBoolean == true, manualLimit,
            root.get("manual_servo_positions")?.asBoolean == true, stereo,
            root.getAsJsonObject("navigation_origin")?.decodeNavigationOrigin(),
            root.getAsJsonObject("collection")?.decodeCollectionStatus())
    }
}

/** Se utiliza desde el hilo principal; OkHttp solo escribe en el canal. */
class BridgeConnection {
    private val client = OkHttpClient.Builder().connectTimeout(4, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS).callTimeout(6, TimeUnit.SECONDS).build()
    private val controlClient = client.newBuilder().callTimeout(225, TimeUnit.MILLISECONDS)
        .retryOnConnectionFailure(false).build()
    var connected by mutableStateOf(false)
        private set
    var telemetry by mutableStateOf<BridgeTelemetry?>(null)
        private set
    var status by mutableStateOf("Sin conexión")
        private set
    var sendStatus by mutableStateOf("")
        private set
    var sending by mutableStateOf(false)
        private set
    val track = mutableStateListOf<GpsFix>()
    private val clientId = UUID.randomUUID().toString()
    var controlStatus by mutableStateOf<ControlGateStatus?>(null)
        private set

    suspend fun observe(base: String, token: String) {
        val endpoint = runCatching { BridgeProtocol.endpoint(base).newBuilder().addPathSegments("api/v1/telemetry").build() }
            .getOrElse { status = "Dirección inválida: ${it.message}"; return }
        track.clear(); sendStatus = ""
        var retry = 1000L
        try {
            while (currentCoroutineContext().isActive) {
                status = "Conectando…"
                val messages = Channel<String>(Channel.CONFLATED)
                val socket = client.newWebSocket(Request.Builder().url(endpoint)
                    .header("Authorization", "Bearer ${token.trim()}").build(), object : WebSocketListener() {
                    override fun onMessage(webSocket: WebSocket, text: String) { messages.trySend(text) }
                    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                        messages.close(IllegalStateException(if (response?.code == 401 || response?.code == 403) "Revisá la clave de conexión" else "Conexión interrumpida"))
                    }
                    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) { messages.close() }
                    override fun onClosing(webSocket: WebSocket, code: Int, reason: String) { webSocket.close(code, null) }
                })
                try {
                    while (currentCoroutineContext().isActive) {
                        val value = BridgeProtocol.decode(withTimeout(5000) { messages.receive() })
                        telemetry = value; connected = true; status = "Conectado"; retry = 1000
                        value.gps?.let { fix ->
                            if (track.isEmpty() || fix.timestampMillis > track.last().timestampMillis) {
                                track.add(fix)
                                if (track.size > 600) track.removeAt(0)
                            }
                        }
                    }
                } catch (e: CancellationException) {
                    if (e !is TimeoutCancellationException) throw e
                    status = "Sin mensajes recientes. Reconectando…"
                } catch (_: Exception) {
                    status = "No se reciben datos válidos. Revisá dirección, clave y puente. Reintentando…"
                } finally { socket.cancel(); messages.cancel(); connected = false; telemetry = null; controlStatus = null }
                delay(retry); retry = (retry * 2).coerceAtMost(15000)
            }
        } finally { connected = false; telemetry = null; status = "Conexión pausada o desconectada" }
    }

    suspend fun sendFence(base: String, token: String, payload: String) {
        if (!connected || sending) return
        sending = true; sendStatus = "Enviando…"
        try {
            val result = withContext(Dispatchers.IO) {
                val url = BridgeProtocol.endpoint(base).newBuilder().addPathSegments("api/v1/geofence").build()
                client.newCall(Request.Builder().url(url).header("Authorization", "Bearer ${token.trim()}")
                    .put(payload.toRequestBody("application/geo+json".toMediaType())).build()).execute().use { response ->
                    require(response.isSuccessful) { "El puente rechazó el envío (${response.code})" }
                    val body = response.body?.string().orEmpty()
                    require(body.length <= 64000)
                    val json = JsonParser.parseString(body).asJsonObject
                    require(json.get("accepted").asBoolean && !json.get("applied_to_robot").asBoolean)
                    "Geocerca recibida y guardada en el puente. No aplicada al robot."
                }
            }
            sendStatus = result
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) { sendStatus = "No se confirmó el envío. Revisá la conexión antes de reintentar." }
        finally { sending = false }
    }

    suspend fun prepareControl(base: String, token: String, physicalReady: Boolean) = controlRequest(
        base, token, "prepare", "POST",
        """{"app_foreground":true,"physical_ready":$physicalReady,"mode":"manual"}""")

    suspend fun confirmControl(base: String, token: String) =
        controlRequest(base, token, "confirm", "POST", "{}")

    suspend fun heartbeat(base: String, token: String, deadman: Boolean) = controlRequest(
        base, token, "heartbeat", "POST", """{"deadman":$deadman}""")

    suspend fun simulateBaseVelocity(base: String, token: String, linear: Double, angular: Double): ControlGateStatus? {
        if (!connected || telemetry?.simulatedBaseOutput == null) return null
        return controlRequest(base, token, "manual/base", "POST",
            """{"linear_m_s":$linear,"angular_rad_s":$angular,"deadman":true}""")
    }

    suspend fun stopControl(base: String, token: String) =
        controlRequest(base, token, "stop", "POST", "{}")

    suspend fun releaseControl(base: String, token: String) =
        controlRequest(base, token, "session", "DELETE", null)

    private suspend fun controlRequest(base: String, token: String, action: String,
        method: String, payload: String?): ControlGateStatus? {
        return try {
            val result = withContext(Dispatchers.IO) {
                val url = BridgeProtocol.endpoint(base).newBuilder().addPathSegments("api/v1/control/$action").build()
                val builder = Request.Builder().url(url).header("Authorization", "Bearer ${token.trim()}")
                    .header("X-Arturito-Client", clientId)
                val body = payload?.toRequestBody("application/json".toMediaType())
                val request = if (method == "DELETE") builder.delete().build() else builder.post(body!!).build()
                controlClient.newCall(request).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw IllegalStateException("Solicitud rechazada (${response.code})")
                    val json = JsonParser.parseString(text).asJsonObject
                    ControlGateStatus(json.get("state").asString, json.get("ready")?.asBoolean ?: false,
                        json.getAsJsonArray("reasons")?.map { it.asString }.orEmpty(),
                        json.get("dry_run").asBoolean, json.get("robot_command_sent").asBoolean,
                        json.get("simulated_base_output").baseOutput())
                }
            }
            require(result.dryRun && !result.robotCommandSent) { "El servidor no confirmó el ensayo en seco" }
            controlStatus = result
            result
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) { controlStatus = ControlGateStatus("blocked", reasons = listOf("REQUEST_FAILED")); null }
    }
}
