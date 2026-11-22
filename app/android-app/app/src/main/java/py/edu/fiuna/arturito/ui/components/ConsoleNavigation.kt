package py.edu.fiuna.arturito.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

private val destinations = listOf("Control" to Figure.Drive, "Visión" to Figure.Camera,
    "Mapa" to Figure.Map, "Estado" to Figure.Status, "Conexión" to Figure.Link)

@Composable
fun ConsoleNavigation(tab: String, navigate: (String) -> Unit, dark: Boolean, toggleTheme: () -> Unit) {
    val colors = MaterialTheme.colorScheme
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(36.dp).background(colors.primary, CircleShape), contentAlignment = Alignment.Center) {
                InstrumentArt(Figure.Arm, Modifier.size(24.dp), ink = colors.onPrimary)
            }
            Text("Arturito", color = colors.onBackground, fontWeight = FontWeight.Bold)
        }
        Surface(Modifier.weight(1f), shape = CircleShape, color = colors.surface, shadowElevation = 1.dp) {
            Row(Modifier.padding(4.dp).selectableGroup(), horizontalArrangement = Arrangement.spacedBy(2.dp),
                verticalAlignment = Alignment.CenterVertically) {
                destinations.forEach { (label, figure) ->
                    val selected = tab == label
                    val ink = if (selected) colors.onPrimary else colors.onSurfaceVariant
                    Surface(Modifier.weight(1f), shape = CircleShape,
                        color = if (selected) colors.primary else Color.Transparent) {
                        Row(Modifier.selectable(selected, role = Role.Tab, onClick = { navigate(label) })
                            .height(42.dp).padding(horizontal = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(5.dp, Alignment.CenterHorizontally)) {
                            InstrumentArt(figure, Modifier.size(20.dp), ink)
                            Text(label, color = ink, style = MaterialTheme.typography.labelLarge, maxLines = 1,
                                overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
        }
        val themeLabel = if (dark) "Activar modo claro" else "Activar modo oscuro"
        FilledTonalIconButton(onClick = toggleTheme, modifier = Modifier.size(46.dp).semantics {
            contentDescription = themeLabel
        }, colors = IconButtonDefaults.filledTonalIconButtonColors(containerColor = colors.surface)) {
            InstrumentArt(if (dark) Figure.Sun else Figure.Moon, Modifier.size(25.dp))
        }
    }
}
