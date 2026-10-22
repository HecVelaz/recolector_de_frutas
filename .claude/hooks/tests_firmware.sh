#!/usr/bin/env bash
# Hook PostToolUse: si Claude editó el firmware, corre `pio test -e native` en la placa afectada
# (en las dos si el cambio está en firmware/lib). Si falla, sale con 2 para que Claude lo vea.
f=$(jq -r '.tool_input.file_path // empty')
raiz="$CLAUDE_PROJECT_DIR"
case "$f" in
  */.pio/*) exit 0 ;;
  "$raiz"/firmware/lib/*)   placas="base brazo" ;;
  "$raiz"/firmware/base/*)  placas="base" ;;
  "$raiz"/firmware/brazo/*) placas="brazo" ;;
  *) exit 0 ;;
esac
pio="$HOME/.platformio/penv/bin/pio"
[[ -x "$pio" ]] || exit 0   # sin PlatformIO no se puede probar: no bloquear
fallo=0
for p in $placas; do
  if ! salida=$(cd "$raiz/firmware/$p" && "$pio" test -e native 2>&1); then
    echo "Fallan las pruebas nativas de firmware/$p (pio test -e native):" >&2
    echo "$salida" | tail -30 >&2
    fallo=1
  fi
done
[[ $fallo -eq 0 ]] || exit 2
