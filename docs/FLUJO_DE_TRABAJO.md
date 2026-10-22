# Cómo trabajar en el repo (detalle)

Movido de `CLAUDE.md` §4 el 22/10 (texto completo). Resumen en `CLAUDE.md`; reglas de firmware en `firmware/CLAUDE.md` y de entregas en `docs/TPF R1/CLAUDE.md`.

- Empezar por `docs/INDICE.md`, `git log --oneline -5` y `git status`. **No leer PDF** (bloqueados en
  `.claude/settings.local.json`): usar sus `.txt`/`.md`. Los `.ipynb` se pueden leer (11/10); preferir su `.md` si existe.
- Firmware: `~/.platformio/penv/bin/pio`; pines solo en `include/pins.h`; drivers por `symlink://../lib/X`; lógica
  sin Arduino con pruebas `pio test -e native`. Verificar `pio test` y `pio run` sin warnings antes de un commit.
  **Apagar los 12 V antes de flashear o resetear.** ROS 2: unidades SI y `frame_id` explícito; `colcon test`.
- **Entregas (`docs/TPF R*/`): el usuario las edita a mano en Drive/Colab** (el profesor sigue el panel de actividad).
  Claude edita el `.ipynb` y el `.md` locales y le pasa qué
  copiar. Imágenes por link `lh3.googleusercontent.com/d/<ID>=w2400`: al cambiar una, subir nueva versión en Drive (mismo
  ID) y cambiar el `=w` para saltear la caché. Diagramas: `.drawio` → PNG con Firefox headless + visor de diagrams.net
  (no hay draw.io instalado; el snap de Firefox no ve `/tmp`: usar `~/snap/firefox/common/render/`).
  **Formato desde la E7 de R1 (17/10):** el `.md` es la fuente; el cuaderno se arma desde él (una celda por cada
  `<!-- celda -->`). El que va a Colab es `Entrega7_.ipynb`, con links `lh3` (no incrustar imágenes en base64: la celda
  queda ilegible en Colab). Diagramas `.drawio` + PNG en `Diagramas/`, figuras en `Imagenes/FigN_*`; tablas y figuras
  grandes (diagramas con letra de 16-20 pt), párrafos cortos, sin emojis. Los IDs que pasa el usuario se verifican
  bajando cada `lh3` y comparando el tamaño con el archivo local. El conector de Drive no tiene permiso de escritura:
  el usuario sube todo a mano. **Si el usuario edita en Colab, manda su versión:** bajar el `.ipynb` de Drive y
  reconstruir el `.md` desde él antes de tocar nada.
- Commits en castellano en `main`; push a GitHub (`HecVelaz/recolector_de_frutas`, privado) solo si el usuario lo pide.
- Plugins: **codex** (revisor con `-s read-only`; sandbox arreglado el 28/09 con el perfil AppArmor `/etc/apparmor.d/bwrap`;
  lanzar con `< /dev/null` **desde la carpeta del repo** y esperar `tokens used`; confirmar a los 20 s que abrió
  sesión); **graphify** (grafo del repo, rehecho el 17/10: usarlo con `graphify query` para preguntas
  amplias, como dónde se usa algo o qué conecta dos partes, y para buscar inconsistencias; para editar, leer igual el
  archivo real. Sus aristas INFERRED pueden estar mal: confirmar en el archivo. **Actualizarlo de vez en cuando**, una vez
  por semana o antes de una entrega o revisión grande, no después de cada commit: el código es gratis (AST), pero cada
  tanda de documentos cuesta ~75-115 k tokens y el armado completo ~450 k); **ponytail**
  (instalado, sin usar todavía); **anatomy** (figuras isométricas, en `~/.claude/skills/`; para informes, no antes del 3/11).
  Locales (`.claude/`, fuera de git): **`/pi-sync`** (rsync a la Pi, `colcon build` y flasheo de los ESP32;
  sin probar con la Pi), un hook que pide confirmar los 12 V apagados antes de `pio ... -t upload` o `esptool`, y otro
  (`.claude/hooks/tests_firmware.sh`, 15/10) que corre `pio test -e native` en la placa afectada al editar `firmware/` (las dos si es `lib/`). `~/pruebas-esp32` sigue siendo el repo de pruebas de componentes sueltos.
- Roles: Claude Code escribe, compila y hace commits; Codex solo revisa. Si se agota el límite de Claude Code y el
  usuario lo pide, Codex puede editar con estas reglas
  (`codex --sandbox workspace-write` en el repo; lee este archivo por `AGENTS.md`); al volver, revisar `git log` antes de seguir.
- **Hardware: trabajar con lo que hay, no con lo ideal** (sin presupuesto ni tiempo para conseguir piezas). Antes de
  proponer un circuito, una lista de componentes o un cambio de hardware (sobre todo potencia: baterías, step-down,
  fusibles, protecciones, cableado, conectores; también sensores o placas): 1) revisar `docs/fotos/` y
  `docs/Componentes_inventario.md`; 2) **preguntar qué componentes hay ahora mismo** si no hay certeza, en vez de
  completar con el componente "ideal". Solo si es imposible con lo disponible: explicar por qué no alcanza y proponer
  la alternativa más simple y barata, sin listas largas de piezas nuevas.
