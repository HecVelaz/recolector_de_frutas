# Lista de compras

Versión del 05/10/2026, armada a partir del conexionado v0.4 (`CONEXIONES.md` y `conexiones.html`) y del inventario
(`Componentes_inventario.md`). Marcar con `[x]` lo que ya se compró. Con la LiPo para la lógica **ya no hace falta
el segundo buck 1**.

## Brazo

- [ ] 2 × motor 36-555 de 98 rpm (82:1), 12 V, eje de 8 mm, con encoder: J2 y J3 (`fotos/motor_j2/`)
- [ ] 2 × driver IBT-2 (BTS7960): J2 y J3 (hay 3: dos de tracción y J1)
- [ ] 2 juegos de transmisión: polea GT2 de 18 dientes con agujero de 8 mm + polea grande + correa cerrada GT2 de
      6 mm (relación a definir; J1 usa 18 → 90)

## Potencia de motores (10S)

- [ ] Diodo Schottky ≥ 30 A (p. ej. MBR6045 o MBR60100) + disipador: el frenado no vuelve al buck 1
- [ ] Capacitor de 2200 µF, ≥ 25 V, bajo ESR, en el bus de 12 V de motores
- [ ] TVS de 15 V y 5 kW (5KP15A), unidireccional
- [ ] Relé automotriz de 12 V y 40 A + zócalo + diodo 1N4007 en la bobina
- [ ] Seta de emergencia enclavable (se rearma girándola) con **2 contactos NC**: uno alimenta la bobina del relé y
      el otro avisa a la S3 (GPIO 47)
- [ ] Interruptor de motores para DC, ≥ 20 A y ≥ 60 V DC (entre la 10S y el buck 1)
- [ ] Llave del brazo de 12 V y 10 A
- [ ] Ventilador de 12 V y 40 mm para el buck 1
- [ ] Fusible de 15 A **apto para ≥ 58 V DC** + portafusible, en la batería (los fusibles de auto comunes son de 32 V)
- [ ] Fusibles de 12 V con portafusible: 15 A tracción, 10 A brazo, 3 A servos
- [ ] Conector XT60 hembra para la 10S

## Lógica (LiPo 3S)

- [ ] Salvalipo (alarma de 1 a 8 celdas) para el conector de balanceo JST-XH
- [ ] Conector Deans (T) hembra + portafusible y fusible de 5 A pegado al conector
- [ ] Interruptor de lógica de 12 V y 5 A
- [ ] Módulo INA219 (recomendado): tensión y corriente de la LiPo por el I²C de la S3 (0x40), para que la Pi se
      apague sola
- [x] Cinta CSI de 22 a 15 pines para la Pi 5 (reemplazada el 05/10)

## Componentes chicos

- [ ] ~10 resistencias de 10 kΩ: pull-downs de los EN (S3 38, WROOM 23) y pull-ups (WROOM 34, 35, 36, 39)
- [ ] 3 resistencias de 1 kΩ y 3 de 2 kΩ: divisores de los ECHO de los HC-SR04
- [ ] 1 resistencia de 120 kΩ y 1 de 8,2 kΩ: divisor de la 10S (S3 GPIO 1)
- [ ] 4 resistencias de 20 kΩ: bajar a 3,3 V las salidas de los encoders de tracción
- [ ] ~6 capacitores de 100 nF: filtros de los bumpers y los finales de carrera
- [ ] 2 MOSFET de nivel lógico (IRLZ44N) + diodos: luz y buzzer desde la Pi

## Cables

- [ ] Silicona de 12-14 AWG roja y negra (potencia)
- [ ] Cable de 18 AWG (lógica)
- [ ] ~4 m de cable mallado o trenzado de 4 hilos para los encoders del brazo
- [ ] Barra de borneras para el GND común y los buses de 12 V

## A confirmar si ya los tienen

- [ ] Luz de estado y buzzer (los pide la guía de R2)
- [ ] Disipador activo de la Pi 5
- [ ] Voltímetro LED de 4,5-30 V para la LiPo (`fotos/Medidor de Voltaje/`)
- [ ] Microinterruptores V-152-1C25 ×10, para bumpers y finales de carrera (`fotos/bumpers/`)
- [ ] 4.º bumper, si la cátedra lo exige (la guía de R2 pide 4): un microinterruptor más en el GPIO 40 de la S3
