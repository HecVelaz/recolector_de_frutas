# Índice de documentos — Recolector de limones (Grupo 2, 2026S2)

Rutas desde `docs/`. `R1/` = `TPF R1 Grupo 2-…/TPF R1 Grupo 2/`, `R2/` = `TPF R2 -…/TPF R2 /`. Sin PDF ni .ipynb.

**Consignas**
- `[2026S2] TPF_DescripcionGeneral.txt` — Consigna R1 (solo brazo): RRP/RRR sobre un eje lineal de 1,2 m; 2 primeros GDL con motor DC en lazo cerrado; ≥2 cámaras estéreo; limón = succión+torsión; ≥2 cajones por tamaño; zona de trabajo esfera Ø30 cm; fruta real sin daño; +4 pts al más rápido. Entregas E1–E9.
- `[2026S2]R2_GuiaTPF.txt` — Guía R2 v0.5 (27/07): robot ROS 2 de ≥40×35 cm y ≥5 kg, encoders+IMU+GPS, ≥3 sensores de distancia + 4 bumpers, autonomía ≥45 min, seta/luz/buzzer, FSM (INACTIVO…EMERGENCIA), rosbags, app móvil, hilera por GPS+visión. Opción B: ≥4 GDL; precisión y recobrado ≥0,80 (30 frutos); error 3D ≤35 mm; ≤45 s por fruto. Limón no figura entre las especies de la guía, pero **se acordó con el profesor usar limón**.

**Contexto**
- `elementos robot recogedor.md` — Hardware real (Pi 5 + ROS 2 Jazzy, 2 ESP32, 2 cámaras NoIR, motores 36GP-555 y 5840-31ZY, IBT-2/L298N, GPS UP501, MPU9250, LiDAR, HC-SR04). **Decisión:** opción 6 de la tabla R1 (RRR-Limón), con pinza con tracción+rotación en vez de succión. Al 27/09: solo pruebas preliminares; estéreo sin validar (falta soporte de cámaras).

**Diseño**
- `ARQUITECTURA.md` — Arquitectura del objetivo mínimo (moverse + YOLO + estéreo + agarrar): reparto de los ESP32, nodos ROS 2, control en cascada, máquina de estados, plan de 5 etapas y preguntas para la cátedra.
- `BITACORA.md` — Bitácora por fecha: lo hecho, commits, revisiones de Codex y comandos usados.
- `CONEXIONES.md` / `conexiones.html` — Diagrama de conexiones: pines de la S3 (base, propuesta), la WROOM (brazo) y la Pi, árbol de alimentación con la seta, y lista de verificación antes de conectar.

**R2 (robot móvil "Arturito R2D2")**
- `R2/Entrega 1/Entrega1.md` — E1 (30/08): estado del arte en cítricos, componentes (batería y LiDAR sin definir), pruebas de IMU/GPS/bumpers/ultrasonido con video.
- `R2/Entrega 2/Entrega2.md` — E2: **plantilla vacía**; fecha y subtítulo copiados de E1.

**R1 (brazo)**
- `R1/Entrega 1/Entrega1_v1.md` — E1 (18/08): 4R = 3R de posición + J4 que rota la pinza; paralelogramo tipo uArm con motores en la base; 150/300/300/50 mm.
- `R1/Entrega 2/Entrega2_v1.md` — E2 (27/08): primer espacio de trabajo; límites q1 ±75°, q2 −25…135°, q3 ±50°; CAD de la pinza.
- `R1/Entrega 3/Entrega3.md` — E3 (13/09): cinemática directa (geometría y DH), cierre del cuatro barras, simulación 3D.
- `R1/Entrega 4/Entrega4.md` — E4 (23/09): cinemática inversa con filtros. **Medidas vigentes** (reemplazan a las de E1–E2 por la evolución del diseño): 150/350,22/329,51, l4 338, balancines 40 mm; **no es Grashof** (sugiere balancín de 60 mm).
- `R1/Entrega 5/Entrega 5.md` — E5 (27/09, versión final): lazo abierto. Base G = 1,58/(0,065s+1), articulación G = 1,33/(0,059s+1); siguiente paso PI + feedforward. Código en github.com/HecVelaz/pruebas-esp32.
- `R1/Entrega 5/Entrega5_v1.md` — Borrador ampliado de E5 (26/09). ⚠ Encabezado copiado de otra plantilla ("…medicamentos").

**Referencias (.txt extraídos de PDF)**
- `R2/…/s10462-023-10674-2.txt` — Zhang 2024, revisión de cosecha automática.
- `R1/Entrega 2/Artículos…/`: `sensors-14-11557` (Font 2014, estéreo + brazo), `agriculture-14-01310` (Han 2024, efectores finales), `agronomy-16-01127` (Ghonimy 2026, integración), `N159.1 … Barrientos` (libro de texto).
- `R1/Entrega 3/Artículos/matecconf…04014.txt` — Schütz 2024, cinemática del uArm Swift.
- `R1/Entrega 4/artículos/`: Tao 2014 (paletizador 4-DOF), Nguyen 2024 (robot con paralelogramo), Gebel 2020 (síntesis del cuatro barras).

**Pendientes / inconsistencias**
1. La lista de componentes de R2 E1 no coincide con el hardware real (2 ESP32, L298N).
