#pragma once

#include <stdint.h>

// Límites del contador de hardware del PCNT: al llegar a uno vuelve a 0, así que sus lecturas valen módulo 32000.
constexpr int32_t PCNT_LIMITE = 32000;

// Diferencia entre dos lecturas del contador (cada una en -32000..32000, así que la diferencia puede pasar de ±32000)
// -> cuentas reales entre ellas, en [-16000, 16000).
// Exacta si entre las dos lecturas el eje se movió menos de 16000 cuentas. Sin Arduino: se prueba en native.
inline int32_t desenvolverPcnt(int32_t d) {
  d %= PCNT_LIMITE;  // (-32000, 32000)
  if (d >= PCNT_LIMITE / 2) d -= PCNT_LIMITE;
  if (d < -PCNT_LIMITE / 2) d += PCNT_LIMITE;
  return d;
}
