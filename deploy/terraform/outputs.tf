output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.hancock.dns_name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.hancock.arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.hancock.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Hancock container logs"
  value       = aws_cloudwatch_log_group.hancock.name
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.hancock.arn
}
