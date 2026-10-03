#pragma once

#include "ControlArticulacion.h"

// Parámetros de las tres articulaciones. Los modelos y ganancias vienen de la Entrega 5 (lazo abierto).
// Lo marcado MEDIR es una estimación que hay que reemplazar con el brazo armado.

constexpr int N_ART = 3;
constexpr float TS = 0.01f;  // periodo del control: 10 ms (100 Hz)

// Límites articulares de la Entrega 4 (q1: base, q2: hombro, q3: balancín de entrada del cuatro barras).
constexpr ConfigArticulacion CFG_ART[N_ART] = {
    {
        // J1 medido en pruebas-esp32/10-control-lazo-cerrado (2026-10-02), montado en el brazo. Ese firmware
        // controla en °/s de la base; acá el lazo de velocidad va en rpm de la salida de la reductora:
        // 1 rpm = 6 °/s de la salida = 6/5 = 1,2 °/s de la base, así que kpVel y kiVel van x1,2.
        "J1",
        3200.0f,  // 16 PPR x4 x reductora 50:1 (medido en pruebas-esp32/06)
        5.0f,     // correa GT2, polea de 18 dientes en el motor y 90 en la base (verificado: 44,44 cuentas/°)
        160.0f,
        -75.0f, 75.0f,   // E4, marco de la cinemática (q1 = 0 en +X del brazo). PENDIENTE: en el banco de pruebas
                         // el cero quedó con el brazo al costado y el rango -45/+135 desde ahí; falta decidir cómo
                         // se traduce al marco de brazo_ik (POSE_CERO de J1 y Q1_LIM de cinematica.py)
        1.58f, 0.065f, 17.0f,  // E5: K rpm/%, tau s; zona muerta girando 17 % (medida con el brazo)
        0.659f, 4.8f,          // PI: 0,549 %/(°/s) y 4 %/° de las pruebas (Ki de diseño 8,44 daba 18 % de
                               // sobrepico por el juego de la correa)
        2.0f, 30.0f, 60.0f,    // kpPos 1/s (sin sobrepico con <= 2,78), velMax °/s, accMax °/s²
        0.3f,                  // tolerancia de llegada ° (se despierta al doble: 0,6°)
        40.0f,                 // duty máx %: el de las pruebas (30 °/s piden ~33 %)
        35.0f, 1.7f, 0.3f,     // atasco: 35 %, menos de 1,7 rpm (2 °/s de la base) durante 0,3 s
        5.0f,                  // margen fuera de límites °
        3.0f,                  // velMin °/s: sin esto se trababa a 0,8° del objetivo
        true,                  // feedforward solo con la zona muerta, como en las pruebas
    },
    {
        "J2",
        4000.0f,  // encoder externo 1000 PPR x4 en la salida del motor
        1.0f,     // MEDIR: transmisión motor -> hombro
        160.0f,
        -25.0f, 135.0f,
        1.33f, 0.059f, 30.0f,  // E5: K, tau; zona muerta: MEDIR (arranca entre 20 y 40 %)
        0.44f, 7.5f,
        2.0f, 20.0f, 40.0f,
        0.5f,
        100.0f,  // el L298N ya pierde ~2,4 V: a 100 % el motor recibe ~9,6 V
        60.0f, 3.0f, 1.0f,  // el sin fin tiene mucha fricción: umbral de atasco por encima de la zona muerta
        5.0f,
    },
    {
        "J3",
        4000.0f,
        1.0f,  // MEDIR
        160.0f,
        -50.0f, 50.0f,
        1.33f, 0.059f, 30.0f,  // mismo motor que J2 (sin caracterizar por separado)
        0.44f, 7.5f,
        2.0f, 20.0f, 40.0f,
        0.5f,
        100.0f,
        60.0f, 3.0f, 1.0f,
        5.0f,
    },
};

// Signos. ENC_INVERTIDO: si con duty positivo la velocidad sale negativa. MOTOR_INVERTIDO: si con duty positivo la
// articulación gira al revés de su sentido positivo (q1 positivo = antihorario visto desde arriba); invierte el
// duty, así que el encoder también hay que invertirlo para que sigan de acuerdo.
// J1 (pruebas-esp32/10): el encoder sube con duty + (normal), pero la base giraba horario -> motor invertido y,
// con él, el encoder. J2 medido en pruebas-esp32/08 (sin verificar el sentido de q2). J3: MEDIR.
constexpr bool ENC_INVERTIDO[N_ART] = {true, true, false};
constexpr bool MOTOR_INVERTIDO[N_ART] = {true, false, false};

// Pose de referencia para el cero manual (comando z) [°]. MEDIR/definir con la mecánica:
// una pose fácil de reproducir a ojo o con una plantilla (por ejemplo, base al frente y brazo vertical).
constexpr float POSE_CERO[N_ART] = {0.0f, 90.0f, 0.0f};

// Homing con final de carrera: velocidad (rpm del motor, con signo hacia el final de carrera),
// ángulo que vale la articulación al tocarlo y tiempo máximo.
constexpr float HOME_RPM[N_ART] = {-10.0f, -10.0f, -10.0f};
constexpr float HOME_Q[N_ART] = {-75.0f, -25.0f, -50.0f};  // MEDIR con la mecánica
// J1 con la correa 5:1: -10 rpm = 12 °/s de la base, 180° de recorrido son 15 s (más arranque y confirmación)
constexpr float HOME_TIMEOUT_S = 25.0f;
// Recorrido máximo del homing: el rango de la articulación más este margen [°]. Corta aunque no venza el tiempo.
constexpr float HOME_MARGEN_DEG = 10.0f;
// El final de carrera cuenta como tocado recién con esta cantidad de lecturas seguidas en bajo (10 ms c/u)
constexpr int HOME_FC_LECTURAS = 3;

// PWM
constexpr uint32_t PWM_BTS_HZ = 20000;  // IBT-2 (como en pruebas-esp32/06)
constexpr uint32_t PWM_L298_HZ = 1000;  // L298N en modo Freno (como en pruebas-esp32/08)
constexpr uint8_t PWM_BITS = 10;

// Servos DSSERVO RDS3218 (20 kg·cm, 4,8-6,8 V), 50 Hz. Pulsos en µs: MEDIR con cada servo para no forzar la pinza
// contra el tope. El RDS3218 viene en versión de 180° y de 270°: con la de 270°, GIRO_US_POR_GRADO = 2000/270.
constexpr uint32_t SERVO_HZ = 50;
constexpr uint8_t SERVO_BITS = 16;
constexpr float PINZA_US_ABIERTA = 1000.0f;
constexpr float PINZA_US_CERRADA = 2000.0f;
constexpr float GIRO_US_CENTRO = 1500.0f;
constexpr float GIRO_US_POR_GRADO = 1000.0f / 90.0f;  // servo típico de 180°: 500-2500 µs
constexpr float GIRO_MAX_DEG = 90.0f;

// Seguridad. Valores de PUESTA EN MARCHA: subirlos recién con la relación de transmisión medida.
constexpr uint32_t JOG_MS = 300;  // el comando d (lazo abierto) se corta solo si no se repite
// % máximo en lazo abierto manual. J1: ~25 rpm del motor; J2/J3: apenas por encima de la zona muerta del sin fin
// (J1 arranca desde quieta con ~25-30 % por la fricción: medido en pruebas-esp32/10)
constexpr float JOG_DUTY_MAX[N_ART] = {30.0f, 45.0f, 45.0f};
constexpr float VEL_CMD_MAX_RPM = 30.0f;  // |rpm| máximo del comando v (el control admite hasta rpmMax)
constexpr float VEL_CMD_S_DEF = 2.0f;     // duración por defecto del comando v
constexpr float VEL_CMD_S_MAX = 5.0f;
// Si la tarea de control deja de correr este tiempo, el watchdog de tareas del ESP32 reinicia la placa
// (al reiniciar, los EN quedan en bajo por los pull-down: puentes deshabilitados)
constexpr uint32_t TWDT_S = 1;
