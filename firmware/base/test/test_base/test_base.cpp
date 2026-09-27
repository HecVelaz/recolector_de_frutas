// Pruebas de la lógica de la base en la PC (sin placa): pio test -e native
#include <math.h>
#include <unity.h>

#include "ControlArticulacion.h"
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

static EntradasSeguridad tranquilo() { return {{false, false, false, false}, NAN, false, 0, 0, 0, 12.5f}; }

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

void test_bumper_delantero_deja_retroceder_y_girar() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.bumper[1] = true;
  float v = 0.1f, w = 0.5f;
  TEST_ASSERT_TRUE(s.filtrar(in, v, w));
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  TEST_ASSERT_EQUAL_FLOAT(0.5f, w);
  v = -0.1f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(-0.1f, v);
}

void test_bumper_trasero_no_deja_retroceder() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  in.bumper[3] = true;
  float v = -0.1f, w = 0;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
}

void test_obstaculo_al_frente() {
  SeguridadBase s(CFG_SEG);
  EntradasSeguridad in = tranquilo();
  float v, w = 0;
  in.distFrente = 0.15f;  // más cerca que la distancia de parada
  v = 0.2f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, v);
  in.distFrente = 0.35f;  // a mitad de camino entre 0,20 y 0,50: la mitad de la velocidad
  v = 0.2f;
  s.filtrar(in, v, w);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.1f, v);
  v = -0.2f;  // retroceder con un obstáculo adelante: libre
  in.distFrente = 0.10f;
  s.filtrar(in, v, w);
  TEST_ASSERT_EQUAL_FLOAT(-0.2f, v);
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
  in.bateria = 10.5f;
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
  RUN_TEST(test_bumper_delantero_deja_retroceder_y_girar);
  RUN_TEST(test_bumper_trasero_no_deja_retroceder);
  RUN_TEST(test_obstaculo_al_frente);
  RUN_TEST(test_watchdog_de_comandos);
  RUN_TEST(test_bateria_baja_avisa_sin_frenar);
  RUN_TEST(test_rueda_sigue_la_consigna);
  return UNITY_END();
}
