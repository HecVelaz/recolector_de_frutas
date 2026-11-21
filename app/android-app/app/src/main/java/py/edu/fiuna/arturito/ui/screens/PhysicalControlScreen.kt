package py.edu.fiuna.arturito.ui.screens

import android.os.SystemClock
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.util.Locale
import java.util.UUID
import java.io.IOException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import py.edu.fiuna.arturito.data.BridgeTelemetry
import py.edu.fiuna.arturito.data.PhysicalControlClient
import py.edu.fiuna.arturito.data.ServoTarget
import py.edu.fiuna.arturito.model.ArmReadings
import py.edu.fiuna.arturito.ui.components.*
import kotlin.math.roundToInt

private const val WARNING_SPEED = 24
private const val MAXIMUM_SELECTION = 42
private const val RECOVERY_WINDOW_MS = 2000L

@Composable
fun PhysicalControlScreen(address: String, token: String, armState: String?, referenced: Boolean,
    baseAvailable: Boolean, foreground: Boolean, linearLimitMps: Double, measuredLinearMps: Double?,
    servoPositions: Boolean?, telemetry: BridgeTelemetry?, collectionOnly: Boolean = false, onMap: () -> Unit) {
    val client = remember { PhysicalControlClient() }
    val scope = rememberCoroutineScope()
    var collection by remember(collectionOnly) { mutableStateOf(collectionOnly) }
    var missionId by remember { mutableStateOf<String?>(null) }
    var lemonCount by remember { mutableIntStateOf(1) }
    var captureBusy by remember { mutableStateOf(false) }
    var parking by remember { mutableStateOf(false) }
    var showBase by remember { mutableStateOf(false) }
    var showArm by remember { mutableStateOf(false) }
    var session by remember { mutableStateOf<String?>(null) }
    var active by remember { mutableStateOf(false) }
    var recovering by remember { mutableStateOf(false) }
    var inputGeneration by remember { mutableIntStateOf(0) }
    var closing by remember { mutableStateOf(false) }
    var homing by remember { mutableStateOf(false) }
    var homeDone by remember { mutableStateOf<String?>(null) }   // aviso de reposo confirmado (ángulos medidos)
    var confirmRun by remember { mutableStateOf<String?>(null) }
    var drive by remember { mutableStateOf(Offset.Zero) }
    var reach by remember { mutableStateOf(Offset.Zero) }
    var swivel by remember { mutableIntStateOf(0) }
    var servo by remember { mutableStateOf<ServoTarget?>(null) }
    var message by remember { mutableStateOf("") }
    var failed by remember { mutableStateOf(false) }
    var speed by remember { mutableIntStateOf(4) }
    var pendingSpeed by remember { mutableStateOf<Int?>(null) }
    var highSpeedAccepted by remember { mutableStateOf(false) }
    val arm = ArmReadings.decode(armState)
    val armStateNow by rememberUpdatedState(armState)
    val idle = session == null && !closing && missionId == null && telemetry?.collection?.active != true
    val moving = active && session != null && !homing
    val mode = if (showBase && showArm) "combined" else if (showBase) "base" else "arm"
    val limitCmS = linearLimitMps * 100
    val maximumSpeed = limitCmS.roundToInt().coerceIn(2, MAXIMUM_SELECTION)
    val appliedCmS = speed.toDouble().coerceAtMost(limitCmS)
    val speedPercent = (100 * appliedCmS / limitCmS).roundToInt().coerceIn(0, 100)
    val liveSpeedPercent by rememberUpdatedState(speedPercent)

    fun neutral() {
        drive = Offset.Zero
        reach = Offset.Zero
        swivel = 0
        servo = null
    }
    fun closeSession() {
        if (session != null) closing = true
        session = null
        neutral()
    }
    fun startSession(home: Boolean) {
        if (!idle) return
        homing = home
        failed = false
        message = ""
        session = UUID.randomUUID().toString()
    }
    fun selectSpeed(value: Float) {
        val next = value.roundToInt().coerceIn(0, maximumSpeed)
        if (pendingSpeed != null) return
        if (next > WARNING_SPEED && !highSpeedAccepted) pendingSpeed = next
        else {
            speed = next
            if (next <= WARNING_SPEED) highSpeedAccepted = false
        }
    }

    // Homing automático (20/11): un toque y confirmar; el puente busca los finales de carrera, fija los ceros y lleva
    // el brazo al reposo (mv 3 17 4) mientras la app siga conectada y en primer plano. Cancelar frena el brazo (s)
    fun requestHome() {
        if (idle && !captureBusy) confirmRun = "homing"
    }
    fun cancelHome() {
        if (homing && session != null) {
            failed = true
            message = "Homing cancelado: el brazo quedó frenado donde estaba. Volvé a hacer el homing."
            closeSession()
        }
    }

    fun captureOrigin() {
        if (captureBusy || !idle) return
        scope.launch {
            captureBusy = true
            failed = false
            message = ""
            try {
                client.captureOrigin(address, token)
                message = "Cero del Móvil guardado desde la posición actual."
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                failed = true
                message = error.message ?: "No se pudo medir la marca."
            } finally {
                captureBusy = false
            }
        }
    }

    LaunchedEffect(collectionOnly) {
        closeSession()
        missionId = null
    }
    LaunchedEffect(foreground) {
        if (!foreground) missionId = null
        if (!foreground && session != null) {
            closeSession()
        }
    }

    LaunchedEffect(missionId, address, token) {
        val id = missionId ?: return@LaunchedEffect
        try {
            client.startCollection(address, token, id, lemonCount)
            while (client.collectionHeartbeat(address, token, id).active) delay(250)
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            if (missionId == id) {
                failed = true
                message = if (error is IOException) "Se perdió el enlace de supervisión."
                    else error.message ?: "Se interrumpió la recolección."
            }
        } finally {
            withContext(NonCancellable) {
                runCatching { client.stopCollection(address, token, id) }
                if (missionId == id) missionId = null
            }
        }
    }

    LaunchedEffect(session, address, token) {
        val id = session ?: return@LaunchedEffect
        var sequence = 0L
        var recoveryStartedAt: Long? = null
        fun pauseInputs() {
            if (recoveryStartedAt == null) {
                recoveryStartedAt = SystemClock.elapsedRealtime()
                inputGeneration += 1
            }
            active = false
            recovering = true
            neutral()
        }
        try {
            client.open(address, token, id, if (homing) "homing" else mode)
            while (true) {
                val allowInput = active && !recovering
                val nextServo = if (allowInput) servo else null
                val result = try {
                    client.input(address, token, id, ++sequence, homing,
                        if (allowInput) drive else Offset.Zero, if (allowInput) reach else Offset.Zero,
                        if (allowInput) swivel else 0, nextServo, liveSpeedPercent)
                } catch (e: IOException) {
                    if (homing) throw IllegalStateException("Se interrumpió la conexión durante el homing.", e)
                    pauseInputs()
                    if (SystemClock.elapsedRealtime() - checkNotNull(recoveryStartedAt) >= RECOVERY_WINDOW_MS) throw e
                    delay(70)
                    continue
                }
                if (result.paused) {
                    pauseInputs()
                    continue
                }
                if (recovering) neutral()
                recoveryStartedAt = null
                recovering = false
                active = true
                if (result.servoSent && servo == nextServo) servo = null
                parking = result.parking
                if (result.homingCompleted) {
                    message = "Homing terminado: ceros confirmados y brazo en reposo."
                    homeDone = ArmReadings.decode(armStateNow)?.joints?.let { j ->
                        "J1 ${number(j[0].angleDegrees)}° · J2 ${number(j[1].angleDegrees)}° · J3 ${number(j[2].angleDegrees)}°"
                    } ?: "J1 3° · J2 17° · J3 4°"
                    closeSession()
                    break
                }
                delay(50)
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            if (session == id) {
                message = if (e is IOException) "El puente no respondió. Revisá la conexión y volvé a habilitar el mando."
                    else e.message ?: "Se interrumpió el mando. Volvé a habilitarlo."
                failed = true
                closeSession()
            }
        } finally {
            active = false
            recovering = false
            parking = false
            neutral()
            withContext(NonCancellable) {
                runCatching { client.close(address, token, id) }
                homing = false
                closing = false
            }
        }
    }

    homeDone?.let { angles ->
        AlertDialog(onDismissRequest = { homeDone = null },
            title = { Text("Brazo en reposo") },
            text = { Text("Homing terminado. Los ceros de J1, J2 y J3 se fijaron en los finales de carrera y el " +
                "brazo confirmó la llegada al reposo.\n\nMedido: $angles") },
            confirmButton = { Button(onClick = { homeDone = null }) { Text("Aceptar") } })
    }
    pendingSpeed?.let { candidate ->
        AlertDialog(onDismissRequest = { pendingSpeed = null }, title = { Text("Velocidad por encima de 24 cm/s") },
            text = { Text("El ajuste solicitado supera el umbral de velocidad segura. El límite actual del banco es de ${number(limitCmS)} cm/s.") },
            confirmButton = { Button(onClick = { speed = candidate; highSpeedAccepted = true; pendingSpeed = null }) { Text("Aceptar") } },
            dismissButton = { TextButton(onClick = { pendingSpeed = null }) { Text("Cancelar") } })
    }
    confirmRun?.let { purpose ->
        val home = purpose == "homing"
        val mission = purpose == "mission"
        AlertDialog(onDismissRequest = { confirmRun = null },
            title = { Text(if (home) "Hacer el homing del brazo" else if (mission) "Preparar la recolección" else "Preparar el mando") },
            text = {
                Text(when {
                    home -> "Con la potencia encendida y el brazo abajo y recogido, despejá su recorrido. Quedate junto al corte físico. " +
                        "El homing sigue solo: busca los finales de carrera, fija los ceros y lleva el brazo al reposo. " +
                        "Se detiene si tocás Cancelar homing, cerrás la app o se corta la conexión."
                    mission -> "El Móvil irá a la parada del arbolito y el brazo intentará llevar " +
                        (if (lemonCount == 1) "un limón" else "$lemonCount limones") + " a la canasta. Confirmá que todo el recorrido está despejado y quedate junto al corte físico."
                    showBase -> "Confirmá que el recorrido está despejado y que podés cortar la potencia."
                    else -> "Confirmá que el recorrido del brazo está despejado y que podés cortar la potencia."
                })
            },
            confirmButton = {
                Button(onClick = {
                    confirmRun = null
                    when {
                        home -> startSession(home = true)
                        mission -> {
                            failed = false
                            message = ""
                            missionId = UUID.randomUUID().toString()
                        }
                        else -> startSession(home = false)
                    }
                }) { Text(if (home) "Iniciar homing" else "Confirmar") }
            },
            dismissButton = { TextButton(onClick = { confirmRun = null }) { Text("Cancelar") } })
    }

    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (!collectionOnly) {
                ConsoleOption(!collection, {
                    if (collection) closeSession()
                    missionId = null
                    collection = false
                }, { Text("Modo manual") })
                ConsoleOption(collection, {
                    if (!collection) closeSession()
                    collection = true
                }, { Text("Modo Recolección") })
            }
            Spacer(Modifier.weight(1f))
            if (session != null) {
                Button(onClick = { closeSession() },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError)) { Text("Parar mando") }
            }
        }
        if (collection) {
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                CollectionPreparation(telemetry?.navigationOrigin, telemetry?.stereo, referenced,
                    baseAvailable && idle && !captureBusy, captureBusy, ::captureOrigin, onMap,
                    homingStatus = when {
                        parking -> "Yendo al reposo"
                        homing -> "Buscando finales de carrera"
                        else -> null
                    }, mission = telemetry?.collection, missionRequested = missionId != null,
                    canStart = baseAvailable && idle && !captureBusy && referenced &&
                        telemetry?.navigationOrigin != null && telemetry.stereo?.status in listOf("located", "searching") &&
                        telemetry.collection != null, onStart = { confirmRun = "mission" },
                    onStop = { missionId = null }, lemons = lemonCount,
                    onLemons = { if (missionId == null) lemonCount = it }) {
                    HomeButton(homing && session != null,
                        foreground && arm != null && ((baseAvailable && idle && !captureBusy) || homing && !closing),
                        ::requestHome, ::cancelHome)
                }
                if (message.isNotEmpty()) Text(message,
                    color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
            }
        } else {
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedCard {
                    Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircleOption("Control del móvil", showBase, { showBase = it }, enabled = idle)
                        CircleOption("Control del brazo", showArm, {
                            showArm = it
                        }, enabled = idle)
                        Spacer(Modifier.weight(1f))
                        if (!baseAvailable) StatusLight("Móvil sin telemetría", Signal.Notice)
                        if (session == null && (showBase || showArm)) {
                            Button(onClick = { confirmRun = "manual" }, enabled = idle && baseAvailable) { Text("Habilitar mando") }
                        } else if (session != null) {
                            StatusLight(when {
                                recovering -> "Recuperando el mando"
                                !active -> "Comprobando"
                                homing -> "Buscando el cero"
                                else -> "Mando habilitado"
                            }, if (moving) Signal.Ready else Signal.Notice)
                        }
                       }
                }
                if (showArm) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        HomeButton(homing && session != null,
                            foreground && arm != null && (baseAvailable && idle || homing && !closing),
                            ::requestHome, ::cancelHome)
                        if (!referenced) Text("Pinza y muñeca disponibles. Buscá el cero para usar los joysticks.",
                            style = MaterialTheme.typography.bodySmall)
                        if (parking) Text("Yendo al reposo.", style = MaterialTheme.typography.bodySmall)
                    }
                }
                if (message.isNotEmpty()) Text(message,
                    color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
                if (!showBase && !showArm) {
                    IllustratedPlaceholder(Figure.Drive, "Mando manual",
                        "Elegí el móvil, el brazo o ambos para ver sus mandos.", Modifier.fillMaxWidth().height(210.dp))
                }
                val generation = inputGeneration
                key(generation) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (showBase) SectionCard("Móvil", Modifier.weight(1f), compact = true) {
                            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                                Joystick("Joystick de tracción", moving && speed > 0, Modifier.size(132.dp)) {
                                    if (generation == inputGeneration) drive = it
                                }
                            }
                            Text("Velocidad solicitada: $speed cm/s", style = MaterialTheme.typography.titleSmall)
                            SpeedBar(speed, maximumSpeed, drive == Offset.Zero, ::selectSpeed)
                            Box(Modifier.fillMaxWidth()) {
                                Text("0", Modifier.align(Alignment.CenterStart), style = MaterialTheme.typography.labelMedium)
                                Text("$maximumSpeed cm/s", Modifier.align(Alignment.CenterEnd),
                                    style = MaterialTheme.typography.labelMedium)
                            }
                            val measured = measuredLinearMps?.let { " · Medida ${number(it * 100)} cm/s" }.orEmpty()
                            Text("Límite del puente: ${number(limitCmS)} cm/s$measured", style = MaterialTheme.typography.bodySmall)
                        }
                        if (showArm) SectionCard("Brazo y pinza", Modifier.weight(1f), compact = true) {
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceEvenly) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("Hombro ↑↓ · Codo ←→", style = MaterialTheme.typography.labelMedium)
                                    Joystick("Joystick de hombro y codo", moving && referenced, Modifier.size(112.dp)) {
                                        if (generation == inputGeneration) reach = it
                                    }
                                }
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("Giro J1", style = MaterialTheme.typography.labelMedium)
                                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                        HeldControl("↶", moving && referenced && swivel <= 0) { held ->
                                            if (generation != inputGeneration) return@HeldControl
                                            if (held) swivel = -1 else if (swivel < 0) swivel = 0
                                        }
                                        HeldControl("↷", moving && referenced && swivel >= 0) { held ->
                                            if (generation != inputGeneration) return@HeldControl
                                            if (held) swivel = 1 else if (swivel > 0) swivel = 0
                                        }
                                    }
                                }
                            }
                            val available = moving && servoPositions == true && servo == null
                            ServoPositions(arm, available) { if (generation == inputGeneration) servo = it }
                            if (servoPositions == false) Text("Actualizá el puente para ajustar la pinza y su giro.",
                                style = MaterialTheme.typography.bodySmall)
                        }
                 }
                }
            }
        }
    }
}

private fun number(value: Double): String = String.format(Locale.getDefault(), "%g", value).trimEnd('0').trimEnd('.', ',')

@Composable
private fun SpeedBar(value: Int, maximumSpeed: Int, enabled: Boolean, onValue: (Float) -> Unit) {
    val colors = MaterialTheme.colorScheme
    val lastStep = (maximumSpeed + 1) / 2
    val currentStep = (value.coerceAtMost(maximumSpeed) + 1) / 2
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxWidth().padding(horizontal = 10.dp).height(12.dp)) {
            val threshold = size.width * (WARNING_SPEED / 2).coerceAtMost(lastStep) / lastStep
            val position = size.width * currentStep / lastStep
            val height = 5.dp.toPx()
            drawLine(colors.outlineVariant, Offset(0f, center.y), Offset(threshold, center.y), height, StrokeCap.Round)
            drawLine(colors.error.copy(alpha = .5f), Offset(threshold, center.y), Offset(size.width, center.y), height, StrokeCap.Round)
            if (value > 0) drawLine(colors.primary, Offset(0f, center.y), Offset(position.coerceAtMost(threshold), center.y), height)
            if (value > WARNING_SPEED) drawLine(colors.error, Offset(threshold, center.y), Offset(position, center.y), height)
        }
        Slider(currentStep.toFloat(), { step -> onValue((step.roundToInt() * 2).coerceAtMost(maximumSpeed).toFloat()) },
            modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "Velocidad solicitada en centímetros por segundo"
        }, enabled = enabled, valueRange = 0f..lastStep.toFloat(), steps = lastStep - 1,
            colors = SliderDefaults.colors(
                thumbColor = if (value > WARNING_SPEED) colors.error else colors.primary,
                activeTrackColor = Color.Transparent, inactiveTrackColor = Color.Transparent,
                activeTickColor = Color.Transparent, inactiveTickColor = Color.Transparent,
                disabledActiveTrackColor = Color.Transparent, disabledInactiveTrackColor = Color.Transparent,
                disabledActiveTickColor = Color.Transparent, disabledInactiveTickColor = Color.Transparent))
    }
}

@Composable
private fun ServoPositions(arm: ArmReadings?, enabled: Boolean, onTarget: (ServoTarget) -> Unit) {
    var open by remember { mutableFloatStateOf(100f) }
    var wrist by remember { mutableFloatStateOf(0f) }
    var openTouched by remember { mutableStateOf(false) }
    var wristTouched by remember { mutableStateOf(false) }
    LaunchedEffect(arm?.gripperPulseUs) {
        if (!openTouched) arm?.gripperPulseUs?.let { open = ((1250 - it) / 7.5f).coerceIn(0f, 100f) }
    }
    LaunchedEffect(arm?.wristPulseUs) {
        if (!wristTouched) arm?.wristPulseUs?.let {
            wrist = ((1500 - it) * 90f / if (it <= 1500) 640 else 650).coerceIn(-90f, 90f)
        }
    }
    Text("Apertura: ${open.roundToInt()} %", style = MaterialTheme.typography.titleSmall)
    Slider(open, { open = it; openTouched = true }, valueRange = 0f..100f, enabled = enabled,
        modifier = Modifier.semantics { contentDescription = "Apertura de la pinza" },
        onValueChangeFinished = { if (enabled) onTarget(ServoTarget(open.roundToInt(), wrist = false)) })
    val degrees = wrist.roundToInt()
    Text("Giro de la pinza: ${if (degrees > 0) "+$degrees" else degrees.toString()}°",
        style = MaterialTheme.typography.titleSmall)
    Slider(wrist, { wrist = it; wristTouched = true }, valueRange = -90f..90f, enabled = enabled,
        modifier = Modifier.semantics { contentDescription = "Giro de la pinza" },
        onValueChangeFinished = { if (enabled) onTarget(ServoTarget(wrist.roundToInt(), wrist = true)) })
    Row(Modifier.fillMaxWidth()) {
        Text("−90° antihorario", Modifier.weight(1f), style = MaterialTheme.typography.labelSmall)
        Text("0°", Modifier.weight(1f), textAlign = TextAlign.Center, style = MaterialTheme.typography.labelSmall)
        Text("+90° horario", Modifier.weight(1f), textAlign = TextAlign.End, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun HomeButton(running: Boolean, enabled: Boolean, onStart: () -> Unit, onCancel: () -> Unit) {
    if (running) Button(onClick = onCancel, colors = ButtonDefaults.buttonColors(
        containerColor = MaterialTheme.colorScheme.error, contentColor = MaterialTheme.colorScheme.onError)) {
        Text("Cancelar homing")
    } else Button(onClick = onStart, enabled = enabled) { Text("Hacer homing") }
}

@Composable
private fun HeldControl(label: String, enabled: Boolean, change: (Boolean) -> Unit) {
    val interactions = remember { MutableInteractionSource() }
    val pressed by interactions.collectIsPressedAsState()
    val dispatch by rememberUpdatedState(change)
    LaunchedEffect(pressed, enabled) { dispatch(pressed && enabled) }
    DisposableEffect(Unit) { onDispose { dispatch(false) } }
    FilledTonalButton({}, enabled = enabled, interactionSource = interactions) { Text(label) }
}
