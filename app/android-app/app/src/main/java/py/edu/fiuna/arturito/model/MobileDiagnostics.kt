package py.edu.fiuna.arturito.model

private val mobileField = Regex("""(?:^|\s)([a-z_]+)=""")
private val mobileWarning = Regex("""\s+(?=(?:SETA|BATERIA_BAJA|no_avanza|no_retrocede)(?:\W|$))""")

fun mobileDiagnosticRows(report: String?): List<Pair<String, String>> {
    if (report.isNullOrBlank()) return emptyList()
    val matches = mobileField.findAll(report).toList()
    val fields = matches.mapIndexed { index, item ->
        val end = matches.getOrNull(index + 1)?.range?.first ?: report.length
        item.groupValues[1] to report.substring(item.range.last + 1, end).removeSuffix(" enlace:").trim()
    }.toMap()
    fun wheel(key: String) = when (fields[key]) {
        "ninguna" -> "Sin fallas"
        "atasco" -> "Atasco"
        "fuera de limites" -> "Fuera de límites"
        "encoder (saltos)" -> "Lectura irregular del encoder"
        else -> fields[key]?.let(::friendlyMobileValue)
    }
    return buildList {
        fun row(label: String, value: String?) {
            if (!value.isNullOrBlank()) add(label to value)
        }
        val mode = fields["modo"]
        row("Modo de tracción", when (mode) {
            "parado" -> "Detenido"
            "libre" -> "Ruedas libres"
            "v/w" -> "Avance y giro"
            "ruedas" -> "Control por rueda"
            "duty" -> "Potencia directa"
            else -> mode?.let(::friendlyMobileValue)
        })
        val safety = fields["seguridad"]
        val safetyState = safety?.split(mobileWarning, limit = 2)?.first()
        row("Seguridad", when (safetyState) {
            "ok" -> "Sin bloqueos reportados"
            "sin comandos" -> "A la espera de una orden"
            "EMERGENCIA (seta)" -> "Parada de emergencia"
            "IMU sin datos" -> "IMU sin lectura"
            else -> safetyState?.let(::friendlyMobileValue)
        })
        val warnings = listOf(
            "SETA" to "Seta de emergencia activa",
            "no_avanza" to "Avance bloqueado",
            "no_retrocede" to "Retroceso bloqueado",
            "frente_sin_eco" to "Sensor frontal sin eco",
            "BATERIA_BAJA" to "Tensión baja",
        ).filter { safety?.contains(it.first) == true }.joinToString(" · ") { it.second }
        row("Avisos de tracción", warnings)
        row("IMU", when (fields["imu"]) {
            "ok" -> "Lectura válida"
            "SIN_DATOS" -> "Sin lectura"
            else -> fields["imu"]?.let(::friendlyMobileValue)
        })
        row("Rueda izquierda", wheel("rueda_izq"))
        row("Rueda derecha", wheel("rueda_der"))
        row("Recuperaciones de IMU", fields["imu_rec"]?.toLongOrNull()?.toString())
        row("Comprobaciones de enlace fallidas", fields["pings_fallidos"]?.toLongOrNull()?.toString())
        row("Cortes de comunicación", fields["cortes"]?.toLongOrNull()?.toString())
    }
}

private fun friendlyMobileValue(text: String) =
    text.replace('_', ' ').lowercase().replaceFirstChar { it.uppercase() }
