// Pruebas de la lógica de la base en la PC (sin placa): pio test -e native
#include <math.h>
#include <unity.h>

#include "ControlArticulacion.h"
#include "Desenvolver.h"
#include "Diferencial.h"
#include "SeguridadBase.h"
#include "base_config.h"

static const float PI_F = 3.14159265f;

// ---------------------------------------------------------------- cinemática

void test_recto_mismas_rpm() {
  Diferencial d(CFG_DIF);
  const Ruedas r = d.ruedasDesde(0.2f, 0.0f);
  const float esperado = 0.2f / (2 * PI_F * CFG_DIF.radioRueda) * 60.0f;  // 38,2 rpm
  TEST_ASSERT_FLOAT_WITHIN(0.01f, esperado, r.izq);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, esperado, r.der);
}

void test_giro_en_el_lugar() {
  Diferencial d(CFG_DIF);
  const Ruedas r = d.ruedasDesde(0.0f, 1.0f);  // antihorario: izquierda atrás, derecha adelante
  TEST_ASSERT_TRUE(r.izq < 0 && r.der > 0);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, -r.izq, r.der);
}

void test_saturacion_conserva_curvatura() {
  Diferencial d(CFG_DIF);
  const Ruedas r = d.ruedasDesde(0.25f, 1.0f);
  TEST_ASSERT_TRUE(fmaxf(fabsf(r.izq), fabsf(r.der)) <= CFG_DIF.rpmMax + 1e-3f);
  float v, w;
  d.cmdDesde(r, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 1.0f / 0.25f, w / v);  // mismo radio de giro que lo pedido
}

void test_ida_y_vuelta_cmd_ruedas() {
  Diferencial d(CFG_DIF);
  float v, w;
  d.cmdDesde(d.ruedasDesde(0.1f, -0.4f), v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.1f, v);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -0.4f, w);
}

void test_rampa_limita_aceleracion() {
  Diferencial d(CFG_DIF);
  float v = 0, w = 0;
  d.rampa(0.2f, 0.0f, 0.1f, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, CFG_DIF.accLin * 0.1f, v);  // 0,03 m/s en 0,1 s
  for (int n = 0; n < 100; n++) d.rampa(0.2f, 0.0f, 0.1f, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.2f, v);
}

// ---------------------------------------------------------------- odometría

void test_odometria_recta() {
  Odometria o(CFG_DIF.trocha);
  for (int n = 0; n < 100; n++) o.actualizar(0.01f, 0.01f, 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, o.x());
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, o.y());
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 1.0f, o.v());
}

void test_odometria_giro_90() {
  Odometria o(CFG_DIF.trocha);
  const float arco = PI_F / 2 * CFG_DIF.trocha / 2;  // cada rueda recorre esto para girar 90° en el lugar
  for (int n = 0; n < 100; n++) o.actualizar(-arco / 100, arco / 100, 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, PI_F / 2, o.theta());
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, o.x());
}

void test_odometria_circulo_completo_vuelve() {
  Odometria o(CFG_DIF.trocha);
  // Radio 1 m: rueda interna (izq) y externa (der) con la proporción de la trocha
  const float R = 1.0f, pasos = 2000;
  const float dth = 2 * PI_F / pasos;
  for (int n = 0; n < pasos; n++) o.actualizar((R - CFG_DIF.trocha / 2) * dth, (R + CFG_DIF.trocha / 2) * dth, 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 0.0f, o.x());
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 0.0f, o.y());
}

// ---------------------------------------------------------------- seguridad

// Todo en orden: nada al frente (INFINITY = eco largo), IMU con datos, batería cargada
static EntradasSeguridad tranquilo() { return {{false, false, false}, INFINITY, false, 0, 0, 0, 40.0f, true}; }  // 10S cargada

void test_seta_enclava_hasta_rearmar() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.seta = true;
  float v = 0.2f, w = 0.5f;
  TEST_ASSERT_FALSE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::Emergencia, s.estado());
  TEST_ASSERT_TRUE(s.deshabilitar());
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  in.seta = false;  // soltar la seta no alcanza
  v = 0.2f;
  TEST_ASSERT_FALSE(s.filtrar(in, v, w));
  in.seta = true;
  TEST_ASSERT_FALSE(s.rearmar(in));  // con la seta apretada no rearma
  in.seta = false;
  TEST_ASSERT_TRUE(s.rearmar(in));
  v = 0.2f;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL_FLOAT(0.2f, v);
}

void test_vuelco_enclava() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.roll = 40.0f;
  float v = 0.1f, w = 0;
  TEST_ASSERT_FALSE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::Vuelco, s.estado());
  TEST_ASSERT_FALSE(s.deshabilitar());  // vuelco: frena, pero no corta los puentes
  TEST_ASSERT_FALSE(s.rearmar(in));
  in.roll = 2.0f;
  TEST_ASSERT_TRUE(s.rearmar(in));
}

void test_bumper_delantero_solo_deja_retroceder_recto() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.bumper[0] = true;
  float v = 0.1f, w = 0.5f;  // avanzar girando: una rueda seguiría empujando contra el objeto
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, w);
  v = -0.1f;
  w = 0.5f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(-0.1f, v);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, w);
}

void test_bumper_lateral_no_deja_girar() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.bumper[2] = true;  // derecho
  float v = 0.1f, w = -0.5f;  // girando: el costado barrería contra el objeto
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL_FLOAT(0.1f, v);  // alejarse recto, hacia adelante o atrás, sí
  TEST_ASSERT_EQUAL_FLOAT(0.0f, w);
  TEST_ASSERT_FALSE(s.bloqueaAdelante());
}

void test_obstaculo_al_frente() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  float v, w = 0;
  in.distFrente = 0.15f;  // más cerca que la distancia de parada
  v = 0.2f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  in.distFrente = 0.35f;  // a mitad de camino entre 0,20 y 0,50: tope = la mitad de vMax
  v = 0.2f;
  s.filtrar(in, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, CFG_SEG.vMax / 2, v);
  v = 0.05f;  // por debajo del tope: no se toca
  s.filtrar(in, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.05f, v);
  v = -0.2f;  // retroceder con un obstáculo adelante: libre
  in.distFrente = 0.10f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(-0.2f, v);
}

void test_tope_por_cercania_no_se_acumula_con_la_rampa() {
  // Como en la tarea: rampa -> seguridad -> fijarRampa, muchos pasos a 0,35 m del obstáculo
  SeguridadBase s(CFG_SEG);
  Diferencial d(CFG_DIF);
  EntradasSeguridad in = tranquilo();
  in.distFrente = 0.35f;
  float v = 0, w = 0;
  for (int n = 0; n < 300; n++) {
    d.rampa(0.2f, 0.0f, TS, v, w);
    s.filtrar(in, v, w);
    d.fijarRampa(v, w);
  }
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, CFG_SEG.vMax / 2, v);  // llega al tope, no a ~0
}

void test_frente_sin_eco_no_deja_avanzar() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.distFrente = NAN;  // sensor desconectado o todavía sin medir
  float v = 0.1f, w = 0.3f;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  TEST_ASSERT_TRUE(s.frenteSinDato());
  TEST_ASSERT_EQUAL_FLOAT(0.3f, w);  // girar en el lugar sí
  v = -0.1f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(-0.1f, v);
}

void test_sin_imu_no_se_mueve() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.imuValida = false;
  float v = 0.1f, w = 0.3f;
  TEST_ASSERT_FALSE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::SinImu, s.estado());
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, w);
  TEST_ASSERT_FALSE(s.rearmar(in));
  in.imuValida = true;  // vuelven los datos: sigue sola
  v = 0.1f;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::Ok, s.estado());
}

void test_watchdog_de_comandos() {
  SeguridadBase s(CFG_SEG);
  s.fijarWatchdog(300);
  EntradasSeguridad in = tranquilo();
  in.msSinCmd = 500;
  float v = 0.1f, w = 0;
  TEST_ASSERT_FALSE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::SinComandos, s.estado());
  in.msSinCmd = 10;  // llega un comando: sigue sola, sin rearmar
  v = 0.1f;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL(SeguridadBase::Estado::Ok, s.estado());
}

void test_bateria_baja_avisa_sin_frenar() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.bateria = 31.0f;  // 10S: 3,1 V por celda
  float v = 0.1f, w = 0;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_TRUE(s.bateriaBaja());
  TEST_ASSERT_EQUAL_FLOAT(0.1f, v);
}

// ---------------------------------------------------------------- control de una rueda

// Motor simulado: primer orden + zona muerta, con el modelo estimado de CFG_RUEDA
struct MotorSim {
  float w = 0;
  double cuentas = 0;
  void paso(float u, float dt) {
    const float zm = CFG_RUEDA.u0 + 2.0f;
    const float uEf = fabsf(u) > zm ? (fabsf(u) - zm) * (u > 0 ? 1.0f : -1.0f) : 0.0f;
    w += dt / CFG_RUEDA.tau * (CFG_RUEDA.K * uEf - w);
    cuentas += w / 60.0f * CFG_RUEDA.cuentasPorVuelta * dt;
  }
};

void test_rueda_sigue_la_consigna() {
  ControlArticulacion k;
  k.configurar(CFG_RUEDA);
  MotorSim m;
  TEST_ASSERT_TRUE(k.velocidad(30.0f));
  for (int n = 0; n < 150; n++) m.paso(k.paso((int64_t)llround(m.cuentas), TS), TS);
  TEST_ASSERT_FLOAT_WITHIN(1.5f, 30.0f, k.w());
  TEST_ASSERT_EQUAL(ControlArticulacion::Falla::Ninguna, k.falla());
}

void setUp() {}
void tearDown() {}

// EncoderPCNT: el contador de hardware vuelve a 0 en ±32000; el acumulado no tiene que saltar
void test_encoder_pasa_el_limite_sin_saltos() {
  TEST_ASSERT_EQUAL_INT32(5, desenvolverPcnt(5));
  TEST_ASSERT_EQUAL_INT32(-7, desenvolverPcnt(-7));
  TEST_ASSERT_EQUAL_INT32(12, desenvolverPcnt(3 - 31991));    // 31991 -> 32000 = 0 -> 3: avanzó 12
  TEST_ASSERT_EQUAL_INT32(-12, desenvolverPcnt(-3 + 31991));  // lo mismo hacia atrás
  TEST_ASSERT_EQUAL_INT32(-15999, desenvolverPcnt(-31999 - 16000 + 32000));
  // Fronteras de la ambigüedad: hasta 15999 en cada sentido es exacto; 16000 ya se lee como -16000
  TEST_ASSERT_EQUAL_INT32(15999, desenvolverPcnt(15999));
  TEST_ASSERT_EQUAL_INT32(-15999, desenvolverPcnt(-15999));
  TEST_ASSERT_EQUAL_INT32(-16000, desenvolverPcnt(16000));
  TEST_ASSERT_EQUAL_INT32(-16000, desenvolverPcnt(-16000));
  TEST_ASSERT_EQUAL_INT32(-15999, desenvolverPcnt(16001));
  TEST_ASSERT_EQUAL_INT32(1, desenvolverPcnt(0 - 31999));   // 31999 -> 32000 = 0
  TEST_ASSERT_EQUAL_INT32(-1, desenvolverPcnt(0 + 31999));  // -31999 -> -32000 = 0
  TEST_ASSERT_EQUAL_INT32(-2, desenvolverPcnt(31999 - 1));  // vuelve atrás justo después de la vuelta a 0
  TEST_ASSERT_EQUAL_INT32(15000, desenvolverPcnt(31000 + 15000 - 32000 - 31000));  // de 31000 a 14000 pasando por 0
  // Simulación: 5 vueltas del contador en cada sentido, leyendo cada 110 cuentas (J2 a 160 rpm cada 10 ms)
  int64_t real = 0, acc = 0;
  int32_t hw = 0, ultimo = 0;
  for (int k = 0; k < 6000; k++) {
    const int32_t paso = k < 3000 ? 110 : -110;
    real += paso;
    hw += paso;
    if (hw >= 32000 || hw <= -32000) hw %= 32000;  // el PCNT vuelve a 0 al llegar al límite
    acc += desenvolverPcnt(hw - ultimo);
    ultimo = hw;
    TEST_ASSERT_EQUAL_INT64(real, acc);
  }
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_recto_mismas_rpm);
  RUN_TEST(test_giro_en_el_lugar);
  RUN_TEST(test_saturacion_conserva_curvatura);
  RUN_TEST(test_ida_y_vuelta_cmd_ruedas);
  RUN_TEST(test_rampa_limita_aceleracion);
  RUN_TEST(test_odometria_recta);
  RUN_TEST(test_odometria_giro_90);
  RUN_TEST(test_odometria_circulo_completo_vuelve);
  RUN_TEST(test_seta_enclava_hasta_rearmar);
  RUN_TEST(test_vuelco_enclava);
  RUN_TEST(test_bumper_delantero_solo_deja_retroceder_recto);
  RUN_TEST(test_bumper_lateral_no_deja_girar);
  RUN_TEST(test_obstaculo_al_frente);
  RUN_TEST(test_tope_por_cercania_no_se_acumula_con_la_rampa);
  RUN_TEST(test_frente_sin_eco_no_deja_avanzar);
  RUN_TEST(test_sin_imu_no_se_mueve);
  RUN_TEST(test_watchdog_de_comandos);
  RUN_TEST(test_bateria_baja_avisa_sin_frenar);
  RUN_TEST(test_rueda_sigue_la_consigna);
  RUN_TEST(test_encoder_pasa_el_limite_sin_saltos);
  return UNITY_END();
}
