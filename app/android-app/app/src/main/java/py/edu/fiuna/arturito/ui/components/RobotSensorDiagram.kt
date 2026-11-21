package py.edu.fiuna.arturito.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import py.edu.fiuna.arturito.model.SensorAlert
import py.edu.fiuna.arturito.model.SensorLook

private val BODY = Color(0xFF33373B)
private val NO_DATA = Color(0xFF8A8F94)
private val SENSOR_ON = Color(0xFF1E88E5)
private val SENSOR_OFF = Color(0xFF4F6A85)
private val BUMPER_ON = Color(0xFFE53935)
private val BUMPER_OFF = Color(0xFF7A6666)
private val IMU_ON = Color(0xFF43A047)
private val IMU_OFF = Color(0xFF5A6E5C)
private val SETA_ON = Color(0xFFFF1744)
private val SETA_OFF = Color(0xFF7E3434)

/** Vista de arriba del robot (como `arturito.jpeg`): cada elemento se ilumina cuando su alerta está activa. */
@Composable
fun RobotSensorDiagram(looks: Map<SensorAlert, SensorLook>, modifier: Modifier = Modifier) {
    val measurer = rememberTextMeasurer()
    val ink = MaterialTheme.colorScheme.onSurface
    val active = looks.filterValues { it == SensorLook.ACTIVE }.keys
    Canvas(modifier.semantics {
        contentDescription = if (active.isEmpty()) "Robot sin alertas" else "Alertas: " + active.joinToString { it.label }
    }) {
        // Dibujo en una caja de 440 × 360 unidades, escalada y centrada.
        val scale = minOf(size.width / 440f, size.height / 360f)
        withTransform({
            translate((size.width - 440f * scale) / 2, (size.height - 360f * scale) / 2)
            scale(scale, scale, Offset.Zero)
        }) { robot(looks, measurer, ink) }
    }
}

private fun DrawScope.robot(looks: Map<SensorAlert, SensorLook>, measurer: TextMeasurer, ink: Color) {
    fun look(alert: SensorAlert) = looks[alert] ?: SensorLook.NO_DATA
    fun color(alert: SensorAlert, on: Color, off: Color) = when (look(alert)) {
        SensorLook.ACTIVE -> on; SensorLook.NORMAL -> off; SensorLook.NO_DATA -> NO_DATA
    }
    fun label(text: String, x: Float, y: Float, color: Color = ink, bold: Boolean = false, size: Int = 12) {
        val layout = measurer.measure(text, TextStyle(color = color, fontSize = size.sp,
            fontWeight = if (bold) FontWeight.Bold else FontWeight.Medium))
        drawText(layout, topLeft = Offset(x - layout.size.width / 2f, y - layout.size.height / 2f))
    }

    label("▲ ADELANTE", 220f, 12f, bold = true, size = 13)
    // Base en T: adelante la parte ancha (esquinas biseladas), atrás la angosta.
    drawPath(Path().apply {
        moveTo(120f, 130f); lineTo(320f, 130f); lineTo(340f, 150f); lineTo(340f, 250f)
        lineTo(100f, 250f); lineTo(100f, 150f); close()
    }, BODY)
    drawRoundRect(BODY, Offset(150f, 240f), Size(140f, 100f), CornerRadius(14f))
    label("Base del robot", 220f, 190f, Color.White, bold = true, size = 13)
    label("vista de arriba", 220f, 210f, Color(0xFFCFD3D6), size = 11)

    // Ultrasonidos: cono cuando detectan a 20 cm o menos.
    fun sonar(alert: SensorAlert, center: Offset, heading: Float, name: String, labelAt: Offset) {
        val c = color(alert, SENSOR_ON, SENSOR_OFF)
        if (look(alert) == SensorLook.ACTIVE) {
            drawArc(SENSOR_ON.copy(alpha = .35f), heading - 22f, 44f, true,
                Offset(center.x - 75f, center.y - 75f), Size(150f, 150f))
            drawCircle(SENSOR_ON.copy(alpha = .3f), 20f, center)
        }
        rotate(heading + 90f, center) {
            drawRoundRect(c, Offset(center.x - 14f, center.y - 7f), Size(28f, 14f), CornerRadius(4f))
        }
        label(name, labelAt.x, labelAt.y, if (look(alert) == SensorLook.ACTIVE) SENSOR_ON else ink,
            bold = look(alert) == SensorLook.ACTIVE)
    }
    sonar(SensorAlert.US_IZQ, Offset(110f, 140f), 225f, "Ultrasonido izq.", Offset(62f, 62f))
    sonar(SensorAlert.US_CENTRAL, Offset(220f, 130f), 270f, "Ultrasonido central", Offset(220f, 40f))
    sonar(SensorAlert.US_DER, Offset(330f, 140f), 315f, "Ultrasonido der.", Offset(378f, 62f))

    // Paragolpes: barra roja que se enciende con el contacto.
    fun bumper(alert: SensorAlert, from: Offset, to: Offset) {
        val c = color(alert, BUMPER_ON, BUMPER_OFF)
        if (look(alert) == SensorLook.ACTIVE) drawLine(BUMPER_ON.copy(alpha = .35f), from, to, 22f, StrokeCap.Round)
        drawLine(c, from, to, 10f, StrokeCap.Round)
    }
    bumper(SensorAlert.BUMPER_FRENTE, Offset(140f, 121f), Offset(196f, 121f))
    bumper(SensorAlert.BUMPER_FRENTE, Offset(244f, 121f), Offset(300f, 121f))
    bumper(SensorAlert.BUMPER_IZQ, Offset(91f, 165f), Offset(91f, 235f))
    bumper(SensorAlert.BUMPER_DER, Offset(349f, 165f), Offset(349f, 235f))
    label("Bumper", 44f, 192f, bold = look(SensorAlert.BUMPER_IZQ) == SensorLook.ACTIVE)
    label("izquierdo", 44f, 208f, bold = look(SensorAlert.BUMPER_IZQ) == SensorLook.ACTIVE)
    label("Bumper", 396f, 192f, bold = look(SensorAlert.BUMPER_DER) == SensorLook.ACTIVE)
    label("derecho", 396f, 208f, bold = look(SensorAlert.BUMPER_DER) == SensorLook.ACTIVE)
    label("Bumper frontal", 220f, 150f, Color.White, bold = look(SensorAlert.BUMPER_FRENTE) == SensorLook.ACTIVE, size = 11)

    // IMU y seta, en la parte de atrás.
    val imu = color(SensorAlert.IMU, IMU_ON, IMU_OFF)
    if (look(SensorAlert.IMU) == SensorLook.ACTIVE)
        drawRoundRect(IMU_ON.copy(alpha = .35f), Offset(164f, 264f), Size(64f, 46f), CornerRadius(10f))
    drawRoundRect(imu, Offset(172f, 272f), Size(48f, 30f), CornerRadius(6f))
    drawRoundRect(Color.White.copy(alpha = .6f), Offset(172f, 272f), Size(48f, 30f), CornerRadius(6f), style = Stroke(1.5f))
    label("IMU", 196f, 287f, Color.White, bold = true)
    label(if (look(SensorAlert.IMU) == SensorLook.ACTIVE) "¡Inclinado!" else "Inclinación", 196f, 324f,
        Color(0xFFCFD3D6), bold = look(SensorAlert.IMU) == SensorLook.ACTIVE, size = 10)

    val seta = color(SensorAlert.SETA, SETA_ON, SETA_OFF)
    if (look(SensorAlert.SETA) == SensorLook.ACTIVE) drawCircle(SETA_ON.copy(alpha = .35f), 27f, Offset(254f, 287f))
    drawCircle(seta, 17f, Offset(254f, 287f))
    drawCircle(Color.White.copy(alpha = .6f), 17f, Offset(254f, 287f), style = Stroke(1.5f))
    label(if (look(SensorAlert.SETA) == SensorLook.ACTIVE) "¡SETA!" else "Seta", 254f, 324f,
        Color(0xFFCFD3D6), bold = look(SensorAlert.SETA) == SensorLook.ACTIVE, size = 10)
}
