#pragma once

#include <stdint.h>

#include "driver/pcnt.h"
#include "freertos/FreeRTOS.h"

// Encoder en cuadratura leído por hardware con el PCNT del ESP32 (x4: flancos de A y de B).
// No usa interrupciones, así que no carga la CPU aunque el motor gire rápido.
// El contador de hardware (16 bits) nunca se borra durante la marcha: al llegar a ±32000 vuelve a 0, y cada
// count() suma al acumulador de 64 bits lo que avanzó desde la lectura anterior (desenvolverPcnt).
// Condición: leer antes de que el eje avance 16000 cuentas (el control lee cada 10 ms: 160 rpm con 1000 PPR x4
// son ~110 cuentas). Antes se usaba la interrupción de límite, y leer entre la vuelta a 0 del contador y la
// interrupción daba un salto falso de 32000 cuentas. Sin Serial ni pines fijos.
class EncoderPCNT {
 public:
  // filterNs: descarta pulsos más cortos (ruido del PWM). Máximo ~12700 ns.
  bool begin(int pinA, int pinB, pcnt_unit_t unit = PCNT_UNIT_0, uint32_t filterNs = 10000);

  // Cuentas acumuladas desde begin() (o desde reset()). Se puede llamar desde varias tareas.
  int64_t count();
  // Cuentas desde la llamada anterior a delta().
  int32_t delta();
  void reset();

  bool ready() const { return ready_; }

  // Niveles actuales de A y B (para verificar el cableado con el motor girado a mano).
  int levelA() const;
  int levelB() const;

 private:
  pcnt_unit_t unit_ = PCNT_UNIT_0;
  int pinA_ = -1, pinB_ = -1;
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
  int16_t lastHw_ = 0;  // última lectura del contador de hardware
  int64_t acc_ = 0;     // cuentas acumuladas
  int64_t lastDelta_ = 0;
  bool ready_ = false;
};
