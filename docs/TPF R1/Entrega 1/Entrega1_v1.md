---
**UNIVERSIDAD NACIONAL DE ASUNCIÓN**

**FACULTAD DE INGENIERÍA**

# **ROBOTICA I**

TRABAJO PRÁCTICO FINAL 2026S2

## **"Robot móvil recogedor de frutas"**


---
---
###**ESTACIÓN [2]:** [Robot móvil recogedor de frutas]
**Grupo [2]:**


*   Pablo Junior Otazu Lujan
*   Gabriela Belén Orrego Arzamendia
*   Héctor Dejesús Velázquez Ojeda
*   Mathias Ramón Aguilar Delvalle


**ENTREGA [1]:** Definición de morfología y arquitectura del robot

**Fecha:** 18/08/2026

**Versión:** [v1.0]

### **1. Aplicación y tarea del robot gupo [2]**

---



#### **1.1. Descripción**

Este proyecto aborda el diseño e implementación de un sistema robótico para la recolección autónoma de limones. La arquitectura propuesta integra los siguientes elementos principales:

- **Manipulador robótico de configuración $4R$**, con tres grados de libertad destinados al posicionamiento del efector final y un grado de libertad rotacional integrado en la herramienta.
- **Efector final especializado**, con un grado de libertad adicional para la apertura y cierre de la pinza.
- **Sistema de visión artificial estereoscópica**, destinado a la detección de los frutos y estimación de su posición tridimensional.
- **Plataforma móvil autónoma**, encargada del desplazamiento del sistema dentro del entorno de trabajo.

El sistema dispone de cinco movimientos accionados independientes: cuatro GDL asociados al manipulador 4R y un GDL adicional correspondiente a la apertura y cierre de la pinza.

> **Objetivo principal:** detectar, localizar, sujetar, desprender y depositar limones de manera autónoma, procurando preservar la integridad del fruto durante todo el proceso.

##### **Secuencia general de operación**

<div align="center">

**Detección** $\rightarrow$ **Localización 3D** $\rightarrow$ **Aproximación** $\rightarrow$ **Sujeción** $\rightarrow$ **Tracción** $\rightarrow$ **Torsión** $\rightarrow$ **Retracción** $\rightarrow$ **Clasificación**

</div>

La tarea inicia con la exploración del entorno en busca de frutos. Una vez estimada la posición tridimensional de cada limón, el manipulador aproxima el efector final de manera secuencial.

La fase de extracción se realiza mediante la sujeción del fruto y la aplicación combinada de una tracción de precarga y un movimiento de torsión, con el objetivo de provocar su desprendimiento del tallo.

Finalmente, el manipulador retira el fruto recolectado y lo deposita en el contenedor correspondiente según su tamaño.

---

#### **1.2. Desafíos principales**

El desarrollo del sistema presenta diferentes desafíos asociados a la percepción, manipulación y coordinación de los subsistemas:

<div align="center">

| Desafío | Descripción |
| :--- | :--- |
| **Localización tridimensional** | Determinar la posición espacial $(X,Y,Z)$ de cada limón mediante un sistema de visión estereoscópica compuesto por al menos dos cámaras. |
| **Oclusión** | Detectar y estimar la posición de frutos parcialmente cubiertos por hojas, ramas u otros elementos del entorno. |
| **Alcanzabilidad** | Garantizar que el manipulador pueda acceder a las diferentes posiciones de los frutos dentro del espacio de trabajo establecido. |
| **Preservación del fruto** | Aplicar fuerzas de sujeción, tracción y torsión suficientes para desprender el limón sin producir daños o deformaciones significativas. |
| **Precisión de posicionamiento** | Alinear correctamente el efector final con el fruto para realizar la sujeción y ejecutar posteriormente los movimientos de extracción. |
| **Coordinación visión-robot** | Transformar las coordenadas tridimensionales obtenidas por las cámaras al sistema de referencia utilizado por el manipulador. |
| **Clasificación** | Determinar el tamaño del fruto recolectado y depositarlo en el contenedor correspondiente. |

</div>

Estos desafíos condicionan tanto la morfología del manipulador como la arquitectura de percepción, control y navegación propuesta para el sistema.



<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1OVAFp71FxOCmWnn2QRQI1EwOglBVOpQq" width="500" />
  <p><b>Fig. 1.</b> Esquema general del sistema robótico propuesto para la recolección autónoma de limones.</p>
</div>

---



### **2. Morfología del Robot**
---
#### **2.1. Configuración general**

Para el desarrollo del proyecto se propone un manipulador articulado de cuatro articulaciones rotativas ($4R$).

El robot presenta un diseño basado en un mecanismo de paralelogramo articulado, cuya geometría permite mantener de forma pasiva una orientación vertical constante de la plataforma del efector final respecto a la superficie de la base durante el movimiento del brazo. De esta manera, no se requiere un actuador adicional para corregir activamente la inclinación de la herramienta [1].

Las tres primeras articulaciones, asociadas al giro de la base, hombro y codo, determinan la posición espacial del efector final en las coordenadas $(X,Y,Z)$. Estos movimientos son accionados mediante tres motores DC, empleándose mecanismos de transmisión articulados para transferir el movimiento hacia las articulaciones correspondientes.

La cuarta articulación rotativa ($J_4$) se encuentra integrada en el efector final y permite la rotación de la pinza alrededor de su eje longitudinal. Este movimiento no interviene directamente en el posicionamiento $(X,Y,Z)$, sino que se utiliza durante la etapa de extracción para aplicar el movimiento de torsión necesario para favorecer el desprendimiento del limón.

De acuerdo con la representación cinemática de manipuladores mediante coordenadas articulares, cada grado de libertad independiente puede describirse mediante una variable articular. Para una articulación rotativa, dicha variable corresponde a un desplazamiento angular [3].

Por esta razón, para el análisis cinemático de posición, el manipulador puede considerarse inicialmente como un subsistema de tres articulaciones rotativas ($3R$), correspondientes a $J_1$, $J_2$ y $J_3$, encargado del posicionamiento espacial del efector final. La articulación $J_4$ puede analizarse de forma desacoplada como una variable de orientación axial de la herramienta.

Por tanto, la configuración completa del manipulador es:

$$
\boxed{\text{Manipulador }4R =
3R\text{ de posicionamiento}
+
1R\text{ de orientación}}
$$

Adicionalmente, el efector final incorpora un servomotor independiente encargado de la apertura y cierre de la pinza. Este movimiento constituye un grado de libertad propio de la herramienta y no se considera una articulación adicional de la cadena cinemática del manipulador.

El vector completo de coordenadas articulares del manipulador se define como:

$$
\mathbf{q} =
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
\theta_3 \\
\theta_4
\end{bmatrix}
$$

donde $\theta_1$, $\theta_2$ y $\theta_3$ corresponden a las variables articulares utilizadas para el posicionamiento del efector final, mientras que $\theta_4$ representa la rotación axial de la herramienta.

Para el análisis inicial de la cinemática de posición se considera entonces el subconjunto:

$$
\mathbf{q}_p =
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
\theta_3
\end{bmatrix}
$$

mientras que la rotación de la herramienta necesaria durante la extracción del fruto se controla independientemente mediante:

$$
\theta_4
$$

Las articulaciones adicionales presentes físicamente en el mecanismo de paralelogramo son articulaciones pasivas y mecánicamente dependientes. Por lo tanto, no representan grados de libertad independientes y no se incorporan como nuevas variables dentro del vector $\mathbf{q}$.

El manipulador estará instalado sobre un robot móvil con navegación autónoma.

<div align="center">

<img src="https://lh3.googleusercontent.com/d/1nJq6tX_8saN1c2WGkJyGATK6oF-47FK0" width="500" />

<p><b>Fig. 2.</b> Modelo digital 3D de un manipulador robótico articulado basado en un sistema de paralelogramos mecánicos.</p>

</div>

| Articulación / Actuador | Tipo | Función |
| :--- | :--- | :--- |
| **$J_1$** | Rotativa | Rotación de la base |
| **$J_2$** | Rotativa | Movimiento del primer eslabón |
| **$J_3$** | Rotativa | Movimiento del segundo eslabón |
| **$J_4$** | Rotativa | Rotación axial de la pinza para aplicar torsión al fruto |
| **Pinza** | Apertura / cierre | Sujeción y liberación del limón |
| **Paralelogramo** | Pasivo | Mantener la orientación de la plataforma del efector final |
---

#### **2.2. Dimensiones preliminares**

Las dimensiones preliminares del manipulador fueron definidas a partir del alcance requerido para la tarea de recolección. En particular, se busca obtener un alcance radial máximo aproximado de 650 mm, de manera que el efector final pueda acceder a los frutos ubicados dentro de la zona de trabajo prevista.

Para ello se adoptaron inicialmente las siguientes dimensiones:

<div align="center">

| Longitud | Medida |
| :--- | :--- |
| **$L_1$** | 150 mm |
| **$L_2$** | 300 mm |
| **$L_3$** | 300 mm |
| **$L_T$** | ≈ 50 mm |

</div>

En esta configuración, $L_1$ corresponde a la distancia vertical entre la base del robot y la primera articulación del brazo, mientras que $L_2$ y $L_3$ representan las longitudes de los dos eslabones principales del manipulador. Por su parte, $L_T$ representa la distancia aproximada desde la última articulación hasta el punto de operación de la herramienta (TCP).

El parámetro $L_1$ determina principalmente la elevación inicial del mecanismo y no contribuye directamente al alcance radial máximo del brazo.

En una configuración completamente extendida, el alcance radial teórico puede aproximarse mediante:

$$
R_{\max} \approx L_2 + L_3 + L_T
$$

por lo que:

$$
R_{\max} \approx 300 + 300 + 50 = 650\text{ mm}
$$

Este valor representa una estimación geométrica preliminar. El alcance real estará condicionado por los límites angulares de las articulaciones, la geometría del mecanismo de paralelogramos, las dimensiones físicas de las piezas y las posibles interferencias mecánicas.

Por lo tanto, las dimensiones propuestas constituyen una primera aproximación y serán verificadas posteriormente mediante el análisis cinemático y la evaluación del espacio de trabajo del manipulador.
<div align="center">
  <img src="https://lh3.googleusercontent.com/d/1cPRrMDnqTlz1GtGvk1PLE19BAGx1aWOW" width="500" />
  <p><b>Fig. 3.</b> Dimensiones principales del manipulador RRR.</p>
</div>


---
#### **2.3. Diseño mecánico preliminar**

Partiendo de la configuración cinemática y las dimensiones establecidas, se desarrolló un modelo mecánico preliminar en SolidWorks con el fin de evaluar la disposición de los eslabones, las articulaciones y el mecanismo de paralelogramos.

El modelo constituye una primera aproximación geométrica del manipulador y será utilizado posteriormente para verificar el rango de movimiento, las interferencias mecánicas y la disposición de los actuadores y elementos estructurales.

<br>

<div align="center">

  <img src="https://lh3.googleusercontent.com/d/17IUc7jgzLv53_FPtIxN9IcOiOrplFCyO" width="650">

  <p>
    <b>Fig. 4.</b> Vista isométrica del diseño mecánico preliminar del manipulador.
  </p>

</div>

<br>

<div align="center">

  <img src="https://lh3.googleusercontent.com/d/1RskQEpKGJIZI6gLIjSuCAfK0jCmLQ6HR" width="650">

  <p>
    <b>Fig. 5.</b> Vista lateral del diseño mecánico preliminar del manipulador.
  </p>

</div>

<br>

Por medio de las vistas se puede observar la configuración general del mecanismo, la ubicación de los actuadores en la base y la disposición preliminar de los eslabones empleados para transmitir el movimiento hacia las articulaciones superiores.

##### **2.3.1. Ventajas**
* Reducción de masa en los eslabones móviles.
* Menor inercia respecto a una configuración con motores directamente montados  sobre cada articulación.
* Centro de masa concentrado cerca de la base.
* Mayor facilidad de mantenimiento de motores y electrónica.
* Estructura compacta.
* Configuración adecuada para tareas repetitivas de posicionamiento y recolección.
##### **2.3.2. Desventajas**
* Mayor complejidad mecánica debido a los mecanismos de transmisión.
* Aparición de holguras en articulaciones y transmisiones.
* Mayor dificultad de fabricación y montaje.
* Acoplamiento mecánico entre algunos movimientos.
* Necesidad de calibración precisa.
* El espacio de trabajo puede presentar restricciones debido a la geometría del mecanismo.
* Posibles configuraciones singulares.
---

### **3. Arquitectura del sistema**

La arquitectura del sistema robótico se divide en diferentes subsistemas encargados de la movilidad, manipulación, percepción, control y ejecución de la tarea de recolección.

#### **3.1. Manipulador 4R**

Estructura mecánica articulada encargada del posicionamiento y orientación del efector final.

Las tres primeras articulaciones rotativas ($J_1$, $J_2$ y $J_3$) conforman el subsistema de posicionamiento **3R**, encargado de ubicar el efector final en las coordenadas espaciales $(X,Y,Z)$ requeridas dentro del espacio de trabajo.

La cuarta articulación ($J_4$) se encuentra integrada en el efector final y permite la rotación de la pinza alrededor de su eje longitudinal para aplicar el movimiento de torsión durante el desprendimiento del fruto.

El brazo utiliza un mecanismo de paralelogramos articulados, encargado de mantener de forma pasiva la plataforma del efector final en orientación horizontal respecto a la base durante el movimiento del manipulador.

Los tres actuadores principales correspondientes a $J_1$, $J_2$ y $J_3$ son motores DC ubicados en la base del manipulador.

---

#### **3.2. Plataforma móvil autónoma**

Base robótica móvil encargada de transportar el manipulador a través del entorno de trabajo.

El sistema de navegación autónoma permite desplazar y posicionar la plataforma frente a los árboles, proporcionando una ubicación adecuada desde la cual el manipulador pueda alcanzar los frutos detectados.

La plataforma deberá considerar funciones de localización, planificación de trayectoria y detección de obstáculos durante el desplazamiento.

---

#### **3.3. Efector final**

Mecanismo especializado encargado de la sujeción y desprendimiento del limón.

El efector final incorpora dos actuadores independientes:

* **Servo de prensión:** encargado de la apertura y cierre de la pinza.
* **Servo rotacional:** encargado del giro de toda la pinza alrededor de su eje longitudinal para aplicar torsión al fruto.

La secuencia prevista para la extracción es:

* **Aproximación:** posicionamiento del efector final frente al fruto.
* **Sujeción:** cierre controlado de la pinza sobre el limón.
* **Precarga:** generación de una leve tracción mediante el movimiento de retracción del manipulador.
* **Torsión:** rotación de la pinza mediante $J_4$ para favorecer el desprendimiento del fruto.
* **Retracción:** retiro del manipulador transportando el fruto hacia la zona de almacenamiento.
* **Liberación:** apertura de la pinza para depositar el limón en el contenedor correspondiente.

<div align="center">

**Aproximación** $\rightarrow$ **Sujeción** $\rightarrow$ **Precarga** $\rightarrow$ **Torsión** $\rightarrow$ **Retracción** $\rightarrow$ **Liberación**

</div>

---

#### **3.4. Sistema de visión artificial**

Módulo de percepción basado en un sistema de visión estereoscópica encargado de capturar imágenes del entorno, detectar los limones y estimar su posición tridimensional.

Las coordenadas obtenidas inicialmente respecto al sistema de referencia de las cámaras deberán transformarse al sistema de referencia de la base del manipulador mediante un proceso de calibración.

De esta manera, cada fruto detectado podrá representarse mediante una posición objetivo:

$$
P_f =
\begin{bmatrix}
X_f \\
Y_f \\
Z_f
\end{bmatrix}
$$

que será utilizada posteriormente por el sistema de control para calcular la configuración articular necesaria.

---

#### **3.5. Sistema de control**

Subsistema encargado de coordinar los movimientos del manipulador y ejecutar las referencias generadas a partir de la posición de los frutos detectados.

Para las articulaciones principales accionadas mediante motores DC se implementará control en lazo cerrado utilizando la realimentación de posición proporcionada por los sensores de cada articulación.

El sistema de control comprende principalmente:

* cálculo de cinemática directa e inversa;
* generación de referencias articulares;
* control de posición de $J_1$, $J_2$ y $J_3$;
* control de la rotación $J_4$;
* control de apertura y cierre de la pinza;
* generación de trayectorias de aproximación, extracción y depósito.

---

#### **3.6. Sistema de comunicación**

Infraestructura encargada del intercambio de información entre los diferentes subsistemas del robot.

Permite transmitir datos entre el sistema de visión artificial, el controlador principal, los controladores de los actuadores, los sensores del manipulador y la plataforma móvil.

Entre la información intercambiada se encuentran las coordenadas de los frutos detectados, referencias articulares, posiciones medidas, estados de los actuadores y señales de supervisión del sistema.

---

#### **3.7. Sistema de alimentación**

Subsistema encargado de proporcionar los niveles de tensión y corriente requeridos por los motores DC, servomotores, sistema de control, sistema de visión y demás componentes electrónicos.

La alimentación deberá dimensionarse teniendo en cuenta principalmente las demandas máximas de corriente producidas durante el movimiento simultáneo de los actuadores y durante las operaciones de sujeción y torsión del fruto.

---

#### **3.8. Sistema de supervisión y seguridad**

Subsistema destinado a supervisar el estado general del robot y evitar movimientos que puedan producir daños en el mecanismo, el entorno o los componentes del sistema.

Se consideran elementos como límites de movimiento de las articulaciones, detección de posiciones extremas, supervisión de los actuadores y procedimientos de detención ante condiciones atípicas.

---

### **4. Arquitectura lógica**
<div align="center">
<img src="https://lh3.googleusercontent.com/d/1GTCsY_giOg5_ZIYgHKqmP0pxebAEKe2f" width="800" />
<p><a href="https://drive.google.com/drive/folders/1EfOoqCBUAYVX5_8i3AinIIrnWdG7-EkG?hl=es" target="_blank"><b>Fig. 6.</b></a> Diagrama de la arquitectura lógica del robot recogedor de frutas.</p>
</div>

---

### **5.Funcionamiento lógico**
<div align="center">
  <img src="https://lh3.googleusercontent.com/d/17_memu5qNhNlXPq-0i2_pVEY16AfB-L8" width="800" />
  <p><a href="https://drive.google.com/drive/folders/1EfOoqCBUAYVX5_8i3AinIIrnWdG7-EkG?hl=es" target="_blank"><b>Fig. 7.</b></a> Diagrama de flujo de los componentes lógicos.</p>
</div>

---

### **6. Referencias**



[1] V. D. Cong, D. A. Duy and L. H. Phuong,
“Design and Fabrication of 3-DOF Robot Arm Using Parallelogram Mechanisms,”
*International Journal of Emerging Trends in Engineering Research*,
vol. 9, no. 9, pp. 1224–1229, 2021.  
DOI: [10.30534/ijeter/2021/03992021](https://doi.org/10.30534/ijeter/2021/03992021)

[2] S. S. Mehta and T. F. Burks,
“Vision-based control of robotic manipulator for citrus harvesting,”
*Computers and Electronics in Agriculture*,
vol. 102, pp. 146–158, 2014.  
DOI: [10.1016/j.compag.2014.01.003](https://doi.org/10.1016/j.compag.2014.01.003)

[3] A. Barrientos, L. F. Peñín, C. Balaguer y R. Aracil,
*Fundamentos de Robótica*, 2.ª ed.,
Madrid, España: McGraw-Hill, 2007.

---
### **7. Carpeta del proyecto grupo 2**
En el link se encuentra la carpeta del proyecto.
[TPF R1 Grupo 2](https://drive.google.com/drive/folders/1d2jONLnkB8FMkP2iqF4ia4UeQ2jRpffz)

---
