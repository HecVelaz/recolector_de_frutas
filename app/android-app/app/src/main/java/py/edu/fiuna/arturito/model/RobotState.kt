package py.edu.fiuna.arturito.model

enum class RobotState(val label: String) {
    INACTIVO("Inactivo"), TELEOP("Teleoperación"), NAVEGANDO("Navegando"),
    BUSCANDO("Buscando"), INTERVINIENDO("Interviniendo"), RECUPERACION("Recuperación"),
    FINALIZADO("Finalizado"), EMERGENCIA("Emergencia")
}

enum class ManualDirection(val label: String, val symbol: String) {
    FORWARD("Avanzando", "↑"), BACKWARD("Retrocediendo", "↓"),
    LEFT("Girando a la izquierda", "↶"), RIGHT("Girando a la derecha", "↷")
}

val demoMissions = listOf("Recolectar en un árbol", "Inspeccionar el área")

fun missionState(progress: Float): RobotState = when {
    progress >= 1f -> RobotState.FINALIZADO
    progress < 0.3f -> RobotState.NAVEGANDO
    progress < 0.55f -> RobotState.BUSCANDO
    progress < 0.85f -> RobotState.INTERVINIENDO
    else -> RobotState.RECUPERACION
}
