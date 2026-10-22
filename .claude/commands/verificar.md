---
description: Verificar el repo sin cambiar nada - git, docs, firmware, ROS 2 y qué copiaría /pi-sync
---

Revisá el repo, en castellano, **sin modificar, commitear ni sincronizar nada** (las salidas de compilación en
`.pio/`, `build/`, `install/` y `log/` están ignoradas por git y no cuentan). Seguí aunque falle un punto.

1. **Git**
   - `git status --short` vacío.
   - `git ls-files -s AGENTS.md firmware/AGENTS.md`: modo `120000`, y `git cat-file -p HEAD:AGENTS.md` (ídem
     `firmware/`) da `CLAUDE.md`.
   - Nada indebido versionado: `git ls-files | grep -E 'settings\.local\.json|^graphify-out/|\.(mp4|mov|avi|mkv)$'`
     vacío, y ningún PDF versionado > 5 MB (`git ls-files -z '*.pdf' | xargs -0 -r du -k` y filtrar).
2. **Docs**
   - Toda ruta citada entre backticks en `CLAUDE.md` y `firmware/CLAUDE.md` existe (las de `{a,b}` expandirlas; las
     relativas de `firmware/CLAUDE.md`, probarlas desde `firmware/` y desde la raíz; ignorar comandos, URLs y rutas
     de la Pi o de otro repo como `HecVelaz/vision_estereo`).
   - `CLAUDE.md` < 8 KB (`wc -c`); `docs/ESTADO.md` < 80 líneas (`wc -l`).
   - Sin estado con fechas en `CLAUDE.md`: `grep -nE '[0-9]{1,2}/[0-9]{1,2}'` y juzgar cada línea; una fecha dentro
     de una regla (fecha límite, "se revirtieron el 16/10") es aceptable, un "hoy/quedó/falta" con fecha no.
3. **Código** (`~/.platformio/penv/bin/pio`), en `firmware/base` y en `firmware/brazo`:
   - `pio test -e native` pasa.
   - `pio run` (env por defecto) y `pio run -e ros` sin errores **ni warnings** (`grep -i warning` en la salida).
   - En `ros2_ws`: `colcon test` y `colcon test-result --verbose` (con Jazzy sourceado y
     `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`). Si no está compilado, `colcon build` antes y decirlo.
4. **Pi**: conexión y rsync del paso 0 y 2 de `.claude/skills/pi-sync/SKILL.md`, **solo con `-n`** (dry-run).
   Mostrar la lista de lo que copiaría, agrupada por carpeta. Si la Pi no responde, FALLA "Pi no accesible".

Al final, una tabla `| Punto | Resultado | Detalle |` con una fila por chequeo (1a, 1b, …) y `OK` / `FALLA`; en
Detalle, el motivo corto de cada falla.
