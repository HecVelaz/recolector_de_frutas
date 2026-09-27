#pragma once

#include <math.h>

#include "ControlArticulacion.h"
#include "Diferencial.h"
#include "SeguridadBase.h"

// Parámetros de la base. Lo marcado MEDIR es una estimación que hay que reemplazar con el robot armado.

constexpr float TS = 0.01f;  // periodo del control: 10 ms (100 Hz)

// Control de velocidad de cada rueda (ControlArticulacion en modo velocidad; el modo posición no se usa).
// Motor de tracción 36GP-555 de 53 rpm (MEDIR: el inventario dice DC 895 planetario de 53 rpm; confirmar cuál es).
// Modelo escalado del 36GP-555 de 160 rpm caracterizado en la E5 (K = 1,58 rpm/%, τ = 65 ms): mismo motor con
// una reducción 3 veces mayor -> K ≈ 0,52 rpm/%. PI con Ti = τ y lazo cerrado de 0,15 s: Kp = τ/(K·0,15).
constexpr ConfigArticulacion CFG_RUEDA = {
    "rueda",
    9600.0f,  // MEDIR: 16 PPR x4 x reductora (150:1 para 53 rpm)
    1.0f,     // la rueda va directo al eje del motor
    60.0f,    // rpm máximas (para descartar saltos del encoder)
    -1e9f, 1e9f,          // sin límites de posición (una rueda gira sin fin)
    0.52f, 0.065f, 8.0f,  // MEDIR: K rpm/%, tau s, zona muerta girando %
    0.83f, 12.8f,         // PI de velocidad
    1.0f, 1.0f, 1.0f,     // lazo de posición: no se usa
    1.0f,
    85.0f,              // duty máx % (arriba de ~85 % el IBT-2 deja de ser lineal)
    50.0f, 2.0f, 1.0f,  // atasco: duty %, rpm, s
    0.0f,
};

// Sentido de cada lado. Los motores van espejados: para avanzar, el derecho gira al revés. MEDIR con `d`.
constexpr bool MOTOR_INVERTIDO[2] = {false, true};  // {izquierdo, derecho}
constexpr bool ENC_INVERTIDO[2] = {false, true};

// Geometría y límites de movimiento (MEDIR radio y trocha)
constexpr ConfigDiferencial CFG_DIF = {
    0.05f,  // radio de rueda [m]
    0.30f,  // trocha: distancia entre ruedas [m]
    50.0f,  // rpm máximas de rueda pedidas al control (el motor da ~53 en vacío)
    0.25f,  // v máx [m/s]  (50 rpm con r = 5 cm: 0,26 m/s)
    1.0f,   // w máx [rad/s]
    0.3f,   // aceleración lineal [m/s²]
    1.5f,   // aceleración angular [rad/s²]
};

// Seguridad (H5, H8, H9, N3)
constexpr ConfigSeguridad CFG_SEG = {
    0.20f,  // distancia de parada al frente [m]
    0.50f,  // desde acá se reduce la velocidad [m]
    25.0f,  // roll o pitch de vuelco [°]
    0,      // watchdog de comandos [ms]: 0 al arrancar (comandos a mano); con la Pi, wd 300
    11.0f,  // batería baja [V] (MEDIR según la química de la batería)
};

// Periodos (en pasos de 10 ms)
constexpr int IMU_CADA = 2;  // 50 Hz
constexpr int US_CADA = 7;   // 70 ms entre disparos de los HC-SR04
constexpr float IMU_FILTRO = 0.1f;  // pasa bajos de roll y pitch (a 50 Hz: ~0,2 s)

// Batería: divisor 100 k / 27 k
constexpr float BATERIA_DIVISOR = (100.0f + 27.0f) / 27.0f;
constexpr uint32_t BATERIA_CADA_MS = 200;

// PWM de los IBT-2 (como en pruebas-esp32/06)
constexpr uint32_t PWM_HZ = 20000;
constexpr uint8_t PWM_BITS = 10;

// Comandos manuales. Valores de PUESTA EN MARCHA.
constexpr float CMD_S_DEF = 1.0f;     // duración por defecto de v y w [s]
constexpr float CMD_S_MAX = 5.0f;
constexpr uint32_t JOG_MS = 300;      // d se corta solo si no se repite
constexpr float JOG_DUTY_MAX = 40.0f;

// Si la tarea de control deja de correr este tiempo, el watchdog de tareas reinicia la placa
constexpr uint32_t TWDT_S = 1;
