#pragma once

// Capa micro-ROS del brazo (solo con -DUSAR_MICROROS, entorno `ros` de platformio.ini).
//
// Publica   /brazo/joint_states  sensor_msgs/JointState  j1..j3: posición [rad], velocidad [rad/s],
//                                                        effort = duty aplicado [%] (diagnóstico)       20 Hz
//           /brazo/estado        std_msgs/String         modo, cero, falla y "llegó" de cada articulación  2 Hz
//           /brazo/respuesta     std_msgs/String         lo que el monitor serial mostraría (respuestas, avisos)
// Suscribe  /brazo/joint_cmd     sensor_msgs/JointState  posiciones [rad]; con nombres j1..j3 o, sin nombres, las 3 en orden
//           /pinza/cierre        std_msgs/Float32        0 = abierta, 100 = cerrada
//           /pinza/giro          std_msgs/Float32        grados, -90..90
//           /brazo/comando       std_msgs/String         los mismos comandos del monitor serial (z, home 2, s, r, wd 300...)
//
// Todo pasa por ejecutar(): mismas validaciones y protecciones que por serial. Si se pierde el agente, el brazo
// se detiene (comando s).

void rosBegin();
void rosLoop();
