#pragma once

#include <stdint.h>

// Reglas de seguridad de la base, sin Arduino (se prueba en la PC: test/). Decide qué movimiento se permite
// a partir de los sensores; la tarea de control aplica el resultado. Requisitos de la guía R2: H5 (distancia y
// bumpers), H8 (seta), H9 (vuelco y pérdida de comunicación), N3 (detención ante obstáculos).

struct ConfigSeguridad {
  float distParada;    // m: obstáculo al frente más cerca que esto -> no avanza
  float distLenta;     // m: entre distParada y esto, la velocidad de avance tiene un tope que baja linealmente
  float inclMax;       // grados de roll o pitch que se consideran vuelco
  uint32_t sinCmdMs;   // watchdog de comandos: sin comandos por más de esto -> parada (0 = apagado)
  float bateriaMin;    // V: por debajo, aviso de batería baja (no detiene)
  float vMax;          // m/s: tope de avance lejos de obstáculos (base del tope por cercanía)
};

struct EntradasSeguridad {
  bool bumper[4];      // frente-izq, frente-der, atrás-izq, atrás-der (true = apretado)
  float distFrente;    // m; INFINITY = nada a la vista; NAN = sensor sin eco (desconectado o sin medir)
  bool seta;           // true = seta apretada (o cable cortado)
  float roll, pitch;   // grados
  uint32_t msSinCmd;   // tiempo desde el último comando aceptado
  float bateria;       // V; NAN = sin medir
  bool imuValida;      // hay una muestra de la IMU reciente (sin ella no se puede vigilar el vuelco)
};

class SeguridadBase {
 public:
  // EMERGENCIA (seta) y VUELCO quedan enclavados: se salen solo con rearmar() y la causa ya despejada.
  enum class Estado : uint8_t { Ok, Emergencia, Vuelco, SinComandos, SinImu };

  explicit SeguridadBase(const ConfigSeguridad &cfg) : cfg_(cfg) {}

  // Evalúa las entradas y recorta el comando (v, w). Devuelve true si los motores pueden estar habilitados;
  // false = puentes deshabilitados (emergencia) o parada (v = w = 0).
  bool filtrar(const EntradasSeguridad &in, float &v, float &w);

  // Rearme manual: borra EMERGENCIA y VUELCO solo si la causa ya no está (seta suelta, base nivelada).
  bool rearmar(const EntradasSeguridad &in);

  void fijarWatchdog(uint32_t ms) { cfg_.sinCmdMs = ms; }
  uint32_t watchdog() const { return cfg_.sinCmdMs; }

  Estado estado() const { return estado_; }
  bool bloqueaAdelante() const { return bloqAdelante_; }
  bool bloqueaAtras() const { return bloqAtras_; }
  bool frenteSinDato() const { return frenteSinDato_; }
  bool bateriaBaja() const { return bateriaBaja_; }
  bool deshabilitar() const { return estado_ == Estado::Emergencia; }  // puentes en bajo (EN = 0)
  static const char *texto(Estado e);

 private:
  ConfigSeguridad cfg_;
  Estado estado_ = Estado::Ok;
  bool bloqAdelante_ = false, bloqAtras_ = false, bateriaBaja_ = false, frenteSinDato_ = false;
};
