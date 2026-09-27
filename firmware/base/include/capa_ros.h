#pragma once

// Capa micro-ROS de la base (solo con -DUSAR_MICROROS, entorno `ros` de platformio.ini).
//
// Publica   /odom                nav_msgs/Odometry        odom -> base_link, pose y velocidad              25 Hz
//           /imu/data_raw        sensor_msgs/Imu          acelerómetro [m/s²] y giroscopio [rad/s], sin orientación  50 Hz
//           /range/frente, /range/izq, /range/der  sensor_msgs/Range  +Inf = nada al alcance, NaN = sin eco  10 Hz
//           /bumpers             std_msgs/UInt8           bits 0..3 = frente-izq, frente-der, atrás-izq, atrás-der  10 Hz
//           /gps/fix             sensor_msgs/NavSatFix    un mensaje por epoch del GPS (~1 Hz)
//           /battery             sensor_msgs/BatteryState tensión [V]                                        1 Hz
//           /base/estado         std_msgs/String          modo, seguridad, bloqueos y fallas                 2 Hz
//           /base/respuesta      std_msgs/String          lo que el monitor serial mostraría (respuestas, avisos)
// Suscribe  /cmd_vel             geometry_msgs/Twist      linear.x [m/s], angular.z [rad/s]
//           /base/comando        std_msgs/String          los mismos comandos del monitor serial (r, s, l, cal, odo0, wd...)
//
// Con micro-ROS el watchdog de comandos arranca en 300 ms: si /cmd_vel deja de llegar, la base frena. Si se pierde
// el agente, la base se detiene.

#include <stdint.h>

#include "ControlArticulacion.h"
#include "SeguridadBase.h"

// Foto del estado de la base, tomada dentro de la sección crítica (main.cpp)
struct EstadoBase {
  float x, y, th, v, w;       // odometría [m, rad, m/s, rad/s]
  float acc[3], gyro[3];      // [g], [°/s]
  bool imuValida;
  float dist[3];              // frente, izq, der [m]
  bool bumper[4];
  bool seta;
  float bateria;              // V
  SeguridadBase::Estado seg;
  bool bloqAdelante, bloqAtras, frenteSinDato, bateriaBaja;
  float rpm[2], u[2];         // rueda izq, der
  ControlArticulacion::Falla falla[2];
  const char *modo;
};

void rosBegin();
void rosLoop();

// En main.cpp
void baseCmdVel(float v, float w);
void baseLeer(EstadoBase &e);
