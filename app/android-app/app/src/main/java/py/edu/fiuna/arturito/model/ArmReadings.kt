package py.edu.fiuna.arturito.model

enum class ArmJointState(val label: String) {
    FREE("Suelta"), POSITIONING("Yendo al destino"), ARRIVED("Llegó"),
    HOLDING("Sosteniendo"), BRAKED("Frenada"), MOVING("En movimiento"), HOMING("Buscando cero")
}

data class ArmJointReading(val angleDegrees: Double, val state: ArmJointState,
    val zeroKnown: Boolean, val limitActive: Boolean)

data class ArmReadings(val joints: List<ArmJointReading>, val gripperPulseUs: Int?, val wristPulseUs: Int?) {
    companion object {
        fun decode(message: String?): ArmReadings? {
            val fields = message?.split(';')?.mapNotNull { part ->
                val pair = part.split('=', limit = 2)
                if (pair.size == 2) pair[0] to pair[1] else null
            }?.toMap() ?: return null
            val angles = fields["q"]?.split(',') ?: return null
            val states = fields["e"]?.split(',') ?: return null
            val zero = fields["c"] ?: return null
            val limits = fields["fc"] ?: return null
            if (angles.size != 3 || states.size != 3 || !zero.matches(Regex("[01]{3}")) ||
                !limits.matches(Regex("[01]{3}"))) return null
            val joints = angles.mapIndexed { i, raw ->
                val angle = raw.toDoubleOrNull()?.takeIf { it.isFinite() } ?: return null
                val state = states[i].toIntOrNull()?.let { ArmJointState.entries.getOrNull(it) } ?: return null
                ArmJointReading(angle, state, zero[i] == '1', limits[i] == '1')
            }
            return ArmReadings(joints, fields["pz"]?.toIntOrNull()?.takeIf { it > 0 },
                fields["mn"]?.toIntOrNull()?.takeIf { it > 0 })
        }
    }
}
