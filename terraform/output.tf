output "forge_py_task_lambda_arn"{
  value = aws_lambda_function.forge_py_task.arn
}

output "cloudwatch_tig_task_lambda_name" {
  value = aws_cloudwatch_log_group.forge_py_task.name
}