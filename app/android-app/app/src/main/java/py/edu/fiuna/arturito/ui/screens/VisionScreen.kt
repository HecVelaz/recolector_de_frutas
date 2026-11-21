package py.edu.fiuna.arturito.ui.screens

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import py.edu.fiuna.arturito.data.RobotCamera
import py.edu.fiuna.arturito.data.RobotVision
import py.edu.fiuna.arturito.data.StereoReading
import py.edu.fiuna.arturito.ui.components.*

/** Último cuadro de una vista mientras [streaming]; se pide cada [periodMs] (el puente renueva cada ~250 ms). */
@Composable
fun rememberCameraFrame(address: String, token: String, camera: RobotCamera, streaming: Boolean,
    periodMs: Long = 300): Pair<Bitmap?, Boolean> {
    val vision = remember { RobotVision() }
    var frame by remember(address, token, streaming, camera) { mutableStateOf<Bitmap?>(null) }
    var error by remember(address, token, streaming, camera) { mutableStateOf(false) }
    LaunchedEffect(address, token, streaming, camera) {
        if (!streaming) return@LaunchedEffect
        while (true) {
            try {
                frame = vision.frame(address, token, camera)
                error = false
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                frame = null
                error = true
            }
            delay(periodMs)
        }
    }
    return frame to error
}

/** El video de una vista, o un texto mientras no llega. */
@Composable
fun CameraFeed(address: String, token: String, camera: RobotCamera, streaming: Boolean, modifier: Modifier = Modifier) {
    val (frame, error) = rememberCameraFrame(address, token, camera, streaming)
    Surface(modifier, color = MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.medium) {
        Box(contentAlignment = Alignment.Center) {
            if (frame != null) {
                Image(remember(frame) { frame.asImageBitmap() }, "Cámara ${camera.label}",
                    Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            } else {
                Text(when {
                    !streaming -> "Video en espera"
                    error -> "Imagen no disponible"
                    else -> "Esperando imagen"
                }, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun VisionScreen(address: String, token: String, active: Boolean, stereo: StereoReading? = null) {
    var camera by remember { mutableStateOf(RobotCamera.LEFT) }
    var enabled by remember { mutableStateOf(false) }
    val streaming = active && enabled
    val (frame, error) = rememberCameraFrame(address, token, camera, streaming)
    LaunchedEffect(active) { if (!active) enabled = false }
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RobotCamera.entries.forEach { choice ->
                ConsoleOption(selected = choice == camera, onClick = { camera = choice }, enabled = streaming,
                    label = { Text(choice.label) })
            }
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Ver cámaras")
            Switch(enabled, { enabled = it }, enabled = active)
            StatusLight(when {
                frame != null -> "En vivo"
                streaming && error -> "Sin imagen"
                streaming -> "Conectando"
                else -> "Apagadas"
            }, if (frame != null) Signal.Ready else if (streaming) Signal.Notice else Signal.Off)
            if (streaming) Text(camera.description, style = MaterialTheme.typography.bodySmall)
        }
        Surface(Modifier.fillMaxWidth().weight(1f), color = MaterialTheme.colorScheme.surfaceVariant,
            shape = MaterialTheme.shapes.medium) {
            Box(contentAlignment = Alignment.Center) {
                val picture = frame
                if (picture != null) {
                    Image(remember(picture) { picture.asImageBitmap() }, "Cámara ${camera.label}",
                        Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                } else {
                    IllustratedPlaceholder(Figure.Camera, when {
                        !active -> "Cámaras sin enlace"
                        !enabled -> "Cámaras apagadas"
                        error -> "Imagen no disponible"
                        else -> "Esperando imagen"
                    }, when {
                        !active -> "Conectá Arturito al robot para ver sus cámaras."
                        !enabled -> "Activá Ver cámaras cuando quieras recibir imágenes."
                        else -> camera.description
                    }, Modifier.fillMaxSize())
                }
            }
        }
        if (active) StereoTargets(stereo)
    }
}
