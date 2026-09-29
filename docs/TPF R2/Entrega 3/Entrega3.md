---
**UNIVERSIDAD NACIONAL DE ASUNCIÓN**

**FACULTAD DE INGENIERÍA**

# **ROBÓTICA II**

TRABAJO PRÁCTICO FINAL 2026S2

## **"Robot recolector de Limones"**


---
###**ROBOT:** [Arturito R2D2]

**Grupo [2]:**


*   Pablo Junior Otazu Lujan
*   Pedro Daniel Vera Ramírez
*   Héctor Dejesús Velázquez Ojeda
*   Mathias Ramón Aguilar Delvalle

**ENTREGA [3]:** Diseño de la plataforma robótica y su montaje.


**Fecha:** [27/09/2026]

**Versión:** [1.0]

---

## Etapa 1: Diseño y Montaje

Para el diseño del robot optamos por una caja de madera en forma de T, de manera que las ruedas no sobresalgan demasiado del cuerpo del robot.

### 1.1 Dimensiones

Para las dimensiones, se puede verificar la siguiente imagen para obtener más detalles.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1U8i0vW7jBCLFu_SymdjkoFAlUrorcExx" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1U8i0vW7jBCLFu_SymdjkoFAlUrorcExx" width="500">
    <br>
    </a><b>Figura 1.</b> Dimensiones de la base.
</div>

La base está formada por madera de 1 cm de espesor. Los laterales siguen el perímetro de la base y cuentan con una altura de 18 cm.

La forma en T reparte las funciones del chasis: el travesaño ancho (40 × 23 cm) forma la parte superior donde se monta el brazo robótico, y el tallo estrecho (34 cm de ancho) es el que aloja las ruedas, haciendo que queden ocultas dentro de la huella del travesaño y no sobresalgan del diseño.

### 1.2 Materiales de la estructura

Todo el robot está hecho de planchas de madera de 1 cm, un material que combina buena rigidez con un peso bajo, algo importante en un móvil que debe trasladarse por terreno irregular.

Las piezas que componen la estructura son:

- **2 planchas en forma de T** (1 cm): una para la base y otra para la tapa.
- **Paredes laterales** (1 cm): siguen el perímetro de la base, usando la misma plancha de madera, y le dan los 18 cm de altura al cuerpo.
- **3 planchas de bumper** (1 cm): dos laterales y una frontal, de 10 cm × 5 cm.
- **1 base impresa en 3D** para el montaje del brazo robótico.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1L7yTsV3OfdVroTy-YpvVxh8GRWpQ2WAa" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1L7yTsV3OfdVroTy-YpvVxh8GRWpQ2WAa" width="500">
    <br>
    </a><b>Figura 2.</b> Base del robot.
</div>

### 1.3 Tapa, laterales y bisagras

La tapa en forma de T está fija a los paneles laterales por medio de dos bisagras, cada una fijada con tornillos tirafondo. La tapa pivota a través de las bisagras para dar acceso a la electrónica interna y a los drivers del robot.

### 1.4 Ruedas, motores y soportes

Las ruedas están fijadas a los ejes de los motores, los cuales están fijos a la base a través de un soporte para los mismos, como se ve en la siguiente figura.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1QzPswBik59VWy94oC5ynOpxibmoK4NVv" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1QzPswBik59VWy94oC5ynOpxibmoK4NVv" width="500">
    <br>
    </a><b>Figura 3.</b> Base del motor para las ruedas.
</div>

De este modo, la rueda queda firmemente sujeta a la base del robot, y es el motor el encargado de transmitirle el movimiento para el desplazamiento.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/15A8kX0KxDvhij1lI5DkbKUPXhTZdPUf8" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/15A8kX0KxDvhij1lI5DkbKUPXhTZdPUf8" width="500">
    <br>
    </a><b>Figura 4.</b> Rueda fijada al soporte del motor sobre la base.
</div>

Para las ruedas optamos por un par de ruedas de 15 cm de diámetro y 6 cm de ancho. Con ese diámetro se obtiene la altura libre necesaria respecto al piso para moverse entre los árboles frutales y realizar la recolección de forma eficiente.

### 1.5 Bumpers

En los laterales y en la parte frontal del robot tenemos 3 planchas de madera que funcionan como bumpers, mediante un mecanismo de resorte que permite que vuelvan a su posición inicial luego de ser presionadas.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1QdNAf0HwtARISjoVU-T4GWjW3QWtJ3-M" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1QdNAf0HwtARISjoVU-T4GWjW3QWtJ3-M" width="500">
    <br>
    </a><b>Figura 5.</b> Bumper lateral con mecanismo de resorte.
</div>

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1ku6In3FWYZOYCDaKo9PnBiEHzW4tq9zw" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1ku6In3FWYZOYCDaKo9PnBiEHzW4tq9zw" width="500">
    <br>
    </a><b>Figura 6.</b> Bumper frontal con mecanismo de resorte.
</div>

Cada uno de los tres bumpers lleva además un final de carrera, que permite al sistema de control detectar el instante en que el bumper se comprime y reaccionar en consecuencia.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1MZSS0Q-Bt38CgbY2G2k67SmoDxUFOTAn" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1MZSS0Q-Bt38CgbY2G2k67SmoDxUFOTAn" width="500">
    <br>
  </a>
  <b>Figura 7.</b> Finales de carrera para los bumpers, zocalo para distribucion electrica, drivers, motores y bateria montados.
</div>

### 1.6 Electrónica de potencia



El robot emplea un driver por motor —es decir, 2 drivers en total—, lo que permite controlar cada rueda de forma independiente y distribuir mejor la carga entre ambos. Esto además posibilita realizar un giro diferencial: variando la velocidad de cada motor por separado, el robot avanza en línea recta o gira sobre su propio eje. El robot dispone de 4 drivers, pero solo dos son para la traccion de las ruedas.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1iqb4MU-GAXMCoNLq0LYKrPpkdXIrV3lr" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1iqb4MU-GAXMCoNLq0LYKrPpkdXIrV3lr" width="500">
    <br>
    </a><b>Figura 8.</b> Motores, drivers y buck fijados a la base.
</div>

En la cara interna del robot se encuentran los drivers de los motores encargados de mover las ruedas y el brazo robótico, el cual estará fijado en la parte superior del robot móvil mediante una base impresa en 3D.

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1G-BwXYNj3D2_HpSrBouFGbxQegeH8CA-" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1G-BwXYNj3D2_HpSrBouFGbxQegeH8CA-" width="500" style="transform: rotate(90deg);">
    <br>
    </a><b>Figura 9.</b> Drivers de los motores del brazo robótico (cara interna).
</div>

<div align="center">
  <a href="https://lh3.googleusercontent.com/d/1mv37R0i-c84JdQb5syPTu44erf7EQ0UF" target="_blank">
    <img src="https://lh3.googleusercontent.com/d/1mv37R0i-c84JdQb5syPTu44erf7EQ0UF" width="500">
    <br>
    </a><b>Figura 10.</b> Base de impresión 3D para el brazo robótico.
</div>

### 1.7 Resumen de materiales

| Cantidad | Pieza | Especificación |
|---|---|---|
| 2 | Plancha base y tapa | Madera, 1 cm de espesor, forma en T |
| 1 juego | Paredes laterales | Madera, 1 cm de espesor, 18 cm de altura |
| 3 | Planchas de bumper | Madera, 1 cm de espesor, 10 x 5 cm |
| 3 | Finales de carrera | — |
| 1 | Base del brazo robótico | Pieza impresa en 3D |
| 2 | Motores DC | — |
| 2 | Ruedas | Diámetro 15 cm, ancho 6 cm |
| 2 | Drivers de motor | Uno por motor |
| 3 | Drivers del brazo robótico | — |
| 2 | Bisagras de tapa | — |
| 3 | Buck DC DC | — |
| — | Tornillería | Tornillos tirafondo |

---