# CLAUDE.md — recolector_de_frutas

Responder en castellano. Detalle histórico en `docs/BITACORA.md`.

## 1. Proyecto
Robot móvil autónomo recolector de limones "Arturito R2D2" (Grupo 2, FIUNA Mecatrónica, 2026S2). Cubre dos
materias: **Robótica I** evalúa el brazo; **Robótica II**, el robot móvil con ROS 2. Objetivo mínimo para aprobar:
**el robot se mueve, detecta el limón con YOLO, lo localiza con estéreo y lo agarra** (`docs/ARQUITECTURA.md`).

## 2. Hardware y arquitectura
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión, IK, misión. Habla por USB (micro-ROS) con dos ESP32.
- **ESP32-S3** (base): 2 motores de tracción + IBT-2, encoders, IMU MPU-6500, GPS UP501, 3 HC-SR04, 4 bumpers,
  seta, batería. **ESP32-WROOM-32D** (brazo): J1 36GP-555 + IBT-2, J2/J3 5840-31ZY (sin fin) + L298N, 2 servos.
- Brazo RRR con cuatro barras (medidas de la E4) + giro de pinza J4. Pines y alimentación: `docs/CONEXIONES.md`.

## 3. Estructura
- `docs/`: consignas, entregas R1/R2, `INDICE.md`, `ARQUITECTURA.md`, `CONEXIONES.md`, inventario, bitácora.
- `firmware/lib/`: drivers y lógica compartidos (`ControlArticulacion`, `EnlaceMicroRos`, BTS7960, L298N,
  EncoderPCNT, HCSR04, MPU9250, UP501). `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/brazo_ik/`: nodo de cinemática inversa. `graphify-out/`: grafo del repo (local, fuera de git).

## 4. Cómo trabajar acá
- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF ni `.ipynb`** (bloqueados en
  `.claude/settings.json`): usar sus `.txt`/`.md`.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor en solo lectura; en esta PC su sandbox no lee archivos: pegar el código en el prompt,
  lanzar con `< /dev/null` y esperar `tokens used` en la salida); **graphify** (grafo del repo); **ponytail**
  (instalado, sin usar todavía). `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas; al volver, revisar `git log` antes de seguir.

## 5. Estado actual (2026-09-27)
- `firmware/brazo`: control en cascada J1-J3 + pinza; comandos por serial o micro-ROS. 14 pruebas OK. **Sin placa.**
- `firmware/base`: tracción diferencial, odometría, sensores, seguridad local; serial o micro-ROS. 19 pruebas OK.
  **Sin placa.**
- Capa micro-ROS: compila en las dos placas; cada sesión arranca **desarmada** (`armar` por `/<parte>/comando`).
  Brazo probado con el agente en la placa sola (28/09, 921600 baudios, 20 Hz); base sin probar.
- `brazo_ik`: 5 pruebas OK y probado en la notebook.
- Revisados por Codex (brazo, base, micro-ROS) y hallazgos aplicados. Visión, estéreo y misión: sin empezar.

## 6. Decisiones
- Limón aunque no figura en la guía R2: aprobado por el profesor.
- Configuración RRR (opción 6 de la tabla R1); pinza con tracción + giro en vez de succión.
- Medidas del brazo vigentes: las de la E4; motor de J1 = 36GP-555 160 rpm (el DC 895 de 2700 rpm fue un error de compra).
- Un ESP32 por subsistema y lazos cerrados en los ESP32: la Pi solo manda consignas y cada placa se detiene sola.
- Control en cascada posición → velocidad, porque la E5 identificó modelos de velocidad.
- Seguridad de la base decidida en la S3 (seta NC, vuelco, bumpers, distancia, watchdog), sin depender de la Pi.
- Armado por sesión en micro-ROS, para que un nodo que siga publicando no mueva el robot al reconectar.
- TRIG común de HC-SR04, EN común de tracción y luz/buzzer en la Pi: la S3 no tiene más GPIO libres.
- Videos (~500 MB) y artículos de terceros fuera de git.

## 7. Próximos pasos
1. Confirmar el motor de tracción: notas = 36GP-555 53 rpm, inventario = DC 895 planetario 53 rpm.
2. Cablear según la lista "Antes de conectar" de `docs/CONEXIONES.md` (pull-down 10 kΩ en los EN, divisores de
   ECHO, pull-ups externos).
3. Primera prueba del brazo en placa (secuencia de su README; `v` sirve para la demo de la E6) y medir lo `MEDIR`.
4. Primera prueba de la base con ruedas en el aire (README) y medir sentidos, radio y trocha.
5. Probar micro-ROS con los agentes (`/dev/ttyACM0` base, `/dev/ttyUSB0` brazo) y medir con `ros2 topic hz`.
6. Probar las cámaras NoIR con YOLO y limones reales (riesgo de color); soporte rígido y calibración estéreo.
7. Nodos de visión y `mision_fsm` mínima para la demo del objetivo mínimo.
8. Preguntas a la cátedra (`docs/ARQUITECTURA.md` §11) y arreglar el salto de 32 000 cuentas de `EncoderPCNT`.
