#include "EnlaceMicroRos.h"

#include <rmw_microros/rmw_microros.h>

namespace {
// Descarta a propósito el código de retorno (rcl/rmw usan warn_unused_result y (void) no lo silencia en GCC)
template <typename T>
inline void ignorar(T) {}

constexpr uint32_t PING_CADA_MS = 500;
constexpr int PING_TIMEOUT_MS = 20;
constexpr uint8_t PINGS_PARA_CORTE = 3;  // ~1,5 s sin respuesta = agente desconectado
constexpr uint32_t HORA_REINTENTO_MS = 500;
constexpr uint32_t HORA_CADA_MS = 60000;
constexpr int HORA_TIMEOUT_MS = 50;
constexpr int SPIN_NS = RCL_MS_TO_NS(5);
}  // namespace

void EnlaceMicroRos::begin(Stream &puerto, const char *nodo, size_t nHandles, Crear crear, Destruir destruir) {
  nodo_ = nodo;
  nHandles_ = nHandles;
  crear_ = crear;
  destruir_ = destruir;
  set_microros_serial_transports(puerto);
}

bool EnlaceMicroRos::timeoutPublicador(rcl_publisher_t *p, int ms) {
  return rmw_uros_set_publisher_session_timeout(rcl_publisher_get_rmw_handle(p), ms) == RMW_RET_OK;
}

bool EnlaceMicroRos::crearTodo() {
  allocator_ = rcl_get_default_allocator();
  support_ = {};
  node_ = rcl_get_zero_initialized_node();
  executor_ = rclc_executor_get_zero_initialized_executor();
  if (rclc_support_init(&support_, 0, nullptr, &allocator_) != RCL_RET_OK) return false;
  if (rclc_node_init_default(&node_, nodo_, "", &support_) != RCL_RET_OK) return false;
  if (rclc_executor_init(&executor_, &support_.context, nHandles_, &allocator_) != RCL_RET_OK) return false;
  if (!crear_(&node_, &support_, &executor_)) return false;
  conHora_ = false;
  pingsPerdidos_ = 0;
  if (rmw_uros_sync_session(1000) == RMW_RET_OK && rmw_uros_epoch_synchronized()) conHora_ = true;
  ultimaHoraMs_ = millis();
  return true;
}

void EnlaceMicroRos::destruirTodo() {
  rmw_context_t *ctx = rcl_context_get_rmw_context(&support_.context);
  if (ctx) ignorar(rmw_uros_set_context_entity_destroy_session_timeout(ctx, 0));
  ignorar(rclc_executor_fini(&executor_));
  destruir_(&node_);
  ignorar(rcl_node_fini(&node_));
  ignorar(rclc_support_fini(&support_));
}

void EnlaceMicroRos::loop() {
  const uint32_t ahora = millis();
  switch (estado_) {
    case Estado::Esperando:
      if (ahora - ultimoPingMs_ >= PING_CADA_MS) {
        ultimoPingMs_ = ahora;
        if (rmw_uros_ping_agent(PING_TIMEOUT_MS, 1) == RMW_RET_OK) estado_ = Estado::Disponible;
      }
      break;

    case Estado::Disponible:
      if (crearTodo()) {
        estado_ = Estado::Conectado;
      } else {
        destruirTodo();
        estado_ = Estado::Esperando;
      }
      break;

    case Estado::Conectado:
      if (ahora - ultimoPingMs_ >= PING_CADA_MS) {
        ultimoPingMs_ = ahora;
        pingsPerdidos_ = rmw_uros_ping_agent(PING_TIMEOUT_MS, 1) == RMW_RET_OK ? 0 : pingsPerdidos_ + 1;
        if (pingsPerdidos_ >= PINGS_PARA_CORTE) {
          // Avisar el corte ya, antes de destruir las entidades (lo que puede tardar): el robot se detiene antes
          estado_ = Estado::Desconectado;
          corte_ = true;
          break;
        }
      }
      if (ahora - ultimaHoraMs_ >= (conHora_ ? HORA_CADA_MS : HORA_REINTENTO_MS)) {
        ultimaHoraMs_ = ahora;
        if (rmw_uros_sync_session(HORA_TIMEOUT_MS) == RMW_RET_OK && rmw_uros_epoch_synchronized()) conHora_ = true;
      }
      ignorar(rclc_executor_spin_some(&executor_, SPIN_NS));
      break;

    case Estado::Desconectado:
      destruirTodo();
      estado_ = Estado::Esperando;
      break;
  }
}

bool EnlaceMicroRos::seCorto() {
  const bool c = corte_;
  corte_ = false;
  return c;
}

bool EnlaceMicroRos::hora(builtin_interfaces__msg__Time &t) const {
  if (!conHora_) return false;
  const int64_t ns = rmw_uros_epoch_nanos();
  t.sec = (int32_t)(ns / 1000000000LL);
  t.nanosec = (uint32_t)(ns % 1000000000LL);
  return true;
}

size_t BufferTexto::write(uint8_t c) {
  if (n_ < CAP) {
    buf_[n_++] = (char)c;
    buf_[n_] = '\0';
    return 1;
  }
  if (!lleno_) {  // marcar el corte en las últimas posiciones
    buf_[CAP - 3] = buf_[CAP - 2] = buf_[CAP - 1] = '.';
    lleno_ = true;
  }
  return 1;
}
