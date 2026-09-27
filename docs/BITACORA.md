# Bitácora

Detalle de lo hecho, en orden. El resumen vigente está en `CLAUDE.md`.

## 2026-09-27

### Entorno
- Node.js v24.21.0 instalado con nvm (sin sudo). Enlaces de `node`, `npm` y `npx` en `~/.local/bin` para que los
  hooks que corren con `/bin/sh` los encuentren (apuntan a la versión v24.21.0 de nvm).
- Codex CLI 0.156.1 con sesión de ChatGPT de la cuenta **pjotazu@fiuna.edu.py** (se intentó entrar con otra cuenta;
  el navegador reutilizaba esa sesión y se decidió seguir con ella).
- Barra de estado de Claude Code: `~/.claude/statusline-command.sh` (modelo, % de contexto, tokens).

### Documentación
- `docs/INDICE.md`: una línea por documento (.txt/.md). `docs/ARQUITECTURA.md`: objetivo mínimo (moverse + YOLO +
  estéreo + agarrar), reparto de hardware, nodos ROS 2, control en cascada, máquina de estados, plan en 5 etapas.
- `docs/Componentes_inventario.md`: planilla de compras convertida desde `Componentes para R1 y R2.xlsx`.
- `docs/CONEXIONES.md` y `docs/conexiones.html`: pines de las dos placas y de la Pi, alimentación, lista de
  verificación. Página publicada: https://claude.ai/artifact/8eJqFaVCGBz39B3EGmGByN (privada).
- Correcciones del usuario incorporadas: el limón fue aprobado por el profesor; las medidas del brazo cambiaron
  con las entregas (vigentes las de la E4); el diseño es RRR (opción 6 de la tabla R1); el motor DC 895 de 2700 rpm
  fue una compra errónea (se usa el 36GP-555 de 160 rpm en J1).

### Revisiones de Codex (solo lectura)
- Proyecto y arquitectura: acordó la división por subsistema; señaló el riesgo de color de las cámaras NoIR, el
  L298N, el control en cascada (la E5 identifica velocidad, no posición) y requisitos de R1 sin cubrir.
- Firmware del brazo: 10 hallazgos aplicados (concurrencia de marcas de tiempo, parada sin retroceso, límites de
  puesta en marcha, homing, watchdog de tareas, servos sin pulsos al arrancar).
- Firmware de la base: 9 aplicados (IMU sin datos, bumper, ultrasonido sin eco, tope por cercanía que no se acumula
  con la rampa, rampa a cero, watchdog que anula, `cal` solo detenido).
- Capa micro-ROS: 10 aplicados, 1 verificado (MTU 512 B × historial 4 = 2048 B por mensaje reliable).

### Grafos (graphify, `graphify-out/`, fuera de git)
- Primero solo de `docs/` (259 nodos). Después del repo completo: 1009 nodos, 1824 aristas, 54 comunidades,
  996 nodos conectados; ~269 mil tokens de extracción de documentos. Ignorados por `.graphifyignore` (raíz) y
  `docs/.graphifyignore`.
- El grafo marcó una arista inferida incorrecta: "NodoIK implementa B7"; no hay planificador sin colisiones.

### Firmware y ROS 2
- Brazo empezó como `~/pruebas-esp32/09-brazo-control` (commits `cd8b420`, `f408f4e`) y se movió a este repo
  (`2a5fc54` allá). Las pruebas en la PC detectaron que sin feedforward de zona muerta cerca del objetivo el motor
  se clavaba a ~1,4°; se corrigió.
- Commits en este repo:
  - `664fb94` repo: documentación y firmware del brazo
  - `69d81c6` nodo `brazo_ik` (cinemática inversa de la E4)
  - `b3d91bd` diagrama de conexiones
  - `35ef366` firmware de la base; `658f6cc` revisión de Codex
  - `04e6bdf` capa micro-ROS; `ec7c70a` revisión de Codex
  - `99231c5` tópicos al día en ARQUITECTURA y README de `brazo_ik`
- Al probar `brazo_ik` a mano, `kill` del `ros2 run` deja vivo el proceso Python del nodo (quedaron 3 nodos
  respondiendo duplicado): cerrarlo con `pkill -f lib/brazo_ik/nodo_ik`.
- Prueba del nodo `brazo_ik` en la notebook: ejemplo de la E4 → q = (0,00°, 45,00°, 0,00°), error 5e-13 mm; punto
  lejano, q1 = 108° y marco equivocado rechazados con su motivo.
- Compilación: brazo `esp32dev` y `ros`, base `esp32s3` y `ros`, sin warnings. micro-ROS: RAM 15,3 % / flash 29,6 %
  (brazo), RAM 22,7 % / flash 7,3 % (base); primera compilación ~8 min cada una.

### Comandos usados
```bash
PIO=~/.platformio/penv/bin/pio
$PIO test -e native            # en firmware/brazo y firmware/base
$PIO run -e esp32dev|esp32s3   # modo serial
$PIO run -e ros                # micro-ROS
cd ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install && colcon test
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0   # base (source ~/microros_ws/install/local_setup.bash)
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0   # brazo
codex exec --skip-git-repo-check -s read-only "<prompt con el código pegado>" < /dev/null > salida.txt
```
