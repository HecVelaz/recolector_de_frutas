# CLAUDE.md — recolector_de_frutas

Repo del robot recolector de limones (Grupo 2). Ver `README.md` para la estructura y `docs/INDICE.md` para la
documentación. Responder en castellano.

## Convenciones

- **ROS 2:** Jazzy, workspace en `ros2_ws/` (paquetes `ament_python`), lógica sin ROS en módulos aparte con
  pruebas `pytest` (`colcon test`). Unidades SI en los tópicos (m, rad), marcos explícitos en `frame_id`.
- **Firmware:** PlatformIO + Arduino (core 2.0.17) en `~/.platformio/penv/bin/pio`. Un proyecto por placa en
  `firmware/<parte>/`, con `include/pins.h` (único lugar de los GPIO), `include/<parte>_config.h`, `src/main.cpp`,
  `README.md` (conexiones, uso, pendientes, tabla de resultados) y pruebas en la PC (`test/`, `pio test -e native`).
- **Drivers compartidos** en `firmware/lib/<Driver>/`, sin `Serial` ni pines fijos, con `library.json`. Se enlazan
  con `lib_deps = symlink://../lib/<Driver>`; no se copian. Un cambio en un driver: recompilar todos los que lo usan.
- La lógica de control va en bibliotecas **sin Arduino** para poder probarla en la PC con un modelo simulado.
- **Motores:** apagar los 12 V antes de flashear o resetear (los EN flotan hasta que arranca el firmware; faltan
  los pull-down de 10 kΩ).
- **Commits:** en castellano, en `main`. Verificar antes: `pio test -e native` y `pio run` sin warnings.
- **Fuera de git:** videos, material de terceros, `graphify-out/` (ver `.gitignore`).

## Roles (como en `~/pruebas-esp32/AGENTS.md`)

- **Modo normal:** Claude Code escribe, compila, flashea y hace commits. Codex **solo revisa**
  (`codex exec --sandbox read-only`), sin modificar archivos. En esta PC el sandbox de Codex no puede leer
  archivos (`bwrap: Operation not permitted`): pasarle el código pegado en el prompt y con `< /dev/null`.
- **Modo respaldo** (se agotó el límite de Claude Code y el usuario lo pide): Codex puede editar y hacer commits
  con estas mismas convenciones. Al volver, Claude Code revisa `git log` antes de seguir.
- **Continuidad:** el estado vive en git y en la sección de abajo. Al empezar: `git log --oneline -5` y
  `git status`. Al terminar: commit y actualizar "Estado actual".

## Estado actual

- **2026-09-27:** repo creado. Documentación ordenada (`docs/INDICE.md`, `docs/ARQUITECTURA.md`,
  `docs/Componentes_inventario.md`). Decisiones: limón aprobado por el profesor; configuración RRR (opción 6 de
  la tabla de R1); pinza con tracción + giro en vez de succión; medidas vigentes del brazo las de la R1 E4; motor
  de la base del brazo = 36GP-555 160 rpm (el DC 895 de 2700 rpm fue una compra errónea).
- **`firmware/brazo`** (movido de `~/pruebas-esp32/09-brazo-control`, commits `cd8b420` y `f408f4e` allá): control
  en cascada de J1-J3 + pinza en la ESP32-WROOM-32D, comandos por serial. 14 pruebas OK en la PC, compila, revisado
  por Codex (10 hallazgos aplicados). **No probado en placa.** Pendiente: todo lo marcado `MEDIR` en
  `include/brazo_config.h`, pull-down de 10 kΩ en los EN, primera prueba en placa (secuencia en su README) y capa
  micro-ROS.
- **`ros2_ws/src/brazo_ik`** (2026-09-27): cinemática inversa de la E4 portada a Python puro (`cinematica.py`, sin
  ROS ni numpy) + nodo `brazo_ik` (`/brazo/objetivo` PointStamped [m, marco brazo_base] -> `/brazo/joint_cmd`
  JointState [rad] y `/brazo/ik_estado`). 5 pruebas OK (ejemplo numérico de la E4 exacto, 2000 idas y vueltas).
  Probado en la notebook. Ojo al probar: `kill` del `ros2 run` deja vivo el proceso Python del nodo
  (`pkill -f lib/brazo_ik/nodo_ik`). La geometría y los límites deben coincidir con `firmware/brazo`.
- **Pendiente general:** `firmware/base` (ESP32-S3), resto de `ros2_ws` en la Pi, prueba de las cámaras NoIR con YOLO
  (riesgo de color, ver `docs/ARQUITECTURA.md` §6), preguntas a la cátedra (§11).
- **Pendiente en `firmware/lib/EncoderPCNT`:** salto falso de 32 000 cuentas (el control del brazo lo filtra).
