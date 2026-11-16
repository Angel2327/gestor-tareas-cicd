#!/usr/bin/env bash
# Rollback de un servicio de ECS a una revisión anterior de su task definition.
#
# Uso: rollback.sh <cluster> <servicio> [task_definition_destino]
#   - Si se pasa el destino (ARN o familia:revisión), vuelve a ese.
#   - Si no, vuelve a la revisión ACTIVA inmediatamente anterior a la actual.
# La imagen de cada revisión está en ECR con etiqueta inmutable (SHA), por eso
# volver a una revisión anterior restaura exactamente la versión anterior.
set -euo pipefail

CLUSTER="$1"
SERVICE="$2"
TARGET="${3:-}"

CURRENT=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].taskDefinition' --output text)
echo "[$SERVICE] revisión actual: $CURRENT"

if [[ -z "$TARGET" ]]; then
  FAMILY_REV="${CURRENT##*/}"      # familia:revision
  FAMILY="${FAMILY_REV%:*}"
  REVISION="${FAMILY_REV##*:}"
  for arn in $(aws ecs list-task-definitions --family-prefix "$FAMILY" \
      --status ACTIVE --sort DESC --query 'taskDefinitionArns[]' --output text); do
    rev="${arn##*:}"
    if (( rev < REVISION )); then
      TARGET="$arn"
      break
    fi
  done
fi

if [[ -z "$TARGET" ]]; then
  echo "::error::[$SERVICE] no hay una revisión anterior a la que volver"
  exit 1
fi

if [[ "$TARGET" == "$CURRENT" ]]; then
  echo "[$SERVICE] ya está en $TARGET; no hay nada que revertir"
  exit 0
fi

IMAGE=$(aws ecs describe-task-definition --task-definition "$TARGET" \
  --query 'taskDefinition.containerDefinitions[0].image' --output text)
echo "[$SERVICE] rollback -> $TARGET"
echo "[$SERVICE] imagen: $IMAGE"

aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
  --task-definition "$TARGET" --query 'service.serviceName' --output text
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"
echo "[$SERVICE] rollback completado"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  echo "| \`$SERVICE\` | \`${CURRENT##*/}\` | \`${TARGET##*/}\` | \`$IMAGE\` |" \
    >> "$GITHUB_STEP_SUMMARY"
fi
