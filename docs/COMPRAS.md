# Lista de compras

Versión del 05/10/2026, armada a partir del conexionado v0.4 (`CONEXIONES.md` y `conexiones.html`) y del inventario
(`Componentes_inventario.md`). Marcar con `[x]` lo que ya se compró. Con la LiPo para la lógica **ya no hace falta
el segundo buck 1**.

## Brazo

- [ ] 2 × motor 36-555 de 58 rpm (139:1), 12 V, eje de 8 mm, con encoder: J2 y J3 (`fotos/motor_j2/`)
- [ ] 2 × driver IBT-2 (BTS7960): J2 y J3 (hay 3: dos de tracción y J1)
- [ ] 2 juegos de transmisión 5:1: polea GT2 de 20 dientes con agujero de 8 mm + polea GT2 de 100 dientes + correa
      cerrada GT2 de 240 mm y 6 mm de ancho (~54 mm entre centros; con 18 → 90 harían falta ~62 mm)

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

Sin INA219 ni salvalipo (06/10): solo pruebas vigiladas de ≤ 30 min; alcanza el indicador de barras.

- [ ] Conector Deans (T) hembra + portafusible y fusible de 5 A pegado al conector
- [ ] Interruptor de lógica de 12 V y 5 A
- [x] Cinta CSI de 22 a 15 pines para la Pi 5 (reemplazada el 05/10)

## Placas de las ESP32 (`placa_s3.html`, `placa_wroom.html`)

- [ ] Perforada doble faz de 9 × 15 cm: se corta en dos tiras de ~9 × 3 cm para la S3 (una sobre cada fila de
      borneras de la Freenove); y una de 7 × 9 cm para la WROOM
- [ ] 2 tiras de pines hembra de 1 × 15 (zócalo de la HW-394)
- [ ] 2 tiras de pines macho de 1 × 40 (entradas y salidas de las perforadas, IBT-2 y servos)
- [ ] 3 cables Dupont hembra-hembra de 8 hilos (IBT-2 del brazo) y un juego de Dupont hembra-macho (de los
      módulos a las borneras de la Freenove)
- [ ] Conectores JST-XH con cable armado: 3 de 4 vías (encoders del brazo) y 4 de 2 vías (finales de carrera y
      reserva)
- [ ] 1 bornera de 2 vías, paso 5,08 mm (6 V de los servos en la placa de la WROOM)
- [ ] 4 separadores M3 (placa de la WROOM)

## Componentes chicos

- [ ] ~12 resistencias de 10 kΩ: pull-downs de los EN (S3 38, WROOM 23) y pull-ups de los finales de carrera
      (WROOM 36, 39); opcionales: pull-ups de WROOM 34, 35 y 27, y 4 en la S3 si los LEDs de la Freenove cargan
      los pines de los bumpers y la seta
- [ ] 3 resistencias de 1 kΩ y 3 de 2 kΩ: divisores de los ECHO de los HC-SR04
- [ ] 1 resistencia de 120 kΩ y 1 de 8,2 kΩ: divisor de la 10S (S3 GPIO 1)
- [ ] 4 resistencias de 20 kΩ: bajar a 3,3 V las salidas de los encoders de tracción
- [ ] ~10 capacitores cerámicos de 100 nF: S3 6 (3 bumpers, seta, reserva y divisor de la batería) y WROOM 3
      (finales de carrera)
- [ ] 2 MOSFET de nivel lógico (IRLZ44N) + diodos: luz y buzzer desde la Pi

## Cables

- [ ] Silicona de 12-14 AWG roja y negra (potencia)
- [ ] Cable de 18 AWG (lógica; también el riel de 6 V y el GND de los servos en la placa de la WROOM)
- [ ] Cable unifilar fino de colores (24-26 AWG) para las perforadas
- [ ] ~4 m de cable mallado o trenzado de 4 hilos para los encoders del brazo
- [ ] Barra de borneras para el GND común y los buses de 12 V

## A confirmar si ya los tienen

- [ ] Luz de estado y buzzer (los pide la guía de R2)
- [ ] Disipador activo de la Pi 5
- [x] Voltímetro LED de 4,5-30 V para la LiPo (`fotos/Medidor de Voltaje/`)
- [ ] Microinterruptores V-152-1C25 ×10, para bumpers y finales de carrera (`fotos/bumpers/`)
- [ ] 4.º bumper, si la cátedra lo exige (la guía de R2 pide 4): un microinterruptor más en el GPIO 40 de la S3
