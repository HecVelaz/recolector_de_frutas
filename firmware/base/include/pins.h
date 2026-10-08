#pragma once

// Placa: Freenove ESP32-S3-WROOM N16R8 (USB nativo /dev/ttyACM0). Controla la base, sus sensores y la seta.
// Pines según docs/CONEXIONES.md. Solo queda libre el GPIO 40 (reservado para un 4.º bumper). El GPS va en la Pi.
// Prohibidos: 19/20 (USB), 26-37 (flash y PSRAM octal). Evitar: 0/3/45/46 (strapping), 43/44 (UART0), 2/48 (LED).
// Los GPIO son de 3,3 V: el ECHO de los HC-SR04 (5 V) va con divisor.

// Tracción: dos IBT-2 (BTS7960) con R_EN + L_EN de los dos puentes unidos a un solo GPIO (+ pull-down 10 kΩ)
constexpr int PIN_IZQ_RPWM = 4;
constexpr int PIN_IZQ_LPWM = 5;
constexpr int PIN_DER_RPWM = 6;
constexpr int PIN_DER_LPWM = 7;
constexpr int PIN_TRACCION_EN = 38;

// Encoders Hall de los motores de tracción (pull-up interno)
constexpr int PIN_IZQ_ENC_A = 15;  // como en la prueba 06
constexpr int PIN_IZQ_ENC_B = 16;
constexpr int PIN_DER_ENC_A = 17;
constexpr int PIN_DER_ENC_B = 18;

// IMU MPU-6500 por I2C (0x68, AD0 a GND)
constexpr int PIN_I2C_SDA = 8;
constexpr int PIN_I2C_SCL = 9;

// HC-SR04: un TRIG y un ECHO por sensor (divisor 1 kΩ / 2 kΩ en cada ECHO). Los 3 miran al frente: se disparan
// de a uno para que no se pisen los ecos. 41/42 eran del GPS, que pasó a la Pi (UART del header).
constexpr int PIN_US_TRIG_FRENTE = 10;
constexpr int PIN_US_TRIG_IZQ = 41;
constexpr int PIN_US_TRIG_DER = 42;
constexpr int PIN_US_ECHO_FRENTE = 11;
constexpr int PIN_US_ECHO_IZQ = 12;
constexpr int PIN_US_ECHO_DER = 13;

// Bumpers: normalmente abiertos a GND, pull-up interno (apretado = LOW)
// 3 bumpers (R2 E3): frente y los dos laterales. GPIO 40 quedó libre (era el 4.º bumper, atrás)
constexpr int PIN_BUMPER_FRENTE = 14;
constexpr int PIN_BUMPER_IZQ = 21;
constexpr int PIN_BUMPER_DER = 39;

// Seta: contacto auxiliar NORMALMENTE CERRADO a GND, pull-up interno. Seta suelta = LOW; apretada o cable
// cortado = HIGH (falla segura).
constexpr int PIN_SETA = 47;

// Tensión de batería LiPo 3S: divisor 100 kΩ (arriba) / 27 kΩ (abajo), ADC1 canal 0 (con la 10S era 120 k / 8,2 k)
constexpr int PIN_BATERIA = 1;
