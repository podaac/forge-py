locals {
  # This is the convention we use to know what belongs to each other
  ecs_resources_name = terraform.workspace == "default" ? "svc-${local.name}-${local.environment}" : "svc-${local.name}-${local.environment}-${terraform.workspace}"
}

resource "aws_sfn_activity" "forge_py_ecs_task" {
  name = "${local.ecs_resources_name}-ecs-activity"
  tags = merge(var.tags, { Project = var.prefix })
}

module "forge_py_fargate" {

  count = var.forge_py_fargate ? 1 : 0

  source = "./fargate"

  prefix = var.prefix
  app_name = var.app_name
  tags = var.tags
  iam_role = var.fargate_iam_role
  command = [
    "/var/lang/bin/python",
    "/var/task//podaac/lambda_handler/lambda_handler.py",
    "activity",
    "--arn",
    aws_sfn_activity.forge_py_ecs_task.id
  ]

  environment = {
    STACK_NAME                  = var.prefix
    CMR_ENVIRONMENT             = var.cmr_environment
    CUMULUS_MESSAGE_ADAPTER_DIR = "/opt/"
    REGION                      = var.region
    CONFIG_BUCKET               = var.config_bucket
    CONFIG_DIR                  = var.config_dir
    FOOTPRINT_OUTPUT_BUCKET     = var.footprint_output_bucket
    FOOTPRINT_OUTPUT_DIR        = var.footprint_output_dir
    CONFIG_URL                  = var.config_url
    LOGGING_LEVEL               = var.log_level
    PYTHONPATH                  = ":/var/task"
  }

  image = "${aws_ecr_repository.lambda-image-repo.repository_url}:${local.ecr_image_tag}"
  ecs_cluster_arn = var.ecs_cluster_arn
  subnet_ids = var.subnet_ids
  scale_dimensions =  var.scale_dimensions != null ? var.scale_dimensions : {"ServiceName" = "${var.prefix}-${var.app_name}-fargate-service","ClusterName" = var.ecs_cluster_name}

  cpu = var.fargate_cpu
  memory = var.fargate_memory
  cluster_name = var.ecs_cluster_name

  desired_count = var.fargate_desired_count
  max_capacity = var.fargate_max_capacity
  min_capacity = var.fargate_min_capacity

  scale_up_cooldown = var.scale_up_cooldown
  scale_down_cooldown = var.scale_down_cooldown

  # Scale up settings
  comparison_operator_scale_up = var.comparison_operator_scale_up
  evaluation_periods_scale_up = var.evaluation_periods_scale_up
  metric_name_scale_up = var.metric_name_scale_up
  namespace_scale_up = var.namespace_scale_up
  period_scale_up = var.period_scale_up
  statistic_scale_up = var.statistic_scale_up
  threshold_scale_up = var.threshold_scale_up
  scale_up_step_adjustment = var.scale_up_step_adjustment

  # Scale down settings
  comparison_operator_scale_down = var.comparison_operator_scale_down
  evaluation_periods_scale_down = var.evaluation_periods_scale_down
  metric_name_scale_down = var.metric_name_scale_down
  namespace_scale_down = var.namespace_scale_down
  period_scale_down = var.period_scale_down
  statistic_scale_down = var.statistic_scale_down
  threshold_scale_down = var.threshold_scale_down
  scale_down_step_adjustment = var.scale_down_step_adjustment
}