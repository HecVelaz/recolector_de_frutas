package py.edu.fiuna.arturito.ui

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.SoundPool
import py.edu.fiuna.arturito.R
import py.edu.fiuna.arturito.model.SensorAlert

/** Los 8 pitidos de alerta. Volumen: las teclas de la tablet (multimedia). En silencio o vibración no suena. */
class AlertSounds(context: Context) {
    private val audio = context.getSystemService(AudioManager::class.java)
    private val pool = SoundPool.Builder().setMaxStreams(1).setAudioAttributes(AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()).build()
    private val ids = SensorAlert.entries.associateWith { pool.load(context, raw(it), 1) }

    fun play(alert: SensorAlert) {
        if (audio?.ringerMode != AudioManager.RINGER_MODE_NORMAL) return
        // Prioridad de SoundPool: con una sola voz, el de mayor prioridad corta al otro.
        pool.play(ids.getValue(alert), 1f, 1f, 10 - alert.group, 0, 1f)
    }

    fun release() = pool.release()

    private fun raw(alert: SensorAlert) = when (alert) {
        SensorAlert.SETA -> R.raw.seta_emergencia
        SensorAlert.IMU -> R.raw.imu_inclinacion
        SensorAlert.BUMPER_IZQ -> R.raw.bumper_izquierdo
        SensorAlert.BUMPER_FRENTE -> R.raw.bumper_frontal
        SensorAlert.BUMPER_DER -> R.raw.bumper_derecho
        SensorAlert.US_IZQ -> R.raw.ultrasonico_izquierdo
        SensorAlert.US_CENTRAL -> R.raw.ultrasonico_central
        SensorAlert.US_DER -> R.raw.ultrasonico_derecho
    }
}
