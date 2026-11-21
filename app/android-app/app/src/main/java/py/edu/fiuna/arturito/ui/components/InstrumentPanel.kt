package py.edu.fiuna.arturito.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

enum class Signal(val lightInk: Color, val lightFill: Color, val darkInk: Color, val darkFill: Color) {
    Ready(Color(0xFF245892), Color(0xFFE0E8F3), Color(0xFFB7D2F5), Color(0xFF293847)),
    Notice(Color(0xFF9E2437), Color(0xFFF7E4E8), Color(0xFFFFB9C3), Color(0xFF43292E)),
    Fault(Color(0xFF831725), Color(0xFFF5CED7), Color(0xFFFFBCC4), Color(0xFF602931)),
    Off(Color(0xFF565E5D), Color(0xFFE8EBE8), Color(0xFFCCD0CD), Color(0xFF363A39))
}

@Composable
fun StatusLight(label: String, signal: Signal, modifier: Modifier = Modifier) {
    val dark = MaterialTheme.colorScheme.surface.luminance() < .4f
    val ink = if (dark) signal.darkInk else signal.lightInk
    val fill = if (dark) signal.darkFill else signal.lightFill
    Row(modifier.background(fill, CircleShape).padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
        Box(Modifier.size(9.dp).background(ink, CircleShape))
        Text(label, color = ink, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun CircleOption(label: String, checked: Boolean, onChange: (Boolean) -> Unit, enabled: Boolean = true) {
    val colors = MaterialTheme.colorScheme
    val accent = if (enabled) colors.primary else colors.outline
    Row(Modifier.heightIn(min = 48.dp).clip(CircleShape)
        .toggleable(checked, enabled = enabled, role = Role.Checkbox, onValueChange = onChange)
        .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(11.dp)) {
        Canvas(Modifier.size(21.dp).border(1.5.dp, accent, CircleShape)) {
            if (checked) {
                drawCircle(accent)
                val stroke = 1.7.dp.toPx()
                val start = Offset(size.width * .28f, size.height * .51f)
                val joint = Offset(size.width * .44f, size.height * .66f)
                val end = Offset(size.width * .73f, size.height * .36f)
                drawLine(colors.onPrimary, start, joint, stroke, StrokeCap.Round)
                drawLine(colors.onPrimary, joint, end, stroke, StrokeCap.Round)
            }
        }
        Text(label, color = if (enabled) colors.onSurface else colors.onSurfaceVariant,
            style = MaterialTheme.typography.bodyMedium)
    }
}

enum class Figure { Drive, Arm, Camera, Mission, Map, Status, Link, Battery, Bridge, Ros, Sun, Moon }

@Composable
fun IllustratedPlaceholder(figure: Figure, title: String, body: String, modifier: Modifier = Modifier,
    action: @Composable () -> Unit = {}) {
    Surface(modifier, color = MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.large) {
        Column(Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(9.dp, Alignment.CenterVertically)) {
            InstrumentArt(figure, Modifier.size(78.dp))
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(body, color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodyMedium, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
            action()
        }
    }
}

@Composable
fun InstrumentArt(figure: Figure, modifier: Modifier = Modifier, ink: Color = MaterialTheme.colorScheme.primary,
    guide: Color = ink.copy(alpha = .32f)) {
    Canvas(modifier) {
        val s = size.minDimension / 48
        val cx = size.width / 2
        val cy = size.height / 2
        fun p(x: Int, y: Int) = Offset(cx + x * s, cy + y * s)
        fun line(x1: Int, y1: Int, x2: Int, y2: Int, color: Color = ink, width: Float = 2.7f) =
            drawLine(color, p(x1, y1), p(x2, y2), width * s, StrokeCap.Round)
        fun circle(x: Int, y: Int, r: Float, color: Color = ink, filled: Boolean = false) {
            if (filled) drawCircle(color, r * s, p(x, y))
            else drawCircle(color, r * s, p(x, y), style = Stroke(2.7f * s))
        }
        fun rect(x: Int, y: Int, w: Int, h: Int, color: Color = ink, filled: Boolean = false) {
            val dimensions = Size(w * s, h * s)
            if (filled) drawRoundRect(color, p(x, y), dimensions, CornerRadius(3 * s))
            else drawRoundRect(color, p(x, y), dimensions, CornerRadius(3 * s), style = Stroke(2.7f * s))
        }
        when (figure) {
            Figure.Drive -> {
                rect(-10, -15, 20, 30)
                rect(-17, -12, 5, 9, filled = true); rect(12, -12, 5, 9, filled = true)
                rect(-17, 4, 5, 9, filled = true); rect(12, 4, 5, 9, filled = true)
                line(0, -7, 0, 6); line(-4, -3, 0, -7); line(4, -3, 0, -7)
            }
            Figure.Arm -> {
                line(-17, 16, 0, 16); line(-10, 12, -4, -9, ink, 5f); line(-4, -9, 13, -4, ink, 5f)
                circle(-10, 12, 3.1f, guide, true); circle(-4, -9, 3.1f, guide, true)
                line(13, -4, 17, 1); line(17, 1, 20, -2); line(17, 1, 18, 6)
                line(-20, 19, 19, 19, guide)
            }
            Figure.Camera -> {
                rect(-19, -11, 38, 23); circle(0, 0, 6f)
                line(-9, -11, -5, -16); line(-5, -16, 5, -16); line(5, -16, 9, -11)
                circle(13, -5, 1.5f, guide, true)
            }
            Figure.Mission -> {
                line(-16, 13, -5, 3, guide); line(-5, 3, 4, 8, guide); line(4, 8, 14, -9, guide)
                circle(-16, 13, 3f, filled = true); circle(-5, 3, 3f, filled = true)
                circle(4, 8, 3f, filled = true); circle(14, -9, 6f); circle(14, -9, 2.1f, filled = true)
            }
            Figure.Map -> {
                line(-17, -11, -17, 13); line(-17, -11, -6, -15); line(-17, 13, -6, 9)
                line(-6, -15, 6, -10); line(-6, 9, 6, 14); line(-6, -15, -6, 9)
                line(6, -10, 17, -14); line(6, 14, 17, 10); line(17, -14, 17, 10); line(6, -10, 6, 14)
            }
            Figure.Status -> {
                circle(0, 0, 18f)
                line(-13, 1, -8, 1); line(-8, 1, -3, -8); line(-3, -8, 2, 8)
                line(2, 8, 7, -1); line(7, -1, 13, -1)
            }
            Figure.Link -> {
                line(-11, 0, 11, 0, guide, 4f); rect(-19, -7, 12, 14); rect(7, -7, 12, 14)
                circle(-13, 0, 2f, filled = true); circle(13, 0, 2f, filled = true)
            }
            Figure.Battery -> {
                rect(-17, -8, 32, 17); line(18, -3, 18, 4)
                for (x in listOf(-11, -4, 3)) line(x, -4, x, 5, guide)
            }
            Figure.Bridge -> {
                rect(-17, -10, 34, 20); line(-12, 3, 8, 3, guide)
                for (x in listOf(-11, -5, 1)) circle(x, -4, 1.7f, filled = true)
                line(-8, 10, -8, 14); line(8, 10, 8, 14)
            }
            Figure.Ros -> {
                for (y in listOf(-10, 0, 10)) for (x in listOf(-10, 0, 10))
                    circle(x, y, 2.6f, if (x == 10 && y == -10) guide else ink, filled = true)
            }
            Figure.Sun -> {
                circle(0, 0, 7f)
                for ((x, y) in listOf(14 to 0, -14 to 0, 0 to 14, 0 to -14,
                    10 to 10, 10 to -10, -10 to 10, -10 to -10)) {
                    line(x, y, (x * 1.27f).toInt(), (y * 1.27f).toInt())
                }
            }
            Figure.Moon -> {
                val path = androidx.compose.ui.graphics.Path().apply {
                    moveTo(p(10, 11).x, p(10, 11).y)
                    quadraticTo(p(-2, 15).x, p(-2, 15).y, p(-8, 6).x, p(-8, 6).y)
                    quadraticTo(p(-16, -5).x, p(-16, -5).y, p(-3, -14).x, p(-3, -14).y)
                    quadraticTo(p(-5, 0).x, p(-5, 0).y, p(10, 11).x, p(10, 11).y)
                }
                drawPath(path, ink, style = Stroke(2.7f * s, cap = StrokeCap.Round))
            }
        }
    }
}

@Composable
fun Joystick(label: String, enabled: Boolean, modifier: Modifier = Modifier, onAxis: (Offset) -> Unit) {
    var position by remember { mutableStateOf(Offset.Zero) }
    val dispatch by rememberUpdatedState(onAxis)
    val primary = MaterialTheme.colorScheme.primary
    val handleCenter = MaterialTheme.colorScheme.onPrimary
    val surface = MaterialTheme.colorScheme.surfaceVariant
    val outline = MaterialTheme.colorScheme.outlineVariant
    Canvas(modifier.aspectRatio(1f).semantics { contentDescription = label }
        .pointerInput(enabled) {
            if (!enabled) return@pointerInput
            awaitEachGesture {
                val touch = awaitFirstDown()
                touch.consume()
                val origin = Offset(size.width / 2f, size.height / 2f)
                val travel = minOf(size.width, size.height) * .34f
                try {
                    while (true) {
                        val next = awaitPointerEvent().changes.firstOrNull { it.id == touch.id } ?: break
                        if (!next.pressed || next.isConsumed) break
                        val delta = (next.position - origin) / travel
                        val length = delta.getDistance()
                        val scale = ((length - .14f) / .86f).coerceIn(0f, 1f)
                        position = if (length > .14f) delta / length * scale else Offset.Zero
                        dispatch(position)
                        next.consume()
                    }
                } finally {
                    position = Offset.Zero
                    dispatch(Offset.Zero)
                }
            }
        }) {
        val r = size.minDimension * .47f
        drawCircle(surface, r)
        drawCircle(outline, r, style = Stroke(1.5.dp.toPx()))
        drawCircle(outline, r * .68f, style = Stroke(1.dp.toPx()))
        val tick = r * .83f
        for (vector in listOf(Offset(0f, 1f), Offset(0f, -1f), Offset(1f, 0f), Offset(-1f, 0f))) {
            drawLine(outline, center + vector * (tick - 7.dp.toPx()), center + vector * tick, 2.dp.toPx(),
                StrokeCap.Round)
        }
        val handle = center + (if (enabled) position else Offset.Zero) * (size.minDimension * .32f)
        drawCircle(if (enabled) primary else outline, r * .27f, handle)
        drawCircle(handleCenter.copy(alpha = .82f), r * .075f, handle)
    }
}
