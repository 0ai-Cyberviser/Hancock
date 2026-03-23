###############################################################################
# Hancock Terraform — Input Variables
###############################################################################

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of the VPC to deploy into"
  type        = string
}

variable "name_prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "hancock"
}

variable "container_image" {
  description = "Full Docker image URI for the Hancock agent"
  type        = string
  default     = "ghcr.io/0ai-cyberviser/hancock:latest"
}

variable "llm_backend" {
  description = "LLM backend to use: 'openai' or 'ollama'"
  type        = string
  default     = "openai"
  validation {
    condition     = contains(["openai", "ollama"], var.llm_backend)
    error_message = "llm_backend must be 'openai' or 'ollama'."
  }
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "task_cpu" {
  description = "ECS task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "ECS task memory in MiB"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Initial ECS service replica count"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum ECS auto-scaling capacity"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum ECS auto-scaling capacity"
  type        = number
  default     = 10
}

variable "enable_deletion_protection" {
  description = "Enable ALB deletion protection"
  type        = bool
  default     = true
}

variable "nvidia_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the NVIDIA API key"
  type        = string
  default     = ""
}

variable "openai_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the OpenAI API key"
  type        = string
  default     = ""
}

variable "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications (optional)"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project     = "hancock"
    ManagedBy   = "terraform"
    Environment = "production"
  }
}
