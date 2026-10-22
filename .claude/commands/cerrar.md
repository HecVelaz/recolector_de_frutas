---
description: Cerrar la sesión - bitácora, ESTADO, PENDIENTES y commit
---

Cerrá la sesión de trabajo, en castellano:

1. Revisá `git status`, `git diff` y los commits de hoy (`git log --since=midnight --oneline`) para saber qué se hizo.
2. Agregá una entrada con la fecha de hoy en `docs/BITACORA.md` (mismo formato que las anteriores): lo hecho,
   mediciones, comandos útiles, revisiones de Codex y commits.
3. Reescribí `docs/ESTADO.md` como foto del estado actual, **máximo 80 líneas**: cambiá la fecha del título, sacá lo
   que ya no es cierto o es historia (eso queda en la bitácora) y no dupliques la bitácora.
4. Actualizá `docs/PENDIENTES.md`: tachá o borrá lo terminado, sumá lo nuevo, reordená por prioridad.
5. Tocá `CLAUDE.md` **solo si cambió una regla** (nunca para poner estado). Si una decisión nueva no es regla, va a
   `docs/DECISIONES.md`.
6. Commit en castellano con todo lo anterior (y lo que haya quedado sin commitear de la sesión, si corresponde).
   No hagas push salvo que te lo pidan.
7. Terminá con un resumen de 3 líneas: qué se hizo, qué sigue, qué quedó sin commitear.
