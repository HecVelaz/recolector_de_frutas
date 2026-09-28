// Capa micro-ROS del brazo: tópicos en capa_ros.h. Solo se compila en el entorno `ros`.
#ifdef USAR_MICROROS

#include "capa_ros.h"

#include <Arduino.h>
#include <sensor_msgs/msg/joint_state.h>
#include <std_msgs/msg/float32.h>
#include <std_msgs/msg/string.h>

#include "ControlArticulacion.h"
#include "EnlaceMicroRos.h"
#include "brazo_config.h"

// Definidos en main.cpp
extern ControlArticulacion ctl[N_ART];
extern portMUX_TYPE mux;
extern Print *out;
void ejecutar(char *linea);

namespace {

template <typename T>
inline void ignorar(T) {}

constexpr uint32_t PERIODO_MS = 50;  // joint_states a 20 Hz
constexpr int ESTADO_CADA = 10;      // estado a 2 Hz
constexpr int PUB_TIMEOUT_MS = 10;
constexpr size_t N_HANDLES = 5;      // 4 suscripciones + 1 timer

EnlaceMicroRos enlace;
BufferTexto salida;

rcl_publisher_t pubJoints, pubEstado, pubResp;
rcl_subscription_t subCmd, subCierre, subGiro, subComando;
rcl_timer_t timer;

// Mensajes con memoria estática (micro-ROS no reserva memoria para las secuencias)
sensor_msgs__msg__JointState joints, cmdIn;
std_msgs__msg__String estadoMsg, respMsg, comandoIn;
std_msgs__msg__Float32 cierreIn, giroIn;

char nombres[N_ART][3] = {{'j', '1', 0}, {'j', '2', 0}, {'j', '3', 0}};
rosidl_runtime_c__String nombresOut[N_ART];
double posOut[N_ART], velOut[N_ART], effOut[N_ART];
char marco[] = "brazo_base";

char nombresInBuf[N_ART][8];
rosidl_runtime_c__String nombresIn[N_ART];
double posIn[N_ART], velIn[N_ART], effIn[N_ART];
char marcoIn[32];
char comandoBuf[80];
char estadoBuf[384];
int tick = 0;

// Armado por sesión: después de cada conexión con el agente los movimientos quedan bloqueados hasta recibir
// "armar" por /brazo/comando (un publicador que siguiera mandando no retoma solo el movimiento al reconectar).
// Detener, liberar, diagnóstico y cero se aceptan siempre.
bool armado = false;
uint32_t ultimoAvisoMs = 0;
const char *const MUEVEN[] = {"m", "j", "v", "d", "home", "pinza", "giro"};

bool mueve(const char *cmd) {
  for (const char *c : MUEVEN)
    if (!strcmp(cmd, c)) return true;
  return false;
}

// Aviso de "desarmado" como mucho una vez por segundo (un publicador a 20 Hz no debe inundar la respuesta)
bool armadoOAvisar() {
  if (armado) return true;
  if (millis() - ultimoAvisoMs > 1000) {
    ultimoAvisoMs = millis();
    out->println(">> Brazo DESARMADO: enviar 'armar' por /brazo/comando para habilitar movimientos.");
  }
  return false;
}

void fijarTexto(rosidl_runtime_c__String &s, char *buf, size_t cap) {
  s.data = buf;
  s.size = 0;
  s.capacity = cap;
}

void prepararMensajes() {
  joints = {};
  joints.header.frame_id = {marco, sizeof(marco) - 1, sizeof(marco)};
  for (int i = 0; i < N_ART; i++) nombresOut[i] = {nombres[i], 2, 3};
  joints.name = {nombresOut, N_ART, N_ART};
  joints.position = {posOut, N_ART, N_ART};
  joints.velocity = {velOut, N_ART, N_ART};
  joints.effort = {effOut, 0, N_ART};  // sin torque medido (el duty va en /brazo/estado)

  cmdIn = {};
  fijarTexto(cmdIn.header.frame_id, marcoIn, sizeof(marcoIn));
  for (int i = 0; i < N_ART; i++) fijarTexto(nombresIn[i], nombresInBuf[i], sizeof(nombresInBuf[i]));
  cmdIn.name = {nombresIn, 0, N_ART};
  cmdIn.position = {posIn, 0, N_ART};
  cmdIn.velocity = {velIn, 0, N_ART};
  cmdIn.effort = {effIn, 0, N_ART};

  comandoIn = {};
  fijarTexto(comandoIn.data, comandoBuf, sizeof(comandoBuf));
  estadoMsg = {};
  fijarTexto(estadoMsg.data, estadoBuf, sizeof(estadoBuf));
}

// Ejecuta un comando de texto como si llegara por el monitor serial
void comando(const char *fmt, ...) {
  char linea[80];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(linea, sizeof(linea), fmt, ap);
  va_end(ap);
  ejecutar(linea);
}

// Valida el mensaje completo antes de mover nada y lo aplica como un solo `m` (todo o nada). Las articulaciones
// que no vienen en el mensaje conservan su objetivo actual.
void alRecibirCmd(const void *m) {
  if (!armadoOAvisar()) return;
  const auto *js = static_cast<const sensor_msgs__msg__JointState *>(m);
  float q[N_ART];
  bool dado[N_ART] = {false, false, false};
  portENTER_CRITICAL(&mux);
  for (int i = 0; i < N_ART; i++) q[i] = ctl[i].qObjetivo();
  portEXIT_CRITICAL(&mux);

  if (js->name.size == 0) {  // sin nombres: las tres en orden
    if (js->position.size != N_ART) {
      out->println(">> /brazo/joint_cmd sin nombres necesita 3 posiciones.");
      return;
    }
    for (int i = 0; i < N_ART; i++) {
      q[i] = js->position.data[i] * RAD_TO_DEG;
      dado[i] = true;
    }
  } else {
    if (js->position.size != js->name.size) {
      out->println(">> /brazo/joint_cmd: la cantidad de nombres y de posiciones no coincide.");
      return;
    }
    for (size_t k = 0; k < js->name.size; k++) {
      const rosidl_runtime_c__String &n = js->name.data[k];
      const int i = (n.size == 2 && n.data[0] == 'j') ? n.data[1] - '1' : -1;
      if (i < 0 || i >= N_ART || dado[i]) {
        out->printf(">> /brazo/joint_cmd: nombre '%.*s' desconocido o repetido (usar j1, j2, j3). No se movió nada.\n",
                    (int)n.size, n.data);
        return;
      }
      q[i] = js->position.data[k] * RAD_TO_DEG;
      dado[i] = true;
    }
  }
  for (int i = 0; i < N_ART; i++) {
    // Un número no finito o enorme se rechaza antes de formatearlo (si no, el texto se cortaría)
    if (!isfinite(q[i]) || fabsf(q[i]) > 720.0f) {
      out->printf(">> /brazo/joint_cmd: j%d fuera de rango. No se movió nada.\n", i + 1);
      return;
    }
  }
  comando("m %.3f %.3f %.3f", q[0], q[1], q[2]);
}

void alRecibirCierre(const void *m) {
  const float v = static_cast<const std_msgs__msg__Float32 *>(m)->data;
  if (!armadoOAvisar()) return;
  if (!isfinite(v) || fabsf(v) > 1000.0f) return;  // ejecutar() valida el rango real
  comando("pinza %.1f", v);
}

void alRecibirGiro(const void *m) {
  const float v = static_cast<const std_msgs__msg__Float32 *>(m)->data;
  if (!armadoOAvisar()) return;
  if (!isfinite(v) || fabsf(v) > 1000.0f) return;
  comando("giro %.1f", v);
}

void alRecibirComando(const void *m) {
  const auto *s = static_cast<const std_msgs__msg__String *>(m);
  char linea[80];
  const size_t n = s->data.size < sizeof(linea) - 1 ? s->data.size : sizeof(linea) - 1;
  memcpy(linea, s->data.data, n);
  linea[n] = '\0';
  // Primera palabra: armar / desarmar, o un comando de movimiento con el brazo desarmado
  char primera[8] = {0};
  sscanf(linea, "%7s", primera);
  if (!strcmp(primera, "armar")) {
    armado = true;
    out->println(">> Brazo ARMADO: se aceptan movimientos.");
    return;
  }
  if (!strcmp(primera, "desarmar")) {
    armado = false;
    char st[] = "s";
    ejecutar(st);
    out->println(">> Brazo DESARMADO.");
    return;
  }
  if (mueve(primera) && !armadoOAvisar()) return;
  ejecutar(linea);
}

const char *textoModo(ControlArticulacion::Modo mo) {
  switch (mo) {
    case ControlArticulacion::Modo::Posicion: return "posicion";
    case ControlArticulacion::Modo::Velocidad: return "velocidad";
    case ControlArticulacion::Modo::Duty: return "duty";
    default: return "libre";
  }
}

void alTimer(rcl_timer_t *t, int64_t) {
  if (!t || !enlace.hora(joints.header.stamp)) return;  // sin hora del agente no se publica
  ControlArticulacion c[N_ART];
  portENTER_CRITICAL(&mux);
  for (int i = 0; i < N_ART; i++) c[i] = ctl[i];
  portEXIT_CRITICAL(&mux);

  for (int i = 0; i < N_ART; i++) {
    posOut[i] = c[i].q() * DEG_TO_RAD;
    velOut[i] = c[i].w() * TWO_PI / 60.0 / CFG_ART[i].relacion;  // rpm del motor -> rad/s de la articulación
  }
  ignorar(rcl_publish(&pubJoints, &joints, nullptr));

  if (++tick % ESTADO_CADA == 0) {
    size_t n = 0;
    n += snprintf(estadoBuf, sizeof(estadoBuf), "%s; ", armado ? "ARMADO" : "DESARMADO");
    for (int i = 0; i < N_ART && n < sizeof(estadoBuf); i++)
      n += snprintf(estadoBuf + n, sizeof(estadoBuf) - n, "J%d %s %s u=%.0f%% falla=%s%s; ", i + 1,
                    textoModo(c[i].modo()), c[i].conCero() ? "cero" : "SIN_CERO", c[i].u(), c[i].textoFalla(),
                    c[i].modo() == ControlArticulacion::Modo::Posicion && c[i].llego() ? " llego" : "");
    estadoMsg.data.size = n < sizeof(estadoBuf) ? n : sizeof(estadoBuf) - 1;
    ignorar(rcl_publish(&pubEstado, &estadoMsg, nullptr));
  }
}

bool crear(rcl_node_t *node, rclc_support_t *support, rclc_executor_t *ex) {
  pubJoints = rcl_get_zero_initialized_publisher();
  pubEstado = rcl_get_zero_initialized_publisher();
  pubResp = rcl_get_zero_initialized_publisher();
  subCmd = rcl_get_zero_initialized_subscription();
  subCierre = rcl_get_zero_initialized_subscription();
  subGiro = rcl_get_zero_initialized_subscription();
  subComando = rcl_get_zero_initialized_subscription();
  timer = rcl_get_zero_initialized_timer();

  const auto *tJoint = ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState);
  const auto *tStr = ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String);
  const auto *tF32 = ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32);
  if (rclc_publisher_init_default(&pubJoints, node, tJoint, "brazo/joint_states") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubEstado, node, tStr, "brazo/estado") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubResp, node, tStr, "brazo/respuesta") != RCL_RET_OK) return false;
  for (rcl_publisher_t *p : {&pubJoints, &pubEstado, &pubResp})
    if (!EnlaceMicroRos::timeoutPublicador(p, PUB_TIMEOUT_MS)) return false;

  if (rclc_subscription_init_default(&subCmd, node, tJoint, "brazo/joint_cmd") != RCL_RET_OK) return false;
  if (rclc_subscription_init_default(&subCierre, node, tF32, "pinza/cierre") != RCL_RET_OK) return false;
  if (rclc_subscription_init_default(&subGiro, node, tF32, "pinza/giro") != RCL_RET_OK) return false;
  if (rclc_subscription_init_default(&subComando, node, tStr, "brazo/comando") != RCL_RET_OK) return false;
  if (rclc_timer_init_default2(&timer, support, RCL_MS_TO_NS(PERIODO_MS), alTimer, true) != RCL_RET_OK) return false;

  if (rclc_executor_add_subscription(ex, &subCmd, &cmdIn, alRecibirCmd, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(ex, &subCierre, &cierreIn, alRecibirCierre, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(ex, &subGiro, &giroIn, alRecibirGiro, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(ex, &subComando, &comandoIn, alRecibirComando, ON_NEW_DATA) != RCL_RET_OK)
    return false;
  if (rclc_executor_add_timer(ex, &timer) != RCL_RET_OK) return false;
  return true;
}

void destruir(rcl_node_t *node) {
  ignorar(rcl_timer_fini(&timer));
  for (rcl_subscription_t *s : {&subCmd, &subCierre, &subGiro, &subComando}) ignorar(rcl_subscription_fini(s, node));
  for (rcl_publisher_t *p : {&pubJoints, &pubEstado, &pubResp}) ignorar(rcl_publisher_fini(p, node));
}

}  // namespace

void rosBegin() {
  out = &salida;
  prepararMensajes();
  enlace.begin(Serial, "brazo", N_HANDLES, crear, destruir);
}

void rosLoop() {
  static bool estabaConectado = false;
  enlace.loop();
  if (enlace.seCorto()) {
    char s[] = "s";
    ejecutar(s);  // sin agente, J1-J3 se detienen y sostienen. Los servos quedan donde están: soltarlos
                  // (sin pulso) podría abrir la pinza y dejar caer el limón.
    armado = false;
    out->println(">> Se perdió el micro-ROS Agent: brazo detenido y desarmado.");
  }
  if (enlace.conectado() && !estabaConectado) {
    armado = false;  // cada sesión empieza desarmada
    out->println(">> Conectado al agente. Brazo DESARMADO: enviar 'armar' por /brazo/comando.");
  }
  estabaConectado = enlace.conectado();
  if (enlace.conectado() && !salida.vacio()) {
    respMsg.data.data = const_cast<char *>(salida.texto());
    respMsg.data.size = salida.largo();
    respMsg.data.capacity = salida.largo() + 1;
    // Un solo intento: con varios fragmentos rcl_publish puede dar error aunque el mensaje llegue, y
    // reintentar en cada vuelta satura el enlace (visto en placa con el mensaje de arranque)
    ignorar(rcl_publish(&pubResp, &respMsg, nullptr));
    salida.limpiar();
  }
}

#endif  // USAR_MICROROS
