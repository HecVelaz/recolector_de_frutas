package py.edu.fiuna.arturito.data

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

/** Vistas del puente (20/11). En las tres se marcan los limones detectados con su distancia. */
enum class RobotCamera(val id: String, val label: String, val description: String) {
    LEFT("left", "Izquierdo", "Cámara izquierda con las detecciones de YOLO"),
    CENTER("center", "Central", "Mapa de profundidad del estéreo: cerca en rojo, lejos en azul"),
    RIGHT("right", "Derecho", "Cámara derecha con los limones del estéreo")
}

class RobotVision {
    private val client = OkHttpClient.Builder().callTimeout(2, TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false).build()

    suspend fun frame(address: String, token: String, camera: RobotCamera): Bitmap? =
        withContext(Dispatchers.IO) {
            val url = BridgeProtocol.endpoint(address).newBuilder()
                .addPathSegments("api/v1/vision/${camera.id}/frame").build()
            val request = Request.Builder().url(url)
                .header("Authorization", "Bearer ${token.trim()}").build()
            client.newCall(request).execute().use { response ->
                if (response.code == 204) return@use null
                check(response.code == 200) { "HTTP ${response.code}" }
                val body = checkNotNull(response.body)
                check(body.contentType()?.toString() == "image/jpeg")
                val source = body.source()
                check(!source.request(1_048_577)) { "Imagen demasiado grande" }
                val bytes = source.readByteArray()
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
                check(bounds.outWidth in 1..1920 && bounds.outHeight in 1..1080)
                checkNotNull(BitmapFactory.decodeByteArray(bytes, 0, bytes.size))
            }
        }
}
