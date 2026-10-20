#pragma once

#include <math.h>

#include "ControlArticulacion.h"
#include "Diferencial.h"
#include "SeguridadBase.h"

// Parámetros de la base. Lo marcado MEDIR es una estimación que hay que reemplazar con el robot armado.

constexpr float TS = 0.01f;  // periodo del control: 10 ms (100 Hz)

// Control de velocidad de cada rueda (ControlArticulacion en modo velocidad; el modo posición no se usa).
// Motor de tracción: 42GM-895H planetario, 12 V, 53 rpm, reductora 189:1, encoder Hall de 11 PPR en el eje del
// motor (hoja del vendedor en docs/fotos/motor_traccion/; 12 V: 2,6 A en vacío, 5,5 A nominal, 10 A bloqueado).
// Modelo provisorio escalado del 36GP-555 de 160 rpm de la E5 (K = 1,58 rpm/%, τ = 65 ms) a 53 rpm -> K ≈ 0,52
// rpm/%; hay que identificarlo de nuevo. PI con Ti = τ y lazo cerrado de 0,15 s: Kp = τ/(K·0,15).
constexpr ConfigArticulacion CFG_RUEDA = {
    "rueda",
    8316.0f,  // 11 PPR x4 x 189 (hoja); verificar girando la rueda a mano, ver README
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

// Geometría y límites de movimiento. Ruedas inflables de 150 mm (docs/fotos/rueda); la trocha es estimada (R2 E3:
// ruedas en los rebajes de 3 cm de la parte angosta de 34 cm): MEDIR las dos con cinta
constexpr ConfigDiferencial CFG_DIF = {
    0.075f,  // radio de rueda [m] (150 mm de diámetro, inflable: MEDIR con el inflado real)
    0.40f,   // trocha: distancia entre centros de rueda [m] (MEDIR)
    50.0f,   // rpm máximas de rueda pedidas al control (el motor da ~53 en vacío)
    0.25f,   // v máx [m/s] (50 rpm con r = 7,5 cm darían 0,39 m/s: se limita para las pruebas)
    1.0f,   // w máx [rad/s]
    0.3f,   // aceleración lineal [m/s²]
    1.5f,   // aceleración angular [rad/s²]
};

// Seguridad (H5, H8, H9, N3)
constexpr ConfigSeguridad CFG_SEG = {
    0.20f,  // distancia de parada al frente [m]
    0.50f,  // desde acá el avance tiene un tope que baja linealmente hasta 0 [m]
    25.0f,  // roll o pitch de vuelco [°]
    0,      // watchdog de comandos [ms]: 0 al arrancar (comandos a mano); con la Pi, wd 300
    10.5f,  // batería baja [V]: LiPo 3S (Zeee 8000 mAh) a 3,5 V por celda; SIN BMS: no bajar de acá
    0.25f,  // tope de avance lejos de obstáculos [m/s] (= vMax de CFG_DIF)
};

// Periodos (en pasos de 10 ms)
constexpr int IMU_CADA = 2;  // 50 Hz
constexpr int US_CADA = 4;   // 40 ms entre disparos, de a un HC-SR04: cada uno mide cada 120 ms (~8 Hz)
constexpr float IMU_FILTRO = 0.1f;  // pasa bajos de roll y pitch (a 50 Hz: ~0,2 s)
constexpr uint32_t IMU_VALIDA_MS = 200;  // sin muestras de la IMU por más de esto, la base no se mueve

// Batería LiPo 3S (9,9-12,6 V, desde el 08/10; antes la 10S): divisor 100 k / 30 k -> 12,6 V da 2,91 V en el ADC
// (con 11 dB mide hasta ~3,1 V: ~13,4 V). Si vuelve la 10S (42 V), volver a 120 k / 8,2 k: este divisor la quemaría
constexpr float BATERIA_DIVISOR = (100.0f + 30.0f) / 30.0f;
constexpr uint32_t BATERIA_CADA_MS = 200;

// PWM de los IBT-2 (como en pruebas-esp32/06)
constexpr uint32_t PWM_HZ = 20000;
constexpr uint8_t PWM_BITS = 10;

// Comandos manuales. Valores de PUESTA EN MARCHA.
constexpr float CMD_S_DEF = 1.0f;     // duración por defecto de v y w [s]
constexpr float CMD_S_MAX = 3.0f;  // también acota cuánto sigue andando si se corta el USB sin watchdog
constexpr uint32_t JOG_MS = 300;      // d se corta solo si no se repite
constexpr float JOG_DUTY_MAX = 25.0f;  // primera prueba de tracción (20/10); antes 40

// Si la tarea de control deja de correr este tiempo, el watchdog de tareas reinicia la placa
constexpr uint32_t TWDT_S = 1;
