package py.edu.fiuna.arturito.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

private val LightConsole = lightColorScheme(
    primary = Color.Black, onPrimary = Color.White,
    primaryContainer = Color(0xFFE1E3E3), onPrimaryContainer = Color(0xFF181919),
    secondary = Color(0xFF505351), onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFE5E7E5), onSecondaryContainer = Color(0xFF252826),
    background = Color(0xFFE9EBE7), onBackground = Color(0xFF161817),
    surface = Color(0xFFFAFAF8), onSurface = Color(0xFF161817),
    surfaceVariant = Color(0xFFECEEEB), onSurfaceVariant = Color(0xFF535854),
    surfaceContainer = Color(0xFFF2F3F0), surfaceContainerHigh = Color(0xFFE7E9E6),
    outline = Color(0xFF727773), outlineVariant = Color(0xFFD2D6D1),
    error = Color(0xFFA12C32), onError = Color.White,
)

private val DarkConsole = darkColorScheme(
    primary = Color.White, onPrimary = Color.Black,
    primaryContainer = Color(0xFF363938), onPrimaryContainer = Color(0xFFF1F1EE),
    secondary = Color(0xFFBEC1BE), onSecondary = Color(0xFF222523),
    secondaryContainer = Color(0xFF333635), onSecondaryContainer = Color(0xFFEDEFEA),
    background = Color(0xFF161818), onBackground = Color(0xFFF0F1ED),
    surface = Color(0xFF222525), onSurface = Color(0xFFF0F1ED),
    surfaceVariant = Color(0xFF2B2E2E), onSurfaceVariant = Color(0xFFBDC1BD),
    surfaceContainer = Color(0xFF292B2B), surfaceContainerHigh = Color(0xFF333636),
    outline = Color(0xFF919693), outlineVariant = Color(0xFF444847),
    error = Color(0xFFFFB3B9), onError = Color(0xFF4D0C14),
)

@Composable
fun ArturitoTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) DarkConsole else LightConsole, shapes = Shapes(
        small = RoundedCornerShape(50), medium = RoundedCornerShape(16.dp),
        large = RoundedCornerShape(21.dp), extraLarge = RoundedCornerShape(28.dp)), content = content)
}
