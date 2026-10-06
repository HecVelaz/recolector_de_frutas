# Índice de documentos — Recolector de limones (Grupo 2, 2026S2)

Rutas desde `docs/`. `R1/` = `TPF R1/`, `R2/` = `TPF R2/` (una carpeta por entrega). Leer los `.md`, no PDF ni .ipynb
(los `.md` de los cuadernos nuevos salen con un script: texto y código, sin las salidas). Videos y artículos de
terceros quedan fuera de git (`.gitignore`).

**Consignas**
- `[2026S2] TPF_DescripcionGeneral.txt` — Consigna R1 (solo brazo): RRP/RRR sobre un eje lineal de 1,2 m; 2 primeros GDL con motor DC en lazo cerrado; ≥2 cámaras estéreo; limón = succión+torsión; ≥2 cajones por tamaño; zona de trabajo esfera Ø30 cm; fruta real sin daño; +4 pts al más rápido. Entregas E1–E9.
- `[2026S2]R2_GuiaTPF.txt` — Guía R2 v0.5 (27/07): robot ROS 2 de ≥40×35 cm y ≥5 kg, encoders+IMU+GPS, ≥3 sensores de distancia + 4 bumpers, autonomía ≥45 min, seta/luz/buzzer, FSM (INACTIVO…EMERGENCIA), rosbags, app móvil, hilera por GPS+visión. Opción B: ≥4 GDL; precisión y recobrado ≥0,80 (30 frutos); error 3D ≤35 mm; ≤45 s por fruto. Limón no figura entre las especies de la guía, pero **se acordó con el profesor usar limón**.

**Contexto**
- `elementos robot recogedor.md` — Hardware real (Pi 5 + ROS 2 Jazzy, 2 ESP32, 2 cámaras NoIR, motores 36GP-555 (J1), DC 895 planetario 53 rpm (tracción) y 5840-31ZY, 4 drivers (2 IBT-2 tracción, IBT-2 J1, L298N J2+J3), GPS UP501, IMU MPU-6500 (sin magnetómetro), LiDAR, HC-SR04).
- `Componentes_inventario.md` — Inventario con precios y correcciones.
- `fotos/` — Hojas del vendedor y fotos: `motor_traccion/` (42GM-895H, 189:1, encoder 11 PPR), `pinza/` (servo RDS3218), `rueda/` (inflable 150 mm, 45 mm de ancho, 650 g), `bateria/` (YONGZHI 10S2P 36 V 4400 mAh, 135×90×60 mm, XT60), `bucks/` (los 4 buck disponibles; el 3, ×2). **Decisión:** opción 6 de la tabla R1 (RRR-Limón), con pinza con tracción+rotación en vez de succión. Al 27/09: solo pruebas preliminares; estéreo sin validar (falta soporte de cámaras).

**Diseño**
- `ARQUITECTURA.md` — Arquitectura del objetivo mínimo (moverse + YOLO + estéreo + agarrar): reparto de los ESP32, nodos ROS 2, control en cascada, máquina de estados, plan de 5 etapas y preguntas para la cátedra.
- `BITACORA.md` — Bitácora por fecha: lo hecho, commits, revisiones de Codex y comandos usados.
- `CONEXIONES.md` — Conexionado v0.4 (05/10): pines de la S3, la WROOM (3 IBT-2, propuesta) y la Pi, circuito de potencia con dos baterías (10S para motores, LiPo 3S para la lógica), cables de cada motor, consumo y autonomía, y lista de verificación antes de conectar. `conexiones.html`: lo mismo como diagrama.
- `COMPRAS.md` — Lista de compras con casillas, del conexionado v0.4.

**R2 (robot móvil "Arturito R2D2")**
- `R2/Entrega 1/Entrega1.md` — E1 (30/08): estado del arte en cítricos, componentes (batería y LiDAR sin definir), pruebas de IMU/GPS/bumpers/ultrasonido con video.
- `R2/Entrega 2/Entrega2.md` — E2 (27/09, v2.1): diseño y primeros montajes: base de madera 400×400 mm, 2 ruedas motrices de ~150 mm + 2 locas, batería 36 V 4400 mAh, ubicación propuesta de sensores, estéreo de banco en cartón. ⚠ Dice MPU-6050 (es MPU-6500) y ROS 2 Humble/Ubuntu 22.04 en la sección 5 (fue Jazzy/24.04.5): corregir en el informe.
- `R2/Entrega 3/Entrega3.md` — E3 (27/09): **dimensiones de la base**: caja en T de 40 cm de largo; adelante la parte ancha 40×23 cm (brazo, sobre base impresa en 3D), atrás la angosta 34×17 cm con las ruedas de tracción en rebajes de 3 cm; paredes de 18 cm, madera de 1 cm, 3 bumpers (frente y laterales) con final de carrera, ruedas de 15 cm × 6 cm. Figuras en Drive (enlaces del cuaderno).

**R1 (brazo)**
- `R1/Entrega 1/Entrega1_v1.md` — E1 (18/08): 4R = 3R de posición + J4 que rota la pinza; paralelogramo tipo uArm con motores en la base; 150/300/300/50 mm.
- `R1/Entrega 2/Entrega2_v1.md` — E2 (27/08): primer espacio de trabajo; límites q1 ±75°, q2 −25…135°, q3 ±50°; CAD de la pinza.
- `R1/Entrega 3/Entrega3.md` — E3 (13/09): cinemática directa (geometría y DH), cierre del cuatro barras, simulación 3D.
- `R1/Entrega 4/Entrega4.md` — E4 (23/09): cinemática inversa con filtros. **Medidas vigentes** (reemplazan a las de E1–E2 por la evolución del diseño): 150/350,22/329,51, l4 338, balancines 40 mm; **no es Grashof** (sugiere balancín de 60 mm).
- `R1/Entrega 5/Entrega 5.md` — E5 (27/09, versión final): lazo abierto. Base G = 1,58/(0,065s+1), articulación G = 1,33/(0,059s+1); zona muerta 16 % (25 % con carga) y 20-40 %; coincide con el firmware. Código en github.com/HecVelaz/pruebas-esp32.

**Referencias (.txt extraídos de PDF)**
- `R2/…/s10462-023-10674-2.txt` — Zhang 2024, revisión de cosecha automática.
- `R1/Entrega 2/Artículos…/`: `sensors-14-11557` (Font 2014, estéreo + brazo), `agriculture-14-01310` (Han 2024, efectores finales), `agronomy-16-01127` (Ghonimy 2026, integración), `N159.1 … Barrientos` (libro de texto).
- `R1/Entrega 3/Artículos/matecconf…04014.txt` — Schütz 2024, cinemática del uArm Swift.
- `R1/Entrega 4/artículos/`: Tao 2014 (paletizador 4-DOF), Nguyen 2024 (robot con paralelogramo), Gebel 2020 (síntesis del cuatro barras).

**Pendientes / inconsistencias**
1. La lista de componentes de R2 E1 no coincide con el hardware real (2 ESP32, L298N).
2. R2 E2: MPU-6050 → MPU-6500; ROS 2 Humble/Ubuntu 22.04.5 → Jazzy/24.04.5 (sección 5).
3. R2 E3: la tabla dice "3 drivers del brazo"; son 2 (IBT-2 de J1 y L298N de J2+J3), 4 en total con los de tracción.
