#pragma once

// Cinemática de la base diferencial y odometría, sin Arduino (se prueba en la PC: test/).
// Convenciones ROS (REP-103): x adelante, y a la izquierda, theta antihorario. v en m/s, w en rad/s.

struct ConfigDiferencial {
  float radioRueda;  // m
  float trocha;      // m, distancia entre los centros de las ruedas
  float rpmMax;      // rpm máximas de rueda que se piden al control
  float vMax;        // m/s
  float wMax;        // rad/s
  float accLin;      // m/s²
  float accAng;      // rad/s²
};

struct Ruedas {
  float izq, der;  // rpm
};

class Diferencial {
 public:
  explicit Diferencial(const ConfigDiferencial &cfg) : cfg_(cfg) {}

  // (v, w) -> rpm de cada rueda. Recorta v y w a sus máximos y, si una rueda pasa de rpmMax, escala las dos
  // por igual (se conserva la curvatura de la trayectoria).
  Ruedas ruedasDesde(float v, float w) const;
  // rpm de cada rueda -> (v, w)
  void cmdDesde(const Ruedas &r, float &v, float &w) const;

  // Rampa de aceleración sobre (v, w): llamar cada dt con la consigna; devuelve la consigna limitada.
  void rampa(float vObj, float wObj, float dt, float &v, float &w);
  void reiniciarRampa() { vRampa_ = wRampa_ = 0.0f; }
  // La seguridad puede recortar el comando después de la rampa: la rampa sigue desde el valor recortado
  // (si no, al liberarse saltaría de golpe a lo que venía acumulando)
  void fijarRampa(float v, float w) {
    vRampa_ = v;
    wRampa_ = w;
  }

  const ConfigDiferencial &cfg() const { return cfg_; }

 private:
  ConfigDiferencial cfg_;
  float vRampa_ = 0.0f, wRampa_ = 0.0f;
};

// Odometría por integración de los avances de cada rueda (punto medio).
class Odometria {
 public:
  explicit Odometria(float trocha) : trocha_(trocha) {}
  // dIzq, dDer: metros recorridos por cada rueda desde la llamada anterior; dt en s.
  void actualizar(float dIzq, float dDer, float dt);
  void reiniciar() { x_ = y_ = th_ = v_ = w_ = 0.0f; }

  float x() const { return x_; }
  float y() const { return y_; }
  float theta() const { return th_; }  // rad, en (-pi, pi]
  float v() const { return v_; }
  float w() const { return w_; }

 private:
  float trocha_;
  float x_ = 0.0f, y_ = 0.0f, th_ = 0.0f, v_ = 0.0f, w_ = 0.0f;
};
