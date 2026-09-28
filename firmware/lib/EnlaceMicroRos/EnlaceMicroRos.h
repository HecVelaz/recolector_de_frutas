#pragma once

#include <Arduino.h>
#include <builtin_interfaces/msg/time.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>

// Conexión con el micro-ROS Agent por serial, con el mismo esquema probado en pruebas-esp32/02-imu-ros2:
// esperar al agente -> crear entidades -> ping cada 500 ms (3 sin respuesta = desconectado) -> destruir y volver
// a esperar. Se puede reiniciar el agente sin resetear la placa. También sincroniza la hora con el agente.
//
// Con transporte serial el USB es del agente: el firmware no debe imprimir por Serial.
class EnlaceMicroRos {
 public:
  // crear: crea los publishers, subscriptions y timers del firmware y los agrega al executor (ya inicializado
  // con nHandles). destruir: los libera (el agente puede no estar: no esperar confirmaciones).
  using Crear = bool (*)(rcl_node_t *node, rclc_support_t *support, rclc_executor_t *executor);
  using Destruir = void (*)(rcl_node_t *node);

  // puerto: Serial ya abierto (Serial.begin) antes de llamar.
  void begin(Stream &puerto, const char *nodo, size_t nHandles, Crear crear, Destruir destruir);

  // Llamar seguido desde loop(). Las esperas propias están acotadas (ping 100 ms, hora 50 ms, executor 5 ms), pero
  // al conectar (sincronización inicial hasta 1 s, creación de entidades) y dentro de los callbacks puede tardar
  // más: la seguridad del robot no debe depender de loop() (vive en la tarea de control).
  void loop();

  bool conectado() const { return estado_ == Estado::Conectado; }
  // true una sola vez cada vez que se pierde la conexión, apenas se detecta (para detener el robot)
  bool seCorto();
  // Hora del agente. false si todavía no hay sincronización: no publicar mensajes con stamp sin hora.
  bool hora(builtin_interfaces__msg__Time &t) const;
  // Diagnóstico desde el arranque (no se reinician al reconectar): pings sin respuesta y cortes declarados
  uint32_t pingsFallidos() const { return pingsFallidos_; }
  uint32_t cortes() const { return cortes_; }

  // Espera máxima de confirmación de un publisher reliable (acota cuánto bloquea cada rcl_publish)
  static bool timeoutPublicador(rcl_publisher_t *p, int ms);

 private:
  enum class Estado { Esperando, Disponible, Conectado, Desconectado };
  bool crearTodo();
  void destruirTodo();

  const char *nodo_ = nullptr;
  size_t nHandles_ = 0;
  Crear crear_ = nullptr;
  Destruir destruir_ = nullptr;

  rcl_allocator_t allocator_;
  rclc_support_t support_;
  rcl_node_t node_;
  rclc_executor_t executor_;

  Estado estado_ = Estado::Esperando;
  uint32_t ultimoPingMs_ = 0;
  uint8_t pingsPerdidos_ = 0;
  uint32_t ultimaHoraMs_ = 0;
  bool conHora_ = false;
  bool corte_ = false;
  uint32_t pingsFallidos_ = 0;
  uint32_t cortes_ = 0;
};

// Print que junta texto en memoria, para mandar por un tópico lo que en modo serial se imprimiría.
// Si se llena, descarta lo que sobra (y lo marca con "...").
class BufferTexto : public Print {
 public:
  size_t write(uint8_t c) override;
  bool vacio() const { return n_ == 0; }
  const char *texto() const { return buf_; }
  size_t largo() const { return n_; }
  void limpiar() {
    n_ = 0;
    buf_[0] = '\0';
    lleno_ = false;
  }

 private:
  static constexpr size_t CAP = 1024;
  char buf_[CAP + 1] = {0};
  size_t n_ = 0;
  bool lleno_ = false;
};
