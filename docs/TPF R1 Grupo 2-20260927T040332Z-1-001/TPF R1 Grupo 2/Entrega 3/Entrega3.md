---
**UNIVERSIDAD NACIONAL DE ASUNCIÓN**

**FACULTAD DE INGENIERÍA**

# **ROBÓTICA I**

TRABAJO PRÁCTICO FINAL 2026S2

## **"Robot móvil recogedor de frutas"**

---
###**Grupo [2]:**

---



*   Pablo Junior Otazu Lujan
*   Gabriela Belén Orrego Arzamendia
*   Héctor Dejesús Velázquez Ojeda
*   Mathias Ramón Aguilar Delvalle

**ENTREGA [3]:** [Diseño preliminar del robot]

**Fecha:** 13/09/2026

**Versión:** [1.0]



---

### **1. Modelo cinemático directo del robot**
Se analiza un robot manipulador RRR inspirado en el uArm, el cual incorpora un mecanismo de cuatro barras en lazo cerrado. Dado que la convención clásica de Denavit-Hartenberg (DH) está diseñada exclusivamente para cadenas cinemáticas seriales, no permite modelar bucles cerrados de forma directa. Por ello, para resolver la cinemática, el sistema de barras paralelas se transforma en un brazo serial equivalente de tres eslabones.

El análisis geométrico y la asignación de parámetros DH se desarrollan hasta el punto muñeca ($P_3$) en función de tres variables articulares independientes. El giro longitudinal y la apertura de la herramienta se omiten en esta etapa, ya que no alteran la posición de dicho punto. La transformación final hacia el efector final se incorporará posteriormente sumando la geometría de la herramienta acoplada.


#### **1.1 Método 1: Por Geometría**
La cinemática directa constituye la base del análisis robótico, permitiendo determinar con precisión la posición y orientación del efector final a partir de las coordenadas articulares. Mediante el uso de métodos geométricos, es posible simplificar la complejidad matemática de estos sistemas descomponiendo la estructura del brazo en relaciones trigonométricas elementales.

En configuraciones más avanzadas, como los mecanismos de cuatro barras (donde se incluye la estructura de tipo paralelogramo), el enfoque geométrico resulta particularmente ventajoso. Este diseño aprovecha la invariancia de los ángulos entre sus eslabones, logrando que el extremo del robot mantenga una orientación constante respecto a la base fija durante todo el movimiento. Esta propiedad no solo facilita el modelado matemático, sino que optimiza el control cinemático al reducir la dependencia de las variables articulares en la orientación del efector [[1]](https://www.youtube.com/watch?v=5PMPBbH0f7o).
<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1iJaOeZGYvsNW7vhEa2rceqs7W9GXJiXV" width="700" />
  <p><b>Fig. 1.</b> Mecanismo de 4 barras utilizado para el robot.</p>
</div>

<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1lrFj1ijCd7jnwqStxCNvM3Wd4OYDvuKr" width="700" />
  <p><b>Fig. 2.</b> Variables utilizadas en el mecanismo de 4 barras para el cálculo de la cinemática directa por el método geométrico.</p>
</div>

#### **1.2 Relación geométrica del mecanismo**

Se consideran las longitudes:

- $l_2$: eslabón fijo inferior $(AB)$. longitud conocida
- $l_4$: eslabón superior $(CD)$.
- $l_{3,1}$: posición inicial del eslabón $l_3$.
- $l_{3,0}$: posición de referencia del eslabón $l_3$.
- $l$: longitud de los eslabones laterales $(AC)$ y $(BD)$, ($l_{3}$=$l_{3,1}$ = $l$).
- $L$: diagonal auxiliar entre los puntos $C$ y $B$.
- $h$: altura vertical del punto $C$.
- $\alpha$, $\beta$ y $\gamma$: ángulos mostrados en el esquema.
- $q_{3O}$: ángulo de salida del mecanismo.

A partir del triángulo formado por $A$, $C$ y $B$, se aplica la ley de cosenos:

$$
L^2 = l^2 + l_2^2 - 2ll_2\cos(\gamma)
$$

Por tanto, la diagonal auxiliar es:

$$
\boxed{
L =
\sqrt{l^2+l_2^2-2ll_2\cos(\gamma)}
}
$$

La altura \(h\) se puede expresar desde los dos triángulos rectángulos:

$$
\sin(\alpha)=\frac{h}{L}
\qquad \Rightarrow \qquad
h=L\sin(\alpha)
$$

$$
\sin(\gamma)=\frac{h}{l}
\qquad \Rightarrow \qquad
h=l\sin(\gamma)
$$

Igualando ambas expresiones de la altura:

$$
L\sin(\alpha)=l\sin(\gamma)
$$

Finalmente, se obtiene:

$$
\boxed{
\sin(\alpha)=\frac{l\sin(\gamma)}{L}
}
$$

y el ángulo \(\alpha\) es:

$$
\boxed{
\alpha=
\sin^{-1}
\left(
\frac{l\sin(\gamma)}{L}
\right)
}
$$

Para determinar el ángulo \(\beta\), se aplica nuevamente la ley de cosenos al triángulo formado por \(C\), \(D\) y \(B\):

$$
l_4^2=L^2+l^2-2Ll\cos(\beta)
$$

Despejando:

$$
\boxed{
\cos(\beta)=
\frac{L^2+l^2-l_4^2}{2Ll}
}
$$

Por consiguiente:

$$
\boxed{
\beta=
\cos^{-1}
\left(
\frac{L^2+l^2-l_4^2}{2Ll}
\right)
}
$$

Para la rama física abierta mostrada en el CAD, el ángulo de salida
se obtiene restando los ángulos:

$$
\boxed{
q_{3O}=\alpha-\beta
}
$$

#### **1.3  Cinemática geométrica considerando el giro de base $q_1$**

La articulación $q_1$ es una articulación rotacional alrededor del eje vertical $Z$.

Por ello, primero se determina la posición del punto final $P_3$ en el plano vertical del brazo. Luego, esa posición se gira alrededor de $Z$ mediante $q_1$ para obtener las coordenadas finales en los ejes $X$, $Y$ y $Z$.



#### **Ángulo interno del paralelogramo**

Los ángulos de entrada del mecanismo son $q_2$ y $q_3$.

El ángulo interno $\gamma$ se obtiene mediante:

$$
\boxed{
\gamma=q_3+ (q_2-\frac{\pi}{2})
}
$$

#### **Posición del punto $P_3$ en el plano vertical**
Tomaremos el plano $X$ $Z$, eso quiere decir que el giro de nuestra articulación de base $q_{1}$ es 0 grados.

Una vez conocido $q_{3,O}$, se calcula la distancia horizontal $r$ y la altura $z$ del punto final.

La distancia horizontal $r$ es la separación entre el eje de giro $Z$ y el punto final $P_3$:

$$
\boxed{
r=x=
l_2\cos(q_2)+
l_3\cos(q_2+q_{3,O})
}
$$

La coordenada vertical incluye la altura fija $h_1$ de la base:

$$
\boxed{
z=
h_1+
l_2\sin(q_2)+
l_3\sin(q_2+q_{3,O})
}
$$
En el eje $Y$ se tiene:
$$
\boxed{
y=0}
$$



<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1FHATt6_A-sRi8mt9W1vjX1bYwjJAWTcR" width="700" />
  <p><b>Fig. 3.</b> Eje X-Z del mecanismo de 4 barras.</p>
</div>
<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1hPpBRDFRbfoDaeWEmvyqX2l5Wm9qHmiA" width="700" />
  <p><b>Fig. 4.</b> Proyección del punto muñeca sobre el espacio tridimensional x y z.</p>
</div>







#### **Giro de base sobre el plano $XY$**

El valor $r$ calculado anteriormente se gira alrededor del eje vertical $Z$ mediante el ángulo $q_1$.

Por tanto, las coordenadas sobre el plano $XY$ son:

$$
\boxed{
x=r\cos(q_1)
}
$$

$$
\boxed{
y=r\sin(q_1)
}
$$

Sustituyendo la expresión de $r$:

$$
x=
\left[
l_2\cos(q_2)+
l_3\cos(q_2+q_{3,O})
\right]\cos(q_1)
$$

$$
y=
\left[
l_2\cos(q_2)+
l_3\cos(q_2+q_{3,O})
\right]\sin(q_1)
$$

#####Posición final del punto $P_3$
Finalmente:

$$
\boxed{
\mathbf{P}_3=
\begin{bmatrix}
x\\
y\\
z
\end{bmatrix}
=
\begin{bmatrix}
\left[
l_2\cos(q_2)+l_3\cos(q_2+q_{3,O})
\right]\cos(q_1)\\[8pt]
\left[
l_2\cos(q_2)+l_3\cos(q_2+q_{3,O})
\right]\sin(q_1)\\[8pt]
h_1+l_2\sin(q_2)+l_3\sin(q_2+q_{3,O})
\end{bmatrix}
}
$$

#### **1.4 Método 2: Denavit-Hartenberg**

Un enfoque similar fue presentado para el robot uArm Swift Pro, mediante
el desarrollo de modelos de cinemática directa e inversa y su posterior
integración con un modelo CAD de simulación. Este procedimiento permitió
comparar el comportamiento cinemático simulado con el robot físico
[[2]](https://doi.org/10.1051/matecconf/202440604014).

Para formular la cinemática directa se utilizó la convención clásica de
Denavit–Hartenberg (DH), asignando a cada eslabón los parámetros
$\theta_i$, $d_i$, $a_i$ y $\alpha_i$. A partir de estos parámetros se
construyen las matrices de transformación homogénea que relacionan los
sistemas de referencia consecutivos [[3]](https://www.mheducation.es/fundamentos-de-robotica-9788448156367-spain).



<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1djQIRY2plrxUpAPUlmpPZkv2i8hCDJrm" width="700" />
  <p><b>Fig. 5.</b> Bosquejo del robot para la obtención de la tabla D-H.</p>
</div>



# Cinemática directa del robot
Se modela el robot hasta el punto muñeca $P_3$ mediante una cadena cinemática equivalente de tres articulaciones rotativas.

Las variables articulares independientes son:

$$
\mathbf q=
\begin{bmatrix}
q_1\\
q_2\\
q_3
\end{bmatrix}
$$

- $q_1$: rotación de la base alrededor del eje vertical $Z_0$.
- $q_2$: ángulo de entrada del brazo.
- $q_3$: ángulo de entrada del mecanismo de paralelogramo.

El ángulo que utiliza el tercer eslabón equivalente no es directamente $q_3$, sino el ángulo de salida del paralelogramo, denominado $q_{3,O}$.

---

### 1. Cálculo del ángulo de salida del paralelogramo

Primero se calcula el ángulo interno $\gamma$:

$$
\boxed{
\gamma=q_3+q_2-\frac{\pi}{2}
}
$$

La diagonal auxiliar $L$ se obtiene mediante la ley de cosenos:

$$
\boxed{
L=
\sqrt{
l_2^2+l^2-2l_2l\cos(\gamma)
}
}
$$

El ángulo $\alpha$ es:

$$
\alpha=
\sin^{-1}
\left(
\frac{l\sin(\gamma)}{L}
\right)
$$

El ángulo $\beta$ es:

$$
\beta=
\cos^{-1}
\left(
\frac{L^2+l^2-l_4^2}{2Ll}
\right)
$$

Por tanto, el ángulo de salida del paralelogramo es:

$$
\boxed{
q_{3,O}=\alpha-\beta
}
$$

---

### 2. Convención de Denavit-Hartenberg

Se adopta la convención con el eje $Z_0$ positivo hacia arriba.
Debido a que el mecanismo posee un lazo cinemático cerrado, el método de Denavit-Hartenberg no representa directamente todas las restricciones geométricas del mecanismo. Por ello, primero se resuelve el cierre del mecanismo de cuatro barras para obtener la variable dependiente $q_{3,O}$. Posteriormente, esta orientación se utiliza para representar el mecanismo mediante una cadena serial equivalente de tres eslabones

| Transformación | $\theta_i$ | $d_i$ | $a_i$ | $\alpha_i$ |
|---|---:|---:|---:|---:|
| S0-S1 | $q_1$ | $h_1$ | $0$ | $+\frac{\pi}{2}$ |
| S1-S2 | $q_2$ | $0$ | $l_2$ | $0$ |
| S2-S3 | $q_{3,O}$ | $0$ | $l_3$ | $0$ |

La tercera variable de la tabla es:

$$
\boxed{
\theta_3=q_{3,O}(q_2,q_3)
}
$$

Por tanto, $q_{3,O}$ no es un cuarto grado de libertad independiente, representa la orientación del balancín de salida y se obtiene como variable dependiente mediante el cierre del mecanismo

---

### 3. Matriz de transformación ${}^{0}A_1$

Se definen:

$$
c_1=\cos(q_1),
\qquad
s_1=\sin(q_1)
$$

Entonces:

$$
{}^{0}A_1=
\begin{bmatrix}
c_1 & 0 & s_1 & 0\\
s_1 & 0 & -c_1 & 0\\
0 & 1 & 0 & h_1\\
0 & 0 & 0 & 1
\end{bmatrix}
$$

---

### 4. Matriz de transformación ${}^{1}A_2$

Se definen:

$$
c_2=\cos(q_2),
\qquad
s_2=\sin(q_2)
$$

Entonces:

$$
{}^{1}A_2=
\begin{bmatrix}
c_2 & -s_2 & 0 & l_2c_2\\
s_2 & c_2 & 0 & l_2s_2\\
0 & 0 & 1 & 0\\
0 & 0 & 0 & 1
\end{bmatrix}
$$

---

### 5. Matriz de transformación ${}^{2}A_3$

Se definen:

$$
c_3=\cos(q_{3,O}),
\qquad
s_3=\sin(q_{3,O})
$$

Entonces:

$$
{}^{2}A_3=
\begin{bmatrix}
c_3 & -s_3 & 0 & l_3c_3\\
s_3 & c_3 & 0 & l_3s_3\\
0 & 0 & 1 & 0\\
0 & 0 & 0 & 1
\end{bmatrix}
$$

---

### 6. Matriz de transformación total

La matriz de transformación desde la base hasta el punto muñeca $P_3$ es:

$$
{}^{0}T_3 =
{}^{0}A_1 \, {}^{1}A_2 \, {}^{2}A_3
$$

Se definen las abreviaturas:

$$
c_{23}=\cos(q_2+q_{3,O})
$$

$$
s_{23}=\sin(q_2+q_{3,O})
$$

Por tanto:

$$
{}^{0}T_3=
\begin{bmatrix}
c_1c_{23} & -c_1s_{23} & s_1 &
c_1\left(l_2c_2+l_3c_{23}\right) \\
s_1c_{23} & -s_1s_{23} & -c_1 &
s_1\left(l_2c_2+l_3c_{23}\right) \\
s_{23} & c_{23} & 0 &
h_1+l_2s_2+l_3s_{23} \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

---

### 7. Cinemática directa: coordenadas del punto $P_3$

La última columna de la matriz ${}^{0}T_3$ contiene la posición del punto muñeca $P_3$ respecto a la base.

$$
\boxed{
x=
\left[
l_2\cos(q_2)+
l_3\cos(q_2+q_{3,O})
\right]\cos(q_1)
}
$$

$$
\boxed{
y=
\left[
l_2\cos(q_2)+
l_3\cos(q_2+q_{3,O})
\right]\sin(q_1)
}
$$

$$
\boxed{
z=
h_1+
l_2\sin(q_2)+
l_3\sin(q_2+q_{3,O})
}
$$

Finalmente, el vector de posición del punto muñeca es:

$$
\boxed{
\mathbf P_3=
\begin{bmatrix}
x\\
y\\
z
\end{bmatrix}
}
$$

$$
\boxed{
\mathbf{P}_3=
\begin{bmatrix}
x\\
y\\
z
\end{bmatrix}
=
\begin{bmatrix}
\left[
l_2\cos(q_2)+l_3\cos(q_2+q_{3,O})
\right]\cos(q_1)\\[8pt]
\left[
l_2\cos(q_2)+l_3\cos(q_2+q_{3,O})
\right]\sin(q_1)\\[8pt]
h_1+l_2\sin(q_2)+l_3\sin(q_2+q_{3,O})
\end{bmatrix}
}
$$

## **2. Simulaciones**


La simulación se estructuró en cuatro bloques, separando el cálculo matemático de la visualización gráfica. En la primera celda se declaran las dimensiones físicas del mecanismo, las restricciones articulares y las ecuaciones utilizadas para determinar la configuración del mecanismo de cuatro barras. En particular, se consideran como variables articulares independientes $q_1$, $q_2$ y $q_3$, mientras que el ángulo de salida $q_{3O}$ se obtiene como una variable dependiente a partir del cierre geométrico del mecanismo. También se calcula la posición del punto de muñeca $P_3$.

La segunda sección configura el entorno tridimensional de visualización, manteniendo una escala y una perspectiva comunes para representar correctamente la geometría y el movimiento del brazo.

El tercer bloque determina el espacio de trabajo mediante el barrido de múltiples combinaciones de $q_1$, $q_2$ y $q_3$. Para cada configuración se resuelve el cierre geométrico del mecanismo de cuatro barras y se descartan las posiciones que no cumplen las restricciones de longitud o que corresponden a una rama geométrica no deseada. De esta manera, se conservan únicamente las configuraciones físicamente válidas y se obtiene el conjunto de posiciones alcanzables por el punto $P_3$.

Finalmente, la última celda implementa el modelo interactivo tridimensional del brazo. Al modificar los parámetros, $q_1$ controla el giro de la base alrededor del eje $Z$, $q_2$ controla el movimiento del eslabón $AB$ y $q_3$ acciona el balancín de entrada $CA$. El movimiento de $CA$ desplaza el punto $C$, provocando el movimiento del acoplador $CD$ y, mediante el cierre geométrico, del balancín de salida $BD$. Por lo tanto, la posición de $D$, la orientación del balancín de salida y el ángulo $q_{3O}$ se determinan automáticamente a partir de la configuración del mecanismo. Finalmente, la posición de $P_3$ se obtiene a partir del movimiento del balancín de salida.

Como referencia visual del volumen objetivo definido para el proyecto, se incorpora una esfera estática de diámetro $30\,\text{cm}$. Esta esfera permite comparar visualmente el espacio de trabajo calculado con la región objetivo de recolección. Su representación no implica que todo el volumen de la esfera sea necesariamente alcanzable, por lo que la cobertura se verifica mediante los puntos obtenidos durante el barrido de configuraciones.



```python
# @title


# ==========================================================
# CINEMÁTICA DIRECTA Y ESPACIO DE TRABAJO — VERSIÓN INTERACTIVA
# Robot paralelogramo RRR
# q3,0 es una variable DEPENDIENTE (se calcula a partir de q2 y q3)
#
# SISTEMA DE REFERENCIA UNIFICADO (coincide con el CAD y los
# esquemas): eje X = rojo, eje Y = verde, eje Z = azul (vertical).
# Ambos gráficos 3D usan EXACTAMENTE el mismo rango y la misma
# escala en los tres ejes, para que no haya confusión al pasar
# de uno a otro ni al rotar con el mouse.
# ==========================================================
# %%
import numpy as np
import plotly.graph_objects as go
import ipywidgets as widgets
from IPython.display import display
from google.colab import output
output.enable_custom_widget_manager()

# ==========================================================
# PARÁMETROS GEOMÉTRICOS DEL ROBOT [mm]
# ==========================================================
h1 = 150.0    # Altura desde la base hasta la articulación 2
l2 = 350.22   # Eslabón fijo inferior (AB)
l3 = 329.51   # Balancín de salida del paralelogramo (segundo eslabón del brazo)
l  = 40.00    # Eslabones laterales del paralelogramo (l3,1 = l3,0 = l)
l4 = 338.00   # Eslabón superior / acoplador (CD)

# ==========================================================
# LÍMITES ARTICULARES [grados]
# ==========================================================
q1_min, q1_max = -75, 75     # Recorrido total: 150°
q2_min, q2_max = -25, 135    # Recorrido total: 160°
q3_min, q3_max = -50, 50     # Recorrido total: 100°


def calcular_q30(q2, q3):
    """
    Calcula el ángulo de salida q30 del mecanismo de cuatro barras.

    q2 y q3 se ingresan en radianes.
    Retorna q30 en radianes.

    Si una combinación no permite cerrar el mecanismo sin cruzar barras,
    retorna np.nan.
    """

    # Ángulo interno entre la barra verde y el balancín de entrada
    gamma = q3 + q2 - np.pi / 2

    # Diagonal auxiliar del lazo de cuatro barras
    L = np.sqrt(
        l**2 + l2**2 - 2 * l * l2 * np.cos(gamma)
    )

    # Condición física de cierre del mecanismo:
    # |l4 - l| <= L <= l4 + l
    L_min = abs(l4 - l)
    L_max = l4 + l

    # Se conserva la rama de montaje del CAD (abierta, sin cruce).
    # En q2 + q3 = 90° AB y CA quedan colineales; después cambia el modo.
    modo_cad = np.cos(q2 + q3) > 0
    valido = (L >= L_min) & (L <= L_max) & modo_cad

    # Se reemplazan las configuraciones imposibles por NaN
    L_seguro = np.where(valido, L, np.nan)

    # Cálculo del ángulo alpha
    sin_alpha = np.clip(
        l * np.sin(gamma) / L_seguro,
        -1.0,
        1.0
    )

    alpha = np.arcsin(sin_alpha)

    # Cálculo del ángulo beta
    cos_beta = np.clip(
        (L_seguro**2 + l**2 - l4**2) / (2 * L_seguro * l),
        -1.0,
        1.0
    )

    beta = np.arccos(cos_beta)

    # Rama física del CAD. alpha + beta es el ensamblaje cruzado.
    q30 = alpha - beta

    # Se asegura que las posturas imposibles permanezcan como NaN
    q30 = np.where(valido, q30, np.nan)

    return q30


def cinematica_directa(q1, q2, q3):
    """
    Cinemática directa del punto P3 (end-effector), coincide con:
        x = [l2 cos(q2) + l3 cos(q2+q3,0)] cos(q1)
        y = [l2 cos(q2) + l3 cos(q2+q3,0)] sin(q1)
        z = h1 + l2 sin(q2) + l3 sin(q2+q3,0)
    q1, q2, q3 en RADIANES
    q3,0 se calcula internamente a partir de q2 y q3 (variable dependiente).
    Retorna x, y, z [mm] y q30 [rad].
    """
    q30 = calcular_q30(q2, q3)
    r = l2 * np.cos(q2) + l3 * np.cos(q2 + q30)

    x = r * np.cos(q1)
    y = r * np.sin(q1)

    z = h1 + l2 * np.sin(q2) + l3 * np.sin(q2 + q30)
    return x, y, z, q30
```


```python
# @title


# ==========================================================
# SISTEMA DE REFERENCIA COMÚN (se calcula una sola vez)
# Rango fijo de X, Y, Z tomado del espacio de trabajo completo,
# y una escena de Plotly reutilizable para que TODOS los
# gráficos 3D del notebook compartan la misma escala y
# orientación de ejes.
# ==========================================================
_n_ref = 15
_q1r = np.radians(np.linspace(q1_min, q1_max, _n_ref))
_q2r = np.radians(np.linspace(q2_min, q2_max, _n_ref))
_q3r = np.radians(np.linspace(q3_min, q3_max, _n_ref))
_Q1r, _Q2r, _Q3r = np.meshgrid(_q1r, _q2r, _q3r, indexing='ij')
_Xr, _Yr, _Zr, _ = cinematica_directa(_Q1r, _Q2r, _Q3r)

_R_max = np.nanmax(np.hypot(_Xr, _Yr))

_z_min = np.nanmin(_Zr)
_z_max = np.nanmax(_Zr)

_pad_xy = 1.08 * _R_max
_pad_z = 0.08 * (_z_max - _z_min)

RANGO_XY = [-_pad_xy, _pad_xy]
RANGO_Z = [_z_min - _pad_z, _z_max + _pad_z]

ESCENA_COMUN = dict(
    xaxis=dict(title='X [mm]', range=RANGO_XY),
    yaxis=dict(title='Y [mm]', range=RANGO_XY),
    zaxis=dict(title='Z [mm]', range=RANGO_Z),
    aspectmode='data',                       # misma escala física en los 3 ejes
    camera=dict(up=dict(x=0, y=0, z=1),       # Z siempre "hacia arriba"
                eye=dict(x=1.4, y=1.4, z=1.0))
)


def trazas_ejes_referencia(longitud=None):
    """
    Devuelve 3 trazas Scatter3d que dibujan los ejes en el origen con
    el mismo código de color que el CAD: X = rojo, Y = verde, Z = azul.
    Sirven de referencia visual fija para no confundir la orientación
    al rotar el gráfico.
    """
    if longitud is None:
        longitud = 0.15 * _R_max
    return [
        go.Scatter3d(x=[0, longitud], y=[0, 0], z=[0, 0], mode='lines',
                      line=dict(color='red', width=6), name='X',
                      showlegend=False),
        go.Scatter3d(x=[0, 0], y=[0, longitud], z=[0, 0], mode='lines',
                      line=dict(color='green', width=6), name='Y',
                      showlegend=False),
        go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, longitud], mode='lines',
                      line=dict(color='blue', width=6), name='Z',
                      showlegend=False),
    ]

```


```python
# @title


# ==========================================================
# ESPACIO DE TRABAJO (interactivo)

# ==========================================================

salida_espacio = widgets.Output()
etiqueta_espacio = widgets.HTML()


def graficar_espacio_trabajo(n=15):
    q1_vals = np.radians(np.linspace(q1_min, q1_max, n))
    q2_vals = np.radians(np.linspace(q2_min, q2_max, n))
    q3_vals = np.radians(np.linspace(q3_min, q3_max, n))

    Q1, Q2, Q3 = np.meshgrid(
        q1_vals, q2_vals, q3_vals, indexing='ij'
    )

    X, Y, Z, q30 = cinematica_directa(Q1, Q2, Q3)

    # Alcance radial con la convención DH:
    # theta3 = q2 + q3,0
    r = l2 * np.cos(Q2) + l3 * np.cos(Q2 + q30)

    # Configuraciones donde el cuatro barras cierra correctamente.
    # Se conserva r >= 0 para mostrar solo la región frontal.
    mascara = (
        np.isfinite(X) &
        np.isfinite(Y) &
        np.isfinite(Z) &
        np.isfinite(r) &
        (r >= 0)
    )

    X = X[mascara]
    Y = Y[mascara]
    Z = Z[mascara]
    r = r[mascara]

    if X.size == 0:
        etiqueta_espacio.value = (
            "<b>No existen configuraciones válidas</b> "
            "para los límites articulares seleccionados."
        )
        with salida_espacio:
            salida_espacio.clear_output(wait=True)
        return

    fig = go.Figure(data=[
        go.Scatter3d(
            x=X,
            y=Y,
            z=Z,
            mode='markers',
            marker=dict(
                size=2,
                color=Z,
                colorscale='Viridis',
                cmin=RANGO_Z[0],
                cmax=RANGO_Z[1],
                opacity=0.5
            ),
            name='Espacio de trabajo'
        ),
        *trazas_ejes_referencia()
    ])

    fig.update_layout(
        title=(
            f"Espacio de trabajo — n={n} muestras/articulación "
            f"({X.size} configuraciones válidas)"
        ),
        scene=ESCENA_COMUN,
        width=600,
        height=700,
        uirevision='espacio_trabajo'
    )

    etiqueta_espacio.value = (
        f"<b>Configuraciones válidas:</b> {X.size} de {n**3}<br>"
        f"<b>Alcance radial:</b> {r.min():.2f} – {r.max():.2f} mm<br>"
        f"<b>Altura Z:</b> {Z.min():.2f} – {Z.max():.2f} mm"
    )

    with salida_espacio:
        salida_espacio.clear_output(wait=True)
        fig.show()


slider_resolucion = widgets.IntSlider(
    min=5,
    max=35,
    step=2,
    value=15,
    description='Resolución',
    continuous_update=False
)

_interaccion_espacio = widgets.interactive_output(
    graficar_espacio_trabajo,
    {'n': slider_resolucion}
)

display(widgets.VBox([
    slider_resolucion,
    etiqueta_espacio,
    salida_espacio
]))
```


```python
# @title

# Posición del end-effector + mecanismo real de cuatro barras
# Esta celda utiliza las variables definidas previamente en el cuaderno:
# h1, l2, l, l3, l4, q1_min/max, q2_min/max, q3_min/max,
# ESCENA_COMUN y trazas_ejes_referencia().




# ==========================================================
# CONFIGURACIÓN
# ==========================================================

# Rama física observada en el CAD: mecanismo abierto, sin cruce de barras.
# La rama +1 corresponde a la otra solución matemática (ensamblaje cruzado).
RAMA_CIERRE = -1

# La esfera queda fija en la posición mostrada en la captura.
R_ZONA_FIJA = 450.0         # mm
Q1_ZONA_FIJA = 0.0          # grados
Z_ZONA_FIJA = 300.0         # mm
DIAMETRO_ZONA_FIJA = 300.0  # mm


# ==========================================================
# CINEMÁTICA DEL MECANISMO DE CUATRO BARRAS
# ==========================================================

def _normalizar_angulo(angulo):
    """Lleva un ángulo al intervalo [-pi, pi]."""
    return np.arctan2(np.sin(angulo), np.cos(angulo))


def _punto_3d(punto_plano, q1):
    """Convierte (radio, z) a (x, y, z) mediante el giro q1."""
    radio, z = punto_plano
    return np.array([
        radio * np.cos(q1),
        radio * np.sin(q1),
        z
    ], dtype=float)


def _interseccion_circulos(centro_1, radio_1, centro_2, radio_2, rama=+1):
    """Intersección seleccionada de dos circunferencias en el plano radial-Z."""
    centro_1 = np.asarray(centro_1, dtype=float)
    centro_2 = np.asarray(centro_2, dtype=float)
    vector = centro_2 - centro_1
    distancia = np.linalg.norm(vector)

    if distancia < 1e-9:
        return None
    if distancia > radio_1 + radio_2:
        return None
    if distancia < abs(radio_1 - radio_2):
        return None

    avance = (radio_1**2 - radio_2**2 + distancia**2) / (2 * distancia)
    altura_cuadrada = radio_1**2 - avance**2
    if altura_cuadrada < -1e-8:
        return None

    altura = np.sqrt(max(altura_cuadrada, 0.0))
    punto_medio = centro_1 + avance * vector / distancia
    perpendicular = np.array([-vector[1], vector[0]]) / distancia
    return punto_medio + rama * altura * perpendicular


def puntos_mecanismo_4b(q1, q2, q3):
    """
    Calcula O, A, B, C, D y P3.

    q2 mueve AB y q3 mueve CA. El punto D se obtiene del cierre
    geométrico; por tanto, el ángulo de salida y q30 son dependientes.
    """
    # En q2 + q3 = 90° las barras AB y CA quedan colineales. Continuar
    # más allá obliga a cambiar al modo cruzado, que no representa al CAD.
    if np.cos(q2 + q3) <= 0:
        return None, np.nan

    O_plano = np.array([0.0, 0.0])
    A_plano = np.array([0.0, h1])

    B_plano = A_plano + l2 * np.array([np.cos(q2), np.sin(q2)])

    theta_entrada = np.pi / 2 - q3
    C_plano = A_plano + l * np.array([
        np.cos(theta_entrada),
        np.sin(theta_entrada)
    ])

    # D debe satisfacer simultáneamente |B-D| = l y |C-D| = l4.
    D_plano = _interseccion_circulos(
        B_plano, l,
        C_plano, l4,
        rama=RAMA_CIERRE
    )
    if D_plano is None:
        return None, np.nan

    theta_BD = np.arctan2(
        D_plano[1] - B_plano[1],
        D_plano[0] - B_plano[0]
    )
    theta_salida = _normalizar_angulo(theta_BD + np.pi)
    q30 = _normalizar_angulo(theta_salida - q2)

    # BP3 es la prolongación opuesta al balancín BD.
    P3_plano = B_plano + l3 * np.array([
        np.cos(theta_salida),
        np.sin(theta_salida)
    ])

    puntos_planos = {
        'O': O_plano,
        'A': A_plano,
        'B': B_plano,
        'C': C_plano,
        'D': D_plano,
        'P3': P3_plano
    }
    puntos_3d = {
        nombre: _punto_3d(punto, q1)
        for nombre, punto in puntos_planos.items()
    }
    return puntos_3d, q30


# ==========================================================
# ELEMENTOS FIJOS DE LA FIGURA
# ==========================================================

def _crear_fondo_espacio_trabajo(n=12):
    """Genera una nube ligera del espacio alcanzable."""
    xs, ys, zs = [], [], []
    q1_muestras = np.radians(np.linspace(q1_min, q1_max, n))
    q2_muestras = np.radians(np.linspace(q2_min, q2_max, n))
    q3_muestras = np.radians(np.linspace(q3_min, q3_max, n))

    for q1 in q1_muestras:
        for q2 in q2_muestras:
            for q3 in q3_muestras:
                puntos, _ = puntos_mecanismo_4b(q1, q2, q3)
                if puntos is None:
                    continue
                xs.append(puntos['P3'][0])
                ys.append(puntos['P3'][1])
                zs.append(puntos['P3'][2])

    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode='markers',
        marker=dict(size=1.4, color='black', opacity=0.12),
        name='Espacio de trabajo',
        hoverinfo='skip'
    )


def _crear_esfera_fija():
    """Crea una esfera inmóvil respecto del sistema de coordenadas global."""
    radio = DIAMETRO_ZONA_FIJA / 2
    angulo = np.radians(Q1_ZONA_FIJA)
    x_centro = R_ZONA_FIJA * np.cos(angulo)
    y_centro = R_ZONA_FIJA * np.sin(angulo)

    u = np.linspace(0, 2 * np.pi, 35)
    v = np.linspace(0, np.pi, 20)
    xs = x_centro + radio * np.outer(np.cos(u), np.sin(v))
    ys = y_centro + radio * np.outer(np.sin(u), np.sin(v))
    zs = Z_ZONA_FIJA + radio * np.outer(np.ones(u.size), np.cos(v))

    return go.Surface(
        x=xs,
        y=ys,
        z=zs,
        colorscale=[[0, '#ef5350'], [1, '#ef5350']],
        opacity=0.28,
        showscale=False,
        name='Zona de trabajo fija',
        hoverinfo='skip'
    )


FONDO_ESPACIO_TRABAJO = _crear_fondo_espacio_trabajo()
ESFERA_FIJA = _crear_esfera_fija()


# ==========================================================
# TRAZAS DEL ROBOT
# ==========================================================

def _traza_barra(punto_1, punto_2, color, nombre, mostrar_leyenda=False):
    longitud = np.linalg.norm(punto_2 - punto_1)
    texto = f'{nombre}<br>Longitud = {longitud:.2f} mm'
    return go.Scatter3d(
        x=[punto_1[0], punto_2[0]],
        y=[punto_1[1], punto_2[1]],
        z=[punto_1[2], punto_2[2]],
        mode='lines',
        line=dict(color=color, width=12),
        text=[texto, texto],
        hovertemplate='%{text}<extra></extra>',
        name='Mecanismo de cuatro barras',
        legendgroup='cuatro_barras',
        showlegend=mostrar_leyenda
    )


def _trazas_robot(puntos):
    O, A = puntos['O'], puntos['A']
    B, C = puntos['B'], puntos['C']
    D, P3 = puntos['D'], puntos['P3']

    return [
        _traza_barra(O, A, '#6a1b9a', 'Base O-A'),
        _traza_barra(
            A, B, '#2e8b57', 'AB = l2 (barra principal)',
            mostrar_leyenda=True
        ),
        _traza_barra(B, D, '#1e88e5', 'BD = l (balancín de salida)'),
        _traza_barra(D, C, '#f4c430', 'DC = l4 (acoplador)'),
        _traza_barra(C, A, '#e53935', 'CA = l (balancín de entrada)'),

        go.Scatter3d(
            x=[B[0], P3[0]],
            y=[B[1], P3[1]],
            z=[B[2], P3[2]],
            mode='lines',
            line=dict(color='#0d47a1', width=12),
            text=[
                f'Antebrazo BP3 = l3<br>Longitud = {l3:.2f} mm',
                f'Antebrazo BP3 = l3<br>Longitud = {l3:.2f} mm'
            ],
            hovertemplate='%{text}<extra></extra>',
            name='Antebrazo BP3'
        ),

        go.Scatter3d(
            x=[O[0], A[0]],
            y=[O[1], A[1]],
            z=[O[2], A[2]],
            mode='markers+text',
            marker=dict(
                size=[10, 12],
                color=['#212121', '#ff8f00'],
                line=dict(color='white', width=2)
            ),
            text=['O: q1', 'A: q2 / q3'],
            textposition=['bottom center', 'bottom center'],
            hovertemplate=(
                '%{text}<br>Articulación actuada<extra></extra>'
            ),
            name='Actuadores en la base'
        ),

        go.Scatter3d(
            x=[B[0], C[0], D[0]],
            y=[B[1], C[1], D[1]],
            z=[B[2], C[2], D[2]],
            mode='markers+text',
            marker=dict(
                size=7,
                color='#616161',
                line=dict(color='white', width=1.5)
            ),
            text=['B', 'C', 'D'],
            textposition='top center',
            hovertemplate=(
                '%{text}<br>Articulación pasiva<extra></extra>'
            ),
            name='Articulaciones pasivas'
        ),

        go.Scatter3d(
            x=[P3[0]],
            y=[P3[1]],
            z=[P3[2]],
            mode='markers+text',
            marker=dict(
                size=10,
                color='#d50000',
                line=dict(color='white', width=2)
            ),
            text=['P3'],
            textposition='top center',
            hovertemplate=(
                'End-effector P3'
                '<br>X = %{x:.2f} mm'
                '<br>Y = %{y:.2f} mm'
                '<br>Z = %{z:.2f} mm'
                '<extra></extra>'
            ),
            name='End-effector P3'
        )
    ]


# ==========================================================
# CONTROLES VISIBLES: q1, q2 Y q3
# ==========================================================

estilo_slider = {'description_width': '110px'}

slider_q1 = widgets.FloatSlider(
    min=q1_min,
    max=q1_max,
    step=1,
    value=0,
    description='q1 [°]',
    continuous_update=True,
    style=estilo_slider
)

slider_q2 = widgets.FloatSlider(
    min=q2_min,
    max=q2_max,
    step=1,
    value=45,
    description='q2 [°]',
    continuous_update=True,
    style=estilo_slider
)

slider_q3 = widgets.FloatSlider(
    min=q3_min,
    max=q3_max,
    step=1,
    value=0,
    description='q3 entrada [°]',
    continuous_update=True,
    style=estilo_slider
)


# ==========================================================
# FIGURA PERSISTENTE
# ==========================================================

TITULO_NORMAL = 'Mecanismo real de 4 barras y zona de trabajo fija'
TITULO_NO_ALCANZABLE = (
    '<span style="color:#b00020">Configuración no alcanzable: '
    'cierre imposible o cambio al modo cruzado.</span>'
)

puntos_iniciales, _ = puntos_mecanismo_4b(
    *np.radians([slider_q1.value, slider_q2.value, slider_q3.value])
)

if puntos_iniciales is None:
    raise ValueError('La posición inicial del mecanismo no es alcanzable.')

# FigureWidget se crea una sola vez. Al actualizar sus trazas no se reinicia
# la cámara, por lo que se conservan el giro, el zoom y el encuadre del usuario.
fig = go.FigureWidget(data=[
    FONDO_ESPACIO_TRABAJO,
    ESFERA_FIJA,
    *_trazas_robot(puntos_iniciales),
    *trazas_ejes_referencia()
])

fig.update_layout(
    title=TITULO_NORMAL,
    width=800,
    height=720,
    margin=dict(l=10, r=10, b=10, t=55),
    legend=dict(
        x=0.01,
        y=0.99,
        xanchor='left',
        yanchor='top',
        bgcolor='rgba(255,255,255,0.70)'
    ),
    # Reutiliza exactamente los mismos ejes, escala y cámara del cuaderno.
    scene=ESCENA_COMUN,
    # También indica a Plotly que debe conservar el estado visual del usuario.
    uirevision='robot_4_barras'
)

# ==========================================================
# ACTUALIZAR SOLO LAS COORDENADAS DEL ROBOT
# ==========================================================

def _actualizar_segmento(traza, punto_1, punto_2):
    traza.x = [punto_1[0], punto_2[0]]
    traza.y = [punto_1[1], punto_2[1]]
    traza.z = [punto_1[2], punto_2[2]]


def _actualizar_trazas_robot(puntos):
    """Modifica las trazas existentes sin volver a crear la figura."""
    O, A = puntos['O'], puntos['A']
    B, C = puntos['B'], puntos['C']
    D, P3 = puntos['D'], puntos['P3']

    # Índices 0 y 1: espacio de trabajo y esfera fija.
    _actualizar_segmento(fig.data[2], O, A)
    _actualizar_segmento(fig.data[3], A, B)
    _actualizar_segmento(fig.data[4], B, D)
    _actualizar_segmento(fig.data[5], D, C)
    _actualizar_segmento(fig.data[6], C, A)
    _actualizar_segmento(fig.data[7], B, P3)

    # Actuadores O y A.
    fig.data[8].x = [O[0], A[0]]
    fig.data[8].y = [O[1], A[1]]
    fig.data[8].z = [O[2], A[2]]

    # Articulaciones pasivas B, C y D.
    fig.data[9].x = [B[0], C[0], D[0]]
    fig.data[9].y = [B[1], C[1], D[1]]
    fig.data[9].z = [B[2], C[2], D[2]]

    # End-effector P3.
    fig.data[10].x = [P3[0]]
    fig.data[10].y = [P3[1]]
    fig.data[10].z = [P3[2]]


def actualizar_pose(_cambio=None):
    q1, q2, q3 = np.radians([
        slider_q1.value,
        slider_q2.value,
        slider_q3.value
    ])
    puntos, _ = puntos_mecanismo_4b(q1, q2, q3)

    if puntos is None:
        fig.layout.title.text = TITULO_NO_ALCANZABLE
        return

    # Se agrupan los cambios en una sola actualización visual.
    with fig.batch_update():
        _actualizar_trazas_robot(puntos)
        fig.layout.title.text = TITULO_NORMAL


for slider in (slider_q1, slider_q2, slider_q3):
    slider.observe(actualizar_pose, names='value')

descripcion = widgets.HTML(
    "<b>Mecanismo real de cuatro barras</b><br>"
    "<b>q1:</b> gira el mecanismo alrededor del eje Z.<br>"
    "<b>q2:</b> mueve la barra AB.<br>"
    "<b>q3:</b> mueve el balancín de entrada CA.<br>"
    "El acoplador CD transmite el movimiento al balancín de salida BD.<br>"
    "<b>q3,0 no se controla:</b> se calcula mediante el cierre geométrico.<br>"
    "Solo se admite la rama física sin cruce: <b>q2 + q3 &lt; 90°</b>."
)

display(widgets.VBox([
    descripcion,
    slider_q1,
    slider_q2,
    slider_q3
]))

contenedor_figura = widgets.Box(
    [fig],
    layout=widgets.Layout(
        width='820px',
        max_width='100%',
        height='740px',
        overflow='hidden'
    )
)

display(contenedor_figura)
```

---

## **3. Referencias**
[[1]](https://www.youtube.com/watch?v=) L. Armesto, “Cinemática directa de robots con métodos geométricos |
Sistemas Robotizados (ANTIGUO),” YouTube, 1 de septiembre de 2020.
[En línea]. Disponible en:
https://www.youtube.com/watch?v=5PMPBbH0f7o

[[2]](https://doi.org/10.1051/matecconf/202440604014) D. Schütz y
J. H. Hepworth, “uArm Swift simulation and control,”
*MATEC Web of Conferences*, vol. 406, art. 04014, 2024.
doi: 10.1051/matecconf/202440604014.

[[3]](https://www.mheducation.es/fundamentos-de-robotica-9788448156367-spain)
A. Barrientos, L. F. Peñín, C. Balaguer y R. Aracil,
*Fundamentos de robótica*, 2.ª ed. Madrid: McGraw-Hill, 2007.

---

## **4. Carpeta del proyecto**
Carpeta del grupo E2:
[TPF - Estación 2](https://drive.google.com/drive/folders/1JggH_t1V1V1kcT6KU79V80s9d-Px1JNs?usp=sharing)
