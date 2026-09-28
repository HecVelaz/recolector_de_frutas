// Firmware de la base (ESP32-S3): tracción diferencial en lazo cerrado, odometría, sensores (IMU, GPS,
// 3 HC-SR04, 4 bumpers, batería) y seguridad local (seta, vuelco, contacto, distancia al frente, watchdog).
//
// Esqueleto, primera versión: comandos por el monitor serial (115200). Más adelante la misma lógica se
// comandará por micro-ROS (/cmd_vel -> /odom, /imu/data_raw, /range/*, /bumpers, /battery), cambiando solo
// la capa de comandos.
//
// Estructura:
//   - tareaControl (núcleo 0, cada 10 ms): encoders, bumpers, seta, IMU, HC-SR04, seguridad, control de las
//     ruedas, odometría. No usa Serial. La seguridad se decide acá, sin esperar a nadie.
//   - loop (núcleo 1): comandos, GPS, batería, mensajes y CSV.
// El estado compartido se toca dentro de la sección crítica; las marcas de tiempo se toman adentro.
#include <Arduino.h>
#include <Wire.h>

#include "BTS7960.h"
#include "ControlArticulacion.h"
#include "Diferencial.h"
#include "EncoderPCNT.h"
#include "HCSR04.h"
#include "MPU9250.h"
#include "SeguridadBase.h"
#include "UP501.h"
#include "base_config.h"
#include "esp_task_wdt.h"
#include "pins.h"

#ifdef USAR_MICROROS
#include "capa_ros.h"
#endif

// Canales LEDC: de a pares comparten timer (misma frecuencia)
constexpr uint8_t CH_IZQ_R = 0, CH_IZQ_L = 1;
constexpr uint8_t CH_DER_R = 2, CH_DER_L = 3;

constexpr float DOS_PI = 6.28318530718f;
const char *const LADO[2] = {"izq", "der"};

BTS7960 motor[2];
EncoderPCNT enc[2];
ControlArticulacion rueda[2];
HCSR04 ultrasonido;
MPU9250 imu(Wire);
UP501 gps(Serial1);
SemaphoreHandle_t i2c;  // la tarea lee la IMU y el loop la calibra: no a la vez
bool hwOk = false, imuOk = false;
// Toda la salida de texto pasa por acá: en modo serial es el monitor; con micro-ROS, un búfer que se publica
// en /base/respuesta (el USB lo usa el agente)
Print *out = &Serial;

// ---- Estado compartido (sección crítica) ----
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
Diferencial dif(CFG_DIF);
Odometria odo(CFG_DIF.trocha);
SeguridadBase seg(CFG_SEG);

enum class Modo : uint8_t { Parado, Libre, Cmd, Ruedas, Duty };
Modo modo = Modo::Libre;  // al arrancar, puentes deshabilitados
float vObj = 0, wObj = 0;          // Cmd
Ruedas rpmObj{0, 0};               // Ruedas
float dutyObj[2] = {0, 0};         // Duty
uint32_t cortarEnMs = 0;           // fin de v / w / d (0 = sin corte)
uint32_t ultimoCmdMs = 0;
uint32_t ticksAtrasados = 0;

struct Sensores {
  bool bumper[4];
  bool seta;
  float dist[3];     // frente, izq, der [m]
  float roll, pitch; // grados
  MPU9250::Vec3 acc, gyro;
  float bateria;     // V
  bool imuValida;    // muestra de la IMU de hace menos de IMU_VALIDA_MS
};
Sensores sens = {{false, false, false, false}, false, {NAN, NAN, NAN}, 0, 0, {0, 0, 0}, {0, 0, 0}, NAN, false};
float vAct = 0, wAct = 0;  // comando después de rampa y seguridad

// CSV del comando log
struct Muestra {
  uint32_t tMs;
  float vRef, wRef, rpmRef[2], rpm[2], u[2], x, y, th;
};
QueueHandle_t colaLog;
bool logOn = false;
uint32_t logCadaTicks = 5;

// ---------------------------------------------------------------- hardware

int64_t cuentas(int i) {
  const int64_t c = enc[i].count();
  return ENC_INVERTIDO[i] ? -c : c;
}

// Los dos IBT-2 comparten el EN: siempre se habilitan o se liberan juntos
void aplicarMotores(const float u[2], bool libre) {
  if (libre) {
    motor[0].coast();
    motor[1].coast();
    return;
  }
  for (int i = 0; i < 2; i++) motor[i].setDuty((MOTOR_INVERTIDO[i] ? -u[i] : u[i]) / 100.0f);
}

const int PIN_BUMPER[4] = {PIN_BUMPER_FRENTE_IZQ, PIN_BUMPER_FRENTE_DER, PIN_BUMPER_ATRAS_IZQ, PIN_BUMPER_ATRAS_DER};

// ---------------------------------------------------------------- tarea de control

void tareaControl(void *) {
  esp_task_wdt_add(nullptr);
  TickType_t ultimo = xTaskGetTickCount();
  const TickType_t periodo = pdMS_TO_TICKS((uint32_t)(TS * 1000));
  int64_t tPrevUs = esp_timer_get_time();
  int64_t cPrev[2] = {cuentas(0), cuentas(1)};
  float roll = 0, pitch = 0;
  bool hayImu = false;       // ya hubo al menos una muestra válida
  uint32_t imuUltimaMs = 0;  // millis() de la última muestra válida
  uint32_t tick = 0;
  for (;;) {
    const bool atrasado = xTaskGetTickCount() - ultimo >= periodo;
    vTaskDelayUntil(&ultimo, periodo);
    esp_task_wdt_reset();
    tick++;

    const int64_t tUs = esp_timer_get_time();
    float dt = (tUs - tPrevUs) * 1e-6f;
    tPrevUs = tUs;
    if (dt < 0.5f * TS) dt = 0.5f * TS;
    if (dt > 5.0f * TS) dt = 5.0f * TS;

    // Sensores (fuera de la sección crítica: I2C y GPIO)
    int64_t c[2] = {cuentas(0), cuentas(1)};
    bool bump[4];
    for (int k = 0; k < 4; k++) bump[k] = digitalRead(PIN_BUMPER[k]) == LOW;
    const bool seta = digitalRead(PIN_SETA) == HIGH;  // contacto NC: HIGH = apretada o cable cortado
    MPU9250::Vec3 acc{0, 0, 0}, gyro{0, 0, 0};
    bool imuNueva = false;
    if (imuOk && tick % IMU_CADA == 0 && xSemaphoreTake(i2c, 0) == pdTRUE) {
      float temp;
      imuNueva = imu.readAccelGyro(acc, gyro, temp);
      xSemaphoreGive(i2c);
      if (imuNueva) {
        const float r = atan2f(acc.y, acc.z) * 57.2958f;
        const float p = atan2f(-acc.x, sqrtf(acc.y * acc.y + acc.z * acc.z)) * 57.2958f;
        // La primera muestra fija el filtro (si no, arrancaría desde 0° y tardaría en ver una base ya inclinada)
        roll = hayImu ? roll + IMU_FILTRO * (r - roll) : r;
        pitch = hayImu ? pitch + IMU_FILTRO * (p - pitch) : p;
        hayImu = true;
        imuUltimaMs = millis();
      }
    }
    if (tick % US_CADA == 0) ultrasonido.disparar();

    float u[2];
    bool libre;
    Muestra m{};
    bool hayMuestra = false;

    portENTER_CRITICAL(&mux);
    const uint32_t ahora = millis();
    if (atrasado) ticksAtrasados++;
    for (int k = 0; k < 4; k++) sens.bumper[k] = bump[k];
    sens.seta = seta;
    for (int k = 0; k < 3; k++) sens.dist[k] = ultrasonido.distancia(k);
    sens.roll = roll;
    sens.pitch = pitch;
    sens.imuValida = hayImu && ahora - imuUltimaMs < IMU_VALIDA_MS;
    if (imuNueva) {
      sens.acc = acc;
      sens.gyro = gyro;
    }

    // Fin de v / w / d
    if (cortarEnMs && (int32_t)(ahora - cortarEnMs) >= 0) {
      cortarEnMs = 0;
      if (modo != Modo::Libre) modo = Modo::Parado;
    }

    // Comando pedido -> (v, w) con rampa (en Ruedas y Duty se estima para que la seguridad lo pueda recortar).
    // Parado o libre: la rampa vuelve a cero en el acto, para que el próximo comando no herede el anterior.
    float v = 0, w = 0;
    switch (modo) {
      case Modo::Cmd: dif.rampa(vObj, wObj, dt, v, w); break;
      case Modo::Ruedas: dif.cmdDesde(rpmObj, v, w); break;
      case Modo::Duty: dif.cmdDesde({dutyObj[0] * CFG_RUEDA.K, dutyObj[1] * CFG_RUEDA.K}, v, w); break;
      default: dif.reiniciarRampa(); break;
    }
    const float vPedida = v, wPedida = w;
    const EntradasSeguridad in = {{bump[0], bump[1], bump[2], bump[3]}, sens.dist[0], seta, roll, pitch,
                                  ahora - ultimoCmdMs, sens.bateria, sens.imuValida};
    const bool puede = seg.filtrar(in, v, w);
    if (modo == Modo::Cmd) dif.fijarRampa(v, w);
    // Vencido el watchdog, el comando viejo se anula: no vuelve solo cuando llega otro mensaje
    if (seg.estado() == SeguridadBase::Estado::SinComandos && modo != Modo::Libre) {
      modo = Modo::Parado;
      cortarEnMs = 0;
    }

    // Una rueda con falla (atasco, encoder) detiene la base entera
    const bool falla = rueda[0].falla() != ControlArticulacion::Falla::Ninguna ||
                       rueda[1].falla() != ControlArticulacion::Falla::Ninguna;
    if (falla && modo != Modo::Libre) modo = Modo::Parado;

    if (!puede || falla || modo == Modo::Parado || modo == Modo::Libre) {
      rueda[0].liberar();
      rueda[1].liberar();
      v = w = 0.0f;
    } else if (modo == Modo::Duty) {
      // Lazo abierto: con cualquier recorte de la seguridad (contacto, obstáculo, tope por cercanía) se corta
      const bool recortado = v != vPedida || w != wPedida;
      for (int i = 0; i < 2; i++) rueda[i].duty(recortado ? 0.0f : dutyObj[i]);
    } else {
      const Ruedas r = dif.ruedasDesde(v, w);
      rueda[0].velocidad(r.izq);
      rueda[1].velocidad(r.der);
    }
    vAct = v;
    wAct = w;

    for (int i = 0; i < 2; i++) u[i] = rueda[i].paso(c[i], dt);
    // Si una rueda entró en falla en este mismo paso, la otra también se frena ya (no un ciclo después)
    if (rueda[0].falla() != ControlArticulacion::Falla::Ninguna || rueda[1].falla() != ControlArticulacion::Falla::Ninguna)
      u[0] = u[1] = 0.0f;
    libre = seg.deshabilitar() || modo == Modo::Libre;

    // Odometría con las cuentas aceptadas por el control (descarta los saltos del encoder)
    const float mPorCuenta = DOS_PI * CFG_DIF.radioRueda / CFG_RUEDA.cuentasPorVuelta;
    float d[2];
    for (int i = 0; i < 2; i++) {
      const int64_t dc = c[i] - cPrev[i];
      const bool salto = fabsf((float)dc) > 3.0f * CFG_RUEDA.rpmMax / 60.0f * CFG_RUEDA.cuentasPorVuelta * dt + 2.0f;
      d[i] = salto ? 0.0f : dc * mPorCuenta;
      cPrev[i] = c[i];
    }
    odo.actualizar(d[0], d[1], dt);

    if (logOn && tick % logCadaTicks == 0) {
      m = {ahora, v, w, {rueda[0].wRef(), rueda[1].wRef()}, {rueda[0].w(), rueda[1].w()}, {u[0], u[1]},
           odo.x(), odo.y(), odo.theta()};
      hayMuestra = true;
    }
    portEXIT_CRITICAL(&mux);

    aplicarMotores(u, libre);
    if (hayMuestra) xQueueSend(colaLog, &m, 0);
  }
}

// ---------------------------------------------------------------- comandos

void ayuda() {
  out->println();
  out->println("Comandos (v en m/s, w en rad/s; + = adelante / giro a la izquierda):");
  out->println("  e                estado: modo, seguridad, odometría y ruedas");
  out->println("  sens             sensores: IMU, GPS, distancias, bumpers, seta, batería");
  out->printf("  v <v> <w> [s]    mover con rampa por s segundos (def %.0f, máx %.0f). Ej: v 0.1 0\n", CMD_S_DEF, CMD_S_MAX);
  out->println("  w <izq> <der> [s] rpm de cada rueda (lazo de velocidad solo). Ej: w 20 20");
  out->printf("  d <izq> <der>    lazo abierto en %% (máx %.0f); se corta a los %lu ms si no se repite\n", JOG_DUTY_MAX,
                (unsigned long)JOG_MS);
  out->println("  s                detener (freno)");
  out->println("  l                liberar: puentes deshabilitados (rueda libre)");
  out->println("  r                rearmar tras seta o vuelco (con la causa despejada) y borrar fallas");
  out->println("  cal              calibrar el giroscopio (robot quieto, 2 s)");
  out->println("  odo0             odometría a cero");
  out->println("  log [hz]         CSV (t_ms,v,w,rpm_ref_izq,rpm_izq,rpm_ref_der,rpm_der,u_izq,u_der,x,y,th); log 0 apaga");
  out->println("  wd <ms>          watchdog de comandos (0 = apagado; con la Pi, 300)");
  out->println("  ?                esta ayuda");
  out->println("Un comando nuevo reemplaza al anterior. La seguridad recorta cualquier comando.");
  out->println();
}

const char *textoModo(Modo m) {
  switch (m) {
    case Modo::Parado: return "parado";
    case Modo::Cmd: return "v/w";
    case Modo::Ruedas: return "ruedas";
    case Modo::Duty: return "duty";
    default: return "libre";
  }
}

void estado() {
  ControlArticulacion r[2];
  Modo mo;
  SeguridadBase::Estado es;
  bool bAd, bAt, batBaja, sinFrente;
  float x, y, th, vo, wo, va, wa;
  uint32_t atr, wd;
  portENTER_CRITICAL(&mux);
  r[0] = rueda[0];
  r[1] = rueda[1];
  mo = modo;
  es = seg.estado();
  bAd = seg.bloqueaAdelante();
  bAt = seg.bloqueaAtras();
  batBaja = seg.bateriaBaja();
  sinFrente = seg.frenteSinDato();
  x = odo.x(); y = odo.y(); th = odo.theta(); vo = odo.v(); wo = odo.w();
  va = vAct; wa = wAct;
  atr = ticksAtrasados;
  wd = seg.watchdog();
  portEXIT_CRITICAL(&mux);
  out->printf("Modo: %s | seguridad: %s%s%s%s%s\n", textoModo(mo), SeguridadBase::texto(es), bAd ? " | no avanza" : "",
                sinFrente ? " (ultrasonido del frente sin eco)" : "", bAt ? " | no retrocede" : "",
                batBaja ? " | BATERÍA BAJA" : "");
  out->printf("Comando: v=%.3f m/s w=%.3f rad/s | odometría: x=%.3f y=%.3f th=%.1f° v=%.3f w=%.3f\n", va, wa, x, y,
                th * 57.2958f, vo, wo);
  for (int i = 0; i < 2; i++)
    out->printf("Rueda %s: ref=%6.1f rpm w=%6.1f rpm u=%6.1f %% vueltas=%.3f | falla: %s | saltos enc: %lu\n", LADO[i],
                  r[i].wRef(), r[i].w(), r[i].u(), r[i].q() / 360.0f, r[i].textoFalla(),
                  (unsigned long)r[i].saltosEncoder());
  out->printf("Ticks atrasados: %lu | watchdog: %lu ms\n", (unsigned long)atr, (unsigned long)wd);
}

void sensores() {
  Sensores s;
  portENTER_CRITICAL(&mux);
  s = sens;
  portEXIT_CRITICAL(&mux);
  if (imuOk && !s.imuValida) out->println("IMU: sin muestras recientes (la base no se mueve)");
  if (imuOk)
    out->printf("IMU: acc=(%.2f, %.2f, %.2f) g gyro=(%.1f, %.1f, %.1f) °/s | roll=%.1f° pitch=%.1f°\n", s.acc.x, s.acc.y,
                  s.acc.z, s.gyro.x, s.gyro.y, s.gyro.z, s.roll, s.pitch);
  else
    out->println("IMU: sin responder (revisar SDA 8 / SCL 9)");
  UP501::Fix f;
  if (gps.readFix(f))
    out->printf("GPS: fix lat=%.6f lon=%.6f sats=%u hdop=%.1f\n", f.latDeg, f.lonDeg, f.satsUsed, f.hdop);
  else
    out->printf("GPS: %s | sats en vista: %d\n", UP501::stateName(gps.state()), gps.satellitesInView());
  out->print("Distancias [m]:");
  const char *nom[3] = {"frente", "izq", "der"};
  for (int k = 0; k < 3; k++) {
    if (isfinite(s.dist[k])) out->printf(" %s=%.2f", nom[k], s.dist[k]);
    else if (isinf(s.dist[k])) out->printf(" %s=libre", nom[k]);
    else out->printf(" %s=SIN ECO", nom[k]);
  }
  out->printf("\nBumpers: FI=%d FD=%d AI=%d AD=%d | seta: %s | batería: ", s.bumper[0], s.bumper[1], s.bumper[2],
                s.bumper[3], s.seta ? "APRETADA" : "suelta");
  if (isfinite(s.bateria)) out->printf("%.2f V\n", s.bateria);
  else out->println("--");
}

bool leerNum(const char *s, float &v) {
  if (!s) return false;
  char *fin = nullptr;
  v = strtof(s, &fin);
  return fin != s && *fin == '\0' && isfinite(v);
}

// Registra un comando aceptado (watchdog). Llamar dentro de la sección crítica.
void aceptado() { ultimoCmdMs = millis(); }

bool leerDuracion(const char *s, float &seg_) {
  seg_ = CMD_S_DEF;
  return !s || (leerNum(s, seg_) && seg_ > 0 && seg_ <= CMD_S_MAX);
}

void ejecutar(char *linea) {
  char *cmd = strtok(linea, " ");
  if (!cmd) return;
  char *a1 = strtok(nullptr, " ");
  char *a2 = strtok(nullptr, " ");
  char *a3 = strtok(nullptr, " ");
  float v1, v2, s;

  if (!strcmp(cmd, "?") || !strcmp(cmd, "h")) {
    ayuda();
  } else if (!strcmp(cmd, "e")) {
    estado();
  } else if (!strcmp(cmd, "sens")) {
    sensores();
  } else if (!hwOk) {
    // Con un error de hardware al arrancar no hay tarea de control: solo diagnóstico (también por micro-ROS)
    out->println(">> Hardware con error al arrancar: comandos deshabilitados (ver el mensaje de inicio y reiniciar).");
  } else if (!strcmp(cmd, "v") || !strcmp(cmd, "w")) {
    if (!leerNum(a1, v1) || !leerNum(a2, v2) || !leerDuracion(a3, s)) {
      out->printf(">> Uso: %s <%s> <%s> [segundos, hasta %.0f]\n", cmd, cmd[0] == 'v' ? "v m/s" : "rpm izq",
                    cmd[0] == 'v' ? "w rad/s" : "rpm der", CMD_S_MAX);
      return;
    }
    portENTER_CRITICAL(&mux);
    if (cmd[0] == 'v') {
      if (modo != Modo::Cmd) dif.fijarRampa(vAct, wAct);
      vObj = v1;
      wObj = v2;
      modo = Modo::Cmd;
    } else {
      rpmObj = {v1, v2};
      modo = Modo::Ruedas;
    }
    cortarEnMs = (millis() + (uint32_t)(s * 1000)) | 1;
    aceptado();
    portEXIT_CRITICAL(&mux);
  } else if (!strcmp(cmd, "d")) {
    if (!leerNum(a1, v1) || !leerNum(a2, v2)) {
      out->println(">> Uso: d <pct izq> <pct der>");
      return;
    }
    v1 = constrain(v1, -JOG_DUTY_MAX, JOG_DUTY_MAX);
    v2 = constrain(v2, -JOG_DUTY_MAX, JOG_DUTY_MAX);
    portENTER_CRITICAL(&mux);
    dutyObj[0] = v1;
    dutyObj[1] = v2;
    modo = Modo::Duty;
    cortarEnMs = (millis() + JOG_MS) | 1;
    aceptado();
    portEXIT_CRITICAL(&mux);
  } else if (!strcmp(cmd, "s") || !strcmp(cmd, "l")) {
    portENTER_CRITICAL(&mux);
    modo = cmd[0] == 'l' ? Modo::Libre : Modo::Parado;
    cortarEnMs = 0;
    aceptado();
    portEXIT_CRITICAL(&mux);
    out->println(cmd[0] == 'l' ? ">> Liberado (rueda libre)." : ">> Detenido.");
  } else if (!strcmp(cmd, "r")) {
    bool ok;
    portENTER_CRITICAL(&mux);
    const EntradasSeguridad in = {{sens.bumper[0], sens.bumper[1], sens.bumper[2], sens.bumper[3]}, sens.dist[0],
                                  sens.seta, sens.roll, sens.pitch, 0, sens.bateria, sens.imuValida};
    ok = seg.rearmar(in);
    if (ok) {
      rueda[0].borrarFalla();
      rueda[1].borrarFalla();
      modo = Modo::Parado;
      cortarEnMs = 0;
      aceptado();
    }
    portEXIT_CRITICAL(&mux);
    out->println(ok ? ">> Rearmado." : ">> No se puede rearmar: seta apretada, base no nivelada o IMU sin datos.");
  } else if (!strcmp(cmd, "cal")) {
    if (!imuOk) {
      out->println(">> IMU sin responder.");
      return;
    }
    portENTER_CRITICAL(&mux);
    const bool quieta = modo == Modo::Parado || modo == Modo::Libre;
    portEXIT_CRITICAL(&mux);
    // Durante los 2 s no se lee la IMU (y la seguridad frena por "IMU sin datos") ni se atienden comandos
    if (!quieta) {
      out->println(">> Detener la base (s) antes de calibrar.");
      return;
    }
    out->println(">> Calibrando el giroscopio: no mover el robot 2 s...");
    xSemaphoreTake(i2c, portMAX_DELAY);
    const MPU9250::CalStatus st = imu.calibrateGyro();
    xSemaphoreGive(i2c);
    const MPU9250::Vec3 b = imu.gyroBias();
    out->printf(">> Calibración: %s | bias = (%.2f, %.2f, %.2f) °/s\n", MPU9250::calStatusName(st), b.x, b.y, b.z);
  } else if (!strcmp(cmd, "odo0")) {
    portENTER_CRITICAL(&mux);
    odo.reiniciar();
    portEXIT_CRITICAL(&mux);
    out->println(">> Odometría en cero.");
  } else if (!strcmp(cmd, "log")) {
#ifdef USAR_MICROROS
    out->println(">> Con micro-ROS no hay log: usar los tópicos (ros2 bag record).");
    return;
#endif
    v1 = 20;
    if (a1 && (!leerNum(a1, v1) || v1 < 0 || v1 > 100)) {
      out->println(">> Uso: log [hz 1..100] (log 0 apaga)");
      return;
    }
    portENTER_CRITICAL(&mux);
    logOn = v1 > 0;
    if (logOn) logCadaTicks = (uint32_t)(100.0f / v1 + 0.5f);
    portEXIT_CRITICAL(&mux);
    if (v1 > 0) out->println("t_ms,v,w,rpm_ref_izq,rpm_izq,rpm_ref_der,rpm_der,u_izq,u_der,x,y,th");
  } else if (!strcmp(cmd, "wd")) {
    if (!leerNum(a1, v1) || v1 < 0 || v1 > 10000) {
      out->println(">> Uso: wd <ms> (0 = apagado, hasta 10000)");
      return;
    }
#ifdef USAR_MICROROS
    // Con micro-ROS el watchdog protege contra un /cmd_vel que deja de llegar: no se puede apagar ni alargar mucho
    if (v1 < 50 || v1 > 1000) {
      out->println(">> Con micro-ROS el watchdog va de 50 a 1000 ms (no se puede apagar).");
      return;
    }
#endif
    portENTER_CRITICAL(&mux);
    seg.fijarWatchdog((uint32_t)v1);  // no cuenta como comando de movimiento: no renueva uno vencido
    portEXIT_CRITICAL(&mux);
    out->printf(">> Watchdog: %.0f ms.\n", v1);
  } else {
    out->printf(">> Comando desconocido: %s (? para ayuda)\n", cmd);
  }
}

char linea[64];
size_t lineaLen = 0;
bool descartando = false;

void leerSerial() {
  while (Serial.available()) {
    const char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (descartando) out->println(">> Línea demasiado larga: descartada.");
      else if (lineaLen > 0 && hwOk) {
        linea[lineaLen] = '\0';
        ejecutar(linea);
      }
      lineaLen = 0;
      descartando = false;
    } else if (lineaLen < sizeof(linea) - 1) {
      linea[lineaLen++] = ch;
    } else {
      descartando = true;
    }
  }
}

// ---------------------------------------------------------------- funciones para la capa micro-ROS

#ifdef USAR_MICROROS
// /cmd_vel: como `v`, sin duración propia (lo corta el watchdog de comandos si deja de llegar)
void baseCmdVel(float v, float w) {
  if (!hwOk || !isfinite(v) || !isfinite(w)) return;
  portENTER_CRITICAL(&mux);
  if (modo != Modo::Cmd) dif.fijarRampa(vAct, wAct);
  vObj = v;
  wObj = w;
  modo = Modo::Cmd;
  cortarEnMs = (millis() + (uint32_t)(CMD_S_MAX * 1000)) | 1;
  aceptado();
  portEXIT_CRITICAL(&mux);
}

void baseLeer(EstadoBase &e) {
  portENTER_CRITICAL(&mux);
  e.x = odo.x();
  e.y = odo.y();
  e.th = odo.theta();
  e.v = odo.v();
  e.w = odo.w();
  e.acc[0] = sens.acc.x;
  e.acc[1] = sens.acc.y;
  e.acc[2] = sens.acc.z;
  e.gyro[0] = sens.gyro.x;
  e.gyro[1] = sens.gyro.y;
  e.gyro[2] = sens.gyro.z;
  e.imuValida = sens.imuValida;
  for (int k = 0; k < 3; k++) e.dist[k] = sens.dist[k];
  for (int k = 0; k < 4; k++) e.bumper[k] = sens.bumper[k];
  e.seta = sens.seta;
  e.bateria = sens.bateria;
  e.seg = seg.estado();
  e.bloqAdelante = seg.bloqueaAdelante();
  e.bloqAtras = seg.bloqueaAtras();
  e.frenteSinDato = seg.frenteSinDato();
  e.bateriaBaja = seg.bateriaBaja();
  for (int i = 0; i < 2; i++) {
    e.rpm[i] = rueda[i].w();
    e.u[i] = rueda[i].u();
    e.falla[i] = rueda[i].falla();
  }
  e.modo = textoModo(modo);
  portEXIT_CRITICAL(&mux);
}
#endif

// ---------------------------------------------------------------- setup / loop

void setup() {
  // Puentes primero y deshabilitados: hasta acá el EN flota (pull-down de 10 kΩ recomendado)
  bool okPwm = motor[0].begin(PIN_IZQ_RPWM, PIN_IZQ_LPWM, PIN_TRACCION_EN, PIN_TRACCION_EN, CH_IZQ_R, CH_IZQ_L, PWM_HZ, PWM_BITS);
  okPwm &= motor[1].begin(PIN_DER_RPWM, PIN_DER_LPWM, PIN_TRACCION_EN, PIN_TRACCION_EN, CH_DER_R, CH_DER_L, PWM_HZ, PWM_BITS);
  motor[0].coast();
  motor[1].coast();

  const bool okEnc = enc[0].begin(PIN_IZQ_ENC_A, PIN_IZQ_ENC_B, PCNT_UNIT_0) &&
                     enc[1].begin(PIN_DER_ENC_A, PIN_DER_ENC_B, PCNT_UNIT_1);

  for (int k = 0; k < 4; k++) pinMode(PIN_BUMPER[k], INPUT_PULLUP);
  pinMode(PIN_SETA, INPUT_PULLUP);
  const int ecos[3] = {PIN_US_ECHO_FRENTE, PIN_US_ECHO_IZQ, PIN_US_ECHO_DER};
  const bool okUs = ultrasonido.begin(PIN_US_TRIG, ecos, 3);

  for (int i = 0; i < 2; i++) rueda[i].configurar(CFG_RUEDA);

  Serial.begin(115200);
#ifdef USAR_MICROROS
  rosBegin();  // desde acá, out es el búfer que se publica en /base/respuesta
#else
  delay(1500);  // dar tiempo a que abra el monitor
#endif

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);
  const MPU9250::Status stImu = imu.begin(MPU9250::Dlpf::Hz20);
  imuOk = stImu == MPU9250::Status::Ok;
  Serial1.begin(UP501::DEFAULT_BAUD, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  analogSetPinAttenuation(PIN_BATERIA, ADC_11db);

  i2c = xSemaphoreCreateMutex();
  colaLog = xQueueCreate(32, sizeof(Muestra));
  hwOk = okPwm && okEnc && okUs && i2c && colaLog;

  out->println();
  out->println("== firmware/base: tracción diferencial (2 × IBT-2 + 36GP-555), IMU, GPS, HC-SR04, bumpers, seta ==");
  out->printf("Control a %.0f Hz en el núcleo 0. Base LIBERADA (puentes deshabilitados).\n", 1.0f / TS);
  if (!okPwm) out->println("ERROR: no se pudo configurar el PWM de los IBT-2.");
  if (!okEnc) out->println("ERROR: no se pudo configurar el PCNT de los encoders.");
  if (!okUs) out->println("ERROR: no se pudieron configurar los HC-SR04.");
  out->printf("IMU: %s (%s)\n", MPU9250::statusName(stImu), imu.modelName());
  if (!hwOk) {
    out->println("Comandos DESHABILITADOS hasta corregir el error y reiniciar.");
    return;
  }
  ayuda();

  ultimoCmdMs = millis();
  esp_task_wdt_init(TWDT_S, true);
  xTaskCreatePinnedToCore(tareaControl, "control", 6144, nullptr, configMAX_PRIORITIES - 2, nullptr, 0);
}

void loop() {
#ifdef USAR_MICROROS
  rosLoop();
#else
  leerSerial();
#endif
  gps.update();

  static uint32_t batMs = 0;
  if (millis() - batMs >= BATERIA_CADA_MS) {
    batMs = millis();
    const float v = analogReadMilliVolts(PIN_BATERIA) * 1e-3f * BATERIA_DIVISOR;
    portENTER_CRITICAL(&mux);
    sens.bateria = v;
    portEXIT_CRITICAL(&mux);
  }

  // Avisar cambios de seguridad y fallas de las ruedas
  static SeguridadBase::Estado previo = SeguridadBase::Estado::Ok;
  static ControlArticulacion::Falla fPrev[2] = {};
  portENTER_CRITICAL(&mux);
  const SeguridadBase::Estado es = seg.estado();
  const ControlArticulacion::Falla f[2] = {rueda[0].falla(), rueda[1].falla()};
  portEXIT_CRITICAL(&mux);
  if (es != previo) {
    out->printf(">> Seguridad: %s%s\n", SeguridadBase::texto(es),
                  (es == SeguridadBase::Estado::Emergencia || es == SeguridadBase::Estado::Vuelco) ? " (r para rearmar)" : "");
    previo = es;
  }
  for (int i = 0; i < 2; i++) {
    if (f[i] != fPrev[i] && f[i] != ControlArticulacion::Falla::Ninguna)
      out->printf(">> Rueda %s: FALLA %s. Base detenida; r para borrar.\n", LADO[i], ControlArticulacion::texto(f[i]));
    fPrev[i] = f[i];
  }

  Muestra m;
  while (colaLog && xQueueReceive(colaLog, &m, 0) == pdTRUE)
    out->printf("%lu,%.3f,%.3f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.3f,%.3f,%.3f\n", (unsigned long)m.tMs, m.vRef, m.wRef,
                  m.rpmRef[0], m.rpm[0], m.rpmRef[1], m.rpm[1], m.u[0], m.u[1], m.x, m.y, m.th);

  delay(1);
}
