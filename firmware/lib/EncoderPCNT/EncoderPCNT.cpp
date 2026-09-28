#include "EncoderPCNT.h"

#include <Arduino.h>

#include "Desenvolver.h"
#include "driver/gpio.h"

bool EncoderPCNT::begin(int pinA, int pinB, pcnt_unit_t unit, uint32_t filterNs) {
  ready_ = false;
  unit_ = unit;
  pinA_ = pinA;
  pinB_ = pinB;

  // Cuadratura x4, como el ejemplo rotary_encoder de ESP-IDF 4.4.
  // Canal 0: cuenta los flancos de A; el nivel de B decide el sentido.
  pcnt_config_t c = {};
  c.pulse_gpio_num = pinA;
  c.ctrl_gpio_num = pinB;
  c.channel = PCNT_CHANNEL_0;
  c.unit = unit;
  c.pos_mode = PCNT_COUNT_DEC;
  c.neg_mode = PCNT_COUNT_INC;
  c.lctrl_mode = PCNT_MODE_REVERSE;
  c.hctrl_mode = PCNT_MODE_KEEP;
  c.counter_h_lim = PCNT_LIMITE;
  c.counter_l_lim = -PCNT_LIMITE;
  if (pcnt_unit_config(&c) != ESP_OK) return false;

  // Canal 1: cuenta los flancos de B; el nivel de A decide el sentido.
  c.pulse_gpio_num = pinB;
  c.ctrl_gpio_num = pinA;
  c.channel = PCNT_CHANNEL_1;
  c.pos_mode = PCNT_COUNT_INC;
  c.neg_mode = PCNT_COUNT_DEC;
  if (pcnt_unit_config(&c) != ESP_OK) return false;

  // Pull-ups internos por si las salidas del encoder son de colector abierto
  gpio_pullup_en((gpio_num_t)pinA);
  gpio_pullup_en((gpio_num_t)pinB);

  // El filtro se mide en ciclos del APB (80 MHz), 10 bits
  uint32_t cycles = filterNs * 80 / 1000;
  if (cycles > 1023) cycles = 1023;
  if (cycles > 0) {
    pcnt_set_filter_value(unit, (uint16_t)cycles);
    pcnt_filter_enable(unit);
  } else {
    pcnt_filter_disable(unit);
  }

  ready_ = true;
  reset();
  return true;
}

int64_t EncoderPCNT::count() {
  if (!ready_) return 0;
  int16_t v;
  portENTER_CRITICAL(&mux_);  // lectura y acumulador juntos (se llama desde la tarea de control y la de comandos)
  pcnt_get_counter_value(unit_, &v);
  acc_ += desenvolverPcnt((int32_t)v - lastHw_);
  lastHw_ = v;
  const int64_t c = acc_;
  portEXIT_CRITICAL(&mux_);
  return c;
}

int32_t EncoderPCNT::delta() {
  const int64_t c = count();
  const int64_t d = c - lastDelta_;
  lastDelta_ = c;
  return (int32_t)d;
}

void EncoderPCNT::reset() {
  if (!ready_) return;
  portENTER_CRITICAL(&mux_);
  pcnt_counter_pause(unit_);
  pcnt_counter_clear(unit_);
  lastHw_ = 0;
  acc_ = 0;
  lastDelta_ = 0;
  pcnt_counter_resume(unit_);
  portEXIT_CRITICAL(&mux_);
}

int EncoderPCNT::levelA() const { return gpio_get_level((gpio_num_t)pinA_); }
int EncoderPCNT::levelB() const { return gpio_get_level((gpio_num_t)pinB_); }
