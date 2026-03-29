terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "hancock" {
  name = "${var.project}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

resource "aws_ecs_cluster_capacity_providers" "hancock" {
  cluster_name       = aws_ecs_cluster.hancock.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ── Task definition ───────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "hancock" {
  family                   = var.project
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "hancock"
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true

    portMappings = [
      { containerPort = 5000, protocol = "tcp", name = "http" },
      { containerPort = 8001, protocol = "tcp", name = "metrics" },
    ]

    environment = [
      { name = "HANCOCK_LLM_BACKEND", value = "openai" },
      { name = "HANCOCK_PORT",         value = "5000" },
      { name = "LOG_FORMAT",           value = "json" },
      { name = "LOG_LEVEL",            value = "INFO" },
    ]

    secrets = [
      { name = "OPENAI_API_KEY",      valueFrom = "${aws_secretsmanager_secret.hancock.arn}:openai_api_key::" },
      { name = "HANCOCK_API_KEY",     valueFrom = "${aws_secretsmanager_secret.hancock.arn}:hancock_api_key::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.hancock.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)\" || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 15
    }
  }])

  tags = local.common_tags
}

# ── ECS Service ───────────────────────────────────────────────────────────────
resource "aws_ecs_service" "hancock" {
  name                               = var.project
  cluster                            = aws_ecs_cluster.hancock.id
  task_definition                    = aws_ecs_task_definition.hancock.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  health_check_grace_period_seconds  = 30

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.hancock.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.hancock.arn
    container_name   = "hancock"
    container_port   = 5000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────
resource "aws_appautoscaling_target" "hancock" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.hancock.name}/${aws_ecs_service.hancock.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.project}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.hancock.resource_id
  scalable_dimension = aws_appautoscaling_target.hancock.scalable_dimension
  service_namespace  = aws_appautoscaling_target.hancock.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# ── Secrets Manager ───────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "hancock" {
  name                    = "${var.project}/secrets"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

# Provide a placeholder JSON structure for the secret.  Replace the values
# out-of-band (e.g. via CI/CD or the AWS Console) before first deploy.
resource "aws_secretsmanager_secret_version" "hancock" {
  secret_id = aws_secretsmanager_secret.hancock.id
  secret_string = jsonencode({
    openai_api_key  = ""
    hancock_api_key = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ── CloudWatch Log Group ──────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "hancock" {
  name              = "/ecs/${var.project}"
  retention_in_days = 30
  tags              = local.common_tags
}

# ── IAM Roles ─────────────────────────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = local.common_tags
}

# ── Locals ────────────────────────────────────────────────────────────────────
locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
