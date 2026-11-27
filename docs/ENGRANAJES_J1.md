# Engranajes doble helicoidales de J1 (base del brazo)

Especificación del usuario (27/11/2026). **Todavía no están montados**: hasta montarlos, el firmware sigue con la correa.

Reemplaza la correa GT2 de 17,5 mm de ancho (poleas de 56,79 y 12,31 mm, relación 4,61:1; el firmware usa 84/18 = 4,667).
Par doble helicoidal (herringbone) de involuta, ejes paralelos, con la V central definida. Eje vertical (la cara del
engranaje queda paralela al suelo).

- Distancia entre centros: **57,00 mm** (la misma de la correa), ranura de ajuste de ±0,3 mm en el soporte del motor.
- Relación **80/15 = 5,333:1**. El engranaje grande gira −15/80 del piñón: **en sentido contrario** (la correa no invertía).
- Módulo transversal 1,200 mm, normal 1,0876 mm. Ángulo de presión normal 20° (transversal 21,880°).
- Hélice ±25°, manos opuestas entre piñón y engranaje.
- Addendum 1,0876 mm, dedendum 1,4682 mm (1,35·mn), altura del diente 2,556 mm.
- Backlash de diseño 0,15 mm adelgazando los dientes (espesor en el primitivo 1,810 mm, hueco 1,960 mm), sin tocar la
  distancia entre centros. En la base son ~0,18° (0,15 / 48 mm); a 0,5 m de alcance, ~1,6 mm.

| Dato | Piñón | Engranaje grande |
|---|---|---|
| Dientes | 15 | 80 |
| Diámetro primitivo | 18,000 | 96,000 |
| Diámetro exterior | 20,175 | 98,175 |
| Diámetro de raíz | 15,064 | 93,064 |
| Diámetro base | 16,70 | 89,09 |
| Ancho total | 17,5 (2 × 8,75) | 17,5 (2 × 8,75) |
| Agujero | Ø8,20 | Ø4,20 (el brazo se fija con un cubo atornillado, aún sin modelar) |
| Hélice | −25° / +25° | +25° / −25° |

En el modelo el engranaje está girado 2,25° (medio paso) para que los dientes entren en los huecos.

Revisado (27/11): mt = mn / cos 25°, diámetros, 57 mm entre centros, espesor + hueco = paso transversal (3,770 mm) y
el medio paso cierran. El piñón de 15 dientes no se socava (equivalente ≈ 20 dientes).

## Qué hay que cambiar al montarlos

Pedido del usuario (27/11): no tocar nada hasta que avise que están montados; ahí, todos los pasos en orden, desde el 1.

Firmware que corre hoy en la WROOM: `pruebas-esp32/20-brazo-coordinado/include/config.h` (`CFG_J1`).
`firmware/brazo/include/brazo_config.h` también, para que no quede atrás.

1. **Relación** `84.0f / 18.0f` → `80.0f / 15.0f`: 41,48 → **47,41 cuentas/°**.
2. **Signos de J1:** al invertirse el sentido, en 20 `false, true` → `true, false` (motor y encoder juntos), para que
   "+ = hacia el mástil" siga igual. Comprobar con un movimiento corto y sin brazo estirado antes de un homing.
3. **Mecánica:** confirmar que el eje del 36GP-555 entra en el Ø8,20 del piñón; diseñar el cubo del engranaje grande
   (el Ø4,20 solo no sostiene el brazo); ajustar la ranura para el juego mínimo sin trabar.
4. **Medir de nuevo** zona muerta, feedforward (17 %) y despegue: cambia la fricción. En 20 el PI de velocidad va en
   °/s de la base, así que no hace falta reescalarlo; en `firmware/brazo` va en rpm del motor: kpVel y kiVel se
   multiplicaban por 1,286 (6/4,667) y pasan a 1,125 (6/5,333): 0,618 y 4,5.
5. **Comentarios con la correa:** "se autobloquea por la correa" y el freno al llegar (el autobloqueo viene de la
   reductora 50:1; comprobar que sigue sin deslizar), el juego de la correa en el comentario del PI, y el homing de
   `firmware/brazo` (−10 rpm = 11,25 °/s de la base; 120° en 10,7 s, entra en los 25 s).
6. Velocidad máxima de la base: 160 rpm / 5,333 = 30 rpm (antes 34,3); los 30 °/s de `velMax` piden 26,7 rpm, sobra.
7. Docs que dicen "correa 18 → 84" para J1: `ARQUITECTURA.md`, `CONEXIONES.md`, `manual/capitulos/03_mecanica.tex`
   y `06_firmware.tex`. Las entregas ya entregadas no se tocan.
