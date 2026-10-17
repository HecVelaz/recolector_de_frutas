# Aclaraciones para Claude — revisión de Robótica I, Entrega 7

Confirmadas por Héctor el 17/10/2026. **Aplicadas el 17/10** en Entrega7.md y Entrega7_.ipynb (ver la bitácora); la relación de J2/J3 quedó confirmada: engranajes helicoidales 15 → 75 (5:1).

## Motores y transmisión

- Los motores 5840-31ZY de J2/J3 ya fueron descartados. Su torque era de **8 kgf·cm**, según lo confirmado por el usuario.
- **J1 conserva su correa GT2 18 → 90 (5:1). J2 y J3 NO usan correas: usan transmisión por engranajes helicoidales.**
- Se hicieron numerosas pruebas con los 5840: se cambió el L298N por IBT-2 para reducir la caída de tensión y aprovechar al máximo la alimentación, pero aun así el motor no levantaba el brazo.
- Se agregó un resorte y consiguió subir, pero el control resultó muy inestable, con oscilación física considerable. Las gráficas de Python podían aparentar cumplimiento sin representar adecuadamente ese comportamiento real. No presentar esas curvas como validación satisfactoria del funcionamiento mecánico de J2/J3.
- **Se probó el motor de J1 de 160 rpm en la posición de J2, con la transmisión helicoidal, y sí tuvo fuerza para levantar el brazo.** Esta prueba ya se hizo: no dejarla como pendiente.
- A partir de ese resultado se compraron los motores de **58 rpm**, con mayor par que el motor de J1. Su llegada sigue pendiente. La bitácora previa indica 22 kgf·cm nominales para la variante de 58 rpm; no confundir este valor con los 8 kgf·cm del motor descartado.
- La relación de transmisión de los engranajes helicoidales NO quedó confirmada en esta conversación. Pedir la relación o el número de dientes antes de recalcular. No trasladar automáticamente el 5:1 de las antiguas correas a los engranajes.

## Cambios a realizar en la entrega

1. Presentar claramente el diseño final previsto y el estado real: los 5840 están descartados y se esperan los motores nuevos. Las fotos históricas pueden mostrar el montaje anterior, con el pie aclaratorio correspondiente.
2. Actualizar tablas, texto y diagramas: correa solo en J1; transmisión helicoidal en J2/J3. Revisar también la descripción de encoders y drivers según la configuración descrita.
3. Usar **246 g para la pinza**, valor del pesaje real que el usuario indicó priorizar frente a los 322 g anteriores. Mantener claro qué incluye el conjunto pesado y revisar los cálculos de masa y torque que usaban 322 g.
4. Justificar el cambio de motores con la secuencia de ensayos anterior. El PWM de 48–59 % por sí solo no es la evidencia de insuficiencia: lo determinante fue que no levantaba sin resorte y que con resorte el comportamiento era inestable.
5. Revisar las cifras de **10,8 N·m, 70 °/s y 44 480 cuentas por vuelta de articulación** de J2/J3: dependen de la antigua reducción externa 5:1 y no quedan validadas para la transmisión helicoidal hasta confirmar su relación. Revisar además las cotas estáticas y su transmisión por el cuatro barras; no presentar capacidad calculada como ensayo satisfactorio con los motores nuevos.
6. Los dos servos de posición fueron **probados individualmente y funcionan bien**. Basta una descripción breve; no hace falta extender su caracterización. Quitar la afirmación de autobloqueo mecánico del servo.
7. El usuario agregará los videos más adelante; sus enlaces siguen pendientes.
8. Las 18 imágenes con marcadores ID_Fig del Markdown sí están incrustadas en el cuaderno local: no tratarlas como faltantes del .ipynb. Mantener ambos archivos coherentes al aplicar los cambios.

## Documentación general pendiente

El AGENTS.md de la raíz es un enlace simbólico a CLAUDE.md. Ambos siguen indicando correas 5:1 para J2/J3 y la prueba de J1 en J2 como pendiente. Corregir esas referencias y la documentación/configuración afectada cuando se confirme la relación helicoidal; no modificar parámetros del firmware suponiendo una relación no medida.
