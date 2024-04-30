variable app_name{
  description = "app name"
  default = "tig"
  type = string
}

variable image{
  description = "ECR image arn"
  default = ""
  type = string
}

variable lambda_container_image_uri{
  description = "public image url"
  type = string
}

variable lambda_role{
  description = "role for lambda"
  type = string
}

variable timeout{
  description = "Lambda function timeout"
  type = number
  default = 600
}

variable memory_size{
  description = "Lambda memory size"
  type = number
  default = 1024
}

variable command{
  description = "Command to run for docker container"
  type = list(string)
  default = ["podaac.lambda_handler.lambda_handler.handler"]
}

variable entry_point{
  description = "Entry point for docker container"
  type = list(string)
  default = ["/var/lang/bin/python", "-m", "awslambdaric"]
}

variable working_directory{
  description = "Working directory for docker container"
  type = string
  default = "/var/task"
}

variable cmr_environment{
  description = "cmr environment"
  type = string
  default = ""
}

variable prefix{
  description = "prefix to aws resources"
  type = string
  default = ""
}

variable subnet_ids{
  description = "subnet id for lambda function"
  type = list(string)
}

variable security_group_ids{
  description = "security group for lambda"
  type = list(string)
}

variable tags{
  description = "tags"
  type = map(string)
  default = {}
}

variable task_logs_retention_in_days{
  description = "Log retention days"
  type = number
  default = 30
}

variable config_bucket{
  description = "Bucket where image configuration files are"
  type = string
  default = null
}

variable config_dir{
  description = "directory of the configuration files in a bucket"
  type = string
  default = null
}

variable config_url{
  description = "the url of where to retrieve configurations"
  type = string
  default = null
}

variable "footprint_output_bucket" {
  type = string
}

variable "footprint_output_dir" {
  type = string
}

variable log_level{
  description = "log level of cumulus logger"
  type = string
  default = "info"
}

variable region{
  description = "aws region"
  type = string
  default = "us-west-2"
}

variable architectures {
  default = ["arm64"]
  type = list
}