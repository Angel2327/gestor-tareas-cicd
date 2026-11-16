#!/usr/bin/env bash
# Ejecuta "alembic upgrade head" como una tarea única de ECS (Fargate) con la
# imagen NUEVA del backend, dentro de la VPC (la base de datos RDS no es pública).
#
# Variables requeridas: CLUSTER, BACKEND_TASK_DEF, SUBNETS (separadas por coma),
#                       SECURITY_GROUP
set -euo pipefail

echo "Ejecutando migraciones con ${BACKEND_TASK_DEF}"

NETWORK="awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=ENABLED}"
OVERRIDES='{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}'

TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$BACKEND_TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "$NETWORK" \
  --overrides "$OVERRIDES" \
  --started-by "github-actions-migrations" \
  --query 'tasks[0].taskArn' --output text)

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "::error::No se pudo iniciar la tarea de migraciones"
  exit 1
fi

echo "Tarea de migraciones: $TASK_ARN (esperando a que termine...)"
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"

EXIT_CODE=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[?name==`backend`].exitCode | [0]' --output text)
REASON=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].stoppedReason' --output text)

echo "Código de salida: ${EXIT_CODE} (${REASON})"
if [[ "$EXIT_CODE" != "0" ]]; then
  echo "::error::Las migraciones fallaron. Revisa CloudWatch Logs del ambiente."
  exit 1
fi
echo "Migraciones aplicadas correctamente"
