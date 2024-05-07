locals {
  # This is the convention we use to know what belongs to each other
  lambda_resources_name = terraform.workspace == "default" ? "svc-${local.name}-${local.environment}" : "svc-${local.name}-${local.environment}-${terraform.workspace}"
}

resource "aws_lambda_function" "forge_py_task" {

  depends_on = [
    null_resource.upload_ecr_image
  ]

  function_name = "${var.prefix}-forge-py-lambda"
  image_uri     = "${aws_ecr_repository.lambda-image-repo.repository_url}:${local.ecr_image_tag}"
  role          = var.lambda_role
  timeout       = var.timeout
  memory_size   = var.memory_size
  package_type  = "Image"
  
  architectures = var.architectures

  image_config {
    command = var.command
    entry_point = var.entry_point
    working_directory = var.working_directory
  }

  environment {
    variables = {
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
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tags = merge(var.tags, { Project = var.prefix })
}

resource "aws_cloudwatch_log_group" "forge_py_task" {
  name              = "/aws/lambda/${aws_lambda_function.forge_py_task.function_name}"
  retention_in_days = var.task_logs_retention_in_days
  tags              = merge(var.tags, { Project = var.prefix })
}


resource "aws_lambda_function" "forge_branch_task" {

  depends_on = [
    null_resource.upload_ecr_image
  ]

  function_name = "${var.prefix}-forge-branch-lambda"
  image_uri     = "${aws_ecr_repository.lambda-image-repo.repository_url}:${local.ecr_image_tag}"
  role          = var.lambda_role
  timeout       = var.timeout
  memory_size   = 256
  package_type  = "Image"
  
  architectures = var.architectures

  image_config {
    command = ["podaac.lambda_handler.lambda_handler_branch.handler"]
    entry_point = var.entry_point
    working_directory = var.working_directory
  }

  environment {
    variables = {
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
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tags = merge(var.tags, { Project = var.prefix })
}

resource "aws_cloudwatch_log_group" "forge_branch_task" {
  name              = "/aws/lambda/${aws_lambda_function.forge_branch_task.function_name}"
  retention_in_days = var.task_logs_retention_in_days
  tags              = merge(var.tags, { Project = var.prefix })
}

