# Registro de imágenes (ECR) compartido por Staging y Producción.
# Se aplica en el job "release" antes de publicar las imágenes.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    key = "registry/terraform.tfstate"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "gestor-tareas"
}

locals {
  components = toset(["backend", "frontend"])
}

resource "aws_ecr_repository" "this" {
  for_each = local.components

  name = "${var.project_name}-${each.key}"
  # Inmutable: una etiqueta (SHA) siempre apunta a la misma imagen -> rollback confiable
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar solo las ultimas 30 imagenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = { type = "expire" }
    }]
  })
}

output "backend_repository_url" {
  value = aws_ecr_repository.this["backend"].repository_url
}

output "frontend_repository_url" {
  value = aws_ecr_repository.this["frontend"].repository_url
}

output "registry" {
  value = split("/", aws_ecr_repository.this["backend"].repository_url)[0]
}
