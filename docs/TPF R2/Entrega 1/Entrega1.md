```python

```

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

**ENTREGA [1]:** [Diagrama, selección de componentes y pruebas de sensores.
]

**Fecha:** [30/08/2026]

**Versión:** [1.0]

---

### **1. Introducción**

La recolección de frutas constituye una etapa importante dentro del proceso de producción agrícola y tradicionalmente requiere una cantidad considerable de tiempo y mano de obra. En cultivos frutícolas, la automatización mediante sistemas robóticos permite integrar locomoción, percepción, navegación y manipulación para realizar tareas de identificación, localización y recolección de frutos [[1]](https://doi.org/10.1007/978-3-030-70400-1).

Los robots recolectores modernos pueden incorporar plataformas móviles, sistemas de visión artificial, sensores de navegación, brazos robóticos y efectores finales. Mediante estos elementos es posible detectar frutos, estimar su posición y controlar el manipulador para realizar la cosecha de manera selectiva [[1]](https://doi.org/10.1007/978-3-030-70400-1), [[2]](https://doi.org/10.1007/s10462-023-10674-2).

Para el presente TPF se propone el desarrollo de un robot móvil autónomo basado en ROS 2 destinado a la recolección de limones. El sistema integrará navegación, percepción, localización, detección de obstáculos y un manipulador robótico encargado de localizar, sujetar y recolectar los frutos. [[4]](https://doi.org/10.1016/j.compag.2025.110131).


La recolección automática de frutas busca disminuir el trabajo manual requerido durante la cosecha y aumentar la eficiencia del proceso. Para ello, los robots recolectores combinan sistemas de percepción, control y manipulación capaces de identificar y localizar los frutos antes de realizar la operación de cosecha [[2]](https://doi.org/10.1007/s10462-023-10674-2).

En estos sistemas, características visuales como el color, la forma y la textura pueden utilizarse para reconocer los frutos y determinar su estado, mientras que un manipulador y un efector final realizan la aproximación, sujeción y separación del fruto [[2]](https://doi.org/10.1007/s10462-023-10674-2).

Entre los principales desafíos de estos sistemas se encuentran la baja eficiencia de algunos prototipos, el daño producido al fruto, los errores de identificación y localización y el elevado costo asociado a estructuras mecánicas complejas [[2]](https://doi.org/10.1007/s10462-023-10674-2).

El entorno agrícola presenta además condiciones variables de iluminación, hojas, ramas, frutos parcialmente ocultos y obstáculos que dificultan el funcionamiento de los sistemas de visión artificial y la aproximación del manipulador [[2]](https://doi.org/10.1007/s10462-023-10674-2).

En robots destinados a cítricos también deben considerarse las variaciones en tamaño, posición y orientación del fruto, así como la necesidad de realizar su separación sin producir daños [[2]](https://doi.org/10.1007/s10462-023-10674-2).
## **1.3 Modelos de referencia**

Zhang et al. [[2]](https://doi.org/10.1007/s10462-023-10674-2) recopilan diferentes desarrollos de robots destinados a la recolección automática de cítricos. Los sistemas estudiados incorporan principalmente visión artificial, manipuladores robóticos y efectores finales especializados para detectar, localizar y separar los frutos.

Uno de los principales modelos de referencia para este proyecto es el robot desarrollado por Yin et al. [[3]](https://doi.org/10.1002/rob.22178), diseñado específicamente para la recolección autónoma de cítricos en un entorno real de cultivo. El sistema integra navegación autónoma, percepción visual, estimación de la posición del fruto, manipulación y un efector final específico para realizar la cosecha.

Durante las evaluaciones de campo, Yin et al. [[3]](https://doi.org/10.1002/rob.22178) obtuvieron una tasa global de éxito de recolección del 87,2 % y un tiempo promedio de 10,9 s por fruto.

Otros desarrollos recopilados por Zhang et al. [[2]](https://doi.org/10.1007/s10462-023-10674-2) presentan resultados de reconocimiento, posicionamiento y recolección que permiten establecer parámetros de comparación para el diseño del presente robot.
## **1.4 Parámetros de referencia y comparativa**

A partir de los robots recolectores de cítricos analizados en la literatura, pueden considerarse como parámetros de evaluación la tasa de éxito de recolección, el tiempo de recolección, la precisión de posicionamiento, la capacidad de reconocimiento y el desempeño en condiciones reales de cultivo [[2]](https://doi.org/10.1007/s10462-023-10674-2), [[3]](https://doi.org/10.1002/rob.22178).

| Sistema de referencia | Parámetro principal | Resultado |
|:----------------------|:--------------------|:---------:|
| Agri-Tech | Velocidad de recolección | 60 cítricos/min |
| Recolección manual de referencia | Velocidad de recolección | 8 cítricos/min |
| Yin et al. (2023) | Éxito global de recolección | 87,2 % |
| Yin et al. (2023) | Tiempo de recolección | 10,9 s/fruto |
| Yang et al. (2019) | Identificación de madurez | 91,9 % |
| Yang et al. (2019) | Error de posicionamiento | 5,9 mm |
| Yang et al. (2019) | Procesamiento de imagen | 0,4 s |
| Liu et al. (2019) | Tiempo de recolección | 5,4 s/fruto |
| Liu et al. (2019) | Altura máxima de trabajo | 1,85 m |
| Wang et al. (2019) | Éxito de corte del tallo | ≈98 % |
| Wang et al. (2019) | Recolección en ambiente natural | 74 % |
| Yang et al. (2023) | Reconocimiento de cítricos | 98 % |
| Yang et al. (2023) | Éxito promedio de recolección | >90 % |

Los resultados anteriores permiten establecer valores de referencia para comparar posteriormente el desempeño del robot desarrollado en este trabajo.

## **1.5 Requisitos principales del TPF**

De acuerdo con la guía del Trabajo Práctico Final, el robot recogedor deberá contar con una base móvil terrestre, al menos dos ruedas motrices controladas independientemente, encoders, una IMU, un receptor GPS/GNSS y una computadora a bordo capaz de ejecutar ROS 2.

Para la detección de obstáculos se utilizarán al menos tres sensores de distancia y cuatro bumpers como elementos de contacto físico. Además, el sistema deberá incorporar percepción visual y un manipulador de al menos 4 GDL encargado de posicionar el efector final utilizado para sujetar y separar el fruto.







### **2. Arquitectura lógica**

<div align="center">

<img src="https://lh3.googleusercontent.com/d/1GTCsY_giOg5_ZIYgHKqmP0pxebAEKe2f"
     width="800" />

<p>
<a href="https://drive.google.com/drive/folders/1EfOoqCBUAYVX5_8i3AinIIrnWdG7-EkG?hl=es"
   target="_blank">
<b>Fig. 1.</b>
</a>
Diagrama de la arquitectura lógica del robot móvil recolector de frutas.
</p>

</div>

[Ver video: Autonomous Orange Harvesting Robot](https://www.youtube.com/watch?v=qnQ94JFqYZY)

---
### **3. Selección de componentes**

La selección de componentes se realizó considerando los requisitos establecidos para el robot móvil recolector de frutas [5], la compatibilidad con ROS 2, la facilidad de integración entre los diferentes subsistemas y la disponibilidad de los elementos para la construcción del prototipo.

| Componente | Cantidad | Característica / modelo | Función principal |
|:-----------|:--------:|:------------------------|:------------------|
| Raspberry Pi 5 | 1 | Computadora de placa única | Ejecutar ROS 2, navegación, visión artificial y control de alto nivel |
| ESP32 | 1 | Microcontrolador | Lectura de sensores y comunicación mediante micro-ROS |
| Motor DC para brazo | 3 | 12 V, reductora y encoder integrados | Accionar las articulaciones principales del brazo robótico |
| Motor DC de tracción | 2 | 12 V, reductora y encoder integrados | Accionar independientemente las dos ruedas motrices del robot |
| Drivers de motores DC | Según diseño | Driver compatible con motores de 12 V | Controlar sentido y velocidad de los motores DC |
| Servomotores | 2 | Servomotores para efector final | Accionar el mecanismo de apertura y cierre de la pinza |
| Cámaras | 2 | Cámaras compatibles con Raspberry Pi 5 | Detección, clasificación y estimación de la posición de los limones |
| LiDAR | 1 | Modelo por definir | Mapeo del entorno, detección de obstáculos y apoyo a la navegación autónoma |
| IMU | 1 | Unidad de medición inercial | Medir aceleración, velocidad angular, orientación e inclinación del robot |
| GPS/GNSS | 1 | FASTRAX UP501A03 | Obtener la posición absoluta del robot y referenciar el recorrido |
| Sensores ultrasónicos | 3 | HC-SR04 | Medición de distancia y detección de obstáculos a corta distancia |
| Bumpers | 4 | Interruptores mecánicos de contacto | Detectar contacto físico y generar una condición de seguridad |
| Ruedas motrices | 2 | Ruedas acopladas a motores DC | Generar la tracción de la plataforma móvil |
| Ruedas locas | 2 | Ruedas tipo caster | Soportar la parte delantera y permitir libre orientación |
| Adaptadores para transmisión | 3 | Adaptadores/poleas para eje de motor | Acoplar los motores del brazo al sistema de transmisión por correas |
| Correas de transmisión | 3 | Correas para transmisión mecánica | Transmitir el movimiento de los motores hacia las articulaciones del brazo |
| Convertidores Buck DC-DC | Según necesidad | Reguladores reductores de tensión | Obtener las tensiones requeridas por los distintos componentes |
| Batería | 1 | Tensión y capacidad por dimensionar | Alimentación general del robot |
| Monitor de batería | 1 | Medición de tensión y, de ser posible, corriente | Supervisar el nivel de energía disponible |
| Paro de emergencia | 1 | Pulsador tipo seta con enclavamiento | Detener de forma segura locomoción y actuadores |
| Indicador luminoso | 1 | Señal luminosa | Indicar estados de funcionamiento y emergencia |
| Aviso acústico | 1 | Buzzer o dispositivo acústico | Indicar advertencias o estados de emergencia |
| Estructura del brazo robótico | 1 | Diseño propio | Soportar motores, transmisiones, articulaciones y efector final |
| Estructura de la plataforma móvil | 1 | Diseño propio | Soportar brazo, electrónica, sensores, batería y cajas de recolección |
| Efector final | 1 | Pinza de dos dedos con rotación | Sujetar y separar el limón durante la recolección |
| Cajas de recolección | 2 | Recipientes para frutos | Almacenar los frutos recolectados |


---

### **3. Funcionamiento lógico**


<br>
<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1BxCZ9x44HqaawffROH314YclNmr9lHwC"
       width="900">

  <p><b>Fig. 3.</b> Diagrama de flujo de adquisición y publicación de sensores mediante micro-ROS y ROS 2.</p>
</div>

---

## **4. Pruebas preliminares de sensores**

En esta etapa se realizaron pruebas individuales de los sensores requeridos para el robot móvil, verificando su lectura mediante el ESP32 y su publicación en ROS 2 mediante micro-ROS.

#### **4.1 Prueba IMU (MPU)**

Se verificó la lectura de aceleración y orientación de la unidad de medición inercial y su publicación mediante ROS 2.

[![Prueba IMU](https://img.youtube.com/vi/F7Sk3o4YSi8/0.jpg)](https://www.youtube.com/watch?v=F7Sk3o4YSi8)

*Video de la prueba de la unidad de medición inercial.*

---

#### **4.2 Prueba GPS**

Se verificó la recepción de datos del módulo GPS y la lectura de la información de posicionamiento.||

[![Prueba GPS](https://img.youtube.com/vi/FlS_Loo6ezY/0.jpg)](https://www.youtube.com/watch?v=FlS_Loo6ezY)

*Video de la prueba del módulo GPS.*

---

#### **4.3 Prueba de Bumpers**

Se verificó el funcionamiento de los cuatro bumpers de contacto, utilizando:

- `0`: sin contacto.
- `1`: bumper presionado.

[![Prueba Bumpers](https://img.youtube.com/vi/UKhHBwPL9gA/0.jpg)](https://www.youtube.com/watch?v=UKhHBwPL9gA)

*Video de la prueba de los bumpers de contacto.*

---

#### **4.4 Prueba de sensores ultrasónicos**

Se verificó la medición de distancia de los sensores HC-SR04 utilizados para la detección de obstáculos.

[![Prueba sensor ultrasónico](https://img.youtube.com/vi/6wftGRV8lBA/0.jpg)](https://www.youtube.com/watch?v=6wftGRV8lBA)

*Video de la prueba del sensor ultrasónico.*


---

### **5.  Enlaces a evidencias de trabajo**

#### **5.1 Prueba de Sensores**
La lista completa de videos correspondientes a las pruebas realizadas puede consultarse en el siguiente enlace:

[**Lista de reproducción – Pruebas (Entrega 1)**](https://www.youtube.com/playlist?list=PLa3OAG4TCwaY)

#### **5.2 Carpeta de evidencias**





---

### **6. Referencias**
[1] M. Karkee and Q. Zhang, Eds., *Fundamentals of Agricultural and Field Robotics*. Cham, Switzerland: Springer, 2021. doi: [10.1007/978-3-030-70400-1](https://doi.org/10.1007/978-3-030-70400-1).


[2] J. Zhang, N. Kang, Q. Qu, L. Zhou, et al., “Automatic fruit picking technology: a comprehensive review of research advances,” *Artificial Intelligence Review*, vol. 57, art. 54, 2024. doi: [10.1007/s10462-023-10674-2](https://doi.org/10.1007/s10462-023-10674-2).


[3] H. Yin, Q. Sun, X. Ren, J. Guo, Y. Yang, Y. Wei, et al., “Development, integration, and field evaluation of an autonomous citrus-harvesting robot,” *Journal of Field Robotics*, vol. 40, pp. 1363–1387, 2023. doi: [10.1002/rob.22178](https://doi.org/10.1002/rob.22178).

[4] D. W. Choi, J. H. Park, J.-H. Yoo, and K. E. Ko, “AI-driven adaptive grasping and precise detaching robot for efficient citrus harvesting,” *Computers and Electronics in Agriculture*, vol. 232, art. 110131, 2025. doi: [10.1016/j.compag.2025.110131](https://doi.org/10.1016/j.compag.2025.110131).
