#!/usr/bin/env bash
# Despliega la nueva versión de la app en un ambiente:
#   1. Guarda la revisión actual de cada servicio (para el rollback).
#   2. Ejecuta las migraciones de la base de datos.
#   3. Actualiza los servicios de ECS (rolling update) y espera a que estén estables.
#
# Variables requeridas: CLUSTER, BACKEND_SERVICE, FRONTEND_SERVICE,
#   BACKEND_TASK_DEF, FRONTEND_TASK_DEF, SUBNETS, SECURITY_GROUP
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="${GITHUB_OUTPUT:-/dev/null}"

current_task_def() {
  aws ecs describe-services --cluster "$CLUSTER" --services "$1" \
    --query 'services[0].taskDefinition' --output text
}

PREV_BACKEND=$(current_task_def "$BACKEND_SERVICE")
PREV_FRONTEND=$(current_task_def "$FRONTEND_SERVICE")
echo "Versión actual (para rollback):"
echo "  backend:  $PREV_BACKEND"
echo "  frontend: $PREV_FRONTEND"
{
  echo "previous_backend_task_def=$PREV_BACKEND"
  echo "previous_frontend_task_def=$PREV_FRONTEND"
} >> "$OUTPUT_FILE"

# 1) Migraciones (antes de cambiar la app: los cambios de esquema son compatibles)
bash "$SCRIPT_DIR/run_migrations.sh"

# 2) Actualizar servicios
update() {
  local service="$1" task_def="$2"
  echo "Actualizando $service -> $task_def"
  aws ecs update-service --cluster "$CLUSTER" --service "$service" \
    --task-definition "$task_def" --query 'service.serviceName' --output text
}
update "$BACKEND_SERVICE" "$BACKEND_TASK_DEF"
update "$FRONTEND_SERVICE" "$FRONTEND_TASK_DEF"

echo "Esperando a que los servicios queden estables..."
aws ecs wait services-stable --cluster "$CLUSTER" \
  --services "$BACKEND_SERVICE" "$FRONTEND_SERVICE"

# 3) Verificar que no actuó el circuit breaker (que vuelve solo a la versión anterior)
for pair in "$BACKEND_SERVICE=$BACKEND_TASK_DEF" "$FRONTEND_SERVICE=$FRONTEND_TASK_DEF"; do
  service="${pair%%=*}"
  expected="${pair#*=}"
  running=$(current_task_def "$service")
  if [[ "$running" != "$expected" ]]; then
    echo "::error::$service quedó en $running. El circuit breaker de ECS revirtió el despliegue."
    exit 1
  fi
done
echo "Despliegue completado"
