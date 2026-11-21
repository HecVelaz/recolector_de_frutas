package py.edu.fiuna.arturito.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalInspectionMode
import py.edu.fiuna.arturito.data.GeofenceStorage
import py.edu.fiuna.arturito.data.BridgeConnection
import py.edu.fiuna.arturito.data.DEFAULT_MANUAL_LIMIT_MPS
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import py.edu.fiuna.arturito.model.*
import py.edu.fiuna.arturito.ui.components.*
import py.edu.fiuna.arturito.ui.screens.*
import py.edu.fiuna.arturito.ui.theme.ArturitoTheme

@Composable
fun RobotApp(initialTab: String = "Control", dark: Boolean = false, onToggleTheme: () -> Unit = {}) {
    var tab by rememberSaveable { mutableStateOf(initialTab) }
    var state by remember { mutableStateOf(RobotState.INACTIVO) }
    var direction by remember { mutableStateOf<ManualDirection?>(null) }
    var heldTestDirection by remember { mutableStateOf<ManualDirection?>(null) }
    var selectedMission by rememberSaveable { mutableIntStateOf(0) }
    var progress by remember { mutableFloatStateOf(0f) }
    var running by remember { mutableStateOf(false) }
    val mapSession = remember { MapSession() }
    val context = LocalContext.current
    val inspection = LocalInspectionMode.current
    val preferences = remember(context) { context.getSharedPreferences("bridge", android.content.Context.MODE_PRIVATE) }
    var address by rememberSaveable { mutableStateOf(if (inspection) "" else preferences.getString("address", "http://192.168.1.159:8001").orEmpty()) }
    var token by rememberSaveable { mutableStateOf(if (inspection) "" else preferences.getString("token", "").orEmpty()) }
    var bridgeEnabled by rememberSaveable {
        mutableStateOf(!inspection && token.isNotBlank() && preferences.getBoolean("autoConnect", true))
    }
    var foreground by remember { mutableStateOf(true) }
    val bridge = remember { BridgeConnection() }
    val scope = rememberCoroutineScope()
    val fenceStorage = remember(context) { GeofenceStorage(context.applicationContext) }
    val fenceSession = remember {
        GeofenceSession().apply {
            if (!inspection) runCatching { fenceStorage.load() }.onSuccess { if (it != null) load(it, initial = true) }
                .onFailure { message = "No se pudo recuperar el archivo guardado. Podés crear un nuevo borrador." }
        }
    }
    val events = remember { mutableStateListOf("Interfaz iniciada en simulación") }

    fun record(message: String) {
        events.add(message)
        if (events.size > 30) events.removeAt(0)
    }
    fun stop() {
        val active = direction != null || running
        direction = null
        running = false
        if (state != RobotState.EMERGENCIA) state = RobotState.INACTIVO
        if (active) record("Movimiento y misión detenidos")
    }
    fun navigate(destination: String) {
        if (direction != null) stop()
        heldTestDirection = null
        if (tab == "Control" && destination != tab && bridge.controlStatus?.state in listOf("ready", "enabled", "active")) {
            scope.launch { bridge.stopControl(address, token) }
        }
        tab = destination
    }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_PAUSE) {
                foreground = false
                heldTestDirection = null
                stop(); mapSession.playing = false
                if (bridgeEnabled) scope.launch { bridge.stopControl(address, token); bridge.releaseControl(address, token) }
            }
            if (event == Lifecycle.Event.ON_RESUME) foreground = true
            if (event == Lifecycle.Event.ON_STOP) foreground = false
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    BackHandler(tab != "Control") { navigate("Control") }

    LaunchedEffect(bridgeEnabled, foreground, address, token) {
        if (bridgeEnabled && foreground && !inspection) bridge.observe(address, token)
    }

    val sessionEnabled = bridge.controlStatus?.state in listOf("enabled", "active")
    val telemetry = bridge.telemetry
    val physical = telemetry?.physicalManual == true
    val localTunnel = runCatching { py.edu.fiuna.arturito.data.BridgeProtocol.endpoint(address).host == "127.0.0.1" }
        .getOrDefault(false)
    LaunchedEffect(sessionEnabled, bridgeEnabled, bridge.connected, foreground, tab) {
        if (!sessionEnabled || !bridgeEnabled || !bridge.connected || !foreground || tab != "Control") {
            heldTestDirection = null
            return@LaunchedEffect
        }
        while (true) {
            val result = when (heldTestDirection) {
                ManualDirection.FORWARD -> bridge.simulateBaseVelocity(address, token, 0.1, 0.0)
                ManualDirection.BACKWARD -> bridge.simulateBaseVelocity(address, token, -0.1, 0.0)
                ManualDirection.LEFT -> bridge.simulateBaseVelocity(address, token, 0.0, 0.2)
                ManualDirection.RIGHT -> bridge.simulateBaseVelocity(address, token, 0.0, -0.2)
                null -> bridge.heartbeat(address, token, deadman = false)
            }
            if (result == null) break
            delay(80)
        }
    }

    LaunchedEffect(tab, mapSession.playing) {
        while (tab == "Mapa" && mapSession.playing) { delay(1000); mapSession.tick() }
    }

    LaunchedEffect(running) {
        while (running) {
            delay(500)
            progress = (progress + 0.025f).coerceAtMost(1f)
            val next = missionState(progress)
            if (state != next) { state = next; record("Misión: ${next.label}") }
            if (progress >= 1f) { running = false; record("Simulación completada") }
        }
    }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        BoxWithConstraints(Modifier.safeDrawingPadding()) {
            if (maxWidth < 760.dp || maxHeight < 460.dp) {
                Column(Modifier.fillMaxSize().padding(32.dp), verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Arturito R2D2", style = MaterialTheme.typography.headlineMedium)
                    Spacer(Modifier.height(16.dp))
                    Text("Usá la tablet en horizontal y ampliá la ventana para ver el panel de control.")
                    Spacer(Modifier.height(16.dp))
                    Badge("SIMULACIÓN", warning = true)
                }
            } else {
                Column(Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        ConsoleNavigation(tab, ::navigate, dark, onToggleTheme)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically) {
                            Column {
                                Text(tab, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold)
                                Text(when (tab) {
                                    "Control" -> "Tracción, brazo y pinza"
                                    "Visión" -> "Cámaras del robot"
                                    "Misión" -> "Planificación de la recolección"
                                    "Mapa" -> "Posición y área de trabajo"
                                    "Estado" -> "Conexiones, sensores y alertas"
                                    else -> "Enlace con la Raspberry Pi"
                                }, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    style = MaterialTheme.typography.bodySmall)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                StatusLight(when {
                                    bridge.connected -> "Puente conectado"
                                    bridgeEnabled -> "Buscando el robot"
                                    else -> "Simulación local"
                                }, if (bridge.connected) Signal.Ready else Signal.Off)
                                if (!bridgeEnabled && tab == "Control") {
                                Button(onClick = {
                                    direction = null; running = false; mapSession.playing = false; state = RobotState.EMERGENCIA
                                    record("Emergencia simulada activada"); tab = "Estado"
                                }, enabled = state != RobotState.EMERGENCIA,
                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error,
                                        contentColor = MaterialTheme.colorScheme.onError)) {
                                    Text("Emergencia simulada")
                                }
                                }
                            }
                        }
                        Box(Modifier.weight(1f)) {
                            when {
                                tab == "Visión" -> VisionScreen(address, token, bridgeEnabled && bridge.connected && foreground,
                                    telemetry?.stereo?.takeIf { bridge.connected })
                                tab == "Conexión" -> ConnectionScreen(bridge, bridgeEnabled, address, token,
                                    onAddress = { address = it }, onToken = { token = it },
                                    onConnect = {
                                        stop(); mapSession.playing = false
                                        preferences.edit().putString("address", address.trim()).putString("token", token.trim())
                                            .putBoolean("autoConnect", true).apply()
                                        bridgeEnabled = true
                                    }, onDisconnect = {
                                        scope.launch { bridge.stopControl(address, token); bridge.releaseControl(address, token) }
                                        preferences.edit().putBoolean("autoConnect", false).apply()
                                        bridgeEnabled = false
                                    })
                                bridgeEnabled && tab == "Mapa" -> BridgeMapScreen(bridge, fenceSession, fenceStorage, address, token)
                                bridgeEnabled && tab == "Estado" -> RobotDashboard(bridge)
                                bridgeEnabled && tab in listOf("Control", "Misión") && localTunnel && telemetry?.controlDryRun != true ->
                                    PhysicalControlScreen(address, token, telemetry?.armState,
                                        telemetry?.manualArmReady == true,
                                        foreground && bridge.connected && telemetry?.manualAnalog == true && telemetry.baseState != null, foreground,
                                        telemetry?.manualLimitMps ?: DEFAULT_MANUAL_LIMIT_MPS,
                                        telemetry?.measuredLinearMps, telemetry?.servoPositions, telemetry,
                                        collectionOnly = tab == "Misión") { navigate("Mapa") }
                                bridgeEnabled && tab == "Misión" -> LiveMissionScreen { navigate("Mapa") }
                                bridgeEnabled && tab == "Control" && physical -> {
                                    IllustratedPlaceholder(Figure.Link, "Mando físico no disponible",
                                        if (bridge.telemetry?.manualAnalog == false) "El puente necesita la actualización de los joysticks."
                                        else "Revisá el enlace por USB en Conexión.", Modifier.fillMaxSize())
                                }
                                bridgeEnabled && tab == "Control" && bridge.telemetry?.controlDryRun == true -> ControlPreparationScreen(bridge,
                                    heldDirection = heldTestDirection,
                                    onHeld = { selected, held ->
                                        if (held && heldTestDirection == null) heldTestDirection = selected
                                        if (!held && heldTestDirection == selected) heldTestDirection = null
                                    },
                                    onPrepare = { physical -> scope.launch { bridge.prepareControl(address, token, physical) } },
                                    onConfirm = { scope.launch { bridge.confirmControl(address, token) } },
                                    onStop = {
                                        heldTestDirection = null
                                        scope.launch { bridge.stopControl(address, token) }
                                    })
                                bridgeEnabled -> IllustratedPlaceholder(Figure.Drive, "Mando en espera",
                                    "El mando físico aparece al conectar con el puente del robot.", Modifier.fillMaxSize()) {
                                    Button(onClick = { navigate("Conexión") }) { Text("Ver conexión") }
                                }
                                else -> when (tab) {
                                "Control" -> ControlScreen(state, direction, running, onHeld = { pressedDirection, held ->
                                    if (held && !running && state != RobotState.EMERGENCIA) {
                                        if (direction == null) { direction = pressedDirection; state = RobotState.TELEOP }
                                    } else if (!held && direction == pressedDirection) {
                                        direction = null
                                        if (state == RobotState.TELEOP) state = RobotState.INACTIVO
                                    }
                                }, onStop = { stop() }, onMission = { navigate("Misión") })
                                "Misión" -> MissionScreen(state, selectedMission, progress, running,
                                    onSelect = { selectedMission = it; progress = 0f; state = RobotState.INACTIVO },
                                    onStart = {
                                        direction = null; progress = 0f; running = true; state = RobotState.NAVEGANDO
                                        record("Iniciada: ${demoMissions[selectedMission]}")
                                    }, onCancel = { stop(); record("Misión cancelada") })
                                "Mapa" -> MapScreen(mapSession, state == RobotState.EMERGENCIA, fenceSession, fenceStorage)
                                else -> StatusScreen(state, events) {
                                    state = RobotState.INACTIVO; progress = 0f; record("Emergencia simulada restablecida")
                                }
                                }
                            }
                        }
                }
            }
        }
    }
}

@Preview(name = "Control · tablet", widthDp = 1280, heightDp = 800, showBackground = true)
@Composable
private fun ControlPreview() { ArturitoTheme { RobotApp() } }

@Preview(name = "Misión · tablet", widthDp = 1280, heightDp = 800, showBackground = true)
@Composable
private fun MissionPreview() { ArturitoTheme { RobotApp(initialTab = "Misión") } }

@Preview(name = "Estado · tablet", widthDp = 1280, heightDp = 800, showBackground = true)
@Composable
private fun StatusPreview() { ArturitoTheme { RobotApp(initialTab = "Estado") } }
