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

**ENTREGA [5]:** Selección de sensores y actuadores: Demostración de Control en lazo abierto

**Fecha:** 27/09/2026

**Versión:** [1.0]



# 1. Control de motores en lazo abierto

### 1.1 Objetivo
El objetivo de esta entrega es caracterizar en lazo abierto los dos motores de la estación (el motor base y el de la articulación). La idea es aplicar una señal PWM conocida y medir con el encoder la respuesta del eje de salida sin aplicar ninguna corrección.

A partir de estas mediciones, se busca obtener los parámetros necesarios para diseñar el control en lazo cerrado en la próxima etapa:
- Zona muerta: el PWM mínimo con el que el motor arranca.
- Ganancia estática (K): la relación de rpm por cada % de PWM.
- Constante de tiempo ($\tau$): para el modelo de primer orden $G(s) = \frac{K}{\tau s + 1}$.
- Simetría y efecto de carga: diferencias al girar en ambos sentidos y cómo afecta ponerle peso al eje.

### 1.2 Lazo abierto: ventajas y desventajas
En esta etapa el controlador fija el PWM y no reacciona al resultado. El encoder se usa solo para medir y graficar, no modifica el PWM.
Esto tiene la ventaja de ser muy simple de implementar y sirve como primer paso para identificar el modelo del motor.

Sin embargo, tiene claras desventajas porque no compensa perturbaciones. Como se verá en los resultados, al colocarle carga al motor base con un PWM del 50%, la velocidad cae unas 21 rpm y el PWM necesario para arrancar sube de 16% a 25%. Tampoco compensa la fricción ni la caída de tensión.

---

## 2. Hardware e Instrumental

### 2.1 Esquemas de conexión y componentes

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/15qXoh5R9jUaKUXyrUEdT6ngH3uuWjLBT" width="600" alt="Conexiones del motor base" />
  <br>
  <b>Fig. 1.</b> Esquema de conexiones del motor base (36GP-555 + IBT-2 + ESP32-S3).
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1sJFkEcjoOIgAW_ROkFcfAptEZOwJw4GJ" width="600" alt="Conexiones del motor articulación" />
  <br>
  <b>Fig. 2.</b> Esquema de conexiones del motor de articulación (5840-31ZY + L298N + ESP32-WROOM).
</p>

| Componente | Configuración y especificaciones |
| :--- | :--- |
| **Motor Base** | ESP32-S3 + Driver IBT-2 (PWM a 20 kHz) + Motor 36GP-555 (50:1, encoder Hall en eje motor). |
| **Motor Articulación** | ESP32-WROOM + Driver L298N (PWM a 1 kHz) + Motor 5840-31ZY (sin fin, encoder óptico 1000 PPR / 4000 CPR). |
| **Alimentación** | Fuente de laboratorio a 12 V con límite de corriente en 3 A (base) y 2 A (articulación). |

### 2.2 Consideraciones eléctricas críticas

* **Protección de entradas GPIO:** El encoder óptico (NPN colector abierto) se alimenta con 5 V pero conmuta a GND. El nivel alto lo fijan los *pull-ups* internos del ESP32 a 3.3 V para evitar sobretensiones.
* **Niveles lógicos IBT-2:** $V_{CC}$ del driver conectado a 3.3 V para acople directo con las salidas del ESP32-S3.
* **Control L298N:** Jumper de `ENA` retirado y controlado por GPIO (nivel alto constante) para forzar el modo **Freno**.
---

# 3. Código de control de motores

### 3.1 Organización y estructura
El código está en el repositorio del grupo, organizado con un proyecto de PlatformIO por prueba. Los drivers se implementaron como bibliotecas propias, sin pines fijos ni dependencias de Serial, para poder reutilizarlas directamente en el lazo cerrado.

| Proyecto | Archivo Principal | Contenido y Funcionalidad |
| :--- | :--- | :--- |
| 06-motor-36gp555 | src/main.cpp | Firmware del motor base: modo manual con rampa, barrido, escalón, perfil, conteo de vueltas, protecciones. |
| | lib/BTS7960/ | Driver del IBT-2: duty con signo entre −1 y 1, freno y rueda libre. |
| | lib/EncoderPCNT/ | Encoder en cuadratura x4 por PCNT. |
| | tools/graficar.py | Ejecuta pruebas desde PC, guarda CSV/PNG y calcula K, zona muerta y tau. |
| 07-motor-rampa-vueltas | src/main.cpp y rampa.py | Rampa de PWM que termina a N vueltas; comparación sin carga vs con carga. |
| 08-motor-5840-l298n | src/main.cpp y lib/L298N/ | Mismo firmware y análisis adaptados al L298N y al ESP32 clásico. |



### 3.2 Pines y configuración del motor base (`06-motor-36gp555`)

**Archivo:** `src/motor_config.h` (Asignación de pines)
```cpp
#pragma once

// Placa: Freenove ESP32-S3-WROOM (N16R8) sobre breakout Freenove v1.2.
// Evitar GPIO19/20 (USB nativo) y GPIO26-37 (flash y PSRAM octal del N16R8).
// Pines elegidos para no chocar con el IMU (8/9), el GPS (41/42/47) ni el lidar (14/21),
// así se pueden conectar todos juntos más adelante. GPIO4-7 y 15/16 son de la cámara, que no se usa.

// Driver IBT-2 (doble BTS7960). Su VCC va a 3V3 del ESP32 (ver README).
constexpr int PIN_RPWM = 4;  // PWM del medio puente derecho: motor hacia adelante
constexpr int PIN_LPWM = 5;  // PWM del medio puente izquierdo: motor hacia atrás
constexpr int PIN_R_EN = 6;  // habilitación del medio puente derecho
constexpr int PIN_L_EN = 7;  // habilitación del medio puente izquierdo
// R_IS y L_IS (sensado de corriente) sin conectar.

// Encoder Hall del motor (fases A y B), alimentado con 3V3.
constexpr int PIN_ENC_A = 15;
constexpr int PIN_ENC_B = 16;

**Archivo:** `src/motor_config.h` (Parámetros y límites)


```cpp
constexpr float REDUCCION = 50.0f;
constexpr float ENCODER_PPR = 16.0f;  // pulsos por vuelta del eje del motor, por fase (dato del vendedor)
constexpr float ENCODER_X = 4.0f;     // se cuentan los flancos de subida y bajada de A y de B
constexpr bool ENCODER_INVERTIDO = false;
constexpr uint32_t PWM_FREQ_HZ = 20000;
constexpr uint8_t PWM_BITS = 10;  // 0..1023
constexpr float RAMPA_PCT_S = 50.0f;    // cambio máximo del duty: 0 -> 100 % en 2 s
constexpr float ATASCO_DUTY_PCT = 40.0f;
constexpr float ATASCO_RPM = 300.0f;
constexpr uint32_t ATASCO_MS = 1000;

```



###3.3 Pines y configuración motor articulación (`08-motor-5840-l298n`)
**Archivo**: `src/motor_config.h` (Asignación de pines)



```cpp
#pragma once

// Placa: ESP32-WROOM-32D (ESP32 clásico, DevKit con conversor USB-serie CH340 -> /dev/ttyUSB0).
// Evitar: GPIO6-11 (flash), 0/2/5/12/15 (strapping), 1/3 (UART0 = USB), 34-39 (solo entrada y sin pull-up).

// Driver L298N, canal A (OUT1/OUT2)
constexpr int PIN_ENA = 25;  // PWM: velocidad. Sacar el jumper de ENA y conectar el pin de señal (no el de 5 V)
constexpr int PIN_IN1 = 26;  // sentido
constexpr int PIN_IN2 = 27;  // sentido

// Encoder incremental externo 38S6G5-B-G24N (NPN colector abierto): necesita pull-up a 3V3
constexpr int PIN_ENC_A = 32;  // cable blanco
constexpr int PIN_ENC_B = 33;  // cable verde
```



**Archivo**: `src/motor_config.h` (Parámetros y límites)


```cpp
constexpr float REDUCCION = 1.0f;
constexpr float ENCODER_PPR = 1000.0f;  // pulsos por vuelta, por fase
constexpr float ENCODER_X = 4.0f;       // flancos de A y B: 4000 cuentas por vuelta de salida
constexpr bool ENCODER_INVERTIDO = true;
constexpr L298N::Modo PWM_MODO = L298N::Modo::Freno;
constexpr uint32_t PWM_FREQ_HZ = 1000;
constexpr uint8_t PWM_BITS = 10;  // 0..1023
constexpr float RAMPA_PCT_S = 50.0f;  // 0 -> 100 % en 2 s
constexpr float ATASCO_DUTY_PCT = 50.0f;
constexpr float ATASCO_RPM = 5.0f;
constexpr uint32_t ATASCO_MS = 1000;
```



### 3.4 Aplicación del PWM

**Driver IBT-2 (motor base)**
Para el control del motor base, el sentido de giro y la velocidad se comandan dividiendo el ciclo de trabajo (*duty cycle*) en dos pines. Un *duty* positivo aplica la señal PWM en el pin `RPWM` (avance), un *duty* negativo la aplica en `LPWM` (retroceso), y un valor de 0 actúa como freno.

Por cuestiones de seguridad, la lógica implementada garantiza que siempre se apague primero el medio puente que no corresponde. De esta manera, se evita por completo la posibilidad de tener ambos pines PWM activos de forma simultánea.

**Archivo:** `lib/BTS7960/BTS7960.cpp`
```cpp
bool BTS7960::setDuty(float duty) {
  if (!ready_ || !isfinite(duty)) return false;
  if (duty > 1.0f) duty = 1.0f;
  if (duty < -1.0f) duty = -1.0f;
  duty_ = duty;

  const uint32_t count = (uint32_t)(fabsf(duty) * maxCount_ + 0.5f);
  
  // Primero se apaga el lado que no corresponde, para no tener los dos PWM activos a la vez
  if (duty >= 0.0f) {
    ledcWrite(chL_, 0);
    ledcWrite(chR_, count);
  } else {
    ledcWrite(chR_, 0);
    ledcWrite(chL_, count);
  }
  
  if (!enabled_) setEnable(true);
  return true;
}
```
**Driver L298N (motor de la articulación)**
La biblioteca implementa dos modos. Se utiliza el modo **Freno**: `ENA` se mantiene en alto y el PWM se aplica a `IN1` (adelante) o `IN2` (atrás). Al frenar en la parte apagada del ciclo, la velocidad resulta proporcional al *duty*. El modo **Rueda Libre** (PWM en `ENA`) se descartó por saturar la curva de respuesta. Al invertir el sentido, el pin inactivo pasa a bajo inmediatamente para evitar pulsos parásitos.

**Archivo:** `lib/L298N/L298N.cpp`
```cpp
bool L298N::setDuty(float duty) {
  if (!ready_ || !isfinite(duty)) return false;
  if (duty > 1.0f) duty = 1.0f;
  if (duty < -1.0f) duty = -1.0f;
  const uint32_t cuenta = (uint32_t)(fabsf(duty) * maxCount_ + 0.5f);
  const bool adelante = duty > 0.0f;
  const bool cambiaSentido = duty != 0.0f && duty_ != 0.0f && (duty_ > 0.0f) != adelante;

  if (modo_ == Modo::Freno) {
    if (duty == 0.0f) {  // freno: los dos IN en bajo con ENA en alto
      fijar(pinIn1_, chA_, pwmIn1_, LOW);
      fijar(pinIn2_, chB_, pwmIn2_, LOW);
    } else if (adelante) {  // primero se suelta el IN del otro sentido, en el acto
      fijar(pinIn2_, chB_, pwmIn2_, LOW);
      pwm(pinIn1_, chA_, pwmIn1_, cuenta);
    } else {
      fijar(pinIn1_, chA_, pwmIn1_, LOW);
      pwm(pinIn2_, chB_, pwmIn2_, cuenta);
    }
    digitalWrite(pinEna_, HIGH);
  } else {  // Modo::RuedaLibre: PWM en ENA
    if (duty == 0.0f) {  // freno: ENA fijo en alto con los dos IN en bajo
      digitalWrite(pinIn1_, LOW);
      digitalWrite(pinIn2_, LOW);
      fijar(pinEna_, chA_, pwmEna_, HIGH);
    } else {
      if (!pwmEna_ || cambiaSentido) {
        // Saliendo del freno, de la rueda libre o cambiando de sentido: ENA en bajo en el acto, y
        // recién después se mueven los IN y se conecta el PWM
        const bool veniaConPwm = pwmEna_;
        fijar(pinEna_, chA_, pwmEna_, LOW);
        // El canal pudo quedar con el duty anterior hasta fin de ciclo: esperar un período
        if (veniaConPwm) delayMicroseconds(periodoUs_ + 50);
        digitalWrite(pinIn1_, adelante ? HIGH : LOW);
        digitalWrite(pinIn2_, adelante ? LOW : HIGH);
      }
      pwm(pinEna_, chA_, pwmEna_, cuenta);
    }
  }
  duty_ = duty;
  enabled_ = true;
  return true;
}

### 3.5 Lectura del encoder por PCNT

Lectura en cuadratura x4 usando el periférico PCNT. Cada canal cuenta los flancos de una fase y lee el nivel de la otra para determinar el sentido.

**Archivo:** `lib/EncoderPCNT/EncoderPCNT.cpp`
```cpp
bool EncoderPCNT::begin(int pinA, int pinB, pcnt_unit_t unit, uint32_t filterNs) {
  ready_ = false;
  unit_ = unit;
  pinA_ = pinA;
  pinB_ = pinB;

  // Cuadratura x4, como el ejemplo rotary_encoder de ESP-IDF 4.4.
  // Canal 0: cuenta los flancos de A; el nivel de B decide el sentido.
  pcnt_config_t c = {};
  c.pulse_gpio_num = pinA;
  c.ctrl_gpio_num = pinB;
  c.channel = PCNT_CHANNEL_0;
  c.unit = unit;
  c.pos_mode = PCNT_COUNT_DEC;
  c.neg_mode = PCNT_COUNT_INC;
  c.lctrl_mode = PCNT_MODE_REVERSE;
  c.hctrl_mode = PCNT_MODE_KEEP;
  c.counter_h_lim = LIM_ALTO;
  c.counter_l_lim = LIM_BAJO;
  if (pcnt_unit_config(&c) != ESP_OK) return false;

  // Canal 1: cuenta los flancos de B; el nivel de A decide el sentido.
  c.pulse_gpio_num = pinB;
  c.ctrl_gpio_num = pinA;
  c.channel = PCNT_CHANNEL_1;
  c.pos_mode = PCNT_COUNT_INC;
  c.neg_mode = PCNT_COUNT_DEC;
  if (pcnt_unit_config(&c) != ESP_OK) return false;
  // ... (pull-ups internos, filtro de 10 µs y desbordes por interrupción)
}

### 3.6 Perfil en escalera (lazo abierto)

Se definen niveles escalonados y tiempos por defecto para las pruebas de respuesta en distintos ciclos de trabajo.

**Archivo:** `06-motor-36gp555/src/main.cpp`
```cpp
constexpr uint32_t PERFIL_SEG_MS_DEF = 5000;
constexpr float PERFIL_NIVELES_DEF[] = {20, 40, 60, 80, 100};
constexpr uint32_t PERFIL_PARADA_MS = 1000;  // freno entre la mitad positiva y la negativa
```
El perfil avanza automáticamente cada 10 ms e imprime los datos (`t_ms,duty_pct,cuentas`). Al invertir el sentido, frena hasta que el motor se detiene por completo. El PWM aplicado es independiente de las lecturas, operando estrictamente en lazo abierto.



```cpp
void pasoPerfil() {
  const uint32_t t = micros();
  Serial.printf("%lu,%.1f,%lld\n", (unsigned long)((t - perfilInicioUs) / 1000), dutyAct,
                (long long)(cuentas() - perfilC0));
  if (modo != Modo::Perfil) return;  // el atasco pudo cortarlo en este tick

  const uint32_t ahora = millis();
  if (perfilEnParada) {
    // Entre las dos mitades: frenado hasta que el motor está quieto (no se invierte girando)
    if (ahora - perfilSegInicioMs >= PERFIL_PARADA_MS && motorQuieto()) {
      perfilEnParada = false;
      perfilSentido = -1;
      perfilIdx = 0;
      aplicarPerfil(-perfilNiv[0]);
    }
    return;
  }
  if (ahora - perfilSegInicioMs < perfilSegMs) return;

  perfilIdx++;
  if (perfilIdx < perfilN) {
    aplicarPerfil(perfilSentido * perfilNiv[perfilIdx]);
  } else if (perfilSentido > 0) {
    perfilEnParada = true;
    aplicarPerfil(0.0f);  // freno
  } else {
    modo = Modo::Manual;
    rampa = true;
    dutyObj = 0.0f;
    aplicarDuty(0.0f);
    Serial.println(">> Fin del perfil.");
    if (ticksPerdidos > 0) {
      Serial.printf("  Aviso: se perdieron %lu muestras (loop atrasado); ver los saltos en t_ms.\n",
                    (unsigned long)ticksPerdidos);
    }
  }
}

```



### 3.7 Rampa por vueltas (motor base, con y sin carga)

El PWM aumenta linealmente en el tiempo cada 10 ms. El encoder se utiliza únicamente para detener la prueba al alcanzar las vueltas deseadas o para cortar el PWM como medida de seguridad si detecta un atasco.

**Archivo:** `07-motor-rampa-vueltas/src/main.cpp`
```cpp
void pasoRampa() {
  const uint32_t t = micros() - inicioUs;
  const int64_t c = cuentas() - c0;
  Serial.printf("%lu,%.1f,%lld\n", (unsigned long)(t / 1000), duty, (long long)c);

  // ¿Completó las vueltas? (en el sentido pedido)
  const float vueltas = sentido * (float)c / (CUENTAS_POR_VUELTA * REDUCCION);
  if (vueltas >= vueltasObj) {
    terminar("vueltas completas");
    return;
  }

  // Corte por atasco: duty alto y el motor no avanza en el sentido pedido
  if (fabsf(duty) >= ATASCO_DUTY_PCT && sentido * rpmMotor < ATASCO_RPM) {
    const uint32_t ahora = millis();
    if (atascoDesdeMs == 0) {
      atascoDesdeMs = ahora;
    } else if (ahora - atascoDesdeMs >= ATASCO_MS) {
      terminar("ATASCO");
      Serial.println("  Carga demasiado alta, eje trabado o encoder desconectado.");
      return;
    }
  } else {
    atascoDesdeMs = 0;
  }

  // Duty de la rampa: lineal en el tiempo, tope 100 %
  float pct = 100.0f * (t / 1e6f) / rampaS;
  if (pct >= 100.0f) {
    pct = 100.0f;
    if (llego100Ms == 0) llego100Ms = millis();
    if (millis() - llego100Ms >= ESPERA_EN_100_MS) {
      terminar("tiempo agotado en 100 %");
      return;
    }
  }
  duty = sentido * pct;
  driver.setDuty(duty / 100.0f);
}

### 3.8 Análisis en la PC

El script `tools/graficar.py perfil` separa los tramos de PWM constante y, en cada uno, ajusta a la velocidad un modelo de primer orden usando `scipy.optimize.curve_fit`. De este ajuste se obtiene la constante de tiempo $\tau$:

**Archivo:** `tools/graficar.py`
```python
def ajustar_primer_orden(ts, v):
    """Ajusta v(t) = v0 + (vf - v0)(1 - exp(-t/tau)) a la velocidad cruda de un tramo."""
    from scipy.optimize import curve_fit

    def modelo(t, v0, vf, tau):
        return v0 + (vf - v0) * (1 - np.exp(-t / tau))

    n = len(v)
    v0_ini = v[: max(n // 50, 2)].mean()
    vf_ini = v[int(n * 0.6):].mean()
    try:
        (v0, vf, tau), _ = curve_fit(modelo, ts, v, p0=(v0_ini, vf_ini, 0.08),
                                     bounds=([-np.inf, -np.inf, 0.005], [np.inf, np.inf, 5.0]), maxfev=5000)
        return v0, vf, tau
    except (RuntimeError, ValueError):
        return v0_ini, vf_ini, float("nan")

```
        
La ganancia $K$ y la zona muerta se calculan a partir de una recta ajustada a las velocidades de régimen de los niveles en los que el motor efectivamente gira:

```python
k, b = np.polyfit(x[gira], y[gira], 1)
zona = -b / k if k else float("nan")

### 3.9 Cómo reproducir las pruebas

A continuación se detallan los comandos para compilar, subir el firmware y ejecutar los scripts de adquisición de datos para ambos motores:

```bash
# Motor base (ESP32-S3). Con los 12 V apagados al flashear:
cd 06-motor-36gp555
~/.platformio/penv/bin/pio run -t upload       # pulsar RST y encender los 12 V
python3 tools/graficar.py barrido
python3 tools/graficar.py escalon 50
python3 tools/graficar.py perfil

cd ../07-motor-rampa-vueltas
~/.platformio/penv/bin/pio run -t upload
python3 tools/rampa.py                          # 0 -> 100 % en 3 s, hasta 3 vueltas
python3 tools/rampa.py --comparar resultados/rampa_<sin_carga>.csv

# Motor articulación (ESP32-WROOM-32D, /dev/ttyUSB0):
cd ../08-motor-5840-l298n
~/.platformio/penv/bin/pio run -t upload
python3 tools/graficar.py perfil

# 4. Resultados y Caracterización

### 4.1 Caracterización de los motores en lazo abierto

El análisis dinámico de ambos actuadores se realizó mediante ensayos de barrido PWM, respuesta al escalón y perfiles en escalera empleando el periférico PCNT ($T_s = 10\text{ ms}$).

#### Motor Base (36GP-555 + IBT-2)

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1nMkaTB0E_o838c02K2qYTp8ZsxVp0GWJ" alt="Fig. 3: Barrido en lazo abierto del motor base" width="750" />
  <br><b>Fig. 3.</b> Barrido PWM vs Velocidad (Adelante/Atrás) - Motor Base.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1GZBt6IL5Ef8mSUb_vGUtJm1kVC87n77f" alt="Fig. 4: Respuesta al escalón del motor base" width="750" />
  <br><b>Fig. 4.</b> Respuesta temporal al escalón de 50 % PWM - Motor Base.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/11ty7QiQKDM0hhuwgzeHNKSzi2CywODLd" alt="Fig. 5: Perfil en escalera del motor base" width="750" />
  <br><b>Fig. 5.</b> Ensayo con perfil en escalera $\pm 20\dots 100\%$ PWM - Motor Base.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1TLp9L4Ve_QGzXINaXvYGxVTn26Ffl_nc" alt="Fig. 6: Parámetros calculados del motor base" width="750" />
  <br><b>Fig. 6.</b> Ajuste lineal y constante de tiempo $\tau$ por nivel - Motor Base.
</p>

- **Respuesta lineal y simetría:** Presenta un comportamiento proporcional entre $20\%$ y $85\%$ de PWM con $K \approx 1{,}58\text{ rpm/\%}$ y una diferencia entre sentidos $< 2{,}5\text{ rpm}$. Por encima del $85\%$ se observa la saturación dinámica del driver.
- **Zona muerta y dinámica:** El movimiento en régimen se sostiene desde $\sim 11\%$, pero requiere $\ge 16\%$ para vencer la fricción estática de arranque ($25\%$ al aplicar carga). La respuesta al escalón confirma una dinámica de primer orden con $\tau \approx 65\text{ ms}$ (asentamiento a los $\sim 300\text{ ms}$).

#### Ensayos de Rampa con y sin Carga

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1TjF3fsCZ4naXIOiaNMx13IEOZnY_T2bS" alt="Fig. 7: Rampa sin carga del motor base" width="750" />
  <br><b>Fig. 7.</b> Rampa de 0 a 100 % en $3\text{ s}$ hasta 3 vueltas sin carga - Motor Base.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1KkkzkBsNBkVWxUQeWaOOQJNujFrpPw76" alt="Fig. 8: Rampa con carga del motor base" width="750" />
  <br><b>Fig. 8.</b> Rampa de 0 a 100 % en $3\text{ s}$ hasta 3 vueltas con carga - Motor Base.
</p>

- **Efecto de la carga:** La incorporación de par resistente desplaza en paralelo la respuesta ($21\text{ rpm}$ menos a medio ciclo), eleva el umbral de arranque a $25\%$ PWM e incrementa el tiempo de posicionamiento de $2{,}99\text{ s}$ a $3{,}42\text{ s}$ para completar 3 vueltas.

 **Registros audiovisual de ensayos (YouTube):**

[![Prueba](https://img.youtube.com/vi/OZjjWf5ewQA/0.jpg)](https://www.youtube.com/watch?v=OZjjWf5ewQA)

- [Ver ensayo de rampa con carga - Motor Base](https://www.youtube.com/watch?v=URL_VIDEO_BASE_CONCARGA)

---

#### Motor Articulación (5840-31ZY + L298N)

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1AI-9Ek6PiuZWjWYRvRpKN9Sw8G9Pbxs3" alt="Fig. 9: Perfil en escalera del motor articulación" width="750" />
  <br><b>Fig. 9.</b> Perfil en escalera $\pm 20\dots 100\%$ PWM en modo Freno - Motor Articulación.
</p>

<p align="center">
  <img src="https://lh3.googleusercontent.com/d/1g4ohBRuty5VtuDc-zbEoF1-aWWRdacKW" alt="Fig. 10: Parámetros del motor articulación" width="750" />
  <br><b>Fig. 10.</b> Ajuste de ganancia y constante de tiempo $\tau$ - Motor Articulación.
</p>

- **Modo Freno vs. Rueda Libre:** La conmutación en las entradas `IN1`/`IN2` (modo Freno) corrigió la saturación prematura observada con PWM en `ENA`, logrando una respuesta lineal entre $40\%$ y $100\%$ ($K \approx 1{,}33\text{ rpm/\%}$, $\tau \approx 59\text{ ms}$).
- **Fricción y limitaciones:** La alta fricción del mecanismo de tornillo sin fin fija la zona muerta de arranque entre $20\%$ y $40\%$ PWM. La velocidad máxima queda acotada a $\sim 140\text{ rpm}$ debido a la caída de tensión en los transistores BJT del L298N ($\sim 9{,}6\text{ V}$ efectivos).

 **Registro audiovisual de ensayos (YouTube):**
-  [Ver ensayo de perfil en escalera - Motor Articulación](https://www.youtube.com/watch?v=URL_VIDEO_ARTICULACION)

---

### Modelos Identificados

$$G_{\text{base}}(s) \approx \frac{1{,}58}{0{,}065s + 1} \quad (20\% \le \vert{}u\vert{} \le 85\%), \qquad G_{\text{art}}(s) \approx \frac{1{,}33}{0{,}059s + 1} \quad (40\% \le \vert{}u\vert{} \le 100\%)$$

---

### 4.2 Resumen comparativo

| Parámetro | Motor base (36GP-555 + IBT-2) | Motor articulación (5840-31ZY + L298N) |
|---|---|---|
| **Modelo $G(s)$** | $1{,}58 / (0{,}065s + 1)$ | $1{,}33 / (0{,}059s + 1)$ |
| **Rango lineal útil** | 20–85 % | 40–100 % |
| **Zona muerta (arranque)** | 16 % (vacío) / 25 % (con carga) | 20–40 % |
| **Velocidad máx. (100% PWM)**| ~145 rpm | ~140 rpm (limitado a 9,6 V por BJT) |
| **Constante de tiempo ($\tau$)**| 65 ms | 59 ms |
| **Simetría y Repetibilidad** | Error < 2,5 rpm / ±1,5 rpm | Error < 5 rpm / ±5 rpm |

---

### 4.3 Problemas encontrados y soluciones

| Problema | Causa raíz | Solución / Estado |
|---|---|---|
| **Pines flotantes en arranque** | Entradas `EN` flotan durante el boot del ESP32 | Parada por software en inicio + pull-down $10\text{ k}\Omega$ a GND |
| **Saturación en L298N** | Conmutación en modo Rueda Libre (PWM en ENA) | Migración a modo Freno (PWM en IN1/IN2 con ENA activo) |
| **Caída de RPM con carga** | Par resistente no compensado | Requiere control en lazo cerrado |
| **Corte de la fuente** | Límite de protección por corriente bajo | Ajuste de corriente máxima en la fuente a $3\text{ A}$ |

---

### 4.4 Conclusiones

Se caracterizaron ambos actuadores mediante modelos de primer orden con $\tau \approx 60\text{ ms}$. Las pruebas confirmaron la vulnerabilidad del lazo abierto: la carga redujo la velocidad en $21\text{ rpm}$ al $50\%$ PWM e incrementó la zona muerta del $16\%$ al $25\%$. Asimismo, se verificó que la conmutación en modo Freno es indispensable para linealizar la respuesta del driver L298N.

---

### 4.5 Próximo paso: Control PI + Feedforward

Diseño del lazo discreto ($T_s = 10\text{ ms}$) cancelando el polo del motor ($T_i = \tau$) para fijar un tiempo de respuesta en lazo cerrado de $0{,}1\text{ s}$:

$$u(t) = \text{sgn}(\omega_{\text{ref}})\cdot u_0 + \frac{\omega_{\text{ref}}}{K} + K_p \cdot e(t) + K_i \int e(t)\,dt$$

- **Motor base:** $K_p \approx 0{,}41\ \%/\text{rpm}$, $K_i \approx 6{,}3\ \%/(\text{rpm}\cdot\text{s})$
- **Motor articulación:** $K_p \approx 0{,}44\ \%/\text{rpm}$, $K_i \approx 7{,}5\ \%/(\text{rpm}\cdot\text{s})$

---

### **5. Referencias**
[1] Infineon Technologies, *BTS7960 High Current PN Half Bridge NovalithIC™*, hoja de datos.

[2] STMicroelectronics, *L298 Dual Full-Bridge Driver*, hoja de datos.

[3] Espressif Systems, *ESP-IDF Programming Guide v4.4: Pulse Counter (PCNT)*. Disponible en: <https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/pcnt.html>.

[4] Espressif Systems, *ESP-IDF Programming Guide v4.4: LED Control (LEDC)*. Disponible en: <https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/ledc.html>.

[5] Espressif Systems, ejemplo *rotary_encoder* de ESP-IDF v4.4. Disponible en: <https://github.com/espressif/esp-idf/tree/v4.4/examples/peripherals/pcnt/rotary_encoder>.

[6] PlatformIO, *Espressif 32 — PlatformIO documentation*. Disponible en: <https://docs.platformio.org/en/latest/platforms/espressif32.html>.

[7] K. Ogata, *Ingeniería de control moderna*, 5.ª ed. Madrid: Pearson, 2010 (sistemas de primer orden y controladores PID).

[8] Naylamp Mechatronics, “Ejemplos_L298N”, GitHub. Disponible en: <https://github.com/naylampmechatronics/Ejemplos_L298N>.

[9] **Proyectos Robóticos**, *Control PID para Arduino*. Disponible en: <https://sites.google.com/site/proyectosroboticos/control-de-motores/control-pid-mejorado?authuser=0>.

---
### **6. Carpeta del proyecto**
Carpeta del grupo E2:
[TPF - Estación 2](https://drive.google.com/drive/folders/1JggH_t1V1V1kcT6KU79V80s9d-Px1JNs?usp=sharing)

Código fuente, CSV y gráficos de esta entrega: [github.com/HecVelaz/pruebas-esp32](https://github.com/HecVelaz/pruebas-esp32) (carpetas `06-motor-36gp555`, `07-motor-rampa-vueltas` y `08-motor-5840-l298n`).
