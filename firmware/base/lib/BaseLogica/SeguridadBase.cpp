#include "SeguridadBase.h"

#include <math.h>

const char *SeguridadBase::texto(Estado e) {
  switch (e) {
    case Estado::Emergencia: return "EMERGENCIA (seta)";
    case Estado::Vuelco: return "VUELCO";
    case Estado::SinComandos: return "sin comandos";
    case Estado::SinImu: return "IMU sin datos";
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
  else if (estado_ != Estado::Emergencia && in.imuValida && !nivelada(in, cfg_.inclMax)) estado_ = Estado::Vuelco;

  bloqAdelante_ = bloqAtras_ = frenteSinDato_ = false;
  if (estado_ == Estado::Emergencia || estado_ == Estado::Vuelco) {
    v = w = 0.0f;
    return false;
  }

  // Sin IMU no se puede vigilar el vuelco: no se mueve (no enclavado, sigue sola cuando vuelven los datos)
  if (!in.imuValida) {
    estado_ = Estado::SinImu;
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

  // Contacto: solo se permite alejarse en línea recta (un giro puede seguir apretando contra el objeto)
  const bool contactoAdelante = in.bumper[0] || in.bumper[1];
  const bool contactoAtras = in.bumper[2] || in.bumper[3];
  if (contactoAdelante || contactoAtras) w = 0.0f;
  bloqAdelante_ = contactoAdelante;
  bloqAtras_ = contactoAtras;

  // Distancia al frente. Sin dato (sensor desconectado o sin medir todavía) no se avanza.
  // Cerca: tope de velocidad (un min(), así no se acumula con la rampa en pasos sucesivos).
  if (isnan(in.distFrente)) {
    frenteSinDato_ = true;
    bloqAdelante_ = true;
  } else if (in.distFrente <= cfg_.distParada) {
    bloqAdelante_ = true;
  } else if (in.distFrente < cfg_.distLenta) {
    const float tope = cfg_.vMax * (in.distFrente - cfg_.distParada) / (cfg_.distLenta - cfg_.distParada);
    if (v > tope) v = tope;
  }
  if (bloqAdelante_ && v > 0.0f) v = 0.0f;
  if (bloqAtras_ && v < 0.0f) v = 0.0f;
  return true;
}

bool SeguridadBase::rearmar(const EntradasSeguridad &in) {
  if (in.seta || !in.imuValida || !nivelada(in, cfg_.inclMax)) return false;
  estado_ = Estado::Ok;
  return true;
}
