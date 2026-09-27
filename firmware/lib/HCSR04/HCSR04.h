#pragma once

#include <Arduino.h>

// Varios HC-SR04 con el TRIG en común y cada ECHO medido por interrupción: no bloquea (sin pulseIn).
// Sin Serial ni pines fijos. El ECHO sale a 5 V: cada pin necesita un divisor (1 kΩ arriba, 2 kΩ abajo).
//
// Uso: disparar() cada >= 60 ms (lo que tarda el eco más largo); distancia(i) devuelve la medición del
// disparo anterior. Todos los sensores se disparan juntos: conviene que apunten a lados distintos.
class HCSR04 {
 public:
  static constexpr int MAX_SENSORES = 4;
  static constexpr uint32_t ECO_MAX_US = 25000;  // ~4,3 m; más largo = nada al alcance (algunos dan 38 ms)

  bool begin(int pinTrig, const int *pinesEcho, int n);
  // Pulso de 10 µs en TRIG. Cierra el ciclo anterior: lo que no respondió queda sin medición (NAN).
  void disparar();
  // Metros del último ciclo completo. INFINITY = eco largo (nada al alcance);
  // NAN = no hubo ningún pulso de eco (sensor desconectado, sin alimentación o todavía sin medir).
  float distancia(int i) const;

 private:
  static void IRAM_ATTR alCambiar(void *arg);

  struct Canal {
    HCSR04 *padre;
    int pin;
    volatile uint32_t subidaUs;
    volatile uint32_t anchoUs;  // 0 = sin eco en este ciclo
    float metros;
  };

  // La interrupción puede correr en otro núcleo que disparar(): noInterrupts() no alcanza
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
  int pinTrig_ = -1;
  int n_ = 0;
  Canal canal_[MAX_SENSORES] = {};
};
