#include "SeguridadBase.h"

#include <math.h>

const char *SeguridadBase::texto(Estado e) {
  switch (e) {
    case Estado::Emergencia: return "EMERGENCIA (seta)";
    case Estado::Vuelco: return "VUELCO";
    case Estado::SinComandos: return "sin comandos";
    default: return "ok";
  }
}

static bool nivelada(const EntradasSeguridad &in, float inclMax) {
  return fabsf(in.roll) < inclMax && fabsf(in.pitch) < inclMax;
}

bool SeguridadBase::filtrar(const EntradasSeguridad &in, float &v, float &w) {
  bateriaBaja_ = isfinite(in.bateria) && in.bateria < cfg_.bateriaMin;

  // Enclavados: primero la seta, después el vuelco
  if (in.seta) estado_ = Estado::Emergencia;
  else if (estado_ != Estado::Emergencia && !nivelada(in, cfg_.inclMax)) estado_ = Estado::Vuelco;

  bloqAdelante_ = bloqAtras_ = false;
  if (estado_ == Estado::Emergencia || estado_ == Estado::Vuelco) {
    v = w = 0.0f;
    return false;
  }

  // Watchdog de comandos: no enclavado, vuelve a Ok con el próximo comando
  if (cfg_.sinCmdMs > 0 && in.msSinCmd > cfg_.sinCmdMs) {
    estado_ = Estado::SinComandos;
    v = w = 0.0f;
    return false;
  }
  estado_ = Estado::Ok;

  // Contacto: un bumper delantero impide avanzar; uno trasero, retroceder. El giro en el lugar se permite
  // para poder salir del contacto.
  bloqAdelante_ = in.bumper[0] || in.bumper[1];
  bloqAtras_ = in.bumper[2] || in.bumper[3];

  // Distancia al frente: parada o avance escalado
  if (isfinite(in.distFrente) && v > 0.0f) {
    if (in.distFrente <= cfg_.distParada) {
      bloqAdelante_ = true;
    } else if (in.distFrente < cfg_.distLenta) {
      v *= (in.distFrente - cfg_.distParada) / (cfg_.distLenta - cfg_.distParada);
    }
  }
  if (bloqAdelante_ && v > 0.0f) v = 0.0f;
  if (bloqAtras_ && v < 0.0f) v = 0.0f;
  return true;
}

bool SeguridadBase::rearmar(const EntradasSeguridad &in) {
  if (in.seta || !nivelada(in, cfg_.inclMax)) return false;
  estado_ = Estado::Ok;
  return true;
}
