# Lista de compras

Versión del 05/10/2026, armada a partir del conexionado v0.4 (`CONEXIONES.md` y `html/conexiones.html`) y del inventario
(`Componentes_inventario.md`). Marcar con `[x]` lo que ya se compró. Desde la v0.6 (08/10) los motores van con la LiPo
directa y la Pi con el power bank: no hace falta ningún buck nuevo.

## Brazo

- [ ] 2 × motor 36-555 de 58 rpm (139:1), 12 V, eje de 8 mm, con encoder: J2 y J3 (`fotos/motor_j2/`)
- [ ] 2 × driver IBT-2 (BTS7960): J2 y J3 (hay 3: dos de tracción y J1)
- [ ] 2 juegos de transmisión 5:1: polea GT2 de 20 dientes con agujero de 8 mm + polea GT2 de 100 dientes + correa
      cerrada GT2 de 240 mm y 6 mm de ancho (~54 mm entre centros; con 18 → 90 harían falta ~62 mm)

## Potencia (v0.6, 08/10: solo con lo que hay)

Ya está: LiPo 3S y su cargador balanceador (motores), selector WEG, par de XT60, seta, power bank Xiaomi PB2030MI (Pi y
ESP32), cable grueso, borneras, capacitores, resistencias. La 10S queda guardada. **No se compra** lo de la v0.4 (Schottky ≥ 30 A, 2200 µF,
TVS, relé, interruptores, ventilador, fusibles de 58 V): ver `CONEXIONES.md` v0.6.

- [x] Par de XT60 con cable (`fotos/conectores/`): reemplaza el Deans de la LiPo (09/10: no hay Deans hembra)
- [x] Selector WEG con 2 bloques BC10 NA (10/10, `fotos/llaves/selector.jpeg`): ON/OFF de los motores, los 2 NA en paralelo.
      Reemplaza a la térmica CHINT C10, que se saca
- [x] **Fusible de auto de lámina de 20 A** (10/10: ya está; falta confirmar el portafusible), pegado al XT60 de la LiPo: la única protección real
      contra un corto (los de auto son para continua hasta 32 V). Buscar primero en el lab o en un auto viejo
- [x] Power bank Xiaomi PB2030MI 20000 mAh, 5 V 3 A: alimenta la Pi (`fotos/bateria 3/`)
- [x] Seta (09/10, `fotos/llaves/hongo.jpeg`): hongo de 22 mm modular, giro para liberar, con 2 bloques NC (10/10): corte del
      + del bus de 12 V + aviso al GPIO 47
- [ ] Capacitores (08/10: hay, falta buscarlos): todos los de ≥ 25 V van al bus de 12 V de motores
- [x] Cinta CSI de 22 a 15 pines para la Pi 5 (reemplazada el 05/10)

## Placas de las ESP32 (`html/placa_s3.html`, `html/placa_wroom.html`)

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
- [ ] 1 resistencia de 100 kΩ y 1 de 27 kΩ: divisor de la LiPo 3S (S3 GPIO 1)
- [ ] 4 resistencias de 20 kΩ: bajar a 3,3 V las salidas de los encoders de tracción
- [ ] ~10 capacitores cerámicos de 100 nF: S3 6 (3 bumpers, seta, reserva y divisor de la batería) y WROOM 3
      (finales de carrera)

## Cables

- [x] Cable grueso para potencia
- [ ] Cable de 18 AWG (lógica; también el riel de 6 V y el GND de los servos en la placa de la WROOM)
- [ ] Cable unifilar fino de colores (24-26 AWG) para las perforadas
- [ ] ~4 m de cable mallado o trenzado de 4 hilos para los encoders del brazo
- [x] Borneras para el GND común y los buses de 12 V

## A confirmar si ya los tienen

- [ ] Después de la prueba integrada (H8): luz, buzzer y habilitación física del brazo con estado visible
- [ ] Disipador activo de la Pi 5
- [x] Voltímetro LED de 4,5-30 V para la LiPo (`fotos/Medidor de Voltaje/`)
- [ ] Microinterruptores V-152-1C25 ×10, para bumpers y finales de carrera (`fotos/bumpers/`)
- [ ] 4.º bumper, si la cátedra lo exige (la guía de R2 pide 4): un microinterruptor más en el GPIO 40 de la S3
