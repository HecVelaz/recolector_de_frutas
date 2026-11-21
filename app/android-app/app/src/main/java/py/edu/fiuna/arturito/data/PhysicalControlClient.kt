package py.edu.fiuna.arturito.data

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import androidx.compose.ui.geometry.Offset
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import py.edu.fiuna.arturito.model.mobileWording

data class PhysicalInputResult(val homingCompleted: Boolean, val servoSent: Boolean, val paused: Boolean,
    val parking: Boolean)
data class ServoTarget(val position: Int, val wrist: Boolean)

class PhysicalControlClient {
    private val client = OkHttpClient.Builder()
        .followRedirects(false).followSslRedirects(false)
        .retryOnConnectionFailure(false).callTimeout(450, TimeUnit.MILLISECONDS).build()
    private val handshake = client.newBuilder().callTimeout(4500, TimeUnit.MILLISECONDS).build()

    suspend fun open(address: String, token: String, id: String, mode: String) {
        request(address, token, id, "physical/session", "POST", JsonObject().apply {
            addProperty("mode", mode)
            addProperty("operator_present", true)
        }, handshake)
    }

    suspend fun captureOrigin(address: String, token: String): NavigationOrigin =
        request(address, token, "", "navigation/origin", "POST", JsonObject(), handshake).decodeNavigationOrigin()

    suspend fun startCollection(address: String, token: String, id: String, lemons: Int): CollectionStatus =
        request(address, token, id, "mission/session", "POST", JsonObject().apply {
            addProperty("operator_present", true)
            addProperty("lemons", lemons)
            addProperty("to_basket", true)
        }, handshake).decodeCollectionStatus()

    suspend fun collectionHeartbeat(address: String, token: String, id: String): CollectionStatus =
        request(address, token, id, "mission/heartbeat", "POST", JsonObject(), client).decodeCollectionStatus()

    suspend fun stopCollection(address: String, token: String, id: String) {
        request(address, token, id, "mission/session", "DELETE", null, client)
    }

    suspend fun input(address: String, token: String, id: String, sequence: Long, homing: Boolean, drive: Offset,
        reach: Offset, swivel: Int, servo: ServoTarget?, speedPercent: Int): PhysicalInputResult {
        val result = request(address, token, id, "physical/input", "POST", JsonObject().apply {
            addProperty("sequence", sequence)
            if (homing) addProperty("motion", "home")
            if (drive != Offset.Zero) add("drive", JsonObject().apply {
                addProperty("forward", -drive.y)
                addProperty("turn", -drive.x)
            })
            if (reach != Offset.Zero || swivel != 0) add("joints", JsonObject().apply {
                addProperty("swivel", swivel)
                addProperty("shoulder", -reach.y)
                addProperty("elbow", reach.x)
            })
            if (servo != null) addProperty(if (servo.wrist) "wrist_degrees" else "gripper_open_percent", servo.position)
            addProperty("speed_percent", speedPercent)
        }, client)
        return PhysicalInputResult(result.get("homing_completed")?.asBoolean == true,
            result.get("servo_sent")?.asBoolean == true, result.get("paused")?.asBoolean == true,
            result.get("homing_parking")?.asBoolean == true)
    }

    suspend fun close(address: String, token: String, id: String) {
        request(address, token, id, "physical/session", "DELETE", null, client)
    }

    private suspend fun request(address: String, token: String, id: String, path: String,
        method: String, body: JsonObject?, transport: OkHttpClient): JsonObject {
        val endpoint = BridgeProtocol.endpoint(address)
        require(endpoint.host == "127.0.0.1") { "El mando requiere conexión por el túnel local." }
        val request = Request.Builder().url(endpoint.newBuilder().addPathSegments("api/v1/$path").build())
            .header("Authorization", "Bearer ${token.trim()}")
            .header("X-Arturito-Client", id)
            .method(method, body?.toString()?.toRequestBody("application/json".toMediaType())).build()
        return suspendCancellableCoroutine { continuation ->
            val call = transport.newCall(request)
            continuation.invokeOnCancellation { call.cancel() }
            call.enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    continuation.resumeWith(Result.failure(e))
                }

                override fun onResponse(call: Call, response: Response) {
                    continuation.resumeWith(runCatching { response.use(::parseResponse) })
                }
            })
        }
    }

    private fun parseResponse(response: Response): JsonObject {
        val result = response.body?.string().orEmpty()
        if (!response.isSuccessful) {
            val detail = runCatching { JsonParser.parseString(result).asJsonObject.get("detail") }.getOrNull()
            val message = when {
                detail?.isJsonArray == true -> detail.asJsonArray.joinToString("\n") { item ->
                    item.asString.let { if (it.matches(Regex("[A-Z_]+"))) controlError(it) else it }
                }
                detail?.isJsonPrimitive == true -> detail.asString
                else -> "Solicitud rechazada (${response.code})."
            }
            throw IllegalStateException(mobileWording(message))
        }
        return JsonParser.parseString(result).asJsonObject
    }
}

private fun controlError(code: String) = when (code) {
    "ROS_UNAVAILABLE" -> "La Raspberry Pi perdió la conexión con ROS 2."
    "BASE_NOT_FRESH", "BASE_TOO_OLD" -> "La Raspberry Pi dejó de recibir el estado del Móvil."
    "BASE_SAFETY_NOT_OK" -> "La seguridad del Móvil impide el movimiento."
    "BASE_IMU_NOT_OK" -> "La IMU del Móvil perdió sus datos."
    "ODOM_NOT_FRESH", "ODOM_TOO_OLD" -> "La Raspberry Pi dejó de recibir la odometría de las ruedas."
    "RANGE_FRONT_NOT_FRESH", "RANGE_FRONT_TOO_OLD" -> "La Raspberry Pi dejó de recibir la distancia frontal."
    "BATTERY_TOO_LOW_OR_UNKNOWN" -> "Tensión de batería insuficiente o desconocida."
    "BASE_CRITICAL_FLAG" -> "Hay una condición crítica en el Móvil. Revisá Estado."
    "BUMPER_ACTIVE_OR_UNKNOWN" -> "Hay un contacto activo o sin confirmar."
    else -> code.removePrefix("BASE_").replace('_', ' ').lowercase().replaceFirstChar { it.uppercase() }
}
