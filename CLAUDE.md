# CLAUDE.md — recolector_de_frutas

**Hablar siempre en castellano** (rioplatense, como el usuario): respuestas, avisos intermedios y explicaciones,
también en sesiones largas o mientras se depura. Nunca pasar al inglés. Detalle histórico en `docs/BITACORA.md`.

## Proyecto
Robot móvil autónomo recolector de limones "Arturito R2D2" (Grupo 2, FIUNA Mecatrónica, 2026S2). **Robótica I**
evalúa el brazo; **Robótica II**, el robot móvil con ROS 2. Objetivo mínimo: **el robot se mueve, detecta el limón con
YOLO, lo localiza con estéreo y lo agarra** (`docs/ARQUITECTURA.md`). **Fecha límite: 9/11/2026.**

## Hardware clave (detalle en `docs/CONEXIONES.md`)
- Base en T de madera (40 cm; adelante la parte ancha con el brazo, atrás las ruedas de tracción de 150 mm), 2× 42GM-895H con IBT-2.
- Potencia v0.6: LiPo 3S directa al bus de 12 V (XT60 → fusible 20 A → seta → selector WEG); Pi y ESP32 con el power bank PB2020MI.
- Raspberry Pi 5 (Ubuntu 24.04, ROS 2 Jazzy): visión estéreo + YOLO, IK, misión, GPS. Habla por USB (micro-ROS) con dos ESP32.
- **ESP32-S3** (base): tracción, encoders, IMU, 3 HC-SR04, 3 bumpers, seta, batería. **ESP32-WROOM-32D** (brazo): J1-J3 con IBT-2, 2 servos.
- 2 cámaras NoIR por CSI en un mástil adelante a la derecha (estéreo, baseline 90 mm); GPS UP501 en la Pi. La demo es al aire libre.
- Brazo RRR tipo uArm (paralelogramo: herramienta siempre horizontal), atrás a la izquierda sobre el eje de tracción.

## Reglas
- **El estado va en `docs/ESTADO.md`, nunca en `CLAUDE.md`.** Este archivo solo cambia si cambia una regla.
  Al cerrar una sesión: `/cerrar`; al empezar: `/retomar`.
- **Hardware: trabajar con lo que hay, no con lo ideal** (sin presupuesto ni tiempo). Antes de proponer un circuito,
  componentes o un cambio de hardware: revisar `docs/fotos/` y `docs/Componentes_inventario.md` y **preguntar qué hay**
  si no hay certeza. Solo si es imposible con lo disponible: explicar por qué y proponer lo más simple y barato.
- **Pines de la S3 vigentes = los de `bb9263d`**: los v0.8 "por lado" se revirtieron el 16/10 a pedido del usuario;
  **no volver a proponerlos**. Pines solo en `include/pins.h` de cada placa.
- **Simulación aislada:** `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` en el launch y en cada terminal; si no, ve y comanda
  los ESP32 reales de la Pi (dominio 0). Con el robot real, no dejar agentes corriendo con el brazo armado si no se usa.
- **10S guardada:** si vuelve, buck 1 y divisor 120 k / 8,2 k **antes** de conectarla (el de 30 k quema el GPIO 1).
- **Seta:** el bloque B va al **GPIO 47, nunca al 1**. Bus de 12 V sin capacitores.
- **Apagar los 12 V antes de flashear o resetear** un ESP32.
- **No leer PDF** (bloqueados): usar sus `.txt`/`.md`. Los `.ipynb` se pueden leer; preferir su `.md` si existe.
- ROS 2: unidades SI y `frame_id` explícito; `colcon test`. Firmware: `pio test` y `pio run` sin warnings antes de un commit.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Entregas (`docs/TPF R*/`): el usuario las edita a mano en Drive/Colab; Claude edita lo local y le pasa qué copiar.
  **Si el usuario editó en Colab, manda su versión.** Las entregas ya entregadas no se tocan sin preguntar.
- Páginas HTML publicadas: republicar en el **mismo link** (IDs en `docs/CONEXIONES.md`, al final); `todo.html` se
  regenera con `armar_todo.py` cada vez que cambia una página.
- Roles: Claude Code escribe, compila y hace commits; **Codex solo revisa** (`-s read-only`, lanzado desde el repo con
  `< /dev/null`). Si se agota el límite y el usuario lo pide, Codex puede editar; al volver, revisar `git log`.
- graphify (`graphify query`) para preguntas amplias; sus aristas INFERRED pueden estar mal: confirmar en el archivo.
  Rehacerlo una vez por semana o antes de una entrega, no después de cada commit (los documentos cuestan tokens).
- Valores marcados `MEDIR` en el código son provisorios: no darlos por medidos ni copiarlos a una entrega como reales.
- Visión: no reentrenar YOLO con imágenes de Gazebo (arruina el modelo para los limones reales); localizar con el
  robot quieto (exposiciones izq/der sin sincronizar).
- Videos (~500 MB) y artículos de terceros fuera de git.

## Qué leer para cada cosa
| Para… | Leer |
|---|---|
| Empezar una sesión | `docs/ESTADO.md`, `docs/PENDIENTES.md`, `git log --oneline -5`, `git status` (o `/retomar`) |
| Índice de todos los documentos y estructura del repo | `docs/INDICE.md` |
| Lo hecho día por día, mediciones, revisiones de Codex | `docs/BITACORA.md` |
| Por qué se decidió algo | `docs/DECISIONES.md` |
| Pines, potencia, borneras, autonomía, IDs de las páginas publicadas | `docs/CONEXIONES.md` |
| Diagramas y cableado | `docs/html/` (`conexiones`, `potencia`, `placa_s3`, `placa_wroom`, `seta`, `checklist_*`, `pi5`) |
| Arquitectura del objetivo mínimo, nodos, FSM | `docs/ARQUITECTURA.md` |
| Manual completo (LaTeX) | `docs/manual/` |
| Firmware, PlatformIO, flasheo, micro-ROS | `firmware/CLAUDE.md` |
| Entregas en Colab/Drive | `docs/TPF R1/CLAUDE.md` |
| Plugins (Codex, graphify, ponytail, anatomy), hooks y comandos locales | `docs/FLUJO_DE_TRABAJO.md` |
| Inventario y compras | `docs/Componentes_inventario.md`, `docs/COMPRAS.md`, `docs/fotos/` |
| IK, misión, simulación | `ros2_ws/src/{brazo_ik,mision,simulacion}/` (README de cada paquete) |
| Visión estéreo + YOLO | repo aparte `HecVelaz/vision_estereo` (su `CLAUDE.md`); datos en `docs/ESTADO.md` |
| Entrenamiento del detector | `vision/entrenamiento_limon/` |

## Estructura
- `firmware/lib/` drivers y lógica compartidos; `firmware/brazo/` y `firmware/base/`: un proyecto PlatformIO por placa.
- `ros2_ws/src/`: `brazo_ik` (cinemática inversa), `mision` (FSM de la demo y TF cámara → brazo), `simulacion` (Gazebo Harmonic).
- `docs/`: consignas, `TPF R1/` y `TPF R2/` (una carpeta por entrega), `fotos/`, `html/`, `manual/`, estado, decisiones y bitácora.
- Pi 5: `r2d2@100.116.96.71` (Tailscale `r2d2-desktop`); copia del repo por rsync con `/pi-sync`.
