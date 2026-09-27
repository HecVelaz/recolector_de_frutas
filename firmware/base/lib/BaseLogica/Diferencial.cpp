#include "Diferencial.h"

#include <math.h>

static constexpr float PI_F = 3.14159265358979f;

static float limitar(float v, float lim) { return v > lim ? lim : (v < -lim ? -lim : v); }

Ruedas Diferencial::ruedasDesde(float v, float w) const {
  v = limitar(v, cfg_.vMax);
  w = limitar(w, cfg_.wMax);
  // rad/s de cada rueda -> rpm
  const float k = 60.0f / (2.0f * PI_F * cfg_.radioRueda);
  Ruedas r{(v - w * cfg_.trocha / 2.0f) * k, (v + w * cfg_.trocha / 2.0f) * k};
  const float mayor = fmaxf(fabsf(r.izq), fabsf(r.der));
  if (mayor > cfg_.rpmMax) {
    const float esc = cfg_.rpmMax / mayor;
    r.izq *= esc;
    r.der *= esc;
  }
  return r;
}

void Diferencial::cmdDesde(const Ruedas &r, float &v, float &w) const {
  const float k = 2.0f * PI_F * cfg_.radioRueda / 60.0f;  // rpm -> m/s
  const float vi = r.izq * k, vd = r.der * k;
  v = (vi + vd) / 2.0f;
  w = (vd - vi) / cfg_.trocha;
}

void Diferencial::rampa(float vObj, float wObj, float dt, float &v, float &w) {
  vObj = limitar(vObj, cfg_.vMax);
  wObj = limitar(wObj, cfg_.wMax);
  vRampa_ += limitar(vObj - vRampa_, cfg_.accLin * dt);
  wRampa_ += limitar(wObj - wRampa_, cfg_.accAng * dt);
  v = vRampa_;
  w = wRampa_;
}

void Odometria::actualizar(float dIzq, float dDer, float dt) {
  const float ds = (dIzq + dDer) / 2.0f;
  const float dth = (dDer - dIzq) / trocha_;
  // Integración en el punto medio del giro
  const float thMedio = th_ + dth / 2.0f;
  x_ += ds * cosf(thMedio);
  y_ += ds * sinf(thMedio);
  th_ = atan2f(sinf(th_ + dth), cosf(th_ + dth));
  if (dt > 0.0f) {
    v_ = ds / dt;
    w_ = dth / dt;
  }
}
