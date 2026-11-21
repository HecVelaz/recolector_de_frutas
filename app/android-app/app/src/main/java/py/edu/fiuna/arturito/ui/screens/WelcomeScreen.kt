package py.edu.fiuna.arturito.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import py.edu.fiuna.arturito.R
import py.edu.fiuna.arturito.ui.theme.ArturitoTheme

@Composable
fun WelcomeScreen() {
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.safeDrawingPadding().padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(stringResource(R.string.welcome_title), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.welcome_subtitle), style = MaterialTheme.typography.titleMedium)
            Text(stringResource(R.string.project_ready), color = MaterialTheme.colorScheme.primary)
            Text(stringResource(R.string.stage_description), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Preview(name = "Tablet horizontal", widthDp = 960, heightDp = 600, showBackground = true)
@Composable
private fun WelcomePreview() {
    ArturitoTheme { WelcomeScreen() }
}
