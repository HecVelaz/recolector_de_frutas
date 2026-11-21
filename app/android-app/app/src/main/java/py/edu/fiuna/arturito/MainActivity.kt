package py.edu.fiuna.arturito

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.*
import androidx.core.view.WindowCompat
import py.edu.fiuna.arturito.ui.RobotApp
import py.edu.fiuna.arturito.ui.theme.ArturitoTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val appearance = getSharedPreferences("appearance", MODE_PRIVATE)
        setContent {
            var selected by remember { mutableStateOf(appearance.getString("theme", null)) }
            val dark = selected?.let { it == "dark" } ?: isSystemInDarkTheme()
            SideEffect {
                WindowCompat.getInsetsController(window, window.decorView).apply {
                    isAppearanceLightStatusBars = !dark
                    isAppearanceLightNavigationBars = !dark
                }
            }
            ArturitoTheme(dark) {
                RobotApp(dark = dark, onToggleTheme = {
                    selected = if (dark) "light" else "dark"
                    appearance.edit().putString("theme", selected).apply()
                })
            }
        }
    }
}
