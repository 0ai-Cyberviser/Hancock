###############################################################################
# Hancock Terraform — Outputs
###############################################################################

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.hancock.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.hancock.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.hancock.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.hancock.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Hancock container logs"
  value       = aws_cloudwatch_log_group.hancock.name
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution IAM role"
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task IAM role"
  value       = aws_iam_role.ecs_task.arn
}
