#pragma once

// Placa: ESP32-WROOM-32D en una HW-394 de 30 pines (USB-C, CH340 -> /dev/ttyUSB0). Controla el brazo completo.
// Pines del conexionado v0.5 (docs/CONEXIONES.md, docs/html/placa_wroom.html). Montada en un shield de borneras de 30 pines.
// v0.5 (12/10): encoder de J2 a 36/39 y finales de carrera de J1/J2 a 32/33, para que ninguno necesite pull-up externo.
// Evitar: GPIO6-11 (flash), 0/2/5/12/15 (strapping), 1/3 (UART0 = USB).
// 34-39: solo entrada y SIN pull-up interno: ahí van solo los encoders, que traen pull-up en su placa.
// Queda libre el GPIO 13 (reserva).

// Los tres IBT-2 (BTS7960) comparten el EN: R_EN y L_EN de los tres al GPIO 23 (+ pull-down 10 kΩ a GND).
// Con un solo EN no se puede dejar una articulación en rueda libre mientras otra se mueve: la que no se mueve
// queda frenada (duty 0 con el puente habilitado). Rueda libre solo cuando las tres están libres.
constexpr int PIN_BRAZO_EN = 23;

// J1 (base giratoria): motor 36GP-555 160 rpm (50:1) + IBT-2
constexpr int PIN_J1_RPWM = 21;
constexpr int PIN_J1_LPWM = 22;
// Encoder SCX-555 (16 PPR, colector abierto con pull-up de 5,1 kΩ en su placa): alimentar a 3V3, NO a 5 V.
// 34/35 no tienen pull-up interno: alcanza el de la placa del encoder
constexpr int PIN_J1_ENC_A = 34;  // negro = Signal A
constexpr int PIN_J1_ENC_B = 35;  // rojo = Signal B

// J2 (hombro): motor 36-555 58 rpm (139:1) + IBT-2 + engranajes helicoidales 15 -> 75
constexpr int PIN_J2_RPWM = 25;
constexpr int PIN_J2_LPWM = 26;
constexpr int PIN_J2_ENC_A = 36;  // VP · negro (SCX-555 a 3V3, como J1; pull-up de su placa)
constexpr int PIN_J2_ENC_B = 39;  // VN · rojo

// J3 (codo, balancín del cuatro barras): motor 36-555 58 rpm (139:1) + IBT-2 + engranajes helicoidales 15 -> 75
constexpr int PIN_J3_RPWM = 16;
constexpr int PIN_J3_LPWM = 17;
constexpr int PIN_J3_ENC_A = 18;  // negro
constexpr int PIN_J3_ENC_B = 19;  // rojo

// Pinza: servo de apertura y servo de giro (J4). Señal a 3,3 V; alimentación de 6 V APARTE (buck 3, no del ESP32).
constexpr int PIN_SERVO_PINZA = 4;
constexpr int PIN_SERVO_GIRO = 14;  // GPIO14 saca pulsos durante el arranque: el servo puede moverse un instante

// Finales de carrera para el homing (normalmente abiertos a GND, pull-up interno; sin 100 nF: el homing pide
// HOME_FC_LECTURAS lecturas seguidas). -1 = no hay.
// Sin final de carrera, el cero se fija a mano en la pose de referencia (comando z).
constexpr int PIN_FC_J1 = 32;
constexpr int PIN_FC_J2 = 33;
constexpr int PIN_FC_J3 = 27;
