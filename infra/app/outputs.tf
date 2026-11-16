output "alb_url" {
  value = "http://${aws_lb.this.dns_name}"
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "backend_service_name" {
  value = aws_ecs_service.this["backend"].name
}

output "frontend_service_name" {
  value = aws_ecs_service.this["frontend"].name
}

output "backend_task_definition_arn" {
  value = aws_ecs_task_definition.backend.arn
}

output "frontend_task_definition_arn" {
  value = aws_ecs_task_definition.frontend.arn
}

output "subnet_ids" {
  description = "Subredes separadas por coma (para la tarea de migraciones)"
  value       = join(",", data.aws_subnets.default.ids)
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}

output "db_endpoint" {
  value = aws_db_instance.this.address
}
