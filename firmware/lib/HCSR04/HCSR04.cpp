#include "HCSR04.h"

#include "soc/gpio_reg.h"

static constexpr float VEL_SONIDO = 343.0f;  // m/s a ~20 °C

// Nivel del pin leyendo el registro: digitalRead no está en IRAM y no debe usarse en la interrupción
static inline IRAM_ATTR int nivel(int pin) {
  return pin < 32 ? (REG_READ(GPIO_IN_REG) >> pin) & 1 : (REG_READ(GPIO_IN1_REG) >> (pin - 32)) & 1;
}

void IRAM_ATTR HCSR04::alCambiar(void *arg) {
  Canal *c = static_cast<Canal *>(arg);
  const uint32_t ahora = micros();
  portENTER_CRITICAL_ISR(&c->padre->mux_);
  if (nivel(c->pin)) {
    c->subidaUs = ahora;
  } else if (c->subidaUs) {
    c->anchoUs = ahora - c->subidaUs;
    c->subidaUs = 0;
  }
  portEXIT_CRITICAL_ISR(&c->padre->mux_);
}

bool HCSR04::begin(int pinTrig, const int *pinesEcho, int n) {
  if (n < 1 || n > MAX_SENSORES) return false;
  pinTrig_ = pinTrig;
  n_ = n;
  pinMode(pinTrig_, OUTPUT);
  digitalWrite(pinTrig_, LOW);
  for (int i = 0; i < n_; i++) {
    Canal &c = canal_[i];
    c.padre = this;
    c.pin = pinesEcho[i];
    c.subidaUs = 0;
    c.anchoUs = 0;
    c.metros = NAN;
    pinMode(c.pin, INPUT);
    attachInterruptArg(digitalPinToInterrupt(c.pin), alCambiar, &c, CHANGE);
  }
  return true;
}

void HCSR04::disparar() {
  // Cerrar el ciclo anterior
  for (int i = 0; i < n_; i++) {
    Canal &c = canal_[i];
    portENTER_CRITICAL(&mux_);
    const uint32_t ancho = c.anchoUs;
    const bool sigueAlto = c.subidaUs != 0;  // el eco todavía no bajó: pulso larguísimo
    c.anchoUs = 0;
    c.subidaUs = 0;
    portEXIT_CRITICAL(&mux_);
    if (ancho > 0 && ancho < ECO_MAX_US) c.metros = ancho * 1e-6f * VEL_SONIDO / 2.0f;
    else if (ancho >= ECO_MAX_US || sigueAlto) c.metros = INFINITY;  // hubo eco, pero sin obstáculo al alcance
    else c.metros = NAN;  // ningún pulso: el sensor no respondió
  }
  digitalWrite(pinTrig_, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinTrig_, LOW);
}

float HCSR04::distancia(int i) const { return (i >= 0 && i < n_) ? canal_[i].metros : NAN; }
