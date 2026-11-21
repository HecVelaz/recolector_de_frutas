package py.edu.fiuna.arturito.ui.components

import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import py.edu.fiuna.arturito.model.ManualDirection

@Composable
fun SectionCard(title: String, modifier: Modifier = Modifier, compact: Boolean = false,
    colors: CardColors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    content: @Composable ColumnScope.() -> Unit) {
    Card(modifier, colors = colors) {
        Column(Modifier.padding(if (compact) 15.dp else 20.dp),
            verticalArrangement = Arrangement.spacedBy(if (compact) 7.dp else 12.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

@Composable
fun ConsoleOption(selected: Boolean, onClick: () -> Unit, label: @Composable () -> Unit,
    enabled: Boolean = true) {
    val colors = MaterialTheme.colorScheme
    FilterChip(selected, onClick, label, enabled = enabled, colors = FilterChipDefaults.filterChipColors(
        selectedContainerColor = colors.primary, selectedLabelColor = colors.onPrimary))
}

@Composable
fun Badge(text: String, warning: Boolean = false) {
    StatusLight(text, if (warning) Signal.Notice else Signal.Ready)
}

@Composable
fun DetailRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.width(12.dp))
        Text(value, Modifier.weight(1.25f), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium,
            textAlign = androidx.compose.ui.text.style.TextAlign.End)
    }
}

@Composable
fun DirectionButton(direction: ManualDirection, enabled: Boolean, onHeld: (ManualDirection, Boolean) -> Unit) {
    val interactions = remember { MutableInteractionSource() }
    val pressed by interactions.collectIsPressedAsState()
    val latestCallback by rememberUpdatedState(onHeld)
    LaunchedEffect(pressed, enabled) { latestCallback(direction, pressed && enabled) }
    DisposableEffect(Unit) { onDispose { latestCallback(direction, false) } }
    FilledTonalButton(
        onClick = {}, enabled = enabled, interactionSource = interactions,
        modifier = Modifier.size(width = 108.dp, height = 68.dp), shape = RoundedCornerShape(18.dp)
    ) { Text(direction.symbol, fontSize = 32.sp) }
}
