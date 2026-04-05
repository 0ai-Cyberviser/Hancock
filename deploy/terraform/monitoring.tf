# CloudWatch alarms and dashboard for Hancock on AWS

# ── CloudWatch Dashboard ──────────────────────────────────────────────────────
resource "aws_cloudwatch_dashboard" "hancock" {
  dashboard_name = "${var.project}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          title  = "ECS CPU Utilization"
          period = 60
          stat   = "Average"
          metrics = [["AWS/ECS", "CPUUtilization",
            "ServiceName", aws_ecs_service.hancock.name,
            "ClusterName", aws_ecs_cluster.hancock.name]]
        }
      },
      {
        type = "metric"
        properties = {
          title  = "ECS Memory Utilization"
          period = 60
          stat   = "Average"
          metrics = [["AWS/ECS", "MemoryUtilization",
            "ServiceName", aws_ecs_service.hancock.name,
            "ClusterName", aws_ecs_cluster.hancock.name]]
        }
      },
      {
        type = "metric"
        properties = {
          title  = "ALB Request Count"
          period = 60
          stat   = "Sum"
          metrics = [["AWS/ApplicationELB", "RequestCount",
            "LoadBalancer", aws_lb.hancock.arn_suffix]]
        }
      },
    ]
  })
}

# ── CPU alarm ─────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 120
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Hancock ECS CPU > 80%"

  dimensions = {
    ServiceName = aws_ecs_service.hancock.name
    ClusterName = aws_ecs_cluster.hancock.name
  }

  alarm_actions = []  # Add SNS ARN here if needed
  tags          = local.common_tags
}

# ── ALB 5xx alarm ─────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.project}-alb-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Hancock ALB 5xx errors > 10 in 1 minute"

  dimensions = {
    LoadBalancer = aws_lb.hancock.arn_suffix
  }

  treat_missing_data = "notBreaching"
  tags               = local.common_tags
}
