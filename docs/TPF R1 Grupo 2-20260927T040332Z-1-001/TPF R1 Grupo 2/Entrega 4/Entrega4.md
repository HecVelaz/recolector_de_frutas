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

**ENTREGA [4]:** Modelo cinemático INVERSO (Simulación). Verificación del espacio de trabajo.

**Fecha:** 23/09/2026

**Versión:** [1.0]



## **1. Cinemática inversa del robot con mecanismo de cuatro barras**
La cinemática inversa consiste en determinar los valores de las variables articulares que permiten al robot ubicar su efector final en una posición deseada del espacio. Es el problema opuesto a la cinemática directa: en lugar de calcular la posición de la muñeca $P_3$ a partir de los ángulos de los motores, se parte de la posición deseada $P_d=(x_d,\,y_d,\,z_d)$ y se buscan los ángulos $q_1$, $q_2$ y $q_3$ que la producen. Este cálculo es indispensable para el control del robot, ya que las tareas se definen en coordenadas cartesianas, pero los motores se comandan en coordenadas articulares.
### **Descripción del robot**

El robot estudiado es un manipulador de 3 grados de libertad con tres actuadores:

- $q_1$: giro de la base alrededor del eje vertical $Z$.
- $q_2$: giro del brazo principal (barra verde $l_2$) en el plano vertical.
- $q_3$: giro del balancín de entrada (barra roja $l_{3,0}$), que transmite el movimiento al antebrazo (barra azul $l_3$) mediante un mecanismo de cuatro barras.

Este tipo de arquitectura, con el actuador del antebrazo ubicado en la base, es habitual en robots manipuladores y paletizadores, porque reduce la masa en movimiento del brazo y aumenta su rigidez [[1]](https://drive.google.com/file/d/1A6TmgVK95j2NsH7j_JB3VN9jatdiAAJn/view?usp=drive_link), [[2]](https://drive.google.com/file/d/1rMQ1tQ1r59F0IsRM7w_aBv_NU0U_Yc1L/view?usp=drive_link).

### **Particularidad del mecanismo**

En los diseños clásicos el cuatro barras es un paralelogramo (eslabones opuestos de igual longitud). En ese caso, el ángulo del antebrazo se relaciona con el actuador de forma directa, $q_{3O}=\pi-\gamma$ [[4]](https://www.youtube.com/watch?v=5PMPBbH0f7o).

En este robot los balancines son iguales, $l_{3,0}=l_{3,1}=40$ mm, pero la barra verde ($l_2=350.22$ mm) y el acoplador ($l_4=338$ mm) tienen longitudes distintas. Por lo tanto, el mecanismo no es un paralelogramo y la relación entre $q_3$ y la orientación del antebrazo es no lineal. Debe resolverse mediante el cierre de lazo del cuatro barras con los ángulos auxiliares $\alpha_4$ y $\beta_4$ [[3]](https://drive.google.com/file/d/1SAsWYSegdkJ7ofSPrZ8D021oHh2uEv0W/view?usp=drive_link). Además, el mecanismo no cumple el criterio de Grashof, lo que limita su rango de movimiento y genera posiciones singulares (puntos muertos) que deben evitarse [[3]](https://drive.google.com/file/d/1SAsWYSegdkJ7ofSPrZ8D021oHh2uEv0W/view?usp=drive_link). La solución a lo último puede darse aumentando la longitud del balanciín de entrada de color rojo.

### **Enfoque de solución**

La cinemática inversa se resuelve por un método geométrico en dos etapas  [[1]](https://doi.org/10.1155/2014/125973), [[2]](https://drive.google.com/file/d/1rMQ1tQ1r59F0IsRM7w_aBv_NU0U_Yc1L/view?usp=drive_link):

1. **Cadena equivalente:** el problema tridimensional se reduce al plano vertical del brazo. Se trata $l_2$ y $l_3$ como un brazo planar de dos eslabones, cuyo ángulo relativo es $q_{3O}$. Con ley de cosenos y la función $\operatorname{atan2}$ se obtienen $q_1$, $q_{3O}$ y $q_2$.
2. **Inversión del cuatro barras:** a partir del $q_{3O}$ requerido, se resuelve el cuadrilátero desde la articulación superior para encontrar el ángulo $\gamma_4$ y, con él, el ángulo real del motor $q_3$.

Como el problema admite varias soluciones matemáticas, cada candidato se filtra según los límites articulares, la rama física del mecanismo y el ángulo de transmisión. Luego se verifica sustituyéndolo en la cinemática directa. Si ningún candidato cumple, el punto se declara no alcanzable.


### **Datos geométricos**

| Símbolo | Eslabón | Longitud [mm] |
|:---:|:---|:---:|
| $h_1$ | Altura del hombro | 150.00 |
| $l_2$ | Barra verde | 350.22 |
| $l_3$ | Barra azul (de $B$ a la muñeca $P_3$) | 329.51 |
| $l_4$ | Barra amarilla (acoplador) | 338.00 |
| $l_{3,0}$ | Balancín de entrada (rojo) | 40.00 |
| $l_{3,1}$ | Balancín de salida (tramo corto del azul) | 40.00 |

En este robot $l_{3,0}=l_{3,1}=l=40\ \text{mm}$

### **Convenciones**

- $q_1$: giro de la base alrededor del eje $Z$.
- $q_2$: ángulo de la barra verde respecto de la horizontal, medido desde el semieje radial $+r$ (lado de la muñeca), en sentido antihorario.
- $q_3$: actuador de la barra roja, cuyo ángulo absoluto es $\theta_i=\dfrac{\pi}{2}-q_3$.
- $\gamma_4$: ángulo auxiliar del cuatro barras en la base:

$$
\gamma_4=q_2+q_3-\frac{\pi}{2}
$$

- $q_{3O}$: ángulo de la barra azul respecto de la prolongación de la barra verde (variable dependiente del cuatro barras).


<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1gcE-dLyLdQ1qOBvKbnWKWKFfnlAolWVp" width="700" />
  <p><b>Fig. 1.</b> Diagrama del mecanismo de 4 barras.</p>
</div>




---

### **1. Modelo directo (punto de partida)**
La posición de la muñeca se obtiene sumando las proyecciones de los eslabones $l_2$ y $l_3$ en el plano del brazo y rotando ese plano con $q_1$ [[1]](https://drive.google.com/file/d/1A6TmgVK95j2NsH7j_JB3VN9jatdiAAJn/view?usp=drive_link), [[4]](https://www.youtube.com/watch?v=5PMPBbH0f7o):
$$
x=\left[l_2\cos q_2+l_3\cos(q_2+q_{3O})\right]\cos q_1
$$

$$
y=\left[l_2\cos q_2+l_3\cos(q_2+q_{3O})\right]\sin q_1
$$

$$
z=h_1+l_2\sin q_2+l_3\sin(q_2+q_{3O})
$$

Cierre directo del cuatro barras (diagonal $L$ desde el extremo de la barra roja hasta $B$):

$$
L=\sqrt{l_2^2+l_{3,0}^2-2\,l_2\,l_{3,0}\cos\gamma_4}
$$

$$
\alpha_4=\operatorname{atan2}\!\left(l_{3,0}\sin\gamma_4,\; l_2-l_{3,0}\cos\gamma_4\right)
$$

$$
\beta_4=\cos^{-1}\!\left(\frac{L^2+l_{3,1}^2-l_4^2}{2\,L\,l_{3,1}}\right)
$$

$$
\boxed{q_{3O}=\alpha_4-\beta_4}
$$

---

### **2. Paso 1 — Reducción al plano radial–$Z$ y cálculo de $q_1$**

Dado el objetivo $P_d=(x_d,\,y_d,\,z_d)$:

$$
\boxed{q_1=\operatorname{atan2}(y_d,\,x_d)}
$$

$$
\boxed{r=\sqrt{x_d^2+y_d^2}}
\qquad\qquad
\boxed{z_p=z_d-h_1}
$$

Con esto el problema se reduce a una cadena planar equivalente de dos eslabones $l_2$ y $l_3$:

$$
r=l_2\cos q_2+l_3\cos(q_2+q_{3O})
$$

$$
z_p=l_2\sin q_2+l_3\sin(q_2+q_{3O})
$$


<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1m5lG6ijE6rRqqXiCSlKUJSCxViymICN4" width="500" />
  <p><b>Fig. 1.</b> Plano XZ cadena equivalente l2-l3.</p>
</div>


---

### **3. Paso 2 — Ángulo equivalente del codo $q_{3O}$**

Elevando al cuadrado y sumando ambas ecuaciones (ley de cosenos) [[2]](https://drive.google.com/file/d/1rMQ1tQ1r59F0IsRM7w_aBv_NU0U_Yc1L/view?usp=drive_link):

$$
r^2+z_p^2=l_2^2+l_3^2+2\,l_2\,l_3\cos q_{3O}
$$

$$
\boxed{c_{3O}=\frac{r^2+z_p^2-l_2^2-l_3^2}{2\,l_2\,l_3}}
$$

**Condición de alcanzabilidad:**

$$
|c_{3O}|\le 1
\quad\Longleftrightarrow\quad
|l_2-l_3|\le\sqrt{r^2+z_p^2}\le l_2+l_3
$$

Si no se cumple, el punto está demasiado lejos o demasiado cerca del hombro y no existe solución.

$$
\boxed{q_{3O}=\pm\cos^{-1}(c_{3O})}
$$

En este mecanismo la barra azul siempre queda "por debajo" de la prolongación de la verde, por lo que la rama física es $q_{3O}<0$:

$$
q_{3O}=-\cos^{-1}(c_{3O})
$$



<div align="center">
  <img src="https://lh3.googleusercontent.com/d/19v--wHdVGLpNWNg3O_tmCGtHk8sYrrJN" width="700" />
  <p><b>Fig. 1.</b> Plano XZ cadena equivalente l2-l3.</p>
</div>

---

### **4. Paso 3 — Ángulo del hombro $q_2$**

El ángulo del hombro se obtiene geométricamente con la función $\operatorname{atan2}$ [[2]](https://drive.google.com/file/d/1rMQ1tQ1r59F0IsRM7w_aBv_NU0U_Yc1L/view?usp=drive_link):

$$
\boxed{
q_2=\operatorname{atan2}(z_p,\,r)-\operatorname{atan2}\!\left(l_3\sin q_{3O},\; l_2+l_3\cos q_{3O}\right)
}
$$

---

### **5. Paso 4 — Cierre inverso del cuatro barras ($q_{3O}\rightarrow\gamma_4$)**

Se resuelve el mismo cuadrilátero, pero ahora desde la articulación superior $B$. Se define el ángulo interior en $B$:

$$
\psi=-q_{3O}
$$

Diagonal desde la base $A$ hasta el extremo $D$ del balancín de salida:

$$
e=\sqrt{l_2^2+l_{3,1}^2-2\,l_2\,l_{3,1}\cos\psi}
$$

Ángulo en $A$ entre la barra verde y la diagonal $AD$:

$$
\delta=\operatorname{atan2}\!\left(l_{3,1}\sin\psi,\; l_2-l_{3,1}\cos\psi\right)
$$

Ángulo en $A$ entre la diagonal $AD$ y la barra roja (triángulo $A$–$C$–$D$ de lados $e$, $l_{3,0}$, $l_4$):

$$
\varepsilon=\cos^{-1}\!\left(\frac{e^2+l_{3,0}^2-l_4^2}{2\,e\,l_{3,0}}\right)
$$

El cuatro barras solo cierra si el argumento de $\cos^{-1}$ está en $[-1,\,1]$. Se obtienen dos candidatos:

$$
\boxed{\gamma_4=-(\delta\pm\varepsilon)}
$$

Aparecen dos candidatos porque la función $q_{3O}(\gamma_4)$ no es monótona: tiene un extremo cerca de $\gamma_4\approx-5^\circ$, así que un mismo $q_{3O}$ puede obtenerse con la barra roja a uno u otro lado de la verde.

---

### **6. Paso 5 — Actuador real $q_3$**

A partir de $\gamma_4=q_2+q_3-\dfrac{\pi}{2}$:

$$
\boxed{q_3=\gamma_4-q_2+\frac{\pi}{2}}
$$

---

### **7. Paso 6 — Filtrado y verificación**

Cada candidato $(q_1,\,q_2,\,q_3)$ se acepta solo si cumple:

1. Límites articulares:

$$
-75^\circ\le q_1\le 75^\circ,
\qquad
-25^\circ\le q_2\le 135^\circ,
\qquad
-50^\circ\le q_3\le 50^\circ
$$

2. Rama física del mecanismo (la barra roja no cruza la verde):

$$
-\pi<\gamma_4<0
\quad\Longleftrightarrow\quad
\cos(q_2+q_3)>0
$$

3. Ángulo de transmisión alejado de los puntos muertos [[3]](https://drive.google.com/file/d/1SAsWYSegdkJ7ofSPrZ8D021oHh2uEv0W/view?usp=drive_link):

$$
\mu=\cos^{-1}\!\left(\frac{l_{3,1}^2+l_4^2-L^2}{2\,l_{3,1}\,l_4}\right),
\qquad
15^\circ\le\mu\le165^\circ
$$

4. Comprobación mediante la cinemática directa:

$$
e_{pos}=\left\|\,P_3(q_1,q_2,q_3)-P_d\,\right\|\approx 0
$$

Si ningún candidato supera los filtros, el punto no es alcanzable con los límites y la rama física del robot.

---

### **8. Límite del mecanismo**
Criterio de Grashof [[3]](https://drive.google.com/file/d/1SAsWYSegdkJ7ofSPrZ8D021oHh2uEv0W/view?usp=drive_link) con $s=40$, $\ell=350.22$, $p=40$, $q=338$:


$$
s+\ell=390.22\;>\;p+q=378
$$

El mecanismo **no es Grashof** (triple balancín). Solo puede armarse si $L\le l_{3,1}+l_4$, lo que limita:

$$
|\gamma_4|\le\cos^{-1}\!\left(\frac{l_2^2+l_{3,0}^2-(l_{3,1}+l_4)^2}{2\,l_2\,l_{3,0}}\right)\approx 131.7^\circ
$$

El balancín rojo puede aumentarse a 60 mm y cumplirá el mecanismo de Grashof.

---

### **9. Ejemplo numérico**

Objetivo: $P_d=(368.32,\;0,\;91.03)\ \text{mm}$

**Paso 1:**

$$
q_1=\operatorname{atan2}(0,\,368.32)=0^\circ,
\qquad
r=368.32\ \text{mm},
\qquad
z_p=91.03-150=-58.97\ \text{mm}
$$

**Paso 2:**

$$
c_{3O}=\frac{368.32^2+(-58.97)^2-350.22^2-329.51^2}{2(350.22)(329.51)}=-0.3990
\;\Rightarrow\;
q_{3O}=-113.516^\circ
$$

**Paso 3:**

$$
q_2=\operatorname{atan2}(-58.97,\,368.32)-\operatorname{atan2}(-302.17,\,218.74)=-9.10^\circ-(-54.10^\circ)=45.00^\circ
$$

**Paso 4:**

$$
\psi=113.516^\circ,
\qquad
e=368.01\ \text{mm},
\qquad
\delta=5.72^\circ,
\qquad
\varepsilon=39.28^\circ
$$

$$
\gamma_4=-(\delta+\varepsilon)=-45.00^\circ
\qquad\text{o}\qquad
\gamma_4=-(\delta-\varepsilon)=+33.56^\circ
$$

**Paso 5:**

$$
q_3=-45.00^\circ-45.00^\circ+90^\circ=0.00^\circ
$$

El segundo candidato daría $q_3=78.56^\circ$, que está fuera de límites y fuera de la rama física, por lo que se descarta.

**Resultado:**

$$
\boxed{q_1=0^\circ,\qquad q_2=45^\circ,\qquad q_3=0^\circ}
\qquad\text{con}\qquad
q_{3O}=-113.516^\circ,
\qquad
e_{pos}\approx 0
$$

---






## **2. Simulación**

La simulación permite elegir una posición deseada del punto muñeca $P_3=(x,\,y,\,z)$ mediante tres sliders. En tiempo real calcula las variables articulares $q_1$, $q_2$ y $q_3$, verifica si el punto es alcanzable y dibuja el robot en 3D junto con su espacio de trabajo.

### **1. Parámetros y restricciones**

Se definen las longitudes del robot ($h_1=150$, $l_2=350.22$, $l_3=329.51$, $l_4=338$, $l_{3,0}=l_{3,1}=40$ mm) y las restricciones físicas:

- Límites articulares: $q_1\in[-75^\circ,75^\circ]$, $q_2\in[-25^\circ,135^\circ]$, $q_3\in[-50^\circ,50^\circ]$.
- Rama física del cuatro barras: $-180^\circ<\gamma_4<0^\circ$, es decir, la barra roja no cruza la verde.
- Ángulo de transmisión $15^\circ\le\mu\le165^\circ$, para descartar posturas cercanas a los puntos muertos del mecanismo.

### **2. Modelo del cuatro barras**

- **Cierre directo** ($\gamma_4\rightarrow q_{3O}$): mediante la diagonal $L$ y los ángulos $\alpha_4$ y $\beta_4$ se obtiene $q_{3O}=\alpha_4-\beta_4$ y el ángulo de transmisión $\mu$.
- **Cierre inverso** ($q_{3O}\rightarrow\gamma_4$): el mismo cuadrilátero se resuelve desde la articulación superior, lo que da dos candidatos $\gamma_4=-(\delta\pm\varepsilon)$.

### **3. Cinemática directa**

A partir de $(q_1,q_2,q_3)$ se calcula $\gamma_4=q_2+q_3-90^\circ$. Con el cierre directo se obtiene $q_{3O}$ y luego la posición de $P_3$. Se usa para verificar cada solución inversa y para generar el espacio de trabajo.

### **4. Cinemática inversa**

Para cada posición de los sliders se ejecuta:

1. $q_1=\operatorname{atan2}(y,x)$, $r=\sqrt{x^2+y^2}$, $z_p=z-h_1$.
2. $c_{3O}$ por ley de cosenos. Si $|c_{3O}|>1$, el punto está demasiado lejos o demasiado cerca del hombro.
3. $q_{3O}=\pm\cos^{-1}(c_{3O})$ y cálculo de $q_2$ para cada rama.
4. Cierre inverso del cuatro barras para obtener $\gamma_4$.
5. $q_3=\gamma_4-q_2+90^\circ$.
6. Filtrado por límites articulares, rama física y ángulo de transmisión, más una verificación con la cinemática directa (error de posición $\approx 0$).

Si ningún candidato supera los filtros, la función no devuelve solo "sin solución": informa el motivo concreto. Los motivos posibles son:

- fuera de alcance;
- $q_1$, $q_2$ o $q_3$ fuera de límites;
- el cuatro barras no cierra;
- la roja cruzaría la verde;
- cercanía a un punto muerto.

### **5. Espacio de trabajo**

Se generan aleatoriamente unas 12 000 combinaciones de $(q_1,q_2,q_3)$ dentro de sus límites. Se evalúan de forma vectorizada con NumPy y se conservan solo las configuraciones válidas. El resultado es una nube de aproximadamente 8 000 puntos. Se calcula una sola vez y además define el rango de los sliders, con un margen extra para poder probar puntos no alcanzables.

### **6. Visualización e interacción**

- **Postura inicial:** la simulación arranca sola con $q_1=0^\circ$, $q_2=45^\circ$, $q_3=0^\circ$, que corresponde a $P_3=(368.32,\;0,\;91.03)$ mm.
- **Figura:** se dibujan la base, los cinco eslabones del mecanismo, el sistema de referencia $X_3Y_3Z_3$ en la muñeca, el punto objetivo y la nube del espacio de trabajo.
- **Actualización:** la figura se crea una única vez. Al mover un slider solo se actualizan las coordenadas del robot, lo que permite una respuesta en vivo y conserva la vista de la cámara.
- **Panel de resultados:** si el punto es alcanzable, muestra $q_1$, $q_2$, $q_3$, $q_{3O}$, $\gamma_4$, $\mu$, la inclinación de $l_3$ ($q_2+q_{3O}$) y el error de posición.
- **Punto no alcanzable:** se ocultan los eslabones, el objetivo se marca con una ✕ roja y se muestra el motivo.

### **7. Validación**

- **Consistencia directa–inversa:** se realizó la prueba directa → inversa → directa sobre miles de configuraciones aleatorias, y siempre se recuperan los ángulos originales con error del orden de $10^{-13}$ mm.
- **Comparación con la Entrega 3:** los resultados coinciden con el modelo de la Entrega 3. La única diferencia es que esta versión descarta, a propósito, las posturas con ángulo de transmisión menor a $15^\circ$.

### **Limitación**

El robot posee 3 grados de libertad, por lo que solo puede imponerse la posición de $P_3$. La orientación del efector queda determinada por la inclinación $q_2+q_{3O}$ y no puede elegirse de forma independiente, en nuestro caso sería horizontal paralelo al palno XY.


```python
# @title
# =============================================================================
# CINEMÁTICA INVERSA con SLIDERS (x, y, z) — Robot con 4 barras
# =============================================================================
import numpy as np
import plotly.graph_objects as go
import ipywidgets as widgets
from IPython.display import display

try:
    from google.colab import output
    output.enable_custom_widget_manager()
except Exception:
    pass

# -----------------------------------------------------------------------------
# PARÁMETROS DEL ROBOT [mm]
# -----------------------------------------------------------------------------
h1  = 150.00    # altura del hombro
l2  = 350.22    # barra verde
l3  = 329.51    # barra azul (articulación superior B -> muñeca P3)
l4  = 338.00    # barra amarilla (acoplador)
l30 = 40.00     # balancín de entrada (rojo)
l31 = 40.00     # balancín de salida (tramo corto del azul)

# Límites articulares [°]
q1_min, q1_max = -75.0, 75.0
q2_min, q2_max = -25.0, 135.0
q3_min, q3_max = -50.0, 50.0
gamma4_min, gamma4_max = -180.0, 0.0   # rama física: la roja no cruza la verde
                                       # (equivale a cos(q2+q3) > 0 de la Entrega 3)
mu_min = 15.0                          # ángulo de transmisión mínimo [°]

TOL_POS = 1e-4

# Convenciones (las mismas de la Entrega 3):
#   q2 : barra verde medida desde la horizontal +r (lado de la muñeca)
#   q3 : barra roja, ángulo absoluto theta_i = 90° - q3
#   gamma4 = q2 + q3 - 90° ;  q3O = alpha4 - beta4


def norm_ang(a):
    return np.arctan2(np.sin(a), np.cos(a))


def en_rango(q_rad, qmin, qmax):
    return qmin - 1e-9 <= np.degrees(q_rad) <= qmax + 1e-9


# -----------------------------------------------------------------------------
# CUATRO BARRAS
# -----------------------------------------------------------------------------
def cuatro_barras_directo(gamma4):
    """gamma4 -> (q3O, mu). None si el mecanismo no cierra."""
    L = np.sqrt(l2**2 + l30**2 - 2*l2*l30*np.cos(gamma4))
    c = (L**2 + l31**2 - l4**2) / (2*l31*L)
    if abs(c) > 1:
        return None
    alpha4 = np.arctan2(l30*np.sin(gamma4), l2 - l30*np.cos(gamma4))
    beta4 = np.arccos(c)
    mu = np.arccos(np.clip((l31**2 + l4**2 - L**2) / (2*l31*l4), -1, 1))
    return alpha4 - beta4, mu


def cuatro_barras_inverso(q30):
    """q3O -> lista de gamma4 candidatos: -(delta ± epsilon)."""
    psi = -q30
    e = np.sqrt(l2**2 + l31**2 - 2*l2*l31*np.cos(psi))
    c = (e**2 + l30**2 - l4**2) / (2*l30*e)
    if abs(c) > 1:
        return []
    delta = np.arctan2(l31*np.sin(psi), l2 - l31*np.cos(psi))
    eps = np.arccos(c)
    return [-(delta + eps), -(delta - eps)]


# -----------------------------------------------------------------------------
# CINEMÁTICA DIRECTA
# -----------------------------------------------------------------------------
def cinematica_directa(q1, q2, q3):
    res = cuatro_barras_directo(q2 + q3 - np.pi/2)
    if res is None:
        return None
    q30, mu = res
    th = q2 + q30
    r = l2*np.cos(q2) + l3*np.cos(th)
    P = np.array([r*np.cos(q1), r*np.sin(q1), h1 + l2*np.sin(q2) + l3*np.sin(th)])
    return P, q30, mu


def config_valida(q1, q2, q3, mu):
    gamma4 = norm_ang(q2 + q3 - np.pi/2)
    return (en_rango(q1, q1_min, q1_max) and en_rango(q2, q2_min, q2_max) and
            en_rango(q3, q3_min, q3_max) and en_rango(gamma4, gamma4_min, gamma4_max) and
            mu_min <= np.degrees(mu) <= 180 - mu_min)


# -----------------------------------------------------------------------------
# CINEMÁTICA INVERSA  (devuelve soluciones y, si no hay, los motivos)
# -----------------------------------------------------------------------------
def cinematica_inversa(x, y, z):
    soluciones, motivos = [], []
    r = np.hypot(x, y)
    zp = z - h1
    dist = np.hypot(r, zp)

    # Paso 1: q1
    q1 = np.arctan2(y, x) if r > 1e-10 else 0.0
    if not en_rango(q1, q1_min, q1_max):
        motivos.append(f"q1 = {np.degrees(q1):.1f}° fuera de [{q1_min:.0f}°, {q1_max:.0f}°]")

    # Paso 2: q3O (codo equivalente)
    c30 = (r**2 + zp**2 - l2**2 - l3**2) / (2*l2*l3)
    if c30 > 1 + 1e-9:
        return [], [f"Demasiado lejos: distancia al hombro {dist:.1f} mm > "
                    f"l2 + l3 = {l2 + l3:.1f} mm"]
    if c30 < -1 - 1e-9:
        return [], [f"Demasiado cerca: distancia al hombro {dist:.1f} mm < "
                    f"|l2 - l3| = {abs(l2 - l3):.1f} mm"]
    q30_abs = np.arccos(np.clip(c30, -1, 1))

    for q30 in (-q30_abs, q30_abs):
        rama = f"rama q3O = {np.degrees(q30):+.1f}°"
        # Paso 3: q2
        q2 = norm_ang(np.arctan2(zp, r) - np.arctan2(l3*np.sin(q30), l2 + l3*np.cos(q30)))
        if not en_rango(q2, q2_min, q2_max):
            motivos.append(f"{rama}: q2 = {np.degrees(q2):.1f}° fuera de "
                           f"[{q2_min:.0f}°, {q2_max:.0f}°]")
            continue
        # Paso 4: invertir el 4 barras
        gammas = cuatro_barras_inverso(q30)
        if not gammas:
            motivos.append(f"{rama}: el cuatro barras no puede dar ese q3O")
            continue
        for gamma4 in gammas:
            # Paso 5: q3
            q3 = norm_ang(gamma4 - q2 + np.pi/2)
            # Paso 6: verificación
            fk = cinematica_directa(q1, q2, q3)
            if fk is None or np.linalg.norm(fk[0] - [x, y, z]) > TOL_POS:
                continue          # pertenece a la otra rama de ensamble
            P, q30_fk, mu = fk
            if not en_rango(q3, q3_min, q3_max):
                motivos.append(f"{rama}: q3 = {np.degrees(q3):.1f}° fuera de "
                               f"[{q3_min:.0f}°, {q3_max:.0f}°]")
            elif not en_rango(norm_ang(gamma4), gamma4_min, gamma4_max):
                motivos.append(f"{rama}: γ4 = {np.degrees(gamma4):.1f}° (la roja cruzaría la verde)")
            elif not (mu_min <= np.degrees(mu) <= 180 - mu_min):
                motivos.append(f"{rama}: ángulo de transmisión {np.degrees(mu):.1f}° "
                               f"(cerca de punto muerto)")
            elif en_rango(q1, q1_min, q1_max):
                soluciones.append(dict(q1=q1, q2=q2, q3=q3, q30=q30_fk, gamma4=gamma4, mu=mu,
                                       P=P, err=np.linalg.norm(P - [x, y, z])))
    soluciones.sort(key=lambda s: abs(s["q3"]))
    return soluciones, (motivos or ["Sin solución con los límites actuales"])


# -----------------------------------------------------------------------------
# PUNTOS DEL ROBOT
# -----------------------------------------------------------------------------
def puntos_robot(q1, q2, q3, q30):
    u = np.array([np.cos(q1), np.sin(q1), 0.0])
    k = np.array([0.0, 0.0, 1.0])
    p = lambda rr, zz: rr*u + zz*k
    th = q2 + q30
    O = np.zeros(3)
    A = p(0, h1)
    B = A + p(l2*np.cos(q2), l2*np.sin(q2))
    C = A + p(l30*np.cos(np.pi/2 - q3), l30*np.sin(np.pi/2 - q3))
    D = B - p(l31*np.cos(th), l31*np.sin(th))
    P3 = B + p(l3*np.cos(th), l3*np.sin(th))
    return O, A, B, C, D, P3


def marco_P3(q1, th):
    X3 = np.array([np.cos(th)*np.cos(q1), np.cos(th)*np.sin(q1), np.sin(th)])
    Y3 = np.array([-np.sin(th)*np.cos(q1), -np.sin(th)*np.sin(q1), np.cos(th)])
    return np.column_stack([X3, Y3, np.cross(X3, Y3)])


# -----------------------------------------------------------------------------
# ESPACIO DE TRABAJO (vectorizado: se calcula una sola vez, en milisegundos)
# -----------------------------------------------------------------------------
def espacio_trabajo(n=12000, semilla=1):
    rng = np.random.default_rng(semilla)
    q1 = np.radians(rng.uniform(q1_min, q1_max, n))
    q2 = np.radians(rng.uniform(q2_min, q2_max, n))
    q3 = np.radians(rng.uniform(q3_min, q3_max, n))
    g4 = norm_ang(q2 + q3 - np.pi/2)
    L = np.sqrt(l2**2 + l30**2 - 2*l2*l30*np.cos(g4))
    c = (L**2 + l31**2 - l4**2) / (2*l31*L)
    mu = np.degrees(np.arccos(np.clip((l31**2 + l4**2 - L**2) / (2*l31*l4), -1, 1)))
    ok = ((np.abs(c) <= 1) & (np.degrees(g4) >= gamma4_min) & (np.degrees(g4) <= gamma4_max)
          & (mu >= mu_min) & (mu <= 180 - mu_min))
    q1, q2, g4, c = q1[ok], q2[ok], g4[ok], c[ok]
    q30 = np.arctan2(l30*np.sin(g4), l2 - l30*np.cos(g4)) - np.arccos(c)
    th = q2 + q30
    r = l2*np.cos(q2) + l3*np.cos(th)
    return np.column_stack([r*np.cos(q1), r*np.sin(q1), h1 + l2*np.sin(q2) + l3*np.sin(th)])


W = espacio_trabajo()
print(f"Puntos del espacio de trabajo: {len(W)}")

# -----------------------------------------------------------------------------
# FIGURA: se crea UNA sola vez; al mover los sliders solo se actualizan
# las coordenadas de las barras (no se vuelve a dibujar la nube de puntos)
# -----------------------------------------------------------------------------
BARRAS = [("Base O-A", "#e8553f"), ("l2 (verde)", "#2ecc71"), ("l30 (roja)", "#e74c3c"),
          ("l4 (amarilla)", "#f1c40f"), ("l31 (azul corto)", "#00bcd4"), ("l3 (azul)", "#3f51b5")]
PARES = [(0, 1), (1, 2), (1, 3), (3, 4), (4, 2), (2, 5)]     # índices de O,A,B,C,D,P3
N_NUBE, N_BARRAS, N_MARCO = 1, len(BARRAS), 3
I_OBJ = N_NUBE + N_BARRAS + N_MARCO
pad = 60


def figura_base():
    trazas = [go.Scatter3d(x=W[:, 0], y=W[:, 1], z=W[:, 2], mode="markers",
                           marker=dict(size=1.5, color="royalblue", opacity=0.15),
                           name="Espacio de trabajo", hoverinfo="skip")]
    for nom, col in BARRAS:
        trazas.append(go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, 0], mode="lines+markers", name=nom,
                                   line=dict(color=col, width=8), marker=dict(size=3, color=col)))
    for eje, col in zip("XYZ", ["red", "green", "blue"]):
        trazas.append(go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, 0], mode="lines", name=f"{eje}3",
                                   line=dict(color=col, width=5)))
    trazas.append(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers", name="Objetivo",
                               marker=dict(size=6, color="yellowgreen", symbol="diamond")))
    lay = go.Layout(
        title="Cinemática inversa — solución articular y robot",
        width=820, height=680, margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(itemsizing="constant"), uirevision="fijo",   # mantiene la cámara
        scene=dict(xaxis=dict(title="X [mm]", range=[W[:, 0].min()-pad, W[:, 0].max()+pad]),
                   yaxis=dict(title="Y [mm]", range=[W[:, 1].min()-pad, W[:, 1].max()+pad]),
                   zaxis=dict(title="Z [mm]", range=[W[:, 2].min()-pad, W[:, 2].max()+pad]),
                   aspectmode="data", camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8))))
    return trazas, lay


def aplicar_solucion(fig, x, y, z, sol):
    """Modifica solo los datos de las trazas del robot / objetivo."""
    tr = fig.data
    if sol is not None:
        pts = puntos_robot(sol["q1"], sol["q2"], sol["q3"], sol["q30"])
        for i, (a, b) in enumerate(PARES):
            t = tr[N_NUBE + i]
            t.update(x=[float(pts[a][0]), float(pts[b][0])],
                     y=[float(pts[a][1]), float(pts[b][1])],
                     z=[float(pts[a][2]), float(pts[b][2])], visible=True)
        P3 = pts[5]
        R = marco_P3(sol["q1"], sol["q2"] + sol["q30"])
        for i in range(3):
            t = tr[N_NUBE + N_BARRAS + i]
            fin = P3 + 55*R[:, i]
            t.update(x=[float(P3[0]), float(fin[0])], y=[float(P3[1]), float(fin[1])],
                     z=[float(P3[2]), float(fin[2])], visible=True)
        obj = tr[I_OBJ]
        obj.marker.color, obj.marker.symbol, obj.marker.size = "yellowgreen", "diamond", 6
        obj.name = "Objetivo"
        fig.layout.title.text = "Cinemática inversa — solución articular y robot"
    else:
        for i in range(N_NUBE, I_OBJ):
            tr[i].visible = False
        obj = tr[I_OBJ]
        obj.marker.color, obj.marker.symbol, obj.marker.size = "red", "x", 8
        obj.name = "Objetivo NO alcanzable"
        fig.layout.title.text = "❌ Punto NO alcanzable"
    tr[I_OBJ].update(x=[float(x)], y=[float(y)], z=[float(z)])


# Postura inicial: la figura se CONSTRUYE ya con el robot dibujado, para que el
# navegador reciba desde el inicio las coordenadas correctas de todas las barras.
P0 = cinematica_directa(0.0, np.radians(45), 0.0)[0]
sols0, motivos0 = cinematica_inversa(*P0)
trazas, lay = figura_base()
fig0 = go.Figure(data=trazas, layout=lay)
aplicar_solucion(fig0, *P0, sols0[0] if sols0 else None)
trazas, lay = fig0.data, fig0.layout

# Modo rápido (FigureWidget). Si Colab no lo soporta, se usa fig.show().
try:
    fig = go.FigureWidget(data=trazas, layout=lay)
    MODO_RAPIDO = True
except Exception:
    # plotly >= 6 necesita 'anywidget' para FigureWidget: se intenta instalar
    try:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anywidget"],
                       check=True, capture_output=True)
        fig = go.FigureWidget(data=trazas, layout=lay)
        MODO_RAPIDO = True
    except Exception:
        fig = go.Figure(data=trazas, layout=lay)
        MODO_RAPIDO = False
        salida = widgets.Output()
print("Modo de actualización:", "rápido (FigureWidget)" if MODO_RAPIDO else "estándar (fig.show)")

# -----------------------------------------------------------------------------
# TEXTO DE ESTADO
# -----------------------------------------------------------------------------
estado = widgets.HTML(layout=widgets.Layout(width="520px", padding="0 0 0 20px"))


def texto_estado(x, y, z, sols, motivos):
    if not sols:
        lista = "".join(f"<li>{m}</li>" for m in motivos)
        return (f"<b style='color:#d93025'>❌ No se puede alcanzar el punto "
                f"({x:.1f}, {y:.1f}, {z:.1f}) mm</b><br>"
                f"<b>Motivo:</b><ul style='margin:4px 0'>{lista}</ul>")
    s = sols[0]
    d = np.degrees
    return f"""
    <b style='color:#137333'>✔ Punto alcanzable</b> — soluciones válidas: {len(sols)}<br>
    <b>q1:</b> {d(s['q1']):.3f}° &nbsp;&nbsp; <b>q2:</b> {d(s['q2']):.3f}° &nbsp;&nbsp;
    <b>q3:</b> {d(s['q3']):.3f}°<br>
    <b>q3O:</b> {d(s['q30']):.3f}° &nbsp;&nbsp; <b>γ4:</b> {d(s['gamma4']):.2f}° &nbsp;&nbsp;
    <b>μ (transmisión):</b> {d(s['mu']):.1f}°<br>
    <b>Inclinación de l3 (q2+q3O):</b> {d(s['q2'] + s['q30']):.2f}°<br>
    <b>Error de posición:</b> {s['err']:.3e} mm"""


# -----------------------------------------------------------------------------
# SLIDERS
# -----------------------------------------------------------------------------
margen = 60.0   # permite salir del espacio de trabajo para ver el aviso


def crear_slider(valor, vmin, vmax, nombre):
    return widgets.FloatSlider(value=round(float(valor), 2), min=float(np.floor(vmin)),
                               max=float(np.ceil(vmax)), step=1.0, description=nombre,
                               continuous_update=MODO_RAPIDO,   # en vivo si es rápido
                               readout_format=".2f", style={"description_width": "55px"},
                               layout=widgets.Layout(width="360px"))


slider_x = crear_slider(P0[0], W[:, 0].min() - margen, W[:, 0].max() + margen, "x [mm]")
slider_y = crear_slider(P0[1], W[:, 1].min() - margen, W[:, 1].max() + margen, "y [mm]")
slider_z = crear_slider(P0[2], W[:, 2].min() - margen, W[:, 2].max() + margen, "z [mm]")


def actualizar(change=None):
    x, y, z = slider_x.value, slider_y.value, slider_z.value
    sols, motivos = cinematica_inversa(x, y, z)
    estado.value = texto_estado(x, y, z, sols, motivos)
    sol = sols[0] if sols else None
    if MODO_RAPIDO:
        with fig.batch_update():          # un solo mensaje al navegador
            aplicar_solucion(fig, x, y, z, sol)
    else:
        aplicar_solucion(fig, x, y, z, sol)
        with salida:
            salida.clear_output(wait=True)
            fig.show()


for s in (slider_x, slider_y, slider_z):
    s.observe(actualizar, names="value")

controles = widgets.VBox([widgets.HTML("<b>Posición deseada</b>"), slider_x, slider_y, slider_z])
# Primero se muestra la interfaz (la figura ya trae la postura inicial) y recién
# después se permiten actualizaciones: así el navegador no pierde ningún cambio.
estado.value = texto_estado(*P0, sols0, motivos0)
display(widgets.VBox([widgets.HBox([controles, estado]), fig if MODO_RAPIDO else salida]))
if not MODO_RAPIDO:
    actualizar()
```

## **3. Referencias**

**[1]** Tao, Y., Chen, F., & Xiong, H. (2014). Kinematics and workspace of a 4-DOF hybrid palletizing robot. *Advances in Mechanical Engineering, 6*, 1–11. https://doi.org/10.1155/2014/125973

**[2]** Nguyen, T. P., Nguyen, H., & Ngo, T. (2024). Design and implementation of a field robot using a parallelogram mechanism. *Science Progress*. https://doi.org/10.1177/00368504241291124

**[3]** Gebel, E. S., & Chigrinova, E. A. (2020). Approximate kinematic synthesis of the four-bar mechanism by two given positions of the links. *Journal of Physics: Conference Series, 1546*, 012129. https://doi.org/10.1088/1742-6596/1546/1/012129

**[4]** *Cinemática directa de un robot con mecanismo de cuatro barras* [Video]. YouTube. https://www.youtube.com/watch?v=5PMPBbH0f7o

