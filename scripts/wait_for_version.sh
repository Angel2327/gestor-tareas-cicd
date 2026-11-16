#!/usr/bin/env bash
# Espera hasta que /api/health del ambiente responda la versión esperada,
# para no probar nunca la versión anterior.
#
# Uso: wait_for_version.sh <url_base> <version> [timeout_segundos]
set -euo pipefail

URL="${1%/}/api/health"
EXPECTED="$2"
TIMEOUT="${3:-600}"
DEADLINE=$((SECONDS + TIMEOUT))

echo "Esperando version=$EXPECTED en $URL"
while (( SECONDS < DEADLINE )); do
  BODY=$(curl -s --max-time 5 "$URL" || true)
  if [[ "$BODY" == *"\"version\":\"$EXPECTED\""* && "$BODY" == *'"database":"ok"'* ]]; then
    echo "Listo: $BODY"
    exit 0
  fi
  echo "Aún no: ${BODY:-sin respuesta}"
  sleep 10
done

echo "::error::$URL no respondió la versión $EXPECTED en ${TIMEOUT}s"
exit 1
