# Infraestructura de UN ambiente (staging o production, según el workspace).
#
#   Internet -> ALB :80 -> /api/*  -> ECS Fargate "backend"  (FastAPI :8000) -> RDS PostgreSQL
#                       -> resto   -> ECS Fargate "frontend" (Nginx   :8080)

locals {
  name = "${var.project_name}-${var.environment_name}"
}

# ---------------------------------------------------------------------------
# Red: VPC por defecto del Learner Lab (subredes públicas en 3 zonas)
# ---------------------------------------------------------------------------
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  }
}

data "aws_iam_role" "lab_role" {
  name = var.lab_role_name
}

# ---------------------------------------------------------------------------
# Security Groups: ALB (público) -> ECS (solo desde ALB) -> RDS (solo desde ECS)
# ---------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "Trafico HTTP publico hacia el ALB"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "ecs" {
  name        = "${local.name}-ecs-sg"
  description = "Tareas de ECS: solo reciben trafico del ALB"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  for_each = toset(["8000", "8080"])

  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = tonumber(each.value)
  to_port                      = tonumber(each.value)
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  # Salida necesaria para descargar imágenes de ECR y leer SSM
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "PostgreSQL: solo accesible desde las tareas de ECS"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# ---------------------------------------------------------------------------
# Base de datos: RDS PostgreSQL (una instancia por ambiente)
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length           = 24
  special          = true
  override_special = "-_"
}

# La contraseña se guarda cifrada en SSM y ECS la inyecta como secreto
resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project_name}/${var.environment_name}/db_password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "this" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "tareas"
  username = "tareas_admin"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period    = var.environment_name == "production" ? 1 : 0
  auto_minor_version_upgrade = true
  apply_immediately          = true
  skip_final_snapshot        = true
  deletion_protection        = false
}

# ---------------------------------------------------------------------------
# Balanceador: un ALB por ambiente con enrutamiento por ruta
# ---------------------------------------------------------------------------
# Sin access logs en S3: la política (SCP) del AWS Learner Lab niega
# s3:GetBucketObjectLockConfiguration, que Terraform necesita para gestionar
# buckets. Las peticiones quedan registradas en los logs de ECS (CloudWatch).
resource "aws_lb" "this" {
  name                       = "${local.name}-alb"
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = data.aws_subnets.default.ids
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "backend" {
  name                 = "${local.name}-api-tg"
  port                 = 8000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.default.id
  deregistration_delay = 15

  health_check {
    path                = "/api/health"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group" "frontend" {
  name                 = "${local.name}-web-tg"
  port                 = 8080
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.default.id
  deregistration_delay = 15

  health_check {
    path                = "/healthz"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# HTTP sin TLS: el AWS Learner Lab no tiene dominio propio, y sin dominio ACM no
# puede emitir un certificado. En un ambiente real: listener 443 con ACM y
# redirección 80 -> 443.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}

# ---------------------------------------------------------------------------
# ECS Fargate: clúster, task definitions y servicios
# ---------------------------------------------------------------------------
resource "aws_ecs_cluster" "this" {
  name = "${local.name}-cluster"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${local.name}"
  retention_in_days = 30
}

locals {
  log_options = {
    "awslogs-group"         = aws_cloudwatch_log_group.this.name
    "awslogs-region"        = var.aws_region
    "awslogs-stream-prefix" = "ecs"
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = data.aws_iam_role.lab_role.arn
  task_role_arn            = data.aws_iam_role.lab_role.arn
  # Conserva las revisiones anteriores ACTIVAS para poder hacer rollback
  skip_destroy = true

  container_definitions = jsonencode([{
    name         = "backend"
    image        = var.backend_image_uri
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "DB_HOST", value = aws_db_instance.this.address },
      { name = "DB_PORT", value = tostring(aws_db_instance.this.port) },
      { name = "DB_NAME", value = aws_db_instance.this.db_name },
      { name = "DB_USER", value = aws_db_instance.this.username },
      { name = "APP_VERSION", value = var.app_version },
      { name = "ENVIRONMENT", value = var.environment_name },
    ]
    secrets = [
      { name = "DB_PASSWORD", valueFrom = aws_ssm_parameter.db_password.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options   = local.log_options
    }
  }])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = data.aws_iam_role.lab_role.arn
  task_role_arn            = data.aws_iam_role.lab_role.arn
  skip_destroy             = true

  container_definitions = jsonencode([{
    name         = "frontend"
    image        = var.frontend_image_uri
    essential    = true
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options   = local.log_options
    }
  }])
}

locals {
  services = {
    backend = {
      task_definition  = aws_ecs_task_definition.backend.arn
      target_group_arn = aws_lb_target_group.backend.arn
      port             = 8000
    }
    frontend = {
      task_definition  = aws_ecs_task_definition.frontend.arn
      target_group_arn = aws_lb_target_group.frontend.arn
      port             = 8080
    }
  }
}

resource "aws_ecs_service" "this" {
  for_each = local.services

  name                              = "${local.name}-${each.key}"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = each.value.task_definition
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true # Sin NAT: necesario para descargar de ECR
  }

  load_balancer {
    target_group_arn = each.value.target_group_arn
    container_name   = each.key
    container_port   = each.value.port
  }

  # Si las tareas nuevas no quedan sanas, ECS vuelve solo a la versión anterior
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Terraform crea el servicio; la versión de la app la cambia el job
  # "deploy-app" (aws ecs update-service), así Infra y App son etapas separadas.
  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener_rule.api, aws_db_instance.this]
}
