variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "gestor-tareas"
}

variable "environment_name" {
  description = "Nombre del ambiente: staging o production"
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment_name)
    error_message = "environment_name debe ser staging o production."
  }
}

variable "backend_image_uri" {
  description = "Imagen del backend en ECR (etiquetada con el SHA)"
  type        = string
}

variable "frontend_image_uri" {
  description = "Imagen del frontend en ECR (etiquetada con el SHA)"
  type        = string
}

variable "app_version" {
  description = "Versión desplegada (SHA del commit); la muestra /api/health"
  type        = string
  default     = "manual"
}

variable "lab_role_name" {
  description = "Rol IAM del AWS Learner Lab usado por las tareas de ECS"
  type        = string
  default     = "LabRole"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "desired_count" {
  description = "Número de tareas por servicio"
  type        = number
  default     = 1
}
