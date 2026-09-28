// Capa micro-ROS de la base: tópicos en capa_ros.h. Solo se compila en el entorno `ros`.
#ifdef USAR_MICROROS

#include "capa_ros.h"

#include <Arduino.h>
#include <geometry_msgs/msg/twist.h>
#include <nav_msgs/msg/odometry.h>
#include <sensor_msgs/msg/battery_state.h>
#include <sensor_msgs/msg/imu.h>
#include <sensor_msgs/msg/nav_sat_fix.h>
#include <sensor_msgs/msg/range.h>
#include <std_msgs/msg/string.h>
#include <std_msgs/msg/u_int8.h>

#include "EnlaceMicroRos.h"
#include "UP501.h"

// Definidos en main.cpp
extern Print *out;
extern UP501 gps;
void ejecutar(char *linea);

namespace {

template <typename T>
inline void ignorar(T) {}

constexpr uint32_t PERIODO_MS = 20;  // 50 Hz: IMU en cada paso
constexpr int ODOM_CADA = 2;         // 25 Hz
constexpr int RANGO_CADA = 5;        // 10 Hz: ultrasonidos y bumpers
constexpr int ESTADO_CADA = 25;      // 2 Hz
constexpr int BATERIA_CADA = 50;     // 1 Hz
constexpr int PUB_TIMEOUT_MS = 10;
constexpr size_t N_HANDLES = 3;      // 2 suscripciones + 1 timer
constexpr char WD_ROS[] = "wd 300";  // watchdog de /cmd_vel con micro-ROS
constexpr float GRAVEDAD = 9.80665f;

EnlaceMicroRos enlace;
BufferTexto salida;

rcl_publisher_t pubOdom, pubImu, pubRango[3], pubBumpers, pubGps, pubBateria, pubEstado, pubResp;
rcl_subscription_t subCmdVel, subComando;
rcl_timer_t timer;

nav_msgs__msg__Odometry odomMsg;
sensor_msgs__msg__Imu imuMsg;
sensor_msgs__msg__Range rangoMsg[3];
std_msgs__msg__UInt8 bumpersMsg;
sensor_msgs__msg__NavSatFix gpsMsg;
sensor_msgs__msg__BatteryState bateriaMsg;
std_msgs__msg__String estadoMsg, respMsg, comandoIn;
geometry_msgs__msg__Twist cmdVelIn;

char marcoOdom[] = "odom", marcoBase[] = "base_link", marcoImu[] = "imu_link", marcoGps[] = "gps_link";
char marcoRango[3][12] = {"us_frente", "us_izq", "us_der"};
const char *TOPICO_RANGO[3] = {"range/frente", "range/izq", "range/der"};
char comandoBuf[80];
char estadoBuf[320];
int tick = 0;

// Armado por sesión: después de cada conexión con el agente, /cmd_vel y los comandos que mueven quedan
// bloqueados hasta recibir "armar" por /base/comando (un publicador que siguiera mandando no retoma solo el
// movimiento al reconectar). Detener, liberar, rearmar la seguridad y diagnóstico se aceptan siempre.
bool armado = false;
uint32_t ultimoAvisoMs = 0;

bool mueve(const char *cmd) { return !strcmp(cmd, "v") || !strcmp(cmd, "w") || !strcmp(cmd, "d"); }

// Aviso de "desarmada" como mucho una vez por segundo (/cmd_vel llega a 10-50 Hz)
bool armadoOAvisar() {
  if (armado) return true;
  if (millis() - ultimoAvisoMs > 1000) {
    ultimoAvisoMs = millis();
    out->println(">> Base DESARMADA: enviar 'armar' por /base/comando para habilitar /cmd_vel.");
  }
  return false;
}

rosidl_runtime_c__String texto(char *s) { return {s, strlen(s), strlen(s) + 1}; }

void prepararMensajes() {
  odomMsg = {};
  odomMsg.header.frame_id = texto(marcoOdom);
  odomMsg.child_frame_id = texto(marcoBase);
  // Covarianzas diagonales aproximadas (x, y, yaw medidos; z, roll, pitch no: varianza enorme)
  const double covPose[6] = {0.01, 0.01, 1e6, 1e6, 1e6, 0.05};
  const double covVel[6] = {0.005, 1e6, 1e6, 1e6, 1e6, 0.02};
  for (int i = 0; i < 6; i++) {
    odomMsg.pose.covariance[i * 7] = covPose[i];
    odomMsg.twist.covariance[i * 7] = covVel[i];
  }

  imuMsg = {};
  imuMsg.header.frame_id = texto(marcoImu);
  imuMsg.orientation_covariance[0] = -1.0;  // sin orientación (la estima imu_filter_madgwick)
  for (int i = 0; i < 3; i++) {
    imuMsg.angular_velocity_covariance[i * 4] = 1e-6;   // como en pruebas-esp32/02-imu-ros2
    imuMsg.linear_acceleration_covariance[i * 4] = 3e-4;
  }

  for (int k = 0; k < 3; k++) {
    rangoMsg[k] = {};
    rangoMsg[k].header.frame_id = texto(marcoRango[k]);
    rangoMsg[k].radiation_type = sensor_msgs__msg__Range__ULTRASOUND;
    rangoMsg[k].field_of_view = 0.26f;  // ~15° del HC-SR04
    rangoMsg[k].min_range = 0.02f;
    rangoMsg[k].max_range = 4.0f;
  }

  gpsMsg = {};
  gpsMsg.header.frame_id = texto(marcoGps);
  gpsMsg.status.service = sensor_msgs__msg__NavSatStatus__SERVICE_GPS;

  bateriaMsg = {};
  bateriaMsg.present = true;
  bateriaMsg.current = bateriaMsg.charge = bateriaMsg.capacity = bateriaMsg.design_capacity = NAN;
  bateriaMsg.percentage = bateriaMsg.temperature = NAN;
  bateriaMsg.power_supply_status = sensor_msgs__msg__BatteryState__POWER_SUPPLY_STATUS_UNKNOWN;

  comandoIn = {};
  comandoIn.data = {comandoBuf, 0, sizeof(comandoBuf)};
  estadoMsg = {};
  estadoMsg.data = {estadoBuf, 0, sizeof(estadoBuf)};
}

void alRecibirCmdVel(const void *m) {
  if (!armadoOAvisar()) return;
  const auto *t = static_cast<const geometry_msgs__msg__Twist *>(m);
  baseCmdVel((float)t->linear.x, (float)t->angular.z);
}

void alRecibirComando(const void *m) {
  const auto *s = static_cast<const std_msgs__msg__String *>(m);
  char linea[80];
  const size_t n = s->data.size < sizeof(linea) - 1 ? s->data.size : sizeof(linea) - 1;
  memcpy(linea, s->data.data, n);
  linea[n] = '\0';
  char primera[8] = {0};
  sscanf(linea, "%7s", primera);
  if (!strcmp(primera, "armar")) {
    armado = true;
    out->println(">> Base ARMADA: se acepta /cmd_vel.");
    return;
  }
  if (!strcmp(primera, "desarmar")) {
    armado = false;
    char st[] = "s";
    ejecutar(st);
    out->println(">> Base DESARMADA.");
    return;
  }
  if (mueve(primera) && !armadoOAvisar()) return;
  ejecutar(linea);
}

void publicarGps() {
  UP501::Fix f;
  while (gps.pollEpoch(f)) {
    if (!enlace.hora(gpsMsg.header.stamp)) continue;
    gpsMsg.status.status = f.fix ? (int8_t)sensor_msgs__msg__NavSatStatus__STATUS_FIX
                                 : (int8_t)sensor_msgs__msg__NavSatStatus__STATUS_NO_FIX;
    gpsMsg.latitude = f.fix ? f.latDeg : NAN;
    gpsMsg.longitude = f.fix ? f.lonDeg : NAN;
    // NavSatFix pide altura sobre el elipsoide: MSL + separación del geoide. Sin la separación no se puede
    // calcular (usar MSL como si fuera elipsoidal sería un error de decenas de metros): NaN
    gpsMsg.altitude = f.fix && isfinite(f.altMslM) && isfinite(f.geoidSepM) ? f.altMslM + f.geoidSepM : NAN;
    // Covarianza aproximada a partir del HDOP (UERE ~5 m); vertical el doble
    const double h = isfinite(f.hdop) ? f.hdop * 5.0 : 50.0;
    gpsMsg.position_covariance[0] = gpsMsg.position_covariance[4] = h * h;
    gpsMsg.position_covariance[8] = 4 * h * h;
    gpsMsg.position_covariance_type = sensor_msgs__msg__NavSatFix__COVARIANCE_TYPE_APPROXIMATED;
    ignorar(rcl_publish(&pubGps, &gpsMsg, nullptr));
  }
}

void alTimer(rcl_timer_t *t, int64_t) {
  builtin_interfaces__msg__Time ahora;
  if (!t || !enlace.hora(ahora)) return;  // sin hora del agente no se publica
  tick++;
  EstadoBase e;
  baseLeer(e);

  if (e.imuValida) {
    imuMsg.header.stamp = ahora;
    imuMsg.linear_acceleration.x = e.acc[0] * GRAVEDAD;
    imuMsg.linear_acceleration.y = e.acc[1] * GRAVEDAD;
    imuMsg.linear_acceleration.z = e.acc[2] * GRAVEDAD;
    imuMsg.angular_velocity.x = e.gyro[0] * DEG_TO_RAD;
    imuMsg.angular_velocity.y = e.gyro[1] * DEG_TO_RAD;
    imuMsg.angular_velocity.z = e.gyro[2] * DEG_TO_RAD;
    ignorar(rcl_publish(&pubImu, &imuMsg, nullptr));
  }

  if (tick % ODOM_CADA == 0) {
    odomMsg.header.stamp = ahora;
    odomMsg.pose.pose.position.x = e.x;
    odomMsg.pose.pose.position.y = e.y;
    odomMsg.pose.pose.orientation.z = sinf(e.th / 2);
    odomMsg.pose.pose.orientation.w = cosf(e.th / 2);
    odomMsg.twist.twist.linear.x = e.v;
    odomMsg.twist.twist.angular.z = e.w;
    ignorar(rcl_publish(&pubOdom, &odomMsg, nullptr));
  }

  if (tick % RANGO_CADA == 0) {
    for (int k = 0; k < 3; k++) {
      rangoMsg[k].header.stamp = ahora;
      rangoMsg[k].range = e.dist[k];  // REP-117: +Inf = nada al alcance, NaN = medición inválida
      ignorar(rcl_publish(&pubRango[k], &rangoMsg[k], nullptr));
    }
    bumpersMsg.data = 0;
    for (int k = 0; k < 4; k++) bumpersMsg.data |= e.bumper[k] ? (1u << k) : 0;
    ignorar(rcl_publish(&pubBumpers, &bumpersMsg, nullptr));
  }

  if (tick % BATERIA_CADA == 0 && isfinite(e.bateria)) {
    bateriaMsg.header.stamp = ahora;
    bateriaMsg.voltage = e.bateria;
    ignorar(rcl_publish(&pubBateria, &bateriaMsg, nullptr));
  }

  if (tick % ESTADO_CADA == 0) {
    const int n = snprintf(estadoBuf, sizeof(estadoBuf),
                           "%s modo=%s seguridad=%s%s%s%s%s%s imu=%s rueda_izq=%s rueda_der=%s",
                           armado ? "ARMADA" : "DESARMADA", e.modo,
                           SeguridadBase::texto(e.seg), e.seta ? " SETA" : "", e.bloqAdelante ? " no_avanza" : "",
                           e.frenteSinDato ? "(frente_sin_eco)" : "", e.bloqAtras ? " no_retrocede" : "",
                           e.bateriaBaja ? " BATERIA_BAJA" : "", e.imuValida ? "ok" : "SIN_DATOS",
                           ControlArticulacion::texto(e.falla[0]), ControlArticulacion::texto(e.falla[1]));
    estadoMsg.data.size = n < (int)sizeof(estadoBuf) ? n : sizeof(estadoBuf) - 1;
    ignorar(rcl_publish(&pubEstado, &estadoMsg, nullptr));
  }

  publicarGps();
}

bool crear(rcl_node_t *node, rclc_support_t *support, rclc_executor_t *ex) {
  for (rcl_publisher_t *p : {&pubOdom, &pubImu, &pubRango[0], &pubRango[1], &pubRango[2], &pubBumpers, &pubGps,
                             &pubBateria, &pubEstado, &pubResp})
    *p = rcl_get_zero_initialized_publisher();
  subCmdVel = rcl_get_zero_initialized_subscription();
  subComando = rcl_get_zero_initialized_subscription();
  timer = rcl_get_zero_initialized_timer();

  const auto *tStr = ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String);
  // Best effort para los flujos rápidos que caben en un paquete (IMU, rangos): no esperan confirmación.
  // Odometry (~700 bytes) no entra en un paquete: va reliable, que fragmenta.
  if (rclc_publisher_init_best_effort(&pubImu, node, ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu), "imu/data_raw") != RCL_RET_OK) return false;
  for (int k = 0; k < 3; k++)
    if (rclc_publisher_init_best_effort(&pubRango[k], node, ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Range), TOPICO_RANGO[k]) != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubOdom, node, ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry), "odom") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubBumpers, node, ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt8), "bumpers") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubGps, node, ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, NavSatFix), "gps/fix") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubBateria, node, ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, BatteryState), "battery") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubEstado, node, tStr, "base/estado") != RCL_RET_OK) return false;
  if (rclc_publisher_init_default(&pubResp, node, tStr, "base/respuesta") != RCL_RET_OK) return false;
  for (rcl_publisher_t *p : {&pubOdom, &pubBumpers, &pubGps, &pubBateria, &pubEstado, &pubResp})
    if (!EnlaceMicroRos::timeoutPublicador(p, PUB_TIMEOUT_MS)) return false;

  if (rclc_subscription_init_default(&subCmdVel, node, ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist), "cmd_vel") != RCL_RET_OK) return false;
  if (rclc_subscription_init_default(&subComando, node, tStr, "base/comando") != RCL_RET_OK) return false;
  if (rclc_timer_init_default2(&timer, support, RCL_MS_TO_NS(PERIODO_MS), alTimer, true) != RCL_RET_OK) return false;

  if (rclc_executor_add_subscription(ex, &subCmdVel, &cmdVelIn, alRecibirCmdVel, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(ex, &subComando, &comandoIn, alRecibirComando, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_timer(ex, &timer) != RCL_RET_OK) return false;
  return true;
}

void destruir(rcl_node_t *node) {
  ignorar(rcl_timer_fini(&timer));
  ignorar(rcl_subscription_fini(&subCmdVel, node));
  ignorar(rcl_subscription_fini(&subComando, node));
  for (rcl_publisher_t *p : {&pubOdom, &pubImu, &pubRango[0], &pubRango[1], &pubRango[2], &pubBumpers, &pubGps,
                             &pubBateria, &pubEstado, &pubResp})
    ignorar(rcl_publisher_fini(p, node));
}

}  // namespace

void rosBegin() {
  out = &salida;
  prepararMensajes();
  enlace.begin(Serial, "base", N_HANDLES, crear, destruir);
}

void rosLoop() {
  static bool wdFijado = false;
  if (!wdFijado) {  // la primera vez, con hwOk ya resuelto en setup()
    char wd[sizeof(WD_ROS)];
    memcpy(wd, WD_ROS, sizeof(WD_ROS));
    ejecutar(wd);
    wdFijado = true;
  }
  static bool estabaConectado = false;
  enlace.loop();
  if (enlace.seCorto()) {
    char s[] = "s";
    ejecutar(s);  // sin agente, la base se detiene (además, el watchdog de /cmd_vel ya la frena a los 300 ms)
    armado = false;
    out->println(">> Se perdió el micro-ROS Agent: base detenida y desarmada.");
  }
  if (enlace.conectado() && !estabaConectado) {
    armado = false;  // cada sesión empieza desarmada
    out->println(">> Conectado al agente. Base DESARMADA: enviar 'armar' por /base/comando.");
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
